import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import RouteMap from "./RouteMap";
import styles from "../styles/Route.module.css";

// DEV fallback data — backend bağlı değilken test için
const DEV_DAY_ROUTES = [
  {
    dayIndex: 0,
    dateLabel: "Apr 24",
    pois: [
      { id: "p1", name: "Hagia Sophia", etaMin: 25, lat: 41.0086, lng: 28.9802 },
      { id: "p2", name: "Topkapi Palace", etaMin: 35, lat: 41.0115, lng: 28.9833 },
      { id: "p3", name: "Galata Tower", etaMin: 30, lat: 41.0256, lng: 28.9744 },
    ],
  },
  {
    dayIndex: 1,
    dateLabel: "Apr 25",
    pois: [
      { id: "p4", name: "Basilica Cistern", etaMin: 20, lat: 41.0084, lng: 28.9779 },
      { id: "p5", name: "Suleymaniye Mosque", etaMin: 30, lat: 41.0162, lng: 28.9637 },
      { id: "p6", name: "Spice Bazaar", etaMin: 25, lat: 41.0165, lng: 28.9702 },
    ],
  },
  {
    dayIndex: 2,
    dateLabel: "Apr 26",
    pois: [
      { id: "p7", name: "Dolmabahce Palace", etaMin: 45, lat: 41.0392, lng: 29.0007 },
      { id: "p8", name: "Ortakoy Mosque", etaMin: 20, lat: 41.0473, lng: 29.0266 },
      { id: "p9", name: "Maiden's Tower Viewpoint", etaMin: 20, lat: 41.0211, lng: 29.0041 },
    ],
  },
];

const DEV_AVAILABLE_POIS = [
  { id: "p10", name: "Blue Mosque", etaMin: 25, lat: 41.0054, lng: 28.9768 },
  { id: "p11", name: "Grand Bazaar", etaMin: 40, lat: 41.0107, lng: 28.9681 },
  { id: "p12", name: "Galataport", etaMin: 35, lat: 41.0259, lng: 28.9816 },
  { id: "p13", name: "Pierre Loti Hill", etaMin: 30, lat: 41.0539, lng: 28.9336 },
  { id: "p14", name: "Rumeli Fortress", etaMin: 30, lat: 41.0849, lng: 29.0568 },
];

function haversineKm(a, b) {
  const R = 6371;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}

const DEFAULT_SPEED_KMH = 18;

function estimateMoveMin(from, to) {
  const km = haversineKm(from, to);
  const min = Math.round((km / DEFAULT_SPEED_KMH) * 60);
  return Math.max(1, min);
}

function isSamePoiOrder(a, b) {
  if (a.length !== b.length) return false;
  return a.every((poi, idx) => poi.id === b[idx]?.id);
}

function clonePois(pois) {
  return pois.map((poi) => ({ ...poi }));
}

function enrichPois(pois) {
  return pois.map((poi, idx) => {
    const prev = pois[idx - 1];
    return {
      ...poi,
      stayMin: poi.etaMin ?? null,
      moveMin: prev ? estimateMoveMin(prev, poi) : null,
    };
  });
}

