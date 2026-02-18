import { apiFetch } from "@/api/client";
import type {
  CreateSavedViewInput,
  SavedViewRecord,
} from "@/domain/saved-view";

interface SavedViewApiRecord {
  id: string;
  name: string;
  filters: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

function parseSavedViewFilters(
  input: Record<string, unknown>,
): SavedViewRecord["filters"] {
  return {
    q: typeof input.q === "string" ? input.q : undefined,
    status: typeof input.status === "string" ? input.status : undefined,
    from: typeof input.from === "string" ? input.from : undefined,
    to: typeof input.to === "string" ? input.to : undefined,
    limit: typeof input.limit === "number" ? input.limit : undefined,
    offset: typeof input.offset === "number" ? input.offset : undefined,
  };
}

function mapSavedViewApiRecord(item: SavedViewApiRecord): SavedViewRecord {
  return {
    id: item.id,
    name: item.name,
    filters: parseSavedViewFilters(item.filters),
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}

export async function listSavedViews(): Promise<SavedViewRecord[]> {
  const payload = await apiFetch<SavedViewApiRecord[]>("/api/v1/saved-views/", {
    method: "GET",
  });

  return payload.map(mapSavedViewApiRecord);
}

export async function createSavedView(
  input: CreateSavedViewInput,
): Promise<SavedViewRecord> {
  const payload = await apiFetch<SavedViewApiRecord>("/api/v1/saved-views/", {
    method: "POST",
    body: JSON.stringify(input),
  });
  return mapSavedViewApiRecord(payload);
}

export async function deleteSavedView(id: string): Promise<void> {
  await apiFetch<unknown>(`/api/v1/saved-views/${id}/`, {
    method: "DELETE",
  });
}
