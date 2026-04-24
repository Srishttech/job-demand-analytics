import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from flask import Flask, render_template, request, redirect, url_for, flash, Response
from google.cloud import bigquery
import pandas as pd
import os
import io
import csv
import time
import glob
import base64
import tempfile

app = Flask(__name__)
app.secret_key = "jobdashboard2024"

# ── Absolute paths ────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(BASE_DIR, "static", "charts")
DATA_DIR   = os.path.join(BASE_DIR, "data")
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR,   exist_ok=True)

# ── GCP Credentials setup ─────────────────────────────────────
def setup_gcp_credentials():
    creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64")
    if creds_b64:
        creds_json = base64.b64decode(creds_b64).decode()
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        tmp.write(creds_json)
        tmp.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
        print("  GCP credentials set from environment variable")
    elif os.path.exists("bigquery_key.json"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "bigquery_key.json"
        print("  GCP credentials set from local file")
    else:
        print("  WARNING: No GCP credentials found!")

setup_gcp_credentials()

# ── BigQuery Config ───────────────────────────────────────────
BQ_PROJECT = "job-demand analysis"   # ← apna exact GCP project ID
BQ_TABLE   = f"{BQ_PROJECT}.jobs_dataset.jobs"

def get_bq_client():
    return bigquery.Client(project=BQ_PROJECT)


# ── BigQuery fetch functions ──────────────────────────────────
def fetch_all_jobs():
    client = get_bq_client()
    query  = f"SELECT * FROM `{BQ_TABLE}`"
    df     = client.query(query).to_dataframe()
    return df


def fetch_filtered_jobs(location=None, job_type=None,
                        skill=None, min_sal=None, max_sal=None):
    client = get_bq_client()
    query  = f"SELECT * FROM `{BQ_TABLE}` WHERE 1=1"

    if location and location != "all":
        query += f" AND location = '{location}'"
    if job_type and job_type != "all":
        query += f" AND job_type = '{job_type}'"
    if skill:
        query += f" AND LOWER(skills) LIKE LOWER('%{skill}%')"
    if min_sal:
        query += f" AND salary >= {float(min_sal) * 100000}"
    if max_sal:
        query += f" AND salary <= {float(max_sal) * 100000}"

    query += " ORDER BY salary DESC"
    return client.query(query).to_dataframe()


# ─────────────────────────────────────────────────────────────
# CHART GENERATION
# ─────────────────────────────────────────────────────────────
def generate_charts(df=None):
    if df is None:
        try:
            df = fetch_all_jobs()
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

    # Chart 1: Top 10 Skills
    try:
        all_skills = df['skills'].dropna().str.split(';').explode().str.strip()
        top_skills = all_skills.value_counts().head(10)
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(top_skills.index[::-1], top_skills.values[::-1],
                       color=BLUE, edgecolor='white', linewidth=0.5)
        for bar in bars:
            ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                    str(int(bar.get_width())), va='center', ha='left',
                    fontsize=10, color='#555')
        ax.set_title('Top 10 In-Demand Skills', fontsize=15,
                     fontweight='bold', pad=15, color=PRIMARY)
        ax.set_xlabel('Number of Job Listings', fontsize=11, color='#555')
        ax.spines[['top','right','left']].set_visible(False)
        ax.set_facecolor('#fafafa')
        fig.patch.set_facecolor('#ffffff')
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, 'skills.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ skills.png")
    except Exception as e:
        print(f"  ✗ skills: {e}"); plt.close()

    # Chart 2: Avg Salary by Location
    try:
        avg_sal = (df[df['salary'] > 0]
                   .groupby('location')['salary']
                   .mean()
                   .sort_values(ascending=True)
                   / 100000)

        fig, ax = plt.subplots(figsize=(8, max(3, len(avg_sal) * 0.6)))
        bars = ax.barh(avg_sal.index, avg_sal.values,
                       color=COLORS[:len(avg_sal)], edgecolor='white')
        for bar in bars:
            ax.text(bar.get_width() + 0.1,
                    bar.get_y() + bar.get_height() / 2,
                    f"{bar.get_width():.1f} LPA",
                    va='center', ha='left', fontsize=9, color='#555')
        ax.set_title('Avg Salary by Location', fontsize=13,
                     fontweight='bold', pad=12, color=PRIMARY)
        ax.set_xlabel('Avg Salary (LPA)', fontsize=10, color='#555')
        ax.spines[['top','right','left']].set_visible(False)
        ax.set_facecolor('#fafafa')
        fig.patch.set_facecolor('#ffffff')
        if len(avg_sal) == 1:
            ax.set_xlim(0, avg_sal.values[0] * 1.4)
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, 'salary_by_loc.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ salary_by_loc.png")
    except Exception as e:
        print(f"  ✗ salary_by_loc: {e}"); plt.close()

    # Chart 3: Salary Distribution
    try:
        salary_data = df[df['salary'] > 0]['salary'] / 100000
        fig, ax = plt.subplots(figsize=(10, 5))
        n, bins, patches = ax.hist(salary_data, bins=10, edgecolor='white', linewidth=0.8)
        for i, patch in enumerate(patches):
            patch.set_facecolor(plt.cm.Blues(0.4 + 0.06 * i))
        ax.set_title('Salary Distribution', fontsize=15,
                     fontweight='bold', pad=15, color=PRIMARY)
        ax.set_xlabel('Salary (LPA)', fontsize=11, color='#555')
        ax.set_ylabel('Number of Jobs', fontsize=11, color='#555')
        ax.spines[['top','right']].set_visible(False)
        ax.set_facecolor('#fafafa')
        fig.patch.set_facecolor('#ffffff')
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, 'salary.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ salary.png")
    except Exception as e:
        print(f"  ✗ salary: {e}"); plt.close()

    # Chart 4: Monthly Trend
    try:
        monthly = (df[df['posted_month'].notna() & (df['posted_month'] != '')]
                   .groupby('posted_month')['title'].count().sort_index())
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(monthly.index, monthly.values, color=PRIMARY, linewidth=2.5,
                marker='o', markersize=6, markerfacecolor=BLUE,
                markeredgecolor='white', markeredgewidth=1.5)
        ax.fill_between(monthly.index, monthly.values, alpha=0.08, color=BLUE)
        ax.set_title('Monthly Job Postings Trend', fontsize=15,
                     fontweight='bold', pad=15, color=PRIMARY)
        ax.set_xlabel('Month', fontsize=11, color='#555')
        ax.set_ylabel('Jobs Posted', fontsize=11, color='#555')
        ax.spines[['top','right']].set_visible(False)
        ax.set_facecolor('#fafafa')
        fig.patch.set_facecolor('#ffffff')
        plt.xticks(rotation=45, ha='right', fontsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, 'trend.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ trend.png")
    except Exception as e:
        print(f"  ✗ trend: {e}"); plt.close()

    # Chart 5: Top Companies
    try:
        top_co = df['company'].value_counts().head(10)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(top_co.index, top_co.values,
               color=COLORS[:len(top_co)], edgecolor='white', linewidth=0.5)
        ax.set_title('Top Companies Hiring', fontsize=15,
                     fontweight='bold', pad=15, color=PRIMARY)
        ax.set_xlabel('Company', fontsize=11, color='#555')
        ax.set_ylabel('Number of Jobs', fontsize=11, color='#555')
        ax.spines[['top','right']].set_visible(False)
        ax.set_facecolor('#fafafa')
        fig.patch.set_facecolor('#ffffff')
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
    try:
        full_df = fetch_all_jobs()

        total           = len(full_df)
        locations_count = full_df['location'].nunique()
        companies       = full_df['company'].nunique()
        avg_salary      = round(full_df[full_df['salary'] > 0]['salary'].mean() / 100000, 1)
        top_location    = full_df['location'].value_counts().index[0]

        stats = {
            "total_jobs":      total,
            "total_locations": locations_count,
            "total_companies": companies,
            "avg_salary_lpa":  avg_salary,
            "top_location":    top_location
        }

        locations = sorted(full_df['location'].dropna().unique().tolist())
        job_types = sorted(full_df['job_type'].dropna().unique().tolist())

        selected_location = request.args.get("location", "all")
        selected_job_type = request.args.get("job_type", "all")
        search_skill      = request.args.get("skill", "").strip()
        min_salary        = request.args.get("min_salary", "").strip()
        max_salary        = request.args.get("max_salary", "").strip()

        any_filter = (selected_location != "all" or
                      selected_job_type != "all" or
                      search_skill != "" or
                      min_salary != "" or
                      max_salary != "")

        if any_filter:
            filtered_df   = fetch_filtered_jobs(
                location  = selected_location,
                job_type  = selected_job_type,
                skill     = search_skill,
                min_sal   = min_salary,
                max_sal   = max_salary
            )
            filtered_jobs = filtered_df.to_dict('records')
            chart_df      = filtered_df if not filtered_df.empty else full_df
            charts_ok     = generate_charts(df=chart_df)
        else:
            filtered_jobs = []
            existing      = glob.glob(os.path.join(CHARTS_DIR, '*.png'))
            charts_ok     = True if len(existing) >= 5 else generate_charts(df=full_df)

    except Exception as e:
        print(f"BigQuery error: {e}")
        return render_template("dashboard.html",
                               error=f"Error: {e}",
                               stats=None, locations=[],
                               job_types=[], filtered_jobs=None,
                               selected_location='all',
                               selected_job_type='all',
                               search_skill='',
                               min_salary='', max_salary='',
                               charts_ok=False,
                               any_filter=False,
                               cache_bust=0)

    return render_template("dashboard.html",
                           stats=stats,
                           locations=locations,
                           job_types=job_types,
                           filtered_jobs=filtered_jobs if any_filter else None,
                           selected_location=selected_location,
                           selected_job_type=selected_job_type,
                           search_skill=search_skill,
                           min_salary=min_salary,
                           max_salary=max_salary,
                           charts_ok=charts_ok,
                           any_filter=any_filter,
                           cache_bust=int(time.time()))


@app.route("/export")
def export_csv():
    selected_location = request.args.get("location", "all")
    selected_job_type = request.args.get("job_type", "all")
    search_skill      = request.args.get("skill", "").strip()
    min_salary        = request.args.get("min_salary", "").strip()
    max_salary        = request.args.get("max_salary", "").strip()

    try:
        filtered_df = fetch_filtered_jobs(
            location = selected_location,
            job_type = selected_job_type,
            skill    = search_skill,
            min_sal  = min_salary,
            max_sal  = max_salary
        )
        jobs = filtered_df.to_dict('records')
    except Exception as e:
        return f"Error: {e}", 500

    output = io.StringIO()
    writer = csv.DictWriter(output,
                            fieldnames=['title','company','location',
                                        'skills','salary','job_type','posted_month'])
    writer.writeheader()
    for job in jobs:
        writer.writerow({k: job.get(k, '') for k in
                        ['title','company','location','skills',
                         'salary','job_type','posted_month']})
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=filtered_jobs.csv"}
    )


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or file.filename == "":
            flash("Please select a CSV file.", "error")
            return redirect(url_for("upload"))
        filepath = os.path.join(DATA_DIR, file.filename)
        file.save(filepath)
        success, message = load_csv_to_bq(filepath)
        flash(message, "success" if success else "error")
        return redirect(url_for("upload"))
    return render_template("upload.html")


@app.route("/load-sample", methods=["POST"])
def load_sample():
    success, message = load_csv_to_bq(os.path.join(DATA_DIR, "jobs.csv"))
    flash(message, "success" if success else "error")
    return redirect(url_for("upload"))


def load_csv_to_bq(filepath):
    try:
        df = pd.read_csv(filepath)
        df.columns = df.columns.str.lower().str.strip()
        if 'id' in df.columns:
            df = df.drop(columns=['id'])

        client     = get_bq_client()
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            autodetect=True,
        )
        job = client.load_table_from_dataframe(df, BQ_TABLE, job_config=job_config)
        job.result()

        # Delete old charts so fresh ones regenerate
        for f in glob.glob(os.path.join(CHARTS_DIR, '*.png')):
            os.remove(f)

        return True, f"Loaded {len(df)} rows to BigQuery!"
    except Exception as e:
        return False, f"Error: {str(e)}"


if __name__ == "__main__":
    app.run(debug=True, port=5000)