// Replanning.jsx
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import RouteMap from "./RouteMap";
import { Button } from "../ui/Button";
import styles from "./Replanning.module.css";

// --- helpers ---
const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
const toInt = (v, fallback) => {
  const n = parseInt(String(v ?? "").replace(/[^\d]/g, ""), 10);
  return Number.isFinite(n) ? n : fallback;
};

// --- DEV fallback POIs (backend gelene kadar) ---
const DEV_ALL_POIS = [
  {
    id: "p1",
    name: "Hagia Sophia",
    category: "Landmark",
    stayMin: 55,
    lat: 41.0086,
    lng: 28.9802,
    imageUrl:
      "https://images.unsplash.com/photo-1564507592333-c60657eea523?auto=format&fit=crop&w=400&q=60",
  },
  {
    id: "p2",
    name: "Topkapi Palace",
    category: "Museum",
    stayMin: 75,
    lat: 41.0115,
    lng: 28.9833,
    imageUrl:
      "https://images.unsplash.com/photo-1600623711310-8f5ec8ac1b8b?auto=format&fit=crop&w=400&q=60",
  },
  {
    id: "p3",
    name: "Galata Tower",
    category: "Viewpoint",
    stayMin: 45,
    lat: 41.0256,
    lng: 28.9744,
    imageUrl:
      "https://images.unsplash.com/photo-1545048702-79362596cdc9?auto=format&fit=crop&w=400&q=60",
  },
  {
    id: "p4",
    name: "Grand Bazaar",
    category: "Shopping",
    stayMin: 60,
    lat: 41.0107,
    lng: 28.9681,
    imageUrl:
      "https://images.unsplash.com/photo-1600716033644-55f7b4f2b2b3?auto=format&fit=crop&w=400&q=60",
  },
];

const DEV_CATEGORIES = [
  { key: "landmarks", label: "Landmarks" },
  { key: "museums", label: "Museums" },
  { key: "dining", label: "Dining" },
  { key: "shopping", label: "Shopping" },
  { key: "nature", label: "Nature" },
  { key: "nightlife", label: "Nightlife" },
  { key: "art", label: "Art & Culture" },
  { key: "relax", label: "Relaxation" },
  { key: "religious", label: "Religious" },
  { key: "historical", label: "Historical" },
  { key: "viewpoints", label: "Viewpoints" },
  { key: "family", label: "Family Friendly" },
];

// basit icon mapping (db/ikon seti gelince replace edersiniz)
const CAT_ICON = {
  landmarks: "🏛️",
  museums: "🖼️",
  dining: "🍽️",
  shopping: "🛍️",
  nature: "🌿",
  nightlife: "🌙",
  art: "🎭",
  relax: "🧘",
  religious: "🕌",
  historical: "📜",
  viewpoints: "🌇",
  family: "👨‍👩‍👧‍👦",
};

function EditablePillNumber({ value, unitLabel, min, max, onCommit }) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(value)), [value]);

  return (
    <div className={styles.valuePill}>
      <input
        className={styles.pillInput}
        value={draft}
        inputMode="numeric"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => {
          const next = clamp(toInt(draft, value), min, max);
          onCommit(next);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
        }}
        aria-label={`Set ${unitLabel}`}
      />
      <span className={styles.pillUnit}>{unitLabel}</span>
    </div>
  );
}

