# DealPilot

DealPilot is a sales agent that finds organisations looking to buy what we
sell: **GDiaL**, **Voisense**, **WorkFabriQ** and **CasExpert**.

This first version is a small web app (built with Streamlit) that searches
UK public-sector tenders and flags the ones that mention our product
keywords.

## What it does

1. Downloads notices from two free UK government services (no sign-up or key needed):
   - **Find a Tender**: higher-value public contracts.
   - **Contracts Finder**: lower-value public contracts.
2. Looks for each product's keywords in the notice title, description and category.
3. Shows the matches in a table: title, buyer, value, closing date, matched
   product, matched keywords and a link to the notice.
4. Gives each match a simple score: 1 point per keyword found (2 if it is in
   the title), plus 2 bonus points if the notice is still open for bids.
5. Lets you download the table as a CSV file.

## Run it on Windows with WSL

These steps assume you already have WSL (Ubuntu) installed. Open the
Ubuntu terminal and run:

```bash
# 1. One-time setup: Python tools and git
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

# 2. Get the code
git clone https://github.com/shejo-jose/dealpilot.git
cd dealpilot

# 3. Create a private Python environment for this project and install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Start the app
streamlit run app.py
```

Streamlit prints a link such as `http://localhost:8501`. Open it in your
Windows browser (Edge or Chrome). Press `Ctrl+C` in the terminal to stop.

Next time, you only need:

```bash
cd dealpilot
source .venv/bin/activate
git pull          # get the latest changes
streamlit run app.py
```

## Using the app

- **Date range**: notices published or updated in this window. A week is a
  good start; Find a Tender has roughly 500 notices a day.
- **Sources**: pick one or both.
- **Notice stage**: `tender` = open invitations to bid, `planning` = early
  notice of an upcoming purchase, `award` = contract already given (useful
  to learn who buys what and when it may renew).
- **Products and keywords**: open a product to edit its keywords, one per
  line. Untick *Include* to skip a product.
- **Fetch**: downloads and matches. Downloads are remembered for an hour, so
  changing keywords and pressing Fetch again is instant. Use *Clear cached
  downloads* to force a fresh download.

To change the default keywords or fill in product descriptions, edit
`config.py`.

## Good to know

- Both services limit how often you can call them. If you hit the limit,
  the app waits (up to two minutes) and tries again, and shows a message
  while it waits.
- Find a Tender's own "stage" filter returned far too few results when we
  tested it, so the app downloads everything in the date range and filters
  by stage itself.
- Keyword matching is simple whole-word search. Broad words such as
  "workforce" or "customer service" will bring in some unrelated notices;
  tune the lists as you learn what works.

## Files

| File | What it is |
| --- | --- |
| `app.py` | The web app (sidebar, table, CSV download) |
| `config.py` | Products, default keywords, scoring settings |
| `matching.py` | Keyword matching and scoring |
| `sources/find_a_tender.py` | Reads Find a Tender |
| `sources/contracts_finder.py` | Reads Contracts Finder |
| `sources/common.py` | Shared download, paging and retry code |

## Not included yet

- US SAM.gov (needs a free API key; new keys allow only 10 calls a day).
- EU TED (not tested yet).
- India GeM and CPPP (no public API).
