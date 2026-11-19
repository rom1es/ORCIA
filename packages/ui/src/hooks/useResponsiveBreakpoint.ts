import { useEffect, useState } from "react";
import {
  resolveResponsiveBreakpoint,
  type ResponsiveBreakpointTier,
} from "../primitives/MobileCompanionView";

export interface UseResponsiveBreakpointResult {
  readonly viewportWidthPx: number;
  readonly tier: ResponsiveBreakpointTier;
  readonly isMobile: boolean;
  readonly isLaptop: boolean;
  readonly isDesktop: boolean;
}

function readWindowWidthPx(fallbackPx: number): number {
  if (typeof window === "undefined") {
    return fallbackPx;
  }
  return window.innerWidth || fallbackPx;
}

/**
 * Reactive viewport breakpoint hook aligned with ORCIA Direction C thresholds:
 * - `DESKTOP`: `>= 1280px`
 * - `LAPTOP`: `768px..1279px`
 * - `MOBILE`: `< 768px`
 */
export function useResponsiveBreakpoint(
  explicitViewportWidthPx?: number,
): UseResponsiveBreakpointResult {
  const [measuredWidthPx, setMeasuredWidthPx] = useState<number>(() =>
    readWindowWidthPx(explicitViewportWidthPx ?? 1440),
  );

  useEffect(() => {
    if (explicitViewportWidthPx !== undefined || typeof window === "undefined") {
      return;
    }

    const syncWidth = (): void => {
      setMeasuredWidthPx(readWindowWidthPx(1440));
    };

    syncWidth();
    window.addEventListener("resize", syncWidth);

    const mediaCleanups: Array<() => void> = [];
    if (typeof window.matchMedia === "function") {
      for (const query of ["(max-width: 767px)", "(min-width: 1280px)"]) {
        const mql = window.matchMedia(query);
        if (typeof mql.addEventListener === "function") {
          mql.addEventListener("change", syncWidth);
          mediaCleanups.push(() => mql.removeEventListener("change", syncWidth));
        }
      }
    }

    return () => {
      window.removeEventListener("resize", syncWidth);
      for (const cleanup of mediaCleanups) {
        cleanup();
      }
    };
  }, [explicitViewportWidthPx]);

  const effectiveWidth =
    explicitViewportWidthPx !== undefined ? explicitViewportWidthPx : measuredWidthPx;
  const tier = resolveResponsiveBreakpoint(effectiveWidth);

  return {
    viewportWidthPx: effectiveWidth,
    tier,
    isMobile: tier === "MOBILE",
    isLaptop: tier === "LAPTOP",
    isDesktop: tier === "DESKTOP",
  };
}
