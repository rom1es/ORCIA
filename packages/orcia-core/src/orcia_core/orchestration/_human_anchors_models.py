"""Data Models & Validation for Human-Led Anchors & Arbitration (`Story 3.4`)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal

from orcia_core.orchestration.errors import HumanAnchorRequiredError
from orcia_core.orchestration.models import TieBreakPolicy

HumanArbitrationStatus = Literal[
    "PENDING",
    "RESOLVED_BY_HUMAN",
    "RESOLVED_BY_AXIOM",
    "DEFERRED_WITH_ASSUMPTION",
]
AuthorIdentityType = Literal["HUMAN", "AGENT"]

MIN_HUMAN_ANCHOR_CHARS = 30


@dataclass(frozen=True, slots=True)
class HumanAnchorSignatureEntity:
    """Cryptographic proof of human authorship for a `human_authored_required: true` section."""

    id: str
    signature_key: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    step_key: str
    section_key: str
    content_text: str
    content_sha256: str
    char_length: int
    authored_by_user_id: str
    author_display_name: str
    signature_hash: str


@dataclass(frozen=True, slots=True)
class ArbitrationOptionItem:
    """Single option inside an `Arbitration Tie-Break Matrix` (`UX-DR6`, `FR-5`)."""

    option_key: str
    title: str
    pros: tuple[str, ...]
    cons: tuple[str, ...]
    si_impact: str
    finops_impact: str
    recommended: bool = False
    ontology_concept_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize option item for JSONB storage and OpenAPI transport."""
        return {
            "option_key": self.option_key,
            "title": self.title,
            "pros": list(self.pros),
            "cons": list(self.cons),
            "si_impact": self.si_impact,
            "finops_impact": self.finops_impact,
            "recommended": self.recommended,
            "ontology_concept_key": self.ontology_concept_key,
        }


@dataclass(frozen=True, slots=True)
class HumanArbitrationRequestEntity:
    """Durable record in `human_arbitration_requests` (`AD-3`, `AD-18`, `UX-DR6`)."""

    id: str
    arbitration_key: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    step_key: str
    tie_break_policy: TieBreakPolicy
    status: HumanArbitrationStatus
    question_title: str
    context_summary: str
    options_matrix: tuple[ArbitrationOptionItem, ...]
    selected_option_key: str | None = None
    human_justification: str | None = None
    resolved_by_user_id: str | None = None
    resolved_by_axiom_key: str | None = None
    outbox_event_id: str | None = None


def validate_human_anchor_submission(
    content_text: str,
    signature_text: str,
    *,
    author_type: AuthorIdentityType = "HUMAN",
    instance: str | None = None,
) -> tuple[str, str, str, int]:
    """Validate human authorship (`author_type == 'HUMAN'`) and `>= 30` meaningful characters."""
    if author_type != "HUMAN":
        raise HumanAnchorRequiredError(
            detail_override=(
                "Toute écriture ou signature par une identité d'agent (author_type='AGENT') sur "
                "un champ human_authored_required: true est strictement interdite (AD-3, FR-4)."
            ),
            instance=instance,
        )
    cleaned_content = content_text.strip()
    cleaned_sig = signature_text.strip()
    char_len = len(cleaned_content)
    if (
        char_len < MIN_HUMAN_ANCHOR_CHARS
        or len(set(cleaned_content.lower())) < 5
        or len(cleaned_sig) < 3
        or any(ord(c) < 32 and c not in ("\n", "\r", "\t") for c in cleaned_content + cleaned_sig)
    ):
        raise HumanAnchorRequiredError(
            detail_override=(
                f"Une ancre humaine obligatoire exige au moins {MIN_HUMAN_ANCHOR_CHARS} "
                f"caractères significatifs rédigés et signés par un humain (reçu: {char_len})."
            ),
            instance=instance,
        )
    content_sha = hashlib.sha256(cleaned_content.encode("utf-8")).hexdigest()
    sig_hash = hashlib.sha256(f"{cleaned_sig}:{content_sha}".encode()).hexdigest()
    return cleaned_content, content_sha, sig_hash, char_len
