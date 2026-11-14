import { type OrciaSearchableSelectOption } from "@orcia/ui";
import { useMemo, useRef, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import { getEligibleParentBuUnits } from "./orgTreeHelpers";
import { searchParentBuUnitsFromApi } from "./orgUnitsApiBridge";

function normalizeSearch(token: string): string {
  return token
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export interface UseParentOrgSearchOptions {
  readonly initialUnits: readonly ConfiguredOrgUnit[];
  readonly editingUnitId?: string;
  readonly rootParentOptionLabel: string;
  readonly parentBuOptionPrefix: string;
  readonly locale?: "fr" | "en";
}

export function useParentOrgSearch({
  initialUnits,
  editingUnitId,
  rootParentOptionLabel,
  parentBuOptionPrefix,
  locale = "fr",
}: UseParentOrgSearchOptions) {
  const [searchQuery, setSearchQuery] = useState("");
  const [remoteUnits, setRemoteUnits] = useState<readonly ConfiguredOrgUnit[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const requestSeqRef = useRef(0);

  const handleSearchQueryChange = (query: string) => {
    setSearchQuery(query);
    const seq = ++requestSeqRef.current;
    searchParentBuUnitsFromApi(query, 10, locale)
      .then((res) => {
        if (seq !== requestSeqRef.current) return;
        if (res.ok) {
          setRemoteUnits(res.units);
          setSearchError(null);
        } else {
          setSearchError(res.errorMessage);
        }
      })
      .catch((err: unknown) => {
        if (seq !== requestSeqRef.current) return;
        setSearchError(err instanceof Error ? err.message : String(err));
      });
  };

  const resetSearch = () => {
    requestSeqRef.current += 1;
    setSearchQuery("");
    setRemoteUnits(null);
    setSearchError(null);
  };

  const activeUnits = remoteUnits !== null ? remoteUnits : initialUnits;
  const eligibleUnits = useMemo(
    () => getEligibleParentBuUnits(activeUnits, editingUnitId),
    [activeUnits, editingUnitId],
  );

  const options: readonly OrciaSearchableSelectOption[] = useMemo(() => {
    const list: OrciaSearchableSelectOption[] = [];
    const normQ = normalizeSearch(searchQuery);
    const rootMatches = !normQ || normalizeSearch(rootParentOptionLabel).includes(normQ);

    if (rootMatches) {
      list.push({
        value: "scope-global",
        label: rootParentOptionLabel,
      });
    }

    for (const bu of eligibleUnits) {
      list.push({
        value: bu.id,
        label: `${parentBuOptionPrefix} ${bu.name}`.trim(),
        subLabel: bu.slug,
      });
    }
    return list;
  }, [eligibleUnits, searchQuery, rootParentOptionLabel, parentBuOptionPrefix]);

  return {
    searchQuery,
    options,
    searchError,
    handleSearchQueryChange,
    resetSearch,
  };
}
