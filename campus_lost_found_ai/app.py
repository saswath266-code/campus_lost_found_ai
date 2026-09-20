import os
import uuid
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

from database import init_db, add_item, get_items, get_item, update_status
from matching import find_matches, ai_status
from storage import save_uploaded_image

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-in-production")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "8")) * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

# Initialize the selected database at startup.
init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    return {"ai_status": ai_status()}


@app.route("/")
def index():
    lost = get_items("lost")
    found = get_items("found")
    return render_template("index.html", lost=lost, found=found)


@app.route("/report/lost", methods=["GET", "POST"])
def report_lost():
    return handle_report("lost")


@app.route("/report/found", methods=["GET", "POST"])
def report_found():
    return handle_report("found")


def handle_report(item_type):
    if request.method == "POST":
        data = request.form
        image = request.files.get("image")
        if image and image.filename and not allowed_file(image.filename):
            flash("Unsupported image type. Use PNG, JPG, JPEG or WEBP.", "error")
            return render_template("report.html", item_type=item_type)

        image_url = save_uploaded_image(image, ALLOWED_EXTENSIONS)
        add_item(
            item_type,
            data.get("name", "").strip(),
            data.get("category", "").strip(),
            data.get("description", "").strip(),
            data.get("location", "").strip(),
            data.get("event_time", "").strip(),
            image_url,
        )
        flash(f"{item_type.title()} item reported successfully. AI matching is ready.")
        return redirect(url_for("index"))
    return render_template("report.html", item_type=item_type)


@app.route("/matches/<int:item_id>")
def matches(item_id):
    item = get_item(item_id)
    if not item:
        return "Item not found", 404
    results = find_matches(item)
    return render_template("matches.html", item=item, results=results)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        expected_user = os.getenv("ADMIN_USERNAME", "admin")
        expected_password = os.getenv("ADMIN_PASSWORD", "change-me")
        if username == expected_user and password == expected_password:
            session["admin_logged_in"] = True
            return redirect(request.args.get("next") or url_for("admin"))
        flash("Invalid admin credentials.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin():
    items = get_items()
    return render_template("admin.html", items=items)


@app.route("/admin/status/<int:item_id>/<status>")
@admin_required
def status(item_id, status):
    allowed = {"under_review", "verified", "returned", "rejected", "searching"}
    if status not in allowed:
        return "Invalid status", 400
    update_status(item_id, status)
    flash("Status updated.")
    return redirect(url_for("admin"))


@app.errorhandler(413)
def too_large(_):
    flash("Image is too large. Please upload a smaller image.", "error")
    return redirect(request.referrer or url_for("index"))


@app.route("/health")
def health():
    return {"status": "ok", "ai": ai_status()}


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
