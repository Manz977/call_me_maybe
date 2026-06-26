import json
from pathlib import Path
from pydantic import TypeAdapter, ValidationError
from src.models import FunctionDefinition, FunctionCall

class JsonIOErorr (Exception):
    '''Raised when an input/output file is misiing, malformed, or invalid'''


class JsonIO:
    @staticmethod
    def _read_json(path: str | Path) -> object:
        try:
            with open(path, "r", encoding="uft-8") as f:
                return json.load(f)
        except FileNotFoundError as exc:
            raise JsonIOErorr(f"Input file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise JsonIOErorr(f"Invalid JSON in {path}: {exc}") from exc

    @staticmethod
    def load_function_definitions(path: str | Path) -> list[FunctionDefinition]:
        raw = JsonIO._read_json(path)
        try:
            return TypeAdapter(list[FunctionDefinition]).validate_python(raw)
        except ValidationError as exc:
            raise JsonIOErorr(f"Bad function definitions in {path}: {exc}") from exc


