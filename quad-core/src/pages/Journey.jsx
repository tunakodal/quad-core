import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import RouteMap from "./RouteMap";
import styles from "../styles/Journey.module.css";

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

function enrichPois(pois, segment) {
    // OSRM segment'ten leg sürelerini al (saniye → dakika)
    const legs = segment?.legs ?? null;

    return pois.map((poi, idx) => {
        const prev = pois[idx - 1];
        let moveMin = null;

        if (prev) {
            const legDuration = legs?.[idx - 1]?.duration;
            if (typeof legDuration === "number") {
                moveMin = Math.max(1, Math.round(legDuration / 60));
            } else {
                // OSRM yoksa haversine fallback
                moveMin = estimateMoveMin(prev, poi);
            }
        }

        return {
            ...poi,
            stayMin: poi.etaMin ?? null,
            moveMin,
        };
    });
}

export default function Journey() {
    const { state } = useLocation();
    const navigate = useNavigate();

    const days = state?.days ?? [];
    const planningInput = state?.planningInput;
    const routeResponse = state?.routeResponse ?? null;

    const [activeDayIndex, setActiveDayIndex] = useState(0);
    const [activePoiIndex, setActivePoiIndex] = useState(-1);

    const activeDay = days[activeDayIndex];

    const activeSegment = useMemo(
        () => routeResponse?.route_plan?.segments?.[activeDayIndex] ?? null,
        [routeResponse, activeDayIndex]
    );

    const activeDayPois = useMemo(() => {
        if (!activeDay) return [];
        return enrichPois(activeDay.pois, activeSegment);
    }, [activeDay, activeSegment]);

    const totalDuration = useMemo(() => {
        return activeDayPois.reduce(
            (sum, poi) => sum + (poi.stayMin ?? 0) + (poi.moveMin ?? 0),
            0
        );
    }, [activeDayPois]);

    const totalDistanceKm = useMemo(() => {
        if (activeSegment?.distance) {
            return (activeSegment.distance / 1000).toFixed(1);
        }
        return null;
    }, [activeSegment]);

    function handleOpenPoi(poi, idx) {
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

    return (
        <div className={styles.page}>

            {/* LEFT DAYS */}
            <div className={styles.daysPanel}>
                {days.map((day, idx) => {
                    const isActive = idx === activeDayIndex;

                    return (
                        <button
                            key={day.dayIndex}
                            onClick={() => {
                                setActiveDayIndex(idx);
                                setActivePoiIndex(-1);
                            }}
                            className={`${styles.dayButton} ${
                                isActive ? styles.active : ""
                            }`}
                        >
                            DAY {idx + 1}
                        </button>
                    );
                })}
            </div>

            {/* DIVIDER */}
            <div className={styles.divider} />

            {/* RIGHT SIDE */}
            <div className={styles.content}>

                {/* MAP CARD */}
                <div className={styles.card}>
                    <div className={styles.cardHeader}>
                        Map
                    </div>

                    <div className={styles.mapWrap}>
                        <RouteMap
                            cityId={planningInput?.cityId}
                            stops={activeDayPois}
                            geometry={activeSegment?.geometry_encoded ?? null}
                            activeIndex={activePoiIndex}
                            onHoverStop={setActivePoiIndex}
                            onSelectStop={(idx) => handleOpenPoi(activeDayPois[idx], idx)}
                        />
                    </div>
                </div>

                {/* POI CARD */}
                <div className={styles.card}>
                    <div className={styles.cardHeader}>
                        <span>Day {activeDayIndex + 1}</span>
                        <span className={styles.dayStats}>
                            {totalDistanceKm && <span>{totalDistanceKm} km</span>}
                            {totalDistanceKm && <span className={styles.statsDot}>·</span>}
                            <span>{totalDuration} min</span>
                        </span>
                    </div>

                    <div className={styles.poiGrid}>
                        {activeDayPois.map((poi, idx) => (
                            <div
                                key={poi.id}
                                className={styles.poiCard}
                                onMouseEnter={() => setActivePoiIndex(idx)}
                                onMouseLeave={() => setActivePoiIndex(-1)}
                                onClick={() => handleOpenPoi(poi, idx)}
                            >
                                <div className={styles.poiIndex}>{idx + 1}</div>

                                <div>
                                    <div className={styles.poiName}>{poi.name}</div>

                                    <div className={styles.poiMeta}>
                                        <span>Stay {poi.stayMin ?? "—"} min</span>
                                        {idx > 0 && <span>Move {poi.moveMin ?? "—"} min</span>}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    );
}