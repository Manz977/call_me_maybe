import json
from pathlib import Path
from pydantic import TypeAdapter, ValidationError
from src.models import FunctionDefinition, FunctionCall, PromptItem

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

    @staticmethod
    def load_prompts(path: str | Path) -> list[str]:
        raw = JsonIO._read_json(path)
        try:
            items = TypeAdapter(list[PromptItem]).validate_python(raw)
        except ValidationError as exc: 
            raise JsonIOErorr(f"Bad prompts in {path}: {exc}") from exc
        return [item.prompt for item in items]
    
    @staticmethod
    def write_results(path: str | Path, records: list[FunctionCall]) -> None:
        output_path = Path(path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump([r.model_dump() for r in records], f, indent=2)
        except OSError as exc:
            raise JsonIOErorr(f"Could not write to {path}: {exc}") from exc