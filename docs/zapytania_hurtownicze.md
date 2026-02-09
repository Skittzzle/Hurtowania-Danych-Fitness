# Zapytania hurtownicze użyte w projekcie

Poniżej zebrane są **wszystkie zapytania SQL** (DDL/DML/SELECT/CTE/OLAP) użyte w repozytorium (wg aktualnie znalezionych miejsc w kodzie).

---

## 1) `database/init.sql` (struktura hurtowni + widoki)

### 1.1 Utworzenie schematu
```sql
CREATE SCHEMA IF NOT EXISTS fitness_dw;
SET search_path TO fitness_dw, public;
```

### 1.2 Tabele wymiarów
```sql
CREATE TABLE IF NOT EXISTS fitness_dw.adresy (
    id SERIAL PRIMARY KEY,
    miasto VARCHAR(50) NOT NULL,
    kod_pocztowy VARCHAR(10) NOT NULL,
    ulica VARCHAR(100) NOT NULL,
    numer_domu VARCHAR(20) NOT NULL
);

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

CREATE TABLE IF NOT EXISTS fitness_dw.sale (
    id SERIAL PRIMARY KEY,
    numer_sali VARCHAR(20) NOT NULL,
    pojemnosc INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fitness_dw.zajecia (
    id SERIAL PRIMARY KEY,
    nazwa_zajec VARCHAR(100) NOT NULL,
    poziom_trudnosci VARCHAR(20) NOT NULL CHECK (poziom_trudnosci IN ('Początkujący', 'Średniozaawansowany', 'Zaawansowany'))
);

CREATE TABLE IF NOT EXISTS fitness_dw.specjalizacje (
    id SERIAL PRIMARY KEY,
    nazwa VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS fitness_dw.klienci (
    id SERIAL PRIMARY KEY,
    imie VARCHAR(50) NOT NULL,
    nazwisko VARCHAR(50) NOT NULL,
    plec VARCHAR(10) NOT NULL CHECK (plec IN ('M', 'K')),
    adres_id INTEGER REFERENCES fitness_dw.adresy(id),
    data_urodzenia DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS fitness_dw.trenerzy (
    id SERIAL PRIMARY KEY,
    imie VARCHAR(50) NOT NULL,
    nazwisko VARCHAR(50) NOT NULL,
    adres_id INTEGER REFERENCES fitness_dw.adresy(id),
    specjalizacja_id INTEGER REFERENCES fitness_dw.specjalizacje(id)
);
```

### 1.3 Tabele faktów
```sql
CREATE TABLE IF NOT EXISTS fitness_dw.wejscia (
    id SERIAL PRIMARY KEY,
    klient_id INTEGER NOT NULL REFERENCES fitness_dw.klienci(id),
    data_id INTEGER NOT NULL REFERENCES fitness_dw.daty(id),
    sala_id INTEGER NOT NULL REFERENCES fitness_dw.sale(id),
    czas_pobytu_min INTEGER NOT NULL CHECK (czas_pobytu_min > 0),
    data_wejscia TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS fitness_dw.platnosci (
    id SERIAL PRIMARY KEY,
    klient_id INTEGER NOT NULL REFERENCES fitness_dw.klienci(id),
    data_id INTEGER NOT NULL REFERENCES fitness_dw.daty(id),
    kwota DECIMAL(10,2) NOT NULL CHECK (kwota > 0),
    metoda_platnosci VARCHAR(20) NOT NULL CHECK (metoda_platnosci IN ('Karta', 'Gotówka', 'Przelew'))
);
```

### 1.4 Widoki analityczne
```sql
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
```

### 1.5 Uprawnienia
```sql
GRANT USAGE ON SCHEMA fitness_dw TO fitness;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA fitness_dw TO fitness;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA fitness_dw TO fitness;
```

---

## 2) `backend/app/routers/*.py` (API analityczne / ETL)

### 2.1 `backend/app/routers/analytics_extended.py`
#### Frekwencja dni miesiąca
```sql
SELECT 
    d.rok,
    d.miesiac,
    d.dzien,
    COUNT(w.id) as liczba_wejsc,
    AVG(w.czas_pobytu_min) as sredni_czas_pobytu,
    SUM(w.czas_pobytu_min) as calkowity_czas_pobytu
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
WHERE d.rok = :rok AND d.miesiac = :miesiac
GROUP BY d.rok, d.miesiac, d.dzien
ORDER BY d.rok, d.miesiac, d.dzien;
```

#### Frekwencja dnia (godzinowa)
```sql
SELECT 
    d.rok,
    d.miesiac,
    d.dzien,
    EXTRACT(HOUR FROM w.godzina_wejscia) as godzina,
    COUNT(w.id) as liczba_wejsc,
    AVG(w.czas_pobytu_min) as sredni_czas_pobytu,
    SUM(w.czas_pobytu_min) as calkowity_czas_pobytu,
    COUNT(DISTINCT w.klient_id) as unikalni_klienci
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
WHERE d.rok = :rok AND d.miesiac = :miesiac AND d.dzien = :dzien
GROUP BY d.rok, d.miesiac, d.dzien, EXTRACT(HOUR FROM w.godzina_wejscia)
ORDER BY d.rok, d.miesiac, d.dzien, godzina;
```

