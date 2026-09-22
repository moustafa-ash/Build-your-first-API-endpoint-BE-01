# The polite scraper

## Target classification

This scraper targets [Books to Scrape](https://books.toscrape.com/), the public
practice sandbox linked from ToScrape. The site is explicitly intended for
learning web scraping and does not require JavaScript. This assignment collects
only the first three catalogue pages (60 books): title, product URL, price,
availability, rating, description, source page, and fetch time.

I checked `https://books.toscrape.com/robots.txt` once on 2026-09-22. It
returned HTTP 404 Not Found, so no robots file was found; that is not permission
to scrape another site. I will not reuse this code on another site without
checking its rules and terms first.

## Run

From this directory, install the lane dependencies and run:

```powershell
python -m pip install -r requirements.txt
python src/main.py
```

The catalogue checkpoint is `catalogue_pages=3 discovered=60
unique_urls=60`. The first run fetches and caches the three catalogue pages;
later development runs read those saved copies instead of requesting them
again.

## Raw detail records

Each detail page is cached separately and produces these provenance-preserving
fields before normalization: `title`, `product_url`, `price_text`,
`availability_text`, `rating_text`, `description`, `source_page`, and
`fetched_at`. The live checkpoint produced `detail_pages=60`; a missing
description is represented as `null`.

## Validated output

Before storage, every record is checked with the Pydantic `BookRecord` schema.
`price_text` is retained alongside numeric `price_gbp`; `product_url` and
`source_page` must be HTTPS URLs. Valid records are written to
`output/books.json`, while records that fail normalization or validation are
written with their reason to `output/errors.json`. The current cached run has
60 valid records and no validation errors.

## Failure handling and report

Every page is isolated. Timeouts and HTTP 5xx responses receive one retry after
one second; 403 and 404 responses are not retried. To reproduce the required
local failure proof, run:

```powershell
python src/main.py --include-broken-url
```

That run completed with `valid_records: 60`, `failed_pages: 1`, and one entry
in `output/run-report.json`; the good records remained intact. The report also
records its UTC start time, duration, network fetches, cache hits, and failure
details.

The scraper sends an identifying user-agent, waits at least 500 ms between real
requests, uses a 10-second timeout, checks status codes, and reads cached HTML
while developing. Use an official API when one exists, never bypass logins,
paywalls, or blocks, and collect only what is needed. This assignment needs no
browser because the required catalogue and product data are already in the
server-sent HTML; a browser would add cost. The selectors are intentionally
specific to the current sandbox markup and may need updating if that markup
changes.
