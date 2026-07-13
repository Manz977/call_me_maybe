"""A thin wrapper around the tokenizer's vocab file for constrained decoding.

Vocabulary loads the token-to-id table once and precomputes a handful of
useful token sets — structural JSON characters, digit-like tokens,
string-safe tokens, and boolean substrings — so the constraints don't have
to scan the whole vocab on every step.
"""

import json
import re
from pathlib import Path
from typing import Callable


_BOOL_SUBSTRINGS: frozenset[str] = frozenset(
    s
    for word in ("true", "false")
    for i in range(len(word))
    for j in range(i + 1, len(word) + 1)
    for s in (word[i:j], word[i:j].capitalize(), word[i:j].upper())
)

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


class Vocabulary:
    """Wraps a tokenizer vocab file and precomputes token sets used to
    constrain generation."""

    def __init__(self, vocab_path: str | Path) -> None:
        """Loads the token-to-id table from disk and precomputes the
        structural, digit, string-safe, and boolean token sets."""
        path = Path(vocab_path)
        raw = json.loads(path.read_text(encoding="utf-8"))

        if (
            isinstance(raw, dict)
            and isinstance(raw.get("model"), dict)
            and "vocab" in raw["model"]
        ):
            token_to_id: dict[str, int] = raw["model"]["vocab"]
        else:
            token_to_id = raw

        self._id_to_token: dict[int, str] = {
            v: k for k, v in token_to_id.items()
        }

        all_ids = set(self._id_to_token)

        self.structural: frozenset[int] = frozenset(
            i
            for i in all_ids
            if self.surface(i) in {"{", "}", '"', ":", ",", "[", "]"}
        )
        self.digit_like: frozenset[int] = frozenset(
            i
            for i in all_ids
            if re.fullmatch(r"[0-9.+\-eE]+", self.surface(i))
        )
        self.string_safe: frozenset[int] = frozenset(
            i
            for i in all_ids
            if '"' not in self.surface(i)
            and not _CONTROL_CHAR_RE.search(self.surface(i))
        )
        self.bool_tokens: frozenset[int] = frozenset(
            i for i in all_ids if self.surface(i) in _BOOL_SUBSTRINGS
        )

    def surface(self, token_id: int) -> str:
        """Returns the human-readable text a token id decodes to, with
        the tokenizer's space and newline markers translated."""
        raw = self._id_to_token[token_id]
        return raw.replace("Ġ", " ").replace("Ċ", "\n")

    def ids_where(self, predicate: "Callable[[str], bool]") -> set[int]:
        """Returns every token id whose surface form satisfies the
        given predicate."""
        return {i for i in self._id_to_token if predicate(self.surface(i))}

    def tokens_extending(self, prefix: str, candidates: set[int]) -> set[int]:
        """Filters a set of candidate token ids down to the ones whose
        surface form extends the given prefix."""
        return {i for i in candidates if self.surface(i).startswith(prefix)}
