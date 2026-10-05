
import requests

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

print("1. Opening NSE homepage...")

home = session.get(
    "https://www.nseindia.com/",
    timeout=30
)

print("Homepage:", home.status_code)
print("Cookies:", session.cookies.get_dict())

print("\n2. Calling official Board Meetings endpoint...")

api_url = (
    "https://www.nseindia.com/api/"
    "corporate-board-meetings"
)

params = {
    "index": "equities"
}

response = session.get(
    api_url,
    params=params,
    timeout=30
)

print("API STATUS:", response.status_code)
print("CONTENT TYPE:", response.headers.get("Content-Type"))
print("CONTENT LENGTH:", len(response.content))

print("\nFIRST 3000 CHARACTERS:\n")
print(response.text[:3000])
