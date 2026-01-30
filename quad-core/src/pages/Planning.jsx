import { useEffect, useMemo, useState } from "react";
import styles from "./Planning.module.css";
import { Button } from "../ui/Button";
import { useNavigate } from "react-router-dom";

const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
const toInt = (v, fallback) => {
  const n = parseInt(String(v ?? "").replace(/[^\d]/g, ""), 10);
  return Number.isFinite(n) ? n : fallback;
};

// Fallback (backend gelene kadar)
const FALLBACK_CITIES = [
  { id: "istanbul", name: "Istanbul" },
  { id: "ankara", name: "Ankara" },
  { id: "izmir", name: "Izmir" },
];

// 12 kategori placeholder (backend’den gelecek)
const FALLBACK_CATEGORIES = [
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

function RangeRow({ title, value, min, max, step, unitLabel, onChange, tickLabels, tickClassName, tickBiasPx}) {
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
        aria-label={title}
      />

      {tickLabels?.length ? (
  <div className={`${styles.ticks} ${tickClassName ?? ""}`}>
    {tickLabels.map((t) => {
      const val = Number(t);
      const pct = ((val - min) / (max - min)) * 100;


      const bias = (pct - 50) / 50; // -1 .. +1
      const px = (tickBiasPx ?? 0) * bias; // sola/sağa

      return (
        <span
          key={t}
          className={styles.tick}
          style={{ left: `${pct}%`, transform: `translateX(calc(-50% + ${px}px))` }}
        >
          {t}
        </span>
      );
    })}
  </div>
) : null}
    </div>
  );
}

function SearchSelect({ placeholder, items, valueId, onSelect }) {
  const selected = items.find((x) => x.id === valueId) || null;
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return items;
    return items.filter((x) => x.name.toLowerCase().includes(s));
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
          {filtered.map((it) => (
            <button
              key={it.id}
              type="button"
              className={styles.option}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => { onSelect(it.id); setOpen(false); }}
            >
              <span className={styles.optionPin} aria-hidden="true">📍</span>
              <span>{it.name}</span>
            </button>
          ))}
          {!filtered.length && <div className={styles.empty}>No results</div>}
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
  const [cities, setCities] = useState(FALLBACK_CITIES);
  const [categories, setCategories] = useState(FALLBACK_CATEGORIES);

  const [cityId, setCityId] = useState(FALLBACK_CITIES[0]?.id ?? "");

  const [days, setDays] = useState(3);          // 1–10
  const [distanceKm, setDistanceKm] = useState(100); // 20–2000

  const [selected, setSelected] = useState(() => new Set(["landmarks", "museums"]));

  const [isGenerating, setIsGenerating] = useState(false);

  const navigate = useNavigate();
  // Backend gelince burayı fetch ile değiştireceğiz:
  // GET /api/cities
  // GET /api/categories
  useEffect(() => {
    setCities(FALLBACK_CITIES);
    setCategories(FALLBACK_CATEGORIES);
  }, []);

  const toggleCategory = (key) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const buildPayload = () => ({
    cityId,
    days,
    distanceKm,
    categories: Array.from(selected),
  });

const onGenerateRoute = async () => {
  setIsGenerating(true);
  try {
    const payload = buildPayload(); // ✅ senin mevcut fonksiyonun

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
              onSelect={setCityId}
          />
        </div>

        {/* Days + Distance */}
        <div className={styles.block}>
          <div className={styles.twoCols}>
            <RangeRow
                title="Days"
                value={days}
                min={1}
                max={10}
                step={1}
                unitLabel="days"
                onChange={(v) => setDays(clamp(v, 1, 10))}
                tickLabels={["1", "3", "5", "7", "10"]}
            />
           <RangeRow
              title="Distance"
              value={distanceKm}
              min={20}
              max={2000}
              step={10}
              unitLabel="km"
              onChange={(v) => setDistanceKm(clamp(v, 20, 2000))}
              tickLabels={[20, 500, 1000, 1500, 2000]}
              tickClassName={styles.distanceTicks}
              tickBiasPx={-15}
            />
          </div>
        </div>

        {/* Categories */}
        <div className={styles.block}>
          <div className={styles.sectionTitle}>Interests</div>
          <div className={styles.grid}>
            {categories.map((c) => (
                <InterestPill
                    key={c.key}
                    label={c.label}
                    checked={selected.has(c.key)}
                    onToggle={() => toggleCategory(c.key)}
                />
            ))}
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