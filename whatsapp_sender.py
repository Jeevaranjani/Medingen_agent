# whatsapp_sender.py

import time
import urllib.parse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys  # fallback


def send_whatsapp_message(
    to_number: str,
    message: str,
    chrome_profile_path: str = r"C:\Users\djeev\medingen_agent\selenium_profile",
    chrome_profile_dir: str = "Default",
    dry_run: bool = False,
    visible: bool = True,
    wait_for_send_seconds: int = 5,
) -> bool:
    """
    Sends a WhatsApp message using WhatsApp Web.

    Strategy:
    - Use the ?text=... parameter in the URL to pre-fill the message
    - Wait for chat to load
    - CLICK the Send button (more reliable than ENTER)
    """

    if dry_run:
        print("\n[DRY RUN] Not sending WhatsApp message.")
        print("To:", to_number)
        print("Message:", message)
        return True

    # Encode the message and build the URL
    encoded_message = urllib.parse.quote_plus(message)
    url = f"https://web.whatsapp.com/send?phone={to_number}&text={encoded_message}"

    options = Options()

    if not visible:
        options.add_argument("--headless=new")

    # Use dedicated Selenium profile (already logged into WhatsApp Web)
    options.add_argument(f"--user-data-dir={chrome_profile_path}")
    options.add_argument(f"--profile-directory={chrome_profile_dir}")

    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    # Your local ChromeDriver path
    service = Service(r"C:\Users\djeev\medingen_agent\chromedriver.exe")

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)

        wait = WebDriverWait(driver, 40)

        # 1) Wait for the chat textbox so we know the page is ready
        wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "div[contenteditable='true'][data-tab='10'], "
                    "div[contenteditable='true'][role='textbox']",
                )
            )
        )

        # Give WhatsApp a moment to insert the pre-filled text
        time.sleep(12.0)

        # 2) Try to click the Send button
        try:
            send_button = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "button[aria-label='Send'], span[data-icon='send']",
                    )
                )
            )
            send_button.click()
        except Exception as e:
            print("[WARN] Failed to click Send button:", e)
            return False

        time.sleep(wait_for_send_seconds)
        print("[INFO] WhatsApp message sent successfully to pharmacist team.")
        return True

    except Exception as e:
        print("[ERROR] WhatsApp error:", e)
        return False

    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
