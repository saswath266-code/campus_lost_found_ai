from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from database import init_db, add_item, get_items, get_item, update_status
from matching import find_matches
import os, uuid

app = Flask(__name__)
app.secret_key = "campus-lost-found-demo-key"

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    lost = get_items("lost")
    found = get_items("found")
    return render_template("index.html", lost=lost, found=found)

@app.route("/report/lost", methods=["GET", "POST"])
def report_lost():
    if request.method == "POST":
        data = request.form
        image_path = save_image(request.files.get("image"))
        add_item(
            "lost", data.get("name"), data.get("category"), data.get("description"),
            data.get("location"), data.get("event_time"), image_path
        )
        flash("Lost item reported successfully.")
        return redirect(url_for("index"))
    return render_template("report.html", item_type="lost")

@app.route("/report/found", methods=["GET", "POST"])
def report_found():
    if request.method == "POST":
        data = request.form
        image_path = save_image(request.files.get("image"))
        add_item(
            "found", data.get("name"), data.get("category"), data.get("description"),
            data.get("location"), data.get("event_time"), image_path
        )
        flash("Found item reported successfully.")
        return redirect(url_for("index"))
    return render_template("report.html", item_type="found")

def save_image(file):
    if not file or not file.filename:
        return ""
    if not allowed_file(file.filename):
        return ""
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(filename))
    file.save(path)
    return "/" + path.replace("\\", "/")

@app.route("/matches/<int:item_id>")
def matches(item_id):
    item = get_item(item_id)
    if not item:
        return "Item not found", 404
    results = find_matches(item)
    return render_template("matches.html", item=item, results=results)

@app.route("/admin")
def admin():
    items = get_items()
    return render_template("admin.html", items=items)

@app.route("/admin/status/<int:item_id>/<status>")
def status(item_id, status):
    allowed = {"under_review", "verified", "returned", "rejected"}
    if status not in allowed:
        return "Invalid status", 400
    update_status(item_id, status)
    flash("Status updated.")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
