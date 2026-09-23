"""CampusFind AI Flask application."""

from __future__ import annotations

import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from database import (
    ITEM_STATUSES,
    ITEM_TYPES,
    DatabaseError,
    add_item,
    get_item,
    get_items,
    get_match_review_by_id,
    init_db,
    set_match_decision,
    update_status,
)
from matching import ai_status, find_matches
from storage import UploadValidationError, save_uploaded_image

load_dotenv()
LOGGER = logging.getLogger(__name__)

CATEGORIES = (
    "Bag",
    "Mobile Phone",
    "Laptop",
    "Earphones",
    "ID Card",
    "Wallet",
    "Keys",
    "Book",
    "Watch",
    "Other",
)


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _upload_limit_bytes() -> int:
    try:
        megabytes = int(os.getenv("MAX_UPLOAD_MB", "8"))
    except ValueError:
        megabytes = 8
    return max(1, min(megabytes, 10)) * 1024 * 1024


def _format_event_time(value: Any) -> str:
    raw = str(value or "").strip()
    for pattern in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, pattern).strftime("%d %b %Y, %I:%M %p")
        except ValueError:
            pass
    return raw or "Not specified"


def _safe_next(value: str | None) -> str | None:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return None


def _clean_text(value: str | None, maximum: int) -> str:
    return " ".join((value or "").split())[:maximum]


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    environment = os.getenv("APP_ENV", "development").strip().lower()
    configured_secret = os.getenv("SECRET_KEY", "").strip()
    if not configured_secret:
        # A random local fallback avoids the insecure prototype default. Production
        # operators are still told by health/logs to configure a persistent key.
        configured_secret = secrets.token_urlsafe(32)
        if environment == "production":
            LOGGER.error("SECRET_KEY is missing in production; sessions will not persist across restarts.")

    app.config.from_mapping(
        SECRET_KEY=configured_secret,
        MAX_CONTENT_LENGTH=_upload_limit_bytes(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=environment == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        DATABASE_READY=False,
        AUTO_INIT_DB=True,
        DEBUG=_truthy(os.getenv("FLASK_DEBUG")) and environment != "production",
    )
    if test_config:
        app.config.update(test_config)

    if app.config["AUTO_INIT_DB"]:
        try:
            init_db()
            app.config["DATABASE_READY"] = True
        except DatabaseError:
            LOGGER.exception("CampusFind database initialization failed")

    @app.template_filter("event_time")
    def event_time_filter(value: Any) -> str:
        return _format_event_time(value)

    @app.context_processor
    def inject_template_helpers() -> dict[str, Any]:
        return {
            "csrf_token": _get_csrf_token,
            "item_statuses": sorted(ITEM_STATUSES),
            "categories": CATEGORIES,
            "database_available": app.config["DATABASE_READY"],
        }

    def _get_csrf_token() -> str:
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    def _validate_csrf() -> None:
        submitted = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        if not expected or not submitted or not hmac.compare_digest(expected, submitted):
            abort(400, description="Your form expired. Refresh the page and try again.")

    def _database_required(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not app.config["DATABASE_READY"]:
                return render_template("unavailable.html"), 503
            try:
                return view(*args, **kwargs)
            except DatabaseError:
                LOGGER.exception("Database request failed")
                app.config["DATABASE_READY"] = False
                return render_template("unavailable.html"), 503

        return wrapped

    def _office_required(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("admin_logged_in"):
                return redirect(url_for("admin_login", next=request.full_path if request.query_string else request.path))
            return view(*args, **kwargs)

        return wrapped

    def _report(item_type: str):
        if request.method == "GET":
            return render_template("report.html", item_type=item_type)

        _validate_csrf()
        name = _clean_text(request.form.get("name"), 120)
        category = _clean_text(request.form.get("category"), 100)
        description = _clean_text(request.form.get("description"), 1000)
        location = _clean_text(request.form.get("location"), 160)
        event_time = _clean_text(request.form.get("event_time"), 100)
        if not name or not description or not location or not event_time:
            flash("Name, description, location, and date/time are required.", "error")
            return redirect(url_for(f"report_{item_type}"))
        if category not in CATEGORIES:
            category = "Other"
        try:
            datetime.fromisoformat(event_time)
        except ValueError:
            flash("Enter a valid date and time.", "error")
            return redirect(url_for(f"report_{item_type}"))

        try:
            image_path = save_uploaded_image(request.files.get("image"), app.config["MAX_CONTENT_LENGTH"])
            item_id = add_item(item_type, name, category, description, location, event_time, image_path)
        except UploadValidationError as error:
            flash(str(error), "error")
            return redirect(url_for(f"report_{item_type}"))
        except RuntimeError:
            flash("The image could not be stored. Your report was not submitted; please try again.", "error")
            return redirect(url_for(f"report_{item_type}"))

        flash(f"{item_type.title()} report #{item_id} submitted. The office will verify any potential match.", "success")
        return redirect(url_for("matches", item_id=item_id))

    @app.get("/")
    def index():
        query = _clean_text(request.args.get("q"), 80)
        category = request.args.get("category", "").strip()
        category = category if category in CATEGORIES else None
        lost: list[dict[str, Any]] = []
        found: list[dict[str, Any]] = []
        if app.config["DATABASE_READY"]:
            try:
                lost = get_items("lost", query=query, category=category, limit=12)
                found = get_items("found", query=query, category=category, limit=12)
            except DatabaseError:
                LOGGER.exception("Homepage database request failed")
                app.config["DATABASE_READY"] = False
        return render_template(
            "index.html",
            lost=lost,
            found=found,
            ai_status=ai_status(),
            query=query,
            selected_category=category or "",
        )

    @app.route("/report/lost", methods=["GET", "POST"])
    @_database_required
    def report_lost():
        return _report("lost")

    @app.route("/report/found", methods=["GET", "POST"])
    @_database_required
    def report_found():
        return _report("found")

    @app.get("/matches/<int:item_id>")
    @_database_required
    def matches(item_id: int):
        item = get_item(item_id)
        if not item:
            abort(404, description="Report not found.")
        try:
            results = find_matches(item)
        except DatabaseError:
            raise
        except Exception:
            LOGGER.exception("Matching failed for item %s", item_id)
            flash("Potential matches could not be prepared right now. Please try again.", "error")
            results = []
        return render_template("matches.html", item=item, results=results, ai_status=ai_status())

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "GET":
            return render_template("admin_login.html", next_url=_safe_next(request.args.get("next")))

        _validate_csrf()
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        configured_username = os.getenv("ADMIN_USERNAME", "").strip()
        configured_password = os.getenv("ADMIN_PASSWORD", "")
        if not configured_username or not configured_password:
            flash("Office login is not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD in the environment.", "error")
            return redirect(url_for("admin_login"))
        if not (
            hmac.compare_digest(username, configured_username)
            and hmac.compare_digest(password, configured_password)
        ):
            flash("Sign-in failed. Check the office credentials.", "error")
            return redirect(url_for("admin_login"))

        session.clear()
        session.permanent = True
        session["admin_logged_in"] = True
        session["admin_username"] = configured_username
        flash("Signed in to the office dashboard.", "success")
        return redirect(_safe_next(request.form.get("next")) or url_for("admin"))

    @app.post("/admin/logout")
    @_office_required
    def admin_logout():
        _validate_csrf()
        session.clear()
        flash("Signed out of the office dashboard.", "success")
        return redirect(url_for("index"))

    @app.get("/admin")
    @_office_required
    @_database_required
    def admin():
        item_type = request.args.get("type") if request.args.get("type") in ITEM_TYPES else None
        status = request.args.get("status") if request.args.get("status") in ITEM_STATUSES else None
        query = _clean_text(request.args.get("q"), 80)
        items = get_items(item_type, query=query, status=status, limit=100)
        return render_template(
            "admin.html",
            items=items,
            query=query,
            selected_type=item_type or "",
            selected_status=status or "",
        )

    @app.post("/admin/items/<int:item_id>/status")
    @_office_required
    @_database_required
    def status(item_id: int):
        _validate_csrf()
        new_status = request.form.get("status", "")
        if new_status not in ITEM_STATUSES:
            abort(400, description="Invalid item status.")
        if not update_status(item_id, new_status):
            abort(404, description="Report not found.")
        flash("Item status updated. This does not by itself prove ownership.", "success")
        return redirect(url_for("admin"))

    @app.post("/admin/reviews/<int:review_id>/decision")
    @_office_required
    @_database_required
    def match_decision(review_id: int):
        _validate_csrf()
        decision = request.form.get("decision", "")
        if decision not in {"under_review", "verified", "rejected"}:
            abort(400, description="Invalid match decision.")
        review = get_match_review_by_id(review_id)
        if not review:
            abort(404, description="Match review not found.")
        set_match_decision(review_id, decision, session.get("admin_username", "office"))
        flash("Match decision saved. A staff member must still verify ownership before return.", "success")
        return redirect(url_for("matches", item_id=review["lost_item_id"]))

    @app.get("/health")
    def health():
        status_code = 200 if app.config["DATABASE_READY"] else 503
        return {
            "status": "ok" if status_code == 200 else "degraded",
            "application": "CampusFind AI",
            "database": "ready" if status_code == 200 else "unavailable",
        }, status_code

    @app.errorhandler(413)
    def file_too_large(error):
        flash("Image is too large. Choose an image within the configured upload limit.", "error")
        return redirect(request.referrer or url_for("index"))

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", code=400, message=getattr(error, "description", "Invalid request.")), 400

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message=getattr(error, "description", "Page not found.")), 404

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        debug=app.config["DEBUG"],
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
    )
