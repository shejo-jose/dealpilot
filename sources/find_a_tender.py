"""UK Find a Tender service (higher-value public contracts).

API docs: https://www.find-tender.service.gov.uk/apidocumentation/1.0/GET-ocdsReleasePackages
- Free, no sign-up.
- Parameters: updatedFrom / updatedTo (format YYYY-MM-DDTHH:MM:SS),
  limit (1-100), cursor. (A stages filter exists but returned far too
  few results in testing, so we filter by stage ourselves.)
- Paging: follow ``links.next``.
- Rate limit: 429 or 503 with Retry-After seconds.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from .common import collect

NAME = "Find a Tender (UK)"
URL = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
NOTICE_URL = "https://www.find-tender.service.gov.uk/Notice/{notice_id}"


def fetch(
    date_from: datetime,
    date_to: datetime,
    stages: list[str],
    max_pages: int = 60,
    progress: Callable[[str], None] | None = None,
) -> list[dict]:
    params = {
        "updatedFrom": date_from.strftime("%Y-%m-%dT%H:%M:%S"),
        "updatedTo": date_to.strftime("%Y-%m-%dT%H:%M:%S"),
        "limit": 100,
    }
    return collect(URL, params, stages, max_pages, NAME,
                   lambda rel: NOTICE_URL.format(notice_id=rel.get("id", "")), progress)
