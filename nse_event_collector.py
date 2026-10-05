import re
import time
import requests
from datetime import datetime, timedelta


# ============================================================
# CONFIGURATION
# ============================================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbySSc5SudGTpSjnIXbQaoeAsr6mYDXFkR2YPnLvpyVIoQsTbflb1W7Wj_oV1EEq_dqS/exec"
WATCHLIST_URL = f"{WEB_APP_URL}?type=eventwatchlist"
POST_URL = WEB_APP_URL

DAYS_AHEAD = 90

NSE_BOARD_MEETINGS_API = "https://www.nseindia.com/api/corporate-board-meetings"
NSE_ANNOUNCEMENTS_API = "https://www.nseindia.com/api/corporate-announcements"

BSE_BOARD_MEETINGS_API = "https://api.bseindia.com/BseIndiaAPI/api/BoardMeeting/w"
BSE_ANNOUNCEMENTS_API = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"


# ============================================================
# SESSIONS
# ============================================================
nse_session = requests.Session()
nse_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
})

bse_session = requests.Session()
bse_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.bseindia.com/",
    "Origin": "https://www.bseindia.com",
})


# ============================================================
# DATE RANGE
# ============================================================
today = datetime.now().date()
end_date = today + timedelta(days=DAYS_AHEAD)


# ============================================================
# TIME & TEXT PARSING
# ============================================================

def extract_event_time(text):
    """
    Extracts meeting/concall time from text description.
    Supports formats: '4:30 PM', '16:30', '05:00 PM IST', '5.30 PM', '17:00 hrs'
    Returns 'HH:MM' (24-hr format) or '' if not found.
    """
    if not text:
        return ""

    # 12-hour pattern: e.g. 4:30 PM, 04.30 PM, 5 PM
    match12 = re.search(
        r'\b((?:1[0-2]|0?[1-9])(?::|\.)[0-5][0-9]\s*(?:AM|PM|am|pm))\b',
        text
    )
    if match12:
        raw_time = match12.group(1).replace(".", ":").upper()
        try:
            parsed = datetime.strptime(raw_time.strip(), "%I:%M %p")
            return parsed.strftime("%H:%M")
        except ValueError:
            pass

    # 24-hour pattern: e.g. 16:30, 17:00 hrs
    match24 = re.search(
        r'\b([01]?[0-9]|2[0-3]):([0-5][0-9])(?:\s*(?:hrs|hours|IST))?\b',
        text
    )
    if match24:
        hour = int(match24.group(1))
        minute = match24.group(2)
        # Exclude unlikely morning times like 00:00 unless intentional
        return f"{hour:02d}:{minute}"

    return ""


def normalize_event_type(purpose, details=""):
    text = f"{purpose or ''} {details or ''}".lower()

    if "financial results" in text or "quarterly" in text:
        return "Quarterly Result"
    if "concall" in text or "conference call" in text or "analyst meet" in text:
        return "Earnings Concall"
    if "annual general meeting" in text:
        return "AGM"
    if "extraordinary general meeting" in text:
        return "EGM"
    if "dividend" in text:
        return "Dividend"
    if "bonus" in text:
        return "Bonus"
    if "stock split" in text:
        return "Stock Split"
    if "fund raising" in text:
        return "Fund Raising"
    if "board meeting" in text:
        return "Board Meeting"

    return "Other"


# ============================================================
# WATCHLIST
# ============================================================

def get_watchlist():
    print("Fetching watchlist from Google Sheet...")

    response = requests.get(
        WATCHLIST_URL,
        timeout=30
    )

    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        raise ValueError("Invalid watchlist response")

    watchlist = []
    for item in data:
        company = item.get("company")
        symbol = item.get("symbol")

        if company and symbol:
            watchlist.append({
                "company": company.strip(),
                "symbol": symbol.strip()
            })

    print(f"Watchlist loaded: {len(watchlist)} companies")
    return watchlist


# ============================================================
# NSE FETCHERS
# ============================================================

def fetch_nse_board_meetings(symbol):
    try:
        response = nse_session.get(
            NSE_BOARD_MEETINGS_API,
            params={
                "index": "equities",
                "symbol": symbol,
            },
            timeout=30,
        )

        if response.status_code != 200:
            return []

        data = response.json()
        events = []

        for item in data:
            date_text = item.get("bm_date")
            if not date_text:
                continue

            try:
                event_date = datetime.strptime(
                    date_text,
                    "%d-%b-%Y",
                ).date()
            except ValueError:
                continue

            if event_date < today or event_date > end_date:
                continue

            details = item.get("bm_desc") or ""
            purpose = item.get("bm_purpose") or ""
            parsed_time = extract_event_time(details)

            events.append({
                "symbol": item.get("bm_symbol") or symbol,
                "company": item.get("sm_name") or "",
                "event_date": event_date.isoformat(),
                "event_time": parsed_time,
                "purpose": purpose,
                "details": details,
                "broadcast_time": item.get("bm_timestamp") or "",
                "attachment": item.get("attachment") or "",
                "source": "NSE Official",
            })

        return events

    except Exception:
        return []


