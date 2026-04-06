import type {
  PoiContentRequest,
  PoiContentResponse,
  PoiQuery,
  PoiQueryResponse,
  ReplanRequest,
  RouteRequest,
  RouteResponse,
  TripDaySuggestionRequest,
  TripDaySuggestionResponse,
} from './types';

const BASE = '/api/v1';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(error?.message ?? `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── Routes ───────────────────────────────────────────────────────────────────

export const routeApi = {
  /**
   * Generate a multi-day itinerary from user preferences.
   * POST /api/v1/routes/generate
   */
  generate(body: RouteRequest): Promise<RouteResponse> {
    return request('/routes/generate', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  /**
   * Replan an existing itinerary after user edits.
   * POST /api/v1/routes/replan
   */
  replan(body: ReplanRequest): Promise<RouteResponse> {
    return request('/routes/replan', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  /**
   * Suggest max feasible trip days based on available POIs.
   * POST /api/v1/routes/suggest-days
   */
  suggestDays(body: TripDaySuggestionRequest): Promise<TripDaySuggestionResponse> {
    return request('/routes/suggest-days', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },
};

// ── POIs ─────────────────────────────────────────────────────────────────────

export const poiApi = {
  /**
   * Search POIs by city and category filters.
   * POST /api/v1/pois/search
   */
  search(body: PoiQuery): Promise<PoiQueryResponse> {
    return request('/pois/search', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  /**
   * Get a single POI by ID.
   * GET /api/v1/pois/{poi_id}
   */
  getById(poiId: string): Promise<PoiQueryResponse> {
    return request(`/pois/${poiId}`);
  },

  /**
   * Get POI content (description, images, audio).
   * POST /api/v1/pois/content
   */
  getContent(body: PoiContentRequest): Promise<PoiContentResponse> {
    return request('/pois/content', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },
};

// ── Health ────────────────────────────────────────────────────────────────────

export const healthApi = {
  /**
   * Check if the backend is alive.
   * GET /health
   */
  check(): Promise<{ status: string; service: string }> {
    return fetch('/health').then((r) => r.json());
  },
};
