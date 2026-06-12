"""
BU URSA timetable scraper — seat3.cfm → all-timetable-{year}-{sem}.json

Covers ALL BU faculties: Engineering, Business, Communication Arts,
Architecture, Law, Hospitality, International (BUIC), Liberal Arts,
IT, Health Sciences, and service/GE courses.

Usage:
    python scrape_timetable.py --user ID --password PASS
    python scrape_timetable.py --user ID --password PASS --year 68 --sem 2
    python scrape_timetable.py --user ID --password PASS --groups engineering,service
    python scrape_timetable.py --user ID --password PASS --dry-run

    --groups  comma-separated group names to scrape (default: all)
              valid: engineering, business, communication_arts, architecture,
                     law, hospitality, international, liberal_arts, technology,
                     health, service

Output files:
    Server/data/all-timetable-{YYYY}-{sem}.json  — raw backup
    Web/public/data/timetable-{YYYY}-{sem}.json  — served by the app

Seat3 15-column layout per data row:
  [0] section   [1] seat_total   [2] seat_taken   [3] seat_left
  [4] status    [5] type         [6] day          [7] time
  [8] room      [9] remark2      [10] remark1
  [11] curr     [12] class       [13] prog        [14] camp
"""
import argparse
import json
import pathlib
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://ursa2.bu.ac.th"

# -------------------------------------------------------------------
# Keyword → (group, display name) mapping.
# Each keyword is searched on seat2/seat3. Overlapping keywords were
# verified: ARC⊂AR, IGE⊂IG, LAW⊂LA, CSI⊂CS — those are omitted.
# -------------------------------------------------------------------
TARGETS = [
    # ── Engineering ──────────────────────────────────────────────
    {"group": "engineering",       "keyword": "EE"},   # Electrical Engineering
    {"group": "engineering",       "keyword": "CE"},   # Computer & Robotics Engineering
    {"group": "engineering",       "keyword": "MI"},   # Multimedia & Entertainment Engineering
    {"group": "engineering",       "keyword": "AIE"},  # AI & Data Engineering
    {"group": "engineering",       "keyword": "ME"},   # Mechanical Engineering (shared)
    {"group": "engineering",       "keyword": "IE"},   # Industrial Engineering (shared)
    {"group": "engineering",       "keyword": "CO"},   # Computer (shared)
    {"group": "engineering",       "keyword": "CS"},   # Computer Science (shared, covers CSI*)
    # ── Business Administration ───────────────────────────────────
    {"group": "business",          "keyword": "AC"},   # Accounting
    {"group": "business",          "keyword": "EC"},   # Economics
    {"group": "business",          "keyword": "FI"},   # Finance
    {"group": "business",          "keyword": "MG"},   # Management
    {"group": "business",          "keyword": "MK"},   # Marketing
    {"group": "business",          "keyword": "BD"},   # Business/Digital Design
    {"group": "business",          "keyword": "ABM"},  # Asian Business Management
    {"group": "business",          "keyword": "DMK"},  # Digital Marketing
    {"group": "business",          "keyword": "BEP"},  # Business Entrepreneurship
    {"group": "business",          "keyword": "BQ"},   # Business (misc)
    {"group": "business",          "keyword": "FB"},   # Finance/Business misc
    {"group": "business",          "keyword": "CIB"},  # International Business sub
    # ── Communication Arts ───────────────────────────────────────
    {"group": "communication_arts","keyword": "BR"},   # Broadcasting (covers BRS*)
    {"group": "communication_arts","keyword": "CA"},   # Communication Arts
    {"group": "communication_arts","keyword": "CB"},   # Communication — Broadcasting
    {"group": "communication_arts","keyword": "CD"},   # Communication Design / Digital
    {"group": "communication_arts","keyword": "CM"},   # Communication Management
    {"group": "communication_arts","keyword": "FM"},   # Film / Media
    {"group": "communication_arts","keyword": "PR"},   # Public Relations
    {"group": "communication_arts","keyword": "JR"},   # Journalism
    {"group": "communication_arts","keyword": "TC"},   # Telecommunications / Media (covers TCM*)
    {"group": "communication_arts","keyword": "CNM"},  # Communication New Media
    {"group": "communication_arts","keyword": "CTA"},  # Creative Technology Arts
    # ── Architecture & Design ─────────────────────────────────────
    {"group": "architecture",      "keyword": "AR"},   # Architecture (covers ARC*)
    {"group": "architecture",      "keyword": "ID"},   # Interior Design
    # ── Law ──────────────────────────────────────────────────────
    {"group": "law",               "keyword": "LA"},   # Law — Thai (covers LAW*)
    {"group": "law",               "keyword": "LW"},   # Law — LW-prefix programs
    {"group": "law",               "keyword": "LM"},   # Legal Management
    # ── Tourism & Hospitality ─────────────────────────────────────
    {"group": "hospitality",       "keyword": "HM"},   # Hotel Management
    {"group": "hospitality",       "keyword": "HT"},   # Hospitality Tourism
    {"group": "hospitality",       "keyword": "TM"},   # Tourism Management
    # ── International Programs (BUIC) ─────────────────────────────
    {"group": "international",     "keyword": "IB"},   # International Business
    {"group": "international",     "keyword": "IF"},   # International Finance
    {"group": "international",     "keyword": "IM"},   # International Management
    {"group": "international",     "keyword": "GI"},   # Global Innovation (≠ IG/IGE)
    {"group": "international",     "keyword": "IS"},   # International Studies
    # ── Fine & Liberal Arts ───────────────────────────────────────
    {"group": "liberal_arts",      "keyword": "FA"},   # Fine Arts
    {"group": "liberal_arts",      "keyword": "VA"},   # Visual Arts
    {"group": "liberal_arts",      "keyword": "PF"},   # Performing Arts (covers PFA*)
    {"group": "liberal_arts",      "keyword": "TH"},   # Thai Language / Culture
    {"group": "liberal_arts",      "keyword": "PS"},   # Psychology / Political Science (covers PSE*)
    {"group": "liberal_arts",      "keyword": "ED"},   # Education / Digital Media
    {"group": "liberal_arts",      "keyword": "FSD"},  # Fashion & Design / Fine Arts sub
    {"group": "liberal_arts",      "keyword": "INT"},  # International Liberal Arts
    # ── Digital Media & Cinematic Arts ────────────────────────────
    {"group": "digital_media",     "keyword": "DCA"},  # Digital Cinema Arts
    {"group": "digital_media",     "keyword": "DMA"},  # Digital Media Arts
    # ── Information Technology ────────────────────────────────────
    {"group": "technology",        "keyword": "IT"},   # Information Technology
    # ── Health Sciences ───────────────────────────────────────────
    {"group": "health",            "keyword": "PT"},   # Physical Therapy
    # ── Service / General Education ───────────────────────────────
    {"group": "service",           "keyword": "GE"},   # General Education
    {"group": "service",           "keyword": "EN"},   # English
    {"group": "service",           "keyword": "EL"},   # English Language
    {"group": "service",           "keyword": "MA"},   # Mathematics
    {"group": "service",           "keyword": "PH"},   # Physics
    {"group": "service",           "keyword": "CH"},   # Chemistry
    {"group": "service",           "keyword": "IG"},   # Intl GE service (covers IGE*)
    {"group": "service",           "keyword": "CP"},   # General competency
    {"group": "service",           "keyword": "TE"},   # Foundation / BUIC general
    {"group": "service",           "keyword": "ST"},   # Statistics
    {"group": "service",           "keyword": "AD"},   # Art & Design foundation
]

