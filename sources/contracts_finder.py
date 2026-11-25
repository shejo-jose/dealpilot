"""UK Contracts Finder (lower-value public contracts, roughly £12k+).

API docs: https://www.contractsfinder.service.gov.uk/apidocumentation/Notices/1/GET-Published-Notice-OCDS-Search
- Free, no sign-up.
- Parameters: publishedFrom / publishedTo (ISO 8601),
  limit (1-100), cursor. Stages are filtered locally, same as Find a Tender.
- Paging: follow ``links.next``.
- Each page can take a few seconds.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from .common import collect

NAME = "Contracts Finder (UK)"
URL = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"
NOTICE_URL = "https://www.contractsfinder.service.gov.uk/Notice/{notice_guid}"
OCID_PREFIX = "ocds-b5fd17-"


def notice_link(ocid: str | None) -> str:
    guid = (ocid or "").removeprefix(OCID_PREFIX)
    return NOTICE_URL.format(notice_guid=guid)


def fetch(
    date_from: datetime,
    date_to: datetime,
    stages: list[str],
    max_pages: int = 60,
    progress: Callable[[str], None] | None = None,
) -> list[dict]:
    params = {
        "publishedFrom": date_from.strftime("%Y-%m-%dT%H:%M:%S"),
        "publishedTo": date_to.strftime("%Y-%m-%dT%H:%M:%S"),
        "limit": 100,
    }
    return collect(URL, params, stages, max_pages, NAME,
                   lambda rel: notice_link(rel.get("ocid")), progress)
