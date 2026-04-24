from google.cloud import bigquery
import pandas as pd
import mysql.connector
import os

# ── Credentials ───────────────────────────────────────
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "bigquery_key.json"

# ── Step 1: MySQL se data lo ──────────────────────────
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",   # ← apna MySQL password
    database="job_dashboard"
)
df = pd.read_sql("SELECT * FROM jobs", conn)
conn.close()
print(f"MySQL se {len(df)} rows mili")
print(df.head(2))

# ── Step 2: BigQuery config ───────────────────────────
PROJECT_ID = "job-demand analysis"   # ← apna exact GCP project ID
DATASET    = "jobs_dataset"
TABLE      = "jobs"
TABLE_ID   = f"{PROJECT_ID}.{DATASET}.{TABLE}"

client = bigquery.Client(project=PROJECT_ID)

# ── Step 3: Dataset banao ─────────────────────────────
dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET}")
dataset_ref.location = "US"
try:
    client.get_dataset(dataset_ref)
    print(f"Dataset already exists")
except:
    client.create_dataset(dataset_ref)
    print(f"Dataset '{DATASET}' created!")

# ── Step 4: Table mein data load karo ────────────────
job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_TRUNCATE",
    autodetect=True,
)

# id column drop karo — BigQuery khud banayega
if 'id' in df.columns:
    df = df.drop(columns=['id'])

job = client.load_table_from_dataframe(df, TABLE_ID, job_config=job_config)
job.result()

table = client.get_table(TABLE_ID)
print(f"\n✅ Done! {table.num_rows} rows BigQuery mein upload ho gayi!")
print(f"Table: {TABLE_ID}")