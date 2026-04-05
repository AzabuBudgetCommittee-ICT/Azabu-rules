from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
import re

from pydantic import ValidationError

from metadata_schema import Metadata


_ENFORCEMENT_DATE_PATTERN = re.compile(r"^(?:\d{8}|XXXXXXXX)$")


def _to_yyyymmdd(value: date) -> int:
    return int(value.strftime("%Y%m%d"))


def _candidate_sort_key(enforcement_date: str, today_yyyymmdd: int) -> int | None:
    if not _ENFORCEMENT_DATE_PATTERN.fullmatch(enforcement_date):
        raise ValueError(f"Invalid enforcement_date format: {enforcement_date}")

    if enforcement_date == "XXXXXXXX":
        return None

    if enforcement_date == "00000000":
        return 0

    try:
        datetime.strptime(enforcement_date, "%Y%m%d")
    except ValueError as error:
        raise ValueError(f"Invalid enforcement_date value: {enforcement_date}") from error

    value = int(enforcement_date)
    if value <= today_yyyymmdd:
        return value

    return None


def resolve_current_revision_from_metadata(metadata: object, today: date | None = None) -> str:
    try:
        metadata_obj = Metadata.model_validate(metadata)
    except ValidationError as error:
        raise ValueError(f"Invalid metadata schema: {error}") from error

    target_date = today or date.today()
    today_yyyymmdd = _to_yyyymmdd(target_date)

    current_revision_id: str | None = None
    current_sort_key: int | None = None

    for revision in metadata_obj.revision_info:
        sort_key = _candidate_sort_key(revision.enforcement_date, today_yyyymmdd)
        if sort_key is None:
            continue

        if current_sort_key is None or sort_key > current_sort_key:
            current_sort_key = sort_key
            current_revision_id = revision.revision_id

    if current_revision_id is None:
        raise ValueError("No current revision could be resolved")

    if current_revision_id != metadata_obj.current_revision_id:
        raise ValueError("current_revision_id does not match resolved revision")

    return metadata_obj.current_revision_id


def resolve_current_revision(metadata_file_path: str | Path, today: date | None = None) -> str:
    metadata_path = Path(metadata_file_path)

    try:
        content = metadata_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Unable to read metadata file: {metadata_path}") from error

    try:
        metadata = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid metadata JSON: {metadata_path}") from error

    return resolve_current_revision_from_metadata(metadata, today=today)