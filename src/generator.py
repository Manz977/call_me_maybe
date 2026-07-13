"""The greedy decoding loop that actually drives constrained generation.

At every step it masks out whatever the active constraint disallows, applies
a repetition penalty and a no-repeat-ngram rule to keep things from looping,
and picks the top remaining token until the constraint says it's done.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from llm_sdk import Small_LLM_Model
    from .vocab import Vocabulary
    from .constraints import NameConstraint, JsonConstraint

MAX_STEPS = 256
NO_REPEAT_NGRAM_SIZE = 3
REPETITION_PENALTY = 3.0


class ControlledGenerationError(Exception):
    pass


def _banned_ngram_tokens(produced: list[int], ngram_size: int) -> set[int]:
    """Finds tokens that would recreate an ngram already seen in the
    produced sequence, so generate() can avoid repeating itself."""
    if len(produced) < ngram_size - 1:
        return set()
    prefix = tuple(produced[-(ngram_size - 1):])
    return {
        produced[i + ngram_size - 1]
        for i in range(len(produced) - ngram_size + 1)
        if tuple(produced[i:i + ngram_size - 1]) == prefix
    }


class Generator:
    """Runs greedy, constraint-masked decoding on top of the
    underlying model."""

    def __init__(
        self, model: "Small_LLM_Model", vocabulary: "Vocabulary"
    ) -> None:
        """Stores the model and vocabulary this generator will decode
        with."""
        self._model = model
        self._vocab = vocabulary

    def next_logits(self, input_ids: list[int]) -> np.ndarray:
        """Fetches the model's next-token logits for the given input
        ids as a numpy array."""
        raw = self._model.get_logits_from_input_ids(input_ids)
        return np.array(raw, dtype=np.float32)

    def generate(
        self,
        initial_ids: list[int],
        constraint: "NameConstraint | JsonConstraint",
    ) -> list[int]:
        """Greedily decodes tokens until the constraint says it's done
        or MAX_STEPS is hit.

        At each step it masks out illegal and recently-repeated tokens, applies
        a repetition penalty to the rest, and takes the highest-scoring token
        that's left, feeding it back into both the model and the constraint.
        """
        ids = list(initial_ids)
        produced: list[int] = []
        token_counts: dict[int, int] = {}

        for _ in range(MAX_STEPS):
            if constraint.is_complete():
                break

            logits = self.next_logits(ids)
            legal = constraint.legal_tokens(self._vocab)

            if not legal:
                raise ControlledGenerationError(
                    "No legal tokens available — FSM reached a dead end"
                )

            mask = np.zeros(len(logits), dtype=bool)
            for token_id in legal:
                if token_id < len(logits):
                    mask[token_id] = True

            banned = _banned_ngram_tokens(produced, NO_REPEAT_NGRAM_SIZE)
            if banned:
                unbanned = mask.copy()
                for token_id in banned:
                    if token_id < len(unbanned):
                        unbanned[token_id] = False
                if unbanned.any():
                    mask = unbanned

            logits[~mask] = -np.inf
            for token_id, count in token_counts.items():
                if mask[token_id] and token_id not in self._vocab.structural:
                    logits[token_id] -= REPETITION_PENALTY * count

            choice = int(np.argmax(logits))

            produced.append(choice)
            ids.append(choice)
            token_counts[choice] = token_counts.get(choice, 0) + 1
            constraint.advance(choice, self._vocab)

        return produced
