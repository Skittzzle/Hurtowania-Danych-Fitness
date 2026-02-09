from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from ..database import get_db

router = APIRouter()

@router.get("/frekwencja-dni-miesiaca", response_model=List[Dict[str, Any]])
def get_frekwencja_dni_miesiaca(
    rok: int = Query(..., description="Rok"),
    miesiac: int = Query(..., description="Miesiąc (1-12)"),
    db: Session = Depends(get_db)
):
    """Pobiera frekwencję dla wszystkich dni w danym miesiącu"""
    try:
        query = text("""
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
            ORDER BY d.rok, d.miesiac, d.dzien
        """)
        
        result = db.execute(query, {"rok": rok, "miesiac": miesiac}).fetchall()
        
        return [
            {
                "rok": row.rok,
                "miesiac": row.miesiac,
                "dzien": row.dzien,
                "liczba_wejsc": row.liczba_wejsc,
                "sredni_czas_pobytu": float(row.sredni_czas_pobytu) if row.sredni_czas_pobytu else 0,
                "calkowity_czas_pobytu": row.calkowity_czas_pobytu
            }
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get daily attendance: {str(e)}")

@router.get("/frekwencja-dnia", response_model=List[Dict[str, Any]])
def get_frekwencja_dnia(
    rok: int = Query(..., description="Rok"),
    miesiac: int = Query(..., description="Miesiąc (1-12)"),
    dzien: int = Query(..., description="Dzień (1-31)"),
    db: Session = Depends(get_db)
):
    """Pobiera szczegółową frekwencję dla danego dnia (po godzinach)"""
    try:
        query = text("""
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
            ORDER BY d.rok, d.miesiac, d.dzien, godzina
        """)
        
        result = db.execute(query, {"rok": rok, "miesiac": miesiac, "dzien": dzien}).fetchall()
        
        return [
            {
                "rok": row.rok,
                "miesiac": row.miesiac,
                "dzien": row.dzien,
                "godzina": int(row.godzina),
                "liczba_wejsc": row.liczba_wejsc,
                "sredni_czas_pobytu": float(row.sredni_czas_pobytu) if row.sredni_czas_pobytu else 0,
                "calkowity_czas_pobytu": row.calkowity_czas_pobytu,
                "unikalni_klienci": row.unikalni_klienci
            }
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hourly attendance: {str(e)}")

@router.get("/frekwencja-podsumowanie-dnia", response_model=Dict[str, Any])
def get_frekwencja_podsumowanie_dnia(
    rok: int = Query(..., description="Rok"),
    miesiac: int = Query(..., description="Miesiąc (1-12)"),
    dzien: int = Query(..., description="Dzień (1-31)"),
    db: Session = Depends(get_db)
):
    """Pobiera podsumowanie frekwencji dla danego dnia"""
    try:
        query = text("""
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
            FROM dzienne_statystyki ds, poprzedni_dzien pd
        """)
        
        result = db.execute(query, {"rok": rok, "miesiac": miesiac, "dzien": dzien}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="No data found for the specified date")
        
        return {
            "data": f"{rok}-{miesiac.toString().padStart(2, '0')}-{dzien.toString().padStart(2, '0')}",
            "liczba_wejsc": result.liczba_wejsc,
            "unikalni_klienci": result.unikalni_klienci,
            "sredni_czas_pobytu": float(result.sredni_czas_pobytu) if result.sredni_czas_pobytu else 0,
            "calkowity_czas_pobytu": result.calkowity_czas_pobytu,
            "liczba_uzytych_sal": result.liczba_uzytych_sal,
            "liczba_zajec": result.liczba_zajec,
            "liczba_wejsc_poprzedni": result.liczba_wejsc_poprzedni,
            "zmiana_procentowa": float(result.zmiana_procentowa)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get daily summary: {str(e)}")

@router.get("/frekwencja-godzinowa", response_model=List[Dict[str, Any]])
def get_frekwencja_godzinowa(
    rok: int = Query(..., description="Rok"),
    miesiac: int = Query(..., description="Miesiąc (1-12)"),
    dzien: Optional[int] = Query(None, description="Dzień (opcjonalny, jeśli nie podany - cały miesiąc)"),
    db: Session = Depends(get_db)
):
    """Pobiera frekwencję godzinową dla danego dnia lub całego miesiąca"""
    try:
        if dzien:
            # Frekwencja godzinowa dla konkretnego dnia
            query = text("""
                SELECT 
                    EXTRACT(HOUR FROM w.godzina_wejscia) as godzina,
                    COUNT(w.id) as liczba_wejsc,
                    COUNT(DISTINCT w.klient_id) as unikalni_klienci,
                    AVG(w.czas_pobytu_min) as sredni_czas_pobytu
                FROM fitness_dw.wejscia w
                JOIN fitness_dw.daty d ON w.data_id = d.id
                WHERE d.rok = :rok AND d.miesiac = :miesiac AND d.dzien = :dzien
                GROUP BY EXTRACT(HOUR FROM w.godzina_wejscia)
                ORDER BY godzina
            """)
            result = db.execute(query, {"rok": rok, "miesiac": miesiac, "dzien": dzien}).fetchall()
        else:
            # Frekwencja godzinowa dla całego miesiąca (uśredniona)
            query = text("""
                SELECT 
                    EXTRACT(HOUR FROM w.godzina_wejscia) as godzina,
                    COUNT(w.id) as liczba_wejsc,
                    COUNT(DISTINCT w.klient_id) as unikalni_klienci,
                    AVG(w.czas_pobytu_min) as sredni_czas_pobytu
                FROM fitness_dw.wejscia w
                JOIN fitness_dw.daty d ON w.data_id = d.id
                WHERE d.rok = :rok AND d.miesiac = :miesiac
                GROUP BY EXTRACT(HOUR FROM w.godzina_wejscia)
                ORDER BY godzina
            """)
            result = db.execute(query, {"rok": rok, "miesiac": miesiac}).fetchall()
        
        return [
            {
                "godzina": int(row.godzina),
                "liczba_wejsc": row.liczba_wejsc,
                "unikalni_klienci": row.unikalni_klienci,
                "sredni_czas_pobytu": float(row.sredni_czas_pobytu) if row.sredni_czas_pobytu else 0
            }
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hourly attendance: {str(e)}")
