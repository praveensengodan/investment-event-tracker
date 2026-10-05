import requests

url = (
    "https://www.nseindia.com/"
    "companies-listing/corporate-filings-board-meetings"
    "?symbol=HDFCBANK&tabIndex=equity"
)

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

response = requests.get(
    url,
    headers=headers,
    timeout=30
)

print("HTTP STATUS:", response.status_code)
print("CONTENT LENGTH:", len(response.text))

html = response.text

terms = [
    "HDFCBANK",
    "HDFC Bank",
    "17-Oct-2026",
    "Financial Results",
    "Board Meeting Intimation"
]

print("\nSEARCH RESULTS:")

for term in terms:
    print(
        term,
        "=>",
        term.lower() in html.lower()
    )

print("\nHDFC OCCURRENCES:")

search_term = "HDFCBANK"
lower_html = html.lower()

position = 0
count = 0

while True:

    position = lower_html.find(
        search_term.lower(),
        position
    )

    if position == -1:
        break

    start = max(0, position - 300)
    end = min(
        len(html),
        position + 700
    )

    print("\n--- MATCH", count + 1, "---")
    print(html[start:end])

    position += len(search_term)
    count += 1

    if count >= 5:
        break
