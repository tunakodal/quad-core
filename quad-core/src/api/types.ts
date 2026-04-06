// ── Travel ──────────────────────────────────────────────────────────────────

export interface TravelPreferences {
  city: string;
  trip_days: number;
  categories: string[];
  max_distance_per_day: number; // meters
}

export interface TravelConstraints {
  max_trip_days?: number;
  max_pois_per_day?: number;
  max_daily_distance?: number; // meters
}

// ── POI ─────────────────────────────────────────────────────────────────────

export interface GeoPoint {
  lat: number;
  lng: number;
}

export interface Poi {
  id: string;
  name: string;
  city: string;
  lat: number;
  lng: number;
  categories: string[];
  eta_min?: number;
  description?: string;
}

export interface PoiQuery {
  city: string;
  categories?: string[];
  text_query?: string;
}

export interface PoiQueryResponse {
  pois: Poi[];
  warnings: ApiWarning[];
}

export interface PoiContentRequest {
  poi_id: string;
  language?: 'TR' | 'EN' | 'DE';
}

export interface PoiContent {
  poi_id: string;
  language: string;
  description?: string;
  images?: string[];
  audio_url?: string;
}

export interface PoiContentResponse {
  content: PoiContent;
  warnings: ApiWarning[];
}

// ── Route ────────────────────────────────────────────────────────────────────

export interface RouteSegment {
  day_index: number;
  path: GeoPoint[];
  distance: number;   // meters
  duration: number;   // seconds
  geometry_encoded: string;
}

export interface DayPlan {
  day_index: number;
  pois: Poi[];
  route_segment?: RouteSegment;
}

export interface Itinerary {
  days: DayPlan[];
  total_distance: number;
  total_duration: number;
}

export interface RoutePlan {
  segments: RouteSegment[];
  total_distance: number;
  total_duration: number;
  geometry_encoded: string;
}

export interface RouteRequest {
  preferences: TravelPreferences;
  constraints: TravelConstraints;
  language?: 'TR' | 'EN' | 'DE';
}

export interface RouteResponse {
  itinerary: Itinerary;
  route_plan: RoutePlan;
  warnings: ApiWarning[];
  effective_trip_days?: number;
}

// ── Replan ──────────────────────────────────────────────────────────────────

export interface DayReorderOperation {
  day_index: number;
  ordered_poi_ids: string[];
}

export interface UserEdits {
  removed_poi_ids?: string[];
  locked_pois_by_day?: Record<number, string[]>;
  reorder_operations?: DayReorderOperation[];
}

export interface ReplanRequest {
  existing_itinerary: Itinerary;
  edits: UserEdits;
  constraints: TravelConstraints;
}

// ── Suggestion ───────────────────────────────────────────────────────────────

export interface TripDaySuggestionRequest {
  city: string;
  categories: string[];
}

export interface TripDaySuggestionResponse {
  max_recommended_days: number;
  poi_count: number;
  warnings: ApiWarning[];
}

// ── Common ───────────────────────────────────────────────────────────────────

export interface ApiWarning {
  code: string;
  message: string;
}

export interface ApiErrorResponse {
  code: string;
  message: string;
  details?: unknown;
}
