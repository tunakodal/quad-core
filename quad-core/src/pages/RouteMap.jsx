import L from "leaflet";
import { MapContainer, TileLayer, Marker, Polyline } from "react-leaflet";

const CITY_CENTERS = {
  istanbul: [41.0082, 28.9784],
  ankara: [39.9334, 32.8597],
  izmir: [38.4237, 27.1428],
};

function escapeHtml(s = "") {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function mkIcon({ n, active, name, imageUrl }) {
  const safeName = escapeHtml(name);

  // Tek parça SVG pin (tepe + uç), numara ortada
  const pinSvg = `
  <svg class="guide-pin__svg" width="44" height="56" viewBox="0 0 44 56" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="0" y2="56">
        <stop offset="0" stop-color="#FF8A00"/>
        <stop offset="1" stop-color="#FF6A00"/>
      </linearGradient>
      <filter id="shadow" x="-20" y="-20" width="84" height="110" color-interpolation-filters="sRGB">
        <feDropShadow dx="0" dy="12" stdDeviation="10" flood-opacity="0.30"/>
      </filter>
    </defs>

    <g filter="url(#shadow)">
      <path d="M22 55C22 55 39 36.6 39 22C39 10.4 31.6 3 22 3C12.4 3 5 10.4 5 22C5 36.6 22 55 22 55Z"
            fill="url(#g)" stroke="rgba(255,255,255,0.65)" stroke-width="2.4" />
      <circle cx="22" cy="22" r="11.2" fill="rgba(255,255,255,0.18)" />
    </g>

    <text x="22" y="27" text-anchor="middle" font-size="14" font-weight="800"
          font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial"
          fill="#0B2F3A">${n}</text>
  </svg>`;

  const card = `
    <div class="guide-snap">
      <div class="guide-snap__img">
        ${imageUrl ? `<img src="${imageUrl}" alt="" />` : `<div class="guide-snap__ph"></div>`}
      </div>
      <div class="guide-snap__name">${safeName}</div>
    </div>
  `;

  return L.divIcon({
    className: "guide-pinWrap",
    html: `
      <div class="guide-pin ${active ? "is-active" : ""}">
        ${card}
        ${pinSvg}
      </div>
    `,
    iconSize: [220, 120],
    iconAnchor: [110, 120],
  });
}

export default function RouteMap({
  cityId,
  stops = [],
  geometry = null,
  activeIndex = -1,
  onHoverStop,
  onSelectStop,
}) {
  const center = CITY_CENTERS[cityId] ?? CITY_CENTERS.istanbul;
  const fallbackLine = stops.map((s) => [s.lat, s.lng]);

  return (
    <div
      className="route-map route-map--dim"
      style={{ position: "relative", width: "100%", height: 420, borderRadius: 16, overflow: "hidden" }}
    >
      <MapContainer center={center} zoom={12} style={{ width: "100%", height: "100%" }}>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {!geometry && stops.length >= 2 ? (
          <Polyline
            positions={fallbackLine}
            pathOptions={{
              color: "#ff6a00",
              weight: 7,
              opacity: 0.9,
              lineCap: "round",
              lineJoin: "round",
            }}
          />
        ) : null}

        {stops.map((s, idx) => (
          <Marker
            key={s.id ?? idx}
            position={[s.lat, s.lng]}
            icon={mkIcon({
              n: idx + 1,
              active: idx === activeIndex,
              name: s.name,
              imageUrl: s.imageUrl,
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