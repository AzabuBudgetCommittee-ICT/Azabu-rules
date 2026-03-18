from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from scripts.resolve_current_revision import (
    resolve_current_revision,
    resolve_current_revision_from_metadata,
)


class ResolveCurrentRevisionTest(unittest.TestCase):
    def test_mixed_effective_dates(self) -> None:
        metadata = {
            "revisions": [
                {
                    "revision_id": "2023LAW1000001_00000000_000000000000000",
                    "effective_date": "00000000",
                },
                {
                    "revision_id": "2023LAW1000001_20240101_2024LAW1000001",
                    "effective_date": "20240101",
                },
                {
                    "revision_id": "2023LAW1000001_XXXXXXXX_2025LAW1000001",
                    "effective_date": "XXXXXXXX",
                },
                {
                    "revision_id": "2023LAW1000001_20270401_2026LAW1000001",
                    "effective_date": "20270401",
                },
                {
                    "revision_id": "2023LAW1000001_20260301_2026LAW1000002",
                    "effective_date": "20260301",
                },
            ]
        }

        result = resolve_current_revision_from_metadata(metadata, today=date(2026, 3, 18))

        self.assertEqual("2023LAW1000001_20260301_2026LAW1000002", result)

    def test_unknown_effective_date_zero_is_candidate(self) -> None:
        metadata = {
            "revisions": [
                {
                    "revision_id": "2023LAW1000001_XXXXXXXX_2025LAW1000001",
                    "effective_date": "XXXXXXXX",
                },
                {
                    "revision_id": "2023LAW1000001_00000000_000000000000000",
                    "effective_date": "00000000",
                },
            ]
        }

        result = resolve_current_revision_from_metadata(metadata, today=date(2026, 3, 18))

        self.assertEqual("2023LAW1000001_00000000_000000000000000", result)

    def test_returns_none_when_no_candidate(self) -> None:
        metadata = {
            "revisions": [
                {
                    "revision_id": "2023LAW1000001_XXXXXXXX_2025LAW1000001",
                    "effective_date": "XXXXXXXX",
                },
                {
                    "revision_id": "2023LAW1000001_20270401_2026LAW1000001",
                    "effective_date": "20270401",
                },
            ]
        }

        result = resolve_current_revision_from_metadata(metadata, today=date(2026, 3, 18))

        self.assertIsNone(result)

    def test_re_evaluation_after_metadata_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "sample.json"

            first_metadata = {
                "revisions": [
                    {
                        "revision_id": "2023LAW1000001_20250101_2025LAW1000001",
                        "effective_date": "20250101",
                    },
                    {
                        "revision_id": "2023LAW1000001_20270401_2026LAW1000001",
                        "effective_date": "20270401",
                    },
                ]
            }
            metadata_path.write_text(
                json.dumps(first_metadata, ensure_ascii=False), encoding="utf-8"
            )

            first_result = resolve_current_revision(
                metadata_path, today=date(2026, 3, 18)
            )
            self.assertEqual("2023LAW1000001_20250101_2025LAW1000001", first_result)

            updated_metadata = {
                "revisions": [
                    {
                        "revision_id": "2023LAW1000001_20250101_2025LAW1000001",
                        "effective_date": "20250101",
                    },
                    {
                        "revision_id": "2023LAW1000001_20260201_2026LAW1000001",
                        "effective_date": "20260201",
                    },
                ]
            }
            metadata_path.write_text(
                json.dumps(updated_metadata, ensure_ascii=False), encoding="utf-8"
            )

            second_result = resolve_current_revision(
                metadata_path, today=date(2026, 3, 18)
            )
            self.assertEqual("2023LAW1000001_20260201_2026LAW1000001", second_result)

    def test_uses_effective_date_in_revision_id_if_missing(self) -> None:
        metadata = {
            "revisions": [
                {"revision_id": "2023LAW1000001_20250301_2025LAW1000001"},
                {"revision_id": "2023LAW1000001_20260201_2026LAW1000001"},
            ]
        }

        result = resolve_current_revision_from_metadata(metadata, today=date(2026, 3, 18))

        self.assertEqual("2023LAW1000001_20260201_2026LAW1000001", result)


if __name__ == "__main__":
    unittest.main()