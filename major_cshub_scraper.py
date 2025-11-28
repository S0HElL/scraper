from playwright._impl._errors import TimeoutError
from playwright.sync_api import sync_playwright
import csv
import time

OUTPUT_CSV = "professors.csv"

# -------------------------------------------
# Utility: clean major titles
# -------------------------------------------
def clean_major(title):
    return title.replace("لیست اساتید گرایش", "").strip()


# -------------------------------------------
# Utility: click an element containing text
# -------------------------------------------
def click_by_text(page, text):
    page.locator(f"text={text}").first.click()


# -------------------------------------------
# Utility: select dropdowns that accept typing
# -------------------------------------------
def fill_dropdown(page, placeholder, value):
    box = page.locator(f"input[placeholder='{placeholder}']")
    box.click()
    box.fill(value)
    
    # The menu needs a space press to show suggestions/register the input.
    time.sleep(4.0)
    page.keyboard.press("Space")
    
    # Wait for the suggestion (which contains the university name text) to appear, then click it.
    # The locator will target the first visible element containing the university name text.
    suggestion_locator = page.locator(f"text={value}").first
    
    # Wait for the suggestion to be visible and then click it.
    try:
        suggestion_locator.wait_for(state="visible", timeout=3000)
        suggestion_locator.click()
    except TimeoutError:
        # If the click fails, we print a warning and let the script continue.
        print(f"Warning: Timeout or element not found for university suggestion: {value}")

    time.sleep(1.0) # Delay after selection


# -------------------------------------------
# Scrape professor card (REPLACEMENT - more robust)
# -------------------------------------------
def parse_professor(p):
    # NAME: try several patterns
    name = ""
    try:
        name = p.locator('span:has-text("نام استاد:") + span').first.inner_text().strip()
    except Exception:
        pass
    if not name:
        try:
            name = p.locator("div:has-text('نام:') + div").first.inner_text().strip()
        except Exception:
            pass
    if not name:
        try:
            name = p.locator("h3, h2, .result-professor__name, .card-title").first.inner_text().strip()
        except Exception:
            name = ""

    # MAJORs inside the card (some cards include their own گرایش)
    majors = ""
    try:
        majors_list = []
        # try label + spans
        for s in p.locator('span:has-text("گرایش:") + span, div:has-text("گرایش:") span').all():
            t = s.inner_text().strip()
            if t:
                majors_list.append(t)
        if not majors_list:
            # fallback: any inline tag that looks like a major
            for s in p.locator('.prof-major, .major-tag, .result-professor__branch').all():
                t = s.inner_text().strip()
                if t:
                    majors_list.append(t)
        majors = " ".join(dict.fromkeys([m for m in majors_list if m]))
    except Exception:
        majors = ""

    # H-INDEX: امتیاز علمی
    h_index = ""
    try:
        h_el = p.locator('span:has-text("امتیاز علمی:") + span, div:has-text("امتیاز علمی")').first
        if h_el:
            txt = h_el.inner_text().strip()
            digits = "".join([c for c in txt if c.isdigit()])
            h_index = digits or txt
    except Exception:
        h_index = ""

    # PROFILE URL: prefer anchors linking to /fa/as or containing 'لینک' text
    profile_url = ""
    try:
        a = p.locator('a[href*="/fa/as"], a[href*="/as/"], a:has-text("لینک صفحه"), a:has-text("لینک")').first
        if a:
            href = a.get_attribute("href") or ""
            profile_url = href.strip()
    except Exception:
        profile_url = ""

    # EMAIL: mailto href or visible email text
    email = ""
    try:
        mail = p.locator('a[href^="mailto:"], a:has-text("ایمیل")').first
        if mail:
            href = mail.get_attribute("href") or ""
            if href.startswith("mailto:"):
                email = href.replace("mailto:", "").strip()
            else:
                # fallback: inner text might be the email
                email = mail.inner_text().strip()
    except Exception:
        email = ""

    # FIELDS / research tags - multiple possible selectors
    fields = []
    try:
        for item in p.locator('.result-professor__research-value span, .research-tag, div:has-text("حوزه") span, .chip').all():
            t = item.inner_text().strip()
            if t:
                fields.append(t)
    except Exception:
        pass
    fields_str = ", ".join(dict.fromkeys([f for f in fields if f]))

    return name, majors, h_index, profile_url, email, fields_str

