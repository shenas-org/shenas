"""Freedom House client.

Downloads the Freedom in the World aggregate Excel dataset. The file
is published annually at a predictable URL pattern. Falls back to
the most recent available year if the current year's file is not yet
published.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any

import httpx
import openpyxl

# URL pattern for the aggregate data file (country-year format)
# The year in the URL is the edition year (covers the prior calendar year).
BASE_URL = "https://freedomhouse.org/sites/default/files"
FILE_PATTERN = "FIW_All_Data_country_year_format_{start}-{end}.xlsx"

# Subcategory columns present in the Excel data (2013+ editions)
SUBCATEGORIES = ("A", "B", "C", "D", "E", "F", "G")
INDICATOR_QUESTIONS = (
    "A1",
    "A2",
    "A3",
    "B1",
    "B2",
    "B3",
    "B4",
    "C1",
    "C2",
    "C3",
    "D1",
    "D2",
    "D3",
    "D4",
    "E1",
    "E2",
    "E3",
    "F1",
    "F2",
    "F3",
    "F4",
    "G1",
    "G2",
    "G3",
    "G4",
)


class FreedomHouseClient:
    """Client that downloads and parses the Freedom House aggregate Excel dataset."""

    def __init__(self) -> None:
        self._http = httpx.Client(timeout=120.0, follow_redirects=True)
        self._data: list[dict[str, Any]] | None = None

    def close(self) -> None:
        self._http.close()

    def _download_excel(self) -> bytes:
        """Try to download the aggregate Excel file, trying recent year ranges."""
        current_year = datetime.now(UTC).year
        # Try the most recent edition first, then fall back
        for end_year in range(current_year, current_year - 3, -1):
            filename = FILE_PATTERN.format(start=2013, end=end_year)
            url = f"{BASE_URL}/{end_year}-02/{filename}"
            resp = self._http.get(url)
            if resp.status_code == 200:
                return resp.content
            # Try alternate month
            url = f"{BASE_URL}/{end_year}-03/{filename}"
            resp = self._http.get(url)
            if resp.status_code == 200:
                return resp.content
        msg = "Could not download Freedom House aggregate data file."
        raise RuntimeError(msg)

    def _parse_excel(self, content: bytes) -> list[dict[str, Any]]:
        """Parse the Excel file into row dicts using openpyxl."""
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            msg = "Excel file has no active worksheet."
            raise RuntimeError(msg)

        rows_iter = ws.iter_rows(values_only=True)
        header = next(rows_iter, None)
        if header is None:
            return []

        # Normalize header names
        columns = [str(h).strip() if h else "" for h in header]
        col_idx: dict[str, int] = {}
        for i, name in enumerate(columns):
            # Map known column name variants
            normalized = name.replace("/", "_").replace(" ", "_").upper()
            col_idx[normalized] = i

        def _get(row: tuple, *keys: str) -> Any:
            for key in keys:
                idx = col_idx.get(key)
                if idx is not None and idx < len(row):
                    return row[idx]
            return None

        result: list[dict[str, Any]] = []
        for row in rows_iter:
            country = _get(row, "COUNTRY_TERRITORY", "COUNTRY", "COUNTRY/TERRITORY")
            if not country:
                continue
            edition = _get(row, "EDITION", "YEAR")
            if edition is None:
                continue

            entry: dict[str, Any] = {
                "country": str(country).strip(),
                "is_territory": str(_get(row, "C_T", "C/T") or "C").strip() == "T",
                "edition": int(edition),
                "status": str(_get(row, "STATUS") or "").strip(),
                "political_rights": _safe_int(_get(row, "PR", "PR_RATING")),
                "civil_liberties": _safe_int(_get(row, "CL", "CL_RATING")),
                "total": _safe_int(_get(row, "TOTAL")),
            }
            # Subcategory scores
            for sub in SUBCATEGORIES:
                entry[f"sub_{sub.lower()}"] = _safe_int(_get(row, sub))
            # Individual indicator scores
            for q in INDICATOR_QUESTIONS:
                entry[f"q_{q.lower()}"] = _safe_int(_get(row, q))

            result.append(entry)

        wb.close()
        return result

    def get_freedom_scores(self) -> list[dict[str, Any]]:
        """Download and parse freedom scores. Results are cached."""
        if self._data is None:
            content = self._download_excel()
            self._data = self._parse_excel(content)
        return self._data


def _safe_int(val: Any) -> int | None:
    """Convert a value to int, returning None for non-numeric values."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
