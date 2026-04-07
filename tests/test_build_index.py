from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.build_index import build_index


class BuildIndexTest(unittest.TestCase):
    def _write_metadata(self, metadata_dir: Path, rule_id: str, status: int = 0) -> dict:
        revision_id = f"{rule_id}_00000000_00000000000000"
        metadata = {
            "rule_id": rule_id,
            "rule_type": "LAW",
            "rule_status": status,
            "rule_name": f"{rule_id}名",
            "rule_name_abbrev": [f"{rule_id}略"],
            "current_revision_id": revision_id,
            "revision_info": [
                {
                    "revision_id": revision_id,
                    "enforcement_date": "00000000",
                }
            ],
        }
        (metadata_dir / f"{rule_id}.json").write_text(
            json.dumps(metadata, ensure_ascii=False), encoding="utf-8"
        )
        return metadata

    def _write_rule_xml(self, rules_dir: Path, rule_id: str) -> None:
        revision_id = f"{rule_id}_00000000_00000000000000"
        rule_dir = rules_dir / rule_id
        rule_dir.mkdir(parents=True, exist_ok=True)
        xml_path = rule_dir / f"{revision_id}.xml"
        xml_path.write_text(
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Law>
  <Article Num=\"1\"><ArticleCaption>第一条</ArticleCaption><Paragraph><ParagraphSentence><Sentence>猫が走る</Sentence></ParagraphSentence></Paragraph></Article>
  <Article Num=\"2\"><ArticleCaption>第二条</ArticleCaption><Paragraph><ParagraphSentence><Sentence>犬も走る</Sentence></ParagraphSentence></Paragraph></Article>
</Law>
""",
            encoding="utf-8",
        )

    def test_single_rule_update_keeps_other_rule_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata_dir = root / "metadata"
            rules_dir = root / "rules"
            search_dir = root / "public" / "search"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            rules_dir.mkdir(parents=True, exist_ok=True)
            search_dir.mkdir(parents=True, exist_ok=True)

            other_doc = {
                "doc_id": "2024LAW1000002-1",
                "rule_id": "2024LAW1000002",
                "article_num": "1",
                "text": "既存テキスト",
                "tokens": ["既存"],
            }
            (search_dir / "documents.json").write_text(
                json.dumps([other_doc], ensure_ascii=False), encoding="utf-8"
            )
            (root / "public" / "rules-index.json").write_text(
                json.dumps([
                    {
                        "rule_id": "2024LAW1000002",
                        "rule_type": "LAW",
                        "rule_status": 0,
                        "rule_name": "既存規程",
                        "rule_name_abbrev": ["既存"],
                        "current_revision_id": "2024LAW1000002_00000000_00000000000000",
                        "revision_info": [
                            {
                                "revision_id": "2024LAW1000002_00000000_00000000000000",
                                "enforcement_date": "00000000",
                            }
                        ],
                    }
                ], ensure_ascii=False),
                encoding="utf-8",
            )

            self._write_metadata(metadata_dir, "2024LAW1000002", status=0)
            self._write_metadata(metadata_dir, "2023LAW1000001", status=0)
            self._write_rule_xml(rules_dir, "2023LAW1000001")

            with patch("scripts.build_index.tokenize", lambda text: text.split()):
                build_index(rule_ids=["2023LAW1000001"], project_root=root)

            documents = json.loads((search_dir / "documents.json").read_text(encoding="utf-8"))
            doc_ids = {item["doc_id"] for item in documents}

            self.assertIn("2024LAW1000002-1", doc_ids)
            self.assertIn("2023LAW1000001-1", doc_ids)
            self.assertIn("2023LAW1000001-2", doc_ids)

    def test_full_build_includes_all_metadata_in_rules_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata_dir = root / "metadata"
            rules_dir = root / "rules"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            rules_dir.mkdir(parents=True, exist_ok=True)

            metadata_a = self._write_metadata(metadata_dir, "2023LAW1000001", status=0)
            metadata_b = self._write_metadata(metadata_dir, "2024LAW1000002", status=0)
            self._write_rule_xml(rules_dir, "2023LAW1000001")
            self._write_rule_xml(rules_dir, "2024LAW1000002")

            with patch("scripts.build_index.tokenize", lambda text: text.split()):
                build_index(rule_ids=None, project_root=root)

            rules_index = json.loads((root / "public" / "rules-index.json").read_text(encoding="utf-8"))
            self.assertEqual([metadata_a, metadata_b], rules_index)

    def test_non_zero_rule_status_excluded_from_search_but_kept_in_rules_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata_dir = root / "metadata"
            rules_dir = root / "rules"
            search_dir = root / "public" / "search"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            rules_dir.mkdir(parents=True, exist_ok=True)
            search_dir.mkdir(parents=True, exist_ok=True)

            inactive_rule_id = "2023LAW1000001"
            inactive_metadata = self._write_metadata(metadata_dir, inactive_rule_id, status=1)
            self._write_rule_xml(rules_dir, inactive_rule_id)

            (search_dir / "documents.json").write_text(
                json.dumps(
                    [
                        {
                            "doc_id": f"{inactive_rule_id}-1",
                            "rule_id": inactive_rule_id,
                            "article_num": "1",
                            "text": "古いデータ",
                            "tokens": ["古い"],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch("scripts.build_index.tokenize", lambda text: text.split()):
                build_index(rule_ids=[inactive_rule_id], project_root=root)

            documents = json.loads((search_dir / "documents.json").read_text(encoding="utf-8"))
            self.assertEqual([], documents)

            rules_index = json.loads((root / "public" / "rules-index.json").read_text(encoding="utf-8"))
            self.assertEqual([inactive_metadata], rules_index)

    def test_differential_build_cleans_removed_rule_from_documents_and_rules_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata_dir = root / "metadata"
            rules_dir = root / "rules"
            search_dir = root / "public" / "search"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            rules_dir.mkdir(parents=True, exist_ok=True)
            search_dir.mkdir(parents=True, exist_ok=True)

            kept_rule = "2023LAW1000001"
            removed_rule = "2024LAW1000002"

            kept_metadata = self._write_metadata(metadata_dir, kept_rule, status=0)
            self._write_rule_xml(rules_dir, kept_rule)

            (search_dir / "documents.json").write_text(
                json.dumps(
                    [
                        {
                            "doc_id": f"{kept_rule}-1",
                            "rule_id": kept_rule,
                            "article_num": "1",
                            "text": "既存",
                            "tokens": ["既存"],
                        },
                        {
                            "doc_id": f"{removed_rule}-1",
                            "rule_id": removed_rule,
                            "article_num": "1",
                            "text": "削除対象",
                            "tokens": ["削除"],
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            (root / "public" / "rules-index.json").write_text(
                json.dumps(
                    [
                        kept_metadata,
                        {
                            "rule_id": removed_rule,
                            "rule_type": "LAW",
                            "rule_status": 0,
                            "rule_name": "削除済み規程",
                            "rule_name_abbrev": ["削除"],
                            "current_revision_id": f"{removed_rule}_00000000_00000000000000",
                            "revision_info": [
                                {
                                    "revision_id": f"{removed_rule}_00000000_00000000000000",
                                    "enforcement_date": "00000000",
                                }
                            ],
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch("scripts.build_index.tokenize", lambda text: text.split()):
                build_index(rule_ids=[kept_rule], project_root=root)

            documents = json.loads((search_dir / "documents.json").read_text(encoding="utf-8"))
            self.assertTrue(all(item["rule_id"] != removed_rule for item in documents))

            rules_index = json.loads((root / "public" / "rules-index.json").read_text(encoding="utf-8"))
            self.assertEqual([kept_metadata], rules_index)

    def test_differential_build_cleans_inactive_rule_even_when_not_targeted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata_dir = root / "metadata"
            rules_dir = root / "rules"
            search_dir = root / "public" / "search"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            rules_dir.mkdir(parents=True, exist_ok=True)
            search_dir.mkdir(parents=True, exist_ok=True)

            target_rule = "2023LAW1000001"
            inactive_rule = "2024LAW1000002"

            self._write_metadata(metadata_dir, target_rule, status=0)
            self._write_rule_xml(rules_dir, target_rule)
            self._write_metadata(metadata_dir, inactive_rule, status=1)

            (search_dir / "documents.json").write_text(
                json.dumps(
                    [
                        {
                            "doc_id": f"{target_rule}-1",
                            "rule_id": target_rule,
                            "article_num": "1",
                            "text": "既存",
                            "tokens": ["既存"],
                        },
                        {
                            "doc_id": f"{inactive_rule}-1",
                            "rule_id": inactive_rule,
                            "article_num": "1",
                            "text": "非有効",
                            "tokens": ["非有効"],
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch("scripts.build_index.tokenize", lambda text: text.split()):
                build_index(rule_ids=[target_rule], project_root=root)

            documents = json.loads((search_dir / "documents.json").read_text(encoding="utf-8"))
            self.assertTrue(all(item["rule_id"] != inactive_rule for item in documents))

    def test_invalid_rule_id_input_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata_dir = root / "metadata"
            metadata_dir.mkdir(parents=True, exist_ok=True)

            self._write_metadata(metadata_dir, "2023LAW1000001", status=0)

            with self.assertRaises(ValueError):
                build_index(rule_ids=["../etc/passwd"], project_root=root)


if __name__ == "__main__":
    unittest.main()