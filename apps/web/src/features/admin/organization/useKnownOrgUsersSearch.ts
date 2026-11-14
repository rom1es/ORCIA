import type { KnownUserOption } from "@orcia/ui";
import { useEffect, useRef, useState } from "react";
import { searchKnownOrgUsersFromApi } from "./orgUnitsApiBridge";

export interface UseKnownOrgUsersSearchOptions {
  readonly initialKnownUsers: readonly KnownUserOption[];
  readonly excludedPrincipalIds?: readonly string[];
  readonly locale?: "fr" | "en";
}

export interface UseKnownOrgUsersSearchResult {
  readonly knownUsers: readonly KnownUserOption[];
  readonly hasMore: boolean;
  readonly isSearching: boolean;
  readonly searchError: string | null;
  readonly onSearchQueryChange: (query: string) => void;
  readonly addKnownUserLocally: (user: KnownUserOption) => void;
}

export function useKnownOrgUsersSearch({
  initialKnownUsers,
  excludedPrincipalIds = [],
  locale = "fr",
}: UseKnownOrgUsersSearchOptions): UseKnownOrgUsersSearchResult {
  const [knownUsers, setKnownUsers] = useState<readonly KnownUserOption[]>(initialKnownUsers);
  const [hasMore, setHasMore] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const requestSeqRef = useRef(0);
  const knownUsersMapRef = useRef<Map<string, KnownUserOption>>(new Map());

  useEffect(() => {
    for (const u of initialKnownUsers) {
      knownUsersMapRef.current.set(u.principalId.toLowerCase().trim(), u);
    }
    setKnownUsers(initialKnownUsers);
  }, [initialKnownUsers]);

  const onSearchQueryChange = (query: string) => {
    const seq = ++requestSeqRef.current;
    const fetchLimit = Math.min(100, 10 + excludedPrincipalIds.length);

    setIsSearching(true);
    void searchKnownOrgUsersFromApi(query, fetchLimit, locale).then((res) => {
      if (requestSeqRef.current !== seq) return;
      setIsSearching(false);
      if (res.ok) {
        setSearchError(null);
        setHasMore(res.hasMore);
        for (const item of res.items) {
          knownUsersMapRef.current.set(item.principalId.toLowerCase().trim(), item);
        }
        setKnownUsers(res.items);
      } else {
        setSearchError(res.errorMessage);
      }
    });
  };

  const addKnownUserLocally = (user: KnownUserOption) => {
    const key = user.principalId.toLowerCase().trim();
    knownUsersMapRef.current.set(key, user);
    setKnownUsers((prev) => {
      const exists = prev.some((u) => u.principalId.toLowerCase().trim() === key);
      return exists ? prev : [user, ...prev];
    });
  };

  return {
    knownUsers,
    hasMore,
    isSearching,
    searchError,
    onSearchQueryChange,
    addKnownUserLocally,
  };
}
