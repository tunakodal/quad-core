import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import RouteMap from "./RouteMap";
import styles from "../styles/Journey.module.css";

function enrichPois(pois) {
    return pois.map((poi, idx) => {
        const prev = pois[idx - 1];
        return {
            ...poi,
            stayMin: poi.etaMin ?? null,
            moveMin: prev ? 10 : null, // sadeleştirdik
        };
    });
}

export default function Journey() {
    const { state } = useLocation();
    const navigate = useNavigate();

    const days = state?.days ?? [];
    const planningInput = state?.planningInput;

    const [activeDayIndex, setActiveDayIndex] = useState(0);
    const [activePoiIndex, setActivePoiIndex] = useState(-1);

    const activeDay = days[activeDayIndex];

    const activeDayPois = useMemo(() => {
        if (!activeDay) return [];
        return enrichPois(activeDay.pois);
    }, [activeDay]);

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
                            geometry={null}
                            activeIndex={activePoiIndex}
                            onHoverStop={setActivePoiIndex}
                            onSelectStop={(idx) => handleOpenPoi(activeDayPois[idx], idx)}
                        />
                    </div>
                </div>

                {/* POI CARD */}
                <div className={styles.card}>
                    <div className={styles.cardHeader}>
                        Day {activeDayIndex + 1}
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