"""
অ্যাডমিন REST API — aiohttp দিয়ে তৈরি।
Bearer token দিয়ে সুরক্ষিত।
bot.py-এর সাথে asyncio.gather() এ একসাথে চলে।
"""

import json
import logging
import re
import sqlite3
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


def _parse_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_task_payload(body: dict[str, Any]) -> dict[str, Any]:
    task_key = re.sub(r"[^a-z0-9_]+", "_", str(body.get("task_key", "")).strip().lower()).strip("_")
    title = str(body.get("title", "")).strip()
    description = str(body.get("description", "")).strip()
    button_text = str(body.get("button_text", "Open")).strip() or "Open"
    task_kind = str(body.get("task_kind", "link")).strip().lower()
    target_url = str(body.get("target_url", "")).strip()

    try:
        reward_points = int(body.get("reward_points", 0))
        daily_limit = int(body.get("daily_limit", 1))
        cooldown_seconds = int(body.get("cooldown_seconds", 0))
        verify_seconds = int(body.get("verify_seconds", 0))
        sort_order = int(body.get("sort_order", 100))
    except (TypeError, ValueError):
        raise ValueError("Task numeric fields are invalid")

    if not task_key:
        raise ValueError("task_key is required")
    if not title:
        raise ValueError("title is required")
    if task_kind not in {"link", "instant"}:
        raise ValueError("task_kind must be 'link' or 'instant'")
    if reward_points <= 0:
        raise ValueError("reward_points must be greater than 0")
    if daily_limit < 1:
        raise ValueError("daily_limit must be at least 1")
    if cooldown_seconds < 0 or verify_seconds < 0 or sort_order < 0:
        raise ValueError("cooldown_seconds, verify_seconds and sort_order cannot be negative")
    if task_kind == "link" and not target_url:
        raise ValueError("target_url is required for link tasks")

    return {
        "task_key": task_key,
        "title": title,
        "description": description,
        "button_text": button_text,
        "task_kind": task_kind,
        "target_url": target_url,
        "reward_points": reward_points,
        "daily_limit": daily_limit,
        "cooldown_seconds": cooldown_seconds,
        "verify_seconds": verify_seconds,
        "is_active": 1 if _parse_bool(body.get("is_active", True), True) else 0,
        "sort_order": sort_order,
    }


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


async def get_user_details(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    user_id = int(request.match_info["id"])
    details = await db.get_user_admin_details(user_id)
    if not details:
        return _not_found("User not found")
    return _json(details)


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


async def delete_user(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    user_id = int(request.match_info["id"])
    user = await db.get_user(user_id)
    if not user:
        return _not_found("User not found")
    await db.delete_user_admin(user_id)
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
    changed = await db.admin_add_points(user_id, points)
    if not changed:
        return _bad_request("Insufficient user balance for deduction")
    return _json({"ok": True})


# ──────────────────────────────────────────────
# Tasks
# ──────────────────────────────────────────────
async def get_tasks(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    include_inactive = _parse_bool(request.rel_url.query.get("include_inactive", "1"), True)
    rows = await db.get_all_tasks(include_inactive=include_inactive)
    return _json({"rows": rows})


async def create_task(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    try:
        body = await request.json()
        task_data = _parse_task_payload(body)
        task_id = await db.create_task_admin(task_data)
    except ValueError as exc:
        return _bad_request(str(exc))
    except sqlite3.IntegrityError:
        return _json({"error": "task_key already exists"}, 409)
    return _json({"ok": True, "id": task_id}, 201)


async def update_task(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    task_id = int(request.match_info["id"])
    existing = await db.get_task_admin_by_id(task_id)
    if not existing:
        return _not_found("Task not found")
    try:
        body = await request.json()
        task_data = _parse_task_payload(body)
        await db.update_task_admin(task_id, task_data)
    except ValueError as exc:
        return _bad_request(str(exc))
    except sqlite3.IntegrityError:
        return _json({"error": "task_key already exists"}, 409)
    return _json({"ok": True})


async def toggle_task(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    task_id = int(request.match_info["id"])
    task = await db.get_task_admin_by_id(task_id)
    if not task:
        return _not_found("Task not found")
    await db.set_task_active_admin(task_id, not bool(task["is_active"]))
    return _json({"ok": True, "is_active": 0 if task["is_active"] else 1})


async def delete_task(request: web.Request) -> web.Response:
    if not _check_auth(request):
        return _unauthorized()
    db: Database = request.app["db"]
    task_id = int(request.match_info["id"])
    task = await db.get_task_admin_by_id(task_id)
    if not task:
        return _not_found("Task not found")
    await db.delete_task_admin(task_id)
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
    app.router.add_get("/api/users/{id}/details", get_user_details)
    app.router.add_post("/api/users/{id}/ban", ban_user)
    app.router.add_post("/api/users/{id}/unban", unban_user)
    app.router.add_delete("/api/users/{id}", delete_user)
    app.router.add_post("/api/users/{id}/add_points", add_points)
    app.router.add_get("/api/tasks", get_tasks)
    app.router.add_post("/api/tasks", create_task)
    app.router.add_put("/api/tasks/{id}", update_task)
    app.router.add_post("/api/tasks/{id}/toggle", toggle_task)
    app.router.add_delete("/api/tasks/{id}", delete_task)

    # static admin panel — serve webapp folder at root so /admin/index.html works
    app.router.add_static("/", path="webapp", name="admin_static", show_index=True)

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
    logger.info(f"অ্যাডমিন API চালু: http://0.0.0.0:{ADMIN_API_PORT}/admin/")
