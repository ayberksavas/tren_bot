# TCDD Train Ticket Monitor

Automated tool that monitors the TCDD (Turkish State Railways) e-bilet website for available train seats on a given route and date. Sends an email notification when tickets matching your criteria are found.

## Requirements

- Python 3.10+
- Brave Browser (Chromium-based)
- Dependencies:
  ```
  pip install undetected-chromedriver selenium
  ```

## Configuration

All settings are at the top of `train.py`:

| Setting | Description | Example |
|---|---|---|
| `FROM_STATION` | Departure station name | `"Ankara Gar"` |
| `TO_STATION` | Arrival station name | `"İSTANBUL(SÖĞÜTLÜÇEŞME) , İSTANBUL"` |
| `TRAVEL_DAY` | Day of the month to check | `9` |
| `CHECK_EVERY_MINUTES` | Base interval between checks | `15` |
| `EARLIEST_DEPARTURE` | Only check trains after this time | `"08:00"` or `None` |
| `LATEST_DEPARTURE` | Only check trains before this time | `"14:00"` or `None` |
| `MIN_SEATS` | Minimum seats to trigger alert (set to 3 to skip the ~2 disabled seats always shown) | `3` |
| `BOT_EMAIL` | Gmail address used to send notifications | `"bot@gmail.com"` |
| `BOT_APP_PASSWORD` | Gmail App Password (not regular password) | `"xxxx xxxx xxxx xxxx"` |
| `NOTIFY_EMAIL` | Email address that receives alerts | `"you@gmail.com"` |
| `TEST_MODE` | `True` = single run with debug output, `False` = monitor loop | `False` |

### Gmail App Password Setup

The bot email needs 2-Factor Authentication enabled to generate an App Password:

1. Enable 2FA on the bot Gmail account (Security > 2-Step Verification)
2. Go to Security > App Passwords
3. Generate a password for "Mail"
4. Use the 16-character code as `BOT_APP_PASSWORD`

## Usage

### Test mode (single run)

```bash
python train.py   # with TEST_MODE = True
```

Opens the browser, fills the form, checks results once, and prints debug info. Use this to verify selectors and station names work correctly.

### Monitor mode (continuous)

```bash
python train.py   # with TEST_MODE = False
```

Runs in a loop:
1. Opens TCDD website
2. Selects departure/arrival stations
3. Picks the travel date from the calendar
4. Searches for trains
5. Parses results: extracts departure time and seat count per train
6. If any train has >= `MIN_SEATS` within the time range: sends email and stops
7. Otherwise: waits a randomized interval and repeats

The wait between checks is randomized (base ± 30% + 0-120s extra) to avoid detection.

## Project Structure

```
tren_bot/
  train.py      - Main script (config, browser automation, parsing, email)
  diagnose.py   - Diagnostic tool for inspecting page elements (optional)
  README.md     - This file
```

### Key functions in train.py

| Function | Purpose |
|---|---|
| `create_driver()` | Launches Brave with undetected-chromedriver |
| `select_station()` | Fills a station dropdown (click > type > select result) |
| `time_in_range()` | Checks if a departure time falls within the configured window |
| `send_email()` | Sends Gmail notification via SMTP |
| `check_results()` | Parses the results page for train times and seat counts |
| `check_tickets()` | Full flow: open site > fill form > search > parse results |
| `debug_find_elements()` | Dumps all page inputs/buttons (test mode only) |

## Disclaimer

This project is for **personal and educational purposes only**. It is not affiliated with, endorsed by, or connected to TCDD or TCDD Tasimacilik A.S. in any way. Use responsibly and in accordance with TCDD's terms of service. The author assumes no liability for any misuse of this tool.