#### Podsumowanie dnia (CTE)
```sql
WITH dzienne_statystyki AS (
    SELECT 
        COUNT(w.id) as liczba_wejsc,
        COUNT(DISTINCT w.klient_id) as unikalni_klienci,
        AVG(w.czas_pobytu_min) as sredni_czas_pobytu,
        SUM(w.czas_pobytu_min) as calkowity_czas_pobytu,
        COUNT(DISTINCT w.sala_id) as liczba_uzytych_sal,
        COUNT(DISTINCT CASE WHEN w.zajecie_id IS NOT NULL THEN w.zajecie_id END) as liczba_zajec
    FROM fitness_dw.wejscia w
    JOIN fitness_dw.daty d ON w.data_id = d.id
    WHERE d.rok = :rok AND d.miesiac = :miesiac AND d.dzien = :dzien
),
poprzedni_dzien AS (
    SELECT 
        COUNT(w.id) as liczba_wejsc_poprzedni
    FROM fitness_dw.wejscia w
    JOIN fitness_dw.daty d ON w.data_id = d.id
    WHERE d.data_pelna = (
        SELECT DATE(d.data_pelna - INTERVAL '1 day')
        FROM fitness_dw.daty d
        WHERE d.rok = :rok AND d.miesiac = :miesiac AND d.dzien = :dzien
        LIMIT 1
    )
)
SELECT 
    ds.*, 
    pd.liczba_wejsc_poprzedni,
    CASE 
        WHEN pd.liczba_wejsc_poprzedni > 0 
        THEN ROUND((ds.liczba_wejsc - pd.liczba_wejsc_poprzedni) * 100.0 / pd.liczba_wejsc_poprzedni, 2)
        ELSE 0
    END as zmiana_procentowa
FROM dzienne_statystyki ds, poprzedni_dzien pd;
```

#### Frekwencja godzinowa (dla dnia / miesiąca)
```sql
SELECT 
    EXTRACT(HOUR FROM w.godzina_wejscia) as godzina,
    COUNT(w.id) as liczba_wejsc,
    COUNT(DISTINCT w.klient_id) as unikalni_klienci,
    AVG(w.czas_pobytu_min) as sredni_czas_pobytu
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
WHERE d.rok = :rok AND d.miesiac = :miesiac AND d.dzien = :dzien
GROUP BY EXTRACT(HOUR FROM w.godzina_wejscia)
ORDER BY godzina;

SELECT 
    EXTRACT(HOUR FROM w.godzina_wejscia) as godzina,
    COUNT(w.id) as liczba_wejsc,
    COUNT(DISTINCT w.klient_id) as unikalni_klienci,
    AVG(w.czas_pobytu_min) as sredni_czas_pobytu
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
WHERE d.rok = :rok AND d.miesiac = :miesiac
GROUP BY EXTRACT(HOUR FROM w.godzina_wejscia)
ORDER BY godzina;
```

### 2.2 `backend/app/routers/analytics_monthly.py`
#### Frekwencja miesiąca we wszystkich latach
```sql
SELECT 
    d.rok,
    d.miesiac,
    COUNT(w.id) as liczba_wejsc,
    COUNT(DISTINCT w.klient_id) as unikalni_klienci,
    AVG(w.czas_pobytu_min) as sredni_czas_pobytu,
    SUM(w.czas_pobytu_min) as calkowity_czas_pobytu
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
WHERE d.miesiac = :miesiac
GROUP BY d.rok, d.miesiac
ORDER BY d.rok, d.miesiac;
```

#### Porównanie miesięcy w roku (funkcje okna)
```sql
SELECT 
    d.miesiac,
    COUNT(w.id) as liczba_wejsc,
    COUNT(DISTINCT w.klient_id) as unikalni_klienci,
    AVG(w.czas_pobytu_min) as sredni_czas_pobytu,
    SUM(w.czas_pobytu_min) as calkowity_czas_pobytu,
    LAG(COUNT(w.id)) OVER (ORDER BY d.miesiac) as poprzedni_miesiac_wejscia,
    CASE 
        WHEN LAG(COUNT(w.id)) OVER (ORDER BY d.miesiac) IS NOT NULL
        THEN ROUND((COUNT(w.id) - LAG(COUNT(w.id)) OVER (ORDER BY d.miesiac)) * 100.0 / LAG(COUNT(w.id)) OVER (ORDER BY d.miesiac), 2)
        ELSE NULL
    END as zmiana_procentowa
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
WHERE d.rok = :rok
GROUP BY d.rok, d.miesiac
ORDER BY d.miesiac;
```

#### Podsumowanie roczne (CTE + porównanie r/r)
```sql
WITH roczne_statystyki AS (
    SELECT 
        COUNT(w.id) as calkowita_liczba_wejsc,
        COUNT(DISTINCT w.klient_id) as unikalni_klienci,
        AVG(w.czas_pobytu_min) as sredni_czas_pobytu,
        SUM(w.czas_pobytu_min) as calkowity_czas_pobytu,
        COUNT(DISTINCT w.sala_id) as liczba_uzytych_sal,
        COUNT(DISTINCT CASE WHEN w.zajecie_id IS NOT NULL THEN w.zajecie_id END) as liczba_zajec,
        COUNT(DISTINCT EXTRACT(MONTH FROM d.data_pelna)) as liczba_aktywnych_miesiecy
    FROM fitness_dw.wejscia w
    JOIN fitness_dw.daty d ON w.data_id = d.id
    WHERE d.rok = :rok
),
poprzedni_rok AS (
    SELECT 
        COUNT(w.id) as calkowita_liczba_wejsc_poprzedni
    FROM fitness_dw.wejscia w
    JOIN fitness_dw.daty d ON w.data_id = d.id
    WHERE d.rok = :rok - 1
)
SELECT 
    rs.*,
    pr.calkowita_liczba_wejsc_poprzedni,
    CASE 
        WHEN pr.calkowita_liczba_wejsc_poprzedni > 0
        THEN ROUND((rs.calkowita_liczba_wejsc - pr.calkowita_liczba_wejsc_poprzedni) * 100.0 / pr.calkowita_liczba_wejsc_poprzedni, 2)
        ELSE 0
    END as zmiana_roczna_procentowa,
    ROUND(rs.calkowita_liczba_wejsc / 12.0, 2) as srednia_miesieczna,
    ROUND(rs.calkowity_czas_pobytu / rs.unikalni_klienci, 2) as sredni_czas_na_klienta
FROM roczne_statystyki rs, poprzedni_rok pr;
```

