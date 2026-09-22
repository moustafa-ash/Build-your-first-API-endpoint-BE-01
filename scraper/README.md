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
