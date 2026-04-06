import { useEffect, useRef, useState, useMemo } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import styles from "../styles/Poi.module.css";
import { Button } from "../ui/Button";
import { fetchPoiContent, fetchPoiAudio } from "../api/supabaseClient";

const LANGS = [
  { key: "TR", label: "Dinle", flagUrl: "https://flagcdn.com/w40/tr.png" },
  { key: "EN", label: "Listen", flagUrl: "https://flagcdn.com/w40/us.png" },
  { key: "DE", label: "Hören", flagUrl: "https://flagcdn.com/w40/de.png" },
];

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
  const basePoi = state?.poi ?? null;

  const [poi] = useState(basePoi);
  const [gallery, setGallery] = useState([]);
  const [description, setDescription] = useState(null);
  const [activeLang, setActiveLang] = useState("EN");
  const [loadingContent, setLoadingContent] = useState(true);
  const [activeImg, setActiveImg] = useState(0);

  // Audio
  const [playerOpen, setPlayerOpen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [current, setCurrent] = useState(0);
  const [audioLoading, setAudioLoading] = useState(false);
  const audioRef = useRef(null);

  // Audio element oluştur
  useEffect(() => {
    const a = new Audio();
    audioRef.current = a;

    const onEnded = () => { setIsPlaying(false); setCurrent(0); };
    const onTimeUpdate = () => setCurrent(a.currentTime);
    const onLoaded = () => setDuration(a.duration || 0);

    a.addEventListener("ended", onEnded);
    a.addEventListener("timeupdate", onTimeUpdate);
    a.addEventListener("loadedmetadata", onLoaded);

    return () => {
      a.pause();
      a.removeEventListener("ended", onEnded);
      a.removeEventListener("timeupdate", onTimeUpdate);
      a.removeEventListener("loadedmetadata", onLoaded);
    };
  }, []);

  // POI değişince resim + açıklama çek
  useEffect(() => {
    if (!poiId) return;
    setLoadingContent(true);
    setGallery([]);
    setDescription(null);
    setActiveImg(0);

    fetchPoiContent(poiId, "EN").then(({ images, description: desc }) => {
      setGallery(images);
      setDescription(desc);
      setLoadingContent(false);
    });
  }, [poiId]);

  // Dil değişince açıklamayı güncelle
  useEffect(() => {
    if (!poiId) return;
    fetchPoiContent(poiId, activeLang).then(({ description: desc }) => {
      if (desc) setDescription(desc);
    });
  }, [activeLang, poiId]);

  // Audio player aç
  const openPlayer = async (langKey) => {
    const a = audioRef.current;
    if (a) {
      a.pause();
      a.removeAttribute("src");
    }

    setActiveLang(langKey);
    setPlayerOpen(true);
    setAudioLoading(true);
    setIsPlaying(false);
    setCurrent(0);
    setDuration(0);

    const audioUrl = await fetchPoiAudio(poiId, langKey);
    console.log("Audio URL:", audioUrl);

    if (!audioUrl || !audioRef.current) {
      setAudioLoading(false);
      return;
    }

    const audio = audioRef.current;
    audio.src = audioUrl;
    audio.load();

    // Yüklenmeyi bekle (max 10 saniye)
    const loaded = await new Promise((resolve) => {
      const timeout = setTimeout(() => resolve(false), 10000);
      const onReady = () => {
        clearTimeout(timeout);
        audio.removeEventListener("canplay", onReady);
        audio.removeEventListener("error", onErr);
        resolve(true);
      };
      const onErr = (e) => {
        clearTimeout(timeout);
        console.error("Audio load error:", e);
        audio.removeEventListener("canplay", onReady);
        audio.removeEventListener("error", onErr);
        resolve(false);
      };
      audio.addEventListener("canplay", onReady);
      audio.addEventListener("error", onErr);
    });

    setDuration(audio.duration || 0);
    setAudioLoading(false);

    if (!loaded) return;

    try {
      await audio.play();
      setIsPlaying(true);
    } catch (e) {
      console.warn("Audio play failed:", e);
      setIsPlaying(false);
    }
  };
  const togglePlay = () => {
    const a = audioRef.current;
    if (!a || !a.src) return;
    if (isPlaying) {
      a.pause();
      setIsPlaying(false);
    } else {
      a.play().then(() => setIsPlaying(true)).catch(console.warn);
    }
  };

  const seek = (sec) => {
    const a = audioRef.current;
    const s = Math.max(0, Math.min(duration, sec));
    if (a && a.src) a.currentTime = s;
    setCurrent(s);
  };

  const jump = (delta) => seek(current + delta);

  const closePlayer = () => {
    const a = audioRef.current;
    if (a) { a.pause(); a.currentTime = 0; }
    setPlayerOpen(false);
    setIsPlaying(false);
    setCurrent(0);
  };

  // Prev / Next POI
  const effectiveIndex = useMemo(() => {
    if (routePois && routeIndex != null) return routeIndex;
    return null;
  }, [routePois, routeIndex]);

  const prevPoi = useMemo(() => {
    if (!routePois || effectiveIndex == null) return null;
    return routePois[effectiveIndex - 1] ?? null;
  }, [routePois, effectiveIndex]);

  const nextPoi = useMemo(() => {
    if (!routePois || effectiveIndex == null) return null;
    return routePois[effectiveIndex + 1] ?? null;
  }, [routePois, effectiveIndex]);

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

  const mainPhoto = gallery[activeImg] ?? gallery[0] ?? null;

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
              {mainPhoto
                ? <img src={mainPhoto} alt={poi.name} />
                : <div className={styles.photoPlaceholder} />
              }
            </div>

            <div className={styles.info}>
              <h2 className={styles.name}>{poi.name}</h2>

              <div className={styles.meta}>
                <span>{poi.city ?? "—"}</span>
                <span className={styles.dot}>•</span>
                <span>Est. visit: <b>{poi.etaMin ?? poi.estimated_visit_duration ?? "—"} min</b></span>
              </div>

              <div className={styles.chips}>
                {[poi.category].filter(Boolean).map((c) => (
                  <span key={c} className={styles.chip}>{c}</span>
                ))}
              </div>

              {/* Dil butonları */}
              <div className={styles.langRow}>
                {LANGS.map((l) => (
                  <button
                    key={l.key}
                    type="button"
                    className={`${styles.langBtn} ${activeLang === l.key && playerOpen ? styles.langBtnOn : ""}`}
                    onClick={() => openPlayer(l.key)}
                  >
                    <span className={styles.flagWrap}>
                      <img src={l.flagUrl} alt="" />
                    </span>
                    <span className={styles.langText}>{l.label}</span>
                    <span className={styles.langCode}>{l.key}</span>
                  </button>
                ))}
              </div>

              {/* Audio Player */}
              {playerOpen && (
                <div className={styles.player}>
                  <div className={styles.playerTop}>
                    <div className={styles.playerTitle}>
                      Audio • {activeLang}
                    </div>
                    <button
                      type="button"
                      className={styles.playerClose}
                      onClick={closePlayer}
                      aria-label="Close audio"
                    >
                      ✕
                    </button>
                  </div>

                  {audioLoading ? (
                    <div className={styles.audioLoading}>Loading audio…</div>
                  ) : (
                    <>
                      <div className={styles.progressWrap}>
                        <input
                          type="range"
                          min={0}
                          max={duration || 0}
                          value={current}
                          onChange={(e) => seek(toInt(e.target.value, current))}
                          className={styles.progress}
                          style={{ "--pct": `${duration ? (current / duration) * 100 : 0}%` }}
                        />
                        <div className={styles.progressTime}>
                          {fmt(current)} / {fmt(duration)}
                        </div>
                      </div>

                      <div className={styles.playerCtrls}>
                        <button className={styles.ctrlBtn} onClick={() => jump(-10)}>−10s</button>
                        <button className={styles.playBtn} onClick={togglePlay}>
                          <span className={styles.playIcon}>
                            {isPlaying ? "⏸" : "▶"}
                          </span>
                        </button>
                        <button className={styles.ctrlBtn} onClick={() => jump(10)}>+10s</button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Açıklama */}
              <div className={styles.desc}>
                {loadingContent
                  ? "Loading description…"
                  : description ?? "No description available."}
              </div>
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
                <div className={styles.navArrow}>←</div>
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
                  {gallery[0]
                    ? <img src={gallery[0]} alt={nextPoi?.name} />
                    : <div className={styles.nextHeroPh} />
                  }
                </div>
                <div className={styles.navNextRow}>
                  <div className={styles.navTexts}>
                    <div className={styles.navTop}>Next</div>
                    <div className={styles.navName}>{nextPoi?.name ?? "—"}</div>
                  </div>
                  <div className={styles.navArrow}>→</div>
                </div>
              </button>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
