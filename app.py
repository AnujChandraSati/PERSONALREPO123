import logging
import os
import shutil
import threading
import uuid

from flask import Flask, jsonify, request

from extractor import extract_media
from telegram_utils import (
    delete_message,
    send_document,
    send_message,
    send_photo,
    set_webhook,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "changeme")
BASE_URL = os.environ.get("BASE_URL")  # e.g. https://your-app.onrender.com
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "10"))

app = Flask(__name__)

# Register the webhook with Telegram once at startup (idempotent, safe to
# call on every worker boot). Only runs if BASE_URL is set.
if BASE_URL:
    _webhook_url = f"{BASE_URL.rstrip('/')}/webhook/{WEBHOOK_SECRET}"
    _result = set_webhook(BOT_TOKEN, _webhook_url)
    logger.info("setWebhook -> %s : %s", _webhook_url, _result)


@app.route("/", methods=["GET"])
def health():
    # Ping this endpoint to keep the free-tier service awake.
    return "ok", 200


@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    message = update.get("message") or update.get("channel_post")
    if not message:
        return jsonify(ok=True)

    chat_id = message["chat"]["id"]
    message_id = message.get("message_id")
    text = (message.get("text") or "").strip()

    if not text:
        return jsonify(ok=True)

    if text in ("/start", "/help"):
        send_message(
            BOT_TOKEN,
            chat_id,
            "Send me a URL (Reddit, Twitter/X, Instagram, etc.) and I'll pull out the media and send it back.",
        )
        return jsonify(ok=True)

    if not text.startswith("http"):
        send_message(BOT_TOKEN, chat_id, "That doesn't look like a URL. Send me a link.")
        return jsonify(ok=True)

    # Process in a background thread so we return 200 to Telegram immediately
    # (otherwise Telegram will retry the webhook on slow extractions).
    threading.Thread(target=process_url, args=(chat_id, text, message_id), daemon=True).start()
    return jsonify(ok=True)


def process_url(chat_id, url, message_id):
    workdir = f"/tmp/media/{uuid.uuid4().hex}"
    try:
        items, status = extract_media(url, workdir)

        # We only ever attempt to send photos/documents. Videos are counted
        # but not sent (this bot is images-only).
        photo_items = [i for i in items if i["kind"] == "photo"]
        doc_items = [i for i in items if i["kind"] not in ("photo", "video")]
        video_items = [i for i in items if i["kind"] == "video"]
        sendable = (photo_items + doc_items)[:MAX_ITEMS]

        sent = 0
        for item in sendable:
            is_file = item["source"] == "file"
            try:
                if item["kind"] == "photo":
                    resp = send_photo(BOT_TOKEN, chat_id, item["value"], is_file=is_file)
                else:
                    resp = send_document(BOT_TOKEN, chat_id, item["value"], is_file=is_file)

                if resp.get("ok"):
                    sent += 1
                else:
                    logger.warning("Telegram send failed: %s", resp)
            except Exception:
                logger.exception("Failed to send item: %s", item)

        has_video = len(video_items) > 0
        has_photo_sent = sent > 0

        if not items:
            # Nothing extracted at all -- most likely an unsupported/video post.
            send_message(
                BOT_TOKEN, chat_id,
                f"Couldn't grab anything from this one (might be a video):\n{url}",
                reply_to_message_id=message_id,
            )
        elif has_video and has_photo_sent:
            n = len(video_items)
            noun = "a video" if n == 1 else f"{n} videos"
            send_message(
                BOT_TOKEN, chat_id,
                f"Sent the photos -- there's also {noun} in there I can't grab:\n{url}",
                reply_to_message_id=message_id,
            )
        elif has_video and not has_photo_sent:
            n = len(video_items)
            noun = "a video" if n == 1 else f"{n} videos"
            send_message(
                BOT_TOKEN, chat_id,
                f"Looks like this is {noun} -- I only grab images:\n{url}",
                reply_to_message_id=message_id,
            )
        elif has_photo_sent:
            # Pure photo success -- clean up by deleting the original message.
            if message_id:
                delete_message(BOT_TOKEN, chat_id, message_id)
        else:
            send_message(
                BOT_TOKEN, chat_id,
                f"Found media but couldn't send it:\n{url}",
                reply_to_message_id=message_id,
            )

    except Exception as e:
        logger.exception("process_url failed")
        send_message(
            BOT_TOKEN, chat_id, f"Something went wrong with:\n{url}",
            reply_to_message_id=message_id,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
