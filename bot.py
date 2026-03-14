import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.utils.token import TokenValidationError, validate_token

from config import BOT_TOKEN
from database import Database
from handlers import start, tasks, wallet, admin, common
from middlewares.throttle import ThrottlingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN পাওয়া যায়নি! .env ফাইলটি চেক করুন।")
        sys.exit(1)

    try:
        validate_token(BOT_TOKEN)
    except TokenValidationError:
        logger.critical(
            "BOT_TOKEN invalid. BotFather থেকে সঠিক token নিয়ে .env আপডেট করুন।"
        )
        sys.exit(1)

    # ডেটাবেস প্রস্তুত করুন
    db = Database()
    await db.init()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # dependency injection — হ্যান্ডলারে `db: Database` প্যারামিটার হিসেবে পাওয়া যাবে
    dp["db"] = db

    # মিডলওয়্যার রেজিস্টার করুন
    dp.message.middleware(ThrottlingMiddleware())

    # রাউটার যোগ করুন (ক্রম গুরুত্বপূর্ণ — admin আগে যাতে /admin কমান্ড আটকায়)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(tasks.router)
    dp.include_router(wallet.router)
    dp.include_router(common.router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="বট শুরু করুন"),
            BotCommand(command="menu", description="মেইন মেনু দেখুন"),
            BotCommand(command="cancel", description="চলমান কাজ বাতিল করুন"),
            BotCommand(command="admin", description="অ্যাডমিন প্যানেল"),
        ]
    )

    logger.info("বট চালু হচ্ছে...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("বট বন্ধ হয়েছে।")


if __name__ == "__main__":
    asyncio.run(main())
