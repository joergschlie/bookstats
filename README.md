# Springer Book Access Timeseries Scraper

Automated daily webscraper that tracks the number of accesses for the Springer Open Access book:
**[Künstlich I Menschlich I Intelligent: Verantwortungsvoller Einsatz von KI durch praxisnahe Forschung und Transfer](https://link.springer.com/book/10.1007/978-3-658-53428-8)** (DOI: `10.1007/978-3-658-53428-8`) as well as all **16 individual chapters**.

## 📊 Data Output

The scraper updates two output files daily:
- **`book_stats.csv`**: UTF-8 with BOM (`utf-8-sig`) encoding for seamless compatibility with Microsoft Excel (German Umlauts are properly displayed).
- **`book_stats.xlsx`**: Excel workbook with formatted column widths and a clean layout.

### Columns
| Column | Description | Example |
| :--- | :--- | :--- |
| `Datum` | Date of the measurement (`YYYY-MM-DD`) | `2026-11-09` |
| `Buch` | Total accesses for the complete book | `7342` |
| `Von der Kohleregion zur Zukunftsregion...` | Chapter 1 accesses | `397` |
| `Industrie 5.0: Mensch, Nachhaltigkeit...` | Chapter 2 accesses | `405` |
| `...` | Chapters 3 to 16 | `...` |

Each day's execution appends a new row to the timeseries. If run multiple times on the same day, it updates that day's entry rather than creating duplicates.

---

## 🚀 Quick Start (Local)

### 1. Requirements & Installation
Python 3.10+ is recommended. Install required packages:
```bash
pip install -r requirements.txt
```

### 2. Run Manually
```bash
python book_scraper.py
```

---

## ⚙️ Automated Daily Execution

### Option A: GitHub Actions (Recommended)

A pre-configured GitHub Actions workflow is included at [`.github/workflows/daily_scrape.yml`](.github/workflows/daily_scrape.yml). It automatically runs every day at **04:00 UTC (05:00 CET)**, runs the scraper, and commits the updated CSV and Excel files back to the repository.

#### Setup Instructions:
1. Initialize git and commit your files:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Springer book access tracker"
   git branch -M main
   ```
2. Create a repository on GitHub (e.g. `bookstats`) and push:
   ```bash
   git remote add origin https://github.com/<YOUR-USERNAME>/bookstats.git
   git push -u origin main
   ```
3. Enable write permissions for GitHub Actions:
   - On GitHub, go to your repository: **Settings** → **Actions** → **General**.
   - Under **Workflow permissions**, select **"Read and write permissions"**.
   - Click **Save**.
4. (Optional) Test it immediately:
   - Go to the **Actions** tab on GitHub.
   - Select **"Daily Book Stats Scraper"** on the left.
   - Click **"Run workflow"** → **"Run workflow"**.

---

### Option B: Local Linux Cronjob

If you prefer to run the scraper on your own Linux machine or server:

1. Open your crontab editor:
   ```bash
   crontab -e
   ```
2. Add a line to execute daily (e.g. at 05:00 AM local time):
   ```cron
   0 5 * * * cd /home/joerg/kmi/bookstats && /usr/bin/python3 book_scraper.py >> scraper.log 2>&1
   ```
3. If you want the local cronjob to also commit and push the results to GitHub automatically:
   ```cron
   0 5 * * * cd /home/joerg/kmi/bookstats && /usr/bin/python3 book_scraper.py && git add book_stats.csv book_stats.xlsx && git diff --staged --quiet || (git commit -m "Daily stats update: $(date +\%Y-\%m-\%d)" && git push) >> scraper.log 2>&1
   ```
