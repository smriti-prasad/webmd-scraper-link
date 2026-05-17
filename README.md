
# WebMD Entity Resolution Pipeline

A Python-based entity resolution pipeline that maps messy healthcare provider/facility records to accurate WebMD profile URLs.

The project combines:

* Google-based retrieval
* Playwright scraping
* Address normalization
* Fuzzy matching
* State filtering
* Weighted verification scoring

to reliably identify the correct WebMD profile even when input data contains:

* typos
* abbreviations
* formatting inconsistencies
* OCR-style errors
* LAST/FIRST naming formats
* incomplete provider names

---

# Problem Statement

Healthcare datasets are often extremely inconsistent.

A single provider or facility may appear in multiple formats:

```text
ANSARI, AMIR ZIA
Dr. Amir Zia Ansari, MD
AMIR Z ANSARI
```

Similarly, addresses may vary:

```text
2910 E FRANKLIN BLVD # 1
2910 East Franklin Boulevard, Suite 1
```

The goal of this project was to:

```text
Take raw healthcare records from Excel
→ Find the correct WebMD page
→ Return the verified WebMD URL
```

at scale.

---

# Core Workflow

```text
Excel Input
    ↓
Normalize names/addresses/states
    ↓
Google retrieval (WebMD-specific)
    ↓
Fetch top candidate links
    ↓
Scrape candidate pages
    ↓
State filtering
    ↓
Fuzzy name matching
    ↓
Fuzzy address matching
    ↓
Weighted verification scoring
    ↓
Best WebMD URL returned
```

---

# Input Format

The pipeline expects an Excel file (`input1.xlsx`) containing:

| CUSTOMER_NAME    | CUST_ADDRESS             | CUST_STATE |
| ---------------- | ------------------------ | ---------- |
| ANSARI, AMIR ZIA | 2910 E FRANKLIN BLVD # 1 | NC         |

---

# Output Format

The pipeline generates:

```text
output_with_links.xlsx
```

with an additional column:

| link                                                      |
| --------------------------------------------------------- |
| [https://doctor.webmd.com/](https://doctor.webmd.com/)... |

If no strong match is found, the field is left blank.

---

# Technologies Used

* Python
* Playwright
* RapidFuzz
* Pandas
* Google Search Retrieval

---

# Why Google Retrieval Was Used

Initially, the approach attempted direct WebMD search endpoints.

However:

* several endpoints returned 404s
* search result structures were inconsistent
* provider/facility URLs were difficult to infer reliably

Instead, Google search was used as the retrieval layer:

```text
site:doctor.webmd.com "ADDRESS" "STATE"
```

This dramatically improved recall.

Address-driven retrieval turned out to be significantly more reliable than name-driven retrieval because:

* healthcare names are noisy
* addresses are usually stable
* facilities often have inconsistent naming

---

# Key Design Decisions

## 1. Address-Based Retrieval

Early versions relied heavily on provider names.

This failed for records such as:

```text
VIDANT MEDICAL GROUP FMAILY MEDCN
```

where OCR-style corruption prevented Google from retrieving relevant pages.

Switching retrieval to:

```text
address + state
```

significantly improved performance.

---

## 2. Name Normalization

The pipeline normalizes:

* punctuation
* titles (`MD`, `DO`, `DR`)
* LAST/FIRST formatting

Example:

```text
ANSARI, AMIR ZIA
→ AMIR ZIA ANSARI
```

---

## 3. Address Normalization

The pipeline standardizes:

```text
BOULEVARD → BLVD
AVENUE → AVE
SUITE → removed
```

This allows:

```text
2910 E FRANKLIN BLVD # 1
```

to correctly match:

```text
2910 East Franklin Boulevard, Suite 1
```

---

## 4. Fuzzy Matching

`RapidFuzz.token_set_ratio()` was selected after experimentation.

It performed particularly well for:

* reordered tokens
* partial overlaps
* abbreviation differences
* OCR corruption

Examples:

```text
FMAILY MEDCN
↔ FAMILY MEDICINE
```

```text
AMIR ANSARI
↔ DR. AMIR ZIA ANSARI, MD
```

---

## 5. Weighted Verification Scoring

The final score combines:

```python
final_score = (
    address_score * 0.7
    + name_score * 0.3
)
```

Address was intentionally weighted more heavily because:

* provider names vary significantly
* addresses are usually unique identifiers

---

## 6. State Filtering

Candidate pages are skipped immediately if state values do not match.

This greatly reduces:

* false positives
* unnecessary scraping
* latency

---

# Handling Different Entity Types

The pipeline supports:

## Providers

Detected using:

```html
h1.provider-full-name
```

## Facilities / Practices

Detected using:

```html
h3.facility-name
```

The scraper dynamically adapts depending on page structure.

---

# Performance Optimizations

Current optimizations include:

* top-5 Google result limiting
* early stopping for strong matches
* state-based candidate elimination
* deduplication of candidate links

---

# Challenges Faced During Development

## Bot Detection

Google frequently flagged automated requests.

Mitigations used:

* custom user-agent
* Playwright stealth patching
* limiting requests
* browser-based retrieval instead of raw requests

---

## Retrieval Recall

The biggest challenge was not fuzzy matching.

It was:

```text
getting the correct candidate pages initially
```

Once retrieval shifted from:

```text
name-based
```

to:

```text
address-based
```

accuracy improved substantially.

---

# Future Improvements

Potential future contributions include:

## Performance / Latency

* async scraping
* multiprocessing
* browser pooling
* caching previously matched entities
* parallel verification

---

## Better Bot Avoidance

* rotating proxies
* CAPTCHA handling
* residential IP routing
* randomized browser fingerprints
* stealth browser frameworks

---

## Better Retrieval

* search engine fallback systems
* direct SERP APIs
* local candidate caching
* semantic retrieval models

---

## Better Entity Resolution

* ZIP-code weighting
* embedding-based similarity
* phonetic matching
* healthcare-specific abbreviation expansion

Examples:

```text
CTR → CENTER
MED → MEDICAL
HLTH → HEALTH
```

---

# Example Match

## Input

```text
CUSTOMER_NAME : ANSARI, AMIR ZIA
CUST_ADDRESS  : 2910 E FRANKLIN BLVD # 1
CUST_STATE    : NC
```

## Output

```text
https://doctor.webmd.com/doctor/amir-ansari-29836e0c-dec5-11e7-9f4c-005056a225bf-overview
```

---

# Installation

```bash
pip install pandas playwright rapidfuzz openpyxl
```

Install Playwright browsers:

```bash
playwright install
```

---

# How to Use

## 1. Place your Excel file in the project directory

The input Excel file should be named:

```text
input1.xlsx
```

and must contain these columns:

| CUSTOMER_NAME | CUST_ADDRESS | CUST_STATE |
| ------------- | ------------ | ---------- |

---

## 2. Install dependencies

```bash
pip install pandas playwright rapidfuzz openpyxl
```

Install Playwright browsers:

```bash
playwright install
```

---

## 3. Run the script

```bash
python main.py
```

---

## 4. Get the output

The script generates:

```text
output_with_links.xlsx
```

with a new column:

```text
link
```

containing the matched WebMD URLs.

---

# Running the Pipeline

```bash
python main.py
```

---

# Disclaimer

This project is intended for educational and research purposes.

Please review and comply with:

* WebMD Terms of Service
* Google Terms of Service
* applicable scraping and data usage policies

---

# Contributions

Contributions are welcome.

Areas with the highest impact:

* reducing scraping latency
* improving bot resistance
* increasing retrieval recall
* improving fuzzy matching quality
* optimizing browser automation