### 2.3 `backend/app/routers/analytics.py` i `backend/app/routers/analytics_fixed.py`
#### Widoki wykorzystywane przez API
Uwaga: routery odwołują się do widoków, których **definicji nie ma** w `database/init.sql` (przynajmniej w aktualnej wersji pliku):
- `fitness_dw.v_frekwencja_miesieczna`
- `fitness_dw.v_popularnosc_zajec`
- `fitness_dw.v_obciazenie_sal`

Zapytania:
```sql
SELECT rok, miesiac, liczba_wejsc, sredni_czas_pobytu
FROM fitness_dw.v_frekwencja_miesieczna
ORDER BY rok, miesiac;

SELECT nazwa_zajec, poziom_trudnosci, liczba_zajec, srednia_ocena, total_participants, avg_participants
FROM fitness_dw.v_popularnosc_zajec
ORDER BY total_participants DESC
LIMIT :limit;

SELECT imie_nazwisko_trenera, specjalizacja, liczba_prowadzonych_zajec, srednia_ocena_zajec, suma_uczestnikow
FROM fitness_dw.v_efektywnosc_trenerow
ORDER BY srednia_ocena_zajec DESC
LIMIT :limit;

SELECT numer_sali, pojemnosc, liczba_unikalnych_klientow, liczba_wejsc, liczba_roznych_zajec, sredni_czas_pobytu
FROM fitness_dw.v_obciazenie_sal
ORDER BY liczba_wejsc DESC
LIMIT :limit;
```

### 2.4 `backend/app/routers/trends.py`
#### Trendy (funkcje okna)
```sql
SELECT 
    rok,
    miesiac,
    liczba_wejsc,
    sredni_czas_pobytu,
    LAG(liczba_wejsc, 1) OVER (ORDER BY rok, miesiac) as poprzednia_miesiac,
    ROUND(
        (liczba_wejsc - LAG(liczba_wejsc, 1) OVER (ORDER BY rok, miesiac)) * 100.0 /
        NULLIF(LAG(liczba_wejsc, 1) OVER (ORDER BY rok, miesiac), 0), 2
    ) as zmiana_procent,
    CASE 
        WHEN liczba_wejsc > LAG(liczba_wejsc, 1) OVER (ORDER BY rok, miesiac) THEN 'wzrost'
        WHEN liczba_wejsc < LAG(liczba_wejsc, 1) OVER (ORDER BY rok, miesiac) THEN 'spadek'
        ELSE 'bez zmian'
    END as trend
FROM fitness_dw.v_frekwencja_miesieczna
ORDER BY rok DESC, miesiac DESC
LIMIT :lat * 12;
```

#### Prognozy (CTE)
```sql
WITH srednia_miesieczna AS (
    SELECT 
        EXTRACT(MONTH FROM data_pelna) as miesiac,
        AVG(liczba_wejsc) as srednia_wejsc
    FROM fitness_dw.wejscia w
    JOIN fitness_dw.daty d ON w.data_id = d.id
    WHERE data_pelna >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY EXTRACT(MONTH FROM data_pelna)
)
SELECT 
    miesiac,
    srednia_wejsc,
    ROUND(srednia_wejsc * 1.05) as prognoza_wzrost,
    ROUND(srednia_wejsc * 0.95) as prognoza_spadek
FROM srednia_miesieczna
ORDER BY miesiac
LIMIT :miesice_naprzod;
```

#### Porównanie r/r (funkcje okna)
```sql
SELECT 
    rok,
    SUM(liczba_wejsc) as calkowita_frekwencja,
    AVG(sredni_czas_pobytu) as sredni_czas_roczny,
    COUNT(DISTINCT miesiac) as liczba_miesiecy_aktywnych,
    ROUND(
        (SUM(liczba_wejsc) - LAG(SUM(liczba_wejsc), 1) OVER (ORDER BY rok)) * 100.0 /
        NULLIF(LAG(SUM(liczba_wejsc), 1) OVER (ORDER BY rok), 0), 2
    ) as zmiana_roczna_procent,
    CASE 
        WHEN SUM(liczba_wejsc) > LAG(SUM(liczba_wejsc), 1) OVER (ORDER BY rok) THEN 'wzrost'
        WHEN SUM(liczba_wejsc) < LAG(SUM(liczba_wejsc), 1) OVER (ORDER BY rok) THEN 'spadek'
        ELSE 'bez zmian'
    END as trend_roczny
FROM fitness_dw.v_frekwencja_miesieczna
GROUP BY rok
ORDER BY rok DESC;
```

