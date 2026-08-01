import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _call(token, method, data=None, files=None, timeout=60):
    url = TELEGRAM_API.format(token=token, method=method)
    resp = requests.post(url, data=data, files=files, timeout=timeout)
    try:
        return resp.json()
    except Exception:
        return {"ok": False, "description": resp.text}


def send_message(token, chat_id, text):
    return _call(token, "sendMessage", data={"chat_id": chat_id, "text": text[:4096]})


def send_photo(token, chat_id, source, caption=None, is_file=False):
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption[:1024]
    if is_file:
        with open(source, "rb") as f:
            return _call(token, "sendPhoto", data=data, files={"photo": f})
    data["photo"] = source
    return _call(token, "sendPhoto", data=data)


def send_video(token, chat_id, source, caption=None, is_file=False):
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption[:1024]
    if is_file:
        with open(source, "rb") as f:
            return _call(token, "sendVideo", data=data, files={"video": f}, timeout=180)
    data["video"] = source
    return _call(token, "sendVideo", data=data, timeout=180)


def send_document(token, chat_id, source, caption=None, is_file=False):
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption[:1024]
    if is_file:
        with open(source, "rb") as f:
            return _call(token, "sendDocument", data=data, files={"document": f}, timeout=180)
    data["document"] = source
    return _call(token, "sendDocument", data=data, timeout=180)


def set_webhook(token, url, secret_token=None):
    data = {"url": url}
    if secret_token:
        data["secret_token"] = secret_token
    return _call(token, "setWebhook", data=data)
