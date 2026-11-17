# Contrat d'Intégration Plateforme OpenShift Logging (`OPS-OPENSHIFT-LOGGING-01`)

- **Identifiant Contrat** : `OPS-OPENSHIFT-LOGGING-01`
- **Références Architecture** : `AD-9`, `AD-12`, `AD-19`, `AD-23` (`AD-23.8`), `FR-28`, `NFR-OBS-1`, `NFR-SEC-1`, `NFR-SEC-4`, `Story 7.0c`
- **Cible Plateforme** : OpenShift Container Platform (`SCC restricted`), OpenShift Logging (`ClusterLogForwarder` `5.9+` / `6.0`), Elasticsearch / OpenSearch d'entreprise, OpenTelemetry Collector / Tempo.

---

## 1. Vue d'Ensemble & Principes 12-Factor

Les conteneurs ORCIA (`api`, `worker-orchestration`, `worker-indexing`, `trigger-dispatcher`, `sandbox-runner`, `web`) fonctionnent sous le profil **OpenShift SCC `restricted`** :
- UID/GID arbitraire non-root attribué dynamiquement par OpenShift (`runAsNonRoot: true`, aucun `runAsUser` ni `fsGroup` figé dans les manifestes).
- Système de fichiers racine monté en lecture seule (`readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]`).
- Aucun fichier de log technique ni état local n'est écrit sur disque : **100 % des journaux** sont émis en **JSON 1 ligne (schéma ECS)** sur `stdout`, avec les seuls répertoires temporaires montés en mémoire `tmpfs` (`emptyDir` sur `/tmp`).
- Les sondes `livenessProbe` (`GET /api/v1/health`) et `readinessProbe` (`GET /ready`) répondent en `< 100 ms` sans requête SQL lourde et leurs réponses HTTP `< 400` sont filtrées par `HealthProbeLogFilter` pour éviter le bruit d'indexation.

---

## 2. Les 4 Engagements Contractuels Plateforme (`Story 7.0c` / `AD-23.8`)

### Engagement 1 — Activation de `structuredTypeKey` sur `ClusterLogForwarder`
L'équipe Plateforme OpenShift active le parsing JSON natif sur le pipeline `ClusterLogForwarder` (`logging.openshift.io/v1` / `observability.openshift.io/v1`) pour les pods du namespace ORCIA afin de préserver sans ré-encapsulation texte les attributs ECS émis sur `stdout` (`timestamp`, `level`, `logger`, `message`, `service`, `env`, `version`, `trace_id`, `span_id`, `workspace_id`, `run_id`, `step_id`, `ctx`, `exception`).

```yaml
apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
metadata:
  name: orcia-app-logs-forwarder
  namespace: openshift-logging
spec:
  outputs:
    - name: enterprise-elasticsearch
      type: elasticsearch
      elasticsearch:
        url: https://opensearch-logs.openshift-logging.svc:9200
        index: app-orcia-prod
        structuredTypeKey: orcia.ecs
```

### Engagement 2 — Compte de Service / Clé d'API Lecture Seule Scopée pour `LogSinkQueryPort`
L'équipe Plateforme provisionne pour ORCIA un compte de service ou une clé d'API Elasticsearch/OpenSearch dédié :
- **Principe de moindre privilège** : droits **lecture seule** (`read`, `view_index_metadata`) strictement restreints au motif d'index du namespace ORCIA (`ORCIA_LOG_SINK_INDEX`, ex. `app-orcia-*`), sans aucun droit d'écriture, de suppression ni d'administration de cluster.
- **Transport sécurisé** : le jeton/clé est injecté hors Git via `Secret` OpenShift (`orcia-runtime-secrets-template` / ExternalSecrets) et résolu par `SecretProviderPort` (`SecretRef`) dans `LogSinkQueryPort`.

### Engagement 3 — Politique `NetworkPolicy` d'Egress Contrôlée
La `NetworkPolicy` du namespace ORCIA (`infra/k8s/base/networkpolicy-sandbox-runner.yaml` et `infra/k8s/base/networkpolicy-runtime-egress.yaml`) applique une séparation stricte :
1. **`orcia-sandbox-runner-isolation`** : `egress: []` (aucune sortie réseau autorisée depuis `sandbox-runner`, zéro Podman-in-Pod / conteneur imbriqué, ingress limité à `api` et `worker-orchestration` sur le port TCP `8096`).
2. **`orcia-runtime-controlled-egress`** : autorise explicitement les flux sortants de `api` et des workers vers :
   - Elasticsearch / OpenSearch d'entreprise (`TCP 9200`) pour `LogSinkQueryPort`,
   - Le collecteur OpenTelemetry / Tempo d'entreprise (`TCP 4317` gRPC / `TCP 4318` HTTP OTLP) pour les traces distribuées (`OTEL_EXPORTER_OTLP_ENDPOINT`),
   - Le data plane interne (PostgreSQL 18 `5432`, Redis `6379`, SeaweedFS `9000`, `sandbox-runner` `8096`, DNS `53`).

### Engagement 4 — Masquage Préalable Obligatoire des Secrets avant Émission (`NFR-SEC-4`)
Comme les journaux `stdout` transitent par le réseau de la plateforme vers le puits centralisé :
- Aucun secret en clair ne doit quitter le pod : le pipeline `structlog` (`mask_secrets_processor`, `scrub_sensitive_text`, `scrub_sensitive_dict`) masque systématiquement avant écriture sur `stdout` les en-têtes `Authorization: Bearer ...` / `Basic ...`, JWT (`eyJ...`), clés d'API (`sk-...`), PAT (`ghp_...`, `pat_...`), `SecretRef(...)`, `ORCIA_BOOTSTRAP_TOKEN`, champs sensibles (`password`, `secret`, `token`, `api_key`, etc.), exceptions et valeurs enregistrées via `register_sensitive_secret_value()`.
- Les variables sensibles de déploiement ne figurent jamais en clair dans `infra/k8s/base/configmap.yaml` ni dans `secret-template.yaml`.
