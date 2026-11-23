import { OrciaDialog, type SubWorkflowLayerViewItem } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../i18n";
import {
  buildDefaultProcessLayers,
  slugifyProcessTitle,
  type CreateProcessFormDialogProps,
} from "./CreateProcessFormDialogHelpers";
import { CreateProcessFormFields } from "./CreateProcessFormFields";

export type { CreateProcessFormDialogProps };

export function CreateProcessFormDialog({
  open,
  onOpenChange,
  isFr,
  openHelpSection,
  upsertWorkflow,
  presetDraft,
}: CreateProcessFormDialogProps): React.ReactElement {
  const copy = resolveDictionaryForFlag(isFr).shellChrome.createProcessDialog;
  const [wfTitle, setWfTitle] = useState("");
  const [wfKey, setWfKey] = useState("");
  const [wfVersion, setWfVersion] = useState("1.0.0");
  const [wfStatus, setWfStatus] = useState<"DRAFT" | "PUBLISHED">("DRAFT");
  const [wfPrePrompt, setWfPrePrompt] = useState("");
  const [wfParamsCsv, setWfParamsCsv] = useState("");
  const [wfSectionsCsv, setWfSectionsCsv] = useState("");
  const [layers, setLayers] = useState<readonly SubWorkflowLayerViewItem[]>(() =>
    buildDefaultProcessLayers(isFr),
  );

  useEffect(() => {
    if (!presetDraft) return;
    setWfTitle(presetDraft.title);
    setWfKey(presetDraft.workflowKey);
    setWfVersion(presetDraft.version);
    setWfStatus(presetDraft.status);
    setWfPrePrompt(presetDraft.prePrompt);
    setWfParamsCsv(presetDraft.requiredParams.join(", "));
    setWfSectionsCsv(presetDraft.requiredMarkdownSections.join(", "));
    if (presetDraft.layers.length > 0) {
      setLayers(presetDraft.layers);
    }
  }, [presetDraft]);

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={copy.dialogTitle}
      testId="create-process-modal"
      closeLabel={copy.closeLabel}
      hideHeaderCloseButton
      contentClassName="orcia-ds-dialog-content-wide"
    >
      <form
        data-testid="create-workflow-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        className="orcia-ds-dialog-body"
        onSubmit={(e) => {
          e.preventDefault();
          const effectiveTitle = wfTitle.trim() || wfKey.trim();
          const effectiveKey =
            wfKey.trim() || slugifyProcessTitle(wfTitle) || "processus-metier";
          if (!effectiveTitle) return;
          upsertWorkflow({
            workflowKey: effectiveKey,
            title: effectiveTitle,
            version: wfVersion.trim() || "1.0.0",
            status: wfStatus,
            prePrompt: wfPrePrompt.trim(),
            prePromptSha256:
              "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", // pragma: allowlist secret
            requiredParams: wfParamsCsv.split(",").map((s) => s.trim()).filter(Boolean),
            requiredMarkdownSections: wfSectionsCsv.split(",").map((s) => s.trim()).filter(Boolean),
            triggers: ["manual"],
            layers,
          });
          setWfTitle("");
          setWfKey("");
          setWfPrePrompt("");
          setWfParamsCsv("");
          setWfSectionsCsv("");
          onOpenChange(false);
        }}
      >
        <CreateProcessFormFields
          copy={copy}
          wfTitle={wfTitle}
          setWfTitle={setWfTitle}
          wfKey={wfKey}
          setWfKey={setWfKey}
          wfStatus={wfStatus}
          setWfStatus={setWfStatus}
          wfPrePrompt={wfPrePrompt}
          setWfPrePrompt={setWfPrePrompt}
          wfParamsCsv={wfParamsCsv}
          setWfParamsCsv={setWfParamsCsv}
          wfSectionsCsv={wfSectionsCsv}
          setWfSectionsCsv={setWfSectionsCsv}
          layers={layers}
          onToggleLayer={(layerId) =>
            setLayers((prev) =>
              prev.map((item) =>
                item.layerId === layerId ? { ...item, enabled: !item.enabled } : item,
              ),
            )
          }
          openHelpSection={openHelpSection}
        />

        <div className="orcia-ds-dialog-footer">
          <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)", marginRight: "auto" }}>
            {formatI18nTemplate(copy.versionTemplate, { version: wfVersion })}
          </span>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="orcia-ds-btn orcia-ds-btn-secondary"
          >
            {copy.cancelCta}
          </button>
          <button
            type="submit"
            data-testid="save-workflow-btn"
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            {copy.saveCta}
          </button>
        </div>
      </form>
    </OrciaDialog>
  );
}
