#!/usr/bin/env python3
"""
Springer Book & Chapter Access Timeseries Scraper
-------------------------------------------------
Captures daily access counts for:
- The entire book: https://link.springer.com/book/10.1007/978-3-658-53428-8
- All individual chapters across all Table of Contents pages

Outputs:
- book_stats.csv (UTF-8 with BOM for Excel compatibility)
- book_stats.xlsx
"""

import sys
import os
import re
import time
from datetime import datetime
import urllib.request
import urllib.error
from bs4 import BeautifulSoup
import pandas as pd

# Base URLs
BASE_URL = "https://link.springer.com"
BOOK_DOI = "10.1007/978-3-658-53428-8"
BOOK_URL = f"{BASE_URL}/book/{BOOK_DOI}"

# Output files
CSV_FILE = "book_stats.csv"
EXCEL_FILE = "book_stats.xlsx"

# Headers mimicking a standard modern desktop browser to avoid bot blocks
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}


def fetch_html(url: str, max_retries: int = 3, retry_delay: float = 2.0) -> str:
    """Fetch HTML content of a URL with retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=HTTP_HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"  [Attempt {attempt}/{max_retries}] Error fetching {url}: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay * attempt)
            else:
                raise


def parse_access_count(html: str) -> int:
    """
    Extract the access count from HTML.
    Looks for the metric element containing 'Accesses'.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Strategy 1: Look for metrics bar count element
    for el in soup.find_all(attrs={"class": re.compile(r"metrics-bar__count", re.I)}):
        text = el.get_text(" ", strip=True)
        m = re.search(r"([\d,.\s]+)\s*Accesses", text, re.I)
        if m:
            clean = m.group(1).replace(",", "").replace(".", "").replace(" ", "").strip()
            if clean.isdigit():
                return int(clean)

    # Strategy 2: Look for 'Accesses' label and find parent count
    label = soup.find(lambda tag: tag.name in ["span", "p"] and "accesses" in tag.get_text().lower())
    if label:
        parent = label.find_parent()
        if parent:
            text = parent.get_text(" ", strip=True)
            m = re.search(r"([\d,.\s]+)\s*Accesses", text, re.I)
            if m:
                clean = m.group(1).replace(",", "").replace(".", "").replace(" ", "").strip()
                if clean.isdigit():
                    return int(clean)

    # Strategy 3: Direct regex fallback
    m = re.search(r">\s*([\d,.\s]+)\s*<span[^>]*class=\"[^\"]*metrics-bar__label\"[^>]*>\s*Accesses\s*</span>", html, re.I)
    if m:
        clean = m.group(1).replace(",", "").replace(".", "").replace(" ", "").strip()
        if clean.isdigit():
            return int(clean)

    raise ValueError("Could not extract access count from page HTML.")


def discover_all_chapters() -> list[dict]:
    """
    Extract chapter URLs and titles from all pages of the book Table of Contents.
    Paginates (?page=1#toc, ?page=2#toc, ...) until no further chapters are found.
    Sorts chapters numerically according to their DOI suffix (e.g. _1, _2, ..., _19).
    """
    pattern = re.compile(rf"/chapter/{re.escape(BOOK_DOI)}_(\d+)")
    seen = set()
    chapters = []
    page = 1

    while True:
        url = f"{BOOK_URL}?page={page}#toc"
        print(f"Discovering chapters from TOC page {page}...")
        try:
            html = fetch_html(url)
        except Exception as e:
            print(f"Failed to fetch TOC page {page}: {e}")
            break

        soup = BeautifulSoup(html, "html.parser")
        new_on_page = 0

        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = pattern.search(href)
            if m:
                clean_href = m.group(0)
                if clean_href not in seen:
                    seen.add(clean_href)
                    chapter_num = int(m.group(1))
                    title = a.get_text(strip=True)
                    chapters.append({
                        "num": chapter_num,
                        "url": f"{BASE_URL}{clean_href}",
                        "title": title
                    })
                    new_on_page += 1

        print(f"  Found {new_on_page} new chapters on page {page}.")
        if new_on_page == 0:
            break
        page += 1

    # Sort numerically by chapter number
    chapters.sort(key=lambda c: c["num"])
    return chapters


def scrape_all() -> dict:
    """Scrape access metrics for the book and all its chapters."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scrape for {today}...")

    # 1. Scrape book page for total book accesses
    print(f"Fetching main book page: {BOOK_URL}")
    book_html = fetch_html(BOOK_URL)
    book_accesses = parse_access_count(book_html)
    print(f"  Book Accesses: {book_accesses}")

    # 2. Discover all chapters across all TOC pages
    chapters = discover_all_chapters()
    print(f"Discovered {len(chapters)} chapters in total.")

    row_data = {
        "Datum": today,
        "Buch": book_accesses
    }

    # 3. Scrape each chapter
    for ch in chapters:
        print(f"Fetching Chapter {ch['num']}: {ch['title'][:50]}...")
        try:
            ch_html = fetch_html(ch["url"])
            ch_accesses = parse_access_count(ch_html)
            print(f"  -> {ch_accesses} accesses")
        except Exception as e:
            print(f"  -> ERROR: {e}. Using None.")
            ch_accesses = None

        row_data[ch["title"]] = ch_accesses
        time.sleep(0.5)  # Polite delay between requests

    return row_data


def update_timeseries_files(new_row: dict):
    """
    Appends or updates today's row in CSV and Excel files.
    If today's date is already present, updates the row.
    Otherwise appends it.
    """
    today = new_row["Datum"]

    # Load existing CSV if available
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
            df["Datum"] = df["Datum"].astype(str)
        except Exception as e:
            print(f"Warning: Could not read existing {CSV_FILE}: {e}. Creating new DataFrame.")
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    new_df_row = pd.DataFrame([new_row])

    if df.empty:
        df = new_df_row
    else:
        # Ensure all columns from new_row exist in df
        for col in new_row.keys():
            if col not in df.columns:
                df[col] = None

        # Check if today already exists
        if today in df["Datum"].values:
            print(f"Entry for {today} already exists. Updating row with all chapters...")
            idx = df[df["Datum"] == today].index[0]
            for col, val in new_row.items():
                df.at[idx, col] = val
        else:
            print(f"Appending new row for {today}...")
            df = pd.concat([df, new_df_row], ignore_index=True)

    # Reorder columns: Datum, Buch, followed by chapters in exact order
    ordered_cols = ["Datum", "Buch"] + [c for c in new_row.keys() if c not in ["Datum", "Buch"]]
    for c in df.columns:
        if c not in ordered_cols:
            ordered_cols.append(c)
    df = df[ordered_cols]

    # Save to CSV (utf-8-sig for perfect Excel compatibility with Umlauts)
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
    print(f"Saved: {CSV_FILE} ({len(df)} row(s), {len(df.columns)} columns)")

    # Save to Excel with formatted styling
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Accesses")
        worksheet = writer.sheets["Accesses"]
        # Autofit column widths
        for col_idx, col_name in enumerate(df.columns, 1):
            max_len = max(
                len(str(col_name)),
                df[col_name].astype(str).map(len).max() if not df.empty else 0
            )
            col_letter = worksheet.cell(row=1, column=col_idx).column_letter
            worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 60)

    print(f"Saved: {EXCEL_FILE} ({len(df)} row(s), {len(df.columns)} columns)")


def main():
    try:
        data = scrape_all()
        update_timeseries_files(data)
        print("Scrape completed successfully!")
    except Exception as e:
        print(f"Fatal error during scraping: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
