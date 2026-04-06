import { useEffect, useMemo, useState } from "react";
import styles from "../styles/Planning.module.css";
import { Button } from "../ui/Button";
import { useNavigate } from "react-router-dom";

const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
const toInt = (v, fallback) => {
  const n = parseInt(String(v ?? "").replace(/[^\d]/g, ""), 10);
  return Number.isFinite(n) ? n : fallback;
};

const ALL_CITIES = [
  { id: "istanbul", name: "İstanbul" },
  { id: "ankara", name: "Ankara" },
  { id: "izmir", name: "İzmir" },

  { id: "adana", name: "Adana" },
  { id: "adiyaman", name: "Adıyaman" },
  { id: "afyon", name: "Afyonkarahisar" },
  { id: "agri", name: "Ağrı" },
  { id: "aksaray", name: "Aksaray" },
  { id: "amasya", name: "Amasya" },
  { id: "antalya", name: "Antalya" },
  { id: "ardahan", name: "Ardahan" },
  { id: "artvin", name: "Artvin" },
  { id: "aydin", name: "Aydın" },

  { id: "balikesir", name: "Balıkesir" },
  { id: "bartin", name: "Bartın" },
  { id: "batman", name: "Batman" },
  { id: "bayburt", name: "Bayburt" },
  { id: "bilecik", name: "Bilecik" },
  { id: "bingol", name: "Bingöl" },
  { id: "bitlis", name: "Bitlis" },
  { id: "bolu", name: "Bolu" },
  { id: "burdur", name: "Burdur" },
  { id: "bursa", name: "Bursa" },

  { id: "canakkale", name: "Çanakkale" },
  { id: "cankiri", name: "Çankırı" },
  { id: "corum", name: "Çorum" },

  { id: "denizli", name: "Denizli" },
  { id: "diyarbakir", name: "Diyarbakır" },
  { id: "duzce", name: "Düzce" },

  { id: "edirne", name: "Edirne" },
  { id: "elazig", name: "Elazığ" },
  { id: "erzincan", name: "Erzincan" },
  { id: "erzurum", name: "Erzurum" },
  { id: "eskisehir", name: "Eskişehir" },

  { id: "gaziantep", name: "Gaziantep" },
  { id: "giresun", name: "Giresun" },
  { id: "gumushane", name: "Gümüşhane" },

  { id: "hakkari", name: "Hakkâri" },
  { id: "hatay", name: "Hatay" },

  { id: "igdir", name: "Iğdır" },
  { id: "isparta", name: "Isparta" },

  { id: "kahramanmaras", name: "Kahramanmaraş" },
  { id: "karabuk", name: "Karabük" },
  { id: "karaman", name: "Karaman" },
  { id: "kars", name: "Kars" },
  { id: "kastamonu", name: "Kastamonu" },
  { id: "kayseri", name: "Kayseri" },
  { id: "kirikkale", name: "Kırıkkale" },
  { id: "kirklareli", name: "Kırklareli" },
  { id: "kirsehir", name: "Kırşehir" },
  { id: "kilis", name: "Kilis" },
  { id: "kocaeli", name: "Kocaeli" },
  { id: "konya", name: "Konya" },
  { id: "kutahya", name: "Kütahya" },

  { id: "malatya", name: "Malatya" },
  { id: "manisa", name: "Manisa" },
  { id: "mardin", name: "Mardin" },
  { id: "mersin", name: "Mersin" },
  { id: "mugla", name: "Muğla" },
  { id: "mus", name: "Muş" },

  { id: "nevsehir", name: "Nevşehir" },
  { id: "nigde", name: "Niğde" },

  { id: "ordu", name: "Ordu" },
  { id: "osmaniye", name: "Osmaniye" },

  { id: "rize", name: "Rize" },

  { id: "sakarya", name: "Sakarya" },
  { id: "samsun", name: "Samsun" },
  { id: "sanliurfa", name: "Şanlıurfa" },
  { id: "siirt", name: "Siirt" },
  { id: "sinop", name: "Sinop" },
  { id: "sirnak", name: "Şırnak" },
  { id: "sivas", name: "Sivas" },

  { id: "tekirdag", name: "Tekirdağ" },
  { id: "tokat", name: "Tokat" },
  { id: "trabzon", name: "Trabzon" },
  { id: "tunceli", name: "Tunceli" },

  { id: "usak", name: "Uşak" },

  { id: "van", name: "Van" },

  { id: "yalova", name: "Yalova" },
  { id: "yozgat", name: "Yozgat" },

  { id: "zonguldak", name: "Zonguldak" },
];

