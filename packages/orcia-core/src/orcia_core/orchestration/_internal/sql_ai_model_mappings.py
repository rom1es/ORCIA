"""PostgreSQL 18 facade adapter for AI Model Mappings (`Story 17.5`, `AD-21`)."""

from __future__ import annotations

from orcia_core.orchestration._internal.sql_ai_model_mutations import (
    create_ai_model_mapping_pg18,
    delete_or_drain_ai_model_mapping_pg18,
    evaluate_ai_model_delete_impact_pg18,
    record_ai_model_test_result_pg18,
    update_ai_model_mapping_pg18,
)
from orcia_core.orchestration._internal.sql_ai_model_queries import (
    COLUMNS_SELECT,
    ensure_ai_model_mappings_schema_on_postgres18,
    get_ai_model_mapping_pg18,
    list_ai_model_mappings_pg18,
    resolve_decrypted_ai_model_for_tier_pg18,
    row_to_mapping,
)

__all__ = [
    "COLUMNS_SELECT",
    "create_ai_model_mapping_pg18",
    "delete_or_drain_ai_model_mapping_pg18",
    "ensure_ai_model_mappings_schema_on_postgres18",
    "evaluate_ai_model_delete_impact_pg18",
    "get_ai_model_mapping_pg18",
    "list_ai_model_mappings_pg18",
    "record_ai_model_test_result_pg18",
    "resolve_decrypted_ai_model_for_tier_pg18",
    "row_to_mapping",
    "update_ai_model_mapping_pg18",
]