export default function Route() {
  const navigate = useNavigate();
  const { state } = useLocation();

  // Backend'den gelen routeResponse (Planning.jsx'ten navigate ile gelir)
  const routeResponse = state?.routeResponse ?? null;

  const planningInput = state?.planningInput ?? {
    cityId: "istanbul",
    cityName: "İstanbul",
    days: 3,
    distanceKm: 45,
    categories: [],
  };

  const initialDays = useMemo(() => {
    // Backend'den gerçek veri geldiyse onu kullan
    if (routeResponse?.itinerary?.days?.length) {
      return routeResponse.itinerary.days.map((day) => {
        const pois = day.pois.map((p) => ({
          id: p.id,
          name: p.name,
          etaMin: p.eta_min ?? p.estimated_visit_duration ?? 30,
          lat: p.location?.latitude ?? p.lat,
          lng: p.location?.longitude ?? p.lng,
        }));

        return {
          dayIndex: day.day_index,
          dateLabel: `Day ${day.day_index + 1}`,
          originalPois: clonePois(pois),
          pois: clonePois(pois),
          modified: false,
        };
      });
    }

    // DEV fallback — backend çalışmıyorsa hâlâ test edebilirsin
    if (import.meta.env.DEV) {
      return DEV_DAY_ROUTES.map((day) => ({
        dayIndex: day.dayIndex,
        dateLabel: day.dateLabel,
        originalPois: clonePois(day.pois),
        pois: clonePois(day.pois),
        modified: false,
      }));
    }

    return [];
  }, [routeResponse]);

  const [days, setDays] = useState(initialDays);
  const [activeDayIndex, setActiveDayIndex] = useState(0);
  const [activePoiIndex, setActivePoiIndex] = useState(-1);
  const [draggingPoiId, setDraggingPoiId] = useState(null);

  const availablePois = useMemo(() => DEV_AVAILABLE_POIS, []);

  const activeDay = days[activeDayIndex] ?? null;

  const activeDayPois = useMemo(() => {
    if (!activeDay) return [];
    return enrichPois(activeDay.pois);
  }, [activeDay]);

  const anyModified = useMemo(() => days.some((day) => day.modified), [days]);

  const canDiscard = anyModified;
  const canFinalize = anyModified;
  const canStart = !anyModified;

  function recomputeDay(day, nextPois) {
    const cleanPois = clonePois(nextPois);
    return {
      ...day,
      pois: cleanPois,
      modified: !isSamePoiOrder(cleanPois, day.originalPois),
    };
  }

  function updateActiveDayPois(nextPois) {
    setDays((prev) =>
      prev.map((day, idx) =>
        idx === activeDayIndex ? recomputeDay(day, nextPois) : day
      )
    );
  }

  function handleDeletePoi(poiId) {
    if (!activeDay) return;
    const nextPois = activeDay.pois.filter((poi) => poi.id !== poiId);
    updateActiveDayPois(nextPois);
  }

  function handleAddPoi(e) {
    const selectedId = e.target.value;
    if (!selectedId || !activeDay) return;

    const poiToAdd = availablePois.find((poi) => poi.id === selectedId);
    if (!poiToAdd) return;

    const alreadyExists = activeDay.pois.some((poi) => poi.id === selectedId);
    if (alreadyExists) {
      e.target.value = "";
      return;
    }

    const nextPois = [...activeDay.pois, { ...poiToAdd }];
    updateActiveDayPois(nextPois);
    e.target.value = "";
  }

  function movePoi(fromIndex, toIndex) {
    if (!activeDay) return;
    if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return;

    const next = [...activeDay.pois];
    const [moved] = next.splice(fromIndex, 1);
    next.splice(toIndex, 0, moved);

    updateActiveDayPois(next);
  }

  function handleDragStart(poiId) {
    setDraggingPoiId(poiId);
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  function handleDrop(targetPoiId) {
    if (!activeDay || !draggingPoiId || draggingPoiId === targetPoiId) {
      setDraggingPoiId(null);
      return;
    }

    const fromIndex = activeDay.pois.findIndex((poi) => poi.id === draggingPoiId);
    const toIndex = activeDay.pois.findIndex((poi) => poi.id === targetPoiId);

    movePoi(fromIndex, toIndex);
    setDraggingPoiId(null);
  }

  function handleDragEnd() {
    setDraggingPoiId(null);
  }

  function handleDiscardChanges() {
    setDays((prev) =>
      prev.map((day) => ({
        ...day,
        pois: clonePois(day.originalPois),
        modified: false,
      }))
    );
    setActivePoiIndex(-1);
  }

  function handleFinalizeReplan() {
    const modifiedDays = days.filter((day) => day.modified);
    console.log("Finalize replan for modified days:", modifiedDays);

    setDays((prev) =>
      prev.map((day) => ({
        ...day,
        originalPois: clonePois(day.pois),
        modified: false,
      }))
    );
  }

  function handleStartJourney() {
    if (!canStart) return;

    navigate("/journey", {
      state: {
        planningInput,
        days,
      },
    });
  }

  function handleOpenPoi(poi, idx) {
    if (!poi) return;

    navigate(`/poi/${poi.id}`, {
      state: {
        poi,
        pois: activeDayPois,
        index: idx,
        planningInput,
        activeDayIndex,
      },
    });
  }

  const selectablePois = useMemo(() => {
    if (!activeDay) return [];
    const existingIds = new Set(activeDay.pois.map((poi) => poi.id));
    return availablePois.filter((poi) => !existingIds.has(poi.id));
  }, [activeDay, availablePois]);

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <section className={styles.topSummary}>
          <div className={styles.summaryContent}>
            <div className={styles.summaryTitle}>Selected Inputs</div>

            <div className={styles.summaryChips}>
              <div className={styles.summaryChip}>
                <span className={styles.chipLabel}>City</span>
                <span className={styles.chipValue}>{planningInput?.cityName ?? "—"}</span>
              </div>

              <div className={styles.summaryChip}>
                <span className={styles.chipLabel}>Days</span>
                <span className={styles.chipValue}>{planningInput?.days ?? "—"}</span>
              </div>

              <div className={styles.summaryChip}>
                <span className={styles.chipLabel}>Distance</span>
                <span className={styles.chipValue}>
                  {planningInput?.distanceKm ? `${planningInput.distanceKm} km` : "0"}
                </span>
              </div>

              <div className={styles.summaryChip}>
                <span className={styles.chipLabel}>Interests</span>
                <span className={styles.chipValue}>
                  {planningInput?.categories?.length ?? 0}
                </span>
              </div>
            </div>
          </div>

          <button
            type="button"
            className={styles.editBtn}
            onClick={() => navigate("/planning")}
          >
            Edit Inputs
          </button>
        </section>

        {/* Backend warnings */}
        {routeResponse?.warnings?.length > 0 && (
          <section className={styles.warningsBar}>
            {routeResponse.warnings.map((w, i) => (
              <div key={i} className={styles.warningItem}>
                ⚠️ {w.message}
              </div>
            ))}
          </section>
        )}

        <section className={styles.daysSection}>
          <div className={styles.daysHeader}>
            <h2 className={styles.sectionTitle}>Days</h2>
            <p className={styles.sectionSubtle}>Switch between calculated daily routes</p>
          </div>

          <div className={styles.daysBar}>
            {days.map((day, idx) => {
              const isActive = idx === activeDayIndex;

              return (
                <button
                  key={day.dayIndex}
                  type="button"
                  className={`${styles.dayTab} ${isActive ? styles.dayTabActive : ""}`}
                  onClick={() => {
                    setActiveDayIndex(idx);
                    setActivePoiIndex(-1);
                  }}
                >
                  <div className={styles.dayTabTop}>
                    <span className={styles.dayTabLabel}>Day {idx + 1}</span>
                    {day.modified && <span className={styles.modifiedDot} />}
                  </div>

                  <div className={styles.dayTabStatus}>
                    {day.modified ? "Modified" : "Original"}
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        <section className={styles.mainGrid}>
          <div className={styles.mapCard}>
            <div className={styles.cardHeader}>
              <h3 className={styles.cardTitle}>Map</h3>
            </div>

            <div className={styles.mapWrap}>
              <RouteMap
                cityId={planningInput?.cityId}
                stops={activeDayPois}
                geometry={
                  routeResponse?.route_plan?.segments?.[activeDayIndex]?.geometry_encoded ?? null
                }
                activeIndex={activePoiIndex}
                onHoverStop={setActivePoiIndex}
                onSelectStop={(idx) => handleOpenPoi(activeDayPois[idx], idx)}
              />
            </div>
          </div>

          <aside className={styles.planCard}>
            <div className={styles.cardHeader}>
              <div>
                <h3 className={styles.cardTitle}>Day {activeDayIndex + 1} Plan</h3>
                <p className={styles.cardSubtle}>Add, delete or reorder POIs for this day</p>
              </div>

              {activeDay?.modified && (
                <span className={styles.modifiedBadge}>Modified</span>
              )}
            </div>

            <div className={styles.addRow}>
              <select
                className={styles.addSelect}
                defaultValue=""
                onChange={handleAddPoi}
              >
                <option value="" disabled>Add a place</option>
                {selectablePois.map((poi) => (
                  <option key={poi.id} value={poi.id}>
                    {poi.name}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.poiList}>
              {activeDayPois.length === 0 ? (
                <div className={styles.emptyState}>No POIs in this day yet.</div>
              ) : (
                activeDayPois.map((poi, idx) => {
                  const isDragging = draggingPoiId === poi.id;
                  return (
                    <div
                      key={poi.id}
                      className={`${styles.poiItem} ${isDragging ? styles.poiItemDragging : ""}`}
                      draggable
                      onDragStart={() => handleDragStart(poi.id)}
                      onDragOver={handleDragOver}
                      onDrop={() => handleDrop(poi.id)}
                      onDragEnd={handleDragEnd}
                      onMouseEnter={() => setActivePoiIndex(idx)}
                      onMouseLeave={() => setActivePoiIndex(-1)}
                    >
                      <button
                        type="button"
                        className={styles.poiOrder}
                        onClick={() => handleOpenPoi(poi, idx)}
                        title="Open POI details"
                      >
                        {idx + 1}
                      </button>

                      <div
                        className={styles.poiMain}
                        role="button"
                        tabIndex={0}
                        onClick={() => handleOpenPoi(poi, idx)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleOpenPoi(poi, idx);
                        }}
                      >
                        <div className={styles.poiName}>{poi.name}</div>

                        <div className={styles.poiMeta}>
                          <span className={styles.poiMetaChip}>
                            Stay {poi.stayMin ? `${poi.stayMin} min` : "—"}
                          </span>

                          {idx > 0 && poi.moveMin ? (
                            <span className={styles.poiMetaChip}>
                              Move {poi.moveMin} min
                            </span>
                          ) : null}
                        </div>
                      </div>

                      <button
                        type="button"
                        className={styles.deleteBtn}
                        onClick={() => handleDeletePoi(poi.id)}
                        aria-label={`Delete ${poi.name}`}
                        title="Delete POI"
                      >
                        ×
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </aside>
        </section>

        <section className={styles.bottomBar}>
          <div className={styles.bottomLeft}>
            <button
              type="button"
              className={styles.secondaryBtn}
              onClick={handleDiscardChanges}
              disabled={!canDiscard}
            >
              Discard Changes
            </button>

            <button
              type="button"
              className={styles.primaryBtn}
              onClick={handleFinalizeReplan}
              disabled={!canFinalize}
            >
              Finalize Replan
            </button>

            <span className={styles.divider}>|</span>

            <button
              type="button"
              className={styles.successBtn}
              onClick={handleStartJourney}
              disabled={!canStart}
            >
              Start Journey
            </button>
          </div>

          <div className={styles.bottomHint}>
            {anyModified
              ? "Finalize changes before starting."
              : "No pending edits. You can start the journey."}
          </div>
        </section>
      </div>
    </div>
  );
}
