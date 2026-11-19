import { beforeEach } from "vitest";
import {
  getRecordedVitestApiCalls,
  resetVitestApiBackend,
  seedVitestInboxNotifications,
  seedVitestPermissionBrokerTickets,
  seedVitestPlatformSetupState,
  setVitestMockRefreshFails,
  setVitestMockReindexStatus,
  setVitestPublicAuthMode,
  type RecordedVitestApiCall,
} from "./setup/mockBackendState";
import { vitestFetchTransport } from "./setup/transportAndOpenApiValidator";

class VitestResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = VitestResizeObserverMock as unknown as typeof ResizeObserver;
}

(globalThis as Record<string, unknown>).__ORCIA_RESET_VITEST_BACKEND__ = resetVitestApiBackend;

if (typeof window !== "undefined") {
  window.scrollTo = () => undefined;
}

beforeEach(() => {
  resetVitestApiBackend();
});

globalThis.fetch = vitestFetchTransport as typeof fetch;

export {
  getRecordedVitestApiCalls,
  resetVitestApiBackend,
  seedVitestInboxNotifications,
  seedVitestPermissionBrokerTickets,
  seedVitestPlatformSetupState,
  setVitestMockRefreshFails,
  setVitestMockReindexStatus,
  setVitestPublicAuthMode,
  vitestFetchTransport,
  type RecordedVitestApiCall,
};
