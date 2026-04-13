import L from "leaflet";
import { MapContainer, TileLayer, Marker, Polyline, useMap } from "react-leaflet";
import { useEffect } from "react";

const CITY_CENTERS = {
  istanbul: [41.0082, 28.9784],
  ankara: [39.9334, 32.8597],
  izmir: [38.4237, 27.1428],
};

function decodePolyline(encoded) {
  const points = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let shift = 0;
    let result = 0;
    let byte;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    lat += result & 1 ? ~(result >> 1) : result >> 1;

    shift = 0;
    result = 0;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    lng += result & 1 ? ~(result >> 1) : result >> 1;

    points.push([lat / 1e5, lng / 1e5]);
  }

  return points;
}

function escapeHtml(s = "") {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function mkIcon({ n, active, name }) {
  const safeName = escapeHtml(name);

  const pinSvg = `
  <svg class="guide-pin__svg" width="36" height="44" viewBox="0 0 36 44" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <filter id="pin-shadow-${n}" x="-6" y="-2" width="48" height="56" color-interpolation-filters="sRGB">
        <feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#03045E" flood-opacity="0.18"/>
      </filter>
    </defs>

    <g filter="url(#pin-shadow-${n})">
      <path d="M18 42C18 42 32 28 32 16.5C32 8.5 25.7 3 18 3C10.3 3 4 8.5 4 16.5C4 28 18 42 18 42Z"
            fill="#1a1c7a" stroke="rgba(255,255,255,0.5)" stroke-width="1.2" />
    </g>

    <text x="18" y="20.5" text-anchor="middle" font-size="14" font-weight="900"
          font-family="Helvetica Neue, Helvetica, Arial, sans-serif"
          fill="#ffffff" letter-spacing="-0.5">${n}</text>
  </svg>`;

  const tooltip = active ? `
    <div style="
      background: var(--surface, rgba(255,255,255,0.95));
      backdrop-filter: blur(8px);
      padding: 6px 14px;
      border-radius: var(--r-md, 14px);
      border: 1px solid var(--border, #e2e8f0);
      box-shadow: 0 4px 14px rgba(0,0,0,0.10);
      font-family: Helvetica Neue, Helvetica, Arial, sans-serif;
      font-size: 13px;
      font-weight: 700;
      color: var(--primary, #03045E);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 200px;
      letter-spacing: -0.2px;
      margin-bottom: 4px;
      text-align: center;
    ">${safeName}</div>
  ` : "";

  return L.divIcon({
    className: "guide-pinWrap",
    html: `
      <div class="guide-pin ${active ? "is-active" : ""}">
        ${tooltip}
        ${pinSvg}
      </div>
    `,
    iconSize: [220, 80],
    iconAnchor: [110, 80],
  });
}

function FitBounds({ stops }) {
  const map = useMap();

  useEffect(() => {
    if (stops.length === 0) return;

    const bounds = L.latLngBounds(stops.map((s) => [s.lat, s.lng]));
    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
  }, [stops, map]);

  return null;
}

export default function RouteMap({
  cityId,
  stops = [],
  geometry = null,
  activeIndex = -1,
  onHoverStop,
  onSelectStop,
}) {
  const defaultCenter = CITY_CENTERS[cityId] ?? CITY_CENTERS.istanbul;

  const routeLine = geometry
    ? decodePolyline(geometry)
    : stops.map((s) => [s.lat, s.lng]);

  return (
    <div
      className="route-map route-map--dim"
      style={{ position: "relative", width: "100%", height: 420, borderRadius: 16, overflow: "hidden" }}
    >
      <MapContainer center={defaultCenter} zoom={12} style={{ width: "100%", height: "100%" }}>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <FitBounds stops={stops} />

        {routeLine.length >= 2 && geometry && (
          <Polyline
            positions={routeLine}
            pathOptions={{
              color: "#ff6a00",
              weight: 5,
              opacity: 0.85,
              lineCap: "round",
              lineJoin: "round",
            }}
          />
        )}

        {stops.map((s, idx) => (
          <Marker
            key={s.id ?? idx}
            position={[s.lat, s.lng]}
            icon={mkIcon({
              n: idx + 1,
              active: idx === activeIndex,
              name: s.name,
            })}
            eventHandlers={{
              mouseover: () => onHoverStop?.(idx),
              mouseout: () => onHoverStop?.(-1),
              click: () => onSelectStop?.(idx),
            }}
          />
        ))}
      </MapContainer>
    </div>
  );
}