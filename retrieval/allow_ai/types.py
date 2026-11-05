"""Immutable bounded values shared by the isolated assistance component."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Request:
    """An authored input and opaque host binding; never a credential container."""
    operation_id: str
    source: str
    intent: str
    kind: str = 'SOURCE_EDIT'
    binding: str = 'fixture'


@dataclass(frozen=True)
class PreparedAttempt:
    """Exact bytes shown to the consent authority before one dispatch."""
    operation_id: str
    attempt: int
    payload: bytes
    payload_hash: str
    model: str
    binding: str


@dataclass(frozen=True)
class Verification:
    """Trusted verifier observation, never decoded from model output."""
    status: str
    code: str | None = None
    projection: str | None = None
    source_hash: str | None = None
    evidence: dict[str, Any] | None = None


@dataclass(frozen=True)
class Result:
    """Closed terminal graph result with optional verified proposal."""
    status: str
    attempts: int
    binding: str
    source: str = ''
    explanation: str = ''
    verification: Verification | None = None
    code: str | None = None
    http_status: int | None = None


class WorkflowFailure(Exception):
    """Content-free controlled workflow denial."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
