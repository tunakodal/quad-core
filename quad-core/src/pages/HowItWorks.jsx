import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./HowItWorks.module.css";
import { Button } from "../ui/Button";

/**
 * Backend plan (wire-in ready):
 * GET /api/poi-samples?limit=20&random=1
 * -> { items: [{ id, name, city, category, lat, lng, bestSeason, estVisitMin, source }, ...] }
 */

const DEV_SAMPLE_ROWS = Array.from({ length: 30 }).map((_, i) => ({
  id: `poi_${String(i + 1).padStart(2, "0")}`,
  name: [
    "Hagia Sophia",
    "Topkapi Palace",
    "Galata Tower",
    "Grand Bazaar",
    "Bosphorus Viewpoint",
    "Dolmabahce Palace",
    "Suleymaniye Mosque",
    "Istiklal Street",
    "Gulhane Park",
    "Spice Bazaar",
    "Maiden’s Tower",
    "Ortakoy",
    "Pierre Loti Hill",
    "Kadikoy Market",
    "Balat Streets",
    "Archaeology Museum",
    "Basilica Cistern",
    "Chora Church",
    "Emirgan Grove",
    "Rumeli Fortress",
    "Princes’ Islands",
    "Karakoy",
    "Taksim Square",
    "Fener",
    "Camlica Hill",
    "Yildiz Park",
    "Kuzguncuk",
    "Sirkeci",
    "Moda Coast",
    "Golden Horn",
  ][i] ?? `Sample POI ${i + 1}`,
  city: "Istanbul",
  category: ["Landmark", "Museum", "Viewpoint", "Shopping", "Nature"][i % 5],
  estVisitMin: [30, 45, 60, 75, 90][i % 5],
  bestSeason: ["Spring", "Summer", "Autumn", "All-year"][i % 4],
  lat: (41.0082 + i * 0.0011).toFixed(4),
  lng: (28.9784 + i * 0.0010).toFixed(4),
  source: ["OSM", "Curated", "Municipal"][i % 3],
}));

function pickRandomN(arr, n) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, n);
}

/**
 * Icons: placeholder bırakıyoruz.
 * iconUrl ileride sizden gelecek (svg/png/jpg).
 */
const API_LIST = [
  {
    key: "osrm",
    name: "OSRM (Routing Engine)",
    desc: "Orders POIs and generates route geometry based on road networks.",
    href: "https://project-osrm.org/docs/v5.24.0/api/",
    iconUrl: "/apis/osrm.png",
  },
  {
    key: "leaflet",
    name: "Leaflet",
    desc: "Map renderer.",
    href: "https://leafletjs.com",
    iconUrl: "/apis/leaflet.jpeg",
  },
  {
    key: "osm-data",
    name: "OpenStreetMap Data",
    desc: "Road network + geographic base data used by routing and map layers.",
    href: "https://www.openstreetmap.org/copyright",
    iconUrl: "/apis/osm.jpeg",
  },
  {
    key: "sentence-similarity",
    name: "E5 Sentence Similarity Model",
    desc: "Computes semantic similarity between user preferences and POI descriptions to support relevance ranking.",
    href: "https://arxiv.org/abs/2212.03533",
    iconUrl: "/apis/e5.png",
  },
  {
    key: "wikipedia",
    name: "Wikipedia / MediaWiki REST API",
    desc: "Fetches POI descriptions and structured extracts via REST endpoints.",
    href: "https://www.mediawiki.org/wiki/API:REST_API",
    iconUrl: "/apis/wiki.png",
  },
  {
    key: "unesco",
    name: "UNESCO References",
    desc: "Authoritative reference pages for heritage-related POIs.",
    href: "https://www.unesco.org.tr/Pages/125/122/UNESCO-Dünya-Mirası-Listesi",
    iconUrl: "/apis/unesco.png",
  },
  {
    key: "images1",
    name: "Flickr",
    desc: "POI photos used in POI detail pages (license-aware sourcing).",
    href: "https://www.flickr.com/services/api/",
    iconUrl: "/apis/flickr.png",
  },
  {
    key: "images2",
    name: "Pixabay",
    desc: "POI photos used in POI detail pages (license-aware sourcing).",
    href: "https://pixabay.com/api/docs/",
    iconUrl: "/apis/pixabay.png",
  },
  {
    key: "tts",
    name: "ElevenLabs Text-to-Speech (TTS)",
    desc: "Optional POI narration in multiple languages.",
    href: "https://elevenlabs.io/docs",
    iconUrl: "/apis/elevenlabs.png",
  },
];

