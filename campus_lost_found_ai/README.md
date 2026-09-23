# CampusFind AI

CampusFind AI is a campus lost-and-found application for HackMint 26 (HACM121). Students can report lost or found objects, while the campus office reviews potential pairs. Gemini can compare two report photos and descriptions, with location and reported time used as supporting context.

The application is deliberately evidence-led: a potential match is never an ownership decision. An authorized office member must inspect the object and verify a claimant before updating an item to `returned`.

## Features

- Lost and found reports with optional, validated PNG/JPG/JPEG/WEBP photos.
- Parameterized MySQL persistence and safe schema initialization.
- Gemini multimodal pair review for category, visible appearance, color, shape, brand/model, distinctive marks, descriptions, location, and time.
- Schema-constrained Gemini JSON, validation of model output, cached pair evidence, and graceful manual screening when a key, image, or API response is unavailable.
- Search and category filters for public reports; protected office dashboard with report status and pair-decision actions.
- Local uploads for development and optional Cloudinary storage for deployments.
- CSRF protection on state-changing forms, POST-only office changes, secure filename/path handling, and production-safe debug/session settings.

## Prerequisites

- Python 3.12 (recommended)
- MySQL 8.0+ running locally or a reachable managed MySQL database
- A Google Gemini API key for photo-based visual evidence (the app still runs in context-screening mode without one)
- Optional: a Cloudinary account for persistent deployed uploads

## Local setup

From the project directory:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation for your user, run this once in that terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Configure MySQL

