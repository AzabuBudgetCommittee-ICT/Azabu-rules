from __future__ import annotations

import unittest

from metadata_schema import Metadata


class MetadataSchemaTest(unittest.TestCase):
    def test_valid_minimum_metadata(self) -> None:
        data = {
            "rule_id": "2023LAW1000001",
            "rule_type": "LAW",
            "rule_status": 0,
            "rule_name": "予算委員会規程",
            "rule_name_abbrev": ["予算規程"],
            "current_revision_id": "2023LAW1000001_20250301_2025LAW1000001",
            "revision_info": [
                {
                    "revision_id": "2023LAW1000001_20250301_2025LAW1000001",
                    "enforcement_date": "20250301",
                }
            ],
        }

        metadata = Metadata.model_validate(data)

        self.assertEqual("2023LAW1000001", metadata.rule_id)
        self.assertEqual(1, len(metadata.revision_info))

    def test_invalid_rule_type_raises(self) -> None:
        data = {
            "rule_id": "2023LAW1000001",
            "rule_type": "LA",
            "rule_status": 0,
            "rule_name": "予算委員会規程",
            "rule_name_abbrev": ["予算規程"],
            "current_revision_id": "2023LAW1000001_20250301_2025LAW1000001",
            "revision_info": [
                {
                    "revision_id": "2023LAW1000001_20250301_2025LAW1000001",
                    "enforcement_date": "20250301",
                }
            ],
        }

        with self.assertRaises(ValueError):
            Metadata.model_validate(data)

    def test_mismatched_enforcement_date_raises(self) -> None:
        data = {
            "rule_id": "2023LAW1000001",
            "rule_type": "LAW",
            "rule_status": 0,
            "rule_name": "予算委員会規程",
            "rule_name_abbrev": ["予算規程"],
            "current_revision_id": "2023LAW1000001_20250301_2025LAW1000001",
            "revision_info": [
                {
                    "revision_id": "2023LAW1000001_20250301_2025LAW1000001",
                    "enforcement_date": "20250302",
                }
            ],
        }

        with self.assertRaises(ValueError):
            Metadata.model_validate(data)

    def test_abbrev_kana_length_mismatch_raises(self) -> None:
        data = {
            "rule_id": "2023LAW1000001",
            "rule_type": "LAW",
            "rule_status": 0,
            "rule_name": "予算委員会規程",
            "rule_name_abbrev": ["予算規程", "委員会規程"],
            "rule_name_abbrev_kana": ["ヨサンクテイ"],
            "current_revision_id": "2023LAW1000001_20250301_2025LAW1000001",
            "revision_info": [
                {
                    "revision_id": "2023LAW1000001_20250301_2025LAW1000001",
                    "enforcement_date": "20250301",
                }
            ],
        }

        with self.assertRaises(ValueError):
            Metadata.model_validate(data)

    def test_current_revision_id_must_exist_in_revision_info(self) -> None:
        data = {
            "rule_id": "2023LAW1000001",
            "rule_type": "LAW",
            "rule_status": 0,
            "rule_name": "予算委員会規程",
            "rule_name_abbrev": ["予算規程"],
            "current_revision_id": "2023LAW1000001_20250401_2025LAW1000001",
            "revision_info": [
                {
                    "revision_id": "2023LAW1000001_20250301_2025LAW1000001",
                    "enforcement_date": "20250301",
                }
            ],
        }

        with self.assertRaises(ValueError):
            Metadata.model_validate(data)


if __name__ == "__main__":
    unittest.main()
