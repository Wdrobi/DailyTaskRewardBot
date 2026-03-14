"""
অ্যাডমিন REST API — aiohttp দিয়ে তৈরি।
Bearer token দিয়ে সুরক্ষিত।
bot.py-এর সাথে asyncio.gather() এ একসাথে চলে।
"""

import json
import logging
from typing import Any

from aiohttp import web

from config import ADMIN_API_TOKEN, ADMIN_API_PORT, ADMIN_USERNAME, ADMIN_PASSWORD
from database import Database

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Auth middleware
# ──────────────────────────────────────────────
def _check_auth(request: web.Request) -> bool:
    if not ADMIN_API_TOKEN:
        return False
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {ADMIN_API_TOKEN}"


def _json(data: Any, status: int = 200) -> web.Response:
    return web.Response(
        text=json.dumps(data, default=str, ensure_ascii=False),
        status=status,
        content_type="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
    )


def _unauthorized() -> web.Response:
    return _json({"error": "Unauthorized"}, 401)


def _not_found(msg: str = "Not found") -> web.Response:
    return _json({"error": msg}, 404)


def _bad_request(msg: str) -> web.Response:
    return _json({"error": msg}, 400)


# ──────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────
async def login(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        username = body.get("username", "")
        password = body.get("password", "")
    except Exception:
        return _bad_request("Invalid JSON")
    if not ADMIN_USERNAME or not ADMIN_PASSWORD or not ADMIN_API_TOKEN:
        return _json({"error": "Admin credentials not configured on server"}, 500)
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return _json({"token": ADMIN_API_TOKEN})
    return _json({"error": "Invalid username or password"}, 401)


# ──────────────────────────────────────────────
# CORS preflight handler
# ──────────────────────────────────────────────
async def handle_options(request: web.Request) -> web.Response:
    return web.Response(
        status=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
        },
    )


# ──────────────────────────────────────────────
# Stats
# ──────────────────────────────────────────────
async def get_stats(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    stats = await db.get_stats()
    return _json(stats)


# ──────────────────────────────────────────────
# Withdrawals
# ──────────────────────────────────────────────
async def get_withdrawals(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    status = request.rel_url.query.get("status", "pending")
    limit = min(int(request.rel_url.query.get("limit", "50")), 200)
    offset = int(request.rel_url.query.get("offset", "0"))
    rows = await db.get_all_withdrawals(status=status, limit=limit, offset=offset)
    total = await db.get_withdrawals_count(status=status)
    return _json({"total": total, "rows": rows})


async def approve_withdrawal(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    wd_id = int(request.match_info["id"])
    wd = await db.get_withdrawal_by_id(wd_id)
    if not wd:
        return _not_found("Withdrawal not found")
    if wd["status"] != "pending":
        return _bad_request("Already processed")
    await db.update_withdrawal_status(wd_id, "approved", "Admin approved via web panel")
    return _json({"ok": True})


async def reject_withdrawal(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    wd_id = int(request.match_info["id"])
    wd = await db.get_withdrawal_by_id(wd_id)
    if not wd:
        return _not_found("Withdrawal not found")
    if wd["status"] != "pending":
        return _bad_request("Already processed")
    await db.restore_points_on_rejection(wd_id)
    await db.update_withdrawal_status(wd_id, "rejected", "Admin rejected via web panel")
    return _json({"ok": True})


# ──────────────────────────────────────────────
# Users
# ──────────────────────────────────────────────
async def get_users(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    limit = min(int(request.rel_url.query.get("limit", "50")), 200)
    offset = int(request.rel_url.query.get("offset", "0"))
    search = request.rel_url.query.get("search", "").strip()
    rows = await db.get_all_users(limit=limit, offset=offset, search=search)
    total = await db.get_users_count(search=search)
    return _json({"total": total, "rows": rows})


async def get_user(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    user_id = int(request.match_info["id"])
    user = await db.get_user(user_id)
    if not user:
        return _not_found("User not found")
    return _json(user)


async def ban_user(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    user_id = int(request.match_info["id"])
    await db.ban_user(user_id)
    return _json({"ok": True})


async def unban_user(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    user_id = int(request.match_info["id"])
    await db.unban_user(user_id)
    return _json({"ok": True})


async def add_points(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    user_id = int(request.match_info["id"])
    try:
        body = await request.json()
        points = int(body.get("points", 0))
    except Exception:
        return _bad_request("Invalid JSON or points value")
    if points == 0:
        return _bad_request("points cannot be 0")
    user = await db.get_user(user_id)
    if not user:
        return _not_found("User not found")
    await db.admin_add_points(user_id, points)
    return _json({"ok": True})


# ──────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────
def create_app(db: Database) -> web.Application:
    app = web.Application()
    app["db"] = db

    app.router.add_route("OPTIONS", "/{path_info:.*}", handle_options)
    app.router.add_post("/api/login", login)
    app.router.add_get("/api/stats", get_stats)
    app.router.add_get("/api/withdrawals", get_withdrawals)
    app.router.add_post("/api/withdrawals/{id}/approve", approve_withdrawal)
    app.router.add_post("/api/withdrawals/{id}/reject", reject_withdrawal)
    app.router.add_get("/api/users", get_users)
    app.router.add_get("/api/users/{id}", get_user)
    app.router.add_post("/api/users/{id}/ban", ban_user)
    app.router.add_post("/api/users/{id}/unban", unban_user)
    app.router.add_post("/api/users/{id}/add_points", add_points)

    # static admin panel
    app.router.add_static("/admin", path="webapp", name="admin_static")

    return app


async def start_admin_api(db: Database) -> None:
    if not ADMIN_API_TOKEN:
        logger.warning("ADMIN_API_TOKEN সেট নেই — অ্যাডমিন API বন্ধ থাকবে।")
        return
    app = create_app(db)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", ADMIN_API_PORT)
    await site.start()
    logger.info(f"অ্যাডমিন API চালু: http://0.0.0.0:{ADMIN_API_PORT}/admin/admin.html")
