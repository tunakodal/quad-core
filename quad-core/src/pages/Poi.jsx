import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import styles from "../styles/Poi.module.css";
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

  const basePoi = state?.poi ?? null;

  const [poi] = useState(basePoi);
  const [gallery, setGallery] = useState([]);
  const [description, setDescription] = useState(null);
  const [activeLang, setActiveLang] = useState("EN");
  const [loadingContent, setLoadingContent] = useState(true);
  const [activeImg, setActiveImg] = useState(0);

  const [playerOpen, setPlayerOpen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [current, setCurrent] = useState(0);
  const [audioLoading, setAudioLoading] = useState(false);
  const audioRef = useRef(null);
  const progressRef = useRef(null);

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

  useEffect(() => {
    if (!poiId) return;
    fetchPoiContent(poiId, activeLang).then(({ description: desc }) => {
      if (desc) setDescription(desc);
    });
  }, [activeLang, poiId]);

  const openPlayer = async (langKey) => {
    const a = audioRef.current;
    if (a) { a.pause(); a.removeAttribute("src"); }
    setActiveLang(langKey);
    setPlayerOpen(true);
    setAudioLoading(true);
    setIsPlaying(false);
    setCurrent(0);
    setDuration(0);
    const audioUrl = await fetchPoiAudio(poiId, langKey);
    if (!audioUrl || !audioRef.current) { setAudioLoading(false); return; }
    const audio = audioRef.current;
    audio.src = audioUrl;
    audio.load();
    const loaded = await new Promise((resolve) => {
      const timeout = setTimeout(() => resolve(false), 10000);
      const onReady = () => { clearTimeout(timeout); audio.removeEventListener("canplay", onReady); audio.removeEventListener("error", onErr); resolve(true); };
      const onErr = () => { clearTimeout(timeout); audio.removeEventListener("canplay", onReady); audio.removeEventListener("error", onErr); resolve(false); };
      audio.addEventListener("canplay", onReady);
      audio.addEventListener("error", onErr);
    });
    setDuration(audio.duration || 0);
    setAudioLoading(false);
    if (!loaded) return;
    try { await audio.play(); setIsPlaying(true); } catch { setIsPlaying(false); }
  };

  const togglePlay = () => {
    const a = audioRef.current;
    if (!a || !a.src) return;
    if (isPlaying) { a.pause(); setIsPlaying(false); }
    else { a.play().then(() => setIsPlaying(true)).catch(() => {}); }
  };

  const seek = (sec) => {
    const a = audioRef.current;
    const s = Math.max(0, Math.min(duration, sec));
    if (a && a.src) a.currentTime = s;
    setCurrent(s);
  };

  const handleProgressClick = (e) => {
    const bar = progressRef.current;
    if (!bar || !duration) return;
    const rect = bar.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    seek(pct * duration);
  };

  const jump = (delta) => seek(current + delta);

  const closePlayer = () => {
    const a = audioRef.current;
    if (a) { a.pause(); a.currentTime = 0; }
    setPlayerOpen(false);
    setIsPlaying(false);
    setCurrent(0);
  };

  const handleBack = () => navigate(-1);

  const mainPhoto = gallery[activeImg] ?? gallery[0] ?? null;
  const pct = duration ? (current / duration) * 100 : 0;

  if (!poi) {
    return (
      <div className={styles.page}>
        <div className={styles.loading}>Loading…</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.container}>

        <button type="button" className={styles.backBtn} onClick={handleBack}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"/>
            <polyline points="12 19 5 12 12 5"/>
          </svg>
          <span>Back</span>
        </button>

        <div className={styles.layout}>
          {/* LEFT */}
          <section className={styles.left}>
            <div className={styles.heroImage}>
              {mainPhoto
                ? <img src={mainPhoto} alt={poi.name} />
                : <div className={styles.heroPlaceholder} />
              }
            </div>

            <div className={styles.infoCard}>
              <h1 className={styles.name}>{poi.name}</h1>

              <div className={styles.meta}>
                {poi.city && <span className={styles.metaChip}>{poi.city}</span>}
                {poi.category && <span className={styles.metaChip}>{poi.category}</span>}
                <span className={styles.metaChip}>
                  {poi.etaMin ?? poi.estimated_visit_duration ?? "—"} min visit
                </span>
              </div>

              <div className={styles.description}>
                {loadingContent
                  ? "Loading description…"
                  : description ?? "No description available."}
              </div>
            </div>
          </section>

          {/* RIGHT */}
          <aside className={styles.right}>
            {/* GALLERY */}
            {gallery.length > 1 && (
              <div className={styles.galleryCard}>
                <div className={styles.thumbStrip}>
                  {gallery.slice(0, 6).map((url, i) => (
                    <button
                      key={url}
                      type="button"
                      className={`${styles.thumb} ${i === activeImg ? styles.thumbActive : ""}`}
                      onClick={() => setActiveImg(i)}
                    >
                      <img src={url} alt="" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* AUDIO CARD */}
            <div className={styles.audioCard}>
              <div className={styles.audioTitle}>Audio Guide</div>

              <div className={styles.langRow}>
                {LANGS.map((l) => (
                  <button
                    key={l.key}
                    type="button"
                    className={`${styles.langBtn} ${activeLang === l.key && playerOpen ? styles.langBtnActive : ""}`}
                    onClick={() => openPlayer(l.key)}
                  >
                    <img src={l.flagUrl} alt="" className={styles.flag} />
                    <span>{l.label}</span>
                  </button>
                ))}
              </div>

              {playerOpen && (
                <div className={styles.player}>
                  <div className={styles.playerHeader}>
                    <span className={styles.playerLabel}>Playing — {activeLang}</span>
                    <button type="button" className={styles.playerClose} onClick={closePlayer}>×</button>
                  </div>

                  {audioLoading ? (
                    <div className={styles.playerLoading}>Loading audio…</div>
                  ) : (
                    <>
                      <div
                        className={styles.progressTrack}
                        ref={progressRef}
                        onClick={handleProgressClick}
                      >
                        <div className={styles.progressFill} style={{ width: `${pct}%` }} />
                        <div className={styles.progressThumb} style={{ left: `${pct}%` }} />
                      </div>

                      <div className={styles.timeRow}>
                        <span>{fmt(current)}</span>
                        <span>{fmt(duration)}</span>
                      </div>

                      <div className={styles.controls}>
                        <button className={styles.skipBtn} onClick={() => jump(-10)}>−10s</button>
                        <button className={styles.playBtn} onClick={togglePlay}>
                          {isPlaying ? "⏸" : "▶"}
                        </button>
                        <button className={styles.skipBtn} onClick={() => jump(10)}>+10s</button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </aside>
        </div>

      </div>
    </div>
  );
}