"""SystemBootstrapWorkflowService (`FR-28`, `AD-10`, `AD-14`, `AD-16`, `UX-DR3`)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace

from orcia_core.bootstrap import models as bm
from orcia_core.bootstrap import workflow_bootstrap_seeds as wbs
from orcia_core.bootstrap.models import (
    CANONICAL_UPSTREAM_ONTOLOGY,
    VALID_ARCHETYPES,
    ModelOrthogonalityReport,
    ModelRouterService,
)
from orcia_core.catalog.models import CatalogItemEntity, CustomizationOverrideEntity, ScalarValue
from orcia_core.catalog.service import FederatedCatalogService
from orcia_core.domain import exceptions as exc
from orcia_core.domain.identifiers import new_uuid7_str
from orcia_core.permissions import models as pm
from orcia_core.permissions.broker import PermissionBrokerService
from orcia_core.permissions.broker_models import reject_control_chars as _clean
from orcia_core.permissions.service import AuthAndOrganizationService


def _sha256_json(data: dict[str, object]) -> tuple[str, str]:
    raw = json.dumps(data, sort_keys=True)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def _make_override(key: str, layer: str, ou_id: str | None, ws_id: str | None, scalars: dict[str, ScalarValue]) -> CustomizationOverrideEntity:  # noqa: E501  # fmt: skip
    _, sha = _sha256_json({"scalars": scalars})
    wf_uri = "db://orcia/catalog/payment-delivery-workflow@v1.2.0"
    return CustomizationOverrideEntity(
        id=new_uuid7_str(), override_key=key, target_uri=wf_uri,
        override_layer="TEAM" if layer == "TEAM" else "WORKSPACE",
        org_unit_id=ou_id, workspace_id=ws_id, user_id=None,
        scalars=dict(scalars), datasources=(), rules=(), facts=(), lenses=(), sha256=sha,
    )  # fmt: skip


class SystemBootstrapWorkflowService:
    """Domain service orchestrating `orcia://system/bootstrap/*` governed workflows (`FR-28`)."""

    def __init__(
        self, *, auth_service: AuthAndOrganizationService, catalog_service: FederatedCatalogService,
        permission_broker_service: PermissionBrokerService, model_router: ModelRouterService | None = None,  # noqa: E501
        workflows: tuple[bm.SystemBootstrapWorkflowSpec, ...] = (),
        runs: tuple[bm.SystemBootstrapRunRecord, ...] = (),
        onboarding_states: tuple[bm.UserOnboardingState, ...] = (),
    ) -> None:  # fmt: skip
        self.auth_service, self.catalog_service = auth_service, catalog_service
        self.permission_broker_service = permission_broker_service
        self.model_router = model_router or ModelRouterService(
            tuple(bm.LlmModelEndpoint(**asdict(s)) for s in wbs.DEFAULT_LLM_MODEL_ENDPOINT_SEEDS)
        )
        self._workflows = {w.uri: w for w in workflows}
        self._runs, self._upstream_ontology = list(runs), dict(CANONICAL_UPSTREAM_ONTOLOGY)
        self._onboarding_by_email = {st.user_email.lower(): st for st in onboarding_states}

    def list_workflows(self) -> list[bm.SystemBootstrapWorkflowSpec]: return list(self._workflows.values())  # noqa: E501  # fmt: skip

    def list_runs(self) -> list[bm.SystemBootstrapRunRecord]: return list(self._runs)  # fmt: skip

    def list_onboarding_states(self) -> list[bm.UserOnboardingState]: return list(self._onboarding_by_email.values())  # noqa: E501  # fmt: skip

    def _upsert_override(self, ovr: CustomizationOverrideEntity) -> None:
        self.catalog_service._overrides = [o for o in self.catalog_service._overrides if o.override_key != ovr.override_key] + [ovr]  # noqa: E501  # fmt: skip

    @staticmethod
    def _enforce_not_observer(user: pm.UserIdentity, *, instance: str | None = None) -> None:
        if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
            raise exc.ObserverModeReadOnlyError(instance=instance)

    def _validate_ontology_terms(self, terms: tuple[bm.OntologyTermSpec, ...], upstream: dict[str, str], *, instance: str | None = None) -> dict[str, str]:  # noqa: E501  # fmt: skip
        merged = dict(upstream)
        for term in terms:
            k, d = _clean(term.term_key, "term_key", instance=instance).lower(), _clean(term.definition, "definition", instance=instance)  # noqa: E501  # fmt: skip
            if k in merged and merged[k].strip().lower() != d.lower():
                raise exc.ValidationDomainError(detail_override=f"Ontology conflict on term '{k}'.", instance=instance)  # noqa: E501  # fmt: skip
            merged[k] = d
        return merged

    def execute_init_organization(
        self, user: pm.UserIdentity, payload: bm.InitOrganizationInput, *, instance: str | None = None  # noqa: E501
    ) -> bm.SystemBootstrapRunRecord:  # fmt: skip
        self._enforce_not_observer(user, instance=instance)
        if user.platform_role != "PLATFORM_ADMIN":
            raise exc.ScopeAccessDeniedError(instance=instance)
        org_name = _clean(payload.organization_name, "org_name", instance=instance)
        if not (payload.oidc_enabled or payload.local_argon2id_enabled):
            raise exc.ValidationDomainError(detail_override="At least one auth mode required.", instance=instance)  # noqa: E501  # fmt: skip
        if not payload.rbac_role_mappings or not _clean(payload.rbac_role_mappings.get("PLATFORM_ADMIN", ""), "rbac_role_mappings.PLATFORM_ADMIN", instance=instance):  # noqa: E501  # fmt: skip
            raise exc.ValidationDomainError(detail_override="PLATFORM_ADMIN RBAC mapping required.", instance=instance)  # noqa: E501  # fmt: skip
        orth = self.model_router.enforce_orthogonality_gate(payload.llm_endpoints, instance=instance)  # noqa: E501  # fmt: skip
        self.model_router._endpoints = {ep.endpoint_key: ep for ep in payload.llm_endpoints}
        run_id, fams = new_uuid7_str(), list(orth.distinct_families)
        run = bm.SystemBootstrapRunRecord(
            run_id, f"boot-init-org-{run_id[-6:]}", "orcia://system/bootstrap/init-organization",
            "GLOBAL", user.primary_org_unit_id, None, user.id, "COMPLETED", True,
            {"auth_rbac_valid": True, "verified_llm_families": fams, "distinct_families_count": len(fams)},  # noqa: E501
            {"organization_name": org_name, "seeded_workflows": len(self._workflows)},
        )  # fmt: skip
        self._runs.append(run)
        return run

    def execute_init_workspace(self, user: pm.UserIdentity, payload: bm.InitWorkspaceInput, *, instance: str | None = None) -> bm.InitWorkspaceOutcome:  # noqa: E501  # fmt: skip
        self._enforce_not_observer(user, instance=instance)
        if user.platform_role not in ("TEAM_LEAD", "PLATFORM_ADMIN"):
            raise exc.ScopeAccessDeniedError(instance=instance)
        t_slug, t_name = _clean(payload.team_slug, "team_slug", instance=instance), _clean(payload.team_name, "team_name", instance=instance)  # noqa: E501  # fmt: skip
        ev = self.auth_service.evaluator
        if not ev.has_org_unit(payload.parent_org_unit_id) or not payload.workspaces or bool(payload.subteam_slug) != bool(payload.subteam_name):  # noqa: E501  # fmt: skip
            raise exc.ValidationDomainError(detail_override="Valid parent_org_unit_id, subteam pair, and >= 1 Workspace required.", instance=instance)  # noqa: E501  # fmt: skip
        team_ont = self._validate_ontology_terms(payload.team_ontology_terms, self._upstream_ontology, instance=instance)  # noqa: E501  # fmt: skip
        for ws_in in payload.workspaces:
            _clean(ws_in.slug, "workspace.slug", instance=instance)
            _clean(ws_in.name, "workspace.name", instance=instance)
            _clean(ws_in.notification_channel, "workspace.notification_channel", instance=instance)
            self._validate_ontology_terms(ws_in.workspace_ontology_terms, team_ont, instance=instance)  # noqa: E501  # fmt: skip
        for mem in payload.invited_members:
            email = _clean(mem.email, "member.email", instance=instance).lower()
            _clean(mem.display_name, "member.display_name", instance=instance)
            if "@" not in email or mem.human_profile_archetype not in VALID_ARCHETYPES:
                raise exc.ValidationDomainError(detail_override=f"Invalid member {email!r}.", instance=instance)  # noqa: E501  # fmt: skip
            if user.platform_role != "PLATFORM_ADMIN" and mem.role in ("PLATFORM_ADMIN", "BU_DIRECTOR"):  # noqa: E501  # fmt: skip
                raise exc.ScopeAccessDeniedError(instance=instance)

        self._upstream_ontology.update(team_ont)
        ex_ou = next((u for u in ev.org_units if u.slug == t_slug), None)
        team_ou = pm.OrgUnitNode(ex_ou.id if ex_ou else new_uuid7_str(), t_slug, t_name, "TEAM", payload.parent_org_unit_id)  # noqa: E501  # fmt: skip
        ev.upsert_org_unit(team_ou)
        owner_ou_id = team_ou.id
        if payload.subteam_slug and payload.subteam_name:
            s_slug = _clean(payload.subteam_slug, "subteam_slug", instance=instance)
            s_name = _clean(payload.subteam_name, "subteam_name", instance=instance)
            ex_sub = next((u for u in ev.org_units if u.slug == s_slug), None)
            sub_ou = pm.OrgUnitNode(ex_sub.id if ex_sub else new_uuid7_str(), s_slug, s_name, "SUB_TEAM", team_ou.id)  # noqa: E501  # fmt: skip
            ev.upsert_org_unit(sub_ou)
            owner_ou_id = sub_ou.id

        self._upsert_override(_make_override(f"ovr-team-{t_slug}", "TEAM", owner_ou_id, None, payload.team_override_scalars))  # noqa: E501  # fmt: skip
        created_ws: list[pm.WorkspaceEntity] = []
        for ws_in in payload.workspaces:
            ex_ws = ev.get_workspace(ws_in.slug)
            if ex_ws is not None:
                ev.enforce_scope_mutation_guard(user, ex_ws.id, instance=instance)
            ws_ent = pm.WorkspaceEntity(
                ex_ws.id if ex_ws else new_uuid7_str(), ws_in.slug.strip(), ws_in.name.strip(),
                owner_ou_id, ws_in.visibility_mode, ex_ws.finops_cost_usd if ex_ws else 0.0,
                ex_ws.datasources if ex_ws else (),
            )  # fmt: skip
            ev.upsert_workspace(ws_ent)
            ev.upsert_membership(pm.WorkspaceMembershipEntity(new_uuid7_str(), ws_ent.id, user.platform_role, "CONTRIBUTOR_ACTION_REQUIRED", user.id))  # noqa: E501  # fmt: skip
            created_ws.append(ws_ent)
            ws_scalars: dict[str, ScalarValue] = {**ws_in.workspace_override_scalars, "notification_channel": ws_in.notification_channel.strip()}  # noqa: E501  # fmt: skip
            self._upsert_override(_make_override(f"ovr-ws-{ws_ent.slug}", "WORKSPACE", None, ws_ent.id, ws_scalars))  # noqa: E501  # fmt: skip

        ws_ids = tuple(w.id for w in created_ws)
        states: list[bm.UserOnboardingState] = []
        for mem in payload.invited_members:
            em = mem.email.strip().lower()
            prev = self._onboarding_by_email.get(em)
            merged_ws = tuple(dict.fromkeys([*(prev.workspace_ids if prev else ()), *ws_ids]))
            st = bm.UserOnboardingState(
                prev.id if prev else new_uuid7_str(), em, prev.user_id if prev else None, user.id,
                owner_ou_id, mem.human_profile_archetype, mem.role, merged_ws,
                prev.init_user_completed if prev else False, prev.linked_connectors if prev else (),
            )  # fmt: skip
            self._onboarding_by_email[em] = st
            states.append(st)

        run_id = new_uuid7_str()
        run = bm.SystemBootstrapRunRecord(
            run_id, f"boot-init-ws-{run_id[-6:]}", "orcia://system/bootstrap/init-workspace",
            "TEAM", owner_ou_id, created_ws[0].id, user.id, "COMPLETED", True,
            {"ontology_conflicts": [], "workspaces_created": len(created_ws), "invited_members": len(states)},  # noqa: E501
            {"team_slug": t_slug, "workspaces": [w.slug for w in created_ws]},
        )  # fmt: skip
        self._runs.append(run)
        return bm.InitWorkspaceOutcome(run, tuple(created_ws), tuple(states))

    def execute_init_datasource(
        self, user: pm.UserIdentity, payload: bm.InitDatasourceInput, *, instance: str | None = None
    ) -> bm.InitDatasourceOutcome:
        self._enforce_not_observer(user, instance=instance)
        if user.platform_role not in ("TEAM_LEAD", "PLATFORM_ADMIN"):
            raise exc.ScopeAccessDeniedError(instance=instance)
        ws = self.auth_service.evaluator.enforce_scope_mutation_guard(user, payload.workspace_id, instance=instance).workspace  # noqa: E501  # fmt: skip
        if not (1 <= payload.freshness_ttl_days <= 3650):
            raise exc.ValidationDomainError(detail_override="freshness_ttl_days out of range.", instance=instance)  # noqa: E501  # fmt: skip
        just, sig = payload.human_anchor_justification.strip(), payload.human_anchor_signature.strip()  # noqa: E501  # fmt: skip
        auth_id = (payload.human_anchor_author_id or user.id).strip()
        if (
            len(just) < 30 or len(set(just.lower())) < 5 or len(sig) < 3 or not auth_id
            or any(ord(c) < 32 and c not in ("\n", "\r", "\t") for c in just + sig)
        ):  # fmt: skip
            raise exc.HumanAnchorRequiredError(instance=instance)

        alias, uri = _clean(payload.alias, "alias", instance=instance), _clean(payload.uri, "uri", instance=instance)  # noqa: E501  # fmt: skip
        role = _clean(payload.role, "role", instance=instance)
        cql = _clean(payload.cql_filter, "cql_filter", instance=instance) if payload.cql_filter else None  # noqa: E501  # fmt: skip
        jql = _clean(payload.jql_filter, "jql_filter", instance=instance) if payload.jql_filter else None  # noqa: E501  # fmt: skip
        if not uri.lower().startswith(f"{payload.scheme}://"):
            raise exc.ValidationDomainError(detail_override=f"URI {uri!r} scheme mismatch.", instance=instance)  # noqa: E501  # fmt: skip

        pol = self.permission_broker_service.import_policy_markdown(user, payload.permission_broker_markdown, workspace_id=ws.id, instance=instance)  # noqa: E501  # fmt: skip
        if pol.connector_scheme != payload.scheme or (payload.execution_identity == "service_principal" and not pol.service_principal_allowed):  # noqa: E501  # fmt: skip
            raise exc.ValidationDomainError(detail_override="Policy scheme or execution_identity mismatch.", instance=instance)  # noqa: E501  # fmt: skip
        pol = replace(pol, human_anchor_author_id=auth_id, human_anchor_signature=sig, freshness_ttl_days=payload.freshness_ttl_days)  # noqa: E501  # fmt: skip
        self.permission_broker_service._policies[pol.policy_key] = pol

        ds_ent = pm.WorkspaceDatasourceEntity(new_uuid7_str(), ws.id, alias, payload.scheme, uri, role, payload.execution_identity, payload.freshness_ttl_days)  # noqa: E501  # fmt: skip
        kept = tuple(d for d in ws.datasources if d.alias != alias)
        self.auth_service.evaluator.upsert_workspace(replace(ws, datasources=(*kept, ds_ent)))

        meta_json, sha = _sha256_json({"alias": alias, "uri": uri, "cql_filter": cql, "jql_filter": jql, "freshness_ttl_days": payload.freshness_ttl_days, "human_anchor_signature": sig})  # noqa: E501  # fmt: skip
        res_id, vis = f"res-ds-{ws.slug}-{alias}", payload.visibility_scope
        cat_item = CatalogItemEntity(
            new_uuid7_str(), res_id, uri, payload.scheme, f"Source {alias} ({payload.scheme}://)",
            just, "datasource", "ORCIA", "v1.0.0", sha, f"cas/{sha}", vis,
            ws.owner_org_unit_id, ws.id, meta_json,
        )  # fmt: skip
        acl = pm.CatalogAclEntry(
            new_uuid7_str(), res_id, uri, cat_item.title, vis,
            ws.owner_org_unit_id, ws.id, can_discover=True, can_execute=True,
            can_read_source=True, can_edit=True, can_admin=True,
        )  # fmt: skip
        self.catalog_service.upsert_catalog_item(cat_item, acl)

        run_id = new_uuid7_str()
        run = bm.SystemBootstrapRunRecord(
            run_id, f"boot-init-ds-{run_id[-6:]}", "orcia://system/bootstrap/init-datasource",
            "WORKSPACE", ws.owner_org_unit_id, ws.id, user.id, "COMPLETED", True,
            {"human_anchor_verified": True, "freshness_ttl_days": payload.freshness_ttl_days, "policy_key": pol.policy_key},  # noqa: E501
            {"workspace_id": ws.id, "alias": alias, "uri": uri},
        )  # fmt: skip
        self._runs.append(run)
        return bm.InitDatasourceOutcome(run, ds_ent, pol, cat_item)

    def execute_init_user(
        self, user: pm.UserIdentity, payload: bm.InitUserInput, *, instance: str | None = None
    ) -> bm.InitUserOutcome:
        self._enforce_not_observer(user, instance=instance)
        em = _clean(payload.user_email or user.email, "user_email", instance=instance).lower()
        if em != user.email.lower() and user.platform_role != "PLATFORM_ADMIN":
            raise exc.ScopeAccessDeniedError(instance=instance)
        arch = _clean(payload.confirmed_human_profile_archetype, "archetype", instance=instance)
        if arch not in VALID_ARCHETYPES or not payload.passthrough_secrets:
            raise exc.ValidationDomainError(detail_override="Valid archetype and secret required.", instance=instance)  # noqa: E501  # fmt: skip
        records, schemes = [], []
        for sec in payload.passthrough_secrets:
            host = _clean(sec.target_host, "target_host", instance=instance)
            secret_val = _clean(sec.plaintext_secret, "plaintext_secret", instance=instance)
            rec = self.auth_service.store_passthrough_credential(user, connector_scheme=sec.connector_scheme, target_host=host, plaintext_secret=secret_val, instance=instance)  # noqa: E501  # fmt: skip
            self.permission_broker_service.register_passthrough_credential(rec)
            records.append(rec)
            if sec.connector_scheme not in schemes:
                schemes.append(sec.connector_scheme)

        prev = self._onboarding_by_email.get(em)
        merged_conn: tuple[pm.DatasourceScheme, ...] = tuple(dict.fromkeys([*(prev.linked_connectors if prev else ()), *schemes]))  # noqa: E501  # fmt: skip
        st = bm.UserOnboardingState(
            prev.id if prev else new_uuid7_str(), em, user.id,
            prev.invited_by_user_id if prev else user.id,
            prev.org_unit_id if prev else user.primary_org_unit_id,
            arch, prev.assigned_role if prev else user.platform_role,
            prev.workspace_ids if prev else (), True, merged_conn,
        )  # fmt: skip
        self._onboarding_by_email[em] = st
        run_id = new_uuid7_str()
        run = bm.SystemBootstrapRunRecord(
            run_id, f"boot-init-user-{run_id[-6:]}", "orcia://system/bootstrap/init-user",
            "WORKSPACE", st.org_unit_id, st.workspace_ids[0] if st.workspace_ids else None,
            user.id, "COMPLETED", True,
            {"human_profile_confirmed": arch, "encrypted_passthrough_count": len(records)},
            {"user_email": em, "linked_connectors": list(merged_conn)},
        )  # fmt: skip
        self._runs.append(run)
        return bm.InitUserOutcome(run, st, tuple(records))


__all__ = ["CANONICAL_UPSTREAM_ONTOLOGY", "VALID_ARCHETYPES", "ModelOrthogonalityReport", "ModelRouterService", "SystemBootstrapWorkflowService"]  # noqa: E501  # fmt: skip
