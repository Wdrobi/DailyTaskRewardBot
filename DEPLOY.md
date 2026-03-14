# Always-On Deployment

This bot uses Telegram long polling. Static hosts like Netlify or Vercel cannot keep it running 24/7. Use an always-on worker/server.

## Recommended options

1. Railway
2. Render Worker
3. VPS with Docker

## Shared environment variables

Set these on your server or hosting provider:

- `BOT_TOKEN`
- `ADMIN_IDS`
- `BOT_USERNAME`
- `FORCE_JOIN_CHANNELS`
- `MINI_APP_URL`
- `TUTORIAL_VIDEO_URL`
- `DATABASE_PATH`

Example:

```env
BOT_TOKEN=123456:replace_me
ADMIN_IDS=1262785125
BOT_USERNAME=DailyTaskRewardBot
FORCE_JOIN_CHANNELS=@yourchannel
MINI_APP_URL=https://dailytaskrewardbot.netlify.app/
TUTORIAL_VIDEO_URL=https://youtube.com/watch?v=your_video_id
DATABASE_PATH=/data/bot_database.db
```

## Railway

1. Create a new project from the GitHub repo.
2. Railway will detect the `Dockerfile` automatically.
3. Add the environment variables from the list above.
4. Add a persistent volume and mount it to `/data`.
5. Deploy.

## Render

1. Create a new Worker service from the repo.
2. Render can use `render.yaml` or the `Dockerfile` directly.
3. Set the same environment variables.
4. Add a disk and mount it to `/data`.
5. Deploy.

## VPS with Docker

```bash
docker build -t daily-task-reward-bot .
docker run -d \
  --name daily-task-reward-bot \
  --restart unless-stopped \
  -e BOT_TOKEN=123456:replace_me \
  -e ADMIN_IDS=1262785125 \
  -e BOT_USERNAME=DailyTaskRewardBot \
  -e FORCE_JOIN_CHANNELS=@yourchannel \
  -e MINI_APP_URL=https://dailytaskrewardbot.netlify.app/ \
  -e TUTORIAL_VIDEO_URL=https://youtube.com/watch?v=your_video_id \
  -e DATABASE_PATH=/data/bot_database.db \
  -v daily-task-reward-bot-data:/data \
  daily-task-reward-bot
```

## VPS with systemd

1. Install Python 3.12+ on the server.
2. Clone the repo into `/opt/daily-task-reward-bot`.
3. Create a virtualenv and install requirements.
4. Put your real env vars into `/opt/daily-task-reward-bot/.env`.
5. Copy `deploy/systemd/daily-task-reward-bot.service` to `/etc/systemd/system/`.
6. Run `sudo systemctl daemon-reload`.
7. Run `sudo systemctl enable --now daily-task-reward-bot`.

Check logs:

```bash
sudo journalctl -u daily-task-reward-bot -f
```

## Important notes

- Rotate the Telegram bot token if the old token was exposed anywhere.
- Keep `.env` local only. Do not commit real secrets.
- If you use SQLite in production, attach persistent storage. Without a disk, your data will be lost on redeploy.
- For higher reliability at scale, move from SQLite to PostgreSQL later.