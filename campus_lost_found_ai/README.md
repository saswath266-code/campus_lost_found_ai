# CampusFind AI — HACM121

AI-powered campus lost-and-found web application based on the supplied Flask prototype.

## What changed

- Real image embeddings using OpenCLIP (local model; no image API is required).
- AI text embeddings using the same CLIP model.
- Combined matching score: 55% image + 25% text + 10% location + 10% time.
- SQLite for local development; PostgreSQL via `DATABASE_URL` for production.
- Local uploads for development; Cloudinary via `CLOUDINARY_URL` for production.
- Password-protected admin dashboard.
- Production WSGI configuration with Gunicorn.
- Render deployment template.
- `/health` endpoint for deployment checks.

## 1. Local setup

Python 3.12 is recommended.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `ADMIN_PASSWORD` in `.env`.

## 2. Start the application

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

The first AI matching request can download the OpenCLIP pretrained weights. Keep the machine connected to the internet during the first model load.

## 3. Test the AI

1. Submit a lost item with an image and description.
2. Submit a found item with a different image and description.
3. Open **Find potential matches**.
4. The result shows separate AI Image and AI Text similarity plus location/time context.

Do not enable `AI_FALLBACK=1` for your final hackathon demonstration; it is only a development fallback.

## 4. Production deployment

### Database

Create a PostgreSQL database and set:

```text
DATABASE_URL=postgresql://...
```

The app automatically uses PostgreSQL when `DATABASE_URL` is present.

### Images

Create a Cloudinary account and set:

```text
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
```

If this is not set, images are stored in `static/uploads`, which is suitable only for local development.

### Admin

Set strong values:

```text
ADMIN_USERNAME=collegeadmin
ADMIN_PASSWORD=<strong-password>
SECRET_KEY=<long-random-secret>
```

### Render

The included `render.yaml` contains a web service and PostgreSQL database definition. Push this folder to GitHub and create the Render service from the repository/Blueprint.

Because OpenCLIP is a PyTorch model, CPU-only hosting may be slower on first load and during matching. For a classroom/hackathon demo, use one worker so the model is loaded once per process. If production traffic grows, use a stronger instance or move inference to a dedicated model service.

## 5. Architecture

```text
Browser (any phone/laptop)
        |
      HTTPS
        v
Flask + Gunicorn
  |       |       |
  |       |       +--> OpenCLIP image/text embeddings
  |       +----------> Cloudinary images
  +------------------> PostgreSQL
        |
        v
  Ranked possible matches
```

## 6. Important limitation

AI matching is a recommendation, not proof of ownership. The college office should verify the item before returning it.