YEAR_TO_BEBE = {
    "68": "2568", "69": "2569", "70": "2570",
    "67": "2567", "66": "2566", "65": "2565",
}


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def norm_time(t: str) -> str:
    """Normalise '12.40-15.40' → '12:40-15:40'."""
    return re.sub(r"(\d+)\.(\d+)", r"\1:\2", t.strip())


def decode_page(resp: requests.Response) -> BeautifulSoup:
    resp.encoding = "windows-874"
    return BeautifulSoup(resp.text, "html.parser")


def login(session: requests.Session, user: str, password: str) -> None:
    """POST credentials; session cookies are set automatically."""
    # Must visit seat1.cfm first — the server issues CFID/CFTOKEN here
    session.get(f"{BASE_URL}/seat/seat1.cfm", timeout=30)

    resp = session.post(
        f"{BASE_URL}/SetFullId.cfm",
        data={"liveid": user, "inter_passwd": password, "option1": "1"},
        timeout=30,
    )
    soup = decode_page(resp)
    body = soup.get_text(" ")
    # Successful login redirects to seat1.cfm showing the search form (has "acdyr" select)
    # Failed login shows "Access Denied" on SetFullId.cfm
    if "Access Denied" in body or "SetFullId" in resp.url:
        print("[ERROR] Login failed — check username/password.", file=sys.stderr)
        sys.exit(1)
    print("[OK] Logged in as", user)


