from pydantic import BaseModel, field_validator, Field
from typing import Any


class ParameterSpec(BaseModel):
    type: str
    description: str = ""


class FunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, ParameterSpec]
    returns: ParameterSpec

class PromptItem(BaseModel):
    prompt: str = Field(min_length=1)

    @field_validator("prompt")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt must not be blank")
        return v
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
