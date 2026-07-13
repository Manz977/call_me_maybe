"""Grammar-style constraints that keep generation on the rails.

NameConstraint walks a trie of valid function names one token at a time, and
JsonConstraint is a small state machine that only allows tokens which keep
the output a well-formed JSON object matching a given parameter schema.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vocab import Vocabulary
    from .models import ParameterSpec


class _TrieNode:
    """One node in the trie NameConstraint builds out of the valid
    function names."""

    def __init__(self) -> None:
        self.children: dict[str, "_TrieNode"] = {}
        self.terminal: bool = False


class NameConstraint:
    """Restricts generation to exactly one of a fixed set of function names."""

    def __init__(self, valid_names: list[str]) -> None:
        """Builds a trie out of the valid names and starts tracking
        position at its root."""
        self._root = _TrieNode()
        for name in valid_names:
            node = self._root
            for ch in name:
                node = node.children.setdefault(ch, _TrieNode())
            node.terminal = True

        self._node: _TrieNode = self._root
        self._done: bool = False

    def legal_tokens(self, vocab: "Vocabulary") -> "frozenset[int] | set[int]":
        """Returns every token whose surface form is consistent with
        some name still reachable from the current trie position."""
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
        """Walks the trie forward by the characters in the chosen
        token, marking the constraint done once a full name or a
        newline is hit."""
        if self._done:
            return
        surface = vocab.surface(token_id)
        if surface == "\n":
            self._done = True
            return
        for ch in surface:
            if ch not in self._node.children:
                raise ValueError(
                    f"Unexpected character {ch!r} in name constraint"
                )
            self._node = self._node.children[ch]
        if self._node.terminal:
            self._done = True

    def is_complete(self) -> bool:
        """Whether a full valid name (or the terminating newline) has
        been produced."""
        return self._done

    @staticmethod
    def _reachable_prefixes(node: _TrieNode, max_depth: int = 32) -> list[str]:
        """Collects every complete name reachable from a trie node,
        capped at max_depth characters so a pathological trie can't
        blow this up."""
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


_JSON_ESCAPE_CHARS = frozenset('"\\/bfnrtu')


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
    """A state machine that only allows tokens keeping the output
    valid JSON matching a schema."""

    MAX_STRING_TOKENS = 40

    def __init__(self, schema: dict[str, "ParameterSpec"]) -> None:
        """Sets up the state machine at its start state, with no keys
        emitted yet."""
        self._schema = schema
        self._state: str = _State.START
        self._emitted_keys: set[str] = set()
        self._current_key: str | None = None
        self._key_progress: str = ""

        self._value_buf: str = ""
        self._string_tokens: int = 0
        self._trailing_backslash: bool = False

    def legal_tokens(self, vocab: "Vocabulary") -> "frozenset[int] | set[int]":
        """Returns whatever tokens are valid next, given the current
        state and the schema's remaining keys and types."""
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
                return vocab.ids_where(lambda t: t == '"')

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
                    lambda t: t.lstrip("-").replace(".", "", 1).isdigit()
                    or t in ("+", "-")
                )
            if typ == "boolean":
                return vocab.bool_tokens

        if s == _State.IN_NUMBER:
            has_more = bool(self._remaining_keys())
            tokens = set(vocab.digit_like)
            if has_more:
                tokens |= vocab.ids_where(lambda t: t == ",")
            else:
                tokens |= vocab.ids_where(lambda t: t == "}")
            return tokens

        if s == _State.IN_STRING:
            at_cap = self._string_tokens >= self.MAX_STRING_TOKENS
            if self._trailing_backslash:
                escapes = vocab.ids_where(
                    lambda t: bool(t) and t[0] in _JSON_ESCAPE_CHARS
                )
                if at_cap:
                    return escapes - vocab.ids_where(lambda t: "\\" in t)
                return escapes
            if at_cap:
                return vocab.ids_where(lambda t: t == '"')
            return vocab.string_safe | vocab.ids_where(lambda t: t == '"')

        if s == _State.IN_BOOL:
            has_more = bool(self._remaining_keys())
            tokens = set(vocab.bool_tokens)
            if has_more:
                tokens |= vocab.ids_where(lambda t: t == ",")
            else:
                tokens |= vocab.ids_where(lambda t: t == "}")
            return tokens

        if s == _State.AFTER_VALUE:
            has_more = bool(self._remaining_keys())
            tokens = set()
            if has_more:
                tokens |= vocab.ids_where(lambda t: t == ",")
            else:
                tokens |= vocab.ids_where(lambda t: t == "}")
            return tokens

        return set()

    def advance(self, token_id: int, vocab: "Vocabulary") -> None:
        """Feeds the chosen token into the state machine, transitioning
        states and tracking keys, string length, and escaping as
        needed."""
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
                self._string_tokens = 0
                self._trailing_backslash = False
            elif typ in ("number", "integer"):
                self._state = _State.IN_NUMBER
            elif typ == "boolean":
                self._state = _State.IN_BOOL
            return

        if s == _State.IN_NUMBER:
            if surface == "}":
                self._state = _State.DONE
            elif surface == ",":
                self._state = _State.AFTER_BRACE
            else:
                self._value_buf += surface
            return

        if s == _State.IN_STRING:
            if surface == '"':
                self._state = _State.AFTER_VALUE
            else:
                self._string_tokens += 1
                for ch in surface:
                    self._trailing_backslash = (
                        ch == "\\" and not self._trailing_backslash
                    )
            return

        if s == _State.IN_BOOL:
            if surface == "}":
                self._state = _State.DONE
            elif surface == ",":
                self._state = _State.AFTER_BRACE
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
        """Whether the closing brace has been emitted and the object
        is done."""
        return self._state == _State.DONE

    def _remaining_keys(self) -> list[str]:
        """Schema keys that haven't been emitted into the JSON object yet."""
        return [k for k in self._schema if k not in self._emitted_keys]

    def _pick_next_key(self) -> str:
        """Picks the next key to emit, in schema order."""
        remaining = self._remaining_keys()
        if not remaining:
            raise RuntimeError("No keys left to emit")
        return remaining[0]
