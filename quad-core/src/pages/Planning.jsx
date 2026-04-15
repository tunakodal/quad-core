import { useEffect, useMemo, useState } from "react";
import styles from "../styles/Planning.module.css";
import { Button } from "../ui/Button";
import { useNavigate } from "react-router-dom";
import { fetchCityCategories } from "../api/supabaseClient";

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

const CATEGORY_TREE = [
  {
    key: "Museum",
    label: "Museums",
    sub: null,
  },
  {
    key: "Cultural Heritage",
    label: "Cultural Heritage",
    sub: [
      { key: "Ancient & Archaeology", label: "Ancient & Archaeology" },
      { key: "Civil & Traditional Architecture", label: "Civil & Traditional Architecture" },
      { key: "Fortifications", label: "Fortifications" },
      { key: "Historical Infrastructure", label: "Historical Infrastructure" },
      { key: "Religious", label: "Religious" },
      { key: "Transportation as Heritage", label: "Transportation as Heritage" },
      { key: "Urban & Monumental Heritage", label: "Urban & Monumental Heritage" },
    ],
  },
  {
    key: "Nature",
    label: "Nature",
    sub: [
      { key: "Parks & Outdoor", label: "Parks & Outdoor" },
      { key: "Terrain & Landforms", label: "Terrain & Landforms" },
      { key: "Water & Coastal", label: "Water & Coastal" },
      { key: "Wildlife & Natural Experience", label: "Wildlife & Natural Experience" },
    ],
  },
];

function EditablePillNumber({ value, unitLabel, min, max, onCommit, disabled }) {
  const [draft, setDraft] = useState(String(value));

  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  return (
    <div className={styles.valuePill}>
      <input
        className={styles.pillInput}
        disabled={disabled}
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
      />
      <span className={styles.pillUnit}>{unitLabel}</span>
    </div>
  );
}

function RangeRow({ title, value, min, max, step, unitLabel, onChange, disabled }) {
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
          disabled={disabled}
        />
      </div>

      <input
        className={styles.range}
        type="range"
        disabled={disabled}
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(toInt(e.target.value, value))}
      />

      <div className={styles.minMax}>
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

