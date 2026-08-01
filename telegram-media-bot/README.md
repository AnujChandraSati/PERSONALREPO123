# Telegram Media Extractor Bot

Send the bot a URL (Reddit, Twitter/X, Instagram, etc.) and it downloads/extracts
the media and sends it back to you in Telegram.

Routing:
- `reddit.com` / `redd.it` links → **RedDownloader** (handles galleries properly)
- everything else → **yt-dlp**, falling back to **gallery-dl** if yt-dlp finds nothing

## 1. Create the bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → follow the
   prompts → copy the bot token it gives you (looks like `123456:ABC-DEF...`).

## 2. Deploy to Render

1. Push this folder to a GitHub repo.
2. On [render.com](https://render.com) → **New +** → **Web Service** → connect the repo.
3. Runtime: Python 3. Build command: `pip install -r requirements.txt`.
   Start command is already set via the `Procfile`.
4. Add environment variables (Render dashboard → Environment):
   - `BOT_TOKEN` — the token from BotFather
   - `WEBHOOK_SECRET` — any random string you make up (acts as a secret path segment)
   - `BASE_URL` — your Render service URL, e.g. `https://your-app.onrender.com`
     (you'll know this after the first deploy — add it and redeploy once you have it)
5. Deploy. On boot, the app automatically calls Telegram's `setWebhook` pointing at
   `BASE_URL/webhook/WEBHOOK_SECRET`.

## 3. Keep it alive

You mentioned pinging it yourself — hit `GET https://your-app.onrender.com/` on an
interval (e.g. every 5 min via [cron-job.org](https://cron-job.org) or UptimeRobot,
or your own script) to keep the free-tier instance from spinning down.

## 4. Test it

Message your bot on Telegram with a URL. It should reply "Working on it..." then
send back whatever media it finds.

## Known limitations

- Telegram bots can't send files over **50MB** via this method.
- Reddit videos (`v.redd.it`) are served as separate video/audio streams; merging
  them requires `ffmpeg` on the server. Render's default Python image doesn't
  include it, so Reddit videos may arrive without audio. To fix, add an
  `apt-get install ffmpeg` step (Render supports this via a `render-build.sh`
  build script, or a Docker-based deploy).
- `MAX_ITEMS` (default 10) caps how many items get sent per carousel/gallery, to
  avoid flooding a chat with huge posts. Adjust via the env var.
- No per-user rate limiting or access control — anyone who finds your bot can use
  it. Add a check against an allow-list of Telegram user IDs in `app.py` if you
  want to restrict it to yourself.
