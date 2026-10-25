"""Layer 3 OpenAPI 3.1 Contract Tests (`0-diff` SDK gate + `Schemathesis` fuzzing, AD-1, AD-17)."""

from __future__ import annotations

import schemathesis
from hypothesis import given, settings
from scripts.export_openapi import export_or_check

from orcia_api.main import create_app


def test_openapi_client_zero_diff_gate() -> None:
    """Verify `packages/api-client/openapi.json` and `src/generated/schema.ts` have 0 diff."""
    exit_code = export_or_check(check_only=True)
    assert exit_code == 0, (
        "OpenAPI 3.1 schema drift detected! Run `.venv/bin/python scripts/export_openapi.py`."
    )


def test_schemathesis_openapi_contract_compliance() -> None:
    """Fuzz all registered OpenAPI 3.1 operations via Schemathesis ASGI runner."""
    app = create_app()
    schema = schemathesis.openapi.from_asgi("/openapi.json", app)

    for op_result in schema.get_all_operations():
        operation = op_result.ok()
        assert operation is not None

        @given(case=operation.as_strategy())
        @settings(max_examples=5, deadline=None)
        def _check_operation(case: schemathesis.Case) -> None:
            response = case.call()
            assert response.status_code < 500
            case.validate_response(
                response,
                excluded_checks=[schemathesis.checks.positive_data_acceptance],
            )
            if response.status_code >= 400:
                raw_ct = response.headers.get("content-type", "")
                ct_str = raw_ct[0] if isinstance(raw_ct, list) else str(raw_ct)
                assert ct_str.startswith("application/problem+json")
                payload = response.json()
                assert "error_code" in payload
                assert len(payload["trace_id"]) == 32

        _check_operation()
