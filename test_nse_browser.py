from playwright.sync_api import sync_playwright

URL = (
    "https://www.nseindia.com/"
    "companies-listing/corporate-filings-board-meetings"
    "?symbol=HDFCBANK&tabIndex=equity"
)

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True
    )

    page = browser.new_page(
        viewport={
            "width": 1440,
            "height": 1000
        },
        locale="en-IN"
    )

    print("Opening NSE...")

    page.goto(
        URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    print("Page loaded.")

    # Give NSE JavaScript time to populate the table
    page.wait_for_timeout(10000)

    text = page.locator("body").inner_text()

    print("\n===== NSE PAGE TEXT =====\n")
    print(text[:20000])

    print("\n===== SEARCH =====\n")

    for term in [
        "HDFCBANK",
        "HDFC Bank",
        "17-Oct-2026",
        "Financial Results",
        "Board Meeting Intimation"
    ]:

        print(
            term,
            "=>",
            term.lower() in text.lower()
        )

    browser.close()
