import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import styles from "./Poi.module.css";
import { Button } from "../ui/Button";

/** DEV fallback */
const DEV_POIS = [
  {
    id: "p1",
    name: "Hagia Sophia",
    city: "Istanbul",
    country: "Türkiye",
    estVisitMin: 55,
    categories: ["Landmark", "Historical"],
    gallery: [
      "/placeholder.jpg",
      "/placeholder.jpg",
      "/placeholder.jpg",
    ],
    description:
      "Hagia Sophia is one of Istanbul’s most iconic landmarks. Originally built as a cathedral, later a mosque, and now a museum-mosque, it represents layers of history. Its dome, mosaics, and massive interior make it a must-see. Plan your visit early to avoid crowds.",
  },
  {
    id: "p2",
    name: "Topkapi Palace",
    city: "Istanbul",
    country: "Türkiye",
    estVisitMin: 75,
    categories: ["Museum"],
    gallery: [
      "/placeholder.jpg",
      "/placeholder.jpg",
      "/placeholder.jpg",    ],
    description:
      "Topkapi Palace served as the main residence of the Ottoman sultans for centuries. Explore courtyards, treasury rooms, and panoramic views of the Bosphorus. Expect security lines and allocate enough time for highlights.",
  },
];

const LANGS = [
  { key: "tr", label: "Dinle", flagUrl: "https://flagcdn.com/w40/tr.png" },
  { key: "en", label: "Listen", flagUrl: "https://flagcdn.com/w40/us.png" },
  { key: "de", label: "Hören", flagUrl: "https://flagcdn.com/w40/de.png" },
];

const DEV_AUDIO_DURATION_SEC = 5 * 60 + 12;

const fmt = (sec) => {
  const s = Math.max(0, Math.floor(sec || 0));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
};

const toInt = (v, fallback) => {
  const n = parseInt(String(v ?? "").replace(/[^\d]/g, ""), 10);
  return Number.isFinite(n) ? n : fallback;
};

