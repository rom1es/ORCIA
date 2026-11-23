import type { TranslationDictionary } from "../types";
import { ACTIVITY_FR_LABELS } from "./activity_labels";
import { ADMIN_AND_STUDIO_FR_LABELS } from "./admin_and_studio_labels";
import { AI_MODELS_HUB_FR } from "./ai_models_hub_labels";
import { ASSISTANT_FR_LABELS } from "./assistant_labels";
import { AUTH_SETTINGS_FR_LABELS } from "./auth_settings_labels";
import { AUTONOMOUS_SUPERVISION_FR_LABELS } from "./autonomous_supervision_labels";
import { AUTONOMY_CONTRACT_FR_LABELS } from "./autonomy_contract_labels";
import { CATEGORY_A_CONTROLLER_FR_LABELS } from "./category_a_controller_labels";
import { CLIENT_ERRORS_FR_LABELS } from "./client_errors_labels";
import { CONTEXTUAL_HELP_FR } from "./contextual_help_catalog_fr";
import { CORE_DOMAIN_FR_LABELS } from "./core_domain_labels_fr";
import { CORE_SHELL_FR_LABELS } from "./core_shell_labels_fr";
import { EPIC18_SOURCES_LABELS_FR } from "./epic18_sources_labels";
import { FEATURE_ADMIN_CATALOG_SETTINGS_FR } from "./feature_admin_catalog_settings_labels_fr";
import { FEATURE_COCKPIT_GATES_FR } from "./feature_cockpit_gates_labels_fr";
import { FEATURE_INBOX_ASSISTANT_FR } from "./feature_inbox_assistant_labels_fr";
import { FEATURE_WORKSPACES_FR } from "./feature_workspaces_labels_fr";
import { FINOPS_FR_LABELS } from "./finops_labels";
import { GATES_AND_INBOX_FR_LABELS } from "./gates_and_inbox_labels";
import { GOVERNANCE_AND_PACKS_FR_LABELS } from "./governance_and_packs_labels";
import { INBOX_AND_COCKPIT_FR_LABELS } from "./inbox_and_cockpit_labels";
import { ONTOLOGY_GLOSSARY_FR } from "./ontology_glossary_labels";
import { PROCESS_CATALOG_VSM_P1_FR } from "./process_catalog_vsm_p1_fr";
import { PROCESS_CATALOG_VSM_P2_FR } from "./process_catalog_vsm_p2_fr";
import { PROCESS_CATALOG_VSM_P3_FR } from "./process_catalog_vsm_p3_fr";
import { PROCESS_CATALOG_WORKFLOWS_FR } from "./process_catalog_workflows_fr";
import { PROCESS_ORCHESTRATION_MODES_FR_LABELS } from "./process_orchestration_modes_labels";
import { PROCESS_STUDIO_UI_FR } from "./process_studio_ui_labels_fr";
import { PROCESS_VSM_EXECUTION_UI_FR } from "./process_vsm_execution_ui_labels_fr";
import { PROFILE_OVERVIEW_FR_LABELS } from "./profile_overview_labels";
import { REFLEXIVE_TRACE_AND_INSPECTOR_FR_LABELS } from "./reflexive_trace_and_inspector_labels";
import { RFC9457_BANNER_FR_LABELS } from "./rfc9457_banner_labels";
import { ROUTES_AND_WIZARDS_FR } from "./routes_and_wizards_labels_fr";
import { SHELL_CHROME_FR } from "./shell_chrome_labels_fr";
import {
  SHELL_BREADCRUMBS_AND_SCOPE_FR,
  SHELL_NOTIFICATIONS_FR,
} from "./shell_notifications_labels_fr";
import { SHELL_AND_SEARCH_FR_LABELS } from "./shell_and_search_labels";
import { WORKFLOW_TRIGGERS_FR_LABELS } from "./workflow_triggers_labels";

export const frDictionary: TranslationDictionary = {
  ...INBOX_AND_COCKPIT_FR_LABELS,
  ...ADMIN_AND_STUDIO_FR_LABELS,
  ...SHELL_AND_SEARCH_FR_LABELS,
  ...ASSISTANT_FR_LABELS,
  ...GOVERNANCE_AND_PACKS_FR_LABELS,
  ...ACTIVITY_FR_LABELS,
  ...FINOPS_FR_LABELS,
  ...GATES_AND_INBOX_FR_LABELS,
  ...PROCESS_ORCHESTRATION_MODES_FR_LABELS,
  ...REFLEXIVE_TRACE_AND_INSPECTOR_FR_LABELS,
  ...CORE_SHELL_FR_LABELS,
  ...CORE_DOMAIN_FR_LABELS,
  locale: "fr",
  clientErrors: CLIENT_ERRORS_FR_LABELS,
  rfc9457Errors: RFC9457_BANNER_FR_LABELS,
  categoryAControllers: CATEGORY_A_CONTROLLER_FR_LABELS,
  featureCockpitGates: FEATURE_COCKPIT_GATES_FR,
  featureInboxAssistant: FEATURE_INBOX_ASSISTANT_FR,
  featureWorkspaces: FEATURE_WORKSPACES_FR,
  featureAdminCatalogSettings: FEATURE_ADMIN_CATALOG_SETTINGS_FR,
  contextualHelp: CONTEXTUAL_HELP_FR,
  shellNotifications: SHELL_NOTIFICATIONS_FR,
  shellBreadcrumbsAndScope: SHELL_BREADCRUMBS_AND_SCOPE_FR,
  shellChrome: SHELL_CHROME_FR,
  routesAndWizards: ROUTES_AND_WIZARDS_FR,
  aiModelsHub: AI_MODELS_HUB_FR,
  authSettings: AUTH_SETTINGS_FR_LABELS,
  autonomousSupervision: AUTONOMOUS_SUPERVISION_FR_LABELS,
  autonomyContract: AUTONOMY_CONTRACT_FR_LABELS,
  epic18Sources: EPIC18_SOURCES_LABELS_FR,
  workflowTriggers: WORKFLOW_TRIGGERS_FR_LABELS,
  processStudioUi: PROCESS_STUDIO_UI_FR,
  processVsmExecutionUi: PROCESS_VSM_EXECUTION_UI_FR,
  processCatalogWorkflows: PROCESS_CATALOG_WORKFLOWS_FR,
  processCatalogVsmP1: PROCESS_CATALOG_VSM_P1_FR,
  processCatalogVsmP2: PROCESS_CATALOG_VSM_P2_FR,
  processCatalogVsmP3: PROCESS_CATALOG_VSM_P3_FR,
  ontologyGlossary: ONTOLOGY_GLOSSARY_FR,
  profileOverview: PROFILE_OVERVIEW_FR_LABELS,
};
