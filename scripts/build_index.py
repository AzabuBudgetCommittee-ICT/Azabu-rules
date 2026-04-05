from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from metadata_schema import Metadata
from scripts.parse_xml import ArticleRecord, parse_rule_xml
from scripts.resolve_current_revision import resolve_current_revision
from scripts.tokenizer import tokenize


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _list_all_rule_ids(metadata_dir: Path) -> list[str]:
    return sorted(path.stem for path in metadata_dir.glob("*.json"))


def _load_metadata(metadata_path: Path) -> tuple[dict[str, Any], Metadata]:
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    model = Metadata.model_validate(raw)
    return raw, model


def _build_documents(rule_id: str, articles: list[ArticleRecord]) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    for article in articles:
        article_num = article.get("article_num", "")
        text = article.get("text", "")
        documents.append(
            {
                "doc_id": f"{rule_id}-{article_num}",
                "rule_id": rule_id,
                "article_num": article_num,
                "text": text,
                "tokens": tokenize(text),
            }
        )

    documents.sort(key=lambda item: item["doc_id"])
    return documents


def _build_search_index(documents: list[dict[str, Any]]) -> dict[str, Any]:
    token_to_doc_ids: dict[str, set[str]] = {}

    for document in documents:
        doc_id = document["doc_id"]
        for token in document.get("tokens", []):
            token_to_doc_ids.setdefault(token, set()).add(doc_id)

    serialized = {
        token: sorted(doc_ids)
        for token, doc_ids in sorted(token_to_doc_ids.items(), key=lambda item: item[0])
    }

    return {
        "token_to_doc_ids": serialized,
    }


def _resolve_target_rule_ids(metadata_dir: Path, requested_rule_ids: list[str] | None) -> list[str]:
    if requested_rule_ids is None:
        return _list_all_rule_ids(metadata_dir)
    return sorted(set(requested_rule_ids))


def build_index(rule_ids: list[str] | None = None, project_root: Path | None = None) -> None:
    root = project_root or _repo_root()
    metadata_dir = root / "metadata"
    rules_dir = root / "rules"

    public_dir = root / "public"
    search_dir = public_dir / "search"

    documents_path = search_dir / "documents.json"
    search_index_path = search_dir / "search-index.json"
    rules_index_path = public_dir / "rules-index.json"

    target_rule_ids = _resolve_target_rule_ids(metadata_dir, rule_ids)
    target_rule_id_set = set(target_rule_ids)

    existing_documents: list[dict[str, Any]] = _load_json(documents_path, [])
    untouched_documents = [
        document
        for document in existing_documents
        if document.get("rule_id") not in target_rule_id_set
    ]

    existing_rules_index: list[dict[str, Any]] = _load_json(rules_index_path, [])
    existing_rules_by_id = {
        str(item.get("rule_id")): item
        for item in existing_rules_index
        if isinstance(item, dict) and item.get("rule_id")
    }

    new_documents: list[dict[str, Any]] = []
    updated_rules_by_id = dict(existing_rules_by_id)

    for rule_id in target_rule_ids:
        metadata_path = metadata_dir / f"{rule_id}.json"
        if not metadata_path.exists():
            raise ValueError(f"Metadata file not found: {metadata_path}")

        metadata_raw, metadata_model = _load_metadata(metadata_path)
        updated_rules_by_id[rule_id] = metadata_raw

        # rule_statusが0以外の規則は、検索対象に含めない。
        if metadata_model.rule_status.value != 0:
            continue

        revision_id = resolve_current_revision(metadata_path)
        xml_path = rules_dir / rule_id / f"{revision_id}.xml"
        articles = parse_rule_xml(xml_path)
        new_documents.extend(_build_documents(rule_id, articles))

    merged_documents = untouched_documents + new_documents
    merged_documents.sort(key=lambda item: item["doc_id"])
    search_index = _build_search_index(merged_documents)

    updated_rules_index = [updated_rules_by_id[rule_id] for rule_id in sorted(updated_rules_by_id)]

    _write_json(documents_path, merged_documents)
    _write_json(search_index_path, search_index)
    _write_json(rules_index_path, updated_rules_index)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build documents/search-index/rules-index with differential updates."
    )
    parser.add_argument(
        "--rule-ids",
        nargs="+",
        help="target rule_ids. if omitted, all metadata/*.json will be processed.",
    )
    args = parser.parse_args()

    build_index(rule_ids=args.rule_ids)


if __name__ == "__main__":
    main()