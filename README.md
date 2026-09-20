# 🔎 CampusFind AI

## HACM121 — Campus Lost-and-Found with Image Matching

CampusFind AI is a smart campus lost-and-found web application developed for **HackMint 26**.

Students can report lost and found items with:

- Item name
- Category
- Description
- Location
- Date/time
- Image

The system stores these reports in a **MySQL database** and generates potential matches using AI-assisted image and text analysis, along with location and time information.

---

# 🚀 What This Project Does

The application provides two main reporting flows:

### Lost Item

A student can report:

```text
I lost my Samsung Galaxy A13
```

with its description, location, time and image.

### Found Item

Another student can report:

```text
I found a Samsung Galaxy A13
```

with its description, location, time and image.

### AI Matching

The system compares the lost and found reports and produces potential matches using multiple signals:

```text
Image similarity
      +
Text similarity
      +
Location similarity
      +
Time similarity
      ↓
Combined Match Score
```

Example:

```text
AI Image       94%
AI Text        98%
Location      100%
Time          100%
-------------------
Overall        96%
```

The result is a **potential match recommendation**. The college office should verify ownership before returning an item.

---

# 🛠️ Technologies Used

## Backend

- Python 3.12
- Flask
- MySQL 8.0

## AI

- Google Gemini API
- AI-assisted image analysis
- AI-assisted text analysis

## Frontend

- HTML
- CSS
- Jinja2 templates
- JavaScript

## Python Libraries

- Flask
- Werkzeug
- Pillow
- NumPy
- Google Gemini SDK
- python-dotenv
- MySQL connector

---

# 💻 System Requirements

Each team member needs the following installed on their computer:

```text
Python 3.12
MySQL Server 8.0
Git
VS Code
A web browser
```

---

# ⚠️ IMPORTANT: USE PYTHON 3.12

This project should be run with:

```text
Python 3.12.x
```

Do NOT create the virtual environment with Python 3.14.

Check your Python version:

```powershell
python --version
```

Expected:

```text
Python 3.12.x
```

If multiple Python versions are installed, check them with:

```powershell
py -0p
```

You should see something similar to:

```text
-V:3.14
C:\Users\USERNAME\AppData\Local\Programs\Python\Python314\python.exe

-V:3.12
C:\Users\USERNAME\AppData\Local\Programs\Python\Python312\python.exe
```

If Python 3.12 is available, use:

```powershell
py -3.12
```

---

# 📥 1. Clone the Project

Open PowerShell.

Clone the GitHub repository:

```powershell
git clone YOUR_GITHUB_REPOSITORY_URL
```

Example:

```powershell
git clone https://github.com/YOUR_USERNAME/campus_lost_found_ai.git
```

Enter the project folder:

```powershell
cd campus_lost_found_ai
```

Check that the project files are present:

```powershell
dir
```

You should see files/folders similar to:

```text
app.py
database.py
matching.py
storage.py
requirements.txt
.env.example
.gitignore
templates
static
README.md
```

---

# 🐍 2. Create the Python Virtual Environment

IMPORTANT:

Make sure you are inside the project directory.

Run:

```powershell
py -3.12 -m venv venv
```

This creates:

```text
venv/
```

inside the project.

---

# ▶️ 3. Activate the Virtual Environment

For Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

After activation, your terminal should look similar to:

```text
(venv) PS C:\...\campus_lost_found_ai>
```

The `(venv)` is important.

It means the project is using its own Python environment.

---

# 🛑 If PowerShell Blocks Activation

If you get an execution-policy error, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate again:

```powershell
.\venv\Scripts\Activate.ps1
```

---

# 📦 4. Upgrade pip

After activating the virtual environment:

```powershell
python -m pip install --upgrade pip
```

---

# 📚 5. Install Project Dependencies

Run:

```powershell
pip install -r requirements.txt
```

Wait until the installation completes.

If installation succeeds, you should return to:

```text
(venv) PS C:\...\campus_lost_found_ai>
```

---

# 🗄️ 6. Install / Verify MySQL

The application uses:

```text
MySQL Server 8.0
```

You need MySQL Server running on:

```text
localhost
Port: 3306
```

You can use:

```text
MySQL Workbench
```

or

```text
MySQL Shell
```

or the MySQL command line.

---

# 🔍 7. Check MySQL on Windows

Run:

```powershell
Get-Service MySQL*
```

If MySQL is installed and running, you should see something similar to:

```text
Status   Name
------   ----
Running  MySQL80
```

