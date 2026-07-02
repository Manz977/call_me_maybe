from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vocab import Vocabulary
    from .models import ParameterSpec
class _TrieNode:
    def __init__(self) -> None:
        self.children: dict[str, "_TrieNode"] = {}
        self.terminal: bool = False


class NameConstraint:
    def __init__(self, valid_names: list[str]) -> None:
        self._root = _TrieNode()
        for name in valid_names:
            node = self._root
            for ch in name:
                node = node.children.setdefault(ch, _TrieNode())
            node.terminal = True

        self._node: _TrieNode = self._root
        self._done: bool = False

    def legal_tokens(self, vocab: "Vocabulary") -> "frozenset[int] | set[int]":
        if self._done:
            return set()

        reachable = self._reachable_prefixes(self._node)

        def ok(surface: str) -> bool:

            for r in reachable:
                if r.startswith(surface) or surface.startswith(r):
                    return True
            return False

        tokens = vocab.ids_where(ok)

        if self._node.terminal:
            tokens |= vocab.ids_where(lambda s: s == "\n")

        return tokens

    def advance(self, token_id: int, vocab: "Vocabulary") -> None:
        if self._done:
            return
        surface = vocab.surface(token_id)
        if surface == "\n":
            self._done = True
            return
        for ch in surface:
            if ch not in self._node.children:
                raise ValueError(f"Unexpected character {ch!r} in name constraint")
            self._node = self._node.children[ch]
        if self._node.terminal:
            self._done = True

    def is_complete(self) -> bool:
        return self._done


    @staticmethod
    def _reachable_prefixes(node: _TrieNode, max_depth: int = 32) -> list[str]:
        results: list[str] = []
        stack: list[tuple[_TrieNode, str]] = [(node, "")]
        while stack:
            cur, prefix = stack.pop()
            if cur.terminal:
                results.append(prefix)
            if len(prefix) < max_depth:
                for ch, child in cur.children.items():
                    stack.append((child, prefix + ch))
        return results

class _State:
    START = "START"
    AFTER_BRACE = "AFTER_BRACE"
    IN_KEY = "IN_KEY"
    AFTER_KEY = "AFTER_KEY"
    BEFORE_VALUE = "BEFORE_VALUE"
    IN_NUMBER = "IN_NUMBER"
    IN_STRING = "IN_STRING"
    IN_BOOL = "IN_BOOL"
    AFTER_VALUE = "AFTER_VALUE"
    DONE = "DONE"

