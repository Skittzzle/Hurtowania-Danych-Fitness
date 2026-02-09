from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from ..database import get_db

router = APIRouter()

@router.get("/segmentacja-klientow", response_model=List[Dict[str, Any]])
def get_segmentacja_klientow(
    db: Session = Depends(get_db)
):
    """Segmentacja klientów według aktywności"""
    try:
        query = text("""
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
            SELECT 
                klient_id,
                imie,
                nazwisko,
                ostatnia_wizyta,
                liczba_wizyt,
                sredni_czas_pobytu,
                liczba_miesiecy_aktywnych,
                dni_od_ostatniej_wizyty,
                segment_klienta,
                czestotliwosc_wizyt,
                czas_wizyt
            FROM segmentacja
            ORDER BY liczba_wizyt DESC
        """)
        
        result = db.execute(query).fetchall()
        
        return [
            {
                "klient_id": row.klient_id,
                "imie": row.imie,
                "nazwisko": row.nazwisko,
                "ostatnia_wizyta": row.ostatnia_wizyta.isoformat() if row.ostatnia_wizyta else None,
                "liczba_wizyt": row.liczba_wizyt,
                "sredni_czas_pobytu": float(row.sredni_czas_pobytu) if row.sredni_czas_pobytu else 0,
                "liczba_miesiecy_aktywnych": row.liczba_miesiecy_aktywnych,
                "dni_od_ostatniej_wizyty": row.dni_od_ostatniej_wizyty,
                "segment_klienta": row.segment_klienta,
                "czestotliwosc_wizyt": row.czestotliwosc_wizyt,
                "czas_wizyt": row.czas_wizyt
            }
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get customer segmentation: {str(e)}")

@router.get("/segmentacja-podsumowanie", response_model=Dict[str, Any])
def get_segmentacja_podsumowanie(
    db: Session = Depends(get_db)
):
    """Podsumowanie segmentacji klientów"""
    try:
        query = text("""
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
            ORDER BY liczba_klientow DESC
        """)
        
        result = db.execute(query).fetchall()
        
        return {
            "segmenty": [
                {
                    "segment": row.segment_klienta,
                    "liczba_klientow": row.liczba_klientow,
                    "procent_klientow": float(row.procent_klientow)
                }
                for row in result
            ],
            "total_klientow": sum(row.liczba_klientow for row in result)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get segmentation summary: {str(e)}")

@router.get("/retencja-klientow", response_model=List[Dict[str, Any]])
def get_retencja_klientow(
    miesiecy: Optional[int] = Query(12, description="Liczba miesięcy analizy"),
    db: Session = Depends(get_db)
):
    """Analiza retencji klientów w czasie"""
    try:
        query = text("""
            WITH retencja_miesieczna AS (
                SELECT 
                    d.rok,
                    d.miesiac,
                    COUNT(DISTINCT k.id) as klienci_miesiac,
                    COUNT(DISTINCT CASE 
                        WHEN d.data_pelna >= CURRENT_DATE - INTERVAL '3 months' 
                        THEN k.id 
                    END) as klienci_aktywni_3m,
                    COUNT(DISTINCT CASE 
                        WHEN d.data_pelna >= CURRENT_DATE - INTERVAL '6 months' 
                        THEN k.id 
                    END) as klienci_aktywni_6m,
                    COUNT(DISTINCT CASE 
                        WHEN d.data_pelna >= CURRENT_DATE - INTERVAL '12 months' 
                        THEN k.id 
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
            ORDER BY rok DESC, miesiac DESC
        """)
        
        result = db.execute(query, {"miesiecy": miesiecy}).fetchall()
        
        return [
            {
                "rok": row.rok,
                "miesiac": row.miesiac,
                "klienci_miesiac": row.klienci_miesiac,
                "klienci_aktywni_3m": row.klienci_aktywni_3m,
                "klienci_aktywni_6m": row.klienci_aktywni_6m,
                "klienci_aktywni_12m": row.klienci_aktywni_12m,
                "retencja_3m_procent": float(row.retencja_3m_procent) if row.retencja_3m_procent else 0,
                "retencja_6m_procent": float(row.retencja_6m_procent) if row.retencja_6m_procent else 0,
                "retencja_12m_procent": float(row.retencja_12m_procent) if row.retencja_12m_procent else 0
            }
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get customer retention: {str(e)}")

@router.get("/wartosc-zycia-klienta", response_model=List[Dict[str, Any]])
def get_wartosc_zycia_klienta(
    db: Session = Depends(get_db)
):
    """Analiza wartości życia klienta (Customer Lifetime Value)"""
    try:
        query = text("""
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
                            ROUND((liczba_wizyt * sredni_czas_pobytu * 0.5) + 
                                  (liczba_miesiecy_aktywnych * 10), 2)
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
            SELECT 
                klient_id,
                imie,
                nazwisko,
                liczba_wizyt,
                sredni_czas_pobytu,
                liczba_miesiecy_aktywnych,
                dni_od_pierwszej_wizyty,
                liczba_roznych_sal,
                srednia_ocena_zajec,
                clv_wartosc,
                czestotliwosc_roczna,
                segment_wartosci
            FROM clv_segmentacja
            ORDER BY clv_wartosc DESC
            LIMIT 50
        """)
        
        result = db.execute(query).fetchall()
        
        return [
            {
                "klient_id": row.klient_id,
                "imie": row.imie,
                "nazwisko": row.nazwisko,
                "liczba_wizyt": row.liczba_wizyt,
                "sredni_czas_pobytu": float(row.sredni_czas_pobytu) if row.sredni_czas_pobytu else 0,
                "liczba_miesiecy_aktywnych": row.liczba_miesiecy_aktywnych,
                "dni_od_pierwszej_wizyty": row.dni_od_pierwszej_wizyty,
                "liczba_roznych_sal": row.liczba_roznych_sal,
                "srednia_ocena_zajec": float(row.srednia_ocena_zajec) if row.srednia_ocena_zajec else 0,
                "clv_wartosc": float(row.clv_wartosc),
                "czestotliwosc_roczna": float(row.czestotliwosc_roczna),
                "segment_wartosci": row.segment_wartosci
            }
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get customer lifetime value: {str(e)}")
