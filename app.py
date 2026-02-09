import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
from backend.app.database import SessionLocal
from backend.app.models import *

# Page configuration
st.set_page_config(
    page_title="Fitness Data Warehouse - Dashboard",
    page_icon="🏋️‍♂️",
    layout="wide"
)

# Premium CSS for responsiveness and dark-mode support
st.markdown("""
<style>
    .stApp {
        background: var(--background-color);
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: var(--primary-color);
    }
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(to right, var(--primary-color), #673ab7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: var(--secondary-background-color);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    /* Fix for tabs visibility in dark mode */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
</style>
""", unsafe_allow_html=True)

import numpy as np
import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from backend.app.services.csv_service import CSVService

def db_create_klient(db, data):
    try:
        new_client = Klienci(**data)
        db.add(new_client)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        st.error(f"Error: {e}")
        return False

def db_create_wejscie(db, data):
    try:
        new_entry = Wejscia(**data)
        db.add(new_entry)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        st.error(f"Error: {e}")
        return False

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def load_dashboard_stats(db, rooms = None, start_date = None, end_date = None, gender = None, years = None):
    try:
        # Base filters that apply to all facts
        base_clauses = ["1=1"]
        if gender and gender != "Wszystko":
            base_clauses.append(f"k.plec = '{gender}'")
        if start_date and end_date:
            base_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
        if years:
            base_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
        
        base_where = " AND ".join(base_clauses)
        
        # Room-specific filter
        room_clause = ""
        if rooms:
            room_clause = f" AND s.numer_sali IN ({','.join([f'\'{r}\'' for r in rooms])})"
        
        # Frequency (Physical Entries in range)
        freq_query = text(f"""
            SELECT COUNT(*) 
            FROM fitness_dw.wejscia w
            JOIN fitness_dw.daty d ON w.data_id = d.id
            JOIN fitness_dw.sale s ON w.sala_id = s.id
            JOIN fitness_dw.klienci k ON w.klient_id = k.id
            WHERE {base_where} {room_clause}
        """)
        total_visits = db.execute(freq_query).scalar() or 0
        
        # Total revenue
        revenue_query = text(f"""
            SELECT SUM(p.kwota) as revenue
            FROM fitness_dw.platnosci p
            JOIN fitness_dw.daty d ON p.data_id = d.id
            JOIN fitness_dw.klienci k ON p.klient_id = k.id
            WHERE {base_where}
        """)
        total_revenue = db.execute(revenue_query).scalar() or 0.0
        
        # Avg rating
        avg_rating_query = text(f"""
            SELECT AVG(uz.ocena_zajec) as avg_rating 
            FROM fitness_dw.uczestnictwo_zajec uz
            JOIN fitness_dw.klienci k ON uz.klient_id = k.id
            JOIN fitness_dw.sale s ON uz.sala_id = s.id
            JOIN fitness_dw.daty d ON uz.data_id = d.id
            WHERE {base_where} {room_clause}
        """)
        avg_rating = db.execute(avg_rating_query).scalar()
        
        return {
            "frekwencja": total_visits,
            "ocena": round(float(avg_rating), 2) if avg_rating else 0.0,
            "przychod": round(float(total_revenue), 2)
        }
    except Exception as e:
        st.error(f"Błąd ładowania statystyk: {e}")
        return None

def load_room_occupancy_vs_capacity(db, gender=None, start_date=None, end_date=None, years=None):
    where_clauses = ["1=1"]
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
        
    where_str = " AND ".join(where_clauses)
    
    query = text(f"""
        SELECT 
            s.numer_sali,
            s.pojemnosc,
            AVG(uz.liczba_uczestnikow) as srednie_oblozenie
        FROM fitness_dw.sale s
        LEFT JOIN fitness_dw.uczestnictwo_zajec uz ON s.id = uz.sala_id
        LEFT JOIN fitness_dw.daty d ON uz.data_id = d.id
        LEFT JOIN fitness_dw.klienci k ON uz.klient_id = k.id
        WHERE {where_str}
        GROUP BY s.id, s.numer_sali, s.pojemnosc
    """)
    df = pd.read_sql(query, db.bind)
    df['procent_wykorzystania'] = (df['srednie_oblozenie'] / df['pojemnosc'] * 100).round(2)
    return df

def load_class_satisfaction(db, gender=None, start_date=None, end_date=None, years=None):
    where_clauses = ["1=1"]
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
        
    where_str = " AND ".join(where_clauses)

    query = text(f"""
        SELECT 
            z.nazwa_zajec,
            AVG(uz.ocena_zajec) as srednia_ocena,
            SUM(uz.liczba_uczestnikow) as suma_uczestnikow
        FROM fitness_dw.uczestnictwo_zajec uz
        JOIN fitness_dw.zajecia z ON uz.zajecie_id = z.id
        JOIN fitness_dw.daty d ON uz.data_id = d.id
        JOIN fitness_dw.klienci k ON uz.klient_id = k.id
        WHERE {where_str}
        GROUP BY z.nazwa_zajec
        ORDER BY suma_uczestnikow DESC
    """)
    return pd.read_sql(query, db.bind)

def load_city_ltv(db, gender=None, start_date=None, end_date=None, years=None):
    where_clauses = ["1=1"]
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
        
    where_str = " AND ".join(where_clauses)
    
    query = text(f"""
        SELECT 
            a.miasto,
            COUNT(DISTINCT k.id) as liczba_klientow,
            SUM(p.kwota) as suma_wplat,
            ROUND(AVG(p.kwota), 2) as srednia_wplata
        FROM fitness_dw.klienci k
        JOIN fitness_dw.adresy a ON k.adres_id = a.id
        JOIN fitness_dw.platnosci p ON k.id = p.klient_id
        JOIN fitness_dw.daty d ON p.data_id = d.id
        WHERE {where_str}
        GROUP BY a.miasto
        ORDER BY suma_wplat DESC
    """)
    return pd.read_sql(query, db.bind)