def fetch_courses(session: requests.Session, acdyr: str, semcode: str, keyword: str) -> dict[str, dict]:
    """
    Query seat2.cfm for a keyword.
    Returns {course_code: {name, credits, open_status}} or {} if not found.
    """
    resp = session.post(
        f"{BASE_URL}/seat/seat2.cfm",
        data={
            "option1": "1",
            "acdyr": acdyr,
            "semcode": semcode,
            "coursecode": keyword,
            "section": "",
            "grdqry_op": "GO",
        },
        timeout=30,
    )
    soup = decode_page(resp)
    body_text = soup.get_text(" ")
    if "Sorry, data not found" in body_text:
        print(f"  [{keyword}] not offered this term — skipping")
        return {}

    result: dict[str, dict] = {}
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 3:
            continue
        code = cells[0].get_text(strip=True)
        desc = cells[1].get_text(strip=True)
        status = cells[2].get_text(strip=True)
        if not re.match(r"^[A-Z]{2,5}\d{3}", code):
            continue
        # credits: "Electric Circuit Theory [3 Credits]" → 3
        m = re.search(r"\[(\d+)\s+Credits?\]", desc, re.I)
        credits = int(m.group(1)) if m else None
        course_name = re.sub(r"\s*\[\d+\s+Credits?\]", "", desc, flags=re.I).strip()
        result[code] = {"name": course_name, "credits": credits, "status": status}

    print(f"  [{keyword}] seat2: {len(result)} courses")
    return result


