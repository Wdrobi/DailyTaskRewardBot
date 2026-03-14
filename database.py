import aiosqlite
import logging
from datetime import datetime, date
from typing import Optional

from config import DATABASE_PATH, POINTS_PER_TAKA

logger = logging.getLogger(__name__)


class Database:
    def __init__(self) -> None:
        self.db_path = DATABASE_PATH

    @staticmethod
    async def _seed_default_tasks(db: aiosqlite.Connection) -> None:
        async with db.execute("SELECT COUNT(*) FROM tasks") as cur:
            row = await cur.fetchone()
            if row and row[0] > 0:
                return

        default_tasks = [
            (
                "watch_ad",
                "📺 অ্যাড দেখুন",
                "একটি স্পন্সরড লিংক খুলুন এবং কিছুক্ষণ থাকুন",
                "📺 অ্যাড দেখুন",
                "link",
                "https://example.com/ad",
                400,
                30,
                3600,
                15,
                1,
                10,
            ),
            (
                "visit_site",
                "🌐 সাইট ভিজিট",
                "সাইট ভিজিট করে রিওয়ার্ড নিন",
                "🌐 সাইট ভিজিট করুন",
                "link",
                "https://example.com/site1",
                500,
                15,
                14400,
                10,
                1,
                20,
            ),
            (
                "daily_checkin",
                "📅 দৈনিক চেক-ইন",
                "প্রতিদিন ১ বার ইনস্ট্যান্ট বোনাস নিন",
                "✅ এখনই নিন",
                "instant",
                "",
                300,
                1,
                86400,
                0,
                1,
                30,
            ),
        ]

        await db.executemany(
            "INSERT INTO tasks ("
            "task_key, title, description, button_text, task_kind, target_url, reward_points, "
            "daily_limit, cooldown_seconds, verify_seconds, is_active, sort_order"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            default_tasks,
        )

    # ──────────────────────────────────────────────
    # সেটআপ
    # ──────────────────────────────────────────────
    async def init(self) -> None:
        """ডেটাবেস তৈরি করুন এবং টেবিলগুলো তৈরি করুন।"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id         INTEGER PRIMARY KEY,
                    username        TEXT    DEFAULT '',
                    full_name       TEXT    DEFAULT '',
                    referred_by     INTEGER,
                    points          INTEGER DEFAULT 0,
                    total_earned    INTEGER DEFAULT 0,
                    total_withdrawn INTEGER DEFAULT 0,
                    is_banned       INTEGER DEFAULT 0,
                    joined_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (referred_by) REFERENCES users(user_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS task_completions (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL,
                    task_type     TEXT    NOT NULL,
                    points_earned INTEGER NOT NULL,
                    completed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_key         TEXT    NOT NULL UNIQUE,
                    title            TEXT    NOT NULL,
                    description      TEXT    DEFAULT '',
                    button_text      TEXT    DEFAULT 'Open',
                    task_kind        TEXT    NOT NULL DEFAULT 'link',
                    target_url       TEXT    DEFAULT '',
                    reward_points    INTEGER NOT NULL,
                    daily_limit      INTEGER NOT NULL DEFAULT 1,
                    cooldown_seconds INTEGER NOT NULL DEFAULT 0,
                    verify_seconds   INTEGER NOT NULL DEFAULT 0,
                    is_active        INTEGER NOT NULL DEFAULT 1,
                    sort_order       INTEGER NOT NULL DEFAULT 100,
                    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id        INTEGER NOT NULL,
                    points         INTEGER NOT NULL,
                    amount_bdt     REAL    NOT NULL,
                    payment_method TEXT    NOT NULL,
                    payment_number TEXT    NOT NULL,
                    status         TEXT    DEFAULT 'pending',
                    admin_note     TEXT,
                    requested_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at   TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id    INTEGER NOT NULL,
                    referred_id    INTEGER NOT NULL UNIQUE,
                    points_awarded INTEGER NOT NULL,
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_id) REFERENCES users(user_id)
                )
            """)

            # পারফরম্যান্সের জন্য ইন্ডেক্স
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_tc_user_type_date "
                "ON task_completions(user_id, task_type, completed_at)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_active_sort "
                "ON tasks(is_active, sort_order)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_wd_user_status "
                "ON withdrawals(user_id, status)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_ref_referrer "
                "ON referrals(referrer_id)"
            )

            await self._seed_default_tasks(db)
            await db.execute(
                "UPDATE tasks SET daily_limit = 30, reward_points = 400 WHERE task_key = 'watch_ad'"
            )
            await db.execute(
                "UPDATE tasks SET daily_limit = 15, reward_points = 500 WHERE task_key = 'visit_site'"
            )
            await db.execute(
                "UPDATE tasks SET reward_points = 300 WHERE task_key = 'daily_checkin'"
            )
            await db.commit()
        logger.info("ডেটাবেস সফলভাবে প্রস্তুত।")

    # ──────────────────────────────────────────────
    # ইউজার ম্যানেজমেন্ট
    # ──────────────────────────────────────────────
    async def get_user(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def register_user(
        self,
        user_id: int,
        username: str,
        full_name: str,
        referred_by: Optional[int] = None,
    ) -> bool:
        """নতুন ইউজার রেজিস্টার করুন। নতুন হলে True, আগে থেকে আছে তাহলে False।"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, full_name, referred_by) "
                "VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, referred_by),
            )
            is_new = db.total_changes > 0
            await db.commit()
            return is_new

    async def update_user_info(self, user_id: int, username: str, full_name: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username, full_name, user_id),
            )
            await db.commit()

    async def ban_user(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
            await db.commit()
            return True

    async def unban_user(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
            await db.commit()
            return True

    # ──────────────────────────────────────────────
    # পয়েন্ট
    # ──────────────────────────────────────────────
    async def add_points(self, user_id: int, points: int) -> bool:
        """ব্যান না হলে পয়েন্ট যোগ করুন।"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users "
                "SET points = points + ?, total_earned = total_earned + ? "
                "WHERE user_id = ? AND is_banned = 0",
                (points, points, user_id),
            )
            changed = db.total_changes > 0
            await db.commit()
            return changed

    async def deduct_points(self, user_id: int, points: int) -> bool:
        """পয়েন্ট কাটুন (উইথড্রয়ালের সময়)। যথেষ্ট পয়েন্ট না থাকলে False।"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT points FROM users WHERE user_id = ? AND is_banned = 0", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                if not row or row[0] < points:
                    return False
            await db.execute(
                "UPDATE users "
                "SET points = points - ?, total_withdrawn = total_withdrawn + ? "
                "WHERE user_id = ? AND points >= ?",
                (points, points, user_id, points),
            )
            await db.commit()
            return True

    # ──────────────────────────────────────────────
    # টাস্ক
    # ──────────────────────────────────────────────
    async def get_active_tasks(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tasks WHERE is_active = 1 ORDER BY sort_order ASC, id ASC"
            ) as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def get_task_by_key(self, task_key: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tasks WHERE task_key = ? AND is_active = 1",
                (task_key,),
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_daily_task_count(self, user_id: int, task_type: str) -> int:
        today = date.today().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM task_completions "
                "WHERE user_id = ? AND task_type = ? AND DATE(completed_at) = ?",
                (user_id, task_type, today),
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

    async def get_last_task_time(self, user_id: int, task_type: str) -> Optional[datetime]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT completed_at FROM task_completions "
                "WHERE user_id = ? AND task_type = ? "
                "ORDER BY completed_at DESC LIMIT 1",
                (user_id, task_type),
            ) as cur:
                row = await cur.fetchone()
                if row:
                    return datetime.fromisoformat(row[0])
                return None

    async def record_task(self, user_id: int, task_type: str, points_earned: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO task_completions (user_id, task_type, points_earned) VALUES (?, ?, ?)",
                (user_id, task_type, points_earned),
            )
            await db.commit()
            return True

    # ──────────────────────────────────────────────
    # উইথড্রয়াল
    # ──────────────────────────────────────────────
    async def has_pending_withdrawal(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM withdrawals WHERE user_id = ? AND status = 'pending'",
                (user_id,),
            ) as cur:
                row = await cur.fetchone()
                return bool(row and row[0] > 0)

    async def create_withdrawal(
        self,
        user_id: int,
        points: int,
        payment_method: str,
        payment_number: str,
    ) -> Optional[int]:
        amount_bdt = points / POINTS_PER_TAKA
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "INSERT INTO withdrawals (user_id, points, amount_bdt, payment_method, payment_number) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, points, amount_bdt, payment_method, payment_number),
            ) as cur:
                wid = cur.lastrowid
            await db.commit()
            return wid

    async def get_pending_withdrawals(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT w.*, u.username, u.full_name "
                "FROM withdrawals w JOIN users u ON w.user_id = u.user_id "
                "WHERE w.status = 'pending' ORDER BY w.requested_at ASC"
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_withdrawal_by_id(self, withdrawal_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def update_withdrawal_status(
        self, withdrawal_id: int, status: str, admin_note: str = ""
    ) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE withdrawals "
                "SET status = ?, admin_note = ?, processed_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (status, admin_note, withdrawal_id),
            )
            await db.commit()
            return True

    async def restore_points_on_rejection(self, withdrawal_id: int) -> bool:
        """প্রত্যাখ্যাত উইথড্রয়ালের পয়েন্ট ফেরত দিন।"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT user_id, points FROM withdrawals WHERE id = ?", (withdrawal_id,)
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    return False
                user_id, points = row
            await db.execute(
                "UPDATE users "
                "SET points = points + ?, total_withdrawn = total_withdrawn - ? "
                "WHERE user_id = ?",
                (points, points, user_id),
            )
            await db.commit()
            return True

    async def get_user_withdrawals(self, user_id: int) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM withdrawals WHERE user_id = ? ORDER BY requested_at DESC LIMIT 10",
                (user_id,),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    # ──────────────────────────────────────────────
    # রেফারেল
    # ──────────────────────────────────────────────
    async def add_referral(self, referrer_id: int, referred_id: int, points: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO referrals (referrer_id, referred_id, points_awarded) VALUES (?, ?, ?)",
                (referrer_id, referred_id, points),
            )
            inserted = db.total_changes > 0
            await db.commit()
            return inserted

    async def get_referral_count(self, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) "
                "FROM referrals r "
                "JOIN users u ON u.user_id = r.referred_id "
                "WHERE r.referrer_id = ? AND u.is_banned = 0",
                (user_id,)
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

    async def get_user_referrals(self, user_id: int, limit: int = 20) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT r.referred_id, r.points_awarded, r.created_at, u.full_name, u.username "
                "FROM referrals r "
                "LEFT JOIN users u ON u.user_id = r.referred_id "
                "WHERE r.referrer_id = ? "
                "ORDER BY r.created_at DESC LIMIT ?",
                (user_id, limit),
            ) as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def get_user_today_summary(self, user_id: int) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*), COALESCE(SUM(points_earned), 0) "
                "FROM task_completions "
                "WHERE user_id = ? AND DATE(completed_at) = DATE('now')",
                (user_id,),
            ) as cur:
                row = await cur.fetchone()
                return {
                    "tasks_completed": row[0] if row else 0,
                    "points_earned": row[1] if row else 0,
                }

    async def get_user_rank(self, user_id: int) -> Optional[int]:
        user = await self.get_user(user_id)
        if not user:
            return None

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) + 1 "
                "FROM users "
                "WHERE is_banned = 0 AND total_earned > ?",
                (user["total_earned"],),
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else None

    # ──────────────────────────────────────────────
    # লিডারবোর্ড ও স্ট্যাটস
    # ──────────────────────────────────────────────
    async def get_top_users(self, limit: int = 10) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT user_id, username, full_name, total_earned, points "
                "FROM users WHERE is_banned = 0 "
                "ORDER BY total_earned DESC LIMIT ?",
                (limit,),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def get_stats(self) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            async def count(query: str, *args) -> int:
                async with db.execute(query, args) as cur:
                    row = await cur.fetchone()
                    return row[0] if row else 0

            total_users = await count("SELECT COUNT(*) FROM users WHERE is_banned = 0")
            today_users = await count(
                "SELECT COUNT(*) FROM users WHERE DATE(joined_at) = DATE('now')"
            )
            today_tasks = await count(
                "SELECT COUNT(*) FROM task_completions WHERE DATE(completed_at) = DATE('now')"
            )
            pending_wd = await count(
                "SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'"
            )
            async with db.execute(
                "SELECT COALESCE(SUM(total_earned), 0) FROM users WHERE is_banned = 0"
            ) as cur:
                total_points = (await cur.fetchone())[0]

        return {
            "total_users": total_users,
            "today_users": today_users,
            "today_tasks": today_tasks,
            "pending_withdrawals": pending_wd,
            "total_points_distributed": total_points,
        }

    async def get_all_user_ids(self) -> list[int]:
        """ব্রডকাস্টের জন্য সব ইউজারের আইডি।"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT user_id FROM users WHERE is_banned = 0"
            ) as cur:
                return [row[0] for row in await cur.fetchall()]

    # ──────────────────────────────────────────────
    # অ্যাডমিন API
    # ──────────────────────────────────────────────
    async def get_all_users(
        self, limit: int = 50, offset: int = 0, search: str = ""
    ) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if search:
                pattern = f"%{search}%"
                async with db.execute(
                    "SELECT * FROM users WHERE (username LIKE ? OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?) "
                    "ORDER BY joined_at DESC LIMIT ? OFFSET ?",
                    (pattern, pattern, pattern, limit, offset),
                ) as cur:
                    return [dict(r) for r in await cur.fetchall()]
            else:
                async with db.execute(
                    "SELECT * FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ) as cur:
                    return [dict(r) for r in await cur.fetchall()]

    async def get_users_count(self, search: str = "") -> int:
        async with aiosqlite.connect(self.db_path) as db:
            if search:
                pattern = f"%{search}%"
                async with db.execute(
                    "SELECT COUNT(*) FROM users WHERE username LIKE ? OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?",
                    (pattern, pattern, pattern),
                ) as cur:
                    row = await cur.fetchone()
                    return row[0] if row else 0
            else:
                async with db.execute("SELECT COUNT(*) FROM users") as cur:
                    row = await cur.fetchone()
                    return row[0] if row else 0

    async def get_all_withdrawals(
        self, status: str = "all", limit: int = 50, offset: int = 0
    ) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status == "all":
                async with db.execute(
                    "SELECT w.*, u.username, u.full_name FROM withdrawals w "
                    "JOIN users u ON w.user_id = u.user_id "
                    "ORDER BY w.requested_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ) as cur:
                    return [dict(r) for r in await cur.fetchall()]
            else:
                async with db.execute(
                    "SELECT w.*, u.username, u.full_name FROM withdrawals w "
                    "JOIN users u ON w.user_id = u.user_id "
                    "WHERE w.status = ? ORDER BY w.requested_at DESC LIMIT ? OFFSET ?",
                    (status, limit, offset),
                ) as cur:
                    return [dict(r) for r in await cur.fetchall()]

    async def get_withdrawals_count(self, status: str = "all") -> int:
        async with aiosqlite.connect(self.db_path) as db:
            if status == "all":
                async with db.execute("SELECT COUNT(*) FROM withdrawals") as cur:
                    row = await cur.fetchone()
                    return row[0] if row else 0
            else:
                async with db.execute(
                    "SELECT COUNT(*) FROM withdrawals WHERE status = ?", (status,)
                ) as cur:
                    row = await cur.fetchone()
                    return row[0] if row else 0

    async def get_all_tasks(self, include_inactive: bool = True) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            base_query = (
                "SELECT t.*, "
                "COALESCE((SELECT COUNT(*) FROM task_completions tc WHERE tc.task_type = t.task_key), 0) AS total_completions, "
                "COALESCE((SELECT COUNT(*) FROM task_completions tc WHERE tc.task_type = t.task_key AND DATE(tc.completed_at) = DATE('now')), 0) AS today_completions "
                "FROM tasks t"
            )
            if include_inactive:
                query = base_query + " ORDER BY t.sort_order ASC, t.id ASC"
                params = ()
            else:
                query = base_query + " WHERE t.is_active = 1 ORDER BY t.sort_order ASC, t.id ASC"
                params = ()
            async with db.execute(query, params) as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def get_task_admin_by_id(self, task_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def create_task_admin(self, task_data: dict) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "INSERT INTO tasks ("
                "task_key, title, description, button_text, task_kind, target_url, reward_points, "
                "daily_limit, cooldown_seconds, verify_seconds, is_active, sort_order"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task_data["task_key"],
                    task_data["title"],
                    task_data["description"],
                    task_data["button_text"],
                    task_data["task_kind"],
                    task_data["target_url"],
                    task_data["reward_points"],
                    task_data["daily_limit"],
                    task_data["cooldown_seconds"],
                    task_data["verify_seconds"],
                    task_data["is_active"],
                    task_data["sort_order"],
                ),
            ) as cur:
                task_id = cur.lastrowid
            await db.commit()
            return task_id

    async def update_task_admin(self, task_id: int, task_data: dict) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET "
                "task_key = ?, title = ?, description = ?, button_text = ?, task_kind = ?, target_url = ?, "
                "reward_points = ?, daily_limit = ?, cooldown_seconds = ?, verify_seconds = ?, "
                "is_active = ?, sort_order = ? "
                "WHERE id = ?",
                (
                    task_data["task_key"],
                    task_data["title"],
                    task_data["description"],
                    task_data["button_text"],
                    task_data["task_kind"],
                    task_data["target_url"],
                    task_data["reward_points"],
                    task_data["daily_limit"],
                    task_data["cooldown_seconds"],
                    task_data["verify_seconds"],
                    task_data["is_active"],
                    task_data["sort_order"],
                    task_id,
                ),
            )
            await db.commit()
            return db.total_changes > 0

    async def set_task_active_admin(self, task_id: int, is_active: bool) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, task_id),
            )
            await db.commit()
            return db.total_changes > 0

    async def delete_task_admin(self, task_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            await db.commit()
            return db.total_changes > 0

    async def get_user_admin_details(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
                user_row = await cur.fetchone()
                if not user_row:
                    return None
                user = dict(user_row)

            referred_by_user = None
            if user.get("referred_by"):
                async with db.execute(
                    "SELECT user_id, username, full_name FROM users WHERE user_id = ?",
                    (user["referred_by"],),
                ) as cur:
                    ref_row = await cur.fetchone()
                    referred_by_user = dict(ref_row) if ref_row else None

            async with db.execute(
                "SELECT COUNT(*), COALESCE(SUM(points_earned), 0) "
                "FROM task_completions WHERE user_id = ?",
                (user_id,),
            ) as cur:
                total_tasks_row = await cur.fetchone()

            async with db.execute(
                "SELECT COUNT(*), COALESCE(SUM(points_earned), 0) "
                "FROM task_completions WHERE user_id = ? AND DATE(completed_at) = DATE('now')",
                (user_id,),
            ) as cur:
                today_tasks_row = await cur.fetchone()

            async with db.execute(
                "SELECT COUNT(*), COALESCE(SUM(points_awarded), 0) "
                "FROM referrals WHERE referrer_id = ?",
                (user_id,),
            ) as cur:
                referral_row = await cur.fetchone()

            async with db.execute(
                "SELECT COUNT(*), COALESCE(SUM(points), 0) "
                "FROM withdrawals WHERE user_id = ? AND status = 'pending'",
                (user_id,),
            ) as cur:
                pending_withdrawal_row = await cur.fetchone()

            async with db.execute(
                "SELECT tc.task_type, COALESCE(t.title, tc.task_type) AS task_title, "
                "COUNT(*) AS completions, COALESCE(SUM(tc.points_earned), 0) AS points_earned "
                "FROM task_completions tc "
                "LEFT JOIN tasks t ON t.task_key = tc.task_type "
                "WHERE tc.user_id = ? "
                "GROUP BY tc.task_type, task_title "
                "ORDER BY completions DESC, points_earned DESC LIMIT 10",
                (user_id,),
            ) as cur:
                task_breakdown = [dict(row) for row in await cur.fetchall()]

            async with db.execute(
                "SELECT tc.id, tc.task_type, COALESCE(t.title, tc.task_type) AS task_title, "
                "tc.points_earned, tc.completed_at "
                "FROM task_completions tc "
                "LEFT JOIN tasks t ON t.task_key = tc.task_type "
                "WHERE tc.user_id = ? "
                "ORDER BY tc.completed_at DESC LIMIT 10",
                (user_id,),
            ) as cur:
                recent_tasks = [dict(row) for row in await cur.fetchall()]

            async with db.execute(
                "SELECT id, points, amount_bdt, payment_method, payment_number, status, requested_at, processed_at "
                "FROM withdrawals WHERE user_id = ? ORDER BY requested_at DESC LIMIT 10",
                (user_id,),
            ) as cur:
                recent_withdrawals = [dict(row) for row in await cur.fetchall()]

            async with db.execute(
                "SELECT r.referred_id, r.points_awarded, r.created_at, u.full_name, u.username "
                "FROM referrals r "
                "LEFT JOIN users u ON u.user_id = r.referred_id "
                "WHERE r.referrer_id = ? "
                "ORDER BY r.created_at DESC LIMIT 10",
                (user_id,),
            ) as cur:
                recent_referrals = [dict(row) for row in await cur.fetchall()]

        rank = await self.get_user_rank(user_id)

        return {
            "user": user,
            "summary": {
                "rank": rank,
                "total_tasks_completed": total_tasks_row[0] if total_tasks_row else 0,
                "task_points_earned": total_tasks_row[1] if total_tasks_row else 0,
                "tasks_today": today_tasks_row[0] if today_tasks_row else 0,
                "points_today": today_tasks_row[1] if today_tasks_row else 0,
                "referral_count": referral_row[0] if referral_row else 0,
                "referral_points": referral_row[1] if referral_row else 0,
                "pending_withdrawals": pending_withdrawal_row[0] if pending_withdrawal_row else 0,
                "pending_withdrawal_points": pending_withdrawal_row[1] if pending_withdrawal_row else 0,
            },
            "referred_by_user": referred_by_user,
            "task_breakdown": task_breakdown,
            "recent_tasks": recent_tasks,
            "recent_withdrawals": recent_withdrawals,
            "recent_referrals": recent_referrals,
        }

    async def delete_user_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET referred_by = NULL WHERE referred_by = ?", (user_id,))
            await db.execute("DELETE FROM task_completions WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM withdrawals WHERE user_id = ?", (user_id,))
            await db.execute(
                "DELETE FROM referrals WHERE referrer_id = ? OR referred_id = ?",
                (user_id, user_id),
            )
            await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            await db.commit()
            return db.total_changes > 0

    async def admin_add_points(self, user_id: int, points: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT points FROM users WHERE user_id = ?",
                (user_id,),
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    return False
                current_points = row[0]

            if points < 0 and current_points < abs(points):
                return False

            earned_delta = points if points > 0 else 0
            await db.execute(
                "UPDATE users SET points = points + ?, total_earned = total_earned + ? WHERE user_id = ?",
                (points, earned_delta, user_id),
            )
            await db.commit()
            return db.total_changes > 0
