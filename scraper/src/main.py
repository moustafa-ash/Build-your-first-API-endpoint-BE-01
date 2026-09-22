"""Polite, cached Books to Scrape pipeline for FlyRank A9."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError, field_validator


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache"
OUTPUT = ROOT / "output"
BASE_URL = "https://books.toscrape.com/"
USER_AGENT = (
    "FlyRankInternship-A9/1.0 "
    "(+https://github.com/moustafa-ash/Build-your-first-API-endpoint-BE-01)"
)
TIMEOUT = 10
MIN_DELAY = 0.5


class BookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None
    source_page: str
    fetched_at: str

    @field_validator("product_url", "source_page")
    @classmethod
    def require_https_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("URL must start with https://")
        return value

    @field_validator("price_gbp")
    @classmethod
    def require_numeric_price(cls, value: float) -> float:
        if value < 0:
            raise ValueError("price must not be negative")
        return value


class FetchError(RuntimeError):
    pass


class Scraper:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.last_request = 0.0
        self.pages_fetched = 0
        self.cache_hits = 0

    def _polite_wait(self) -> None:
        remaining = MIN_DELAY - (time.monotonic() - self.last_request)
        if remaining > 0:
            time.sleep(remaining)

    def fetch(self, url: str, cache_path: Path) -> tuple[str, str]:
        if cache_path.exists():
            self.cache_hits += 1
            print(f"CACHE HIT {url} ({cache_path.stat().st_size} bytes)")
            fetched_at = datetime.fromtimestamp(
                cache_path.stat().st_mtime, tz=timezone.utc
            ).isoformat().replace("+00:00", "Z")
            return cache_path.read_text(encoding="utf-8").replace("Â£", "£"), fetched_at

        last_error: Exception | None = None
        for attempt in range(2):
            if attempt:
                time.sleep(1)
            self._polite_wait()
            self.last_request = time.monotonic()
            try:
                response = self.session.get(url, timeout=TIMEOUT)
            except requests.Timeout as exc:
                last_error = exc
                if attempt == 0:
                    continue
                raise FetchError(f"timeout after retry: {url}") from exc
            except requests.RequestException as exc:
                raise FetchError(f"request failed: {exc}") from exc

            if response.status_code == 200:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                text = response.content.decode("utf-8", errors="replace")
                cache_path.write_text(text, encoding="utf-8")
                self.pages_fetched += 1
                print(f"FETCH {url} ({len(response.content)} bytes)")
                fetched_at = datetime.now(timezone.utc).isoformat().replace(
                    "+00:00", "Z"
                )
                return text, fetched_at

            if 500 <= response.status_code < 600 and attempt == 0:
                last_error = FetchError(f"HTTP {response.status_code}")
                continue
            raise FetchError(f"HTTP {response.status_code} for {url}")

        raise FetchError(f"request failed: {last_error}")


def clean_text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def product_cache_path(url: str) -> Path:
    parts = [part for part in urlparse(url).path.split("/") if part]
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", parts[-2] if len(parts) > 1 else parts[-1])
    return CACHE / "details" / f"{slug}.html"


def discover(scraper: Scraper) -> tuple[dict[str, str], int]:
    current_url = urljoin(BASE_URL, "catalogue/page-1.html")
    discovered: dict[str, str] = {}
    for page_number in range(1, 4):
        html, _ = scraper.fetch(
            current_url, CACHE / f"catalogue-page-{page_number}.html"
        )
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.select("article.product_pod h3 a[href]"):
            product_url = urljoin(current_url, link["href"])
            discovered.setdefault(product_url, current_url)
        if page_number < 3:
            next_link = soup.select_one("li.next a[href]")
            if not next_link:
                raise FetchError(f"catalogue page {page_number} has no next link")
            current_url = urljoin(current_url, next_link["href"])
    print(
        f"catalogue_pages=3 discovered={sum(1 for _ in discovered)} "
        f"unique_urls={len(discovered)}"
    )
    return discovered, 3


def extract_raw(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("article.product_page") or soup
    rating = product.select_one("p.star-rating")
    rating_text = " ".join(
        item for item in (rating.get("class", []) if rating else []) if item != "star-rating"
    )
    description_node = soup.select_one("#product_description + p")
    return {
        "title": clean_text(product.select_one("h1")),
        "product_url": product_url,
        "price_text": clean_text(product.select_one(".price_color")),
        "availability_text": clean_text(product.select_one(".availability")),
        "rating_text": rating_text,
        "description": clean_text(description_node) or None,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def normalize(raw: dict) -> BookRecord:
    price_text = raw["price_text"]
    raw["price_gbp"] = float(price_text.replace("£", "").replace(",", "").strip())
    return BookRecord.model_validate(raw)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(include_broken_url: bool = False) -> None:
    started = datetime.now(timezone.utc)
    scraper = Scraper()
    failures: list[dict[str, str]] = []
    errors: list[dict] = []
    records: list[BookRecord] = []

    products, _ = discover(scraper)
    urls = list(products)
    if include_broken_url:
        urls.append(urljoin(BASE_URL, "catalogue/this-page-is-intentionally-missing.html"))

    first_raw = None
    for product_url in urls:
        source_page = products.get(product_url, urljoin(BASE_URL, "catalogue/page-1.html"))
        try:
            html, fetched_at = scraper.fetch(product_url, product_cache_path(product_url))
            raw = extract_raw(html, product_url, source_page, fetched_at)
            if first_raw is None:
                first_raw = raw.copy()
            records.append(normalize(raw))
        except (FetchError, ValueError, ValidationError, KeyError) as exc:
            reason = str(exc)
            if isinstance(exc, FetchError):
                failures.append({"url": product_url, "reason": reason})
            errors.append({"url": product_url, "reason": reason})

    records.sort(key=lambda record: record.product_url)
    errors.sort(key=lambda error: error["url"])
    write_json(OUTPUT / "books.json", [record.model_dump(mode="json") for record in records])
    write_json(OUTPUT / "errors.json", errors)
    duration = (datetime.now(timezone.utc) - started).total_seconds()
    report = {
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "duration_seconds": round(duration, 3),
        "pages_fetched": scraper.pages_fetched,
        "cache_hits": scraper.cache_hits,
        "valid_records": len(records),
        "invalid_records": len(errors) - len(failures),
        "failed_pages": len(failures),
        "failures": failures,
    }
    write_json(OUTPUT / "run-report.json", report)
    if first_raw:
        print("RAW RECORD")
        print(json.dumps(first_raw, indent=2, ensure_ascii=False))
    print(f"detail_pages={len(products)} valid_records={len(records)} failed_pages={len(failures)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the polite Books to Scrape pipeline")
    parser.add_argument(
        "--include-broken-url",
        action="store_true",
        help="add one local failure case for the Stage 5 demonstration",
    )
    args = parser.parse_args()
    run(include_broken_url=args.include_broken_url)