def fetch_nse_announcements(symbol):
    """
    Fetches NSE Corporate Announcements to capture concalls and investor meetings.
    """
    try:
        response = nse_session.get(
            NSE_ANNOUNCEMENTS_API,
            params={
                "index": "equities",
                "symbol": symbol,
            },
            timeout=30,
        )

        if response.status_code != 200:
            return []

        data = response.json()
        if not isinstance(data, list):
            return []

        events = []
        for item in data:
            desc = item.get("desc") or ""
            attmnt_text = item.get("attmntText") or ""
            combined_desc = f"{desc} {attmnt_text}"

            # Only interest in concall / earnings meet announcements
            lower_text = combined_desc.lower()
            if not any(k in lower_text for k in ["conference call", "concall", "earnings call", "analyst", "investor meet"]):
                continue

            date_str = item.get("an_dt") or ""
            event_date = None

            if date_str:
                for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%d-%m-%Y"):
                    try:
                        event_date = datetime.strptime(date_str.split()[0], fmt).date()
                        break
                    except Exception:
                        continue

            if not event_date or event_date < today or event_date > end_date:
                continue

            event_time = extract_event_time(combined_desc)
            attachment = item.get("attmntFile") or ""
            if attachment and not attachment.startswith("http"):
                attachment = f"https://nsearchives.nseindia.com/corporate/{attachment}"

            events.append({
                "symbol": symbol,
                "company": item.get("sm_name") or "",
                "event_date": event_date.isoformat(),
                "event_time": event_time,
                "purpose": desc,
                "details": combined_desc,
                "broadcast_time": date_str,
                "attachment": attachment,
                "source": "NSE Announcement",
            })

        return events

    except Exception:
        return []


# ============================================================
# BSE FETCHERS
# ============================================================

def fetch_bse_events(symbol, company=""):
    """
    Fetches Board Meetings & Corporate Announcements from BSE India API.
    """
    events = []

    try:
        # 1. BSE Board Meetings
        bm_resp = bse_session.get(
            BSE_BOARD_MEETINGS_API,
            params={"scripcode": symbol},
            timeout=30,
        )

        if bm_resp.status_code == 200:
            bm_data = bm_resp.json()
            table = bm_data if isinstance(bm_data, list) else bm_data.get("Table", [])

            for item in table:
                date_text = item.get("MeetingDate") or item.get("BMDATE")
                if not date_text:
                    continue

                event_date = None
                for fmt in ("%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%d-%b-%Y", "%d-%m-%Y"):
                    try:
                        event_date = datetime.strptime(date_text.split()[0], fmt).date()
                        break
                    except Exception:
                        continue

                if not event_date or event_date < today or event_date > end_date:
                    continue

                purpose = item.get("Purpose") or item.get("PURPOSE") or ""
                details = item.get("ShortName") or item.get("COMPNAME") or ""
                parsed_time = extract_event_time(purpose)

                events.append({
                    "symbol": symbol,
                    "company": company or item.get("COMPNAME") or symbol,
                    "event_date": event_date.isoformat(),
                    "event_time": parsed_time,
                    "purpose": purpose,
                    "details": f"{purpose} {details}".strip(),
                    "broadcast_time": "",
                    "attachment": item.get("Attachment") or "",
                    "source": "BSE Official",
                })

    except Exception:
        pass

    try:
        # 2. BSE Corporate Announcements
        ann_resp = bse_session.get(
            BSE_ANNOUNCEMENTS_API,
            params={
                "pageno": "1",
                "strCat": "-1",
                "strPrevDate": "",
                "strScrip": symbol,
                "strSearch": "P",
                "strToDate": "",
                "strType": "C",
            },
            timeout=30,
        )

        if ann_resp.status_code == 200:
            ann_data = ann_resp.json()
            table = ann_data if isinstance(ann_data, list) else ann_data.get("Table", [])

            for item in table:
                head = item.get("NEWSSUB") or item.get("HEADLINE") or ""
                desc = item.get("NEWS_DT") or ""
                combined = f"{head} {desc}"

                event_time = extract_event_time(combined)
                # Check for meeting or concall keywords
                lower_text = combined.lower()
                if not any(k in lower_text for k in ["board meeting", "financial results", "conference call", "concall", "analyst"]):
                    continue

                date_text = item.get("NEWS_DT") or ""
                event_date = None
                if date_text:
                    for fmt in ("%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%d-%b-%Y"):
                        try:
                            event_date = datetime.strptime(date_text.split()[0], fmt).date()
                            break
                        except Exception:
                            continue

                if not event_date or event_date < today or event_date > end_date:
                    continue

                events.append({
                    "symbol": symbol,
                    "company": company or item.get("SLONGNAME") or symbol,
                    "event_date": event_date.isoformat(),
                    "event_time": event_time,
                    "purpose": head,
                    "details": combined,
                    "broadcast_time": date_text,
                    "attachment": item.get("ATTACHMENTNAME") or "",
                    "source": "BSE Official",
                })

    except Exception:
        pass

    return events


