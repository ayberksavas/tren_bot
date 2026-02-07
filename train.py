import time
import re
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# --- CONFIGURATION ---
FROM_STATION = "ANKARA GAR , ANKARA"                # Must match the exact name on the website
TO_STATION = "İSTANBUL(SÖĞÜTLÜÇEŞME) , İSTANBUL"    # Must match the exact name on the website
TRAVEL_DAY = 9               # Day of the month to pick from the calendar (e.g. 9 for the 9th)
CHECK_EVERY_MINUTES = 15     # Base wait time

# Time filter: only check trains departing within this window (24h format)
# Set to None to ignore
EARLIEST_DEPARTURE = "06:00"   # e.g. "08:00" or None for no lower bound
LATEST_DEPARTURE = "23:59"     # e.g. "14:00" or None for no upper bound

# Minimum available seats to trigger an alert
# Set to 3 to ignore the 2 disabled-person seats that are usually shown
MIN_SEATS = 3

# --- EMAIL NOTIFICATION ---
BOT_EMAIL = "your-bot@gmail.com"              # Gmail address to send from
BOT_APP_PASSWORD = "xxxx xxxx xxxx xxxx"       # Gmail App Password (16-char)
NOTIFY_EMAIL = "your-email@gmail.com"          # Email to receive alerts

# --- TEST MODE ---
TEST_MODE = False  # Set to False for automated loop

def create_driver():
    """Creates a browser instance with 'human' settings using undetected-chromedriver."""
    options = uc.ChromeOptions()
    # Use Brave browser (Chromium-based)
    options.binary_location = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

    # options.add_argument("--headless")  # Uncomment to run in background (invisible)

    # undetected-chromedriver auto-downloads matching driver and handles anti-detection
    driver = uc.Chrome(options=options, version_main=143)
    return driver

def debug_find_elements(driver):
    """Helper function to find form elements - run this first to identify correct selectors."""
    print("\n" + "="*60)
    print("DEBUG MODE: Finding form elements...")
    print("="*60)

    # Look for input fields
    inputs = driver.find_elements(By.TAG_NAME, "input")
    print(f"\nFound {len(inputs)} input elements:")
    for i, inp in enumerate(inputs):
        inp_id = inp.get_attribute("id")
        inp_name = inp.get_attribute("name")
        inp_placeholder = inp.get_attribute("placeholder")
        inp_type = inp.get_attribute("type")
        visible = inp.is_displayed()
        if inp_id or inp_name or inp_placeholder:
            print(f"  [{i}] id='{inp_id}', name='{inp_name}', placeholder='{inp_placeholder}', type='{inp_type}', visible={visible}")

    # Look for buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")
    print(f"\nFound {len(buttons)} button elements:")
    for i, btn in enumerate(buttons):
        btn_id = btn.get_attribute("id")
        btn_text = btn.text[:50] if btn.text else ""
        btn_class = btn.get_attribute("class")
        print(f"  [{i}] id='{btn_id}', text='{btn_text}', class='{btn_class[:50] if btn_class else ''}'")

    # Look for dropdown/autocomplete related elements
    print(f"\nDropdown-related elements:")
    for selector in ["[class*='dropdown']", "[class*='autocomplete']", "[class*='p-overlay']", "[role='listbox']"]:
        els = driver.find_elements(By.CSS_SELECTOR, selector)
        if els:
            print(f"  '{selector}': found {len(els)} elements")
            for j, el in enumerate(els[:3]):
                print(f"    [{j}] tag={el.tag_name}, class='{(el.get_attribute('class') or '')[:80]}', visible={el.is_displayed()}")

    print("\n" + "="*60)
    print("Debug info printed above. Continuing with form fill...")
    print("="*60 + "\n")

def select_station(driver, input_id, station_name):
    """
    Handles the TCDD custom dropdown.
    Clicks the station input, types the name, then clicks the matching
    autocomplete result button directly.
    """
    wait = WebDriverWait(driver, 15)

    # 1. Click to open dropdown
    print(f"[...] Selecting {station_name}...")
    input_box = wait.until(EC.element_to_be_clickable((By.ID, input_id)))
    input_box.click()
    time.sleep(2)

    # 2. Type station name character by character
    for char in station_name:
        driver.switch_to.active_element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))
    print(f"  -> Typed: {station_name}")

    # 3. Wait for autocomplete results to filter
    time.sleep(2)

    # 4. Find and click the matching autocomplete result button
    # Results are <button> elements whose text contains the station name
    search_upper = station_name.upper()
    buttons = driver.find_elements(By.TAG_NAME, "button")
    clicked = False
    for btn in buttons:
        if btn.is_displayed() and search_upper in (btn.text or "").upper():
            driver.execute_script("arguments[0].click();", btn)
            print(f"  -> Clicked: '{btn.text.strip()[:50]}'")
            clicked = True
            break

    if not clicked:
        # Fallback: Tab + Enter (works for the first station)
        print(f"  -> No matching button found, trying Tab+Enter...")
        driver.switch_to.active_element.send_keys(Keys.TAB)
        time.sleep(0.5)
        driver.switch_to.active_element.send_keys(Keys.ENTER)

    time.sleep(1)
    print(f"[OK] Selected: {station_name}")