function RangeRow({
  title,
  value,
  min,
  max,
  step,
  unitLabel,
  onChange,
  tickValues,
  fixEndTick = false,
  thumbPx = 22,
  tickOffsets = {},
}) {
  return (
    <div className={styles.rangeRow}>
      <div className={styles.rangeHead}>
        <div className={styles.rangeTitle}>{title}</div>
        <EditablePillNumber value={value} unitLabel={unitLabel} min={min} max={max} onCommit={onChange} />
      </div>

      <div className={styles.rangeWrap} style={{ ["--thumb"]: `${thumbPx}px` }}>
        <input
          className={styles.range}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(toInt(e.target.value, value))}
          aria-label={title}
        />

        {tickValues?.length ? (
          <div className={styles.ticksAbs} aria-hidden="true">
           {tickValues.map((t) => {
              const p = (t - min) / (max - min);
              const isMax = t === max;

              // px cinsinden mikro düzeltme
              const dx = tickOffsets[t] ?? 0;

              return (
                <span
                  key={t}
                  className={styles.tickAbs}
                  style={
                    isMax
                      ? { left: "100%", transform: `translateX(calc(-100% + ${dx}px))` }
                      : { left: `${p * 100}%`, transform: `translateX(calc(-50% + ${dx}px))` }
                  }
                >
                  {t}
                </span>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Drawer({ title, open, onClose, children, footer }) {
  return (
    <>
      <div className={`${styles.drawerBackdrop} ${open ? styles.drawerBackdropOn : ""}`} onClick={onClose} />
      <aside className={`${styles.drawer} ${open ? styles.drawerOn : ""}`}>
        <div className={styles.drawerHeader}>
          <div className={styles.drawerTitle}>{title}</div>
          <button type="button" className={styles.drawerClose} onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className={styles.drawerBody}>{children}</div>

        <div className={styles.drawerFooter}>{footer}</div>
      </aside>
    </>
  );
}

function PoiPickItem({ poi, checked, onToggle }) {
  return (
    <button
      type="button"
      className={`${styles.poiRow} ${checked ? styles.poiRowOn : ""}`}
      onClick={onToggle}
      aria-pressed={checked}
    >
      <img className={styles.poiThumb} src={poi.imageUrl} alt="" loading="lazy" />
      <div className={styles.poiMeta}>
        <div className={styles.poiName}>{poi.name}</div>
        <div className={styles.poiSub}>
          {poi.category}
          {poi.stayMin ? ` • ${poi.stayMin} min` : ""}
        </div>
      </div>
      <span className={`${styles.poiTick} ${checked ? styles.poiTickOn : ""}`} aria-hidden="true">
        ✓
      </span>
    </button>
  );
}

export default function Replanning() {
  const navigate = useNavigate();
  const { state } = useLocation();

  const planningInput = state?.planningInput ?? {
    cityId: "istanbul",
    days: 3,
    distanceKm: 100,
    categories: ["landmarks", "museums"],
  };

  const [days, setDays] = useState(() => clamp(toInt(planningInput.days, 3), 1, 10));
  const [distanceKm, setDistanceKm] = useState(() => clamp(toInt(planningInput.distanceKm, 100), 20, 2000));

  const [categories, setCategories] = useState(DEV_CATEGORIES);
  const [selectedCategories, setSelectedCategories] = useState(() => new Set(planningInput.categories ?? []));

  const [allPois, setAllPois] = useState(import.meta.env.DEV ? DEV_ALL_POIS : []);
  const [selectedPois, setSelectedPois] = useState(() => {
    const seed = import.meta.env.DEV ? DEV_ALL_POIS.slice(0, 3) : [];
    return seed;
  });

  const [poiQuery, setPoiQuery] = useState("");
  const [drawer, setDrawer] = useState(null); // "pois" | "cats" | null
  const [isGenerating, setIsGenerating] = useState(false);

  // planningInput değişirse sayfayı senkronla (geri dönme vs.)
  useEffect(() => {
    setDays(clamp(toInt(planningInput.days, 3), 1, 10));
    setDistanceKm(clamp(toInt(planningInput.distanceKm, 100), 20, 2000));
    setSelectedCategories(new Set(planningInput.categories ?? []));
  }, [planningInput.days, planningInput.distanceKm, planningInput.categories]);

  // --- backend hook points (şimdilik boş) ---
  useEffect(() => {
    // Backend hazır olunca:
    // fetch(`/api/categories`).then(r=>r.json()).then(setCategories)
    // fetch(`/api/pois?cityId=${planningInput.cityId}`).then(r=>r.json()).then(setAllPois)
  }, [planningInput.cityId]);

  // --- derived ---
  const selectedCatCount = selectedCategories.size;
  const selectedPoiIds = useMemo(() => new Set(selectedPois.map((p) => p.id)), [selectedPois]);

  const filteredPois = useMemo(() => {
    const q = poiQuery.trim().toLowerCase();
    if (!q) return allPois;
    return allPois.filter((p) => (p.name ?? "").toLowerCase().includes(q));
  }, [allPois, poiQuery]);

  // Selected her zaman selectedPois üzerinden gelsin (arama varsa selected içinde de filtrele)
  const selectedList = useMemo(() => {
    const q = poiQuery.trim().toLowerCase();
    if (!q) return selectedPois;
    return selectedPois.filter((p) => (p.name ?? "").toLowerCase().includes(q));
  }, [selectedPois, poiQuery]);

  // Available arama+seçili filtreli
  const availableList = useMemo(() => {
    return filteredPois.filter((p) => !selectedPoiIds.has(p.id));
  }, [filteredPois, selectedPoiIds]);

  // --- actions ---
  const toggleCategory = (key) => {
    setSelectedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const togglePoi = (poi) => {
    setSelectedPois((prev) => {
      const has = prev.some((x) => x.id === poi.id);
      if (has) return prev.filter((x) => x.id !== poi.id);
      return [...prev, poi];
    });
  };

  const buildPayload = () => ({
    cityId: planningInput.cityId,
    days,
    distanceKm,
    categories: Array.from(selectedCategories),
    selectedPoiIds: selectedPois.map((p) => p.id),
  });

  const restartPlanning = async () => {
    setIsGenerating(true);
    try {
      const payload = buildPayload();
      console.log("Restart planning payload:", payload);

      // Backend hazır olunca:
      // const res = await fetch("/api/replan", {
      //   method: "POST",
      //   headers: { "Content-Type": "application/json" },
      //   body: JSON.stringify(payload),
      // });
      // const data = await res.json();
      // setSelectedPois(data.pois);
      // setGeometry(data.geometry);

      await new Promise((r) => setTimeout(r, 900)); // DEV fake wait
    } finally {
      setIsGenerating(false);
    }
  };

  const confirmRoute = () => {
    navigate("/route", { state: { planningInput: buildPayload() } });
  };

  return (
    <div className={styles.page}>
      {/* blocking overlay */}
      {isGenerating && (
        <div className={styles.blockingOverlay} role="status" aria-live="polite">
          <div className={styles.loadingCard}>
            <div className={styles.spinner} />
            <div className={styles.loadingText}>Generating route…</div>
          </div>
        </div>
      )}

      <div className={styles.hero} aria-busy={isGenerating ? "true" : "false"}>
        <div className={styles.topRow}>
          <h2 className={styles.title}>Adjust Planning</h2>
        </div>

        <div className={styles.grid}>
          {/* LEFT: controls */}
          <section className={styles.left}>
            <div className={styles.card}>
              <div className={styles.cardTitle}>Constraints</div>

              <div className={styles.rangeGrid}>
                <RangeRow
                  title="Days"
                  value={days}
                  min={1}
                  max={10}
                  step={1}
                  unitLabel="days"
                  onChange={(v) => setDays(clamp(v, 1, 10))}
                  tickValues={[1, 3, 5, 7, 10]}
                  fixEndTick
                  thumbPx={22}
                  tickOffsets={{
                    1: +11,
                    3: +7,
                    7: -3,
                    10: -5,
                  }}
                />

                <RangeRow
                  title="Distance"
                  value={distanceKm}
                  min={20}
                  max={2000}
                  step={10}
                  unitLabel="km"
                  onChange={(v) => setDistanceKm(clamp(v, 20, 2000))}
                  tickValues={[20, 500, 1000, 1500, 2000]}
                  fixEndTick
                  thumbPx={22}
                  tickOffsets={{
                    20: +13,
                    500: +7,
                    1000: +1,
                    1500: -6,
                    2000: +3,
                  }}
                />
              </div>

              <div className={styles.actionsCol}>
                <button type="button" className={styles.panelAction} onClick={() => setDrawer("pois")}>
                  <div className={styles.panelActionMain}>Edit POIs</div>
                  <div className={styles.panelActionSub}>{selectedPois.length} selected</div>
                </button>

                <button type="button" className={styles.panelAction} onClick={() => setDrawer("cats")}>
                  <div className={styles.panelActionMain}>Edit Categories</div>
                  <div className={styles.panelActionSub}>{selectedCatCount} selected</div>
                </button>
              </div>
            </div>

            <div className={styles.card}>
              <div className={styles.bottomActions}>
                <Button variant="ghost" className={styles.longBtn} onClick={restartPlanning} disabled={isGenerating}>
                  Restart Planning
                </Button>

                <Button variant="primary" className={styles.longBtn} onClick={confirmRoute} disabled={isGenerating}>
                  Confirm Route
                </Button>
              </div>
            </div>
          </section>

          {/* RIGHT: map */}
          <section className={styles.right}>
            <div className={styles.card}>
              <div className={styles.cardTitle}>Map</div>
              <RouteMap cityId={planningInput.cityId} stops={selectedPois} geometry={null} mapTheme="dim" />
            </div>
          </section>
        </div>
      </div>

      {/* Drawer: POIs */}
      <Drawer
        title="Edit POIs"
        open={drawer === "pois"}
        onClose={() => setDrawer(null)}
        footer={
          <>
            <Button
              variant="ghost"
              className={styles.drawerBtn}
              onClick={() => {
                setSelectedPois([]);
              }}
            >
              Clear
            </Button>
            <Button variant="primary" className={styles.drawerBtn} onClick={() => setDrawer(null)}>
              Done
            </Button>
          </>
        }
      >
        <div className={styles.drawerHint}>Select / remove POIs.</div>

        <div className={styles.searchRow}>
          <span className={styles.searchIcon} aria-hidden="true">
            ⌕
          </span>
          <input
            className={styles.searchInput}
            placeholder="Search POIs..."
            value={poiQuery}
            onChange={(e) => setPoiQuery(e.target.value)}
          />
        </div>

        <div className={styles.drawerSectionTitle}>Selected</div>
        {selectedList.length === 0 ? (
          <div className={styles.drawerEmpty}>No selected POIs yet.</div>
        ) : (
          <div className={styles.poiPickList}>
            {selectedList.map((p) => (
              <PoiPickItem key={p.id} poi={p} checked onToggle={() => togglePoi(p)} />
            ))}
          </div>
        )}

        <div className={styles.drawerSectionTitle}>Available</div>
        {availableList.length === 0 ? (
          <div className={styles.drawerEmpty}>No more POIs found.</div>
        ) : (
          <div className={styles.poiPickList}>
            {availableList.map((p) => (
              <PoiPickItem key={p.id} poi={p} checked={false} onToggle={() => togglePoi(p)} />
            ))}
          </div>
        )}
      </Drawer>

      {/* Drawer: Categories */}
      <Drawer
        title="Edit Categories"
        open={drawer === "cats"}
        onClose={() => setDrawer(null)}
        footer={
          <>
            <Button variant="ghost" className={styles.drawerBtn} onClick={() => setSelectedCategories(new Set())}>
              Clear
            </Button>
            <Button variant="primary" className={styles.drawerBtn} onClick={() => setDrawer(null)}>
              Done
            </Button>
          </>
        }
      >
        <div className={styles.drawerHint}>Categories will be sent to backend. (Multi-select)</div>

        <div className={styles.catList}>
          {categories.map((c) => {
            const on = selectedCategories.has(c.key);
            return (
                <button
                    key={c.key}
                    type="button"
                    className={`${styles.catRow} ${on ? styles.catRowOn : ""}`}
                    onClick={() => toggleCategory(c.key)}
                    aria-pressed={on}
                >
                  <span className={styles.catIconSlot} aria-hidden="true"/> {/* ikon boş slot */}
                  <span className={styles.catLabel}>{c.label}</span>

                  <span className={`${styles.catSwitch} ${on ? styles.catSwitchOn : ""}`} aria-hidden="true">
                    <span className={styles.catKnob}/>
                  </span>
                </button>
            );
          })}
        </div>
      </Drawer>
    </div>
  );
}