from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from llm_sdk import Small_LLM_Model
    from .vocab import Vocabulary
    from .constraints import NameConstraint, JsonConstraint

MAX_STEPS = 256


class ControlledGenerationError(Exception):
    pass


class Generator:
    def __init__(
        self, model: "Small_LLM_Model", vocabulary: "Vocabulary"
    ) -> None:
        self._model = model
        self._vocab = vocabulary

    def next_logits(self, input_ids: list[int]) -> np.ndarray:
        raw = self._model.get_logits_from_input_ids(input_ids)
        return np.array(raw, dtype=np.float32)

    def generate(
        self,
        initial_ids: list[int],
        constraint: "NameConstraint | JsonConstraint",
    ) -> list[int]:
        ids = list(initial_ids)
        produced: list[int] = []

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

            logits[~mask] = -np.inf
            choice = int(np.argmax(logits))

            produced.append(choice)
            ids.append(choice)
            constraint.advance(choice, self._vocab)

        return produced
