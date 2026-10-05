import requests
import time
from datetime import datetime, timedelta


# ============================================================
# CONFIGURATION
# ============================================================
WATCHLIST_URL = https://script.google.com/macros/s/AKfycbySSc5SudGTpSjnIXbQaoeAsr6mYDXFkR2YPnLvpyVIoQsTbflb1W7Wj_oV1EEq_dqS/exec?type=eventwatchlist
WATCHLIST = [
    "NSE",
    "GATEWAY",
    "KPITTECH",
    "CMSINFO",
    "SKYGOLD",
    "HDFCBANK",
    "CIPLA",
    "ICICIAMC",
    "TATAMOTORS",
    "LGEINDIA",
    "TATACAP",
    "TATACHEM",
    "LICI",
    "BRIGADE",
    "ASHOKLEY",
    "TATAPOWER",
    "ZYDUSLIFE",
    "DRREDDY",
    "NSDL",
    "KTKBANK",
    "SOUTHBANK",
    "IDFCFIRSTB",
    "HDBFS",
    "INDUSINDBK",
    "TMB",
    "NATCOPHARM",
]


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
        f"Companies: {len(WATCHLIST)}"
    )

    print("=" * 70)

    for symbol in WATCHLIST:

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
# PREPARE EVENTS
# ============================================================

def prepare_events(events):

    prepared = []

    for event in events:

        event_type = normalize_event_type(
            event.get("purpose"),
            event.get("details"),
        )

        prepared.append({
            "symbol":
                event.get("symbol"),

            "company":
                event.get("company"),

            "event_type":
                event_type,

            "event_date":
                event.get("event_date"),

            "event_time":
                "",

            "status":
                "Confirmed",

            "source":
                "NSE Official",

            "source_url":
                event.get("attachment") or "",

            "notes":
                event.get("details") or "",

            "broadcast_time":
                event.get("broadcast_time") or "",
        })

    return prepared


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
        f"TOTAL UPCOMING EVENTS: "
        f"{len(prepared_events)}"
    )
    print("=" * 70)

    for event in sorted(
        prepared_events,
        key=lambda x: (
            x["event_date"],
            x["symbol"],
            x["event_type"],
        ),
    ):

        print(
            event["event_date"],
            "|",
            event["symbol"],
            "|",
            event["company"],
            "|",
            event["event_type"],
        )


if __name__ == "__main__":
    main()
