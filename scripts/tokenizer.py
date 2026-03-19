from __future__ import annotations

from sudachipy import dictionary, tokenizer


_TOKENIZER = dictionary.Dictionary().create()
_ALLOWED_POS = {"名詞", "動詞", "形容詞", "形状詞", "副詞"}


def _normalize_lemma(lemma: str, fallback: str) -> str:
    if lemma and lemma != "*":
        return lemma
    if fallback and fallback != "*":
        return fallback
    return ""


def tokenize(text: str) -> list[str]:
    if not text or not text.strip():
        return []

    tokens: list[str] = []
    morphemes = _TOKENIZER.tokenize(text, tokenizer.Tokenizer.SplitMode.C)

    for morpheme in morphemes:
        pos = morpheme.part_of_speech()
        if not pos or pos[0] not in _ALLOWED_POS:
            continue

        lemma = _normalize_lemma(morpheme.dictionary_form(), morpheme.normalized_form())
        if lemma:
            tokens.append(lemma)

    return tokens