# -------------------------------------------
# MAIN
# -------------------------------------------
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="cshub_session.json")
        page = context.new_page()

        page.goto("https://major.cshub.ir/professor-search")
        page.wait_for_timeout(1500)

        # Click advanced search
        page.locator("li[title='جستجوی پیشرفته']").click()
        page.wait_for_timeout(1000)

        universities = ["دانشگاه تهران"]  # Add more later

        # CSV header
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Name", "University", "Majors", "h-index",
                "Profile URL", "Email", "Fields"
            ])

        for uni in universities:
            print(f"\n=== Starting university: {uni} ===")

            # ---- Fill dropdowns ----
            fill_dropdown(page, "نام دانشگاه مورد نظر را وارد کنید", uni)

            # ----------------------------------------------------------------
            # --------------------  CRITICAL PATCH START  --------------------
            # ----------------------------------------------------------------

            # Blur dropdowns to allow the search button to be clickable
            page.locator("body").click(position={"x": 10, "y": 10})
            page.wait_for_timeout(300)


            # --- CLICK THE BLUE SEARCH BUTTON (NUCLEAR GUARANTEED CLICK) ---

            print("  → Locating the search button…")

            button_selector = "button:has-text('جستجوی موارد انتخاب شده')"

            # Wait for it to be visible (even if disabled)
            page.wait_for_selector(button_selector, state="visible", timeout=15000)
            btn = page.locator(button_selector)

            print("  → Found button. Forcing scroll…")
            btn.scroll_into_view_if_needed()

            # Try normal click
            try:
                btn.click(timeout=4000)
                print("  → Normal click succeeded.")
            except Exception as e:
                print("  → Normal click failed:", e)

                # Force-enabled (Angular often marks button disabled)
                print("  → Attempting to force-enable...")
                page.evaluate("""
                    sel => {
                        const b = document.querySelector(sel);
                        if (b) { b.disabled = false; b.removeAttribute('disabled'); }
                    }
                """, button_selector)

                page.wait_for_timeout(200)

                # Try forced click
                try:
                    print("  → Trying forced click()…")
                    btn.click(force=True, timeout=4000)
                    print("  → Forced click succeeded.")
                except Exception as e2:
                    print("  → Forced click failed:", e2)

                    # Final fallback: direct DOM dispatch
                    print("  → Trying DOM click injection…")
                    page.evaluate("""
                        sel => {
                            const b = document.querySelector(sel);
                            if (b) {
                                b.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                                b.dispatchEvent(new MouseEvent('mouseup',   { bubbles: true }));
                                b.dispatchEvent(new MouseEvent('click',     { bubbles: true }));
                            }
                        }
                    """, button_selector)

                    print("  → DOM event click dispatched.")


            page.wait_for_timeout(1200)

            # Scroll down to ensure the professors are in the viewport and to move past the search menu
            print("  → Scrolling down to view results...")
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(500)

            # ----------------------------------------------------------------
            # --------------------  CRITICAL PATCH END    --------------------
            # ----------------------------------------------------------------

            # ---- Find all major groups (robust, scoped to results_section) ----

            # Wait for the results container area to appear
            RESULTS_TITLE_SELECTOR = "div:has-text('نتایج جستجو')"
            try:
                page.wait_for_selector(RESULTS_TITLE_SELECTOR, state="visible", timeout=60000)
            except TimeoutError:
                print(f"  → No results section found or timeout for university: {uni}")
                continue

            page.wait_for_timeout(500)  # let things settle

            results_section = page.locator(RESULTS_TITLE_SELECTOR).first

            # Find major header/buttons inside results_section only
            # Look for text nodes that include "لیست اساتید گرایش" or "گرایش"
            major_candidates = results_section.locator("text=لیست اساتید گرایش, text=گرایش, .mat-expansion-panel-header, .result-branch-title, button")

            major_texts = []
            # collect only candidates that are likely to open professor lists
            for el in major_candidates.all():
                t = ""
                try:
                    t = el.inner_text().strip()
                except Exception:
                    continue
                if not t:
                    continue
                # require the string to contain 'گرایش' or start with 'لیست اساتید'
                if "گرایش" in t or "لیست اساتید" in t:
                    major_texts.append(t)

            # dedupe while preserving order
            seen = set()
            major_texts_unique = []
            for t in major_texts:
                if t not in seen:
                    seen.add(t)
                    major_texts_unique.append(t)

            print(f"  → Found {len(major_texts_unique)} major groups (scoped).")

            # ---- Process each major: click it, wait for its cards, scrape scoped cards ----
            PROFESSOR_CARD_SELECTOR = "div.card.bg-base-100.shadow-xl.mb-4, .result-professor"

            for major_title in major_texts_unique:
                cleaned = clean_major(major_title)
                print(f"    -> Opening major: {cleaned}")

                # find the exact element in results_section and click it (try multiple fallbacks)
                clicked = False
                try:
                    mbtn = results_section.locator(f"button:has-text('{major_title}'), text={major_title}").first
                    if mbtn.count() > 0:
                        try:
                            mbtn.click(force=True)
                        except Exception:
                            # ensure visible then DOM click
                            handle = mbtn.element_handle()
                            if handle:
                                page.evaluate("el => el.click()", handle)
                        clicked = True
                except Exception:
                    clicked = False

                # If click not successful, try clicking by partial text match or index
                if not clicked:
                    try:
                        alt = results_section.locator(f"text={major_title}").first
                        if alt.count() > 0:
                            try:
                                alt.click(force=True)
                                clicked = True
                            except Exception:
                                handle = alt.element_handle()
                                if handle:
                                    page.evaluate("el => el.click()", handle)
                                    clicked = True
                    except Exception:
                        clicked = False

                if not clicked:
                    print(f"      → Warning: couldn't click major element for '{major_title}'. Skipping.")
                    continue

                # Wait for professor cards to appear; allow multiple pages inside the major
                try:
                    page.wait_for_selector(PROFESSOR_CARD_SELECTOR, state="visible", timeout=10000)
                except TimeoutError:
                    print(f"      → No professor cards found for major: {cleaned} (Timeout)")
                    continue

                # After expanding the major, gather visible professor cards (scoped)
                prof_cards = page.locator(PROFESSOR_CARD_SELECTOR).filter(has=results_section).filter(has=page.locator(f"text={cleaned}").first) \
                              if page.locator(f"text={cleaned}").count() > 0 else page.locator(PROFESSOR_CARD_SELECTOR).filter(has=results_section)

                # fallback: if the above scoping returns 0, just take visible prof cards in results_section
                if prof_cards.count() == 0:
                    prof_cards = results_section.locator(PROFESSOR_CARD_SELECTOR).filter(has=results_section)

                total = prof_cards.count()
                print(f"      → Found {total} professor cards for '{cleaned}'.")

                for i in range(total):
                    pcard = prof_cards.nth(i)
                    try:
                        name, majors, h_index, profile_url, email, fields = parse_professor(pcard)
                        with open(OUTPUT_CSV, "a", newline="", encoding="utf-8-sig") as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                name, uni, majors or cleaned, h_index,
                                profile_url, email, fields
                            ])
                    except Exception as e:
                        print("      → Error parsing professor:", type(e).__name__, e)
                        continue

                # small pause before proceeding to next major
                page.wait_for_timeout(500)


        print("\n=== Finished ===")
        browser.close()


if __name__ == "__main__":
    main()
