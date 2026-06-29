from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .constraints import JsonConstraint, NameConstraint
from .models import FunctionCall, FunctionDefinition, ParameterSpec

if TYPE_CHECKING:
    from .generator import Generator
    from .vocab import Vocabulary


def _selection_prompt(prompt: str, functions: list[FunctionDefinition]) -> str:
    lines = [
        "You are a function dispatcher. Given a user request, "
        "reply with ONLY the name of the function to call — nothing else.\n",
        "Available functions:",
    ]
    for fn in functions:
        param_names = ", ".join(fn.parameters.keys())
        lines.append(f"  {fn.name}({param_names}) — {fn.description}")
    lines.append(f"\nUser request: {prompt}")
    lines.append("\nFunction name:")
    return "\n".join(lines)


def _arg_prompt(
    prompt: str,
    name: str,
    schema: dict[str, ParameterSpec],
) -> str:
    params_desc = ", ".join(
        f'"{k}": {v.type}' for k, v in schema.items()
    )
    return (
        f"You are filling in arguments for the function `{name}`.\n"
        f"Parameters: {{{params_desc}}}\n"
        f"User request: {prompt}\n"
        f"Reply with ONLY a valid JSON object containing the arguments.\n"
        f"JSON:"
    )


class FunctionCaller:
    def __init__(
        self,
        generator: "Generator",
        vocabulary: "Vocabulary",
        functions_by_name: dict[str, FunctionDefinition],
    ) -> None:
        self._generator = generator
        self._vocab = vocabulary
        self._functions_by_name = functions_by_name

    def process(self, prompt: str) -> FunctionCall:
        model = self._generator._model
        functions = list(self._functions_by_name.values())

        sel_prompt = _selection_prompt(prompt, functions)
        name_ids = self._generator.generate(
            model.encode(sel_prompt).squeeze(0).tolist(),
            NameConstraint(list(self._functions_by_name.keys())),
        )
        name = model.decode(name_ids).strip()

        schema = self._functions_by_name[name].parameters
        arg_prompt = _arg_prompt(prompt, name, schema)
        arg_ids = self._generator.generate(
            model.encode(arg_prompt).squeeze(0).tolist(),
            JsonConstraint(schema),
        )
        params = json.loads(model.decode(arg_ids))

        return FunctionCall(prompt=prompt, name=name, parameters=params)
