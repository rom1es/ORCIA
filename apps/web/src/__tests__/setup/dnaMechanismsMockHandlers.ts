import { backendState, jsonResponse, problemResponse } from "./mockBackendState";

export function handleDnaMechanismsMockRoute(params: {
  path: string;
  method: string;
  body: Record<string, unknown>;
  isObserver: boolean;
}): Response | null {
  const { path, method, body, isObserver } = params;

  const dnaListMatch = path.match(/^\/api\/v1\/workspaces\/([^/]+)\/dna-mechanisms$/);
  if (dnaListMatch && method === "GET") {
    const wsId = decodeURIComponent(dnaListMatch[1] ?? "");
    const rows = backendState.dnaMechanisms
      .filter((entry) => String(entry.workspace_id) === wsId)
      .map((entry) => entry.mechanism as Record<string, unknown>);
    return jsonResponse(rows);
  }

  const dnaCompileMatch = path.match(/^\/api\/v1\/workspaces\/([^/]+)\/dna-mechanisms\/compile$/);
  if (dnaCompileMatch && method === "POST") {
    if (isObserver) {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    const wsId = decodeURIComponent(dnaCompileMatch[1] ?? "");
    const ruleId = String(body.rule_id ?? "RULE-01");
    const directiveTitle = String(body.directive_title ?? "Orientation Qualité");
    const normTitle = String(body.norm_title ?? `Règle ${ruleId}`);
    const requiredField = String(body.required_field ?? "reference_code");
    const existing = backendState.dnaMechanisms.find(
      (entry) =>
        String(entry.workspace_id) === wsId &&
        String((entry.mechanism as Record<string, unknown>).rule_id) === ruleId,
    );
    let mechanismId = existing
      ? String((existing.mechanism as Record<string, unknown>).mechanism_id)
      : "";
    if (!mechanismId) {
      backendState.dnaMechanismSeq += 1;
      mechanismId = `0195f000-0000-7000-8200-${String(backendState.dnaMechanismSeq).padStart(12, "0")}`;
    }
    const scriptName = `${ruleId.toLowerCase().replace(/[^a-z0-9_]/g, "_")}.star`;
    const mechanism: Record<string, unknown> = {
      mechanism_id: mechanismId,
      rule_id: ruleId,
      directive_title: directiveTitle,
      norm_title: normTitle,
      script_name: scriptName,
      starlark_code: `def check(ctx):\n    val = ctx.payload.get("${requiredField}", "")\n    if not val:\n        orcia_sys.emit_verdict("${ruleId}", "FAIL", "Champ ${requiredField} obligatoire")\n        return False\n    orcia_sys.emit_verdict("${ruleId}", "PASS", "Conforme")\n    return True`,
      sha256: `sha256:${ruleId.toLowerCase()}`,
      passing_test_payload:
        (body.passing_test_payload as Record<string, unknown> | undefined) ?? {
          [requiredField]: "ORCIA_VALID_01",
        },
      failing_test_payload:
        (body.failing_test_payload as Record<string, unknown> | undefined) ?? {
          [requiredField]: "invalid value!",
        },
      explanation_fr: `Vérifie automatiquement la conformité de la règle « ${ruleId} » avant chaque validation.`,
      self_corrected: Boolean(body.simulate_initial_bad_regex),
      compile_elapsed_ms: 1.4,
      verified_badge_fr: "✓ Vérifié automatiquement (cas valide + cas rejeté)",
      causal_breadcrumb: `Orientation ➔ Règle (${ruleId}) ➔ Contrôle automatique`,
      signed_and_active: true,
    };
    backendState.dnaMechanisms = [
      { workspace_id: wsId, mechanism },
      ...backendState.dnaMechanisms.filter(
        (entry) =>
          !(
            String(entry.workspace_id) === wsId &&
            String((entry.mechanism as Record<string, unknown>).rule_id) === ruleId
          ),
      ),
    ];
    return jsonResponse(mechanism);
  }

  const dnaActivateMatch = path.match(
    /^\/api\/v1\/workspaces\/([^/]+)\/dna-mechanisms\/([^/]+)\/activate$/,
  );
  if (dnaActivateMatch && method === "POST") {
    if (isObserver) {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    const wsId = decodeURIComponent(dnaActivateMatch[1] ?? "");
    const mechId = decodeURIComponent(dnaActivateMatch[2] ?? "");
    let activated: Record<string, unknown> | null = null;
    backendState.dnaMechanisms = backendState.dnaMechanisms.map((entry) => {
      const mech = entry.mechanism as Record<string, unknown>;
      if (String(entry.workspace_id) === wsId && String(mech.mechanism_id) === mechId) {
        activated = { ...mech, signed_and_active: true };
        return { workspace_id: wsId, mechanism: activated };
      }
      return entry;
    });
    if (!activated) {
      return problemResponse(
        404,
        "ERR_RESOURCE_NOT_FOUND",
        "Mécanisme ADN introuvable",
        `Mécanisme '${mechId}' introuvable pour l'espace '${wsId}'.`,
        path,
      );
    }
    return jsonResponse(activated);
  }

  return null;
}
