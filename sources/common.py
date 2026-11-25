"""Shared helpers for the tender sources.

Both UK services publish notices in the Open Contracting Data Standard
(OCDS) format and page through results the same way: each response has
a ``links.next`` URL until there are no more results. Both may answer
429 (too many requests) or 503 (busy) with a ``Retry-After`` header
saying how many seconds to wait.
"""

from __future__ import annotations

import time
from typing import Callable, Iterator

import requests

USER_AGENT = "DealPilot-POC/0.1 (tender research)"
TIMEOUT = 60  # seconds; Contracts Finder can take several seconds per page
MAX_RETRIES = 5
DEFAULT_WAIT = 10  # seconds, used when the server gives no Retry-After
PAGE_PAUSE = 0.5  # seconds between pages, to stay under the rate limits


class SourceError(RuntimeError):
    """Raised when a source cannot be read after retries."""


def get_json(
    session: requests.Session,
    url: str,
    params: dict | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """GET a URL and return JSON, waiting and retrying on 429/503/network errors.

    Contracts Finder answers 429 with ``Retry-After: 120`` (two minutes)
    when hit too often, so a wait message is passed to ``progress``.
    """
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(min(DEFAULT_WAIT, 2 ** attempt))
            continue

        if resp.status_code in (429, 503):
            wait = resp.headers.get("Retry-After")
            try:
                wait_s = float(wait) if wait is not None else DEFAULT_WAIT
            except ValueError:
                wait_s = DEFAULT_WAIT
            last_error = SourceError(f"HTTP {resp.status_code}, waited {wait_s:.0f}s")
            if progress:
                progress(f"Server asked us to slow down; waiting {wait_s:.0f} seconds...")
            time.sleep(min(wait_s, 120))
            continue

        if resp.status_code != 200:
            raise SourceError(f"HTTP {resp.status_code} from {resp.url}: {resp.text[:300]}")

        return resp.json()

    raise SourceError(f"Gave up after {MAX_RETRIES} tries: {last_error}")


def iter_releases(
    url: str,
    params: dict,
    max_pages: int,
    progress: Callable[[str], None] | None = None,
) -> Iterator[dict]:
    """Yield OCDS releases, following ``links.next`` for up to ``max_pages`` pages.

    ``progress(message)`` is called after each page so the app can show progress.
    """
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    session.headers["Accept"] = "application/json"

    next_url, next_params = url, params
    count = 0
    for page in range(1, max_pages + 1):
        data = get_json(session, next_url, next_params, progress)
        releases = data.get("releases") or []
        count += len(releases)
        yield from releases
        if progress:
            progress(f"page {page}, {count} notices so far")
        next_url = (data.get("links") or {}).get("next")
        next_params = None  # the next link already carries every parameter
        if not next_url or not releases:
            return
        time.sleep(PAGE_PAUSE)


def release_stage(release: dict) -> str | None:
    """Map OCDS release tags to one of: planning, tender, award.

    Cancelled tenders return None so they are dropped.
    """
    tags = release.get("tag") or []
    if "tenderCancellation" in tags:
        return None
    if any(t.startswith(("award", "contract")) for t in tags):
        return "award"
    if any(t.startswith("tender") for t in tags):
        return "tender"
    if any(t.startswith("planning") for t in tags):
        return "planning"
    return None


def collect(
    url: str,
    params: dict,
    stages: list[str],
    max_pages: int,
    source_name: str,
    make_link: Callable[[dict], str],
    progress: Callable[[str], None] | None = None,
) -> list[dict]:
    """Download releases and keep the ones in the chosen stages.

    Stages are filtered here rather than with the API's ``stages``
    parameter: in testing (Nov 2026), Find a Tender's ``stages=tender``
    returned 4 notices for a day that had 44 tender notices.
    """
    wanted = set(stages)
    rows = []
    for rel in iter_releases(url, params, max_pages, progress):
        stage = release_stage(rel)
        if stage is None or (wanted and stage not in wanted):
            continue
        row = normalise_release(rel, source_name, make_link(rel))
        row["stage"] = stage
        rows.append(row)
    return rows


def normalise_release(release: dict, source: str, link: str) -> dict:
    """Turn one OCDS release into a flat row the app can show and search."""
    tender = release.get("tender") or {}
    value = tender.get("value") or {}
    amount = value.get("amount")
    if amount is None:
        amount = (tender.get("minValue") or {}).get("amount")

    cpv = []
    cls = tender.get("classification") or {}
    if cls.get("description"):
        cpv.append(cls["description"])
    for c in tender.get("additionalClassifications") or []:
        if c.get("description"):
            cpv.append(c["description"])
    for item in tender.get("items") or []:
        for c in item.get("additionalClassifications") or []:
            if c.get("description"):
                cpv.append(c["description"])
        c = item.get("classification") or {}
        if c.get("description"):
            cpv.append(c["description"])

    lot_text = " ".join(
        (lot.get("title") or "") + " " + (lot.get("description") or "")
        for lot in tender.get("lots") or []
    )

    return {
        "source": source,
        "ocid": release.get("ocid"),
        "notice_id": release.get("id"),
        "published": release.get("date"),
        "stage": ", ".join(release.get("tag") or []),
        "status": tender.get("status"),
        "title": (tender.get("title") or release.get("title") or "").strip(),
        "description": ((tender.get("description") or "") + " " + lot_text).strip(),
        "categories": "; ".join(dict.fromkeys(cpv)),
        "buyer": (release.get("buyer") or {}).get("name"),
        "value": amount,
        "currency": value.get("currency") or "GBP",
        "closing_date": (tender.get("tenderPeriod") or {}).get("endDate"),
        "link": link,
    }