const TEAM = [
  { name: "Ebrar Sude Doğan", role: "Project Manager", photoUrl: "/us/ebrar_sude_dogan.jpeg" },
  { name: "Erdem Baran", role: "Database Administrator & API Specialist", photoUrl: "/us/erdem_baran.jpeg" },
  { name: "Kayrahan Toprak Tosun", role: "Scrum Master & Backend Development Leader", photoUrl: "/us/kayrahan_toprak_tosun.jpeg" },
  { name: "Tuna Kodal", role: "AI Specialist & Frontend Development Leader", photoUrl: "/us/tuna_kodal.jpeg" },
];


const FLOW = [
  {
    key: "input",
    title: "User Planning Input",
    text:
      "User selects city, trip days, distance constraints, interest categories, and exclusions. These inputs define feasibility and the candidate POI pool.",
    iconUrl: "/project_flow/data.png",
  },
  {
    key: "filter",
    title: "Database Retrieval & Category Filtering",
    text:
      "Backend retrieves POIs from the database for the selected city, then applies category-based filtering and basic constraints.",
    iconUrl: "/project_flow/database-storage.png",
  },
  {
    key: "rank",
    title: "POI Ranking (Feasibility-Aware)",
    text:
      "A ranking step prioritizes POIs when the user cannot visit everything. The goal is to select what is most relevant and realistically visitable within time/distance limits.",
    iconUrl: "/project_flow/top-three.png",
  },
  {
    key: "route",
    title: "Shortest Path / Ordering via OSRM",
    text:
      "Ranked POIs are sent to OSRM to compute an ordered path and route geometry. This produces an efficient travel sequence on real road networks.",
    iconUrl: "/project_flow/path.png",
  },
  {
    key: "split",
    title: "Day-by-Day Itinerary Construction",
    text:
      "The ordered route is segmented into daily plans according to trip days, estimated visit durations, and distance constraints.",
    iconUrl: "/project_flow/calendar.png",
  },
  {
    key: "viz",
    title: "Frontend Route Visualization",
    text:
      "Map renders markers and route polylines. The user explores POIs via the interactive map and the ordered stop list.",
    iconUrl: "/project_flow/web-design.png",
  },
  {
    key: "replan",
    title: "Optional Replanning (User Edits)",
    text:
      "User may edit POIs or constraints. If changed, the system reruns OSRM routing to produce an updated itinerary.",
    iconUrl: "/project_flow/planning.png",
  },
  {
    key: "details",
    title: "POI Details & Optional Narration",
    text:
      "POI pages provide descriptions, images, and optional audio narration (TTS). Users can navigate between POIs and return to the route overview.",
    iconUrl: "/project_flow/greek-pillars.png",
  },
];

function IconPh({ iconUrl, alt }) {
  if (iconUrl) {
    return <img className={styles.iconImg} src={iconUrl} alt={alt ?? ""} />;
  }
  return <div className={styles.iconPh} aria-hidden="true" />;
}

