from playwright._impl._errors import TimeoutError
from playwright.sync_api import sync_playwright
import json
import time

OUTPUT_JSONL = "professors.jsonl"

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
# Scrape professor card - FIXED VERSION
# -------------------------------------------
def parse_professor(p):
    """
    Parse a single professor card and extract relevant information.
    Each card should be a discrete div.card element.
    """
    # NAME: Look for the professor's name
    name = ""
    try:
        # Try specific selector for professor name
        name_elem = p.locator('span:has-text("نام استاد:") + span, .professor-name, h3, h2').first
        name = name_elem.inner_text().strip()
        # Clean up if it includes "نام استاد:"
        if "نام استاد:" in name:
            name = name.replace("نام استاد:", "").strip()
    except Exception:
        name = ""

    # MAJOR: Look for the major/field within this specific card
    majors = ""
    try:
        # Try to get sub-majors (گرایش) which are now a list of spans with class result-professor__group-value
        sub_major_elems = p.locator('.result-professor__group-value').all()
        sub_majors = [elem.inner_text().strip() for elem in sub_major_elems if elem.inner_text().strip()]
        if sub_majors:
            majors = ", ".join(sub_majors)
        
        # Fallback to the main major (رشته) if no sub-majors are found
        if not majors:
            field_elem = p.locator('span:has-text("رشته:") + span').first
            majors = field_elem.inner_text().strip()
            if "رشته:" in majors:
                majors = majors.replace("رشته:", "").strip()

    except Exception:
        majors = ""

    # H-INDEX: امتیاز علمی
    h_index = ""
    try:
        h_elem = p.locator('span:has-text("امتیاز علمی:") + span').first
        h_text = h_elem.inner_text().strip()
        # Extract only digits
        h_index = "".join([c for c in h_text if c.isdigit()])
    except Exception:
        h_index = ""

    # PROFILE URL
    profile_url = ""
    try:
        link = p.locator('a[href*="/fa/as"], a[href*="/as/"], a:has-text("لینک")').first
        href = link.get_attribute("href") or ""
        profile_url = href.strip()
    except Exception:
        profile_url = ""

    # EMAIL
    email = ""
    try:
        mail = p.locator('a[href^="mailto:"]').first
        href = mail.get_attribute("href") or ""
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").strip()
    except Exception:
        email = ""

    # RESEARCH FIELDS
    fields = []
    try:
        # Look for research field tags/chips within this card only
        for item in p.locator('.result-professor__research-value').all():
            t = item.inner_text().strip()
            if t and len(t) < 100:  # Avoid capturing giant text blocks
                fields.append(t)
    except Exception:
        pass
    
    # Deduplicate fields and return the list
    fields = list(dict.fromkeys([f for f in fields if f]))

    return name, majors, h_index, profile_url, email, fields


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
        page.wait_for_timeout(3000)

        universities = ["دانشگاه تهران"]  # Add more later

        all_professors = {} # Dictionary to store unique professors, keyed by name

        for uni in universities:
            print(f"\n=== Starting university: {uni} ===")

            # ---- Fill dropdowns ----
            fill_dropdown(page, "نام دانشگاه مورد نظر را وارد کنید", uni)

            # Blur dropdowns to allow the search button to be clickable
            page.locator("body").click(position={"x": 10, "y": 10})
            page.wait_for_timeout(300)

            # --- CLICK THE BLUE SEARCH BUTTON ---
            print("  → Locating the search button…")
            button_selector = "button:has-text('جستجوی موارد انتخاب شده')"

            # Wait for it to be visible
            page.wait_for_selector(button_selector, state="visible", timeout=15000)
            btn = page.locator(button_selector)

            print("  → Found button. Forcing scroll…")
            try:
                handle = btn.element_handle()
                if handle:
                    page.evaluate("el => el.scrollIntoView({block: 'center'})", handle)
                else:
                    btn.scroll_into_view_if_needed()
            except Exception:
                try:
                    btn.scroll_into_view_if_needed()
                except Exception:
                    pass

            # Try normal click
            clicked = False
            try:
                btn.click(timeout=4000)
                print("  → Normal click succeeded.")
                clicked = True
            except Exception as e:
                print("  → Normal click failed:", e)

            if not clicked:
                # Force-enabled (Angular often marks button disabled)
                print("  → Attempting to force-enable...")
                try:
                    page.evaluate("""
                        sel => {
                            const b = document.querySelector(sel);
                            if (b) { b.disabled = false; b.removeAttribute('disabled'); b.setAttribute('aria-disabled', 'false'); }
                        }
                    """, button_selector)
                except Exception:
                    pass

                page.wait_for_timeout(200)

                # Try forced click
                try:
                    print("  → Trying forced click()…")
                    btn.click(force=True, timeout=4000)
                    print("  → Forced click succeeded.")
                    clicked = True
                except Exception as e2:
                    print("  → Forced click failed:", e2)

            if not clicked:
                # Final fallback: direct DOM dispatch
                try:
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
                    clicked = True
                except Exception as e3:
                    print("  → DOM click injection failed:", e3)

            page.wait_for_timeout(1200)

            # Scroll down to view results
            print("  → Scrolling down to view results...")
            try:
                page.mouse.wheel(0, 500)
            except Exception:
                pass
            page.wait_for_timeout(500)

            # Wait for the results container
            RESULTS_TITLE_SELECTOR = "div:has-text('نتایج جستجو')"
            try:
                page.wait_for_selector(RESULTS_TITLE_SELECTOR, state="visible", timeout=60000)
            except TimeoutError:
                print(f"  → No results section found or timeout for university: {uni}")
                continue

            page.wait_for_timeout(500)

            results_section = page.locator(RESULTS_TITLE_SELECTOR).first

            # Find major expansion panels
            major_candidates = results_section.locator("div.professor__list")

            major_texts = []
            for el in major_candidates.all():
                t = ""
                try:
                    title_span = el.locator("span.professor__list-title").first
                    t = title_span.inner_text().strip()
                except Exception:
                    continue
                if t:
                    major_texts.append(t)

            # Dedupe while preserving order
            seen = set()
            major_texts_unique = []
            for t in major_texts:
                if t not in seen:
                    seen.add(t)
                    major_texts_unique.append(t)

            print(f"  → Found {len(major_texts_unique)} major groups.")

            # Process each major
            for major_title in major_texts_unique:
                cleaned = clean_major(major_title)
                print(f" -> Opening major: {cleaned}")

                # پیدا کردن دکمه‌ی باز کردن گرایش
                major_panel = results_section.locator(f"div.professor__list:has-text('{major_title}')").first
                if major_panel.count() == 0:
                    print(f" → Warning: couldn't locate major panel for '{major_title}'. Skipping.")
                    continue

                # اسکرول و کلیک برای باز کردن
                major_panel.scroll_into_view_if_needed()
                page.wait_for_timeout(500)

                try:
                    major_panel.click(timeout=8000)
                    print(f" → Expanded major: {cleaned}")
                    page.wait_for_timeout(1500)  # صبر برای انیمیشن و لود کارت‌ها
                except Exception as e:
                    print(f" → Failed to click major panel: {e}")
                    continue

                # صبر کنیم تا حداقل یک کارت ظاهر شود
                try:
                    page.wait_for_selector("div.professor__details", state="visible", timeout=10000)
                except TimeoutError:
                    print(f" → No professor cards appeared for {cleaned}")
                    # همچنان سعی می‌کنیم ادامه دهیم و گرایش را ببندیم
                    pass
 
                # حالا تمام کارت‌های visible را بگیریم
                cards = page.locator("div.professor__details").filter(has_text=cleaned).all()
                
                if not cards:
                    # اگر فیلتر دقیق کار نکرد، همه کارت‌های visible را بگیریم و دستی چک کنیم
                    print(" → Filter by text failed, using fallback with manual check...")
                    all_visible_cards = page.locator("div.professor__details:visible").all()
                    cards = []
                    for card in all_visible_cards:
                        try:
                            card_text = card.inner_text()
                            if cleaned in card_text or major_title in card_text:
                                cards.append(card)
                        except:
                            continue

                total = len(cards)
                print(f" → Found {total} professor cards for '{cleaned}'.")

                for idx, pcard in enumerate(cards):
                    try:
                        # مطمئن شویم کارت هنوز attached است
                        if not pcard.is_visible():
                            continue

                        name, majors_from_card, h_index, profile_url, email, fields = parse_professor(pcard)

                        # اگر نام داشت، داده‌ها را ذخیره یا ادغام کن
                        if name and name.strip():
                            key = name.strip()  # Use name as a simple key for merging
                            current_major = majors_from_card.strip() or cleaned
                            
                            if key in all_professors:
                                # ادغام: اضافه کردن گرایش جدید و ادغام فیلدهای تحقیقاتی
                                prof_data = all_professors[key]
                                if current_major not in prof_data['major_list']:
                                    prof_data['major_list'].append(current_major)
                                
                                # ادغام فیلدهای تحقیقاتی و حذف تکراری
                                prof_data['research_fields'].extend(fields)
                                prof_data['research_fields'] = list(dict.fromkeys(prof_data['research_fields']))
                                all_professors[key] = prof_data
                                
                                print(f"   [MERGED] {name} with major: {current_major}")
                            else:
                                # افزودن پروفسور جدید
                                all_professors[key] = {
                                    "name": key,
                                    "university": uni,
                                    "major_list": [current_major], # Store as list for merging
                                    "h_index": h_index,
                                    "profile_url": profile_url,
                                    "email": email,
                                    "research_fields": fields,
                                }
                                print(f"   [NEW] Found: {name}")
                        else:
                            print(f"   Skipped card {idx+1}: no name")

                    except Exception as e:
                        print(f"   Error processing card {idx+1}: {e}")
                        continue

                # گرایش را ببندیم تا صفحه شلوغ نشود و کارت‌های بعدی تداخل نکنند
                try:
                    major_panel.click(timeout=5000)
                    page.wait_for_timeout(500)
                except:
                    pass

                page.wait_for_timeout(800)  # فاصله بین گرایش‌ها

        print(f"\n=== Finished scraping: {len(all_professors)} unique professors found ===")
        
        # FINAL WRITE TO JSONL FILE
        professor_count = 0
        with open(OUTPUT_JSONL, "w", encoding="utf-8") as f: # Use "w" to overwrite/create new file
            for key, prof_data in all_professors.items():
                professor_count += 1
                
                # Join major list back into a string as a single 'major' entry
                # NOTE: The original JSONL example showed a single string for major,
                # but the request mentioned "محمد علی اخائی" who is in "شبکه های کامپیوتری, هوش مصنوعی"
                # so I will keep the original request's output structure and join the list of majors.
                # If the user wants an array for majors, they will need to clarify.
                # For now, I will join them into a string as in the original CSV logic, but I will
                # rename the field to "majors" for clarity since it will contain multiple.
                majors_joined = ", ".join(prof_data['major_list'])
                
                data = {
                    "id": professor_count,
                    "name": prof_data['name'],
                    "university": prof_data['university'],
                    "major": majors_joined, # Keep as string to match original structure (unless clarified)
                    "h_index": prof_data['h_index'],
                    "profile_url": prof_data['profile_url'],
                    "email": prof_data['email'],
                    "research_fields": prof_data['research_fields'],
                    "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                json_line = json.dumps(data, ensure_ascii=False)
                f.write(json_line + "\n")

        print(f"=== Finished writing: {professor_count} professors saved to {OUTPUT_JSONL} ===")
        browser.close()


if __name__ == "__main__":
    main()