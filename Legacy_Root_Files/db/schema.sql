-- =============================================================
--  GUIDE Database Schema
--  PostgreSQL 15+
--
--  Tablolar:
--    1. pois            → Turistik nokta metadata
--    2. poi_contents    → Dil bazlı açıklama metinleri
--    3. media_assets    → Görsel ve ses asset referansları
--
--  NOT: Tüm tablo yapıları app/models/domain.py ve
--       app/repositories/repositories.py ile birebir hizalıdır.
-- =============================================================


-- -------------------------------------------------------------
--  Enum Types
-- -------------------------------------------------------------

CREATE TYPE language_code AS ENUM ('TR', 'EN', 'DE');
CREATE TYPE media_type    AS ENUM ('image', 'audio');


-- -------------------------------------------------------------
--  1. pois
--     Karşılık: domain.Poi
--     Kaynak:   repositories.PoiRepository / JsonDataSource
-- -------------------------------------------------------------

CREATE TABLE pois (
    id                       TEXT        PRIMARY KEY,
    name                     TEXT        NOT NULL,
    category                 TEXT        NOT NULL,
    city                     TEXT        NOT NULL,
    latitude                 DOUBLE PRECISION NOT NULL
                                         CHECK (latitude  BETWEEN -90  AND  90),
    longitude                DOUBLE PRECISION NOT NULL
                                         CHECK (longitude BETWEEN -180 AND 180),
    estimated_visit_duration INTEGER     NOT NULL CHECK (estimated_visit_duration > 0)  -- dakika
);

-- Şehir + kategori bazlı arama için index (PoiRepository.find_by_city_and_categories)
CREATE INDEX idx_pois_city          ON pois (city);
CREATE INDEX idx_pois_city_category ON pois (city, category);


-- -------------------------------------------------------------
--  2. poi_contents
--     Karşılık: domain.PoiContent
--     Kaynak:   repositories.ContentRepository
-- -------------------------------------------------------------

CREATE TABLE poi_contents (
    id               SERIAL        PRIMARY KEY,
    poi_id           TEXT          NOT NULL REFERENCES pois(id) ON DELETE CASCADE,
    language         language_code NOT NULL,
    description_text TEXT          NOT NULL DEFAULT '',

    UNIQUE (poi_id, language)   -- her POI için dil başına tek içerik
);

CREATE INDEX idx_poi_contents_poi_lang ON poi_contents (poi_id, language);


-- -------------------------------------------------------------
--  3. media_assets
--     Karşılık: domain.MediaAsset
--     Kaynak:   repositories.MediaRepository / AudioAssetResolver
--
--     language sütunu:
--       - Görseller (image) için NULL
--       - Ses dosyaları (audio) için TR / EN / DE
-- -------------------------------------------------------------

CREATE TABLE media_assets (
    asset_id     TEXT        PRIMARY KEY,
    poi_id       TEXT        NOT NULL REFERENCES pois(id) ON DELETE CASCADE,
    url_or_path  TEXT        NOT NULL,
    media_type   media_type  NOT NULL,
    language     language_code NULL,      -- sadece audio için dolu
    sort_order   INTEGER     NOT NULL DEFAULT 1,

    -- Bir POI'nin aynı dildeki ses dosyası tekil olmalı
    UNIQUE (poi_id, media_type, language)
);

CREATE INDEX idx_media_assets_poi        ON media_assets (poi_id);
CREATE INDEX idx_media_assets_poi_type   ON media_assets (poi_id, media_type);
CREATE INDEX idx_media_assets_poi_audio  ON media_assets (poi_id, media_type, language)
    WHERE media_type = 'audio';


-- =============================================================
--  Örnek Seed Verisi  (mevcut data/pois.json ile aynı)
--  Tuna bu bloğu DB'ye import etmek ya da Alembic seed ile
--  doldurmak için referans olarak kullanabilir.
-- =============================================================

INSERT INTO pois VALUES
    ('istanbul-hagia-sophia',    'Hagia Sophia',     'Historical', 'Istanbul',  41.0086,  28.9802, 90),
    ('istanbul-blue-mosque',     'Blue Mosque',      'Historical', 'Istanbul',  41.0054,  28.9768, 60),
    ('istanbul-topkapi',         'Topkapi Palace',   'Historical', 'Istanbul',  41.0115,  28.9834, 120),
    ('istanbul-grand-bazaar',    'Grand Bazaar',     'Shopping',   'Istanbul',  41.0107,  28.9680, 90),
    ('istanbul-basilica-cistern','Basilica Cistern', 'Historical', 'Istanbul',  41.0084,  28.9779, 45),
    ('istanbul-galata-tower',    'Galata Tower',     'Historical', 'Istanbul',  41.0256,  28.9744, 60),
    ('istanbul-bosphorus-cruise','Bosphorus Cruise', 'Nature',     'Istanbul',  41.0082,  28.9784, 120),
    ('istanbul-spice-bazaar',    'Spice Bazaar',     'Shopping',   'Istanbul',  41.0165,  28.9703, 45),
    ('ankara-ataturk-mausoleum', 'Atatürk Mausoleum','Historical', 'Ankara',    39.9258,  32.8371, 90),
    ('ankara-ankara-castle',     'Ankara Castle',    'Historical', 'Ankara',    39.9407,  32.8637, 60),
    ('ankara-museum-anatolian',  'Museum of Anatolian Civilizations','Museum','Ankara',39.9402,32.8638,120),
    ('ankara-atakule',           'Atakule Tower',    'Landmark',   'Ankara',    39.8802,  32.8541, 30),
    ('izmir-clock-tower',        'Konak Clock Tower','Landmark',   'Izmir',     38.4192,  27.1287, 30),
    ('izmir-agora',              'Agora of Smyrna',  'Historical', 'Izmir',     38.4196,  27.1416, 60),
    ('izmir-kadifekale',         'Kadifekale',       'Historical', 'Izmir',     38.4068,  27.1483, 45),
    ('izmir-kemeralti',          'Kemeraltı Bazaar', 'Shopping',   'Izmir',     38.4189,  27.1354, 90);