function SearchSelect({ placeholder, items, valueId, onSelect }) {
  const selected = items?.find((x) => x.id === valueId) || null;
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");

  const normalize = (str) =>
    str
      .replace(/İ/g, "i")  // U+0130 does not convert correctly with toLowerCase()
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
    return items.filter((x) => normalize(x.name).includes(s));
  }, [items, q]);

  return (
    <div className={styles.selectWrap}>
      <div className={styles.selectTop}>
        <span className={styles.searchIcon} aria-hidden="true">
          ⌕
        </span>
        <input
          className={styles.selectInput}
          placeholder={placeholder}
          value={open ? q : selected?.name ?? ""}
          onFocus={() => {
            setOpen(true);
            setQ("");
          }}
          onChange={(e) => {
            setOpen(true);
            setQ(e.target.value);
          }}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
        />
        <span className={styles.chev} aria-hidden="true">
          ▾
        </span>
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
                onClick={() => {
                  onSelect(it.id);
                  setOpen(false);
                }}
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

export default function Planning() {
  const [cityId, setCityId] = useState("");
  const [cityName, setCityName] = useState("");

  const [daysRange, setDaysRange] = useState({ min: 0, max: 0 });
  const [distanceRange, setDistanceRange] = useState({ min: 0, max: 0 });

  const [days, setDays] = useState(0);
  const [distanceKm, setDistanceKm] = useState(0);

  const [selected, setSelected] = useState(new Set());
  const [availableKeys, setAvailableKeys] = useState(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const navigate = useNavigate();

  const [suggestion, setSuggestion] = useState(null);
  const [showSuggestionModal, setShowSuggestionModal] = useState(false);
  const [pendingPayload, setPendingPayload] = useState(null);

  const [cities] = useState(ALL_CITIES);

  useEffect(() => {
    if (!cityId) {
      setAvailableKeys(null);
      setSelected(new Set());
      setDaysRange({ min: 0, max: 0 });
      setDistanceRange({ min: 0, max: 0 });
      setDays(0);
      setDistanceKm(0);
      return;
    }

    fetchCityCategories(cityId).then((result) => {
      if (!result || !result.categories || result.categories.length === 0) {
        setAvailableKeys(null);
        setSelected(new Set());
        setDaysRange({ min: 0, max: 0 });
        setDays(0);
        setDistanceRange({ min: 0, max: 0 });
        setDistanceKm(0);
        return;
      }

      const frontendKeys = new Set(result.categories);

      setAvailableKeys(frontendKeys.size > 0 ? frontendKeys : null);
      setSelected(new Set(frontendKeys));

      const maxDays = result.maxDays ?? 5;
      setDaysRange({ min: 1, max: maxDays });
      setDays(1);

      const minDist = Math.floor(result.minDistanceKm ?? 0);
      const maxDist = Math.ceil(result.maxDistanceKm ?? 500);
      setDistanceRange({ min: minDist, max: maxDist });
      setDistanceKm(minDist);
    });
  }, [cityId]);

  const toggleMain = (cat) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (!cat.sub) {
        if (next.has(cat.key)) next.delete(cat.key);
        else next.add(cat.key);
        return next;
      }
      const visibleSubs = cat.sub.filter((s) => !availableKeys || availableKeys.has(s.key));
      const allSelected = visibleSubs.every((s) => next.has(s.key));
      if (allSelected) {
        visibleSubs.forEach((s) => next.delete(s.key));
      } else {
        visibleSubs.forEach((s) => next.add(s.key));
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

  const fetchSuggestion = async (payload) => {
    const res = await fetch("/api/v1/routes/suggest-days", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        city: payload.cityId,
        categories: payload.categories,
      }),
    });

    if (!res.ok) throw new Error("Suggestion failed");

    return res.json();
  };

  const onGenerateRoute = async () => {
    setIsGenerating(true);
    setErrorMsg(null);

    try {
      const payload = buildPayload();

      const suggestionRes = await fetchSuggestion(payload);

      if (suggestionRes.poi_count === 0) {
        setErrorMsg("No POIs found for selected categories");
        return;
      }

      if (payload.days > suggestionRes.max_recommended_days) {
        setSuggestion(suggestionRes);
        setPendingPayload(payload);
        setShowSuggestionModal(true);
        return;
      }

      await generateRoute(payload);
    } catch (err) {
      setErrorMsg(err.message || "Something went wrong");
    } finally {
      setIsGenerating(false);
    }
  };

  const generateRoute = async (payload) => {
    const distanceMeters = Math.max(payload.distanceKm * 1000, 1000);

    const requestBody = {
      preferences: {
        city: payload.cityId,
        trip_days: payload.days,
        categories: payload.categories,
        max_distance_per_day: distanceMeters,
      },
      constraints: {
        max_trip_days: payload.days,
        max_pois_per_day: 9,
        max_daily_distance: distanceMeters,
      },
      language: "EN",
    };

    const response = await fetch("/api/v1/routes/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(errText || "Generate failed");
    }

    const data = await response.json();

    navigate("/route", {
      state: {
        planningInput: payload,
        routeResponse: data,
      },
    });
  };

  const visibleCategoryTree = useMemo(() => {
    if (!availableKeys) return CATEGORY_TREE;

    return CATEGORY_TREE
      .map((cat) => {
        if (!cat.sub) {
          return availableKeys.has(cat.key) ? cat : null;
        }
        const visibleSubs = cat.sub.filter((s) => availableKeys.has(s.key));
        if (visibleSubs.length === 0) return null;
        return { ...cat, sub: visibleSubs };
      })
      .filter(Boolean);
  }, [availableKeys]);

  return (
    <div className={styles.page}>
      {showSuggestionModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalCard}>
            <h3 className={styles.modalTitle}>Maximum Trip Duration Reached</h3>

            <p className={styles.modalText}>
              Based on your selected categories, the maximum feasible trip duration is{" "}
              <strong>{suggestion.max_recommended_days} days</strong>.
            </p>

            <p className={styles.modalSubText}>
              Your current selection exceeds the available POIs. You can continue with the
              suggested duration or modify your preferences.
            </p>

            <div className={styles.modalActions}>
              <button
                className={styles.primaryBtn}
                onClick={async () => {
                  try {
                    setIsGenerating(true);

                    const newPayload = {
                      ...pendingPayload,
                      days: suggestion.max_recommended_days,
                    };

                    setShowSuggestionModal(false);

                    await generateRoute(newPayload);
                  } catch (err) {
                    console.error(err);
                    setErrorMsg(err.message);
                  } finally {
                    setIsGenerating(false);
                  }
                }}
              >
                Continue
              </button>

              <button
                className={styles.secondaryBtn}
                onClick={() => setShowSuggestionModal(false)}
              >
                Modify Selection
              </button>
            </div>
          </div>
        </div>
      )}

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
            "By failing to prepare, you are preparing to fail."
          </p>
          <p className={styles.quoteAuthor}>— Benjamin Franklin</p>
        </div>

        <div className={styles.block}>
          <div className={styles.rangeTitle}>Select City</div>
          <SearchSelect
            placeholder="Search city..."
            items={cities}
            valueId={cityId}
            onSelect={(id) => {
              setCityId(id);
              const sel = cities.find((c) => c.id === id);
              setCityName(sel?.name ?? "");
            }}
          />
        </div>

        <div className={`${styles.hero} ${!cityId ? styles.disabledSection : ""}`}>
          <div className={styles.twoCols}>
            <div className={styles.block}>
              <RangeRow
                title="Days"
                value={days}
                min={daysRange.min}
                max={daysRange.max}
                step={1}
                unitLabel="days"
                onChange={(v) => setDays(clamp(v, daysRange.min, daysRange.max))}
                disabled={!cityId}
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
                onChange={(v) => setDistanceKm(clamp(v, distanceRange.min, distanceRange.max))}
                disabled={!cityId}
              />
            </div>
          </div>

          <div className={styles.block}>
            <div className={styles.sectionTitle}>Interests</div>

            <div className={styles.categoryGrid}>
              {visibleCategoryTree.filter((cat) => cat.sub).map((cat) => {
                const visibleSubs = cat.sub;
                const isAllSelected = visibleSubs.every((s) => selected.has(s.key));

                return (
                  <div key={cat.key} className={styles.categoryBlock}>
                    <label
                      className={`${styles.mainChip} ${
                        isAllSelected ? styles.mainChipActive : ""
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isAllSelected}
                        ref={(el) => {
                          if (el) {
                            const someSelected =
                              visibleSubs.some((s) => selected.has(s.key)) && !isAllSelected;
                            el.indeterminate = someSelected;
                          }
                        }}
                        onChange={() => toggleMain(cat)}
                      />
                      <span>{cat.label}</span>
                    </label>

                    <div className={styles.subList}>
                      {visibleSubs.map((s) => (
                        <label
                          key={s.key}
                          className={`${styles.subChip} ${
                            selected.has(s.key) ? styles.subChipActive : ""
                          }`}
                        >
                          <input
                            type="checkbox"
                            disabled={!cityId}
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

              {visibleCategoryTree.filter((cat) => !cat.sub).map((cat) => (
                <div key={cat.key} className={styles.fullWidth}>
                  <div className={styles.categoryBlock}>
                    <label
                      className={`${styles.mainChip} ${
                        selected.has(cat.key) ? styles.mainChipActive : ""
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selected.has(cat.key)}
                        onChange={() => toggleMain(cat)}
                      />
                      <span>{cat.label}</span>
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.cta}>
            <Button
              variant="primary"
              onClick={onGenerateRoute}
              disabled={isGenerating || !cityId}
            >
              Generate Route
            </Button>
          </div>
        </div>

        {errorMsg && <div className={styles.errorBanner}>⚠️ {errorMsg}</div>}
      </div>
    </div>
  );
}                                                                                   