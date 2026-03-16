from __future__ import annotations

from pathlib import Path
from typing import TypedDict
import xml.etree.ElementTree as ET
import re


class ArticleRecord(TypedDict):
    rule_id: str
    article_num: str
    text: str


class RevisionInfo(TypedDict):
    rule_id: str
    effective_date: str
    amending_rule_id: str


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_rule_and_revision_id(xml_path: Path) -> tuple[str, str]:
    parts = xml_path.parts

    for index, part in enumerate(parts):
        if part != "rules":
            continue

        expected_index = index + 2
        if expected_index >= len(parts):
            break

        rule_id = parts[index + 1]
        revision_filename = parts[index + 2]

        if expected_index != len(parts) - 1:
            break
        if not revision_filename.endswith(".xml"):
            break

        revision_id = Path(revision_filename).stem
        if not rule_id or not revision_id:
            break

        return rule_id, revision_id

    raise ValueError(
        "XML path must include the 'rules/{rule_id}/{revision_id}.xml' structure."
    )


def _parse_revision_id(rule_id: str, revision_id: str) -> RevisionInfo:
    parts = revision_id.split("_")
    if len(parts) != 3:
        raise ValueError(f"Invalid revision_id format: {revision_id}")

    revision_rule_id, effective_date, amending_rule_id = parts

    if revision_rule_id != rule_id:
        raise ValueError(
            "revision_id rule_id must match the rule_id in path: "
            f"{revision_rule_id} != {rule_id}"
        )

    if not re.fullmatch(r"[0-9X]{8}", effective_date):
        raise ValueError(f"Invalid effective_date in revision_id: {effective_date}")

    if not re.fullmatch(r"[A-Za-z0-9X]+", amending_rule_id):
        raise ValueError(
            f"Invalid amending_rule_id in revision_id: {amending_rule_id}"
        )

    return {
        "rule_id": revision_rule_id,
        "effective_date": effective_date,
        "amending_rule_id": amending_rule_id,
    }


def parse_rule_xml(xml_file_path: str | Path) -> list[ArticleRecord]:
    """Parse e-LAWS style rule XML and extract articles.

    Args:
        xml_file_path: Path to an XML file in the form rules/{rule_id}/{revision_id}.xml.

    Returns:
        A list of dictionaries containing rule_id, article_num and article text.

    Raises:
        ValueError: If the XML is empty/invalid, the file cannot be read,
            or path/revision_id structure is invalid.
    """
    xml_path = Path(xml_file_path)
    rule_id, revision_id = _extract_rule_and_revision_id(xml_path)
    _revision_info = _parse_revision_id(rule_id, revision_id)

    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as error:
        raise ValueError(f"Invalid or empty XML: {xml_path}") from error
    except OSError as error:
        raise ValueError(f"Unable to read XML file: {xml_path}") from error

    root = tree.getroot()
    articles: list[ArticleRecord] = []

    for element in root.iter():
        if _local_name(element.tag) != "Article":
            continue

        article_num = element.attrib.get("Num", "")
        article_text = _normalize_text("".join(element.itertext()))

        articles.append(
            {
                "rule_id": rule_id,
                "article_num": article_num,
                "text": article_text,
            }
        )

    return articles
