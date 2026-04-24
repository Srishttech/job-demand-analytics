import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from flask import Flask, render_template, request, redirect, url_for, flash, Response
import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
import io
import csv
import time
import sqlalchemy

app = Flask(__name__)
app.secret_key = "jobdashboard2024"

# ── Absolute paths ────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(BASE_DIR, "static", "charts")
DATA_DIR   = os.path.join(BASE_DIR, "data")
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR,   exist_ok=True)

# ── DB CONFIG ─────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "root",    # ← change this
    "database": "job_dashboard"
}
# Render pe SQLite, local pe MySQL
import platform
USE_SQLITE = os.environ.get("USE_SQLITE", "false").lower() == "true"

# ─────────────────────────────────────────────────────────────
# HELPER: DB connection
# ─────────────────────────────────────────────────────────────
def get_connection():
    if USE_SQLITE:
        import sqlite3
        db_path = os.path.join(BASE_DIR, "jobs.db")
        return sqlite3.connect(db_path)
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"DB Error: {e}")
        return None

# ─────────────────────────────────────────────────────────────
# HELPER: SQLAlchemy engine
# ─────────────────────────────────────────────────────────────
def get_engine():
    return sqlalchemy.create_engine(
        f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
    )


# ─────────────────────────────────────────────────────────────
# CHART GENERATION — df=None means load full data from DB
# ─────────────────────────────────────────────────────────────
def generate_charts(df=None):

    # ── Step 1: agar df pass nahi hua toh DB se lo ───────────
    if df is None:
        try:
            engine = get_engine()
            df = pd.read_sql("SELECT * FROM jobs", engine)
            engine.dispose()
        except Exception as e:
            print(f"  Chart gen failed: {e}")
            return False

    if df is None or df.empty:
        print("  Chart gen failed: no data")
        return False

    print(f"  Generating charts for {len(df)} rows...")

    PRIMARY = "#1a1a1a"
    BLUE    = "#378ADD"
    COLORS  = ["#1a1a1a","#378ADD","#1D9E75","#EF9F27","#7F77DD",
               "#E24B4A","#5DCAA5","#F4A261","#A8DADC","#457B9D"]

    # ── Chart 1: Top 10 Skills ────────────────────────────────
    try:
        all_skills = df['skills'].dropna().str.split(';').explode().str.strip()
        top_skills = all_skills.value_counts().head(10)
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(top_skills.index[::-1], top_skills.values[::-1],
                       color=BLUE, edgecolor='white', linewidth=0.5)
        for bar in bars:
            ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                    str(int(bar.get_width())), va='center', ha='left', fontsize=10, color='#555')
        ax.set_title('Top 10 In-Demand Skills', fontsize=15, fontweight='bold', pad=15, color=PRIMARY)
        ax.set_xlabel('Number of Job Listings', fontsize=11, color='#555')
        ax.spines[['top','right','left']].set_visible(False)
        ax.set_facecolor('#fafafa'); fig.patch.set_facecolor('#ffffff')
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, 'skills.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ skills.png")
    except Exception as e:
        print(f"  ✗ skills: {e}"); plt.close()

    # ── Chart 2: Jobs by Location ─────────────────────────────
    try:
        loc_counts = df['location'].value_counts().head(8)
        fig, ax = plt.subplots(figsize=(8, 7))
        wedges, texts, autotexts = ax.pie(
            loc_counts.values, labels=loc_counts.index, autopct='%1.1f%%',
            colors=COLORS[:len(loc_counts)], pctdistance=0.82,
            wedgeprops=dict(width=0.55, edgecolor='white', linewidth=2))
        for t in texts: t.set_fontsize(11)
        for a in autotexts: a.set_fontsize(9); a.set_color('white'); a.set_fontweight('bold')
        ax.set_title('Jobs by Location', fontsize=15, fontweight='bold', pad=20, color=PRIMARY)
        fig.patch.set_facecolor('#ffffff')
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, 'locations.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ locations.png")
    except Exception as e:
        print(f"  ✗ locations: {e}"); plt.close()

    # ── Chart 3: Salary Distribution ─────────────────────────
    try:
        salary_data = df[df['salary'] > 0]['salary'] / 100000
        fig, ax = plt.subplots(figsize=(10, 5))
        n, bins, patches = ax.hist(salary_data, bins=10, edgecolor='white', linewidth=0.8)
        for i, patch in enumerate(patches):
            patch.set_facecolor(plt.cm.Blues(0.4 + 0.06 * i))
        ax.set_title('Salary Distribution', fontsize=15, fontweight='bold', pad=15, color=PRIMARY)
        ax.set_xlabel('Salary (LPA)', fontsize=11, color='#555')
        ax.set_ylabel('Number of Jobs', fontsize=11, color='#555')
        ax.spines[['top','right']].set_visible(False)
        ax.set_facecolor('#fafafa'); fig.patch.set_facecolor('#ffffff')
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, 'salary.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ salary.png")
    except Exception as e:
        print(f"  ✗ salary: {e}"); plt.close()

    # ── Chart 4: Monthly Trend ────────────────────────────────
    try:
        monthly = (df[df['posted_month'].notna() & (df['posted_month'] != '')]
                   .groupby('posted_month')['title'].count().sort_index())
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(monthly.index, monthly.values, color=PRIMARY, linewidth=2.5,
                marker='o', markersize=6, markerfacecolor=BLUE,
                markeredgecolor='white', markeredgewidth=1.5)
        ax.fill_between(monthly.index, monthly.values, alpha=0.08, color=BLUE)
        ax.set_title('Monthly Job Postings Trend', fontsize=15, fontweight='bold', pad=15, color=PRIMARY)
        ax.set_xlabel('Month', fontsize=11, color='#555')
        ax.set_ylabel('Jobs Posted', fontsize=11, color='#555')
        ax.spines[['top','right']].set_visible(False)
        ax.set_facecolor('#fafafa'); fig.patch.set_facecolor('#ffffff')
        plt.xticks(rotation=45, ha='right', fontsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, 'trend.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ trend.png")
    except Exception as e:
        print(f"  ✗ trend: {e}"); plt.close()

    # ── Chart 5: Top Companies ────────────────────────────────
    try:
        top_co = df['company'].value_counts().head(10)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(top_co.index, top_co.values, color=COLORS[:len(top_co)],
               edgecolor='white', linewidth=0.5)
        ax.set_title('Top Companies Hiring', fontsize=15, fontweight='bold', pad=15, color=PRIMARY)
        ax.set_xlabel('Company', fontsize=11, color='#555')
        ax.set_ylabel('Number of Jobs', fontsize=11, color='#555')
        ax.spines[['top','right']].set_visible(False)
        ax.set_facecolor('#fafafa'); fig.patch.set_facecolor('#ffffff')
        plt.xticks(rotation=30, ha='right', fontsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, 'companies.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ companies.png")
    except Exception as e:
        print(f"  ✗ companies: {e}"); plt.close()

    return True


# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    conn = get_connection()
    if not conn:
        return render_template("dashboard.html", stats=None,
                               error="DB not connected — run init_db.py first",
                               locations=[], job_types=[],
                               filtered_jobs=None,
                               selected_location='all',
                               selected_job_type='all',
                               search_skill='',
                               min_salary='', max_salary='',
                               charts_ok=False, cache_bust=0)

    cursor = conn.cursor(dictionary=True)

    # ── Summary stats ─────────────────────────────────────────
    cursor.execute("SELECT COUNT(*) as total FROM jobs")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(DISTINCT location) as locs FROM jobs")
    locations_count = cursor.fetchone()["locs"]
    cursor.execute("SELECT COUNT(DISTINCT company) as comps FROM jobs")
    companies = cursor.fetchone()["comps"]
    cursor.execute("SELECT AVG(salary) as avg_sal FROM jobs WHERE salary > 0")
    avg_row = cursor.fetchone()
    avg_salary = round(avg_row["avg_sal"] / 100000, 1) if avg_row["avg_sal"] else 0
    cursor.execute("SELECT location, COUNT(*) as cnt FROM jobs GROUP BY location ORDER BY cnt DESC LIMIT 1")
    top_loc = cursor.fetchone()

    stats = {
        "total_jobs":      total,
        "total_locations": locations_count,
        "total_companies": companies,
        "avg_salary_lpa":  avg_salary,
        "top_location":    top_loc["location"] if top_loc else "N/A"
    }

    # ── Dropdown options ──────────────────────────────────────
    cursor.execute("SELECT DISTINCT location FROM jobs ORDER BY location")
    locations = [r["location"] for r in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT job_type FROM jobs ORDER BY job_type")
    job_types = [r["job_type"] for r in cursor.fetchall()]

    # ── Filter params from URL ────────────────────────────────
    selected_location = request.args.get("location", "all")
    selected_job_type = request.args.get("job_type", "all")
    search_skill      = request.args.get("skill", "").strip()
    min_salary        = request.args.get("min_salary", "").strip()
    max_salary        = request.args.get("max_salary", "").strip()

    # ── MySQL filtered query ──────────────────────────────────
    query  = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if selected_location != "all":
        query += " AND location = %s";   params.append(selected_location)
    if selected_job_type != "all":
        query += " AND job_type = %s";   params.append(selected_job_type)
    if search_skill:
        query += " AND skills LIKE %s";  params.append(f"%{search_skill}%")
    if min_salary:
        query += " AND salary >= %s";    params.append(float(min_salary) * 100000)
    if max_salary:
        query += " AND salary <= %s";    params.append(float(max_salary) * 100000)
    query += " ORDER BY salary DESC"

    cursor.execute(query, params)
    filtered_jobs = cursor.fetchall()
    cursor.close()
    conn.close()

    # ── Pandas filtered_df for charts ─────────────────────────
    try:
        engine = get_engine()
        full_df = pd.read_sql("SELECT * FROM jobs", engine)
        engine.dispose()

        filtered_df = full_df.copy()
        if selected_location != "all":
            filtered_df = filtered_df[filtered_df['location'] == selected_location]
        if selected_job_type != "all":
            filtered_df = filtered_df[filtered_df['job_type'] == selected_job_type]
        if search_skill:
            filtered_df = filtered_df[filtered_df['skills'].str.contains(search_skill, case=False, na=False)]
        if min_salary:
            filtered_df = filtered_df[filtered_df['salary'] >= float(min_salary) * 100000]
        if max_salary:
            filtered_df = filtered_df[filtered_df['salary'] <= float(max_salary) * 100000]

        # agar filtered empty hai toh full data use karo
        chart_df  = filtered_df if not filtered_df.empty else full_df
        charts_ok = generate_charts(df=chart_df)

    except Exception as e:
        print(f"Chart error: {e}")
        charts_ok = False

    return render_template("dashboard.html",
                           stats=stats,
                           locations=locations,
                           job_types=job_types,
                           filtered_jobs=filtered_jobs,
                           selected_location=selected_location,
                           selected_job_type=selected_job_type,
                           search_skill=search_skill,
                           min_salary=min_salary,
                           max_salary=max_salary,
                           charts_ok=charts_ok,
                           cache_bust=int(time.time()))


# ─────────────────────────────────────────────────────────────
# CSV EXPORT
# ─────────────────────────────────────────────────────────────
@app.route("/export")
def export_csv():
    conn = get_connection()
    if not conn:
        return "DB Error", 500

    cursor = conn.cursor(dictionary=True)

    selected_location = request.args.get("location", "all")
    selected_job_type = request.args.get("job_type", "all")
    search_skill      = request.args.get("skill", "").strip()
    min_salary        = request.args.get("min_salary", "").strip()
    max_salary        = request.args.get("max_salary", "").strip()

    query  = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if selected_location != "all":
        query += " AND location = %s";  params.append(selected_location)
    if selected_job_type != "all":
        query += " AND job_type = %s";  params.append(selected_job_type)
    if search_skill:
        query += " AND skills LIKE %s"; params.append(f"%{search_skill}%")
    if min_salary:
        query += " AND salary >= %s";   params.append(float(min_salary) * 100000)
    if max_salary:
        query += " AND salary <= %s";   params.append(float(max_salary) * 100000)
    query += " ORDER BY salary DESC"

    cursor.execute(query, params)
    jobs = cursor.fetchall()
    cursor.close()
    conn.close()

    output = io.StringIO()
    writer = csv.DictWriter(output,
                            fieldnames=['title','company','location',
                                        'skills','salary','job_type','posted_month'])
    writer.writeheader()
    for job in jobs:
        writer.writerow({
            'title':        job['title'],
            'company':      job['company'],
            'location':     job['location'],
            'skills':       job['skills'],
            'salary':       job['salary'],
            'job_type':     job['job_type'],
            'posted_month': job['posted_month']
        })

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=filtered_jobs.csv"}
    )


# ─────────────────────────────────────────────────────────────
# UPLOAD
# ─────────────────────────────────────────────────────────────
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or file.filename == "":
            flash("Please select a CSV file.", "error")
            return redirect(url_for("upload"))
        filepath = os.path.join(DATA_DIR, file.filename)
        file.save(filepath)
        success, message = load_csv_to_db(filepath)
        flash(message, "success" if success else "error")
        return redirect(url_for("upload"))
    return render_template("upload.html")


@app.route("/load-sample", methods=["POST"])
def load_sample():
    success, message = load_csv_to_db(os.path.join(DATA_DIR, "jobs.csv"))
    flash(message, "success" if success else "error")
    return redirect(url_for("upload"))


def load_csv_to_db(filepath):
    try:
        df = pd.read_csv(filepath)
        df.columns = df.columns.str.lower().str.strip()
        conn = get_connection()
        if not conn:
            return False, "Database connection failed."
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs")
        inserted, skipped = 0, 0
        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO jobs
                        (title, skills, location, salary, company, job_type, posted_month)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(row.get("title", "Unknown")),
                    str(row.get("skills", "")),
                    str(row.get("location", "Unknown")),
                    float(row.get("salary", 0)) if pd.notna(row.get("salary")) else 0,
                    str(row.get("company", "Unknown")),
                    str(row.get("job_type", "Full-time")),
                    str(row.get("posted_month", ""))
                ))
                inserted += 1
            except Exception:
                skipped += 1
        conn.commit()
        cursor.close()
        conn.close()
        return True, f"Loaded {inserted} rows! ({skipped} skipped)"
    except Exception as e:
        return False, f"Error: {str(e)}"


if __name__ == "__main__":
    app.run(debug=True, port=5000)