import { createContext, useContext } from "react";
import type { Stats } from "./api";

export interface LayoutData {
  stats?: Stats;
  statsError?: string;
  /** True once we've confirmed the logged-in user owns this project. Undefined while unknown/checking. */
  isOwner?: boolean;
}

export const LayoutDataContext = createContext<LayoutData>({});

export function useLayoutData(): LayoutData {
  return useContext(LayoutDataContext);
}