export default function HowItWorks() {
  const navigate = useNavigate();

  const [rows, setRows] = useState(() => pickRandomN(DEV_SAMPLE_ROWS, 20));
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    // Backend hazır olunca:
    // refreshRandom();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshRandom = async () => {
    setLoading(true);
    setErr("");
    try {
      if (import.meta.env.DEV) {
        setRows(pickRandomN(DEV_SAMPLE_ROWS, 20));
        return;
      }

      // Backend (example)
      // const res = await fetch(`/api/poi-samples?limit=20&random=1`);
      // if (!res.ok) throw new Error("Fetch failed");
      // const data = await res.json();
      // setRows(Array.isArray(data.items) ? data.items : []);

      console.log("Hook point: GET /api/poi-samples?limit=20&random=1");
    } catch (e) {
      setErr(e?.message ?? "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  const tableMeta = useMemo(() => {
    if (loading) return "Loading random samples…";
    if (err) return `Backend not connected: ${err}`;
    return `Showing 20 random samples. You can change the sample set using the “Random Refresh” button.`;
  }, [loading, err]);

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <header className={styles.header}>
          <h2 className={styles.title}>
            How <span className={styles.brand}>GUIDE</span> Works
          </h2>
          <p className={styles.subtitle}>
            GUIDE combines curated POI data, AI-based ranking, and external services to generate optimized travel routes.
          </p>
        </header>

        {/* DB overview FIRST */}
        <section className={styles.section}>
          <div className={styles.sectionTitle}>Point of Interest Database Overview</div>

          <div className={styles.tableWrap}>
            <div className={styles.tableTopRow}>
              <div className={styles.tableMeta}>{tableMeta}</div>

              <button type="button" className={styles.tableAction} onClick={refreshRandom} disabled={loading}>
                Random Refresh
              </button>
            </div>

            <div className={styles.tableScroll}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>City</th>
                    <th>Category</th>
                    <th>Est. Visit</th>
                    <th>Best Season</th>
                    <th>Lat</th>
                    <th>Lng</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id}>
                      <td className={styles.mono}>{r.id}</td>
                      <td className={styles.strongCell}>{r.name}</td>
                      <td>{r.city}</td>
                      <td>{r.category}</td>
                      <td>{r.estVisitMin ? `${r.estVisitMin} min` : "—"}</td>
                      <td>{r.bestSeason ?? "—"}</td>
                      <td className={styles.mono}>{r.lat}</td>
                      <td className={styles.mono}>{r.lng}</td>
                      <td>{r.source ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* APIs AFTER DB */}
        <section className={styles.section}>
          <div className={styles.sectionTitle}>Data Sources & External Services</div>

          <div className={styles.apiGrid}>
            {API_LIST.map((a) => (
                <a
                    key={a.key}
                    href={a.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.apiCard}
                >
                  <div className={styles.apiTop}>
                    <div className={styles.apiIcon}>
                      <IconPh iconUrl={a.iconUrl} alt=""/>
                    </div>
                    <div className={styles.apiName}>{a.name}</div>
                  </div>

                  <div className={styles.apiDesc}>{a.desc}</div>
                  <div className={styles.apiIO}>{a.io}</div>
                </a>
            ))}
          </div>
        </section>

        {/* System Flow */}
        <section className={styles.section}>
          <div className={styles.sectionTitle}>System Flow</div>

          <div className={styles.flowGrid}>
            {FLOW.map((f) => (
                <div key={f.key} className={styles.flowCard}>
                  <div className={styles.flowIcon}>
                    <IconPh iconUrl={f.iconUrl} alt=""/>
                  </div>

                  <div className={styles.flowBody}>
                    <div className={styles.flowTitle}>{f.title}</div>
                    <div className={styles.flowText}>{f.text}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Team */}
        <section className={styles.section}>
          <div className={styles.teamTitle}>
            Meet the team behind <span className={styles.teamAccent}>GUIDE</span>
          </div>

          <div className={styles.teamGrid}>
            {TEAM.map((m) => (
              <div key={m.name} className={styles.memberCard}>
                <div className={styles.avatar}>
                  {m.photoUrl ? (
                    <img className={styles.avatarImg} src={m.photoUrl} alt={m.name} />
                  ) : (
                    <div className={styles.avatarPh} aria-hidden="true" />
                  )}
                </div>
                <div className={styles.memberName}>{m.name}</div>
                <div className={styles.memberRole}>{m.role}</div>
              </div>
            ))}
          </div>
        </section>

        <div className={styles.bottomRow}>
          <Button variant="ghost" className={styles.backBtnBottom} onClick={() => navigate("/")}>
            ← Back to landing
          </Button>
        </div>
      </div>
    </div>
  );
}