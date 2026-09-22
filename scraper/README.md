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