### 2.5 `backend/app/routers/segmentation.py`
#### Segmentacja klientów (CTE + CASE)
```sql
WITH ostatnia_aktywnosc AS (
    SELECT 
        k.id as klient_id,
        k.imie,
        k.nazwisko,
        MAX(d.data_pelna) as ostatnia_wizyta,
        COUNT(w.id) as liczba_wizyt,
        AVG(w.czas_pobytu_min) as sredni_czas_pobytu,
        COUNT(DISTINCT d.miesiac) as liczba_miesiecy_aktywnych,
        CURRENT_DATE - MAX(d.data_pelna) as dni_od_ostatniej_wizyty
    FROM fitness_dw.klienci k
    LEFT JOIN fitness_dw.wejscia w ON k.id = w.klient_id
    LEFT JOIN fitness_dw.daty d ON w.data_id = d.id
    GROUP BY k.id, k.imie, k.nazwisko
),
segmentacja AS (
    SELECT 
        *,
        CASE 
            WHEN dni_od_ostatniej_wizyty <= 30 AND liczba_wizyt >= 10 THEN 'Aktywni Premium'
            WHEN dni_od_ostatniej_wizyty <= 30 AND liczba_wizyt >= 5 THEN 'Aktywni Regularni'
            WHEN dni_od_ostatniej_wizyty <= 60 AND liczba_wizyt >= 3 THEN 'Aktywni Okazjonalni'
            WHEN dni_od_ostatniej_wizyty > 60 AND liczba_wizyt >= 5 THEN 'Uśpieni'
            WHEN dni_od_ostatniej_wizyty > 90 THEN 'Nieaktywni'
            ELSE 'Nowi'
        END as segment_klienta,
        CASE 
            WHEN liczba_wizyt >= 20 THEN 'Wysoka'
            WHEN liczba_wizyt >= 10 THEN 'Średnia'
            WHEN liczba_wizyt >= 5 THEN 'Niska'
            ELSE 'Bardzo niska'
        END as czestotliwosc_wizyt,
        CASE 
            WHEN sredni_czas_pobytu >= 90 THEN 'Długi'
            WHEN sredni_czas_pobytu >= 60 THEN 'Średni'
            WHEN sredni_czas_pobytu >= 30 THEN 'Krótki'
            ELSE 'Bardzo krótki'
        END as czas_wizyt
    FROM ostatnia_aktywnosc
)
SELECT *
FROM segmentacja
ORDER BY liczba_wizyt DESC;
```

#### Segmentacja podsumowanie (okno: udział %)
```sql
WITH ostatnia_aktywnosc AS (
    SELECT 
        k.id as klient_id,
        MAX(d.data_pelna) as ostatnia_wizyta,
        COUNT(w.id) as liczba_wizyt,
        CURRENT_DATE - MAX(d.data_pelna) as dni_od_ostatniej_wizyty
    FROM fitness_dw.klienci k
    LEFT JOIN fitness_dw.wejscia w ON k.id = w.klient_id
    LEFT JOIN fitness_dw.daty d ON w.data_id = d.id
    GROUP BY k.id
),
segmentacja AS (
    SELECT 
        CASE 
            WHEN dni_od_ostatniej_wizyty <= 30 AND liczba_wizyt >= 10 THEN 'Aktywni Premium'
            WHEN dni_od_ostatniej_wizyty <= 30 AND liczba_wizyt >= 5 THEN 'Aktywni Regularni'
            WHEN dni_od_ostatniej_wizyty <= 60 AND liczba_wizyt >= 3 THEN 'Aktywni Okazjonalni'
            WHEN dni_od_ostatniej_wizyty > 60 AND liczba_wizyt >= 5 THEN 'Uśpieni'
            WHEN dni_od_ostatniej_wizyty > 90 THEN 'Nieaktywni'
            ELSE 'Nowi'
        END as segment_klienta
    FROM ostatnia_aktywnosc
)
SELECT 
    segment_klienta,
    COUNT(*) as liczba_klientow,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as procent_klientow
FROM segmentacja
GROUP BY segment_klienta
ORDER BY liczba_klientow DESC;
```

#### Retencja (CTE)
```sql
WITH retencja_miesieczna AS (
    SELECT 
        d.rok,
        d.miesiac,
        COUNT(DISTINCT k.id) as klienci_miesiac,
        COUNT(DISTINCT CASE 
            WHEN d.data_pelna >= CURRENT_DATE - INTERVAL '3 months' THEN k.id
        END) as klienci_aktywni_3m,
        COUNT(DISTINCT CASE 
            WHEN d.data_pelna >= CURRENT_DATE - INTERVAL '6 months' THEN k.id
        END) as klienci_aktywni_6m,
        COUNT(DISTINCT CASE 
            WHEN d.data_pelna >= CURRENT_DATE - INTERVAL '12 months' THEN k.id
        END) as klienci_aktywni_12m
    FROM fitness_dw.wejscia w
    JOIN fitness_dw.klienci k ON w.klient_id = k.id
    JOIN fitness_dw.daty d ON w.data_id = d.id
    WHERE d.data_pelna >= CURRENT_DATE - INTERVAL ':miesiecy months'
    GROUP BY d.rok, d.miesiac
    ORDER BY d.rok DESC, d.miesiac DESC
)
SELECT 
    rok,
    miesiac,
    klienci_miesiac,
    klienci_aktywni_3m,
    klienci_aktywni_6m,
    klienci_aktywni_12m,
    ROUND(klienci_aktywni_3m * 100.0 / NULLIF(klienci_miesiac, 0), 2) as retencja_3m_procent,
    ROUND(klienci_aktywni_6m * 100.0 / NULLIF(klienci_miesiac, 0), 2) as retencja_6m_procent,
    ROUND(klienci_aktywni_12m * 100.0 / NULLIF(klienci_miesiac, 0), 2) as retencja_12m_procent
FROM retencja_miesieczna
ORDER BY rok DESC, miesiac DESC;
```

