import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "YourBot")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_database.db")
MINI_APP_URL: str = os.getenv("MINI_APP_URL", "")
TUTORIAL_VIDEO_URL: str = os.getenv("TUTORIAL_VIDEO_URL", "https://youtube.com")
FORCE_JOIN_CHANNELS: list[str] = [
    item.strip()
    for item in os.getenv("FORCE_JOIN_CHANNELS", "").split(",")
    if item.strip()
]

_raw_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x.strip()) for x in _raw_admin_ids.split(",") if x.strip().isdigit()]

ADMIN_API_TOKEN: str = os.getenv("ADMIN_API_TOKEN", "")
ADMIN_API_PORT: int = int(os.getenv("ADMIN_API_PORT", "8080"))
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")

# ---------- টাস্ক রিওয়ার্ড (পয়েন্ট) ----------
TASK_REWARDS: dict[str, int] = {
    "watch_ad":      300,
    "visit_site":    400,
    "daily_checkin": 200,
}

# রেফারেল রিওয়ার্ড
REFERRAL_REWARD: int = 5000

# ---------- প্রতিদিনের সীমা ----------
DAILY_TASK_LIMITS: dict[str, int] = {
    "watch_ad":      30,
    "visit_site":    15,
    "daily_checkin": 1,
}

# ---------- কুলডাউন (সেকেন্ড) ----------
TASK_COOLDOWNS: dict[str, int] = {
    "watch_ad":      3600,   # ১ ঘণ্টা
    "visit_site":    14400,  # ৪ ঘণ্টা
    "daily_checkin": 86400,  # ২৪ ঘণ্টা
}

# অ্যাড দেখার সর্বনিম্ন সময় (সেকেন্ড) — অ্যান্টি-চিট
MIN_AD_WATCH_SECONDS: int = 15
MIN_SITE_VISIT_SECONDS: int = 10

# ---------- উইথড্রয়াল সেটিংস ----------
WITHDRAWAL_ENABLED: bool = False       # পেমেন্ট ইন্টিগ্রেশন সম্পন্ন হলে True করুন
MIN_WITHDRAWAL_POINTS: int = 500        # ন্যূনতম উত্তোলনযোগ্য পয়েন্ট
POINTS_PER_TAKA: int = 100              # 100 পয়েন্ট = 1 টাকা

# ---------- স্যাম্পল অ্যাড / সাইট URL (পরে DB থেকে নেওয়া যাবে) ----------
AD_URL: str = "https://example.com/ad"
SITE_URLS: list[str] = [
    "https://example.com/site1",
    "https://example.com/site2",
    "https://example.com/site3",
]

# ---------- রেট লিমিট (মিডলওয়্যার) ----------
THROTTLE_RATE: float = 0.5   # সেকেন্ডে বার্তা-ব্যবধান (স্প্যাম কন্ট্রোল)
