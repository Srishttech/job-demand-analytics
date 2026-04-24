CREATE DATABASE IF NOT EXISTS job_dashboard;
USE job_dashboard;

-- Step 2: Create jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    title        VARCHAR(200)  NOT NULL,
    skills       TEXT,
    location     VARCHAR(100),
    salary       DECIMAL(12, 2) DEFAULT 0,
    company      VARCHAR(200),
    job_type     VARCHAR(50)   DEFAULT 'Full-time',
    posted_month VARCHAR(20),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 3: Verify table was created
DESCRIBE jobs;

-- (Optional) Check row count after CSV load
-- SELECT COUNT(*) FROM jobs;
