import { createContext, useContext } from "react";
import type { Stats } from "./api";

export interface LayoutData {
  stats?: Stats;
  statsError?: string;
}

export const LayoutDataContext = createContext<LayoutData>({});

export function useLayoutData(): LayoutData {
  return useContext(LayoutDataContext);
}