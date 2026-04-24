"""
Run this ONCE on Day 1 to:
  1. Create the database and table
  2. Load the sample jobs.csv into MySQL

Usage:
    python init_db.py
"""

import mysql.connector
from mysql.connector import Error
import pandas as pd
import os

# ── CHANGE THESE ──────────────────────────────────────────────
MYSQL_USER     = "root"
MYSQL_PASSWORD = "root"   # ← put your MySQL password here
MYSQL_HOST     = "localhost"
DB_NAME        = "job_dashboard"
CSV_PATH       = "data/jobs.csv"
# ─────────────────────────────────────────────────────────────


def create_database(cursor):
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.execute(f"USE {DB_NAME}")
    print(f"  Database '{DB_NAME}' ready.")


def create_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            title        VARCHAR(200)  NOT NULL,
            skills       TEXT,
            location     VARCHAR(100),
            salary       DECIMAL(12,2) DEFAULT 0,
            company      VARCHAR(200),
            job_type     VARCHAR(50)   DEFAULT 'Full-time',
            posted_month VARCHAR(20),
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  Table 'jobs' ready.")


def load_csv(cursor, conn):
    if not os.path.exists(CSV_PATH):
        print(f"  CSV not found at {CSV_PATH}. Skipping load.")
        return

    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.lower().str.strip()

    print(f"  CSV loaded: {len(df)} rows")
    print(f"  Columns found: {list(df.columns)}")

    cursor.execute("DELETE FROM jobs")   # fresh load each time
    inserted = 0

    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO jobs (title, skills, location, salary, company, job_type, posted_month)
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
        except Exception as e:
            print(f"  Skipped a row: {e}")

    conn.commit()
    print(f"  Inserted {inserted} rows successfully!")


def main():
    print("\n── Job Dashboard DB Setup ──────────────────────────")

    try:
        # Connect WITHOUT specifying DB first
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        cursor = conn.cursor()

        print("\n[1/3] Creating database...")
        create_database(cursor)

        print("\n[2/3] Creating table...")
        create_table(cursor)

        print("\n[3/3] Loading CSV data...")
        load_csv(cursor, conn)

        cursor.close()
        conn.close()

        print("\n All done! Run  python app.py  to start the server.")
        print(" Open browser at:  http://localhost:5000\n")

    except Error as e:
        print(f"\n MySQL Error: {e}")
        print(" Check your MYSQL_PASSWORD in this file and try again.\n")


if __name__ == "__main__":
    main()