def load_payment_methods(db, gender=None, start_date=None, end_date=None, years=None):
    where_clauses = ["1=1"]
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
        
    where_str = " AND ".join(where_clauses)
    
    query = text(f"""
        SELECT metoda_platnosci, COUNT(*) as liczba, SUM(kwota) as suma
        FROM fitness_dw.platnosci p
        JOIN fitness_dw.klienci k ON p.klient_id = k.id
        JOIN fitness_dw.daty d ON p.data_id = d.id
        WHERE {where_str}
        GROUP BY metoda_platnosci
    """)
    return pd.read_sql(query, db.bind)

def load_monthly_revenue(db, gender=None, start_date=None, end_date=None, years=None):
    where_clauses = ["1=1"]
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
        
    where_str = " AND ".join(where_clauses)
    
    query = text(f"""
        SELECT d.rok, d.miesiac, SUM(p.kwota) as suma_wplat
        FROM fitness_dw.platnosci p
        JOIN fitness_dw.klienci k ON p.klient_id = k.id
        JOIN fitness_dw.daty d ON p.data_id = d.id
        WHERE {where_str}
        GROUP BY d.rok, d.miesiac
        ORDER BY d.rok, d.miesiac
    """)
    df = pd.read_sql(query, db.bind)
    if not df.empty:
        df['data'] = df.apply(lambda row: f"{int(row['rok'])}-{int(row['miesiac']):02d}", axis=1)
    return df

def load_correlation_matrix(db):
    query = text("""
        SELECT 
            EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) as wiek,
            EXTRACT(HOUR FROM w.data_wejscia) as godzina,
            EXTRACT(DOW FROM w.data_wejscia) as dzien_tyg,
            w.czas_pobytu_min as czas_pobytu
        FROM fitness_dw.wejscia w
        JOIN fitness_dw.klienci k ON w.klient_id = k.id
    """)
    df = pd.read_sql(query, db.bind)
    return df.corr()