def time_in_range(dep_time_str):
    """Check if a departure time like '08:40' falls within EARLIEST/LATEST config."""
    if not EARLIEST_DEPARTURE and not LATEST_DEPARTURE:
        return True
    try:
        h, m = map(int, dep_time_str.split(":"))
        dep_mins = h * 60 + m
        if EARLIEST_DEPARTURE:
            eh, em = map(int, EARLIEST_DEPARTURE.split(":"))
            if dep_mins < eh * 60 + em:
                return False
        if LATEST_DEPARTURE:
            lh, lm = map(int, LATEST_DEPARTURE.split(":"))
            if dep_mins > lh * 60 + lm:
                return False
        return True
    except:
        return True

def send_email(subject, body):
    """Send an email notification via Gmail SMTP."""
    try:
        msg = MIMEMultipart()
        msg["From"] = BOT_EMAIL
        msg["To"] = NOTIFY_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(BOT_EMAIL, BOT_APP_PASSWORD)
            server.sendmail(BOT_EMAIL, NOTIFY_EMAIL, msg.as_string())

        print(f"[EMAIL] Notification sent to {NOTIFY_EMAIL}")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send: {e}")


def check_results(driver, page_text):
    """
    Parse train result cards. Each card's text looks like:
      YHT: 81003 ANKARA - İSTANBUL
      Daha fazla bilgi
      ANKARA GAR   BOZÜYÜK YHT
      06:50 ... 08:31
      ...
      ₺540,00
      (4)     <-- seat count

    We extract departure time and seat count from each card.
    """
    # Get the full page text and split into lines for parsing
    lines = page_text.split("\n")

    # Find all departure times and seat counts
    # Departure times: standalone HH:MM on a line, from the departure station column
    # Seat counts: (N) pattern
    trains = []
    current_train = None

    for line in lines:
        line = line.strip()

        # Detect train header like "YHT: 81003 ANKARA - İSTANBUL"
        if line.startswith("YHT:") or line.startswith("ANAHAT:"):
            current_train = {"name": line, "dep_time": None, "seats": 0}
            continue

        # Detect departure time (HH:MM format, standalone or first on line)
        time_match = re.match(r'^(\d{2}:\d{2})$', line)
        if time_match and current_train and not current_train["dep_time"]:
            current_train["dep_time"] = time_match.group(1)
            continue

        # Detect seat count like (2), (4), (12)
        seat_match = re.match(r'^\((\d+)\)$', line)
        if seat_match and current_train:
            current_train["seats"] = int(seat_match.group(1))
            trains.append(current_train)
            current_train = None
            continue

    if not trains:
        print("[--] Could not parse any train cards from the results page.")
        if TEST_MODE:
            print("[DEBUG] Page text preview:")
            print(page_text[:1000])
        return

    # Display all trains
    print(f"\n{'='*60}")
    print(f"  Found {len(trains)} trains")
    print(f"{'='*60}")

    found_seats = False
    for t in trains:
        dep = t["dep_time"] or "??:??"
        seats = t["seats"]
        name = t["name"]

        # Check time filter
        in_range = time_in_range(dep)
        time_flag = "" if in_range else " [outside time range]"

        # Check seat threshold
        if seats >= MIN_SEATS and in_range:
            print(f"  !!! {dep} | {seats} seats | {name}{time_flag}")
            found_seats = True
        else:
            print(f"      {dep} | {seats} seats | {name}{time_flag}")

    print(f"{'='*60}")

    if found_seats:
        print(f"\n[ALERT] TICKETS AVAILABLE (>= {MIN_SEATS} seats)!")
        print("!!! GO BOOK NOW !!!")

        # Build email body with matching trains
        matching = [t for t in trains if t["seats"] >= MIN_SEATS and time_in_range(t["dep_time"] or "")]
        email_lines = [f"Bilet bulundu! {FROM_STATION} -> {TO_STATION}\n"]
        for t in matching:
            email_lines.append(f"  {t['dep_time']} | {t['seats']} koltuk | {t['name']}")
        email_lines.append(f"\nhttps://ebilet.tcddtasimacilik.gov.tr/")
        email_body = "\n".join(email_lines)

        send_email(
            f"TCDD Bilet Bulundu! {FROM_STATION} -> {TO_STATION}",
            email_body
        )

        if TEST_MODE:
            input("\nPress ENTER to close browser...")
        return True
    else:
        print(f"\n[--] No trains with >= {MIN_SEATS} seats in the time range.")
        return False


