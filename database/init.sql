-- Inicjalizacja FINALNEJ ARCHITEKTURY HURTOWNI (KONSTELACJA / GALAXY SCHEMA)
-- Projekt na ocenę bardzo dobrą (bdb)

CREATE SCHEMA IF NOT EXISTS fitness_dw;
SET search_path TO fitness_dw, public;

-- ==========================================
-- 1. TABELE WYMIARÓW (DIMENSIONS)
-- ==========================================

-- Tabela wymiaru Adresy
CREATE TABLE IF NOT EXISTS fitness_dw.adresy (
    id SERIAL PRIMARY KEY,
    miasto VARCHAR(50) NOT NULL,
    kod_pocztowy VARCHAR(10) NOT NULL,
    ulica VARCHAR(100) NOT NULL,
    numer_domu VARCHAR(20) NOT NULL
);

-- Tabela wymiaru Daty (Wymiar współdzielony)
CREATE TABLE IF NOT EXISTS fitness_dw.daty (
    id SERIAL PRIMARY KEY,
    dzien INTEGER NOT NULL,
    miesiac INTEGER NOT NULL,
    rok INTEGER NOT NULL,
    data_pelna DATE NOT NULL,
    dzien_tygodnia VARCHAR(20) NOT NULL,
    kwartal INTEGER NOT NULL,
    UNIQUE(data_pelna)
);

-- Tabela wymiaru Sale (Wymiar współdzielony)
CREATE TABLE IF NOT EXISTS fitness_dw.sale (
    id SERIAL PRIMARY KEY,
    numer_sali VARCHAR(20) NOT NULL,
    pojemnosc INTEGER NOT NULL
);

-- Tabela wymiaru Zajecia
CREATE TABLE IF NOT EXISTS fitness_dw.zajecia (
    id SERIAL PRIMARY KEY,
    nazwa_zajec VARCHAR(100) NOT NULL,
    poziom_trudnosci VARCHAR(20) NOT NULL CHECK (poziom_trudnosci IN ('Początkujący', 'Średniozaawansowany', 'Zaawansowany'))
);

-- Tabela wymiaru Specjalizacje (Snowflake normalization)
CREATE TABLE IF NOT EXISTS fitness_dw.specjalizacje (
    id SERIAL PRIMARY KEY,
    nazwa VARCHAR(100) NOT NULL UNIQUE
);

-- Tabela wymiaru Klienci (Wymiar współdzielony)
CREATE TABLE IF NOT EXISTS fitness_dw.klienci (
    id SERIAL PRIMARY KEY,
    imie VARCHAR(50) NOT NULL,
    nazwisko VARCHAR(50) NOT NULL,
    plec VARCHAR(10) NOT NULL CHECK (plec IN ('M', 'K')),
    adres_id INTEGER REFERENCES fitness_dw.adresy(id),
    data_urodzenia DATE NOT NULL
);

-- Tabela wymiaru Trenerzy
CREATE TABLE IF NOT EXISTS fitness_dw.trenerzy (
    id SERIAL PRIMARY KEY,
    imie VARCHAR(50) NOT NULL,
    nazwisko VARCHAR(50) NOT NULL,
    adres_id INTEGER REFERENCES fitness_dw.adresy(id),
    specjalizacja_id INTEGER REFERENCES fitness_dw.specjalizacje(id)
);

-- ==========================================
-- 2. TABELE FAKTÓW (FACT TABLES) -> KONSTELACJA
-- ==========================================

-- FAKT 1: Wejscia (Frekwencja fizyczna)
CREATE TABLE IF NOT EXISTS fitness_dw.wejscia (
    id SERIAL PRIMARY KEY,
    klient_id INTEGER NOT NULL REFERENCES fitness_dw.klienci(id),
    data_id INTEGER NOT NULL REFERENCES fitness_dw.daty(id),
    sala_id INTEGER NOT NULL REFERENCES fitness_dw.sale(id),
    czas_pobytu_min INTEGER NOT NULL CHECK (czas_pobytu_min > 0),
    data_wejscia TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- FAKT 2: Uczestnictwo_zajec (Analiza sesji)
CREATE TABLE IF NOT EXISTS fitness_dw.uczestnictwo_zajec (
    id SERIAL PRIMARY KEY,
    data_id INTEGER NOT NULL REFERENCES fitness_dw.daty(id),
    klient_id INTEGER NOT NULL REFERENCES fitness_dw.klienci(id),
    trener_id INTEGER NOT NULL REFERENCES fitness_dw.trenerzy(id),
    zajecie_id INTEGER NOT NULL REFERENCES fitness_dw.zajecia(id),
    sala_id INTEGER NOT NULL REFERENCES fitness_dw.sale(id),
    ocena_zajec DECIMAL(3,2) CHECK (ocena_zajec BETWEEN 1.0 AND 5.0),
    czas_trwania INTEGER NOT NULL CHECK (czas_trwania > 0),
    liczba_uczestnikow INTEGER NOT NULL CHECK (liczba_uczestnikow > 0),
    data_zajec TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- FAKT 3: Platnosci (Analiza finansowa - Nowy fakt)
CREATE TABLE IF NOT EXISTS fitness_dw.platnosci (
    id SERIAL PRIMARY KEY,
    klient_id INTEGER NOT NULL REFERENCES fitness_dw.klienci(id),
    data_id INTEGER NOT NULL REFERENCES fitness_dw.daty(id),
    kwota DECIMAL(10,2) NOT NULL CHECK (kwota > 0),
    metoda_platnosci VARCHAR(20) NOT NULL CHECK (metoda_platnosci IN ('Karta', 'Gotówka', 'Przelew'))
);

-- ==========================================
-- 3. WIDOKI ANALITYCZNE
-- ==========================================

-- Widok efektywności trenerów (Snowflake join)
CREATE OR REPLACE VIEW fitness_dw.v_efektywnosc_trenerow AS
SELECT 
    t.imie || ' ' || t.nazwisko AS trener,
    sp.nazwa AS specjalizacja,
    COUNT(uz.id) AS liczba_prowadzonych_zajec, 
    AVG(uz.ocena_zajec) AS srednia_ocena,
    SUM(uz.liczba_uczestnikow) AS calkowita_liczba_uczestnikow
FROM fitness_dw.trenerzy t
JOIN fitness_dw.specjalizacje sp ON t.specjalizacja_id = sp.id
JOIN fitness_dw.uczestnictwo_zajec uz ON t.id = uz.trener_id
GROUP BY t.id, t.imie, t.nazwisko, sp.nazwa;

-- Widok analizy finansowej (Nowy fakt)
CREATE OR REPLACE VIEW fitness_dw.v_analiza_finansowa AS
SELECT 
    d.rok,
    d.miesiac,
    SUM(p.kwota) as przychod_calkowity,
    AVG(p.kwota) as srednia_wplata,
    COUNT(p.id) as liczba_transakcji
FROM fitness_dw.platnosci p
JOIN fitness_dw.daty d ON p.data_id = d.id
GROUP BY d.rok, d.miesiac;

-- Granty
GRANT USAGE ON SCHEMA fitness_dw TO fitness;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA fitness_dw TO fitness;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA fitness_dw TO fitness;
