"""Normalization utilities.

Deduplicate (zone, code) pairs and enrich with duplicate/meta flags.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

__all__ = ["apply"]


def _deduplicate(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (unique_rows, dup_rows). Duplicate key is (zone, code)."""
    key_to_row: dict[tuple[str, str], dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []

    for row in rows:
        key = (row.get("zone"), row.get("code"))
        if key not in key_to_row:
            key_to_row[key] = row
            row["is_duplicate"] = False
        else:
            # keep record with higher confidence
            existing = key_to_row[key]
            if row.get("conf", 0) > existing.get("conf", 0):
                key_to_row[key] = row
            row["is_duplicate"] = True
            duplicates.append(row)

    unique_rows = list(key_to_row.values())
    logger.info(
        f"Normalization » {len(duplicates)} duplicates removed, retained {len(unique_rows)} unique rows"
    )
    return unique_rows, duplicates


def apply(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:  # noqa: D401
    """Deduplicate `rows` on (zone, code) keeping highest confidence record.

    Returns enriched unique rows list.
    """
    unique_rows, _ = _deduplicate(rows)
    return unique_rows
