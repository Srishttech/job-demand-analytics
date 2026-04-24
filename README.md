# Job Demand Analytics Dashboard

A Flask web application that analyses job market data — skill demand, salary trends, location insights, and company hiring patterns — from any uploaded CSV dataset.

**Built with:** Python · Flask · MySQL · Pandas · Matplotlib · HTML/CSS

---

## Project Structure

```
job_dashboard/
├── app.py               ← Main Flask application
├── init_db.py           ← One-click DB setup + CSV loader
├── setup_db.sql         ← Raw SQL if you prefer MySQL Workbench
├── requirements.txt     ← Python dependencies
├── data/
│   └── jobs.csv         ← Sample dataset (35 jobs)
├── static/
│   ├── style.css        ← Stylesheet
│   └── charts/          ← Matplotlib charts saved here (Day 2+)
└── templates/
    ├── home.html
    ├── dashboard.html
    └── upload.html
```

---

## Day 1 Setup — Step by Step

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Set your MySQL password
Open `init_db.py` and change line 18:
```python
MYSQL_PASSWORD = "your_password"   # ← put your actual MySQL password
```
Do the same in `app.py` line 14.

### Step 3 — Run DB setup (creates DB + table + loads sample data)
```bash
python init_db.py
```
You should see:
```
[1/3] Creating database...   Database 'job_dashboard' ready.
[2/3] Creating table...      Table 'jobs' ready.
[3/3] Loading CSV data...    Inserted 35 rows successfully!
All done! Run python app.py to start the server.
```

### Step 4 — Start Flask server
```bash
python app.py
```

### Step 5 — Open browser
```
http://localhost:5000
```

---

## CSV Format (for uploading your own data)

| Column | Required | Example |
|--------|----------|---------|
| title | Yes | Data Scientist |
| skills | Yes | Python;SQL;ML (semicolon separated) |
| location | Yes | Bangalore |
| salary | No | 800000 (in rupees) |
| company | No | TCS |
| job_type | No | Full-time |
| posted_month | No | 2024-01 |

---

## Progress Tracker

- [x] Day 1 — Setup, DB, CSV loading, basic routes
- [ ] Day 2 — Matplotlib charts (skills, salary, location)
- [ ] Day 3 — Flask routes + templates for charts
- [ ] Day 4 — Filters + search + more charts
- [ ] Day 5 — UI polish + stat cards
- [ ] Day 6 — Deploy on Render.com
- [ ] Day 7 — Resume update + GitHub README + LinkedIn post
