import requests
import time
from datetime import datetime, timedelta


# ============================================================
# CONFIGURATION
# ============================================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbySSc5SudGTpSjnIXbQaoeAsr6mYDXFkR2YPnLvpyVIoQsTbflb1W7Wj_oV1EEq_dqS/exec"
WATCHLIST_URL = f"{WEB_APP_URL}?type=eventwatchlist"
POST_URL = WEB_APP_URL

DAYS_AHEAD = 90

NSE_BOARD_MEETINGS_API = (
    "https://www.nseindia.com/api/"
    "corporate-board-meetings"
)

# ============================================================
# NSE SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/json,text/plain,*/*"
    ),
    "Accept-Language": (
        "en-IN,en;q=0.9"
    ),
    "Referer": (
        "https://www.nseindia.com/"
    ),
})


# ============================================================
# DATE RANGE
# ============================================================

today = datetime.now().date()

end_date = (
    today +
    timedelta(days=DAYS_AHEAD)
)


# ============================================================
# FETCH EVENTS FOR ONE COMPANY
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
                "company": company,
                "symbol": symbol
            })

    print(f"Watchlist loaded: {len(watchlist)} companies")

    return watchlist

def fetch_nse_events(symbol):

    print(
        f"Fetching {symbol}...",
        end=" "
    )

    try:

        response = session.get(
            NSE_BOARD_MEETINGS_API,
            params={
                "index": "equities",
                "symbol": symbol,
            },
            timeout=30,
        )

        if response.status_code != 200:

            print(
                f"FAILED - HTTP {response.status_code}"
            )

            return []

        data = response.json()

        events = []

        for item in data:

            date_text = item.get(
                "bm_date"
            )

            if not date_text:
                continue

            try:

                event_date = datetime.strptime(
                    date_text,
                    "%d-%b-%Y",
                ).date()

            except ValueError:

                continue

            # Only upcoming events
            if event_date < today:
                continue

            if event_date > end_date:
                continue

            events.append({
                "symbol": item.get(
                    "bm_symbol"
                ),

                "company": item.get(
                    "sm_name"
                ),

                "event_date": (
                    event_date.isoformat()
                ),

                "purpose": item.get(
                    "bm_purpose"
                ),

                "details": item.get(
                    "bm_desc"
                ),

                "broadcast_time": item.get(
                    "bm_timestamp"
                ),

                "attachment": item.get(
                    "attachment"
                ),
            })

        print(
            f"OK - {len(events)} events"
        )

        return events

    except Exception as error:

        print(
            f"ERROR - {error}"
        )

        return []


# ============================================================
# FETCH ALL WATCHLIST COMPANIES
# ============================================================

def collect_nse_events():

    all_events = []
    watchlist = get_watchlist()

    print("=" * 70)
    print("NSE INVESTMENT EVENT COLLECTOR")
    print("=" * 70)

    print(
        f"Date: {today}"
    )

    print(
        f"Looking ahead until: {end_date}"
    )

    print(
        f"Companies: {len(watchlist)}"
    )

    print("=" * 70)

    for item in watchlist:
        symbol = item["symbol"]
        company = item["company"]

        events = fetch_nse_events(
            symbol
        )

        all_events.extend(
            events
        )

        # Avoid sending requests too quickly
        time.sleep(1)

    return all_events


# ============================================================
# NORMALIZE EVENT TYPE
# ============================================================

def normalize_event_type(
    purpose,
    details=""
):

    text = (
        f"{purpose or ''} "
        f"{details or ''}"
    ).lower()

    if "financial results" in text:
        return "Quarterly Result"

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

        if not symbol or not company or not event_date:
            continue

        event_type = normalize_event_type(
            purpose,
            details,
        )

        key = f"{symbol}|{event_type}|{event_date}"

        source_url = event.get("attachment") or ""
        note_candidate = details or purpose or ""

        if key in events_by_key:
            existing = events_by_key[key]
            # Retain source URL if available
            if source_url and not existing["sourceUrl"]:
                existing["sourceUrl"] = source_url
            # Merge notes without duplication
            if note_candidate and note_candidate not in existing["notes"]:
                existing["notes"] = (
                    f"{existing['notes']}; {note_candidate}".strip("; ")
                )
        else:
            events_by_key[key] = {
                "symbol": symbol,
                "company": company,
                "eventType": event_type,
                "eventDate": event_date,
                "eventTime": "",
                "status": "Confirmed",
                "source": "NSE Official",
                "sourceUrl": source_url,
                "notes": note_candidate,
            }

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

        print(
            f"HTTP Status: {response.status_code}"
        )

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

    events = collect_nse_events()

    prepared_events = prepare_events(
        events
    )

    print()
    print("=" * 70)
    print(
        f"TOTAL UNIQUE UPCOMING EVENTS: "
        f"{len(prepared_events)}"
    )
    print("=" * 70)

    for event in sorted(
        prepared_events,
        key=lambda x: (
            x["eventDate"],
            x["symbol"],
            x["eventType"],
        ),
    ):

        print(
            event["eventDate"],
            "|",
            event["symbol"],
            "|",
            event["company"],
            "|",
            event["eventType"],
        )

    # Sync events to Google Sheet & Google Calendar
    send_events_to_sheet(prepared_events)


if __name__ == "__main__":
    main()