#### CLV (CTE)
```sql
WITH clv_klientow AS (
    SELECT 
        k.id as klient_id,
        k.imie,
        k.nazwisko,
        COUNT(w.id) as liczba_wizyt,
        AVG(w.czas_pobytu_min) as sredni_czas_pobytu,
        COUNT(DISTINCT d.miesiac) as liczba_miesiecy_aktywnych,
        MIN(d.data_pelna) as pierwsza_wizyta,
        MAX(d.data_pelna) as ostatnia_wizyta,
        CURRENT_DATE - MIN(d.data_pelna) as dni_od_pierwszej_wizyty,
        COUNT(DISTINCT w.sala_id) as liczba_roznych_sal,
        AVG(uz.ocena_zajec) as srednia_ocena_zajec
    FROM fitness_dw.klienci k
    LEFT JOIN fitness_dw.wejscia w ON k.id = w.klient_id
    LEFT JOIN fitness_dw.daty d ON w.data_id = d.id
    LEFT JOIN fitness_dw.uczestnictwo_zajec uz ON k.id = uz.klient_id
    GROUP BY k.id, k.imie, k.nazwisko
),
clv_obliczenia AS (
    SELECT 
        *,
        CASE 
            WHEN liczba_wizyt > 0 THEN 
                ROUND((liczba_wizyt * sredni_czas_pobytu * 0.5) + (liczba_miesiecy_aktywnych * 10), 2)
            ELSE 0
        END as clv_wartosc,
        CASE 
            WHEN dni_od_pierwszej_wizyty > 0 THEN 
                ROUND(liczba_wizyt * 365.0 / dni_od_pierwszej_wizyty, 2)
            ELSE 0
        END as czestotliwosc_roczna
    FROM clv_klientow
),
clv_segmentacja AS (
    SELECT 
        *,
        CASE 
            WHEN clv_wartosc >= 1000 THEN 'Wysoka wartość'
            WHEN clv_wartosc >= 500 THEN 'Średnia wartość'
            WHEN clv_wartosc >= 100 THEN 'Niska wartość'
            ELSE 'Bardzo niska wartość'
        END as segment_wartosci
    FROM clv_obliczenia
)
SELECT *
FROM clv_segmentacja
ORDER BY clv_wartosc DESC
LIMIT 50;
```

### 2.6 `backend/app/routers/etl.py`
#### Czyszczenie tabel
```sql
DELETE FROM fitness_dw.uczestnictwo_zajec;
DELETE FROM fitness_dw.wejscia;
DELETE FROM fitness_dw.klienci;
DELETE FROM fitness_dw.trenerzy;
DELETE FROM fitness_dw.zajecia;
DELETE FROM fitness_dw.sale;
DELETE FROM fitness_dw.daty;
DELETE FROM fitness_dw.adresy;
```

#### Reset sekwencji
```sql
ALTER SEQUENCE fitness_dw.adresy_id_seq RESTART WITH 1;
ALTER SEQUENCE fitness_dw.daty_id_seq RESTART WITH 1;
ALTER SEQUENCE fitness_dw.sale_id_seq RESTART WITH 1;
ALTER SEQUENCE fitness_dw.zajecia_id_seq RESTART WITH 1;
ALTER SEQUENCE fitness_dw.klienci_id_seq RESTART WITH 1;
ALTER SEQUENCE fitness_dw.trenerzy_id_seq RESTART WITH 1;
ALTER SEQUENCE fitness_dw.wejscia_id_seq RESTART WITH 1;
ALTER SEQUENCE fitness_dw.uczestnictwo_zajec_id_seq RESTART WITH 1;
```

#### Status danych
```sql
SELECT COUNT(*) FROM fitness_dw.<table>;
```

---

## 3) `backend/app/services/*.py` (ETL / CSV)

### 3.1 `backend/app/services/etl_service.py` (ETL: INSERT/RETURNING)
Zapytania powtarzają się wzorcem `INSERT INTO ... RETURNING id` dla wymiarów i faktów. Najważniejsze:

```sql
INSERT INTO fitness_dw.adresy (miasto, kod_pocztowy, ulica, numer_domu)
VALUES (:miasto, :kod_pocztowy, :ulica, :numer_domu)
RETURNING id;

INSERT INTO fitness_dw.daty (dzien, miesiac, rok, data_pelna, dzien_tygodnia, kwartal)
VALUES (:dzien, :miesiac, :rok, :data_pelna, :dzien_tygodnia, :kwartal)
RETURNING id;

INSERT INTO fitness_dw.sale (numer_sali, pojemnosc)
VALUES (:numer_sali, :pojemnosc)
RETURNING id;

INSERT INTO fitness_dw.zajecia (nazwa_zajec, poziom_trudnosci)
VALUES (:nazwa_zajec, :poziom_trudnosci)
RETURNING id;

INSERT INTO fitness_dw.specjalizacje (nazwa)
VALUES (:nazwa)
ON CONFLICT (nazwa) DO UPDATE SET nazwa = EXCLUDED.nazwa
RETURNING id;

INSERT INTO fitness_dw.trenerzy (imie, nazwisko, adres_id, specjalizacja_id)
VALUES (:imie, :nazwisko, :adres_id, :spec_id)
RETURNING id;

INSERT INTO fitness_dw.klienci (imie, nazwisko, plec, adres_id, data_urodzenia)
VALUES (:imie, :nazwisko, :plec, :adres_id, :data_urodzenia)
RETURNING id;

INSERT INTO fitness_dw.wejscia (klient_id, data_id, sala_id, czas_pobytu_min, data_wejscia)
VALUES (:klient_id, :data_id, :sala_id, :czas_pobytu_min, :data_wejscia);

INSERT INTO fitness_dw.uczestnictwo_zajec (data_id, klient_id, trener_id, zajecie_id, sala_id, ocena_zajec, czas_trwania, liczba_uczestnikow, data_zajec)
VALUES (:data_id, :klient_id, :trener_id, :zajecie_id, :sala_id, :ocena_zajec, :czas_trwania, :liczba_uczestnikow, :data_zajec);

INSERT INTO fitness_dw.platnosci (klient_id, data_id, kwota, metoda_platnosci)
VALUES (:klient_id, :data_id, :kwota, :metoda);
```