# ============================================================
# UNIFIED COLLECTION
# ============================================================

def collect_all_events():
    all_events = []
    watchlist = get_watchlist()

    print("=" * 70)
    print("INVESTMENT EVENT COLLECTOR (NSE & BSE)")
    print("=" * 70)
    print(f"Date: {today}")
    print(f"Looking ahead until: {end_date}")
    print(f"Companies in Watchlist: {len(watchlist)}")
    print("=" * 70)

    for item in watchlist:
        symbol = item["symbol"]
        company = item["company"]

        print(f"Fetching {symbol} ({company})...", end=" ")

        # 1. Fetch from NSE Board Meetings
        nse_events = fetch_nse_board_meetings(symbol)

        # 2. Fetch from NSE Announcements (Concalls & Timed Meets)
        nse_ann_events = fetch_nse_announcements(symbol)

        company_events = nse_events + nse_ann_events

        # 3. If NSE has no events or for BSE securities, query BSE
        if not company_events:
            bse_events = fetch_bse_events(symbol, company)
            company_events.extend(bse_events)

        print(f"OK - {len(company_events)} events found")
        all_events.extend(company_events)

        time.sleep(1)

    return all_events


# ============================================================
# PREPARE & DEDUPLICATE EVENTS
# ============================================================

def prepare_events(events):
    events_by_key = {}

    for event in events:
        symbol = event.get("symbol")
        company = event.get("company")
        event_date = event.get("event_date")
        purpose = event.get("purpose")
        details = event.get("details")
        event_time = event.get("event_time") or ""

        if not symbol or not company or not event_date:
            continue

        event_type = normalize_event_type(
            purpose,
            details,
        )

        key = f"{symbol}|{event_type}|{event_date}"
        source_url = event.get("attachment") or ""
        note_candidate = details or purpose or ""
        source = event.get("source") or "NSE Official"

        if key in events_by_key:
            existing = events_by_key[key]

            # Upgrade time if newly extracted
            if event_time and not existing["eventTime"]:
                existing["eventTime"] = event_time

            # Retain source URL
            if source_url and not existing["sourceUrl"]:
                existing["sourceUrl"] = source_url

            # Merge notes without duplication
            if note_candidate and note_candidate not in existing["notes"]:
                existing["notes"] = f"{existing['notes']}; {note_candidate}".strip("; ")
        else:
            events_by_key[key] = {
                "symbol": symbol,
                "company": company,
                "eventType": event_type,
                "eventDate": event_date,
                "eventTime": event_time,
                "status": "Confirmed",
                "source": source,
                "sourceUrl": source_url,
                "notes": note_candidate,
            }

    # Cross-match: if an Earnings Concall has a time on the same date as a Quarterly Result,
    # enrich the Quarterly Result with the concall time if needed.
    for key, event in list(events_by_key.items()):
        if event["eventType"] == "Earnings Concall" and event["eventTime"]:
            result_key = f"{event['symbol']}|Quarterly Result|{event['eventDate']}"
            if result_key in events_by_key and not events_by_key[result_key]["eventTime"]:
                events_by_key[result_key]["eventTime"] = event["eventTime"]
                events_by_key[result_key]["notes"] += f" (Concall scheduled at {event['eventTime']})"

    return list(events_by_key.values())


# ============================================================
# SEND EVENTS TO GOOGLE SHEET & CALENDAR
# ============================================================

def send_events_to_sheet(events):
    print()
    print("=" * 70)
    print("SYNCING EVENTS TO GOOGLE SHEET & CALENDAR")
    print("=" * 70)

    if not events:
        print("No events to send.")
        return

    payload = {
        "events": events
    }

    try:
        response = requests.post(
            POST_URL,
            json=payload,
            timeout=60,
        )

        print(f"HTTP Status: {response.status_code}")
        try:
            data = response.json()
            print("Apps Script Response:", data)
        except Exception:
            print("Response:", response.text[:300])

    except Exception as error:
        print(f"Failed to post events to Apps Script: {error}")


# ============================================================
# MAIN
# ============================================================

def main():
    events = collect_all_events()
    prepared_events = prepare_events(events)

    print()
    print("=" * 70)
    print(f"TOTAL UNIQUE UPCOMING EVENTS: {len(prepared_events)}")
    print("=" * 70)

    for event in sorted(
        prepared_events,
        key=lambda x: (
            x["eventDate"],
            x["symbol"],
            x["eventType"],
        ),
    ):
        time_str = f" @ {event['eventTime']}" if event.get("eventTime") else ""
        print(
            event["eventDate"],
            "|",
            event["symbol"],
            "|",
            event["company"],
            "|",
            f"{event['eventType']}{time_str}",
        )

    # Sync events to Google Sheet & Google Calendar
    send_events_to_sheet(prepared_events)


if __name__ == "__main__":
    main()
