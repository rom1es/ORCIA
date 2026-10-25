"""ORCIA Core — Hexagonal Domain, Ports, Schemas, Observability & Testing."""

from __future__ import annotations

BOUNDED_CONTEXTS: tuple[str, ...] = (
    "orchestration",
    "blackboard",
    "catalog",
    "ontology",
    "rag",
    "gates",
    "permissions",
    "audit_finops",
)

__version__ = "0.1.0"

__all__ = ["BOUNDED_CONTEXTS", "__version__"]
