from pydantic import BaseModel
from typing import Any


class ParameterSpec(BaseModel):
    type: str
    description: str


class FunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, ParameterSpec]
    returns: ParameterSpec


class FunctionCall(BaseModel):
    prompt: str
    name: str
    parameters: dict[str, Any]


TYPE_MAP: dict[str, type] = {
    "number": float,
    "string": str,
    "boolean": bool,
    "integer": int
}
