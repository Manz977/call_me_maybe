"""Ties the generator and constraints together into an actual function call.

Given a raw user prompt, this module first asks the model to pick a function
name under a name only constraint, then asks it to fill in the arguments
under a JSON constraint built from that function's parameter schema.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .constraints import JsonConstraint, NameConstraint
from .models import TYPE_MAP, FunctionCall, FunctionDefinition, ParameterSpec

if TYPE_CHECKING:
    from .generator import Generator
    from .vocab import Vocabulary


def _selection_prompt(prompt: str, functions: list[FunctionDefinition]) -> str:
    """Builds the prompt that gets the model to name which function to call.

    Every candidate function is listed with its signature and description so
    the model has enough to go on when picking one.
    """
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
    """Builds the prompt that gets the model to fill in a function's arguments.

    It's explicitly told to copy values straight out of the user request
    rather than computing the actually function.
    """
    params_desc = ", ".join(
        f'"{k}": {v.type}' for k, v in schema.items()
    )
    return (
        f"You are filling in arguments for the function `{name}`.\n"
        f"Parameters: {{{params_desc}}}\n"
        f"User request: {prompt}\n"
        f"Reply with ONLY a valid JSON object containing the arguments, "
        f"using values copied verbatim from the user request — "
        f"do not compute, transform, or evaluate the function yourself.\n"
        f"JSON:"
    )


class FunctionCaller:
    """Turns a natural language prompt into a validated FunctionCall."""

    def __init__(
        self,
        generator: "Generator",
        vocabulary: "Vocabulary",
        functions_by_name: dict[str, FunctionDefinition],
    ) -> None:
        """Stores the generator, vocabulary,
        and functions this caller can dispatch to."""
        self._generator = generator
        self._vocab = vocabulary
        self._functions_by_name = functions_by_name

    def process(self, prompt: str) -> FunctionCall:
        """Resolves one prompt into a function call,
        name first and then arguments.

        The model picks a function name under a NameConstraint, then fills
        in that function's arguments under a JsonConstraint built from its
        schema, with the resulting values cast to their declared types.
        """
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
        params = {
            key: TYPE_MAP[schema[key].type](value)
            for key, value in params.items()
        }

        return FunctionCall(prompt=prompt, name=name, parameters=params)
