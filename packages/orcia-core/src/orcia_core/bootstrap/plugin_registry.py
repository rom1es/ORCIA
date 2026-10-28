"""Python `entry_points` Plugin Discovery Registry (`orcia.uri_resolvers`, `orcia.llm_gateways`).

Implements Open/Closed in-process plugin discovery (`Story 3.2c`, `M7`, `Q3: 3A`) via
`importlib.metadata.entry_points`.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from typing import Any

from orcia_core.bootstrap._internal.litellm_adapter import LiteLLMAdapter
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.ports import LLMPort

URI_RESOLVER_ENTRYPOINT_GROUP = "orcia.uri_resolvers"
LLM_GATEWAY_ENTRYPOINT_GROUP = "orcia.llm_gateways"


@dataclass(frozen=True, slots=True)
class UriSchemePluginDescriptor:
    """Descriptor for an in-process federated URI resolver plugin (`orcia.uri_resolvers`)."""

    scheme: str
    description: str
    supports_cas_pinning: bool = True


def resolve_git_scheme_plugin() -> UriSchemePluginDescriptor:
    """Entry point target for `git://` URI resolver."""
    return UriSchemePluginDescriptor(scheme="git", description="Git repository resolver (git://)")


def resolve_jira_scheme_plugin() -> UriSchemePluginDescriptor:
    """Entry point target for `jira://` URI resolver."""
    return UriSchemePluginDescriptor(scheme="jira", description="Jira issue/JQL resolver (jira://)")


def resolve_confluence_scheme_plugin() -> UriSchemePluginDescriptor:
    """Entry point target for `confluence://` URI resolver."""
    return UriSchemePluginDescriptor(
        scheme="confluence", description="Confluence page resolver (confluence://)"
    )


def resolve_db_scheme_plugin() -> UriSchemePluginDescriptor:
    """Entry point target for `db://` DDL-only URI resolver."""
    return UriSchemePluginDescriptor(scheme="db", description="DDL-only schema resolver (db://)")


def resolve_nexus_scheme_plugin() -> UriSchemePluginDescriptor:
    """Entry point target for `nexus://` artifact repository URI resolver."""
    return UriSchemePluginDescriptor(
        scheme="nexus", description="Nexus/Artifactory binary resolver (nexus://)"
    )


def resolve_orcia_scheme_plugin() -> UriSchemePluginDescriptor:
    """Entry point target for `orcia://` internal catalog URI resolver."""
    return UriSchemePluginDescriptor(
        scheme="orcia", description="Internal ORCIA catalog resolver (orcia://)"
    )


def build_litellm_gateway_plugin(**kwargs: Any) -> LLMPort:
    """Entry point target for `litellm` production LLM gateway."""
    return LiteLLMAdapter(**kwargs)


def build_cassette_gateway_plugin(**kwargs: Any) -> LLMPort:
    """Entry point target for `cassette` deterministic CI LLM gateway."""
    return DeterministicCassetteLLM(**kwargs)


DEFAULT_URI_RESOLVER_ENTRY_POINTS: tuple[EntryPoint, ...] = (
    EntryPoint(
        name="git",
        value="orcia_core.bootstrap.plugin_registry:resolve_git_scheme_plugin",
        group=URI_RESOLVER_ENTRYPOINT_GROUP,
    ),
    EntryPoint(
        name="jira",
        value="orcia_core.bootstrap.plugin_registry:resolve_jira_scheme_plugin",
        group=URI_RESOLVER_ENTRYPOINT_GROUP,
    ),
    EntryPoint(
        name="confluence",
        value="orcia_core.bootstrap.plugin_registry:resolve_confluence_scheme_plugin",
        group=URI_RESOLVER_ENTRYPOINT_GROUP,
    ),
    EntryPoint(
        name="db",
        value="orcia_core.bootstrap.plugin_registry:resolve_db_scheme_plugin",
        group=URI_RESOLVER_ENTRYPOINT_GROUP,
    ),
    EntryPoint(
        name="nexus",
        value="orcia_core.bootstrap.plugin_registry:resolve_nexus_scheme_plugin",
        group=URI_RESOLVER_ENTRYPOINT_GROUP,
    ),
    EntryPoint(
        name="orcia",
        value="orcia_core.bootstrap.plugin_registry:resolve_orcia_scheme_plugin",
        group=URI_RESOLVER_ENTRYPOINT_GROUP,
    ),
)

DEFAULT_LLM_GATEWAY_ENTRY_POINTS: tuple[EntryPoint, ...] = (
    EntryPoint(
        name="litellm",
        value="orcia_core.bootstrap.plugin_registry:build_litellm_gateway_plugin",
        group=LLM_GATEWAY_ENTRYPOINT_GROUP,
    ),
    EntryPoint(
        name="cassette",
        value="orcia_core.bootstrap.plugin_registry:build_cassette_gateway_plugin",
        group=LLM_GATEWAY_ENTRYPOINT_GROUP,
    ),
)


class PluginRegistryService:
    """Discovers and loads `orcia.uri_resolvers` and `orcia.llm_gateways` via `entry_points`."""

    @staticmethod
    def discover_uri_resolvers() -> dict[str, UriSchemePluginDescriptor]:
        """Discover all installed `orcia.uri_resolvers` plugins (`git`, `jira`, `confluence`...)."""
        discovered = list(entry_points(group=URI_RESOLVER_ENTRYPOINT_GROUP))
        active_eps = discovered if discovered else list(DEFAULT_URI_RESOLVER_ENTRY_POINTS)
        registry: dict[str, UriSchemePluginDescriptor] = {}
        for ep in active_eps:
            factory = ep.load()
            descriptor: UriSchemePluginDescriptor = factory()
            registry[ep.name] = descriptor
        return registry

    @staticmethod
    def discover_llm_gateways() -> dict[str, Any]:
        """Discover all installed `orcia.llm_gateways` factory plugins (`litellm`, `cassette`)."""
        discovered = list(entry_points(group=LLM_GATEWAY_ENTRYPOINT_GROUP))
        active_eps = discovered if discovered else list(DEFAULT_LLM_GATEWAY_ENTRY_POINTS)
        registry: dict[str, Any] = {}
        for ep in active_eps:
            registry[ep.name] = ep.load()
        return registry


__all__ = [
    "DEFAULT_LLM_GATEWAY_ENTRY_POINTS",
    "DEFAULT_URI_RESOLVER_ENTRY_POINTS",
    "LLM_GATEWAY_ENTRYPOINT_GROUP",
    "URI_RESOLVER_ENTRYPOINT_GROUP",
    "PluginRegistryService",
    "UriSchemePluginDescriptor",
    "build_cassette_gateway_plugin",
    "build_litellm_gateway_plugin",
    "resolve_confluence_scheme_plugin",
    "resolve_db_scheme_plugin",
    "resolve_git_scheme_plugin",
    "resolve_jira_scheme_plugin",
    "resolve_nexus_scheme_plugin",
    "resolve_orcia_scheme_plugin",
]
