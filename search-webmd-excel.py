# WebMD Excel Link Matching Pipeline

import pandas as pd
from playwright.sync_api import sync_playwright
from rapidfuzz import fuzz
import urllib.parse
import re

# ============================================================
# FILES
# ============================================================

INPUT_FILE = "input1.xlsx"
OUTPUT_FILE = "output_with_links.xlsx"

# ============================================================
# NORMALIZATION FUNCTIONS
# ============================================================

def norm_name(n):

    n = str(n).upper().strip()

    # remove titles
    n = re.sub(r"\b(MD|DO|DR)\b", "", n)

    # LAST, FIRST -> FIRST LAST
    if "," in n:

        parts = [p.strip() for p in n.split(",")]

        if len(parts) >= 2:

            last = parts[0]
            first = parts[1]

            n = f"{first} {last}"

    # remove punctuation
    n = re.sub(r"[^\w\s]", " ", n)

    return " ".join(n.split())


def norm_address(a):

    a = str(a).upper()

    # remove suite/unit indicators
    a = re.sub(r"\b(SUITE|STE|UNIT|#)\s*\w*", "", a)

    replacements = {
        "EAST": "E",
        "WEST": "W",
        "NORTH": "N",
        "SOUTH": "S",
        "BOULEVARD": "BLVD",
        "AVENUE": "AVE",
        "DRIVE": "DR",
        "STREET": "ST",
        "ROAD": "RD",
        "LANE": "LN",
    }

    for k, v in replacements.items():
        a = a.replace(k, v)

    # remove punctuation
    a = re.sub(r"[^\w\s]", " ", a)

    return " ".join(a.split())


def norm_state(s):

    return str(s).replace(",", "").strip().upper()

# ============================================================
# GOOGLE SEARCH FUNCTION
# ============================================================

def search_webmd(page, addr, state):

    query = urllib.parse.quote(
        f'site:doctor.webmd.com "{addr}" "{state}"'
    )

    google_url = (
        f"https://www.google.com/search?q={query}"
    )

    print(f"\nSearching Google:\n{google_url}")

    page.goto(
        google_url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(5000)

    links = []

    # only organic results
    results = page.locator("div.yuRUbf a")

    for i in range(results.count()):

        href = results.nth(i).get_attribute("href")

        if not href:
            continue

        if "doctor.webmd.com" in href:
            links.append(href)

    # remove duplicates
    links = list(dict.fromkeys(links))

    return links

# ============================================================
# MATCHING FUNCTION
# ============================================================

def find_best_webmd_link(
    page,
    external_name,
    external_addr,
    external_state
):

    query_name = norm_name(external_name)
    query_addr = norm_address(external_addr)
    query_state = norm_state(external_state)

    best_score = 0
    best_link = ""

    # ========================================================
    # GET TOP 5 GOOGLE RESULTS
    # ========================================================

    candidate_links = search_webmd(
        page,
        external_addr,
        external_state
    )[:5]

    print("\nTop Candidate Links:\n")

    for link in candidate_links:
        print(link)

    # ========================================================
    # CHECK EACH LINK
    # ========================================================

    for URL in candidate_links:

        print(f"\nChecking: {URL}")

        try:

            page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(2000)

            # ------------------------------------------------
            # STATES
            # ------------------------------------------------

            if (
                page.locator(".loc-coi-locsta")
                .count() == 0
            ):
                continue

            states = page.locator(
                ".loc-coi-locsta"
            )

            state_list = [
                states.nth(i)
                .inner_text()
                .strip()
                for i in range(states.count())
            ]

            normalized_states = [
                norm_state(s)
                for s in state_list
            ]

            # skip state mismatch pages
            if query_state not in normalized_states:
                continue

            # ------------------------------------------------
            # ENTITY NAME
            # ------------------------------------------------

            page_names = []

            # facility
            if (
                page.locator("h3.facility-name")
                .count() > 0
            ):

                page_names = [
                    norm_name(x)
                    for x in page.locator(
                        "h3.facility-name"
                    ).all_inner_texts()
                ]

            # doctor
            elif (
                page.locator(
                    "h1.provider-full-name"
                ).count() > 0
            ):

                provider_name = (
                    page.locator(
                        "h1.provider-full-name"
                    )
                    .inner_text()
                    .strip()
                )

                page_names = [
                    norm_name(provider_name)
                ]

            # ------------------------------------------------
            # NAME SCORE
            # ------------------------------------------------

            best_name_score = 0

            for pname in page_names:

                score = fuzz.token_set_ratio(
                    query_name,
                    pname
                )

                if score > best_name_score:
                    best_name_score = score

            # ------------------------------------------------
            # ADDRESSES
            # ------------------------------------------------

            if (
                page.locator(".loc-coi-locad")
                .count() == 0
            ):
                continue

            locations = page.locator(
                ".loc-coi-locad"
            )

            location_list = [
                locations.nth(i)
                .inner_text()
                .strip()
                for i in range(locations.count())
            ]

            # ------------------------------------------------
            # ADDRESS MATCHING
            # ------------------------------------------------

            for addr, state in zip(
                location_list,
                state_list
            ):

                norm_addr = norm_address(addr)
                norm_st = norm_state(state)

                # compare only same state
                if norm_st != query_state:
                    continue

                addr_score = fuzz.token_set_ratio(
                    query_addr,
                    norm_addr
                )

                # combined score
                final_score = (
                    addr_score * 0.7
                    + best_name_score * 0.3
                )

                print(
                    f"Address Score: {addr_score} | "
                    f"Name Score: {best_name_score} | "
                    f"Final Score: {final_score}"
                )

                if final_score > best_score:

                    best_score = final_score
                    best_link = URL

                    # early stop
                    if best_score >= 95:
                        break

            if best_score >= 95:
                break

        except Exception as e:

            print(f"Error checking {URL}: {e}")
            continue

    # ========================================================
    # RETURN FINAL LINK
    # ========================================================

    if best_score >= 85:
        return best_link

    return ""

# ============================================================
# LOAD INPUT FILE
# ============================================================

print("\nLoading Excel file...\n")

df = pd.read_excel(INPUT_FILE)

# create output column
if "link" not in df.columns:
    df["link"] = ""

# ============================================================
# PLAYWRIGHT SESSION
# ============================================================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled"
        ]
    )

    page = browser.new_page(
        user_agent=(
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/122.0.0.0 "
            "Safari/537.36"
        )
    )

    # stealth patch
    page.add_init_script("""

    Object.defineProperty(
        navigator,
        'webdriver',
        {
            get: () => undefined
        }
    );

    """)

    # ========================================================
    # PROCESS EACH ROW
    # ========================================================

    for idx, row in df.iterrows():

        print("\n================================================")
        print(f"ROW {idx + 1}")
        print("================================================")

        external_name = str(row["CUSTOMER_NAME"])
        external_addr = str(row["CUST_ADDRESS"])
        external_state = str(row["CUST_STATE"])

        print(f"Name   : {external_name}")
        print(f"Address: {external_addr}")
        print(f"State  : {external_state}")

        try:

            final_link = find_best_webmd_link(
                page,
                external_name,
                external_addr,
                external_state
            )

            df.at[idx, "link"] = final_link

            print(f"\nFINAL LINK: {final_link}")

        except Exception as e:

            print(f"\nERROR: {e}")
            df.at[idx, "link"] = ""

    browser.close()

# ============================================================
# SAVE OUTPUT
# ============================================================

print("\nSaving output file...\n")

df.to_excel(
    OUTPUT_FILE,
    index=False
)

print(f"\nDone. Output saved as: {OUTPUT_FILE}")