const CITY_CONFIG = {
  adana: { distance: [0, 540], days: [1, 3] },
  adiyaman: { distance: [0, 310], days: [1, 4] },
  afyonkarahisar: { distance: [0, 385], days: [1, 4] },
  agri: { distance: [5, 445], days: [1, 2] },
  aksaray: { distance: [0, 285], days: [1, 4] },
  amasya: { distance: [0, 135], days: [1, 3] },
  ankara: { distance: [0, 110], days: [1, 6] },
  antalya: { distance: [0, 690], days: [1, 8] },
  ardahan: { distance: [0, 335], days: [1, 2] },
  artvin: { distance: [30, 410], days: [1, 4] },
  aydin: { distance: [25, 420], days: [1, 3] },
  balikesir: { distance: [0, 585], days: [1, 5] },
  bartin: { distance: [0, 160], days: [1, 4] },
  batman: { distance: [0, 255], days: [1, 2] },
  bayburt: { distance: [0, 280], days: [1, 4] },
  bilecik: { distance: [0, 205], days: [1, 2] },
  bingol: { distance: [0, 160], days: [1, 3] },
  bitlis: { distance: [0, 305], days: [1, 4] },
  bolu: { distance: [0, 385], days: [1, 4] },
  burdur: { distance: [50, 425], days: [1, 2] },
  bursa: { distance: [0, 180], days: [1, 5] },
  canakkale: { distance: [10, 475], days: [1, 6] },
  cankiri: { distance: [5, 330], days: [1, 3] },
  corum: { distance: [25, 470], days: [1, 5] },
  denizli: { distance: [5, 310], days: [1, 3] },
  diyarbakir: { distance: [0, 260], days: [1, 3] },
  duzce: { distance: [30, 195], days: [1, 2] },
  edirne: { distance: [0, 20], days: [1, 2] },
  elazig: { distance: [0, 210], days: [1, 3] },
  erzincan: { distance: [0, 520], days: [1, 3] },
  erzurum: { distance: [0, 400], days: [1, 4] },
  eskisehir: { distance: [0, 420], days: [1, 3] },
  gaziantep: { distance: [0, 320], days: [1, 3] },
  giresun: { distance: [0, 325], days: [1, 4] },
  gumushane: { distance: [35, 385], days: [1, 2] },
  hakkari: { distance: [25, 280], days: [1, 2] },
  hatay: { distance: [0, 255], days: [1, 3] },
  igdir: { distance: [45, 305], days: [1, 1] },
  isparta: { distance: [0, 315], days: [1, 4] },
  istanbul: { distance: [0, 150], days: [1, 8] },
  izmir: { distance: [0, 370], days: [1, 8] },
  kahramanmaras: { distance: [10, 450], days: [1, 4] },
  karabuk: { distance: [0, 130], days: [1, 3] },
  karaman: { distance: [55, 235], days: [1, 1] },
  kars: { distance: [10, 410], days: [1, 4] },
  kastamonu: { distance: [0, 440], days: [1, 3] },
  kayseri: { distance: [0, 420], days: [1, 5] },
  kilis: { distance: [0, 55], days: [1, 2] },
  kirikkale: { distance: [5, 295], days: [1, 3] },
  kirklareli: { distance: [45, 255], days: [1, 2] },
  kirsehir: { distance: [15, 290], days: [1, 3] },
  kocaeli: { distance: [5, 285], days: [1, 2] },
  konya: { distance: [0, 505], days: [1, 7] },
  kutahya: { distance: [0, 320], days: [1, 2] },
  malatya: { distance: [0, 355], days: [1, 4] },
  manisa: { distance: [0, 380], days: [1, 3] },
  mardin: { distance: [0, 195], days: [1, 3] },
  mersin: { distance: [5, 500], days: [1, 5] },
  mugla: { distance: [25, 645], days: [1, 5] },
  mus: { distance: [0, 365], days: [1, 4] },
  nevsehir: { distance: [0, 220], days: [1, 4] },
  nigde: { distance: [0, 310], days: [1, 2] },
  ordu: { distance: [0, 290], days: [1, 4] },
  osmaniye: { distance: [15, 255], days: [1, 3] },
  rize: { distance: [0, 225], days: [1, 4] },
  sakarya: { distance: [25, 210], days: [1, 2] },
  samsun: { distance: [0, 305], days: [1, 4] },
  sanliurfa: { distance: [0, 420], days: [1, 4] },
  siirt: { distance: [0, 140], days: [1, 2] },
  sinop: { distance: [0, 305], days: [1, 4] },
  sirnak: { distance: [0, 225], days: [1, 2] },
  sivas: { distance: [0, 460], days: [1, 3] },
  tekirdag: { distance: [0, 175], days: [1, 2] },
  tokat: { distance: [0, 315], days: [1, 4] },
  trabzon: { distance: [0, 275], days: [1, 3] },
  tunceli: { distance: [0, 310], days: [1, 3] },
  usak: { distance: [0, 175], days: [1, 3] },
  van: { distance: [5, 510], days: [1, 5] },
  yalova: { distance: [5, 125], days: [1, 2] },
  yozgat: { distance: [0, 325], days: [1, 2] },
  zonguldak: { distance: [20, 175], days: [1, 1] },
};

