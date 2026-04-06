import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://wutikckdmhfyqnyjgqzw.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind1dGlrY2tkbWhmeXFueWpncXp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQyMDQ4NTIsImV4cCI6MjA4OTc4MDg1Mn0.YqDQ9xtsy__nlvhj5y33NxRNO3WIIUvel7GXghf02TQ';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// ── City ID → Supabase DB name mapping ──────────────────────────────────────
const CITY_ID_TO_DB_NAME = {
  istanbul: 'Istanbul', ankara: 'Ankara', izmir: 'Izmir',
  adana: 'Adana', adiyaman: 'Adiyaman', afyon: 'Afyonkarahisar',
  agri: 'Agri', aksaray: 'Aksaray', amasya: 'Amasya',
  antalya: 'Antalya', ardahan: 'Ardahan', artvin: 'Artvin',
  aydin: 'Aydin', balikesir: 'Balikesir', bartin: 'Bartin',
  batman: 'Batman', bayburt: 'Bayburt', bilecik: 'Bilecik',
  bingol: 'Bingol', bitlis: 'Bitlis', bolu: 'Bolu',
  burdur: 'Burdur', bursa: 'Bursa', canakkale: 'Canakkale',
  cankiri: 'Cankiri', corum: 'Corum', denizli: 'Denizli',
  diyarbakir: 'Diyarbakir', duzce: 'Duzce', edirne: 'Edirne',
  elazig: 'Elazig', erzincan: 'Erzincan', erzurum: 'Erzurum',
  eskisehir: 'Eskisehir', gaziantep: 'Gaziantep', giresun: 'Giresun',
  gumushane: 'Gumushane', hakkari: 'Hakkari', hatay: 'Hatay',
  igdir: 'Igdir', isparta: 'Isparta', kahramanmaras: 'Kahramanmaras',
  karabuk: 'Karabuk', karaman: 'Karaman', kars: 'Kars',
  kastamonu: 'Kastamonu', kayseri: 'Kayseri', kirikkale: 'Kirikkale',
  kirklareli: 'Kirklareli', kirsehir: 'Kirsehir', kilis: 'Kilis',
  kocaeli: 'Kocaeli', konya: 'Konya', kutahya: 'Kutahya',
  malatya: 'Malatya', manisa: 'Manisa', mardin: 'Mardin',
  mersin: 'Mersin', mugla: 'Mugla', mus: 'Mus',
  nevsehir: 'Nevsehir', nigde: 'Nigde', ordu: 'Ordu',
  osmaniye: 'Osmaniye', rize: 'Rize', sakarya: 'Sakarya',
  samsun: 'Samsun', sanliurfa: 'Sanliurfa', siirt: 'Siirt',
  sinop: 'Sinop', sirnak: 'Sirnak', sivas: 'Sivas',
  tekirdag: 'Tekirdag', tokat: 'Tokat', trabzon: 'Trabzon',
  tunceli: 'Tunceli', usak: 'Usak', van: 'Van',
  yalova: 'Yalova', yozgat: 'Yozgat', zonguldak: 'Zonguldak',
};

// ── Cities ───────────────────────────────────────────────────────────────────

export async function fetchCityCategories(cityId) {
  const dbName = CITY_ID_TO_DB_NAME[cityId];
  if (!dbName) return null;

  const { data, error } = await supabase
    .from('cities')
    .select('categories, max_days, min_distance_km, max_distance_km')
    .eq('name', dbName)
    .maybeSingle();

  if (error || !data) return null;

  return {
    categories: data.categories ?? [],
    maxDays: data.max_days ?? 5,
    minDistanceKm: data.min_distance_km ?? 0,
    maxDistanceKm: data.max_distance_km ?? 500,
  };
}

// ── POI Media ────────────────────────────────────────────────────────────────

/**
 * Bir POI'ye ait tüm resimleri çeker (sort_order'a göre sıralı).
 * @param {string|number} poiId
 * @returns {Promise<string[]>} S3 URL listesi
 */
export async function fetchPoiImages(poiId) {
  const { data, error } = await supabase
    .from('media_assets')
    .select('url_or_path, sort_order')
    .eq('poi_id', Number(poiId))
    .eq('media_type', 'image')
    .order('sort_order', { ascending: true });

  if (error || !data) return [];
  return data.map((r) => r.url_or_path);
}

/**
 * Bir POI'ye ait belirli dildeki audio URL'sini çeker.
 * @param {string|number} poiId
 * @param {'TR'|'EN'|'DE'} language
 * @returns {Promise<string|null>} S3 URL veya null
 */
export async function fetchPoiAudio(poiId, language) {
  const { data, error } = await supabase
    .from('media_assets')
    .select('url_or_path')
    .eq('poi_id', Number(poiId))
    .eq('media_type', 'audio')
    .eq('language', language.toUpperCase())
    .maybeSingle();

  if (error || !data) return null;
  return data.url_or_path;
}

/**
 * Bir POI'ye ait belirli dildeki açıklama metnini çeker.
 * @param {string|number} poiId
 * @param {'TR'|'EN'|'DE'} language
 * @returns {Promise<string|null>}
 */
export async function fetchPoiDescription(poiId, language) {
  const { data, error } = await supabase
    .from('poi_contents')
    .select('description_text')
    .eq('poi_id', Number(poiId))
    .eq('language', language.toUpperCase())
    .maybeSingle();

  if (error || !data) return null;
  return data.description_text;
}

/**
 * Bir POI için tüm içeriği tek seferde çeker: resimler, açıklama, audio.
 * @param {string|number} poiId
 * @param {'TR'|'EN'|'DE'} language
 */
export async function fetchPoiContent(poiId, language = 'EN') {
  const [images, description, audioUrl] = await Promise.all([
    fetchPoiImages(poiId),
    fetchPoiDescription(poiId, language),
    fetchPoiAudio(poiId, language),
  ]);

  return { images, description, audioUrl };
}