def fetch_sections(session: requests.Session, acdyr: str, semcode: str,
                   keyword: str, group: str, course_info: dict) -> list[dict]:
    """
    Query seat3.cfm?all=1 and parse the 15-column table.
    Returns list of flat section-meeting dicts ready for output JSON.
    """
    resp = session.get(
        f"{BASE_URL}/seat/seat3.cfm",
        params={
            "acdyr": acdyr,
            "semcode": semcode,
            "coursecode": keyword,
            "option1": "1",
            "section": "",
            "all": "1",
        },
        timeout=60,
    )
    soup = decode_page(resp)

    current_code: str | None = None
    current_prefix: str | None = None
    current_name: str | None = None
    sections: list[dict] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        # Each course is one table: row[0] = header (2 cells: code + name),
        # then header rows, then data rows (15 cells each).
        first_cells = rows[0].find_all("td")
        if len(first_cells) == 2:
            code_text = first_cells[0].get_text(strip=True)
            if re.match(r"^[A-Z]{2,5}\d{3}", code_text):
                current_code = code_text
                current_prefix = re.match(r"^([A-Za-z]+)", current_code).group(1)
                current_name = first_cells[1].get_text(strip=True)

        # Always scan all rows in this table for 15-col data rows
        for row in rows:
            cells = row.find_all("td")
            if len(cells) != 15 or current_code is None:
                continue

            cell = [c.get_text(separator=" ").replace("\xa0", " ").strip() for c in cells]
            section = cell[0]
            if not section:
                continue
            # skip pure-header rows
            if section.lower() in ("section", "total", "taken", "left"):
                continue

            info = course_info.get(current_code, {})
            day = cell[6]
            raw_time = cell[7]
            time_str = norm_time(raw_time) if raw_time else ""
            room = cell[8] or None

            # Skip rows where day or time are blank (no schedule assigned)
            if not day or not time_str:
                continue

            sections.append({
                "prefix": current_prefix,
                "group": group,
                "course": current_code,
                "course_name": info.get("name") or current_name or current_code,
                "section": section,
                "status": cell[4],
                "type": cell[5],
                "day": day,
                "time": time_str,
                "room": room,
                "credits": info.get("credits"),
            })

    print(f"  [{keyword}] seat3: {len(sections)} meeting rows")
    return sections


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def scrape(args: argparse.Namespace) -> None:
    acdyr = args.year
    semcode = args.sem
    be_year = YEAR_TO_BEBE.get(acdyr, f"25{acdyr}")

    # Filter targets by --groups if specified
    group_filter = None
    if args.groups and args.groups.lower() != "all":
        group_filter = {g.strip() for g in args.groups.split(",")}

    active = [t for t in TARGETS if group_filter is None or t["group"] in group_filter]
    print(f"Scraping: acdyr={acdyr} ({be_year}), sem={semcode}, "
          f"groups={'all' if group_filter is None else ','.join(sorted(group_filter))}, "
          f"keywords={len(active)}")

    session = requests.Session()
    session.verify = True
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    )

    if not args.dry_run:
        login(session, args.user, args.password)

    all_sections: list[dict] = []
    # Deduplicate across keywords: same course+section+day+time = same meeting
    seen: set[tuple] = set()

    for target in active:
        kw = target["keyword"]
        group = target["group"]
        print(f"\nKeyword: {kw}  [{group}]")

        if args.dry_run:
            print(f"  [dry-run] would fetch {kw}")
            continue

        try:
            course_info = fetch_courses(session, acdyr, semcode, kw)
            if not course_info:
                continue
            time.sleep(0.4)  # polite delay
            sections = fetch_sections(session, acdyr, semcode, kw, group, course_info)
            added = 0
            for sec in sections:
                key = (sec["course"], sec["section"], sec["day"], sec["time"])
                if key not in seen:
                    seen.add(key)
                    all_sections.append(sec)
                    added += 1
            dupes = len(sections) - added
            if dupes:
                print(f"  [{kw}] deduplicated {dupes} rows")
            time.sleep(0.4)
        except requests.RequestException as e:
            print(f"  [WARN] network error for {kw}: {e}", file=sys.stderr)
            continue

    if args.dry_run:
        print("\n[dry-run] Done — no files written.")
        return

    # ------- Write outputs -------
    sem_label = {"1": "1", "2": "2", "3": "0"}[semcode]  # 3=summer stored as 0 in filenames? keep as-is
    sem_label = semcode  # use raw semcode as file suffix

    meta = {
        "acdyr": acdyr,
        "year": be_year,
        "semcode": semcode,
        "semester": {"1": "1", "2": "2", "3": "Summer"}.get(semcode, semcode),
        "scrapedFrom": "ursa2.bu.ac.th/seat",
        "faculty": "School of Engineering + shared service courses",
    }

    payload = {"meta": meta, "count": len(all_sections), "sections": all_sections}

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    server_data = repo_root / "Server" / "data"
    web_data = repo_root / "Web" / "public" / "data"

    server_out = server_data / f"all-timetable-{be_year}-{sem_label}.json"
    web_out = web_data / f"timetable-{be_year}-{sem_label}.json"

    for path in (server_data, web_data):
        path.mkdir(parents=True, exist_ok=True)

    with open(server_out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {server_out}")

    # Web version: same structure, credits already embedded per row
    with open(web_out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[saved] {web_out}")

    # Update terms.json
    terms_path = web_data / "terms.json"
    try:
        terms_data = json.loads(terms_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        terms_data = {"terms": []}

    sem_labels = {"1": f"ปี {be_year} / เทอม 1", "2": f"ปี {be_year} / เทอม 2", "3": f"ปี {be_year} / ซัมเมอร์"}
    file_name = f"timetable-{be_year}-{sem_label}.json"
    new_term = {
        "year": be_year,
        "semester": semcode,
        "label": sem_labels.get(semcode, f"{be_year}/{semcode}"),
        "file": file_name,
        "count": len(all_sections),
    }

    # Replace existing entry or append
    updated = False
    for i, t in enumerate(terms_data["terms"]):
        if t["year"] == be_year and t["semester"] == semcode:
            terms_data["terms"][i] = new_term
            updated = True
            break
    if not updated:
        terms_data["terms"].append(new_term)

    # Sort by year desc, semester asc
    terms_data["terms"].sort(key=lambda t: (t["year"], t["semester"]))

    with open(terms_path, "w", encoding="utf-8") as f:
        json.dump(terms_data, f, ensure_ascii=False, indent=2)
    print(f"[saved] {terms_path}")

    print(f"\nDone — {len(all_sections)} total meeting rows.")


def main() -> None:
    p = argparse.ArgumentParser(description="Scrape BU URSA timetable data")
    p.add_argument("--user", required=True, help="URSA username (student ID)")
    p.add_argument("--password", required=True, help="URSA password")
    p.add_argument("--year", default="68", help="Academic year code (e.g. 68 = 2568 B.E., default: 68)")
    p.add_argument("--sem", default="1", choices=["1", "2", "3"], help="Semester (1/2/3=summer, default: 1)")
    p.add_argument("--groups", default="all",
                   help="Comma-separated groups to scrape (default: all). "
                        "Options: engineering, business, communication_arts, architecture, "
                        "law, hospitality, international, liberal_arts, technology, health, service")
    p.add_argument("--dry-run", action="store_true", help="Print what would be scraped without writing files")
    args = p.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