const CATEGORY_TREE = [
  {
    key: "museums",
    label: "Museums",
    sub: null,
  },
  {
    key: "cultural",
    label: "Cultural Heritage",
    sub: [
      { key: "archaeology", label: "Ancient & Archaeology" },
      { key: "architecture", label: "Civil & Traditional Architecture" },
      { key: "fortifications", label: "Fortifications" },
      { key: "infrastructure", label: "Historical Infrastructure" },
      { key: "religious", label: "Religious" },
      { key: "transport", label: "Transportation as Heritage" },
      { key: "monumental", label: "Urban & Monumental Heritage" },
    ],
  },
  {
    key: "nature",
    label: "Nature",
    sub: [
      { key: "parks", label: "Parks & Outdoor" },
      { key: "terrain", label: "Terrain & Landforms" },
      { key: "water", label: "Water & Coastal" },
      { key: "wildlife", label: "Wildlife & Natural Experience" },
    ],
  },
];



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

function RangeRow({ title, value, min, max, step, unitLabel, onChange }) {
  return (
      <div className={styles.rangeRow}>
        <div className={styles.rangeHead}>
          <div className={styles.rangeTitle}>{title}</div>
          <EditablePillNumber
              value={value}
              unitLabel={unitLabel}
              min={min}
              max={max}
              onCommit={onChange}
          />
        </div>

        <input
            className={styles.range}
            type="range"
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => onChange(toInt(e.target.value, value))}
        />

        {/* 🔥 SADE MIN MAX */}
        <div className={styles.minMax}>
          <span>{min}</span>
          <span>{max}</span>
        </div>
      </div>
  );
}

