import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import RouteMap from "./RouteMap";
import styles from "./Route.module.css";
import { Button } from "../ui/Button";

const DEV_POIS = [
  {
    id: "p1",
    name: "Hagia Sophia",
    etaMin: 25, // stay
    lat: 41.0086,
    lng: 28.9802,
    imageUrl: "",
  },
  {
    id: "p2",
    name: "Topkapi Palace",
    etaMin: 35,
    lat: 41.0115,
    lng: 28.9833,
    imageUrl: "",
  },
  {
    id: "p3",
    name: "Galata Tower",
    etaMin: 30,
    lat: 41.0256,
    lng: 28.9744,
    imageUrl: "",
  },
];

// ---- travel estimate (backend gelene kadar) ----
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

export default function Route() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const planningInput = state?.planningInput;

  const pois = useMemo(() => (import.meta.env.DEV ? DEV_POIS : []), []);
  const geometry = null;

  const [activeIndex, setActiveIndex] = useState(-1);
  const [isFinished, setIsFinished] = useState(false);

  // ✅ FIX: burada pois.map olmalıydı (poisWithTimes.map değil)
  const poisWithTimes = useMemo(() => {
    if (!pois?.length) return [];
    return pois.map((p, i) => {
      const prev = pois[i - 1];
      return {
        ...p,
        stayMin: p.etaMin ?? null,
        // Move = previous -> current
        moveMin: prev ? estimateMoveMin(prev, p) : null,
      };
    });
  }, [pois]);

  // ✅ POI’ye giderken route state’i taşı
  const openPoi = (poi, idx) => {
    if (!poi) return;
    navigate(`/poi/${poi.id}`, {
      state: {
        poi, // seçilen POI
        pois: poisWithTimes, // route listesi (prev/next için)
        index: idx, // sıradaki index
        planningInput,
      },
    });
  };

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <h2 className={styles.title}>Your Route</h2>

        <div className={styles.metaRow}>
          <div className={styles.metaItem}>
            <span className={styles.metaKey}>City:</span>
            <span className={styles.metaValue}>{planningInput?.cityId ?? "—"}</span>
          </div>
          <div className={styles.metaItem}>
            <span className={styles.metaKey}>Days:</span>
            <span className={styles.metaValue}>{planningInput?.days ?? "—"}</span>
          </div>
          <div className={styles.metaItem}>
            <span className={styles.metaKey}>Distance:</span>
            <span className={styles.metaValue}>
              {planningInput?.distanceKm ? `${planningInput.distanceKm} km` : "—"}
            </span>
          </div>
          <div className={styles.metaItem}>
            <span className={styles.metaKey}>Interests:</span>
            <span className={styles.metaValue}>{planningInput?.categories?.length ?? "—"}</span>
          </div>
        </div>

        <div className={styles.grid}>
          <div className={styles.left}>
            <div className={`${styles.card} ${styles.detailsCard}`}>
              <div className={styles.cardTitle}>Map</div>

              <RouteMap
                cityId={planningInput?.cityId}
                stops={poisWithTimes}
                geometry={geometry}
                activeIndex={activeIndex}
                onHoverStop={setActiveIndex}
                onSelectStop={(idx) => openPoi(poisWithTimes[idx], idx)}
              />

              {!planningInput && (
                <div className={styles.note}>
                  No planning input received. Go back to Planning and generate again.
                </div>
              )}
            </div>
          </div>

          <aside className={styles.right}>
            <div className={styles.card}>
              <div className={styles.cardTitle}>Route Details</div>

              <div className={styles.poiScroll}>
                {poisWithTimes.length === 0 ? (
                  <div className={styles.empty}>
                    POI list will appear here when backend is connected.
                  </div>
                ) : (
                  <ol className={styles.poiList}>
                    {poisWithTimes.map((p, idx) => (
                      <li
                        key={p.id ?? idx}
                        className={styles.poiItem}
                        role="button"
                        tabIndex={0}
                        onMouseEnter={() => setActiveIndex(idx)}
                        onMouseLeave={() => setActiveIndex(-1)}
                        onClick={() => openPoi(p, idx)}
                        onKeyDown={(e) => e.key === "Enter" && openPoi(p, idx)}
                        title="Open POI"
                      >
                        <div className={styles.poiIdx}>{idx + 1}</div>

                        <div className={styles.poiThumb} aria-hidden="true">
                          {p.imageUrl ? (
                            <img className={styles.poiImg} src={p.imageUrl} alt="" />
                          ) : (
                            <div className={styles.poiImgPh} />
                          )}
                        </div>

                        <div className={styles.poiBody}>
                          <div className={styles.poiName}>{p.name}</div>

                          <div className={styles.timeRow}>
                            <span className={styles.timeChip}>
                              <span className={styles.timeIcon} aria-hidden="true">
                                ⏱
                              </span>
                              <span>Stay</span>
                              <b>{p.stayMin ? `${p.stayMin}m` : "—"}</b>
                            </span>

                            {idx > 0 && p.moveMin ? (
                              <span className={styles.timeChip}>
                                <span className={styles.timeIcon} aria-hidden="true">
                                  ➜
                                </span>
                                <span>Move</span>
                                <b>{`${p.moveMin}m`}</b>
                              </span>
                            ) : null}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </div>

              {!isFinished && (
                <div className={styles.actions}>
                  <Button
                    variant="ghost"
                    className={styles.longThinBtn}
                    onClick={() => navigate("/replanning", { state: { planningInput } })}
                  >
                    Replan
                  </Button>

                  <Button
                    variant="primary"
                    className={styles.longThinBtn}
                    onClick={() => setIsFinished(true)}
                  >
                    Finish
                  </Button>
                </div>
              )}

              {isFinished && <div className={styles.finishMsg}>Enjoy your trip ✨</div>}
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}