### 3.2 `backend/app/services/csv_service.py` (import CSV)
```sql
INSERT INTO <table> (<cols>) VALUES (<placeholders>) ON CONFLICT DO NOTHING;
```

---

## 4) `database/*.py` (import/export)

### 4.1 `database/import_csv.py`
```sql
TRUNCATE TABLE fitness_dw.wejscia, fitness_dw.uczestnictwo_zajec, fitness_dw.klienci, fitness_dw.trenerzy, fitness_dw.specjalizacje, fitness_dw.zajecia, fitness_dw.sale, fitness_dw.daty, fitness_dw.adresy CASCADE;
```

### 4.2 `database/generate_csv.py`
```sql
SELECT * FROM fitness_dw.<table>;
```

---

## 5) `app.py` (Streamlit GUI: zapytania analityczne + OLAP)

W `app.py` jest najwięcej SQL (dynamiczne filtry + OLAP). Poniżej najważniejsze zapytania (występują jako `sqlalchemy.text(...)` oraz `pd.read_sql`).

### 5.1 Statystyki dashboardu
```sql
SELECT COUNT(*)
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
JOIN fitness_dw.sale s ON w.sala_id = s.id
JOIN fitness_dw.klienci k ON w.klient_id = k.id
WHERE <dynamic_where>;

SELECT SUM(p.kwota) as revenue
FROM fitness_dw.platnosci p
JOIN fitness_dw.daty d ON p.data_id = d.id
JOIN fitness_dw.klienci k ON p.klient_id = k.id
WHERE <dynamic_where>;

SELECT AVG(uz.ocena_zajec) as avg_rating
FROM fitness_dw.uczestnictwo_zajec uz
JOIN fitness_dw.klienci k ON uz.klient_id = k.id
JOIN fitness_dw.sale s ON uz.sala_id = s.id
JOIN fitness_dw.daty d ON uz.data_id = d.id
WHERE <dynamic_where>;
```

### 5.2 Obłożenie vs pojemność
```sql
SELECT 
    s.numer_sali,
    s.pojemnosc,
    AVG(uz.liczba_uczestnikow) as srednie_oblozenie
FROM fitness_dw.sale s
LEFT JOIN fitness_dw.uczestnictwo_zajec uz ON s.id = uz.sala_id
LEFT JOIN fitness_dw.daty d ON uz.data_id = d.id
LEFT JOIN fitness_dw.klienci k ON uz.klient_id = k.id
WHERE <dynamic_where>
GROUP BY s.id, s.numer_sali, s.pojemnosc;
```

### 5.3 Satysfakcja zajęć
```sql
SELECT 
    z.nazwa_zajec,
    AVG(uz.ocena_zajec) as srednia_ocena,
    SUM(uz.liczba_uczestnikow) as suma_uczestnikow
FROM fitness_dw.uczestnictwo_zajec uz
JOIN fitness_dw.zajecia z ON uz.zajecie_id = z.id
JOIN fitness_dw.daty d ON uz.data_id = d.id
JOIN fitness_dw.klienci k ON uz.klient_id = k.id
WHERE <dynamic_where>
GROUP BY z.nazwa_zajec
ORDER BY suma_uczestnikow DESC;
```

### 5.4 City LTV / metody płatności / przychód miesięczny
```sql
SELECT 
    a.miasto,
    COUNT(DISTINCT k.id) as liczba_klientow,
    SUM(p.kwota) as suma_wplat,
    ROUND(AVG(p.kwota), 2) as srednia_wplata
FROM fitness_dw.klienci k
JOIN fitness_dw.adresy a ON k.adres_id = a.id
JOIN fitness_dw.platnosci p ON k.id = p.klient_id
JOIN fitness_dw.daty d ON p.data_id = d.id
WHERE <dynamic_where>
GROUP BY a.miasto
ORDER BY suma_wplat DESC;

SELECT metoda_platnosci, COUNT(*) as liczba, SUM(kwota) as suma
FROM fitness_dw.platnosci p
JOIN fitness_dw.klienci k ON p.klient_id = k.id
JOIN fitness_dw.daty d ON p.data_id = d.id
WHERE <dynamic_where>
GROUP BY metoda_platnosci;

SELECT d.rok, d.miesiac, SUM(p.kwota) as suma_wplat
FROM fitness_dw.platnosci p
JOIN fitness_dw.klienci k ON p.klient_id = k.id
JOIN fitness_dw.daty d ON p.data_id = d.id
WHERE <dynamic_where>
GROUP BY d.rok, d.miesiac
ORDER BY d.rok, d.miesiac;
```

