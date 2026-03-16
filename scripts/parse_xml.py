from __future__ import annotations

from pathlib import Path
from typing import TypedDict
import xml.etree.ElementTree as ET
import re


class ArticleRecord(TypedDict):
    rule_id: str
    article_num: str
    text: str


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_rule_id(xml_path: Path) -> str:
    parts = xml_path.parts
    for index, part in enumerate(parts):
        if part == "rules" and index + 1 < len(parts):
            return parts[index + 1]
    raise ValueError(
        "XML path must include the 'rules/{rule_id}/{revision_id}.xml' structure."
    )


def parse_rule_xml(xml_file_path: str | Path) -> list[ArticleRecord]:
    """Parse e-LAWS style rule XML and extract articles.

    Args:
        xml_file_path: Path to an XML file in the form rules/{rule_id}/{revision_id}.xml.

    Returns:
        A list of dictionaries containing rule_id, article_num and article text.

    Raises:
        ValueError: If the XML is empty/invalid, the file cannot be read, or the path structure is invalid.
    """
    xml_path = Path(xml_file_path)
    rule_id = _extract_rule_id(xml_path)

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
