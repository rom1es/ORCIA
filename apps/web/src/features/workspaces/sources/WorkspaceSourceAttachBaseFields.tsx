import React from "react";
import type { EnterpriseConnectorItemResponse } from "@orcia/api-client";
import { FormInput, modalInputStyle } from "./WorkspaceSourceAttachCodegraphFields";

export type WorkspaceSourceNature =
  | "DOCUMENT_KB"
  | "WORK_TRACKER"
  | "SOURCE_CODE"
  | "RELATIONAL_SCHEMA";

export interface WorkspaceSourceAttachBaseFieldsProps {
  readonly nature: WorkspaceSourceNature;
  readonly connectorId: string;
  readonly alias: string;
  readonly scheme: string;
  readonly uri: string;
  readonly connectors: readonly EnterpriseConnectorItemResponse[];
  readonly hasActiveEmbeddingModel: boolean;
  readonly copy: {
    readonly natureLabel: string;
    readonly natureDoc: string;
    readonly natureTracker: string;
    readonly natureCode: string;
    readonly natureSchema: string;
    readonly ragOptionDisabledSuffix: string;
    readonly connectorLabel: string;
    readonly connectorNone: string;
    readonly aliasLabel: string;
    readonly aliasPlaceholder: string;
    readonly schemeLabel: string;
    readonly uriLabel: string;
    readonly uriPlaceholder: string;
  };
  readonly onNatureChange: (nature: WorkspaceSourceNature) => void;
  readonly onConnectorIdChange: (connectorId: string) => void;
  readonly onAliasChange: (alias: string) => void;
  readonly onSchemeChange: (scheme: string) => void;
  readonly onUriChange: (uri: string) => void;
}

export function WorkspaceSourceAttachBaseFields({
  nature,
  connectorId,
  alias,
  scheme,
  uri,
  connectors,
  hasActiveEmbeddingModel,
  copy,
  onNatureChange,
  onConnectorIdChange,
  onAliasChange,
  onSchemeChange,
  onUriChange,
}: WorkspaceSourceAttachBaseFieldsProps): React.ReactElement {
  return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
        <div>
          <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.natureLabel}</label>
          <select
            data-testid="modal-source-nature-select"
            value={nature}
            onChange={(e) => onNatureChange(e.target.value as WorkspaceSourceNature)}
            style={modalInputStyle}
          >
            <option value="DOCUMENT_KB" disabled={!hasActiveEmbeddingModel}>
              {copy.natureDoc}
              {!hasActiveEmbeddingModel ? copy.ragOptionDisabledSuffix : ""}
            </option>
            <option value="WORK_TRACKER" disabled={!hasActiveEmbeddingModel}>
              {copy.natureTracker}
              {!hasActiveEmbeddingModel ? copy.ragOptionDisabledSuffix : ""}
            </option>
            <option value="SOURCE_CODE">{copy.natureCode}</option>
            <option value="RELATIONAL_SCHEMA" disabled={!hasActiveEmbeddingModel}>
              {copy.natureSchema}
              {!hasActiveEmbeddingModel ? copy.ragOptionDisabledSuffix : ""}
            </option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.connectorLabel}</label>
          <select
            data-testid="modal-connector-select"
            value={connectorId}
            onChange={(e) => onConnectorIdChange(e.target.value)}
            style={modalInputStyle}
          >
            <option value="">{copy.connectorNone}</option>
            {connectors.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.connector_kind})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
        <div>
          <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.aliasLabel} *</label>
          <FormInput
            testId="modal-source-alias-input"
            type="text"
            required
            placeholder={copy.aliasPlaceholder}
            value={alias}
            onChange={(e) => onAliasChange(e.target.value)}
          />
        </div>
        <div>
          <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.schemeLabel}</label>
          <FormInput
            testId="modal-source-scheme-input"
            type="text"
            required
            value={scheme}
            onChange={(e) => onSchemeChange(e.target.value)}
          />
        </div>
      </div>

      <div>
        <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.uriLabel} *</label>
        <FormInput
          testId="modal-source-uri-input"
          type="text"
          required
          placeholder={copy.uriPlaceholder}
          value={uri}
          onChange={(e) => onUriChange(e.target.value)}
        />
      </div>
    </>
  );
}
