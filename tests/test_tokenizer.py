from __future__ import annotations

import unittest

from scripts.tokenizer import tokenize


class TokenizerTest(unittest.TestCase):
    def test_tokenize_filters_and_lemmatizes(self) -> None:
        text = "猫が走った。とても速い。"

        result = tokenize(text)

        self.assertIn("猫", result)
        self.assertIn("走る", result)
        self.assertIn("速い", result)
        self.assertIn("とても", result)
        self.assertNotIn("が", result)
        self.assertNotIn("。", result)

    def test_empty_string_returns_empty_list(self) -> None:
        self.assertEqual([], tokenize(""))

    def test_symbols_only_returns_empty_list(self) -> None:
        self.assertEqual([], tokenize("。、！？（）"))


if __name__ == "__main__":
    unittest.main()