def check_tickets():
    driver = create_driver()
    try:
        print("Opening TCDD Website...")
        driver.get("https://ebilet.tcddtasimacilik.gov.tr/")

        wait = WebDriverWait(driver, 15)

        # Wait for page to fully load
        time.sleep(3)

        # In test mode, run debug to find elements first
        if TEST_MODE:
            debug_find_elements(driver)

        # --- FILL FORM ---
        # 1. Select Departure
        select_station(driver, "fromTrainInput", FROM_STATION)

        # Click body to reset focus/close any open dropdown before next station
        driver.find_element(By.TAG_NAME, "body").click()
        time.sleep(2)

        # 2. Select Arrival
        select_station(driver, "toTrainInput", TO_STATION)
        time.sleep(2)  # Wait for dropdown to fully close

        # 3. Set Date by clicking the day in the calendar popup
        date_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='GidişTarihi']")
        driver.execute_script("arguments[0].click();", date_input)
        time.sleep(1.5)  # Wait for calendar popup to open

        # Find all visible elements with the day number text and click the first
        # clickable one (past dates are greyed out, first match = closest future date)
        day_str = str(TRAVEL_DAY)
        clicked = False

        # Calendar day cells are typically <td>, <span>, <div>, or <a> elements
        for tag in ["td", "span", "div", "a", "button"]:
            if clicked:
                break
            elements = driver.find_elements(By.TAG_NAME, tag)
            for el in elements:
                if el.is_displayed() and el.text.strip() == day_str:
                    # Skip elements that look disabled/greyed out
                    cls = (el.get_attribute("class") or "").lower()
                    if "disabled" in cls or "passive" in cls or "old" in cls:
                        continue
                    driver.execute_script("arguments[0].click();", el)
                    print(f"[OK] Date: clicked day {TRAVEL_DAY}")
                    clicked = True
                    break

        if not clicked:
            print(f"[WARNING] Could not find day {TRAVEL_DAY} in the calendar")

        time.sleep(1)

        # 4. Click Search (use JavaScript to avoid overlay issues)
        search_btn = driver.find_element(By.ID, "searchSeferButton")
        driver.execute_script("arguments[0].click();", search_btn)

        # --- CHECK RESULTS ---
        print("[...] Searching for available seats...")
        time.sleep(7)  # Give page time to load results

        page_text = driver.find_element(By.TAG_NAME, "body").text

        if "sefer bulunamadı" in page_text.lower() or "sonuç bulunamadı" in page_text.lower():
            print("[--] No trains found for this route/date.")
            return False
        else:
            return check_results(driver, page_text)

    except Exception as e:
        print(f"[WARNING] An error occurred: {e}")
        return False
    finally:
        driver.quit()

# --- MAIN LOOP ---
if __name__ == "__main__":
    from datetime import datetime

    if TEST_MODE:
        print("\n*** RUNNING IN TEST MODE (single run) ***\n")
        check_tickets()
        print("\n*** TEST COMPLETE ***")
        print("If selectors worked, set TEST_MODE = False to enable automated checking.")
    else:
        attempt = 0
        print(f"\n{'='*60}")
        print(f"  TCDD Ticket Monitor Started")
        print(f"  {FROM_STATION} -> {TO_STATION} | Day: {TRAVEL_DAY}")
        print(f"  Time range: {EARLIEST_DEPARTURE or 'any'} - {LATEST_DEPARTURE or 'any'}")
        print(f"  Min seats: {MIN_SEATS} | Check every ~{CHECK_EVERY_MINUTES} min")
        print(f"  Notifications -> {NOTIFY_EMAIL}")
        print(f"{'='*60}\n")

        while True:
            attempt += 1
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{now}] --- Check #{attempt} ---")

            found = check_tickets()

            if found:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tickets found! Stopping monitor.")
                break

            # Randomized sleep: base ± 30% + random extra 0-120s
            # e.g. 15 min base -> anywhere from ~10.5 to ~21.5 min
            base_seconds = CHECK_EVERY_MINUTES * 60
            jitter = random.uniform(-0.3, 0.3) * base_seconds
            extra = random.uniform(0, 120)
            sleep_time = base_seconds + jitter + extra

            next_check = datetime.now().strftime("%H:%M:%S")
            mins = int(sleep_time // 60)
            secs = int(sleep_time % 60)
            print(f"[{next_check}] Next check in ~{mins}m {secs}s")
            time.sleep(sleep_time)
