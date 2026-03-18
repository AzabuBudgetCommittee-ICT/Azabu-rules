from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
import re
from typing import Any, Mapping


_EFFECTIVE_DATE_PATTERN = re.compile(r"^(?:\d{8}|XXXXXXXX)$")


def _to_yyyymmdd(value: date) -> int:
    return int(value.strftime("%Y%m%d"))


def _parse_effective_date_from_revision_id(revision_id: str) -> str:
    parts = revision_id.split("_")
    if len(parts) != 3:
        raise ValueError(f"Invalid revision_id format: {revision_id}")
    return parts[1]


def _candidate_sort_key(effective_date: str, today_yyyymmdd: int) -> int | None:
    if not _EFFECTIVE_DATE_PATTERN.fullmatch(effective_date):
        raise ValueError(f"Invalid effective_date format: {effective_date}")

    if effective_date == "XXXXXXXX":
        return None

    if effective_date == "00000000":
        return 0

    try:
        datetime.strptime(effective_date, "%Y%m%d")
    except ValueError as error:
        raise ValueError(f"Invalid effective_date value: {effective_date}") from error

    value = int(effective_date)
    if value <= today_yyyymmdd:
        return value

    return None


def resolve_current_revision_from_metadata(
    metadata: Mapping[str, Any], today: date | None = None
) -> str | None:
    revisions = metadata.get("revisions")
    if not isinstance(revisions, list):
        raise ValueError("metadata must include a list field 'revisions'")

    target_date = today or date.today()
    today_yyyymmdd = _to_yyyymmdd(target_date)

    current_revision_id: str | None = None
    current_sort_key: int | None = None

    for revision in revisions:
        if not isinstance(revision, Mapping):
            raise ValueError("each revision must be an object")

        revision_id = revision.get("revision_id")
        if not isinstance(revision_id, str) or not revision_id:
            raise ValueError("each revision must include non-empty 'revision_id'")

        effective_date = revision.get("effective_date")
        if effective_date is None:
            effective_date = _parse_effective_date_from_revision_id(revision_id)
        if not isinstance(effective_date, str):
            raise ValueError("'effective_date' must be a string")

        sort_key = _candidate_sort_key(effective_date, today_yyyymmdd)
        if sort_key is None:
            continue

        if current_sort_key is None or sort_key > current_sort_key:
            current_sort_key = sort_key
            current_revision_id = revision_id

    return current_revision_id


def resolve_current_revision(metadata_file_path: str | Path, today: date | None = None) -> str | None:
    metadata_path = Path(metadata_file_path)

    try:
        content = metadata_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Unable to read metadata file: {metadata_path}") from error

    try:
        metadata = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid metadata JSON: {metadata_path}") from error

    if not isinstance(metadata, Mapping):
        raise ValueError("metadata root must be an object")

    return resolve_current_revision_from_metadata(metadata, today=today)