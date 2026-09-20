# Campus Lost & Found AI Matching

A Python Flask hackathon MVP for a college lost-and-found portal.

## Features

- Report lost items
- Report found items
- Upload item photos
- Store reports in SQLite
- Compare lost and found reports
- Calculate image, text, location and time similarity
- Rank multiple possible claimants
- Admin verification workflow
- Mark items as verified, returned or rejected

## Run in VS Code

### 1. Open the project folder

Open `campus_lost_found` in VS Code.

### 2. Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

If PowerShell blocks activation, use:

```bash
venv\Scripts\activate.bat
```

### 3. Install packages

```bash
pip install -r requirements.txt
```

### 4. Run

```bash
python app.py
```

### 5. Open the website

Open:

http://127.0.0.1:5000

## Important

This is a hackathon MVP. The matching engine intentionally avoids requiring a large AI model.

For the final hackathon version, replace `basic_image_similarity()` in `matching.py` with CLIP/OpenCLIP embeddings. The database and UI can remain mostly unchanged.

The AI score is only a recommendation. The college office should verify ownership before returning an item.