function SearchSelect({ placeholder, items, valueId, onSelect }) {
  const selected = items.find((x) => x.id === valueId) || null;
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");

  const normalize = (str) =>
      str
          .toLowerCase()
          .replace(/ı/g, "i")
          .replace(/ğ/g, "g")
          .replace(/ş/g, "s")
          .replace(/ö/g, "o")
          .replace(/ç/g, "c")
          .replace(/ü/g, "u");

  const filtered = useMemo(() => {
    const s = normalize(q.trim());
    if (!s) return items;

    return items.filter((x) =>
        normalize(x.name).includes(s)
    );
  }, [items, q]);

  return (
    <div className={styles.selectWrap}>
      <div className={styles.selectTop}>
        <span className={styles.searchIcon} aria-hidden="true">⌕</span>
        <input
          className={styles.selectInput}
          placeholder={placeholder}
          value={open ? q : selected?.name ?? ""}
          onFocus={() => { setOpen(true); setQ(""); }}
          onChange={(e) => { setOpen(true); setQ(e.target.value); }}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
        />
        <span className={styles.chev} aria-hidden="true">▾</span>
      </div>

      {open && (
        <div className={styles.dropdown} role="listbox">
          <div className={styles.dropdownInner}>
            {filtered.map((it) => (
              <button
                key={it.id}
                type="button"
                className={styles.option}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => { onSelect(it.id); setOpen(false); }}
              >
                <span className={styles.dot}></span>
                <span>{it.name}</span>
              </button>
            ))}
            {!filtered.length && <div className={styles.empty}>No results</div>}
          </div>
        </div>
      )}
    </div>
  );
}

function InterestPill({ label, checked, onToggle }) {
  return (
    <button
      type="button"
      className={`${styles.interestPill} ${checked ? styles.interestOn : ""}`}
      onClick={onToggle}
      aria-pressed={checked}
    >
      {/* ICON SLOT (sonra icon koyacaksın) */}
      <span className={styles.iconSlot} aria-hidden="true" />
      <span className={styles.interestLabel}>{label}</span>
      <span className={`${styles.miniSwitch} ${checked ? styles.miniSwitchOn : ""}`}>
        <span className={styles.miniKnob} />
      </span>
    </button>
  );
}