If the service exists but is stopped:

```powershell
Start-Service MySQL80
```

Then check again:

```powershell
Get-Service MySQL*
```

---

# 🔑 8. Test MySQL

If this works:

```powershell
mysql --version
```

you can use:

```powershell
mysql -u root -p
```

If Windows says:

```text
mysql : The term 'mysql' is not recognized
```

MySQL may still be installed.

On a standard MySQL Server 8.0 installation, use:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" --version
```

Then log in:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
```

Enter the MySQL root password.

---

# 🔐 9. Configure the Environment File

The project contains:

```text
.env.example
```

Create a new file named:

```text
.env
```

The `.env` file must be in the **project root**, next to `app.py`.

Your structure should look like:

```text
campus_lost_found_ai/
│
├── app.py
├── database.py
├── matching.py
├── requirements.txt
├── .env
├── .env.example
├── templates/
└── static/
```

---

# 📝 10. Configure `.env`

Open `.env` and add:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

SECRET_KEY=campus-lost-found-secret

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=campus_lost_found
MYSQL_USER=root
MYSQL_PASSWORD=YOUR_MYSQL_PASSWORD
```

Replace:

```text
YOUR_GEMINI_API_KEY
```

with your Gemini API key.

Replace:

```text
YOUR_MYSQL_PASSWORD
```

with your local MySQL root password.

---

# 🤖 11. Get a Gemini API Key

Open Google AI Studio:

https://aistudio.google.com/app/apikey

Create an API key.

Copy the key.

Put it into:

```env
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

Example:

```env
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXX
```

Do NOT post the API key in:

- GitHub
- WhatsApp groups
- Discord
- Screenshots
- README
- Source code

---

# 🔒 12. NEVER COMMIT `.env`

The `.env` file contains secrets.

The repository should already have:

```text
.env
```

inside `.gitignore`.

Check:

```powershell
git status
```

`.env` should NOT appear as a file that is going to be committed.

If `.env` appears in Git changes, STOP and do not commit it.

---

# 👥 TEAM MEMBERS

Each team member should create their own `.env`.

For example:

### Team Member 1

```env
GEMINI_API_KEY=member1_key
MYSQL_PASSWORD=member1_mysql_password
```

### Team Member 2

```env
GEMINI_API_KEY=member2_key
MYSQL_PASSWORD=member2_mysql_password
```

### Team Member 3

```env
GEMINI_API_KEY=member3_key
MYSQL_PASSWORD=member3_mysql_password
```

Do not share passwords or API keys through Git.

---

# 🏗️ 13. Initialize the Database

You do NOT need to manually create the application database.

The project initializes it automatically.

Make sure:

```text
(venv)
```

is visible in your terminal.

Then run:

```powershell
python -c "from database import init_db; init_db()"
```

Expected output:

```text
MySQL database initialized successfully.
```

The application will create:

```text
campus_lost_found
```

and the required tables.

---

# 🔍 14. Verify the Database

You can verify it using MySQL.

Login:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
```

Then:

```sql
SHOW DATABASES;
```

You should see:

```text
campus_lost_found
```

Select the database:

```sql
USE campus_lost_found;
```

Check tables:

```sql
SHOW TABLES;
```

You should see the application's required tables.

To inspect the items table:

```sql
DESCRIBE items;
```

Exit MySQL:

```sql
exit;
```

---

# ▶️ 15. Run the Flask Application

Make sure the virtual environment is active:

```text
(venv)
```

Run:

```powershell
python app.py
```

Expected output:

```text
MySQL database initialized successfully.

 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

---

# 🌐 16. Open CampusFind AI

Open your browser:

```text
http://127.0.0.1:5000
```

You should see:

```text
CampusFind AI
```

---

# 🧪 17. Test the Application

## Test A — Homepage

Open:

```text
http://127.0.0.1:5000
```

Check that the homepage loads correctly.

You should see options such as:

```text
Report Lost
Report Found
Office
```

---

# 📱 18. Test Lost Item Reporting

Click:

```text
I Lost Something
```

or:

```text
Report Lost
```

Fill in the details.

Example:

```text
Item Name:
Samsung Galaxy A13

Category:
Mobile Phone

Description:
Black Samsung Galaxy phone with a cracked screen

Location:
KPRIET Boys Hostel

Time:
20 September 2026
```

Upload an image.

Submit the form.

A successful request should appear in the Flask terminal similar to:

```text
POST /report/lost 302
```

---

# 🔎 19. Verify the Lost Item in MySQL

Login to MySQL:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
```

Then:

```sql
USE campus_lost_found;

SELECT id, type, name, category, location, status, image
FROM items;
```

You should see the lost item.

Example:

```text
+----+------+--------------------+--------------+--------------------+-----------+
| id | type | name               | category     | location           | status    |
+----+------+--------------------+--------------+--------------------+-----------+
|  1 | lost | Samsung Galaxy A13 | Mobile Phone | KPRIET Boys Hostel | searching |
+----+------+--------------------+--------------+--------------------+-----------+
```

---

# 📦 20. Test Found Item Reporting

Go back to the website.

Click:

```text
Report Found
```

Create a found-item report.

For example:

```text
Item Name:
Samsung Galaxy A13

Category:
Mobile Phone

Description:
Black Samsung Galaxy phone with cracked screen

Location:
KPRIET Boys Hostel

Time:
20 September 2026
```

Upload an image.

Submit.

---

# 🔍 21. Verify Both Items

Run:

```sql
USE campus_lost_found;

SELECT id, type, name, category, location, status, image
FROM items;
```

You should have something similar to:

```text
ID   TYPE    NAME
1    lost    Samsung Galaxy A13
2    found   Samsung Galaxy A13
```

---

# 🤖 22. Test AI Matching

Suppose the lost item has:

```text
ID = 1
```

Open:

```text
http://127.0.0.1:5000/matches/1
```

The application will show potential matching found items.

The matching page can display:

```text
AI Image
AI Text
Location
Time
Overall
```

Example:

```text
AI Image       94%
AI Text        98%
Location      100%
Time          100%
-------------------
Overall        96%
```

---

# 🧠 How Matching Works

The application considers multiple pieces of information.

```text
                    LOST ITEM
                       │
          ┌────────────┼────────────┐
          ↓            ↓            ↓
       Image         Text       Location/Time
          │            │            │
          ↓            ↓            ↓
       AI Image     AI Text     Context
       Analysis     Analysis    Similarity
          │            │            │
          └────────────┼────────────┘
                       ↓
                 Match Score
                       ↓
              Potential Match
