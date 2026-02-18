import type { DecisionListFilters } from "@/api/decisions";

export interface SavedViewRecord {
  id: string;
  name: string;
  filters: Partial<DecisionListFilters>;
  createdAt: string;
  updatedAt: string;
}

export interface CreateSavedViewInput {
  name: string;
  filters: Partial<DecisionListFilters>;
}