Install MySQL Community Server, start its service, then edit `.env`. At minimum set a valid MySQL account:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=campus_lost_found
MYSQL_USER=root
MYSQL_PASSWORD=your-local-mysql-password
```

`init_db()` creates `MYSQL_DATABASE` if the supplied MySQL account has permission. If your account cannot create databases, create it once in MySQL and grant that account access:

```sql
CREATE DATABASE campus_lost_found CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON campus_lost_found.* TO 'your_user'@'%';
FLUSH PRIVILEGES;
```

Initialize the schema explicitly (the web app also performs this safely at startup):

```powershell
python scripts/init_db.py
```

The existing `items` table is retained. A small `match_reviews` table is added to retain Gemini evidence and office pair decisions.

### Configure environment variables

Copy the keys from `.env.example`; never commit `.env`.

| Variable | Required | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | Yes for persistent sessions | Long random Flask session secret. |
| `MYSQL_*` | Yes | MySQL connection details. |
| `GEMINI_API_KEY` | Required for visual AI | Key from Google AI Studio / Gemini API. |
| `GEMINI_MODEL` | No | Defaults to `gemini-2.5-flash`. |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Yes for office sign-in | Credentials for `/admin`; use unique production values. |
| `MAX_UPLOAD_MB` | No | Image limit, clamped to 1-10 MB; defaults to 8. |
| `MAX_GEMINI_CANDIDATES` | No | Photo pairs analyzed per matches page, 1-10; defaults to 5. |
| `CLOUDINARY_URL` | Recommended in production | Persistent image storage connection string. |
| `CLOUDINARY_ALLOWED_HOSTS` | No | Exact trusted stored-image hostnames; default `res.cloudinary.com`. |

To create a secure local secret, run:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Get the Gemini key from [Google AI Studio](https://aistudio.google.com/app/apikey), then set only this placeholder in `.env`:

```env
GEMINI_API_KEY=your-key-here
```

Do not paste any real key into source code, issue trackers, screenshots, or Git commits.

### Optional Cloudinary setup

Local uploads are written to `static/uploads/`, which is suitable only for development. For a public deployment, create an unsigned server-side Cloudinary credential in the Cloudinary console and set its supplied value:

```env
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
CLOUDINARY_ALLOWED_HOSTS=res.cloudinary.com
```

The server verifies an uploaded image before it is sent to Cloudinary. The source project ignores local uploads except `static/uploads/.gitkeep`.

## Run locally

```powershell
python app.py
```

Open <http://127.0.0.1:5000>. `FLASK_DEBUG` defaults to `0`; leave it disabled for demos and production. The `/health` route returns `200` when the MySQL initialization succeeded and `503` when it did not.

## Matching behavior

1. The app retrieves opposite-type reports that are not already returned.
2. It calculates transparent category, report-term, location, and time proximity signals.
3. For the most context-compatible pairs that both have photos, Gemini receives the two images and report metadata. Its structured response lists visual and distinctive evidence, missing evidence, compatibility, and a cautious lead category.
4. The visible **evidence confidence** is calculated from Gemini visual evidence (40%) plus description (25%), category (15%), location (10%), and time (10%). It is a triage value, not a probability of ownership.
5. Completed evidence is fingerprinted and stored in `match_reviews`; unchanged pairs reuse it so repeated page views do not make needless Gemini calls.
6. Missing keys, photos, API failures, blocked/invalid model outputs, or malformed JSON switch the relevant pair to clearly-labelled manual context screening. No visual-AI score is invented.

Office staff can mark a pair under review, verified as a lead, or rejected. Those pair decisions do not automatically return an item; set the separate item status only after real-world checks.

## Testing

Run the built-in unit and route checks after installing dependencies:

```powershell
python -m unittest discover -s tests -v
```

The suite covers template routes, reporting validation, invalid uploads, missing Gemini configuration, API failure fallback, malformed Gemini response fallback, missing image fallback, and cached evidence behavior. For a MySQL CRUD smoke test, use a disposable database name:

```powershell
$env:MYSQL_DATABASE = "campus_find_smoke_test"
python -c "from database import init_db, add_item, get_item, update_status; init_db(); i=add_item('lost','Test keys','Keys','Blue tag','Library','2026-09-23T10:00',''); assert get_item(i)['name']=='Test keys'; assert update_status(i,'under_review'); print('MySQL CRUD smoke test passed')"
Remove-Item Env:MYSQL_DATABASE
```

Use a database created only for this smoke test and remove it through your normal MySQL administration process when finished.

## Deployment on Render

`render.yaml` installs `requirements.txt`, starts Gunicorn, and exposes `/health`. Render does not provide MySQL as a `render.yaml` database resource, so provision managed MySQL separately (or use an existing campus MySQL service), then set these Render environment variables manually:

```text
MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD
GEMINI_API_KEY
ADMIN_USERNAME, ADMIN_PASSWORD
CLOUDINARY_URL
```

`SECRET_KEY` is generated by Render; `APP_ENV=production` and `FLASK_DEBUG=0` are configured. Set `CLOUDINARY_URL` before accepting production uploads because the Render filesystem is ephemeral. Restrict your managed MySQL network/firewall access to the Render service where your provider supports it.

For a platform using a Procfile, the project uses:

```text
web: gunicorn --workers 1 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT app:app
```

## Project structure

```text
campus_lost_found_ai/
├── app.py                 # Flask routes, sessions, CSRF, reporting, office workflow
├── database.py            # Parameterized MySQL access and schema initialization
├── matching.py            # Gemini pair evidence and transparent context screening
├── storage.py             # Image validation and local/Cloudinary storage
├── templates/             # Responsive public and office pages
├── static/style.css       # CampusFind visual system
├── scripts/init_db.py     # Standalone database initialization
├── tests/                 # Unit and route checks
├── .env.example           # Safe environment variable template
├── Procfile
└── render.yaml
```

## Troubleshooting

**`CampusFind needs its database`**

- Confirm MySQL is running and that the `MYSQL_*` values in `.env` are correct.
- Run `python scripts/init_db.py` from the activated environment.
- Ensure the database user can create/use `MYSQL_DATABASE`.

**Gemini is shown as context screening only**

- Add a valid `GEMINI_API_KEY` to `.env`, then restart the app.
- Confirm `google-genai` is installed from `requirements.txt`.
- A pair also needs two readable item photos for visual analysis.

**A pair says Gemini evidence was unusable**

- The app intentionally rejects malformed or incomplete model responses instead of displaying an invented score. Refresh later or inspect the reports manually.

**Cloudinary upload fails**

- Check `CLOUDINARY_URL` for accidental quotes/spaces and confirm it is a server credential.
- Leave `CLOUDINARY_URL` blank to use local storage while developing.

**Port is already in use**

- Stop the other development server or run with another `PORT`, for example `$env:PORT=5001; python app.py`.

## Team workflow and security

Each teammate needs their own clone, virtual environment, `.env`, Gemini key, and MySQL access. Commit source code, `.env.example`, and docs; never commit `venv/`, `.env`, real uploads, API keys, passwords, or generated archives. Before a demo, submit one lost report and one found report with representative photos, inspect the evidence screen as the office user, and verify the human-review language is clear.