### 5.5 Korelacje
```sql
SELECT 
    EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) as wiek,
    EXTRACT(HOUR FROM w.data_wejscia) as godzina,
    EXTRACT(DOW FROM w.data_wejscia) as dzien_tyg,
    w.czas_pobytu_min as czas_pobytu
FROM fitness_dw.wejscia w
JOIN fitness_dw.klienci k ON w.klient_id = k.id;
```

### 5.6 Rotation / pivot (OLAP)
```sql
SELECT sp.nazwa as label, COUNT(uz.id) as liczba_wejsc
FROM fitness_dw.uczestnictwo_zajec uz
JOIN fitness_dw.trenerzy t ON uz.trener_id = t.id
JOIN fitness_dw.specjalizacje sp ON t.specjalizacja_id = sp.id
JOIN fitness_dw.daty d ON uz.data_id = d.id
JOIN fitness_dw.sale s ON uz.sala_id = s.id
JOIN fitness_dw.klienci k ON uz.klient_id = k.id
WHERE <dynamic_where>
GROUP BY sp.nazwa;

SELECT <select_cols>
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
JOIN fitness_dw.sale s ON w.sala_id = s.id
JOIN fitness_dw.klienci k ON w.klient_id = k.id
WHERE <dynamic_where>
GROUP BY <group_by>
ORDER BY <group_by>;
```

### 5.7 Drill-down (dni miesiąca)
```sql
SELECT d.dzien, COUNT(w.id) as liczba_wejsc
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
WHERE d.rok = <rok> AND d.miesiac = <miesiac>
GROUP BY d.dzien
ORDER BY d.dzien;
```

### 5.8 Heatmap obłożenia
```sql
SELECT 
    d.dzien_tygodnia,
    EXTRACT(HOUR FROM w.data_wejscia) as godzina,
    COUNT(*) as liczba_wejsc
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
JOIN fitness_dw.sale s ON w.sala_id = s.id
JOIN fitness_dw.klienci k ON w.klient_id = k.id
WHERE <dynamic_where>
GROUP BY d.dzien_tygodnia, godzina;
```

### 5.9 Dane do ML
```sql
WITH client_history AS (
    SELECT 
        klient_id,
        COUNT(*) OVER (PARTITION BY klient_id ORDER BY data_wejscia) as total_prev_visits
    FROM fitness_dw.wejscia
)
SELECT 
    EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) as wiek,
    CASE WHEN k.plec = 'M' THEN 1 ELSE 0 END as plec_bin,
    EXTRACT(HOUR FROM w.data_wejscia) as godzina,
    EXTRACT(DOW FROM w.data_wejscia) as dzien_tyg,
    d.miesiac,
    CASE WHEN d.dzien_tygodnia IN ('Saturday', 'Sunday') THEN 1 ELSE 0 END as is_weekend,
    ch.total_prev_visits,
    w.czas_pobytu_min as target
FROM fitness_dw.wejscia w
JOIN fitness_dw.klienci k ON w.klient_id = k.id
JOIN fitness_dw.daty d ON w.data_id = d.id
JOIN client_history ch ON w.klient_id = ch.klient_id AND w.id = w.id
WHERE <dynamic_where>
LIMIT 10000;
```

### 5.10 Zapytania pomocnicze (filtry, transakcje)
```sql
SELECT MIN(data_pelna), MAX(data_pelna) FROM fitness_dw.daty;
SELECT DISTINCT rok FROM fitness_dw.daty ORDER BY rok DESC;
SELECT DISTINCT numer_sali FROM fitness_dw.sale ORDER BY numer_sali;

TRUNCATE TABLE fitness_dw.platnosci CASCADE;
TRUNCATE TABLE fitness_dw.uczestnictwo_zajec CASCADE;
TRUNCATE TABLE fitness_dw.wejscia CASCADE;
TRUNCATE TABLE fitness_dw.klienci CASCADE;

SELECT id, miasto, ulica FROM fitness_dw.adresy LIMIT 10;
SELECT id, imie, nazwisko FROM fitness_dw.klienci ORDER BY nazwisko LIMIT 100;
SELECT id, numer_sali FROM fitness_dw.sale;
SELECT id FROM fitness_dw.daty WHERE data_pelna = :d;
```

---

## 6) `app.py` (ROLLUP / CUBE / GROUPING SETS)

Sekcja dodana, aby w projekcie występowały jawne konstrukcje SQL: `ROLLUP`, `CUBE`, `GROUPING SETS`.

### 6.1 ROLLUP (przychód: rok → miesiąc → suma)
Źródło: `app.py` → `load_rollup_revenue(...)`

```sql
SELECT
    d.rok,
    d.miesiac,
    SUM(p.kwota) as suma_wplat,
    GROUPING(d.rok) as g_rok,
    GROUPING(d.miesiac) as g_miesiac
FROM fitness_dw.platnosci p
JOIN fitness_dw.daty d ON p.data_id = d.id
JOIN fitness_dw.klienci k ON p.klient_id = k.id
WHERE <dynamic_where>
GROUP BY ROLLUP(d.rok, d.miesiac)
ORDER BY d.rok NULLS LAST, d.miesiac NULLS LAST;
```

### 6.2 CUBE (frekwencja: płeć × dzień tygodnia + sumy częściowe)
Źródło: `app.py` → `load_cube_attendance(...)`