```

The score is a recommendation.

It does NOT automatically prove that the item belongs to the person reporting it.

---

# 🖼️ 23. Uploaded Images

Uploaded images are stored locally during development under:

```text
static/uploads/
```

Example:

```text
static/uploads/
├── image1.png
├── image2.png
└── image3.jpg
```

These uploaded files should not be committed to GitHub.

The `.gitignore` contains:

```text
static/uploads/*
```

---

# 📁 24. Project Structure

```text
campus_lost_found_ai/
│
├── app.py
│
├── database.py
│
├── matching.py
│
├── storage.py
│
├── requirements.txt
│
├── .env
├── .env.example
├── .gitignore
│
├── Procfile
├── render.yaml
│
├── README.md
├── UPGRADE_NOTES.md
│
├── static/
│   ├── style.css
│   │
│   └── uploads/
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── report.html
│   ├── matches.html
│   └── admin.html
│
└── venv/
```

---

# 📄 25. Important Files

## `app.py`

Main Flask application.

Handles:

- Routes
- Lost reports
- Found reports
- Matching pages
- Admin page
- Form processing

---

## `database.py`

Handles:

- MySQL connection
- Database initialization
- Table creation
- Item insertion
- Item retrieval

---

## `matching.py`

Handles:

- Matching logic
- Image analysis
- Text analysis
- Location similarity
- Time similarity
- Combined score

---

## `storage.py`

Handles image/file storage functionality.

---

## `templates/`

Contains the HTML pages used by Flask.

---

## `static/`

Contains:

- CSS
- Uploaded images
- Other frontend static files

---

# 🔄 26. Getting New Changes from GitHub

Before starting work:

```powershell
git pull
```

If your teammate has changed `requirements.txt`, run:

```powershell
pip install -r requirements.txt
```

Then start the application:

```powershell
python app.py
```

---

# 🌿 27. Recommended Git Workflow

Do NOT directly modify the main branch when working on a feature.

Create a branch:

```powershell
git checkout -b feature-name
```

Example:

```powershell
git checkout -b improve-matching
```

Check your branch:

```powershell
git branch
```

Make your changes.

Then:

```powershell
git add .
```

Commit:

```powershell
git commit -m "Improve matching system"
```

Push:

```powershell
git push -u origin improve-matching
```

Then create a Pull Request on GitHub if your team uses Pull Requests.

---

# 📤 28. Simple Git Workflow

If the team is directly working on the same branch:

```powershell
git pull
```

Make changes.

Then:

```powershell
git add .
```

```powershell
git commit -m "Your change description"
```

```powershell
git push
```

---

# ⚠️ 29. NEVER COMMIT THESE

Never push:

```text
.env
venv/
__pycache__/
*.pyc
static/uploads/*
```

Especially:

```text
.env
```

because it contains:

```text
GEMINI_API_KEY
MYSQL_PASSWORD
```

---

# 🛑 30. Common Problem — Python 3.14

If you see:

```text
No matching distribution found
```

or packages refusing to install, check:

```powershell
python --version
```

If it shows:

```text
Python 3.14.x
```

do NOT use that environment.

Delete the environment:

```powershell
deactivate
```

Then:

```powershell
rmdir /s /q venv
```

If PowerShell doesn't accept that command, use:

```powershell
Remove-Item -Recurse -Force venv
```

Create it again using Python 3.12:

```powershell
py -3.12 -m venv venv
```

Activate:

```powershell
.\venv\Scripts\Activate.ps1
```

Then:

```powershell
pip install -r requirements.txt
```

---

# 🛑 31. Common Problem — `mysql` Not Recognized

If:

```powershell
mysql --version
```

gives:

```text
mysql : The term 'mysql' is not recognized
```

don't immediately reinstall MySQL.

Check:

```powershell
Get-Service MySQL*
```

If you see:

```text
Running  MySQL80
```

MySQL is already installed and running.

Use the full executable path:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" --version
```

Login using:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
```

---

# 🛑 32. Common Problem — MySQL Service Stopped

Check:

```powershell
Get-Service MySQL*
```

If it says:

```text
Stopped
```

run:

```powershell
Start-Service MySQL80
```

Then:

```powershell
Get-Service MySQL*
```

It should show:

```text
Running
```

---

# 🛑 33. Common Problem — Database Connection Error

If the application cannot connect to MySQL:

### Check MySQL:

```powershell
Get-Service MySQL*
```

### Check `.env`:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=campus_lost_found
MYSQL_USER=root
MYSQL_PASSWORD=YOUR_MYSQL_PASSWORD
```

### Reinitialize:

```powershell
python -c "from database import init_db; init_db()"
```

Expected:

```text
MySQL database initialized successfully.
```

---

# 🛑 34. Common Problem — Gemini API Error

Check that `.env` contains:

```env
GEMINI_API_KEY=YOUR_API_KEY
```

Make sure:

- The API key is valid.
- The key has not been revoked.
- There are no accidental spaces.
- `.env` is in the project root.
- You restarted Flask after changing `.env`.

Restart:

```powershell
Ctrl + C
```

Then:

```powershell
python app.py
```

---

# 🛑 35. Common Problem — `.env` Not Loading

The `.env` file must be here:

```text
campus_lost_found_ai/
    app.py
    database.py
    matching.py
    .env
```

NOT:

```text
campus_lost_found_ai/
    venv/
        .env
```

and NOT:

```text
campus_lost_found_ai/
    templates/
        .env
```

---

# 🛑 36. Common Problem — Port 5000 Already in Use

If Flask says:

```text
Address already in use
```

another Flask process may already be running.

Stop the existing Flask terminal with:

```text
Ctrl + C
```

Then run:

```powershell
python app.py
```

---

# 🛑 37. Common Problem — Flask Shows `500`

If the browser displays:

```text
Internal Server Error
```

look at the Flask terminal.

The terminal contains the actual traceback.

Copy the **last part of the traceback** when asking the team for help.

Do not randomly change multiple files.

---

# 🧪 38. Recommended Testing Order

When setting up the project on a new computer, test in this exact order:

```text
1. Python
   ↓
2. Virtual environment
   ↓
3. Dependencies
   ↓
4. MySQL
   ↓
5. .env
   ↓
6. Database initialization
   ↓
7. Flask
   ↓
8. Homepage
   ↓
9. Lost report
   ↓
10. Found report
   ↓
11. MySQL records
   ↓
12. AI matching
```

If something fails, identify which step failed before changing anything else.

---

# 🌐 39. Local Development vs Public Deployment

When running:

```text
http://127.0.0.1:5000
```

the application is running only on the developer's computer.

Other students cannot access that URL from their own devices.

For a public deployment, the architecture will be:

```text
                    Internet
                       │
                       ↓
              Public CampusFind URL
                       │
                       ↓
                    Flask
                  /    |    \
                 /     |     \
                ↓      ↓      ↓
             MySQL   Gemini  Storage
                │
                ↓
          Lost/Found Data
```

A production deployment requires:

- Public server/cloud hosting
- Production WSGI server
- Production database
- Secure environment variables
- Persistent image storage

---

# 🔐 40. Security Rules for the Team

Never hard-code:

```text
Gemini API key
MySQL password
Secret keys
```

Never write:

```python
GEMINI_API_KEY = "AIza..."
```

inside Python files.

Use:

```env
GEMINI_API_KEY=...
```

inside `.env`.

Never commit `.env`.

---

# 👥 41. Team Setup

Every team member should have:

```text
Their own Git clone
Their own Python venv
Their own .env
Their own Gemini API key
Their own local MySQL installation
```

The source code is shared through GitHub.

The secrets are NOT shared through GitHub.

---

# 🧑‍💻 42. Quick Setup for a New Team Member

If Python 3.12 and MySQL are already installed:

```powershell
git clone YOUR_GITHUB_REPOSITORY_URL
cd campus_lost_found_ai

py -3.12 -m venv venv

.\venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

pip install -r requirements.txt
```

Create:

```text
.env
```

Add:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

SECRET_KEY=campus-lost-found-secret

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=campus_lost_found
MYSQL_USER=root
MYSQL_PASSWORD=YOUR_MYSQL_PASSWORD
```

Start MySQL.

Then:

```powershell
python -c "from database import init_db; init_db()"
```

Then:

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

Done. 🎉

---

# 📌 43. Daily Development Workflow

Every time you start working:

```powershell
cd campus_lost_found_ai
```

Activate environment:

```powershell
.\venv\Scripts\Activate.ps1
```

Get latest changes:

```powershell
git pull
```

If dependencies changed:

```powershell
pip install -r requirements.txt
```

Start the server:

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

---

# 🏆 44. HackMint 26

## Problem Statement

```text
HACM121
Campus Lost-and-Found with Image Matching
```

## Project

```text
CampusFind AI
```

## Objective

Build a campus-focused lost-and-found system that allows students to report lost and found objects and automatically identify potential matches using image and textual information.

---

# 🎯 45. Project Flow

```text
             STUDENT
                │
        ┌───────┴────────┐
        ↓                ↓
   REPORT LOST      REPORT FOUND
        │                │
        └───────┬────────┘
                ↓
              MySQL
                │
                ↓
          Matching Engine
                │
       ┌────────┼────────┐
       ↓        ↓        ↓
     Image    Text   Location/Time
       │        │        │
       └────────┼────────┘
                ↓
          Match Score
                │
                ↓
       Potential Matches
                │
                ↓
          Office Review
                │
                ↓
         Item Verification
```

---

# 👨‍💻 Team Members

### Member 1

Name:

```text
____________________________
```

GitHub:

```text
____________________________
```

---

### Member 2

Name:

```text
____________________________
```

GitHub:

```text
____________________________
```

---

### Member 3

Name:

```text
____________________________
```

GitHub:

```text
____________________________
```

---

# 📞 Team Rule

If something doesn't work:

### 1. Check the terminal.

### 2. Read the last error.

### 3. Check Python:

```powershell
python --version
```

### 4. Check virtual environment:

```text
(venv)
```

### 5. Check MySQL:

```powershell
Get-Service MySQL*
```

### 6. Check `.env`.

### 7. Check Gemini API key.

### 8. Only then modify code.

---

# ✅ Final Setup Checklist

Before saying the project works, verify:

```text
[ ] Python 3.12 installed
[ ] Git installed
[ ] MySQL 8.0 installed
[ ] MySQL service running
[ ] Repository cloned
[ ] Python venv created
[ ] venv activated
[ ] pip upgraded
[ ] requirements installed
[ ] .env created
[ ] Gemini API key added
[ ] MySQL password added
[ ] Database initialized
[ ] Flask starts
[ ] Homepage loads
[ ] Lost report works
[ ] Found report works
[ ] Images upload correctly
[ ] MySQL records are created
[ ] AI matching page works
```

---

# 🎉 CampusFind AI

**HackMint 26 — HACM121**

> Report it. Find it. Let AI connect the pieces.

```text
CampusFind AI
Smart Campus Lost-and-Found
```