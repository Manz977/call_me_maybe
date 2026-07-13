"""Reading and writing the JSON files this project passes around.

JsonIO loads function definitions and prompts off disk and validates them
against the pydantic models, then serializes the resulting FunctionCall
records back out once generation is done.
"""

import json
from pathlib import Path
from pydantic import TypeAdapter, ValidationError
from src.models import FunctionDefinition, FunctionCall, PromptItem


class JsonIOErorr(Exception):
    '''Raised when an input/output file is misiing, malformed, or invalid'''


class JsonIO:
    """Static helpers for loading and validating the project's JSON
    inputs and outputs."""

    @staticmethod
    def _read_json(path: str | Path) -> object:
        """Reads and parses a JSON file, wrapping missing-file and
        parse errors in JsonIOErorr."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as exc:
            raise JsonIOErorr(f"Input file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise JsonIOErorr(f"Invalid JSON in {path}: {exc}") from exc

    @staticmethod
    def load_function_definitions(
        path: str | Path,
    ) -> list[FunctionDefinition]:
        """Loads a file's worth of function definitions and validates
        each one against the schema."""
        raw = JsonIO._read_json(path)
        try:
            return TypeAdapter(list[FunctionDefinition]).validate_python(raw)
        except ValidationError as exc:
            raise JsonIOErorr(
                f"Bad function definitions in {path}: {exc}"
            ) from exc

    @staticmethod
    def load_prompts(path: str | Path) -> list[str]:
        """Loads a file of prompt items and returns just the prompt
        strings, rejecting any that are blank."""
        raw = JsonIO._read_json(path)
        try:
            items = TypeAdapter(list[PromptItem]).validate_python(raw)
        except ValidationError as exc:
            raise JsonIOErorr(f"Bad prompts in {path}: {exc}") from exc
        return [item.prompt for item in items]

    @staticmethod
    def write_results(path: str | Path, records: list[FunctionCall]) -> None:
        """Writes the generated function calls out as JSON, creating
        parent directories if needed."""
        output_path = Path(path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump([r.model_dump() for r in records], f, indent=2)
        except OSError as exc:
            raise JsonIOErorr(f"Could not write to {path}: {exc}") from exc