```sql
SELECT
    k.plec,
    d.dzien_tygodnia,
    COUNT(w.id) as liczba_wejsc,
    GROUPING(k.plec) as g_plec,
    GROUPING(d.dzien_tygodnia) as g_dzien_tygodnia
FROM fitness_dw.wejscia w
JOIN fitness_dw.klienci k ON w.klient_id = k.id
JOIN fitness_dw.daty d ON w.data_id = d.id
JOIN fitness_dw.sale s ON w.sala_id = s.id
WHERE <dynamic_where>
GROUP BY CUBE(k.plec, d.dzien_tygodnia)
ORDER BY k.plec NULLS LAST, d.dzien_tygodnia NULLS LAST;
```

### 6.3 GROUPING SETS (uczestnictwo: specjalizacja / rok / miesiąc + sumy)
Źródło: `app.py` → `load_grouping_sets_participation(...)`

```sql
SELECT
    sp.nazwa as specjalizacja,
    d.rok,
    d.miesiac,
    COUNT(uz.id) as liczba_sesji,
    SUM(uz.liczba_uczestnikow) as suma_uczestnikow,
    GROUPING(sp.nazwa) as g_specjalizacja,
    GROUPING(d.rok) as g_rok,
    GROUPING(d.miesiac) as g_miesiac
FROM fitness_dw.uczestnictwo_zajec uz
JOIN fitness_dw.trenerzy t ON uz.trener_id = t.id
JOIN fitness_dw.specjalizacje sp ON t.specjalizacja_id = sp.id
JOIN fitness_dw.daty d ON uz.data_id = d.id
JOIN fitness_dw.sale s ON uz.sala_id = s.id
JOIN fitness_dw.klienci k ON uz.klient_id = k.id
WHERE <dynamic_where>
GROUP BY GROUPING SETS (
    (sp.nazwa, d.rok, d.miesiac),
    (sp.nazwa, d.rok),
    (d.rok),
    ()
)
ORDER BY sp.nazwa NULLS LAST, d.rok NULLS LAST, d.miesiac NULLS LAST;
```

### 6.4 ROLLUP (frekwencja: sala → rok → miesiąc → suma)
Źródło: `app.py` → `load_rollup_attendance_room_month(...)`

```sql
SELECT
    s.numer_sali,
    d.rok,
    d.miesiac,
    COUNT(w.id) as liczba_wejsc,
    GROUPING(s.numer_sali) as g_sala,
    GROUPING(d.rok) as g_rok,
    GROUPING(d.miesiac) as g_miesiac
FROM fitness_dw.wejscia w
JOIN fitness_dw.daty d ON w.data_id = d.id
JOIN fitness_dw.sale s ON w.sala_id = s.id
JOIN fitness_dw.klienci k ON w.klient_id = k.id
WHERE <dynamic_where>
GROUP BY ROLLUP(s.numer_sali, d.rok, d.miesiac)
ORDER BY s.numer_sali NULLS LAST, d.rok NULLS LAST, d.miesiac NULLS LAST;
```

### 6.5 CUBE (płatności: metoda × płeć + sumy częściowe)
Źródło: `app.py` → `load_cube_payments_method_gender(...)`

```sql
SELECT
    p.metoda_platnosci,
    k.plec,
    COUNT(p.id) as liczba_platnosci,
    SUM(p.kwota) as suma_kwot,
    GROUPING(p.metoda_platnosci) as g_metoda,
    GROUPING(k.plec) as g_plec
FROM fitness_dw.platnosci p
JOIN fitness_dw.daty d ON p.data_id = d.id
JOIN fitness_dw.klienci k ON p.klient_id = k.id
WHERE <dynamic_where>
GROUP BY CUBE(p.metoda_platnosci, k.plec)
ORDER BY p.metoda_platnosci NULLS LAST, k.plec NULLS LAST;
```

### 6.6 GROUPING SETS (przychód: czas i metoda płatności + sumy)
Źródło: `app.py` → `load_grouping_sets_revenue_time_method(...)`

```sql
SELECT
    d.rok,
    d.miesiac,
    p.metoda_platnosci,
    SUM(p.kwota) as suma_kwot,
    COUNT(p.id) as liczba_platnosci,
    GROUPING(d.rok) as g_rok,
    GROUPING(d.miesiac) as g_miesiac,
    GROUPING(p.metoda_platnosci) as g_metoda
FROM fitness_dw.platnosci p
JOIN fitness_dw.daty d ON p.data_id = d.id
JOIN fitness_dw.klienci k ON p.klient_id = k.id
WHERE <dynamic_where>
GROUP BY GROUPING SETS (
    (d.rok, d.miesiac, p.metoda_platnosci),
    (d.rok, p.metoda_platnosci),
    (d.rok, d.miesiac),
    (p.metoda_platnosci),
    ()
)
ORDER BY d.rok NULLS LAST, d.miesiac NULLS LAST, p.metoda_platnosci NULLS LAST;
```

---

## Notatki kontrolne

1. **Brakujące widoki**: w kodzie API występują odwołania do `v_frekwencja_miesieczna`, `v_popularnosc_zajec`, `v_obciazenie_sal`, ale ich definicji nie widać w `database/init.sql`.
2. W `app.py` wiele zapytań używa **f-stringów z wstrzykniętymi wartościami** (dynamiczny `WHERE`). Dla projektu akademickiego to zwykle OK, ale technicznie lepiej używać parametrów (bezpieczniej).