def load_rotated_attendance(db, rooms=None, start_date=None, end_date=None, pivot="Miesiąc", gender=None, years=None):
    where_clauses = ["1=1"]
    if rooms:
        where_clauses.append(f"s.numer_sali IN ({','.join([f'\'{r}\'' for r in rooms])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    
    where_str = " AND ".join(where_clauses)
    
    if pivot == "Miesiąc":
        group_by = "d.rok, d.miesiac"
        select_cols = "d.rok, d.miesiac, COUNT(w.id) as liczba_wejsc"
    elif pivot == "Dzień Tygodnia":
        group_by = "d.dzien_tygodnia"
        select_cols = "d.dzien_tygodnia as label, COUNT(w.id) as liczba_wejsc"
    else: # Specjalizacja
        query = text(f"""
            SELECT sp.nazwa as label, COUNT(uz.id) as liczba_wejsc
            FROM fitness_dw.uczestnictwo_zajec uz
            JOIN fitness_dw.trenerzy t ON uz.trener_id = t.id
            JOIN fitness_dw.specjalizacje sp ON t.specjalizacja_id = sp.id
            JOIN fitness_dw.daty d ON uz.data_id = d.id
            JOIN fitness_dw.sale s ON uz.sala_id = s.id
            JOIN fitness_dw.klienci k ON uz.klient_id = k.id
            WHERE {where_str}
            GROUP BY sp.nazwa
        """)
        return pd.read_sql(query, db.bind)

    query = text(f"""
        SELECT {select_cols}
        FROM fitness_dw.wejscia w
        JOIN fitness_dw.daty d ON w.data_id = d.id
        JOIN fitness_dw.sale s ON w.sala_id = s.id
        JOIN fitness_dw.klienci k ON w.klient_id = k.id
        WHERE {where_str}
        GROUP BY {group_by}
        ORDER BY {group_by}
    """)
    df = pd.read_sql(query, db.bind)
    if pivot == "Miesiąc" and not df.empty:
        df['label'] = df.apply(lambda row: f"{int(row['rok'])}-{int(row['miesiac']):02d}", axis=1)
    return df

def load_trainer_performance(db, rooms=None, gender=None, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if rooms:
        where_clauses.append(f"s.numer_sali IN ({','.join([f'\'{r}\'' for r in rooms])})")
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
        
    where_str = " AND ".join(where_clauses)
        
    query = text(f"""
        SELECT t.imie || ' ' || t.nazwisko AS imie_nazwisko_trenera, sp.nazwa AS specjalizacja, 
               COUNT(uz.id) AS liczba_prowadzonych_zajec, 
               AVG(uz.ocena_zajec) AS srednia_ocena_zajec, 
               SUM(uz.liczba_uczestnikow) AS suma_uczestnikow
        FROM fitness_dw.trenerzy t
        JOIN fitness_dw.specjalizacje sp ON t.specjalizacja_id = sp.id
        JOIN fitness_dw.uczestnictwo_zajec uz ON t.id = uz.trener_id
        JOIN fitness_dw.sale s ON uz.sala_id = s.id
        JOIN fitness_dw.klienci k ON uz.klient_id = k.id
        JOIN fitness_dw.daty d ON uz.data_id = d.id
        WHERE {where_str}
        GROUP BY t.id, t.imie, t.nazwisko, sp.nazwa
        ORDER BY srednia_ocena_zajec DESC
    """)
    return pd.read_sql(query, db.bind)

def load_segmentation_summary(db, gender=None, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
    
    where_str = " AND ".join(where_clauses)
    
    query = text(f"""
        WITH ostatnia_aktywnosc AS (
            SELECT 
                k.id as klient_id,
                MAX(d.data_pelna) as ostatnia_wizyta,
                COUNT(w.id) as liczba_wizyt,
                CURRENT_DATE - MAX(d.data_pelna) as dni_od_ostatniej_wizyty
            FROM fitness_dw.klienci k
            LEFT JOIN fitness_dw.wejscia w ON k.id = w.klient_id
            LEFT JOIN fitness_dw.daty d ON w.data_id = d.id
            WHERE {where_str}
            GROUP BY k.id
        ),
        segmentacja AS (
            SELECT 
                CASE 
                    WHEN dni_od_ostatniej_wizyty <= 30 AND liczba_wizyt >= 10 THEN 'Aktywni Premium'
                    WHEN dni_od_ostatniej_wizyty <= 30 AND liczba_wizyt >= 5 THEN 'Aktywni Regularni'
                    WHEN dni_od_ostatniej_wizyty <= 60 AND liczba_wizyt >= 3 THEN 'Aktywni Okazjonalni'
                    WHEN dni_od_ostatniej_wizyty > 60 AND liczba_wizyt >= 5 THEN 'Uśpieni'
                    WHEN dni_od_ostatniej_wizyty > 90 OR dni_od_ostatniej_wizyty IS NULL THEN 'Nieaktywni'
                    ELSE 'Nowi'
                END as segment_klienta
            FROM ostatnia_aktywnosc
        )
        SELECT 
            segment_klienta,
            COUNT(*) as liczba_klientow
        FROM segmentacja
        GROUP BY segment_klienta
        ORDER BY liczba_klientow DESC
    """)
    return pd.read_sql(query, db.bind)

def load_customer_retention(db, gender=None, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
        
    where_str = " AND ".join(where_clauses)
    
    query = text(f"""
        WITH retencja_miesieczna AS (
            SELECT 
                d.rok,
                d.miesiac,
                COUNT(DISTINCT k.id) as klienci_miesiac
            FROM fitness_dw.wejscia w
            JOIN fitness_dw.klienci k ON w.klient_id = k.id
            JOIN fitness_dw.daty d ON w.data_id = d.id
            WHERE {where_str}
            GROUP BY d.rok, d.miesiac
        )
        SELECT 
            rok,
            miesiac,
            klienci_miesiac
        FROM retencja_miesieczna
        ORDER BY rok, miesiac
    """)
    df = pd.read_sql(query, db.bind)
    if not df.empty:
        df['data'] = df.apply(lambda row: f"{int(row['rok'])}-{int(row['miesiac']):02d}", axis=1)
    return df

def load_customer_ltv(db):
    query = text("""
        WITH clv_klientow AS (
            SELECT 
                k.imie || ' ' || k.nazwisko as klient,
                COUNT(w.id) as liczba_wizyt,
                AVG(w.czas_pobytu_min) as sredni_czas_pobytu,
                COUNT(DISTINCT d.miesiac) as liczba_miesiecy_aktywnych
            FROM fitness_dw.klienci k
            LEFT JOIN fitness_dw.wejscia w ON k.id = w.klient_id
            LEFT JOIN fitness_dw.daty d ON w.data_id = d.id
            GROUP BY k.id, k.imie, k.nazwisko
        )
        SELECT 
            klient,
            liczba_wizyt,
            ROUND((liczba_wizyt * sredni_czas_pobytu * 0.5) + (liczba_miesiecy_aktywnych * 10), 2) as clv_wartosc
        FROM clv_klientow
        ORDER BY clv_wartosc DESC
        LIMIT 10
    """)
    return pd.read_sql(query, db.bind)

def load_occupancy_heatmap(db, rooms=None, gender=None, date_range=None):
    where_clauses = ["1=1"]
    if rooms:
        where_clauses.append(f"s.numer_sali IN ({','.join([f'\'{r}\'' for r in rooms])})")
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if date_range:
        where_clauses.append(f"d.data_pelna BETWEEN '{date_range[0]}' AND '{date_range[1]}'")
        
    where_str = " AND ".join(where_clauses)
        
    query = text(f"""
        SELECT 
            d.dzien_tygodnia,
            EXTRACT(HOUR FROM w.data_wejscia) as godzina,
            COUNT(*) as liczba_wejsc
        FROM fitness_dw.wejscia w
        JOIN fitness_dw.daty d ON w.data_id = d.id
        JOIN fitness_dw.sale s ON w.sala_id = s.id
        JOIN fitness_dw.klienci k ON w.klient_id = k.id
        WHERE {where_str}
        GROUP BY d.dzien_tygodnia, godzina
    """)
    df = pd.read_sql(query, db.bind)
    if df.empty: return pd.DataFrame()
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['dzien_tygodnia'] = pd.Categorical(df['dzien_tygodnia'], categories=days_order, ordered=True)
    pivot = df.pivot(index='dzien_tygodnia', columns='godzina', values='liczba_wejsc').fillna(0)
    return pivot

def load_ml_data(db, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
        
    where_str = " AND ".join(where_clauses)
    
    query = text(f"""
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
        JOIN client_history ch ON w.klient_id = ch.klient_id AND w.id = w.id -- dummy join for row matching
        WHERE {where_str}
        LIMIT 10000
    """)
    return pd.read_sql(query, db.bind)

def load_correlation_matrix(db, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
        
    where_str = " AND ".join(where_clauses)

    query = text(f"""
        SELECT 
            EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) as wiek,
            EXTRACT(HOUR FROM w.data_wejscia) as godzina,
            EXTRACT(DOW FROM w.data_wejscia) as dzien_tyg,
            w.czas_pobytu_min as czas_pobytu
        FROM fitness_dw.wejscia w
        JOIN fitness_dw.klienci k ON w.klient_id = k.id
        JOIN fitness_dw.daty d ON w.data_id = d.id
        WHERE {where_str}
    """)
    df = pd.read_sql(query, db.bind)
    return df.corr()

def load_demographics(db, years=None, start_date=None, end_date=None, active_only=True):
    if active_only:
        where_clauses = ["1=1"]
        if years:
            where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
        if start_date and end_date:
            where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")
        where_str = " AND ".join(where_clauses)

        query = text(f"""
            SELECT 
                k.plec,
                CASE 
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) < 20 THEN ' < 20'
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) BETWEEN 20 AND 30 THEN '20-30'
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) BETWEEN 30 AND 45 THEN '30-45'
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) BETWEEN 45 AND 60 THEN '45-60'
                    ELSE '60+'
                END as grupa_wiekowa,
                COUNT(DISTINCT k.id) as liczba
            FROM fitness_dw.klienci k
            WHERE EXISTS (
                SELECT 1
                FROM fitness_dw.wejscia w
                JOIN fitness_dw.daty d ON w.data_id = d.id
                WHERE w.klient_id = k.id
                AND {where_str}
            )
            GROUP BY k.plec, grupa_wiekowa
            ORDER BY grupa_wiekowa
        """)
        return pd.read_sql(query, db.bind)

    query = text("""
        SELECT 
            k.plec,
            CASE 
                WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) < 20 THEN ' < 20'
                WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) BETWEEN 20 AND 30 THEN '20-30'
                WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) BETWEEN 30 AND 45 THEN '30-45'
                WHEN EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM k.data_urodzenia) BETWEEN 45 AND 60 THEN '45-60'
                ELSE '60+'
            END as grupa_wiekowa,
            COUNT(DISTINCT k.id) as liczba
        FROM fitness_dw.klienci k
        GROUP BY k.plec, grupa_wiekowa
        ORDER BY grupa_wiekowa
    """)
    return pd.read_sql(query, db.bind)

def load_rollup_revenue(db, gender=None, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")

    where_str = " AND ".join(where_clauses)

    query = text(f"""
        SELECT
            d.rok,
            d.miesiac,
            SUM(p.kwota) as suma_wplat,
            GROUPING(d.rok) as g_rok,
            GROUPING(d.miesiac) as g_miesiac
        FROM fitness_dw.platnosci p
        JOIN fitness_dw.daty d ON p.data_id = d.id
        JOIN fitness_dw.klienci k ON p.klient_id = k.id
        WHERE {where_str}
        GROUP BY ROLLUP(d.rok, d.miesiac)
        ORDER BY d.rok NULLS LAST, d.miesiac NULLS LAST
    """)
    return pd.read_sql(query, db.bind)

def load_cube_attendance(db, rooms=None, gender=None, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if rooms:
        rooms_sql = ",".join([f"'{r}'" for r in rooms])
        where_clauses.append(f"s.numer_sali IN ({rooms_sql})")
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")

    where_str = " AND ".join(where_clauses)

    query = text(f"""
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
        WHERE {where_str}
        GROUP BY CUBE(k.plec, d.dzien_tygodnia)
        ORDER BY k.plec NULLS LAST, d.dzien_tygodnia NULLS LAST
    """)
    return pd.read_sql(query, db.bind)

def load_grouping_sets_participation(db, rooms=None, gender=None, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if rooms:
        rooms_sql = ",".join([f"'{r}'" for r in rooms])
        where_clauses.append(f"s.numer_sali IN ({rooms_sql})")
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")

    where_str = " AND ".join(where_clauses)

    query = text(f"""
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
        WHERE {where_str}
        GROUP BY GROUPING SETS (
            (sp.nazwa, d.rok, d.miesiac),
            (sp.nazwa, d.rok),
            (d.rok),
            ()
        )
        ORDER BY sp.nazwa NULLS LAST, d.rok NULLS LAST, d.miesiac NULLS LAST
    """)
    return pd.read_sql(query, db.bind)

def load_rollup_attendance_room_month(db, rooms=None, gender=None, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if rooms:
        rooms_sql = ",".join([f"'{r}'" for r in rooms])
        where_clauses.append(f"s.numer_sali IN ({rooms_sql})")
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")

    where_str = " AND ".join(where_clauses)

    query = text(f"""
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
        WHERE {where_str}
        GROUP BY ROLLUP(s.numer_sali, d.rok, d.miesiac)
        ORDER BY s.numer_sali NULLS LAST, d.rok NULLS LAST, d.miesiac NULLS LAST
    """)
    return pd.read_sql(query, db.bind)

def load_cube_payments_method_gender(db, gender=None, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")

    where_str = " AND ".join(where_clauses)

    query = text(f"""
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
        WHERE {where_str}
        GROUP BY CUBE(p.metoda_platnosci, k.plec)
        ORDER BY p.metoda_platnosci NULLS LAST, k.plec NULLS LAST
    """)
    return pd.read_sql(query, db.bind)

def load_grouping_sets_revenue_time_method(db, gender=None, years=None, start_date=None, end_date=None):
    where_clauses = ["1=1"]
    if gender and gender != "Wszystko":
        where_clauses.append(f"k.plec = '{gender}'")
    if years:
        where_clauses.append(f"d.rok IN ({','.join([str(y) for y in years])})")
    if start_date and end_date:
        where_clauses.append(f"d.data_pelna BETWEEN '{start_date}' AND '{end_date}'")

    where_str = " AND ".join(where_clauses)

    query = text(f"""
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
        WHERE {where_str}
        GROUP BY GROUPING SETS (
            (d.rok, d.miesiac, p.metoda_platnosci),
            (d.rok, p.metoda_platnosci),
            (d.rok, d.miesiac),
            (p.metoda_platnosci),
            ()
        )
        ORDER BY d.rok NULLS LAST, d.miesiac NULLS LAST, p.metoda_platnosci NULLS LAST
    """)
    return pd.read_sql(query, db.bind)

def main():
    st.markdown('<div class="main-header">🏋️‍♂️ Fitness HD Analytics Professional</div>', unsafe_allow_html=True)

    db = get_db()
    
    # --- Sidebar Filtering (OLAP: Selection / Slicing) ---
    st.sidebar.markdown("### 🛠 Globalne Filtry")
    
    # 1. Date range (Separate Calendars)
    date_query = text("SELECT MIN(data_pelna), MAX(data_pelna) FROM fitness_dw.daty")
    date_range_res = db.execute(date_query).fetchone()
    min_db_date, max_db_date = date_range_res[0], date_range_res[1]
    
    import datetime
    default_start = max_db_date - datetime.timedelta(days=180)
    if default_start < min_db_date: default_start = min_db_date

    col_d1, col_d2 = st.sidebar.columns(2)
    with col_d1:
        start_date = st.date_input("Od", value=default_start, min_value=min_db_date, max_value=max_db_date)
    with col_d2:
        end_date = st.date_input("Do", value=max_db_date, min_value=min_db_date, max_value=max_db_date)
    
    # Validation: Ensure end_date is not before start_date
    if start_date > end_date:
        st.sidebar.error("Błąd: Data 'Od' musi być przed 'Do'.")
        # Graceful fallback to prevent SQL errors
        end_date = start_date

    # 2. Year filter
    years_query = text("SELECT DISTINCT rok FROM fitness_dw.daty ORDER BY rok DESC")
    all_years = [str(r[0]) for r in db.execute(years_query).fetchall()]
    
    # 3. Room selection
    rooms_query = text("SELECT DISTINCT numer_sali FROM fitness_dw.sale ORDER BY numer_sali")
    all_rooms = [r[0] for r in db.execute(rooms_query).fetchall()]

    col_f1, col_f2 = st.sidebar.columns(2)
    with col_f1:
        if st.button("Reset Lat"):
            st.session_state.ms_years = all_years
            st.rerun()
    with col_f2:
        if st.button("Reset Sal"):
            st.session_state.ms_rooms = all_rooms
            st.rerun()

    selected_years = st.sidebar.multiselect(
        "Lata (Filtr roczny)", 
        all_years, 
        default=all_years,
        key='ms_years'
    )
        
    selected_rooms = st.sidebar.multiselect(
        "Filtruj po salach", 
        all_rooms, 
        default=all_rooms,
        key='ms_rooms'
    )
    
    # 4. Gender filter
    gender_filter = st.sidebar.radio("Płeć klientów", ["Wszystko", "M", "K"], index=0)
    
    st.sidebar.divider()
    
    # --- Pivot / Rotation Configuration (OLAP) ---
    st.sidebar.markdown("### 🔄 Obrót Osi (Rotation)")
    pivot_option = st.sidebar.selectbox(
        "Grupowanie na wykresie",
        ["Miesiąc", "Dzień Tygodnia", "Specjalizacja"],
        index=0
    )
    
    # --- Applying filters to UI components ---
    stats = load_dashboard_stats(db, rooms=selected_rooms, start_date=start_date, end_date=end_date, gender=gender_filter, years=selected_years)

    if stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Liczba wejść (Wybrany zakres)", stats["frekwencja"], 
                      help="Całkowita liczba fizycznych wejść do klubu w wybranym oknie czasowym.")
        with col2:
            st.metric("Średnia ocena zajęć", f"{stats['ocena']} / 5.0",
                      help="Średnia ocena wystawiana przez klientów po zajęciach grupowych.")
        with col3:
            st.metric("Przychód (Płatności)", f"{stats['przychod']} PLN",
                      help="Suma wpłat zarejestrowanych w tabeli faktów Płatności.")

    st.divider()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📈 Frekwencja", "👨‍🏫 Trenerzy", "🔍 Segmentacja", 
        "🕒 Obłożenie", "🤖 ML Predykcje", "🏢 Sale i Zajęcia",
        "💸 Biznes", "🧬 Korelacje", "📝 Transakcje", "🧊 ROLLUP/CUBE"
    ])

    with tab1:
        st.write(f"### Analiza Trendów (Obrót: {pivot_option})")
        df_rot = load_rotated_attendance(db, rooms=selected_rooms, start_date=start_date, end_date=end_date, pivot=pivot_option, gender=gender_filter, years=selected_years)
        
        if not df_rot.empty:
            st.markdown("---")
            col_dd1, col_dd2 = st.columns([1, 3])
            with col_dd1:
                st.write("#### 🔍 Drill-down (Zwijanie/Rozwijanie)")
                detail_level = st.radio("Poziom szczegółowości", ["Ogólny (Wybrany obrót)", "Szczegółowy (Dni miesiąca)"], key="dd_level")
            
            if detail_level == "Szczegółowy (Dni miesiąca)" and pivot_option == "Miesiąc":
                selected_month = st.selectbox("Wybierz miesiąc do analizy szczegółowej", df_rot['label'].tolist())
                y_m = selected_month.split('-')
                query_dd = text(f"""
                    SELECT d.dzien, COUNT(w.id) as liczba_wejsc
                    FROM fitness_dw.wejscia w
                    JOIN fitness_dw.daty d ON w.data_id = d.id
                    WHERE d.rok = {y_m[0]} AND d.miesiac = {int(y_m[1])}
                    GROUP BY d.dzien ORDER BY d.dzien
                """)
                df_dd = pd.read_sql(query_dd, db.bind)
                fig_dd = px.line(df_dd, x='dzien', y='liczba_wejsc', title=f'Szczegóły dla {selected_month}', markers=True)
                st.plotly_chart(fig_dd, width='stretch')
            else:
                fig = px.bar(df_rot, x='label', y='liczba_wejsc', 
                            title=f'Wejścia wg {pivot_option}',
                            color='liczba_wejsc')
                st.plotly_chart(fig, width='stretch')
            
            st.write("#### Szczegółowy trend miesięczny")
            df_trend = load_rotated_attendance(db, rooms=selected_rooms, start_date=start_date, end_date=end_date, pivot="Miesiąc", gender=gender_filter, years=selected_years)
            fig_t = px.line(df_trend, x='label', y='liczba_wejsc', markers=True, title="Trend czasowy")
            st.plotly_chart(fig_t, width='stretch')
            
            st.download_button("Export Trend CSV", df_rot.to_csv(index=False), "trend_data.csv", "text/csv")
        else:
            st.info("Brak danych dla wybranych filtrów.")

    with tab2:
        st.write("### Efektywność Trenerów")
        df_trainers = load_trainer_performance(db, rooms=selected_rooms, gender=gender_filter, years=selected_years, start_date=start_date, end_date=end_date)
        if not df_trainers.empty:
            fig = px.scatter(df_trainers, x='liczba_prowadzonych_zajec', y='srednia_ocena_zajec',
                            size='suma_uczestnikow', color='specjalizacja',
                            hover_name='imie_nazwisko_trenera',
                            title='Analiza Trenerów: Ocena vs Liczba Zajęć')
            st.plotly_chart(fig, width='stretch')
            st.dataframe(df_trainers, width='stretch')
            st.download_button("Export Trainer Stats CSV", df_trainers.to_csv(index=False), "trainer_performance.csv", "text/csv")

    with tab3:
        st.write("### Segmentacja i Retencja (Globalne)")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            # Segmentacja based on all time/filters
            df_seg = load_segmentation_summary(db, gender=gender_filter, years=selected_years, start_date=start_date, end_date=end_date)
            if not df_seg.empty:
                fig_seg = px.pie(df_seg, values='liczba_klientow', names='segment_klienta', 
                                title='Udział segmentów', hole=0.5)
                st.plotly_chart(fig_seg, width='stretch')
        with col_s2:
            df_ret = load_customer_retention(db, gender=gender_filter, years=selected_years, start_date=start_date, end_date=end_date)
            if not df_ret.empty:
                fig_ret = px.area(df_ret, x='data', y='klienci_miesiac',
                                 title='Liczba aktywnych klientów MoM', color_discrete_sequence=['#673ab7'])
                st.plotly_chart(fig_ret, width='stretch')

    with tab4:
        st.write("### Godziny Szczytu (Heatmap)")
        df_heat = load_occupancy_heatmap(db, rooms=selected_rooms, gender=gender_filter, date_range=(start_date, end_date))
        if not df_heat.empty:
            fig_heat = px.imshow(df_heat, x=df_heat.columns, y=df_heat.index,
                                color_continuous_scale='Magma', title='Obłożenie godzinowe vs Dzień')
            st.plotly_chart(fig_heat, width='stretch')
        else:
            st.info("Brak danych dla wybranych filtrów.")

    with tab5:
        st.write("### Machine Learning: Predykcja Czasu Pobytu")
        df_ml = load_ml_data(db, start_date=start_date, end_date=end_date, years=selected_years)
        if not df_ml.empty and len(df_ml) > 100:
            if gender_filter != "Wszystko":
                df_ml = df_ml[df_ml['plec_bin'] == (1 if gender_filter == "M" else 0)]
            
            features = ['wiek', 'plec_bin', 'godzina', 'dzien_tyg', 'miesiac', 'is_weekend', 'total_prev_visits']
            X = df_ml[features]
            y = df_ml['target']
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Using Random Forest with more depth for better capture of non-linear patterns
            model = RandomForestRegressor(n_estimators=150, max_depth=10, random_state=42)
            model.fit(X_train, y_train)
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("#### Kalkulator Czasu")
                i_wiek = st.number_input("Wiek", 15, 90, 30, key='ml_age')
                i_plec = st.radio("Płeć", ["M", "K"], index=(0 if gender_filter!="K" else 1), horizontal=True, key='ml_gender')
                i_godz = st.slider("Godzina", 6, 23, 18, key='ml_hour')
                i_dz = st.selectbox("Dzień tyg", ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nie"], key='ml_day')
                i_ms = st.slider("Miesiąc", 1, 12, 1, key='ml_month')
                i_loyalty = st.number_input("Liczba dotychczasowych wizyt", 0, 500, 10, key='ml_loyalty')
                
                days_m = {"Pon":0, "Wt":1, "Śr":2, "Czw":3, "Pt":4, "Sob":5, "Nie":6}
                is_we = 1 if i_dz in ["Sob", "Nie"] else 0
                
                input_data = pd.DataFrame([[i_wiek, 1 if i_plec=="M" else 0, i_godz, days_m[i_dz], i_ms, is_we, i_loyalty]], 
                                          columns=features)
                pred = model.predict(input_data)[0]
                st.metric("Przewidywany czas (min)", int(pred))

            with c2:
                st.write("#### Jakość Modelu i Ważność Cech")
                mae = mean_absolute_error(y_test, model.predict(X_test))
                st.info(f"MAE (Średni błąd): {round(mae, 2)} min")
                
                # Feature importance chart
                importances = pd.DataFrame({'cecha': features, 'waga': model.feature_importances_}).sort_values('waga', ascending=False)
                fig_imp = px.bar(importances, x='waga', y='cecha', orientation='h', title="Wpływ cech na czas pobytu")
                st.plotly_chart(fig_imp, width='stretch')
                st.write(f"Model wytrenowany na wycinku danych ({len(df_ml)} rekordów).")
        else:
            st.info("Zbyt mało danych dla wybranych filtrów, by wytrenować zaawansowany model.")

    with tab6:
        st.write("### Wykorzystanie Sal i Popularność Zajęć")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            df_room = load_room_occupancy_vs_capacity(db, gender=gender_filter, start_date=start_date, end_date=end_date, years=selected_years)
            fig_room = px.bar(df_room, x='numer_sali', y='procent_wykorzystania',
                             title='% Wykorzystania Pojemności Sal', color='procent_wykorzystania',
                             color_continuous_scale='YlOrRd')
            st.plotly_chart(fig_room, width='stretch')
        with col_r2:
            df_class = load_class_satisfaction(db, gender=gender_filter, start_date=start_date, end_date=end_date, years=selected_years)
            if not df_class.empty:
                fig_class = px.scatter(df_class, x='suma_uczestnikow', y='srednia_ocena',
                                      text='nazwa_zajec', size='suma_uczestnikow',
                                      title='Satysfakcja vs Popularność Zajęć')
                st.plotly_chart(fig_class, width='stretch')
            else:
                st.info("Brak danych o zajęciach dla filtrów.")

    with tab7:
        st.write("### Analityka Finansowa i Biznesowa (3. Tabela Faktów)")
        
        # New Monthly Revenue Trend
        st.write("#### Trend Przychodu Miesięcznego (MoM)")
        df_monthly = load_monthly_revenue(db, gender=gender_filter, start_date=start_date, end_date=end_date, years=selected_years)
        if not df_monthly.empty:
            fig_monthly = px.area(df_monthly, x='data', y='suma_wplat', 
                                title='Suma wpłat w czasie',
                                labels={'suma_wplat': 'Suma wpłat (PLN)', 'data': 'Miesiąc'},
                                color_discrete_sequence=['#4caf50'])
            st.plotly_chart(fig_monthly, width='stretch')
        
        col_b1, col_b2 = st.columns(2)
        
        with col_b1:
            df_city = load_city_ltv(db, gender=gender_filter, start_date=start_date, end_date=end_date, years=selected_years)
            if not df_city.empty:
                fig_city = px.bar(
                    df_city,
                    x='miasto',
                    y='suma_wplat',
                    color='miasto',
                    title='Suma wpłat wg Miast',
                    labels={'suma_wplat': 'Przychód (PLN)', 'miasto': 'Miasto'},
                    hover_data={'srednia_wplata': True, 'liczba_klientow': True}
                )
                fig_city.update_layout(showlegend=False)
                st.plotly_chart(fig_city, width='stretch')
            else:
                st.info("Brak danych finansowych dla wybranych filtrów.")

        with col_b2:
            df_pay = load_payment_methods(db, gender=gender_filter, start_date=start_date, end_date=end_date, years=selected_years)
            if not df_pay.empty:
                fig_pay = px.pie(df_pay, values='suma', names='metoda_platnosci',
                                title='Udział Metod Płatności', hole=0.4)
                st.plotly_chart(fig_pay, width='stretch')
        
        st.write("#### Szczegółowy podgląd")
        st.dataframe(df_city, width='stretch')

    with tab8:
        st.write("### DNA Hurtowni: Macierz Korelacji")
        st.write("Zależności statystyczne między atrybutami wejść.")
        corr = load_correlation_matrix(db, years=selected_years, start_date=start_date, end_date=end_date)
        if not corr.empty:
            fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r', 
                                aspect='auto', title='Korelacja parametrów wejścia')
            st.plotly_chart(fig_corr, width='stretch')
        
        st.divider()
        st.write("### Rozkład Wiekowy (Demografia)")
        demo_mode = st.radio(
            "Populacja",
            ["Aktywni w wybranym okresie", "Wszyscy klienci"],
            horizontal=True,
            key="demo_mode"
        )
        df_demo = load_demographics(
            db,
            years=selected_years,
            start_date=start_date,
            end_date=end_date,
            active_only=(demo_mode == "Aktywni w wybranym okresie")
        )
        if not df_demo.empty:
            if gender_filter != "Wszystko":
                df_demo = df_demo[df_demo['plec'] == gender_filter]
                
            fig_demo = px.bar(df_demo, x='grupa_wiekowa', y='liczba', color='plec', 
                             barmode='group', color_discrete_map={'M':'#1a73e8', 'K':'#e91e63'})
            st.plotly_chart(fig_demo, width='stretch')
        else:
            st.info("Brak danych demograficznych dla filtrów.")

    with tab9:
        st.write("### Rejestracja Nowych Danych (Transakcje)")
        t_col1, t_col2 = st.columns(2)
        
        with t_col1:
            st.markdown("#### 👤 Dodaj Klienta")
            with st.form("new_client_form"):
                f_imie = st.text_input("Imię")
                f_nazwisko = st.text_input("Nazwisko")
                f_plec = st.selectbox("Płeć", ["M", "K"])
                f_urodz = st.date_input("Data urodzenia", min_value=datetime.date(1950, 1, 1))
                
                # Fetch address IDs for selection simplified
                addr_query = text("SELECT id, miasto, ulica FROM fitness_dw.adresy LIMIT 10")
                addresses = db.execute(addr_query).fetchall()
                f_addr = st.selectbox("Adres", options=[a[0] for a in addresses], 
                                     format_func=lambda x: next(f"{a[1]}, {a[2]}" for a in addresses if a[0] == x))
                
                if st.form_submit_button("Zapisz Klienta"):
                    if db_create_klient(db, {"imie": f_imie, "nazwisko": f_nazwisko, "plec": f_plec, 
                                            "data_urodzenia": f_urodz, "adres_id": f_addr}):
                        st.success("Dodano klienta!")
        
        with t_col2:
            st.markdown("#### 🚪 Zarejestruj Wejście")
            with st.form("new_entry_form"):
                cli_query = text("SELECT id, imie, nazwisko FROM fitness_dw.klienci ORDER BY nazwisko LIMIT 100")
                clients = db.execute(cli_query).fetchall()
                f_klient = st.selectbox("Klient", options=[c[0] for c in clients],
                                       format_func=lambda x: next(f"{c[1]} {c[2]}" for c in clients if c[0] == x))
                
                room_query = text("SELECT id, numer_sali FROM fitness_dw.sale")
                rooms = db.execute(room_query).fetchall()
                f_room = st.selectbox("Sala", options=[r[0] for r in rooms], 
                                     format_func=lambda x: next(r[1] for r in rooms if r[0] == x))
                
                f_date = st.date_input("Data wejścia")
                f_time = st.time_input("Godzina wejścia")
                f_duration = st.number_input("Czas pobytu (min)", 1, 480, 60)
                
                if st.form_submit_button("Zapisz Wejście"):
                    # Find date_id or create if missing? Simplified: assuming current date range loaded
                    d_query = text("SELECT id FROM fitness_dw.daty WHERE data_pelna = :d")
                    d_res = db.execute(d_query, {"d": f_date}).fetchone()
                    if d_res:
                        dt_full = datetime.datetime.combine(f_date, f_time)
                        if db_create_wejscie(db, {"klient_id": f_klient, "sala_id": f_room, 
                                                 "data_id": d_res[0], "czas_pobytu_min": f_duration, 
                                                 "data_wejscia": dt_full}):
                            st.success("Zarejestrowano wejście!")
                    else:
                        st.error("Błąd: Data musi istnieć w wymiarze Daty (zakładka ETL).")

    with tab10:
        st.write("### Zaawansowane agregacje: ROLLUP / CUBE / GROUPING SETS")

        show_grouping_flags = st.checkbox("Pokaż kolumny GROUPING (g_*)", value=False)

        st.write("#### ROLLUP: Przychód (rok → miesiąc → suma)")
        df_rollup = load_rollup_revenue(db, gender=gender_filter, years=selected_years, start_date=start_date, end_date=end_date)
        if not show_grouping_flags:
            df_rollup = df_rollup.loc[:, [c for c in df_rollup.columns if not c.startswith('g_')]]
        st.dataframe(df_rollup, width='stretch')
        st.download_button("Export ROLLUP CSV", df_rollup.to_csv(index=False), "rollup_revenue.csv", "text/csv")

        st.write("#### ROLLUP: Frekwencja (sala → rok → miesiąc → suma)")
        df_rollup2 = load_rollup_attendance_room_month(db, rooms=selected_rooms, gender=gender_filter, years=selected_years, start_date=start_date, end_date=end_date)
        if not show_grouping_flags:
            df_rollup2 = df_rollup2.loc[:, [c for c in df_rollup2.columns if not c.startswith('g_')]]
        st.dataframe(df_rollup2, width='stretch')
        st.download_button("Export ROLLUP 2 CSV", df_rollup2.to_csv(index=False), "rollup_attendance_room_month.csv", "text/csv")

        st.write("#### CUBE: Frekwencja wg płci i dnia tygodnia (+ sumy częściowe)")
        df_cube = load_cube_attendance(db, rooms=selected_rooms, gender=gender_filter, years=selected_years, start_date=start_date, end_date=end_date)
        if not show_grouping_flags:
            df_cube = df_cube.loc[:, [c for c in df_cube.columns if not c.startswith('g_')]]
        st.dataframe(df_cube, width='stretch')
        st.download_button("Export CUBE CSV", df_cube.to_csv(index=False), "cube_attendance.csv", "text/csv")

        st.write("#### CUBE: Płatności wg metody i płci (+ sumy częściowe)")
        df_cube2 = load_cube_payments_method_gender(db, gender=gender_filter, years=selected_years, start_date=start_date, end_date=end_date)
        if not show_grouping_flags:
            df_cube2 = df_cube2.loc[:, [c for c in df_cube2.columns if not c.startswith('g_')]]
        st.dataframe(df_cube2, width='stretch')
        st.download_button("Export CUBE 2 CSV", df_cube2.to_csv(index=False), "cube_payments_method_gender.csv", "text/csv")

        st.write("#### GROUPING SETS: Uczestnictwo w zajęciach (specjalizacja / rok / miesiąc + sumy)")
        df_gs = load_grouping_sets_participation(db, rooms=selected_rooms, gender=gender_filter, years=selected_years, start_date=start_date, end_date=end_date)
        if not show_grouping_flags:
            df_gs = df_gs.loc[:, [c for c in df_gs.columns if not c.startswith('g_')]]
        st.dataframe(df_gs, width='stretch')
        st.download_button("Export GROUPING SETS CSV", df_gs.to_csv(index=False), "grouping_sets_participation.csv", "text/csv")

        st.write("#### GROUPING SETS: Przychód w czasie i wg metody (+ sumy)")
        df_gs2 = load_grouping_sets_revenue_time_method(db, gender=gender_filter, years=selected_years, start_date=start_date, end_date=end_date)
        if not show_grouping_flags:
            df_gs2 = df_gs2.loc[:, [c for c in df_gs2.columns if not c.startswith('g_')]]
        st.dataframe(df_gs2, width='stretch')
        st.download_button("Export GROUPING SETS 2 CSV", df_gs2.to_csv(index=False), "grouping_sets_revenue_time_method.csv", "text/csv")

    if st.sidebar.button("Odśwież dane"):
        st.rerun()

    st.sidebar.divider()

    with st.sidebar.expander("⚙️ Administracja (ETL)"):
        if st.button("Załaduj dane z CSV", help="Wczytuje dane z plików seed w database/seeds", key="btn_load_csv"):
            csv_s = CSVService(db)
            with st.spinner("Ładowanie danych..."):
                res = csv_s.load_all_csvs()
                st.success(res["message"])
                st.rerun()

        if st.button("Wyczyść wszystkie dane", help="CAŁKOWITE CZYSZCZENIE BAZY", key="btn_clear_all"):
            db.execute(text("TRUNCATE TABLE fitness_dw.platnosci CASCADE"))
            db.execute(text("TRUNCATE TABLE fitness_dw.uczestnictwo_zajec CASCADE"))
            db.execute(text("TRUNCATE TABLE fitness_dw.wejscia CASCADE"))
            db.execute(text("TRUNCATE TABLE fitness_dw.klienci CASCADE"))
            # Clear other tables if needed...
            db.commit()
            st.warning("Dane wyczyszczone.")
            st.rerun()

if __name__ == "__main__":
    main()
