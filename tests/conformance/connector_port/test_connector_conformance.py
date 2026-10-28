"""Conformance Test Suite for `ConnectorPort` (`AD-20`, `Story 3.2e`, `AC-E3`, `AC-E4`)."""

from __future__ import annotations

import pytest
from tests.fixtures.plugins.orcia_connector_sap_fake import (
    FakeSapErpConnector,
    register_fake_sap_connector,
)

from orcia_core.catalog.cas_resolver import FederatedUriResolver, parse_federated_uri
from orcia_core.permissions.broker_models import extract_connector_scheme
from orcia_kernel.errors import OrciaDomainError, ResourceNotFoundError, ValidationDomainError
from orcia_kernel.ports import (
    ConnectorPort,
    is_registered_connector_scheme,
    register_connector,
    unregister_connector,
)
from orcia_pack_sdlc.connectors import (
    create_confluence_connector,
    create_git_connector,
    create_jira_connector,
    create_nexus_connector,
)


@pytest.mark.parametrize(
    ("connector_factory", "sample_uri", "missing_uri", "expected_scheme", "expected_version"),
    [
        (
            create_git_connector,
            "git://claims/core-engine@main",
            "git://claims/404-not-found@main",
            "git",
            "main",
        ),
        (
            create_jira_connector,
            "jira://claims/issues/PAY-142",
            "jira://claims/issues/404-missing",
            "jira",
            "PAY-142",
        ),
        (
            create_confluence_connector,
            "confluence://CLAIMS/pages/101-spec@v12",
            "confluence://CLAIMS/pages/404-not-found@v1",
            "confluence",
            "v12",
        ),
        (
            create_nexus_connector,
            "nexus://artifacts/packs/bmad-pack.tar.gz@1.0.0",
            "nexus://artifacts/packs/404-not-found.tar.gz@1.0.0",
            "nexus",
            "1.0.0",
        ),
        (
            FakeSapErpConnector,
            "sap://erp-prod/orders/4500012345@v1",
            "sap://erp-prod/orders/404-missing@v1",
            "sap",
            "v1",
        ),
    ],
)
def test_connector_port_conformance_contract(
    connector_factory: object,
    sample_uri: str,
    missing_uri: str,
    expected_scheme: str,
    expected_version: str,
) -> None:
    """Verify every `ConnectorPort` satisfies capabilities, fetch, invoke, health & map_error."""
    connector = connector_factory()  # type: ignore[operator]
    assert isinstance(connector, ConnectorPort)

    # 1. capabilities()
    caps = connector.capabilities()
    assert caps.scheme == expected_scheme
    assert caps.supports_read is True
    assert len(caps.display_name) > 0
    assert len(caps.pack_name) > 0

    # 2. health()
    health = connector.health()
    assert health.scheme == expected_scheme
    assert health.state == "HEALTHY"
    assert health.latency_ms >= 0.0

    # 3. fetch(uri)
    fetched = connector.fetch(sample_uri)
    assert fetched.scheme == expected_scheme
    assert fetched.uri == sample_uri
    assert fetched.resolved_version == expected_version
    assert len(fetched.content_bytes) > 0
    assert len(fetched.sha256) == 64

    # 4. invoke(action, payload, idempotency_key) idempotency
    inv1 = connector.invoke(
        "sync_metadata",
        {"target_uri": sample_uri},
        idempotency_key=f"idem-{expected_scheme}-001",
    )
    assert inv1.scheme == expected_scheme
    assert inv1.replayed_from_idempotency_cache is False
    assert inv1.status == "SUCCEEDED"

    inv2 = connector.invoke(
        "sync_metadata",
        {"target_uri": sample_uri, "ignored_extra": "on_replay"},
        idempotency_key=f"idem-{expected_scheme}-001",
    )
    assert inv2.replayed_from_idempotency_cache is True
    assert inv2.output == inv1.output

    # 5. map_error(exc) -> OrciaDomainError (RFC 9457)
    with pytest.raises(ResourceNotFoundError) as not_found_exc:
        connector.fetch(missing_uri)
    assert isinstance(not_found_exc.value, OrciaDomainError)
    assert not_found_exc.value.error_code == "ERR_RESOURCE_NOT_FOUND"

    with pytest.raises(ValidationDomainError) as val_exc:
        connector.fetch("invalid://wrong-scheme/path")
    assert isinstance(val_exc.value, OrciaDomainError)
    assert val_exc.value.error_code == "ERR_VALIDATION_FAILED"


def test_fake_sap_connector_resolves_through_federated_uri_resolver_and_broker() -> None:
    """Verify `sap://` fake connector works end-to-end with 0 Core edits."""
    try:
        sap_conn = register_fake_sap_connector()
        assert is_registered_connector_scheme("sap") is True

        parsed = parse_federated_uri("sap://erp-prod/orders/4500012345@v1")
        assert parsed.scheme == "sap"
        assert parsed.authority == "erp-prod"
        assert parsed.path == "orders/4500012345"
        assert parsed.version_or_ref == "v1"

        resolver = FederatedUriResolver()
        res1 = resolver.resolve("sap://erp-prod/orders/4500012345@v1")
        assert res1.scheme == "sap"
        assert res1.resolved_version == "v1"
        assert res1.cache_hit is False
        assert res1.cas_key == f"cas/{res1.sha256}"

        res2 = resolver.resolve("sap://erp-prod/orders/4500012345@v1")
        assert res2.cache_hit is True
        assert res2.sha256 == res1.sha256

        broker_scheme = extract_connector_scheme("sap://erp-prod/orders/4500012345")
        assert broker_scheme == "sap"
        assert sap_conn.health().state == "HEALTHY"
    finally:
        unregister_connector("sap")
        register_connector(create_git_connector())
