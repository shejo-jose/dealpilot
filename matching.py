"""Match tender notices to DealPilot products by keyword, and score them."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pandas as pd

from config import DESCRIPTION_HIT_POINTS, OPEN_BONUS, TITLE_HIT_POINTS


def _pattern(keyword: str) -> re.Pattern:
    # Whole-word, case-insensitive match; spaces in a keyword match any
    # whitespace, and a plural "s"/"es" is allowed ("system" finds "systems").
    words = [re.escape(w) for w in keyword.strip().split()]
    return re.compile(r"\b" + r"\s+".join(words) + r"(?:e?s)?\b", re.IGNORECASE)


def _parse_date(value) -> datetime | None:
    if not value:
        return None
    try:
        ts = pd.Timestamp(value)
    except (ValueError, TypeError):
        return None
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.to_pydatetime()


def is_open(row: dict, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    closing = _parse_date(row.get("closing_date"))
    if closing is not None:
        return closing > now
    return row.get("status") in ("active", "planned", "planning")


def dedupe(rows: list[dict]) -> list[dict]:
    """Keep only the newest release for each procurement (ocid)."""
    latest: dict[str, dict] = {}
    for r in rows:
        key = r.get("ocid") or r.get("link")
        if key not in latest or (r.get("published") or "") > (latest[key].get("published") or ""):
            latest[key] = r
    return list(latest.values())


# Reference codes some buyers put in front of titles, e.g. "CA18704 - ",
# "SCE0078 - ", "IT2716 - ", "P0402 - ", "715862519 - ".
_REF_PREFIX = re.compile(r"^\s*[A-Za-z]{0,5}[\d][\w/.-]*\s*[-:_]\s+")


def _norm(text: str | None) -> str:
    text = _REF_PREFIX.sub("", text or "")
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def merge_cross_source(rows: list[dict]) -> list[dict]:
    """Merge notices that appear on both Find a Tender and Contracts Finder.

    Two rows are the same notice when the buyer matches and one title
    contains the other once reference codes and punctuation are ignored
    (e.g. "St Matthew's Primary School _ Luton" and
    "CA18704 - St Matthew's Primary School _ Luton"). The higher-scoring
    row is kept and its source lists both sites.
    """
    rows = sorted(rows, key=lambda r: r["score"], reverse=True)
    kept: list[dict] = []
    for r in rows:
        buyer, title = _norm(r.get("buyer")), _norm(r.get("title"))
        twin = None
        if buyer and title:
            for k in kept:
                if k["source"] == r["source"] or r["source"] in k["source"]:
                    continue
                kt = _norm(k.get("title"))
                if _norm(k.get("buyer")) == buyer and (title in kt or kt in title):
                    twin = k
                    break
        if twin is None:
            kept.append(dict(r))
        else:
            twin["source"] = f"{twin['source']} + {r['source']}"
    return kept


COLUMNS = [
    "score", "title", "buyer", "value", "currency", "closing_date", "open",
    "matched_product", "other_products", "matched_keywords", "source",
    "stage", "published", "link",
]


def match(rows: list[dict], products: dict[str, list[str]], open_only: bool = False) -> pd.DataFrame:
    """Return a table of notices that hit at least one product keyword.

    ``products`` maps product name -> list of keywords.
    """
    compiled = {
        name: [(kw, _pattern(kw)) for kw in kws if kw.strip()]
        for name, kws in products.items()
    }
    now = datetime.now(timezone.utc)
    out = []
    for r in dedupe(rows):
        title = r.get("title") or ""
        body = f"{r.get('description') or ''} {r.get('categories') or ''}"
        product_scores = {}
        product_hits = {}
        for name, pats in compiled.items():
            score, hits = 0, []
            for kw, pat in pats:
                if pat.search(title):
                    score += TITLE_HIT_POINTS
                    hits.append(f"{kw} (title)")
                elif pat.search(body):
                    score += DESCRIPTION_HIT_POINTS
                    hits.append(kw)
            if hits:
                product_scores[name] = score
                product_hits[name] = hits
        if not product_scores:
            continue

        open_now = is_open(r, now)
        if open_only and not open_now:
            continue
        ranked = sorted(product_scores, key=product_scores.get, reverse=True)
        best = ranked[0]
        score = product_scores[best] + (OPEN_BONUS if open_now else 0)
        out.append(
            {
                "score": score,
                "title": r.get("title"),
                "buyer": r.get("buyer"),
                "value": r.get("value"),
                "currency": r.get("currency"),
                "closing_date": _parse_date(r.get("closing_date")),
                "open": open_now,
                "matched_product": best,
                "other_products": ", ".join(ranked[1:]),
                "matched_keywords": "; ".join(
                    f"{p}: {', '.join(product_hits[p])}" for p in ranked
                ),
                "source": r.get("source"),
                "stage": r.get("stage"),
                "published": _parse_date(r.get("published")),
                "link": r.get("link"),
            }
        )

    df = pd.DataFrame(merge_cross_source(out), columns=COLUMNS)
    for col in ("closing_date", "published"):
        df[col] = pd.to_datetime(df[col], utc=True)
    if not df.empty:
        df = df.sort_values(["score", "closing_date"], ascending=[False, True], na_position="last")
        df = df.reset_index(drop=True)
    return df
