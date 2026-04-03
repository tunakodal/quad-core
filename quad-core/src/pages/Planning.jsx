import { useEffect, useMemo, useState } from "react";
import styles from "../styles/Planning.module.css";
import { Button } from "../ui/Button";
import { useNavigate } from "react-router-dom";

const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
const toInt = (v, fallback) => {
  const n = parseInt(String(v ?? "").replace(/[^\d]/g, ""), 10);
  return Number.isFinite(n) ? n : fallback;
};

const FALLBACK_CITIES = [
  { id: "istanbul", name: "İstanbul" },
  { id: "ankara", name: "Ankara" },
  { id: "izmir", name: "İzmir" },
];

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
              <span className={styles.dot}></span>
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
  const [distanceRange, setDistanceRange] = useState({
    min: 20,
    max: 2000,
  });

  const [daysRange, setDaysRange] = useState({
    min: 1,
    max: 5,
  });

  const [cities, setCities] = useState(FALLBACK_CITIES);
  const [cityId, setCityId] = useState(FALLBACK_CITIES[0]?.id ?? "");

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
    setCities(FALLBACK_CITIES);
  }, []);

  useEffect(() => {
    let newDistanceRange;
    let newDaysRange;

    if (cityId === "istanbul") {
      newDistanceRange = { min: 20, max: 500 };
      newDaysRange = { min: 1, max: 3 };
    } else if (cityId === "ankara") {
      newDistanceRange = { min: 30, max: 800 };
      newDaysRange = { min: 1, max: 4 };
    } else if (cityId === "izmir") {
      newDistanceRange = { min: 25, max: 600 };
      newDaysRange = { min: 1, max: 3 };
    } else {
      newDistanceRange = { min: 20, max: 2000 };
      newDaysRange = { min: 1, max: 5 };
    }

    setDistanceRange(newDistanceRange);
    setDaysRange(newDaysRange);

    // 🔥 RESET
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
              onSelect={setCityId}
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