export default function Planning() {
  const [distanceRange, setDistanceRange] = useState({
    min: 20,
    max: 2000,
  });

  const [daysRange, setDaysRange] = useState({
    min: 1,
    max: 5,
  });

  const [cities, setCities] = useState(ALL_CITIES);
  const [cityId, setCityId] = useState(ALL_CITIES[0]?.id ?? "");
  const [cityName, setCityName] = useState(ALL_CITIES[0]?.name ?? "");

  const [days, setDays] = useState(3);          // 1–10
  const [distanceKm, setDistanceKm] = useState(100); // 20–2000

  const [selected, setSelected] = useState(() => {
    const all = new Set();

    CATEGORY_TREE.forEach((cat) => {
      if (cat.sub) {
        cat.sub.forEach((s) => all.add(s.key));
      } else {
        all.add(cat.key);
      }
    });

    return all;
  });

  const [isGenerating, setIsGenerating] = useState(false);

  const navigate = useNavigate();
  // Backend gelince burayı fetch ile değiştireceğiz:
  // GET /api/cities
  // GET /api/categories
  useEffect(() => {
    setCities(ALL_CITIES);
  }, []);

  useEffect(() => {
    const config = CITY_CONFIG[cityId] || {
      distance: [20, 2000],
      days: [1, 5],
    };

    const newDistanceRange = {
      min: config.distance[0],
      max: config.distance[1],
    };

    const newDaysRange = {
      min: config.days[0],
      max: config.days[1],
    };

    setDistanceRange(newDistanceRange);
    setDaysRange(newDaysRange);

    // 🔥 RESET (aynı mantık ama cleaner)
    setDistanceKm(newDistanceRange.min);
    setDays(newDaysRange.min);

  }, [cityId]);

  const [expanded, setExpanded] = useState(null);
  const toggleMain = (cat) => {
    setSelected((prev) => {
      const next = new Set(prev);

      if (!cat.sub) {
        if (next.has(cat.key)) next.delete(cat.key);
        else next.add(cat.key);
        return next;
      }

      const allSelected = cat.sub.every((s) => next.has(s.key));

      if (allSelected) {
        cat.sub.forEach((s) => next.delete(s.key));
      } else {
        cat.sub.forEach((s) => next.add(s.key));
      }

      return next;
    });
  };

  const toggleSub = (key) => {
    setSelected((prev) => {
      const next = new Set(prev);

      if (next.has(key)) next.delete(key);
      else next.add(key);

      return next;
    });
  };

  const buildPayload = () => ({
    cityId,
    cityName,
    days,
    distanceKm,
    categories: Array.from(selected),
  });

const onGenerateRoute = async () => {
  setIsGenerating(true);
  try {
    const payload = buildPayload();

    // DEV fake wait
    await new Promise((r) => setTimeout(r, 900));

    navigate("/route", { state: { planningInput: payload } });
  } finally {
    setIsGenerating(false);
  }
};


  return (
    <div className={styles.page}>
      {isGenerating && (
        <div className={styles.blockingOverlay} role="alert" aria-live="polite">
          <div className={styles.loadingCard}>
            <div className={styles.spinner} />
            <div className={styles.loadingText}>Generating route…</div>
          </div>
        </div>
      )}
      <div className={styles.hero}>
        <div className={styles.inlineQuote}>
          <p className={styles.quoteText}>
            “By failing to prepare, you are preparing to fail.”
          </p>
          <p className={styles.quoteAuthor}>
            — Benjamin Franklin
          </p>
        </div>

        {/* City */}
        <div className={styles.block}>
          <div className={styles.rangeTitle}>Select City</div>
          <SearchSelect
              placeholder="Search city..."
              items={cities}
              valueId={cityId}
              onSelect={(id) => {
                setCityId(id);

                const selected = cities.find(c => c.id === id);
                setCityName(selected?.name ?? null);
              }}
          />
        </div>

        {/* Days + Distance */}
        <div className={styles.twoCols}>

          <div className={styles.block}>
            <RangeRow
                title="Days"
                value={days}
                min={daysRange.min}
                max={daysRange.max}
                step={1}
                unitLabel="days"
                onChange={(v) =>
                    setDays(clamp(v, daysRange.min, daysRange.max))
                }
            />
          </div>

          <div className={styles.block}>
            <RangeRow
                title="Distance"
                value={distanceKm}
                min={distanceRange.min}
                max={distanceRange.max}
                step={5}
                unitLabel="km"
                onChange={(v) =>
                    setDistanceKm(clamp(v, distanceRange.min, distanceRange.max))
                }
            />
          </div>

        </div>

        {/* Categories */}
        <div className={styles.block}>
          <div className={styles.sectionTitle}>Interests</div>

          <div className={styles.categoryGrid}>

            {/* ÜST (sub olanlar) */}
            {CATEGORY_TREE.filter((cat) => cat.sub).map((cat) => {
              const isAllSelected = cat.sub.every((s) => selected.has(s.key));

              return (
                  <div key={cat.key} className={styles.categoryBlock}>

                    <label className={styles.mainRow}>
                      <input
                          type="checkbox"
                          checked={isAllSelected}
                          ref={(el) => {
                            if (el) {
                              const someSelected =
                                  cat.sub.some((s) => selected.has(s.key)) && !isAllSelected;

                              el.indeterminate = someSelected;
                            }
                          }}
                          onChange={() => toggleMain(cat)}
                      />
                      <span>{cat.label}</span>
                    </label>

                    <div className={styles.subList}>
                      {cat.sub.map((s) => (
                          <label key={s.key} className={styles.subRow}>
                            <input
                                type="checkbox"
                                checked={selected.has(s.key)}
                                onChange={() => toggleSub(s.key)}
                            />
                            <span>{s.label}</span>
                          </label>
                      ))}
                    </div>
                  </div>
              );
            })}

            {/* ALT (sub olmayan → Museums) */}
            {CATEGORY_TREE.filter((cat) => !cat.sub).map((cat) => {
              const isSelected = selected.has(cat.key);

              return (
                  <div key={cat.key} className={styles.fullWidth}>
                    <div className={styles.categoryBlock}>

                      <label className={styles.mainRow}>
                        <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleMain(cat)}
                        />
                        <span>{cat.label}</span>
                      </label>

                    </div>
                  </div>
              );
            })}

          </div>
        </div>

        <div className={styles.cta}>
          <Button
            variant="primary"
            onClick={onGenerateRoute}
            disabled={isGenerating}
          >
            Generate Route
          </Button>
        </div>
      </div>
    </div>
  );
}