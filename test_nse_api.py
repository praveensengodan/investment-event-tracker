import requests
import json

session = requests.Session()

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

session.headers.update(headers)

api_url = (
    "https://www.nseindia.com/api/"
    "corporate-board-meetings"
)

params = {
    "index": "equities",
    "symbol": "HDFCBANK"
}

print("Requesting HDFC Bank events...")

response = session.get(
    api_url,
    params=params,
    timeout=30
)

print("STATUS:", response.status_code)

data = response.json()

print("NUMBER OF RECORDS:", len(data))

print("\nHDFC EVENTS:\n")

for event in data:

    print(
        "Symbol:",
        event.get("bm_symbol")
    )

    print(
        "Company:",
        event.get("sm_name")
    )

    print(
        "Date:",
        event.get("bm_date")
    )

    print(
        "Purpose:",
        event.get("bm_purpose")
    )

    print(
        "Details:",
        event.get("bm_desc")
    )

    print(
        "Broadcast:",
        event.get("bm_timestamp")
    )

    print(
        "Attachment:",
        event.get("attachment")
    )

    print("-" * 80)
