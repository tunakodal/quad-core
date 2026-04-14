import { useMemo, useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import RouteMap from "./RouteMap";
import styles from "../styles/Route.module.css";

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

function mapPoiFromBackend(p) {
  return {
    id: p.id,
    name: p.name,
    etaMin: p.eta_min ?? p.estimated_visit_duration ?? 30,
    lat: p.location?.latitude ?? p.lat,
    lng: p.location?.longitude ?? p.lng,
  };
}

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

  const routeResponse = state?.routeResponse ?? null;

  const planningInput = state?.planningInput ?? {
    cityId: "istanbul",
    cityName: "İstanbul",
    days: 3,
    distanceKm: 45,
    categories: [],
  };

  const [currentRouteResponse, setCurrentRouteResponse] = useState(routeResponse);
  const [replanLoading, setReplanLoading] = useState(false);

  const initialDays = useMemo(() => {
    if (currentRouteResponse?.itinerary?.days?.length) {
      return currentRouteResponse.itinerary.days.map((day) => {
        const pois = day.pois.map(mapPoiFromBackend);
        return {
          dayIndex: day.day_index,
          dateLabel: `Day ${day.day_index + 1}`,
          originalPois: clonePois(pois),
          pois: clonePois(pois),
          modified: false,
        };
      });
    }

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
  }, []);

  const [days, setDays] = useState(initialDays);
  const [activeDayIndex, setActiveDayIndex] = useState(0);
  const [activePoiIndex, setActivePoiIndex] = useState(-1);
  const [dragState, setDragState] = useState({
    dragging: false,
    fromIndex: -1,
    overIndex: -1,
  });
  const [addSearch, setAddSearch] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const addRef = useRef(null);

  // Available POI'ler — ayrı state, replan'dan bağımsız
  const [availablePoiList, setAvailablePoiList] = useState(() => {
    if (routeResponse?.available_pois?.length) {
      return routeResponse.available_pois.map(mapPoiFromBackend);
    }
    if (import.meta.env.DEV) return DEV_AVAILABLE_POIS;
    return [];
  });

  useEffect(() => {
    function handleClickOutside(e) {
      if (addRef.current && !addRef.current.contains(e.target)) {
        setAddOpen(false);
      }
    }
    document.addEventListener("pointerdown", handleClickOutside);
    return () => document.removeEventListener("pointerdown", handleClickOutside);
  }, []);

  const activeDay = days[activeDayIndex] ?? null;

  const activeDayPois = useMemo(() => {
    if (!activeDay) return [];
    return enrichPois(activeDay.pois);
  }, [activeDay]);

  const anyModified = useMemo(() => days.some((day) => day.modified), [days]);

  const canDiscard = anyModified;
  const canFinalize = anyModified;
  const canStart = !anyModified;

  // Dropdown filtresi — tüm günlerdeki POI'leri hariç tut
  const filteredAddPois = useMemo(() => {
    if (!activeDay) return [];
    const existingIds = new Set(
      days.flatMap((day) => day.pois.map((poi) => poi.id))
    );
    const available = availablePoiList.filter((poi) => !existingIds.has(poi.id));
    if (!addSearch.trim()) return available;
    const q = addSearch.toLowerCase();
    return available.filter((poi) => poi.name.toLowerCase().includes(q));
  }, [activeDay, days, availablePoiList, addSearch]);

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

    const deletedPoi = activeDay.pois.find((poi) => poi.id === poiId);
    const nextPois = activeDay.pois.filter((poi) => poi.id !== poiId);
    updateActiveDayPois(nextPois);

    // Silinen POI'yi available listesine geri ekle
    if (deletedPoi) {
      setAvailablePoiList((prev) => {
        if (prev.some((p) => p.id === deletedPoi.id)) return prev;
        return [...prev, { ...deletedPoi }];
      });
    }
  }

  function handleAddPoiById(poiId) {
    if (!activeDay) return;
    const poiToAdd = availablePoiList.find((poi) => poi.id === poiId);
    if (!poiToAdd) return;

    const nextPois = [...activeDay.pois, { ...poiToAdd }];
    updateActiveDayPois(nextPois);

    // Available listesinden çıkar
    setAvailablePoiList((prev) => prev.filter((p) => p.id !== poiId));

    setAddSearch("");
    setAddOpen(false);
  }

  function movePoi(fromIndex, toIndex) {
    if (!activeDay) return;
    if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return;
    const next = [...activeDay.pois];
    const [moved] = next.splice(fromIndex, 1);
    next.splice(toIndex, 0, moved);
    updateActiveDayPois(next);
  }

  function handlePointerDown(e, idx) {
    e.preventDefault();
    setDragState({ dragging: true, fromIndex: idx, overIndex: idx });

    const handleMove = (moveE) => {
      const elements = document.querySelectorAll(`.${styles.poiItem}`);
      const y = moveE.clientY ?? moveE.touches?.[0]?.clientY;
      for (let i = 0; i < elements.length; i++) {
        const rect = elements[i].getBoundingClientRect();
        if (y >= rect.top && y <= rect.bottom) {
          setDragState((prev) => ({ ...prev, overIndex: i }));
          break;
        }
      }
    };

    const handleUp = () => {
      setDragState((prev) => {
        if (prev.fromIndex !== prev.overIndex && prev.fromIndex >= 0 && prev.overIndex >= 0) {
          movePoi(prev.fromIndex, prev.overIndex);
        }
        return { dragging: false, fromIndex: -1, overIndex: -1 };
      });
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
    };

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
  }

  function handleDiscardChanges() {
    // Discard sırasında eklenen POI'leri available'a geri ver,
    // silinen POI'leri available'dan geri çek
    const originalIds = new Set(
      days.flatMap((day) => day.originalPois.map((p) => p.id))
    );
    const currentIds = new Set(
      days.flatMap((day) => day.pois.map((p) => p.id))
    );

    // Eklenenler (current'ta var, original'da yok) → available'a geri ekle
    const addedPois = days.flatMap((day) =>
      day.pois.filter((p) => !originalIds.has(p.id))
    );

    // Silinenler (original'da var, current'ta yok) → available'dan çıkar
    const removedIds = new Set(
      days.flatMap((day) =>
        day.originalPois.filter((p) => !currentIds.has(p.id)).map((p) => p.id)
      )
    );

    setAvailablePoiList((prev) => {
      let updated = prev.filter((p) => !removedIds.has(p.id));
      for (const poi of addedPois) {
        if (!updated.some((p) => p.id === poi.id)) {
          updated = [...updated, { ...poi }];
        }
      }
      return updated;
    });

    setDays((prev) =>
      prev.map((day) => ({
        ...day,
        pois: clonePois(day.originalPois),
        modified: false,
      }))
    );
    setActivePoiIndex(-1);
  }

  async function handleFinalizeReplan() {
    if (!canFinalize) return;

    const orderedPoiIdsByDay = {};
    days.forEach((day) => {
      if (day.modified) {
        orderedPoiIdsByDay[day.dayIndex] = day.pois.map((p) => p.id);
      }
    });

    const requestBody = {
      existing_itinerary: currentRouteResponse.itinerary,
      edits: {
        ordered_poi_ids_by_day: orderedPoiIdsByDay,
      },
      constraints: {
        max_daily_distance: (planningInput.distanceKm ?? 20) * 1000,
        max_trip_days: planningInput.days ?? 3,
        max_pois_per_day: 9,
      },
    };

    setReplanLoading(true);

    try {
      const resp = await fetch("/api/v1/routes/replan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      if (!resp.ok) {
        console.error("Replan failed:", resp.status);
        return;
      }

      const data = await resp.json();
      setCurrentRouteResponse(data);

      setDays((prev) =>
        prev.map((day) => {
          const backendDay = data.itinerary.days.find(
            (d) => d.day_index === day.dayIndex
          );

          if (!backendDay) return { ...day, modified: false };

          const newPois = backendDay.pois.map(mapPoiFromBackend);

          return {
            ...day,
            pois: clonePois(newPois),
            originalPois: clonePois(newPois),
            modified: false,
          };
        })
      );
    } catch (err) {
      console.error("Replan error:", err);
    } finally {
      setReplanLoading(false);
    }
  }

  function handleStartJourney() {
    if (!canStart) return;
    navigate("/journey", {
      state: {
        planningInput,
        days,
        routeResponse: currentRouteResponse,
      },
    });
  }

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

        {currentRouteResponse?.warnings?.length > 0 && (
          <section className={styles.warningsBar}>
            {currentRouteResponse.warnings.map((w, i) => (
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
                  activeDay?.modified
                    ? null
                    : currentRouteResponse?.route_plan?.segments?.[activeDayIndex]?.geometry_encoded ?? null
                }
                activeIndex={activePoiIndex}
                onHoverStop={setActivePoiIndex}
                onSelectStop={null}
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

            {availablePoiList.length > 0 && (
              <div className={styles.addRow} ref={addRef}>
                <div className={styles.selectWrap}>
                  <div
                    className={styles.selectTop}
                    onClick={() => setAddOpen(!addOpen)}
                  >
                    <span className={styles.searchIcon}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="11" cy="11" r="8"/>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                      </svg>
                    </span>

                    <input
                      className={styles.selectInput}
                      type="text"
                      placeholder="Search place to add..."
                      value={addSearch}
                      onChange={(e) => {
                        setAddSearch(e.target.value);
                        setAddOpen(true);
                      }}
                      onFocus={() => setAddOpen(true)}
                    />

                    <span className={styles.chev}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="6 9 12 15 18 9"/>
                      </svg>
                    </span>
                  </div>

                  {addOpen && (
                    <div className={styles.dropdown}>
                      <div className={styles.dropdownInner}>
                        {filteredAddPois.map((poi) => (
                          <button
                            key={poi.id}
                            type="button"
                            className={styles.option}
                            onClick={() => handleAddPoiById(poi.id)}
                          >
                            <span className={styles.optionPin}>•</span>
                            {poi.name}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className={styles.poiList}>
              {activeDayPois.length === 0 ? (
                <div className={styles.emptyState}>No POIs in this day yet.</div>
              ) : (
                activeDayPois.map((poi, idx) => {
                  const isDragged = dragState.dragging && dragState.fromIndex === idx;
                  const isOver = dragState.dragging && dragState.overIndex === idx && dragState.fromIndex !== idx;

                  return (
                    <div
                      key={poi.id}
                      className={`
                        ${styles.poiItem}
                        ${isDragged ? styles.poiItemDragging : ""}
                        ${isOver ? styles.poiItemOver : ""}
                      `}
                      onMouseEnter={() => setActivePoiIndex(idx)}
                      onMouseLeave={() => setActivePoiIndex(-1)}
                    >
                      <div
                        className={styles.poiDragHandle}
                        onPointerDown={(e) => handlePointerDown(e, idx)}
                      >
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                          <circle cx="5" cy="3" r="1.5" fill="#8494a7"/>
                          <circle cx="11" cy="3" r="1.5" fill="#8494a7"/>
                          <circle cx="5" cy="8" r="1.5" fill="#8494a7"/>
                          <circle cx="11" cy="8" r="1.5" fill="#8494a7"/>
                          <circle cx="5" cy="13" r="1.5" fill="#8494a7"/>
                          <circle cx="11" cy="13" r="1.5" fill="#8494a7"/>
                        </svg>
                      </div>

                      <div className={styles.poiOrder}>
                        {idx + 1}
                      </div>

                      <div className={styles.poiMain}>
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
              disabled={!canFinalize || replanLoading}
            >
              {replanLoading ? "Replanning..." : "Finalize Replan"}
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
            {replanLoading
              ? "Computing new routes..."
              : anyModified
                ? "Finalize changes before starting."
                : "No pending edits. You can start the journey."}
          </div>
        </section>
      </div>
    </div>
  );
}