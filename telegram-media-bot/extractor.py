import os
import subprocess

import yt_dlp
from RedDownloader import RedDownloader

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic"}
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov"}


def _kind_for_ext(ext):
    ext = (ext or "").lower()
    if ext in IMAGE_EXTS:
        return "photo"
    if ext in VIDEO_EXTS:
        return "video"
    return "document"


# ---------- Reddit (RedDownloader) ----------

def extract_reddit(url, workdir):
    os.makedirs(workdir, exist_ok=True)
    try:
        RedDownloader.Download(url, output="media", destination=workdir, verbose=False)
    except Exception as e:
        return [], f"RedDownloader error: {e}"

    files = []
    for root, _dirs, fs in os.walk(workdir):
        for f in fs:
            files.append(os.path.join(root, f))

    items = [
        {"kind": _kind_for_ext(os.path.splitext(f)[1]), "source": "file", "value": f}
        for f in files
    ]
    status = f"{len(items)} file(s) downloaded."
    return items, status


# ---------- Generic (yt-dlp) ----------

def _collect_ytdlp_urls(entry):
    found = []
    for fmt in entry.get("formats") or []:
        ext = (fmt.get("ext") or "").lower()
        if ext in IMAGE_EXTS and fmt.get("url"):
            found.append(("photo", fmt["url"]))
        elif ext in VIDEO_EXTS and fmt.get("vcodec") not in (None, "none") and fmt.get("url"):
            found.append(("video", fmt["url"]))

    if (entry.get("ext") or "").lower() in IMAGE_EXTS and entry.get("url"):
        found.append(("photo", entry["url"]))

    if not found:
        thumb = entry.get("thumbnail")
        if thumb:
            found.append(("photo", thumb))

    return found


def extract_ytdlp(url):
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return [], f"yt-dlp error: {e}"

    if not info:
        return [], "yt-dlp returned nothing."

    entries = [e for e in (info.get("entries") or [info]) if e]

    items = []
    seen = set()
    for entry in entries:
        for kind, u in _collect_ytdlp_urls(entry):
            if u not in seen:
                seen.add(u)
                items.append({"kind": kind, "source": "url", "value": u})

    status = f"{len(entries)} entrie(s), {len(items)} media item(s) found."
    return items, status


# ---------- Generic fallback (gallery-dl) ----------

def extract_gallery_dl(url):
    try:
        result = subprocess.run(
            ["gallery-dl", "-g", url], capture_output=True, text=True, timeout=90
        )
    except Exception as e:
        return [], f"gallery-dl error: {e}"

    urls = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    items = []
    for u in urls:
        ext = os.path.splitext(u.split("?")[0])[1]
        items.append({"kind": _kind_for_ext(ext) or "photo", "source": "url", "value": u})

    status = f"{len(items)} item(s) found."
    return items, status


# ---------- Dispatcher ----------

def extract_media(url, workdir):
    url = url.strip()

    if "reddit.com" in url or "redd.it" in url:
        items, status = extract_reddit(url, workdir)
        return items, f"[RedDownloader] {status}"

    items, status = extract_ytdlp(url)
    if items:
        return items, f"[yt-dlp] {status}"

    g_items, g_status = extract_gallery_dl(url)
    return g_items, f"[yt-dlp] {status} | [gallery-dl] {g_status}"