export default function Poi() {
  const navigate = useNavigate();
  const { poiId } = useParams();
  const { state } = useLocation();

  const routePois = state?.pois ?? null;
  const routeIndex = Number.isFinite(state?.index) ? state.index : null;

  // DEMO İÇİN. SİLİNECEK
  const fallbackPois = useMemo(() => {
    // Eğer state ile route gelmediyse, DEV datasını "route" gibi kullan
    return import.meta.env.DEV ? DEV_POIS : [];
  }, []);

  const effectivePois = routePois?.length ? routePois : (fallbackPois.length ? fallbackPois : null);

  const effectiveIndex = useMemo(() => {
    if (routePois?.length && routeIndex != null) return routeIndex;

    // route yoksa: poiId'ye göre DEV listesinde index bul
    if (!effectivePois?.length) return null;
    const idx = effectivePois.findIndex((x) => String(x.id) === String(poiId));
    return idx >= 0 ? idx : 0;
  }, [routePois, routeIndex, effectivePois, poiId]);
  // DEMO SON

  const [poi, setPoi] = useState(state?.poi ?? null);

  // gallery
  const [activeImg, setActiveImg] = useState(0);

  // audio ui
  const [activeLang, setActiveLang] = useState(null);
  const [playerOpen, setPlayerOpen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  // progress
  const [duration, setDuration] = useState(DEV_AUDIO_DURATION_SEC);
  const [current, setCurrent] = useState(0);
  const rafRef = useRef(null);

  const audioRef = useRef(null);

  useEffect(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.preload = "auto";
    }
    const a = audioRef.current;

    const onEnded = () => setIsPlaying(false);
    a.addEventListener("ended", onEnded);
    return () => a.removeEventListener("ended", onEnded);
  }, []);

  // POI load hook
  useEffect(() => {
  let cancelled = false;

  async function load() {
    // Backend gelince:
    // const data = await fetch(`/api/pois/${poiId}`).then(r=>r.json());
    // if(!cancelled) setPoi(data);

    const found = DEV_POIS.find((x) => String(x.id) === String(poiId)) ?? DEV_POIS[0];

    // ✅ Route'tan gelen "kısa" poi varsa, onu dummy ile birleştir:
    // dummy: description/gallery/city vs sağlar
    // state.poi: backend gelince güncel alanları override eder
    const merged = state?.poi ? { ...found, ...state.poi } : found;

    if (!cancelled) setPoi(merged);
  }

  load();
  return () => {
    cancelled = true;
  };
}, [poiId, state]);

  // poi değişince reset
  useEffect(() => {
    setActiveImg(0);
    setActiveLang(null);
    setPlayerOpen(false);
    setIsPlaying(false);
    setCurrent(0);
    setDuration(DEV_AUDIO_DURATION_SEC);

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    cancelAnimationFrame(rafRef.current);
  }, [poi?.id]);

  const gallery = poi?.gallery?.length ? poi.gallery : [];
  const mainPhoto = gallery[activeImg] ?? gallery[0] ?? null;

  const prevPoi = useMemo(() => {
    if (!effectivePois || effectiveIndex == null) return null;
    return effectivePois[effectiveIndex - 1] ?? null;
  }, [effectivePois, effectiveIndex]);

  const nextPoi = useMemo(() => {
    if (!effectivePois || effectiveIndex == null) return null;
    return effectivePois[effectiveIndex + 1] ?? null;
  }, [effectivePois, effectiveIndex]);

  const goPoi = (p) => {
    if (!p) return;
    const idx = routePois ? routePois.findIndex((x) => x.id === p.id) : null;

    navigate(`/poi/${p.id}`, {
      state: {
        ...state,
        poi: p,
        pois: routePois ?? state?.pois ?? null,
        index: idx != null && idx >= 0 ? idx : state?.index ?? null,
      },
    });
  };

  const backToRoute = () => navigate("/route", { state: state ?? {} });

  // --- player behaviour ---
  const tick = () => {
    rafRef.current = requestAnimationFrame(() => {
      setCurrent((t) => {
        if (!isPlaying) return t;
        const next = Math.min(duration, t + 0.25);
        return next >= duration ? duration : next;
      });
      tick();
    });
  };

  const startTicking = () => {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(tick);
  };

  const openPlayer = (langKey) => {
    setActiveLang(langKey);
    setPlayerOpen(true);

    // Backend gelince:
    // fetch(`/api/tts?poiId=${poi.id}&lang=${langKey}`) -> { audioUrl, durationSec }
    // audioRef.current.src = audioUrl; setDuration(durationSec); audioRef.current.play();

    setIsPlaying(true);
    startTicking();
  };

  const togglePlay = () => {
    setIsPlaying((p) => {
      const next = !p;
      if (next) startTicking();
      return next;
    });
  };

  const seek = (sec) => {
    const s = Math.max(0, Math.min(duration, sec));
    setCurrent(s);
    // backend gelince: audioRef.current.currentTime = s;
  };

  const jump = (delta) => seek(current + delta);

  const closePlayer = () => {
    setPlayerOpen(false);
    setIsPlaying(false);
    setCurrent(0);
    // backend gelince: audioRef.current.pause(); audioRef.current.currentTime = 0;
  };

  if (!poi) {
    return (
      <div className={styles.page}>
        <div className={styles.loading}>Loading…</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div className={styles.layout}>
          {/* LEFT */}
          <section className={styles.left}>
            <div className={styles.mainPhoto}>
              {mainPhoto ? <img src={mainPhoto} alt={poi.name} /> : null}
            </div>

            <div className={styles.info}>
              <h2 className={styles.name}>{poi.name}</h2>

              <div className={styles.meta}>
                <span>
                  {poi.city}, {poi.country ?? "Türkiye"}
                </span>
                <span className={styles.dot}>•</span>
                <span>
                  Est. visit: <b>{poi.estVisitMin ?? "—"} min</b>
                </span>
              </div>

              <div className={styles.chips}>
                {(poi.categories ?? []).map((c) => (
                  <span key={c} className={styles.chip}>
                    {c}
                  </span>
                ))}
              </div>

              {/* Language buttons ALWAYS visible */}
              <div className={styles.langRow}>
                {LANGS.map((l) => (
                  <button
                    key={l.key}
                    type="button"
                    className={`${styles.langBtn} ${activeLang === l.key ? styles.langBtnOn : ""}`}
                    onClick={() => openPlayer(l.key)}
                  >
                    <span className={styles.flagWrap}>
                      <img src={l.flagUrl} alt="" />
                    </span>
                    <span className={styles.langText}>{l.label}</span>
                    <span className={styles.langCode}>{l.key.toUpperCase()}</span>
                  </button>
                ))}
              </div>

              {/* Player bar */}
              {playerOpen ? (
                <div className={styles.player}>
                  <div className={styles.playerTop}>
                    <div className={styles.playerTitle}>
                      {activeLang ? `Audio • ${activeLang.toUpperCase()}` : "Audio"}
                    </div>

                    <button
                      type="button"
                      className={styles.playerClose}
                      onClick={closePlayer}
                      aria-label="Close audio"
                      title="Close"
                    >
                      ✕
                    </button>
                  </div>

                  <div className={styles.progressWrap}>
                    <input
                      type="range"
                      min={0}
                      max={duration || 0}
                      value={current}
                      onChange={(e) => seek(toInt(e.target.value, current))}
                      className={styles.progress}
                      style={{
                        "--pct": `${duration ? (current / duration) * 100 : 0}%`,
                      }}
                    />

                    <div className={styles.progressTime}>
                      {fmt(current)} / {fmt(duration)}
                    </div>
                  </div>

                  <div className={styles.playerCtrls}>
                    <button className={styles.ctrlBtn} onClick={() => jump(-10)} aria-label="Back 10s">
                      −10s
                    </button>

                    <button className={styles.playBtn} onClick={togglePlay} aria-label="Play/Pause">
                      <span className={styles.playIcon} aria-hidden="true">
                        {isPlaying ? "❚❚" : "▶"}
                      </span>
                    </button>

                    <button className={styles.ctrlBtn} onClick={() => jump(10)} aria-label="Forward 10s">
                      +10s
                    </button>
                  </div>
                </div>
              ) : null}

              <div className={styles.desc}>{poi.description ?? "—"}</div>
            </div>
          </section>

          {/* RIGHT */}
          <aside className={styles.right}>
            <div className={styles.galleryTop}>
              <div className={styles.galleryStrip}>
                {gallery.slice(0, 6).map((url, i) => (
                  <button
                    key={url}
                    type="button"
                    className={`${styles.thumb} ${i === activeImg ? styles.thumbOn : ""}`}
                    onClick={() => setActiveImg(i)}
                    aria-label={`Photo ${i + 1}`}
                  >
                    <img src={url} alt="" />
                  </button>
                ))}
              </div>

              <div className={styles.dots}>
                {gallery.slice(0, 6).map((_, i) => (
                  <button
                    key={i}
                    type="button"
                    className={`${styles.dotBtn} ${i === activeImg ? styles.dotOn : ""}`}
                    onClick={() => setActiveImg(i)}
                    aria-label={`Select photo ${i + 1}`}
                  />
                ))}
              </div>
            </div>

            <div className={styles.nav}>
              <button
                  type="button"
                  className={`${styles.navCard} ${!prevPoi ? styles.navDisabled : ""}`}
                  onClick={() => goPoi(prevPoi)}
                  disabled={!prevPoi}
              >
                <div className={styles.navArrow} aria-hidden="true">
                  ←
                </div>
                <div className={styles.navTexts}>
                  <div className={styles.navTop}>Previous</div>
                  <div className={styles.navName}>{prevPoi?.name ?? "—"}</div>
                </div>
              </button>

              <Button variant="ghost" className={styles.backBtn} onClick={backToRoute}>
                Back to Route
              </Button>

              <button
                  type="button"
                  className={`${styles.navCard} ${styles.navNextBig} ${!nextPoi ? styles.navDisabled : ""}`}
                  onClick={() => goPoi(nextPoi)}
                  disabled={!nextPoi}
              >
                <div className={styles.nextHero}>
                  {nextPoi?.gallery?.[0] ? (
                      <img src={nextPoi.gallery[0]} alt={nextPoi.name}/>
                  ) : (
                      <div className={styles.nextHeroPh}/>
                  )}
                </div>

                <div className={styles.navNextRow}>
                  <div className={styles.navTexts}>
                    <div className={styles.navTop}>Next</div>
                    <div className={styles.navName}>{nextPoi?.name ?? "—"}</div>
                  </div>

                  <div className={styles.navArrow} aria-hidden="true">→</div>
                </div>
              </button>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}