# login_once_and_save.py
from playwright.sync_api import sync_playwright
import time, json, os


print("Opening browser – log in normally (you will receive SMS)")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)   # you see the browser
    context = browser.new_context()
    page = context.new_page()
    
    page.goto("https://major.cshub.ir/professor-search")
    page.wait_for_url("**/professor-search", timeout=60000)  # wait up to 1 min
    
    input("After you receive SMS and are fully logged in → press Enter here...")
    
    # Save everything: cookies + localStorage + sessionStorage
    storage = context.storage_state(path="cshub_session.json")
    print("Session saved to cshub_session.json – you can close the browser now")
    browser.close()

print("Done! Now run the main scraper – it will never ask for login again")