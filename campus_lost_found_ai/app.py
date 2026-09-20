import os
import uuid

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

from database import (
    init_db,
    add_item,
    get_items,
    get_item,
    update_status
)

from matching import find_matches


# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------
# FLASK APP
# ---------------------------------------------------------

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key"
)


# ---------------------------------------------------------
# UPLOAD CONFIGURATION
# ---------------------------------------------------------

UPLOAD_FOLDER = os.path.join(
    "static",
    "uploads"
)

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------

init_db()


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower() in ALLOWED_EXTENSIONS
    )


def save_image(file):

    if not file:
        return ""


    if not file.filename:
        return ""


    if not allowed_file(file.filename):

        return ""


    original_name = secure_filename(
        file.filename
    )

    extension = original_name.rsplit(
        ".",
        1
    )[1].lower()


    filename = (
        f"{uuid.uuid4().hex}.{extension}"
    )


    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )


    file.save(filepath)


    # Store web-accessible path in MySQL
    return "/" + filepath.replace(
        "\\",
        "/"
    )


# ---------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------

@app.route("/")
def index():

    lost = get_items("lost")

    found = get_items("found")

    # Gemini API status for the homepage
    gemini_key = os.getenv("GEMINI_API_KEY")

    ai_status = {
        "enabled": bool(gemini_key),
        "provider": "Gemini API"
    }

    return render_template(
        "index.html",
        lost=lost,
        found=found,
        ai_status=ai_status
    )


# ---------------------------------------------------------
# REPORT LOST ITEM
# ---------------------------------------------------------

@app.route(
    "/report/lost",
    methods=["GET", "POST"]
)
def report_lost():

    if request.method == "POST":

        data = request.form

        image_file = request.files.get(
            "image"
        )

        image_path = save_image(
            image_file
        )


        # Validate required fields

        name = data.get(
            "name",
            ""
        ).strip()


        if not name:

            flash(
                "Item name is required."
            )

            return redirect(
                url_for("report_lost")
            )


        add_item(
            "lost",
            name,
            data.get("category", "").strip(),
            data.get("description", "").strip(),
            data.get("location", "").strip(),
            data.get("event_time", "").strip(),
            image_path
        )


        flash(
            "Lost item reported successfully."
        )


        return redirect(
            url_for("index")
        )


    return render_template(
        "report.html",
        item_type="lost"
    )


# ---------------------------------------------------------
# REPORT FOUND ITEM
# ---------------------------------------------------------

@app.route(
    "/report/found",
    methods=["GET", "POST"]
)
def report_found():

    if request.method == "POST":

        data = request.form

        image_file = request.files.get(
            "image"
        )

        image_path = save_image(
            image_file
        )


        # Validate required fields

        name = data.get(
            "name",
            ""
        ).strip()


        if not name:

            flash(
                "Item name is required."
            )

            return redirect(
                url_for("report_found")
            )


        add_item(
            "found",
            name,
            data.get("category", "").strip(),
            data.get("description", "").strip(),
            data.get("location", "").strip(),
            data.get("event_time", "").strip(),
            image_path
        )


        flash(
            "Found item reported successfully."
        )


        return redirect(
            url_for("index")
        )


    return render_template(
        "report.html",
        item_type="found"
    )


# ---------------------------------------------------------
# MATCHING PAGE
# ---------------------------------------------------------

@app.route(
    "/matches/<int:item_id>"
)
def matches(item_id):

    item = get_item(
        item_id
    )


    if not item:

        return (
            "Item not found",
            404
        )


    try:

        results = find_matches(
            item
        )

    except Exception as error:

        print(
            "Matching error:",
            error
        )

        flash(
            "AI matching failed. "
            "Please check your Gemini API configuration."
        )

        results = []


    return render_template(
    "matches.html",
    item=item,
    results=results,
    ai_status={
        "enabled": bool(os.getenv("GEMINI_API_KEY")),
        "provider": "Gemini API"
    }
)


# ---------------------------------------------------------
# ADMIN PAGE
# ---------------------------------------------------------

@app.route("/admin")
def admin():

    items = get_items()

    return render_template(
        "admin.html",
        items=items
    )


# ---------------------------------------------------------
# UPDATE ITEM STATUS
# ---------------------------------------------------------

@app.route(
    "/admin/status/<int:item_id>/<status>"
)
def status(
    item_id,
    status
):

    allowed = {
        "under_review",
        "verified",
        "returned",
        "rejected"
    }


    if status not in allowed:

        return (
            "Invalid status",
            400
        )


    update_status(
        item_id,
        status
    )


    flash(
        "Status updated."
    )


    return redirect(
        url_for("admin")
    )


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.route("/health")
def health():

    return {
        "status": "ok",
        "application": "Campus Lost and Found"
    }


# ---------------------------------------------------------
# ERROR: FILE TOO LARGE
# ---------------------------------------------------------

@app.errorhandler(413)
def file_too_large(error):

    flash(
        "Image is too large. "
        "Maximum size is 10 MB."
    )

    return redirect(
        url_for("index")
    )


# ---------------------------------------------------------
# RUN APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )