# Investment Event Tracker — Project Context

## Overview

A fully automated investment-event tracker for a 28-stock watchlist built exclusively using free components:
- **Google Sheets:** Stores the master watchlist (`Event Watchlist`) and processed event tracking sheet (`Stock Event Tracker`).
- **Google Apps Script:** Web app providing REST endpoints for dynamic watchlist retrieval (`doGet`) and event receiving/sync (`doPost`).
- **GitHub Actions:** Serverless runner executing the Python collection script on demand (and scheduled daily in future).
- **Official NSE API:** Direct corporate event and board meeting data feed from NSE India without third-party paid services or browser automation.
- **Google Calendar:** Dedicated calendar (`Investment Events`, `Asia/Kolkata`) displaying confirmed upcoming company events.

---

## Architecture & Data Flow

```text
Google Sheet (Event Watchlist)
       ↓
Apps Script Web App (/exec?type=eventwatchlist)
       ↓
GitHub Actions (Python 3.12 Runner)
       ↓
Official NSE API (corporate-board-meetings)
       ↓
Apps Script POST (/exec)
       ↓
Google Sheet (Stock Event Tracker)
       ↓
Investment Events Google Calendar (Asia/Kolkata)
```

---

## Watchlist Configuration

- **Source Tab:** `Event Watchlist`
- **Total Tracked Companies:** 28 companies (27 active symbols + 1 TBD)
- **Active Filter:** `doGetEventWatchlist()` returns active rows where symbol is valid (excludes `TBD`).

### Usable Symbols (28 Companies)

| # | Company | Symbol | Exchange / BSE Scrip |
|---|---|---|---|
| 1 | NSE | `NSE` | BSE: `544937` |
| 2 | Gateway Distriparks | `GATEWAY` | NSE / BSE |
| 3 | KPIT Technologies | `KPITTECH` | NSE / BSE |
| 4 | CMS Info Systems | `CMSINFO` | NSE / BSE |
| 5 | Sky Gold & Diamonds | `SKYGOLD` | NSE / BSE |
| 6 | HDFC Bank | `HDFCBANK` | NSE / BSE |
| 7 | Cipla | `CIPLA` | NSE / BSE |
| 8 | ICICI Prudential AMC | `ICICIAMC` | NSE / BSE |
| 9 | Tata Motors | `TATAMOTORS` | NSE / BSE |
| 10 | Tata Motors Passenger Vehicles | `TMPV` | NSE / BSE |
| 11 | LG Electronics India | `LGEINDIA` | NSE / BSE |
| 12 | Tata Capital | `TATACAP` | NSE / BSE |
| 13 | Tata Chemicals | `TATACHEM` | NSE / BSE |
| 14 | Life Insurance Corporation | `LICI` | NSE / BSE |
| 15 | Brigade Enterprises | `BRIGADE` | NSE / BSE |
| 16 | Ashok Leyland | `ASHOKLEY` | NSE / BSE |
| 17 | Tata Power | `TATAPOWER` | NSE / BSE |
| 18 | Zydus Lifesciences | `ZYDUSLIFE` | NSE / BSE |
| 19 | Dr. Reddy's Laboratories | `DRREDDY` | NSE / BSE |
| 20 | NSDL | `NSDL` | BSE: `544467` |
| 21 | Karnataka Bank | `KTKBANK` | NSE / BSE |
| 22 | South Indian Bank | `SOUTHBANK` | NSE / BSE |
| 23 | IDFC FIRST Bank | `IDFCFIRSTB` | NSE / BSE |
| 24 | HDB Financial Services | `HDBFS` | NSE / BSE |
| 25 | IndusInd Bank | `INDUSINDBK` | NSE / BSE |
| 26 | Tamilnad Mercantile Bank | `TMB` | NSE / BSE |
| 27 | Natco Pharma | `NATCOPHARM` | NSE / BSE |
| 28 | ITC | `ITC` | NSE / BSE |

---

## Google Apps Script & Sheets Specification

### Web App Endpoints (`doGet`)
- `/exec` — Base execution URL (defaults to Indian Stock Alerts from `Alerts` sheet)
- `/exec?type=us` — US alerts from `US Stock Alerts` sheet
- `/exec?type=eventwatchlist` — Returns active event watchlist JSON array:
  - Source Sheet: `Event Watchlist`
  - Active Filter: Column 0 (`TRUE`), Column 1 (Company), Column 2 (Symbol $\neq$ `TBD`)
  - Output format: `[{"company": "...", "symbol": "..."}]`

### Event Receiver Endpoint (`doPost`)
GitHub Actions POSTs collected events to `/exec` with `Content-Type: application/json`:
```json
{
  "events": [
    {
      "company": "HDFC Bank",
      "symbol": "HDFCBANK",
      "eventType": "Quarterly Result",
      "eventDate": "2026-10-17",
      "eventTime": "",
      "source": "NSE Official",
      "sourceUrl": "https://nsearchives.nseindia.com/...",
      "notes": "Financial Results for Q2"
    }
  ]
}
```

- **Event Key Formula:** `event.symbol + "|" + event.eventType + "|" + event.eventDate`
- **Behavior:** Updates existing row if `Event Key` matches, otherwise appends a new row to `Stock Event Tracker`.
- **Calendar Hook:** Immediately calls `syncInvestmentEvents()` upon processing POST batch.

### Stock Event Tracker Sheet Columns

| Column | Header | Description |
|---|---|---|
| A | `Company` | Full company name |
| B | `Symbol` | Stock trading ticker symbol |
| C | `Event Type` | Normalized type (e.g. `Quarterly Result`, `AGM`, `Dividend`) |
| D | `Event Date` | Date object / ISO format `YYYY-MM-DD` |
| E | `Event Time` | Specific time if confirmed, otherwise blank |
| F | `Status` | `Confirmed` / `Tentative` |
| G | `Source` | Data source identifier (e.g. `NSE Official`) |
| H | `Source URL` | Direct link to exchange attachment / circular |
| I | `Calendar Event ID` | Google Calendar event reference for synchronization |
| J | `Last Checked` | Timestamp of last sync/check |
| K | `Notes` | Additional details / description |
| L | `Event Key` | Unique composite key (`SYMBOL|EVENT_TYPE|EVENT_DATE`) |

### Google Calendar Integration (`syncInvestmentEvents`)
- **Target Calendar:** `Investment Events` (auto-created if not found)
- **Timezone:** `Asia/Kolkata`
- **Matching & Deduplication:** Checks `Calendar Event ID` first; falls back to search by title (`Company - Event Type`) within target date window.
- **Event Modes:** Creates All-Day events when `Event Time` is blank; creates 1-hour timed events when `Event Time` is present.

---

## Repository Structure & Core Components

```text
investment-event-tracker/
├── project_context.md                         # Complete project documentation and state
├── nse_event_collector.py                     # Python event extraction & normalization logic
└── .github/
    └── workflows/
        └── nse-event-collector.yml            # GitHub Actions workflow runner
```

### Key Modules

- **`nse_event_collector.py`**:
  - `get_watchlist()`: Queries Apps Script endpoint to retrieve dynamic company list.
  - `fetch_nse_events(symbol)`: Queries official NSE board meetings API for the specified symbol.
  - `collect_nse_events()`: Iterates across all watchlist items with request throttling (`time.sleep(1)`).
  - `normalize_event_type(purpose, details)`: Normalizes exchange purpose strings into standard classifications (`Quarterly Result`, `AGM`, `EGM`, `Dividend`, `Bonus`, `Stock Split`, `Fund Raising`, `Board Meeting`, `Other`).
  - `prepare_events(events)`: Formats normalized event dictionaries ready for output/sync.

- **`.github/workflows/nse-event-collector.yml`**:
  - Workflow name: `NSE Event Collector`
  - Trigger: `workflow_dispatch` (manual trigger; daily cron schedule will be added once pipeline is fully validated).
  - Environment: `ubuntu-latest`, Python `3.12`, `requests` dependency.

---

## NSE API Integration Details

- **Endpoint:** `https://www.nseindia.com/api/corporate-board-meetings`
- **Parameters:** `index=equities`, `symbol={SYMBOL}`
- **Headers:** Session uses browser `User-Agent`, `Accept`, `Accept-Language`, and `Referer` (`https://www.nseindia.com/`).
- **Lookahead Window:** 90 days from current date (`today` to `today + 90 days`).
- **Field Mappings:**
  - `bm_date`: Event date (`%d-%b-%Y` → `YYYY-MM-DD`)
  - `bm_symbol`: Stock ticker
  - `sm_name`: Company name
  - `bm_purpose`: Event purpose
  - `bm_desc`: Detailed description
  - `bm_timestamp`: Broadcast timestamp (*note: do not treat as meeting start time*)
  - `attachment`: PDF / announcement link

---

## Current Status & Next Steps

### Exact Current Position
1. **Full end-to-end pipeline tested & verified working in production:**
   - Dynamic watchlist retrieved from Google Sheet (`Event Watchlist`).
   - Official NSE API queried for all 27 active stocks.
   - Deduplication successfully merged duplicate exchange circulars into unique meeting records.
   - Batch payload posted to Google Apps Script endpoint (`doPost`).
   - `Stock Event Tracker` sheet updated with full metadata (Columns A–L).
   - Google Calendar (`Investment Events`, `Asia/Kolkata`) automatically synchronized.
2. **Automatic Execution:**
   - GitHub Actions scheduled twice daily at 6:00 AM IST & 6:30 PM IST with manual `workflow_dispatch` available anytime.
3. **Next Focus (Phase F):**
   - Add BSE support / Scrip Code fetching for BSE-only securities (e.g. NSE, NSDL).
   - Verify Tata Motors PV symbol when assigned.
   - Expand NSE sources to include Corporate Actions (Dividends, Splits, Bonus, AGM/EGM).

### Roadmap

#### Phase A — Dynamic Watchlist
- [x] Create `Event Watchlist` sheet
- [x] Configure Apps Script `doGetEventWatchlist()` endpoint
- [x] Test endpoint returning 27 companies
- [x] Integrate `get_watchlist()` in Python collector
- [x] Connect dynamic watchlist execution in `collect_nse_events()`

#### Phase B — NSE Collection & Deduplication
- [x] Official NSE API integration (Board Meetings)
- [x] Filter upcoming 90-day window
- [x] Deduplicate multiple records for same meeting (e.g. `Board Meeting Intimation` vs `Financial Results`)
- [x] Implement robust composite `Event Key`
- [ ] Add Event Calendar source
- [ ] Add Shareholder Meetings / Postal Ballot source
- [ ] Add Corporate Actions source

#### Phase C — Google Sheet Receiver
- [x] Design `Stock Event Tracker` schema (Columns A–L)
- [x] Implement Apps Script `doPost()` receiver
- [x] End-to-end GitHub Actions → Google Sheet write/update test (Verified)

#### Phase D — Google Calendar Sync
- [x] Configure `Investment Events` calendar
- [x] Implement and verify `syncInvestmentEvents()` logic
- [x] End-to-end event update → calendar entry verification (Verified)

#### Phase E — Automation & Scheduling
- [x] Add GitHub Actions daily cron schedule (6:00 AM IST & 6:30 PM IST)
- [x] Retain `workflow_dispatch` for manual on-demand triggers
- [x] Verified automatic end-to-end execution

#### Phase F — Future Enhancements
- [ ] Add BSE collector / Scrip Code support for BSE-listed securities (NSE, NSDL)
- [ ] Verify Tata Motors PV symbol when listed/assigned
- [ ] Corporate actions tracking (Record dates, Ex-dates, Dividends, Buybacks, Splits/Bonus)
- [ ] Company IR fallback sources for unlisted / special filings
