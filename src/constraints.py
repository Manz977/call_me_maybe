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


class JsonConstraint:
    def __init__(self, schema: dict[str, "ParameterSpec"]) -> None:
        self._schema = schema
        self._state: str = _State.START
        self._emitted_keys: set[str] = set()
        self._current_key: str | None = None
        self._key_progress: str = ""

        self._value_buf: str = ""

    def legal_tokens(self, vocab: "Vocabulary") -> "frozenset[int] | set[int]":
        s = self._state

        if s == _State.START:
            return vocab.ids_where(lambda t: t == "{")

        if s == _State.AFTER_BRACE:
            tokens = vocab.ids_where(lambda t: t == '"')
            if not self._remaining_keys():
                tokens |= vocab.ids_where(lambda t: t == "}")
            return tokens

        if s == _State.IN_KEY:
            assert self._current_key is not None
            remaining = self._current_key[len(self._key_progress):]
            if not remaining:
                # key fully emitted — next must be closing quote
                return vocab.ids_where(lambda t: t == '"')
            # tokens that are a prefix of or equal to remaining
            def key_ok(surface: str) -> bool:
                return remaining.startswith(surface) or surface == remaining
            return vocab.ids_where(key_ok)

        if s == _State.AFTER_KEY:
            return vocab.ids_where(lambda t: t == ":")

        if s == _State.BEFORE_VALUE:
            assert self._current_key is not None
            typ = self._schema[self._current_key].type
            if typ == "string":
                return vocab.ids_where(lambda t: t == '"')
            if typ in ("number", "integer"):
                return vocab.structural & vocab.digit_like | vocab.ids_where(
                    lambda t: t.lstrip("-").replace(".", "", 1).isdigit() or t in ("+", "-")
                )
            if typ == "boolean":
                return vocab.bool_tokens

        if s == _State.IN_NUMBER:
            has_more = bool(self._remaining_keys())
            tokens = set(vocab.digit_like)
            tokens |= vocab.ids_where(lambda t: t == "}")
            if has_more:
                tokens |= vocab.ids_where(lambda t: t == ",")
            return tokens

        if s == _State.IN_STRING:
            return vocab.string_safe | vocab.ids_where(lambda t: t == '"')

        if s == _State.IN_BOOL:
            has_more = bool(self._remaining_keys())
            tokens = set(vocab.bool_tokens)
            tokens |= vocab.ids_where(lambda t: t == "}")
            if has_more:
                tokens |= vocab.ids_where(lambda t: t == ",")
            return tokens

        if s == _State.AFTER_VALUE:
            has_more = bool(self._remaining_keys())
            tokens: set[int] = vocab.ids_where(lambda t: t == "}")
            if has_more:
                tokens |= vocab.ids_where(lambda t: t == ",")
            return tokens

        return set() 

    def advance(self, token_id: int, vocab: "Vocabulary") -> None:
        surface = vocab.surface(token_id)
        s = self._state

        if s == _State.START:
            if surface == "{":
                self._state = _State.AFTER_BRACE
            return

        if s == _State.AFTER_BRACE:
            if surface == "}":
                self._state = _State.DONE
            elif surface == '"':
                self._current_key = self._pick_next_key()
                self._key_progress = ""
                self._state = _State.IN_KEY
            return

        if s == _State.IN_KEY:
            assert self._current_key is not None
            remaining = self._current_key[len(self._key_progress):]
            if surface == '"' and not remaining:
                # closing quote — key fully written
                self._emitted_keys.add(self._current_key)
                self._state = _State.AFTER_KEY
            else:
                self._key_progress += surface
            return

        if s == _State.AFTER_KEY:
            if surface == ":":
                self._state = _State.BEFORE_VALUE
            return

        if s == _State.BEFORE_VALUE:
            assert self._current_key is not None
            typ = self._schema[self._current_key].type
            self._value_buf = surface
            if typ == "string":
                self._state = _State.IN_STRING
            elif typ in ("number", "integer"):
                self._state = _State.IN_NUMBER
            elif typ == "boolean":
                self._state = _State.IN_BOOL
            return

        if s == _State.IN_NUMBER:
            if surface == "}":
                self._state = _State.DONE
            elif surface == ",":
                self._state = _State.AFTER_BRACE  # comma already consumed
            else:
                self._value_buf += surface
            return

        if s == _State.IN_STRING:
            if surface == '"':
                self._state = _State.AFTER_VALUE
            return

        if s == _State.IN_BOOL:
            if surface == "}":
                self._state = _State.DONE
            elif surface == ",":
                self._state = _State.AFTER_BRACE  # comma already consumed
            else:
                self._value_buf += surface
            return

        if s == _State.AFTER_VALUE:
            if surface == "}":
                self._state = _State.DONE
            elif surface == ",":
                self._state = _State.AFTER_BRACE
            return

    def is_complete(self) -> bool:
        return self._state == _State.DONE

    def _remaining_keys(self) -> list[str]:
        return [k for k in self._schema if k not in self._emitted_keys]

    def _pick_next_key(self) -> str:
        remaining = self._remaining_keys()
        if not remaining:
            raise RuntimeError("No keys left to emit")
        return remaining[0]
