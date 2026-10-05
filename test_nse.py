import requests

url = "https://www.nseindia.com/companies-listing/corporate-filings-board-meetings"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

response = requests.get(
    url,
    headers=headers,
    timeout=30
)

print("HTTP STATUS:", response.status_code)
print("CONTENT LENGTH:", len(response.text))

print("\nFIRST 1000 CHARACTERS:\n")
print(response.text[:1000])
