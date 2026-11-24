import type { TranslationDictionary } from "../types";
import { ACTIVITY_EN_LABELS } from "./activity_labels";
import { ADMIN_AND_STUDIO_EN_LABELS } from "./admin_and_studio_labels";
import { AI_MODELS_HUB_EN } from "./ai_models_hub_labels";
import { ASSISTANT_EN_LABELS } from "./assistant_labels";
import { AUTH_SETTINGS_EN_LABELS } from "./auth_settings_labels";
import { AUTONOMOUS_SUPERVISION_EN_LABELS } from "./autonomous_supervision_labels";
import { AUTONOMY_CONTRACT_EN_LABELS } from "./autonomy_contract_labels";
import { CATEGORY_A_CONTROLLER_EN_LABELS } from "./category_a_controller_labels";
import { CLIENT_ERRORS_EN_LABELS } from "./client_errors_labels";
import { CONTEXTUAL_HELP_EN } from "./contextual_help_catalog_en";
import { CORE_DOMAIN_EN_LABELS } from "./core_domain_labels_en";
import { CORE_SHELL_EN_LABELS } from "./core_shell_labels_en";
import { EPIC18_SOURCES_LABELS_EN } from "./epic18_sources_labels";
import { FEATURE_ADMIN_CATALOG_SETTINGS_EN } from "./feature_admin_catalog_settings_labels_en";
import { FEATURE_COCKPIT_GATES_EN } from "./feature_cockpit_gates_labels_en";
import { FEATURE_INBOX_ASSISTANT_EN } from "./feature_inbox_assistant_labels_en";
import { FEATURE_WORKSPACES_EN } from "./feature_workspaces_labels_en";
import { FINOPS_EN_LABELS } from "./finops_labels";
import { GATES_AND_INBOX_EN_LABELS } from "./gates_and_inbox_labels";
import { GOVERNANCE_AND_PACKS_EN_LABELS } from "./governance_and_packs_labels";
import { INBOX_AND_COCKPIT_EN_LABELS } from "./inbox_and_cockpit_labels";
import { ONTOLOGY_GLOSSARY_EN } from "./ontology_glossary_labels";
import { PROCESS_CATALOG_VSM_P1_EN } from "./process_catalog_vsm_p1_en";
import { PROCESS_CATALOG_VSM_P2_EN } from "./process_catalog_vsm_p2_en";
import { PROCESS_CATALOG_VSM_P3_EN } from "./process_catalog_vsm_p3_en";
import { PROCESS_CATALOG_WORKFLOWS_EN } from "./process_catalog_workflows_en";
import { PROCESS_ORCHESTRATION_MODES_EN_LABELS } from "./process_orchestration_modes_labels";
import { PROCESS_STUDIO_UI_EN } from "./process_studio_ui_labels_en";
import { PROCESS_VSM_EXECUTION_UI_EN } from "./process_vsm_execution_ui_labels_en";
import { PROFILE_OVERVIEW_EN_LABELS } from "./profile_overview_labels";
import {
  ROLE_DISPLAY_LABELS_EN,
  TEMP_PASSWORD_MODAL_EN,
} from "./role_display_labels";
import { REFLEXIVE_TRACE_AND_INSPECTOR_EN_LABELS } from "./reflexive_trace_and_inspector_labels";
import { RFC9457_BANNER_EN_LABELS } from "./rfc9457_banner_labels";
import { ROUTES_AND_WIZARDS_EN } from "./routes_and_wizards_labels_en";
import { SHELL_CHROME_EN } from "./shell_chrome_labels_en";
import {
  SHELL_BREADCRUMBS_AND_SCOPE_EN,
  SHELL_NOTIFICATIONS_EN,
} from "./shell_notifications_labels_en";
import { SHELL_AND_SEARCH_EN_LABELS } from "./shell_and_search_labels";
import { SHOWCASE_LABELS_EN } from "./showcase_labels_en";
import { WORKFLOW_TRIGGERS_EN_LABELS } from "./workflow_triggers_labels";

export const enDictionary: TranslationDictionary = {
  ...INBOX_AND_COCKPIT_EN_LABELS,
  ...ADMIN_AND_STUDIO_EN_LABELS,
  ...SHELL_AND_SEARCH_EN_LABELS,
  ...ASSISTANT_EN_LABELS,
  ...GOVERNANCE_AND_PACKS_EN_LABELS,
  ...ACTIVITY_EN_LABELS,
  ...FINOPS_EN_LABELS,
  ...GATES_AND_INBOX_EN_LABELS,
  ...PROCESS_ORCHESTRATION_MODES_EN_LABELS,
  ...REFLEXIVE_TRACE_AND_INSPECTOR_EN_LABELS,
  ...CORE_SHELL_EN_LABELS,
  ...CORE_DOMAIN_EN_LABELS,
  locale: "en",
  clientErrors: CLIENT_ERRORS_EN_LABELS,
  rfc9457Errors: RFC9457_BANNER_EN_LABELS,
  categoryAControllers: CATEGORY_A_CONTROLLER_EN_LABELS,
  featureCockpitGates: FEATURE_COCKPIT_GATES_EN,
  featureInboxAssistant: FEATURE_INBOX_ASSISTANT_EN,
  featureWorkspaces: FEATURE_WORKSPACES_EN,
  featureAdminCatalogSettings: FEATURE_ADMIN_CATALOG_SETTINGS_EN,
  contextualHelp: CONTEXTUAL_HELP_EN,
  shellNotifications: SHELL_NOTIFICATIONS_EN,
  shellBreadcrumbsAndScope: SHELL_BREADCRUMBS_AND_SCOPE_EN,
  shellChrome: SHELL_CHROME_EN,
  showcase: SHOWCASE_LABELS_EN,
  routesAndWizards: ROUTES_AND_WIZARDS_EN,
  aiModelsHub: AI_MODELS_HUB_EN,
  authSettings: AUTH_SETTINGS_EN_LABELS,
  autonomousSupervision: AUTONOMOUS_SUPERVISION_EN_LABELS,
  autonomyContract: AUTONOMY_CONTRACT_EN_LABELS,
  epic18Sources: EPIC18_SOURCES_LABELS_EN,
  workflowTriggers: WORKFLOW_TRIGGERS_EN_LABELS,
  processStudioUi: PROCESS_STUDIO_UI_EN,
  processVsmExecutionUi: PROCESS_VSM_EXECUTION_UI_EN,
  processCatalogWorkflows: PROCESS_CATALOG_WORKFLOWS_EN,
  processCatalogVsmP1: PROCESS_CATALOG_VSM_P1_EN,
  processCatalogVsmP2: PROCESS_CATALOG_VSM_P2_EN,
  processCatalogVsmP3: PROCESS_CATALOG_VSM_P3_EN,
  ontologyGlossary: ONTOLOGY_GLOSSARY_EN,
  profileOverview: PROFILE_OVERVIEW_EN_LABELS,
  roleDisplayLabels: ROLE_DISPLAY_LABELS_EN,
  tempPasswordModal: TEMP_PASSWORD_MODAL_EN,
};
