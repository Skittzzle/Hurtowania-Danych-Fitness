from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from ..database import get_db

router = APIRouter()

@router.get("/frekwencja-miesiac-wszystkie-lata", response_model=List[Dict[str, Any]])
def get_frekwencja_miesiac_wszystkie_lata(
    miesiac: int = Query(..., description="Miesiąc (1-12)"),
    db: Session = Depends(get_db)
):
    """Pobiera frekwencję dla wybranego miesiąca we wszystkich dostępnych latach"""
    try:
        query = text("""
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
            ORDER BY d.rok, d.miesiac
        """)
        
        result = db.execute(query, {"miesiac": miesiac}).fetchall()
        
        return [
            {
                "rok": row.rok,
                "miesiac": row.miesiac,
                "liczba_wejsc": row.liczba_wejsc,
                "unikalni_klienci": row.unikalni_klienci,
                "sredni_czas_pobytu": float(row.sredni_czas_pobytu) if row.sredni_czas_pobytu else 0,
                "calkowity_czas_pobytu": row.calkowity_czas_pobytu
            }
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monthly data across all years: {str(e)}")

@router.get("/frekwencja-porownanie-miesiecy", response_model=List[Dict[str, Any]])
def get_frekwencja_porownanie_miesiecy(
    rok: int = Query(..., description="Rok"),
    db: Session = Depends(get_db)
):
    """Pobiera porównanie frekwencji między miesiącami w danym roku"""
    try:
        query = text("""
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
            ORDER BY d.miesiac
        """)
        
        result = db.execute(query, {"rok": rok}).fetchall()
        
        return [
            {
                "miesiac": row.miesiac,
                "nazwa_miesiaca": f"Miesiąc {row.miesiac}",
                "liczba_wejsc": row.liczba_wejsc,
                "unikalni_klienci": row.unikalni_klienci,
                "sredni_czas_pobytu": float(row.sredni_czas_pobytu) if row.sredni_czas_pobytu else 0,
                "calkowity_czas_pobytu": row.calkowity_czas_pobytu,
                "poprzedni_miesiac_wejscia": row.poprzedni_miesiac_wejscia,
                "zmiana_procentowa": float(row.zmiana_procentowa) if row.zmiana_procentowa else 0
            }
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monthly comparison: {str(e)}")

@router.get("/frekwencja-podsumowanie-roczne", response_model=Dict[str, Any])
def get_frekwencja_podsumowanie_roczne(
    rok: int = Query(..., description="Rok"),
    db: Session = Depends(get_db)
):
    """Pobiera roczne podsumowanie frekwencji"""
    try:
        query = text("""
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
            FROM roczne_statystyki rs, poprzedni_rok pr
        """)
        
        result = db.execute(query, {"rok": rok}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="No data found for specified year")
        
        return {
            "rok": rok,
            "calkowita_liczba_wejsc": result.calkowita_liczba_wejsc,
            "unikalni_klienci": result.unikalni_klienci,
            "sredni_czas_pobytu": float(result.sredni_czas_pobytu) if result.sredni_czas_pobytu else 0,
            "calkowity_czas_pobytu": result.calkowity_czas_pobytu,
            "liczba_uzytych_sal": result.liczba_uzytych_sal,
            "liczba_zajec": result.liczba_zajec,
            "liczba_aktywnych_miesiecy": result.liczba_aktywnych_miesiecy,
            "calkowita_liczba_wejsc_poprzedni": result.calkowita_liczba_wejsc_poprzedni,
            "zmiana_roczna_procentowa": float(result.zmiana_roczna_procentowa),
            "srednia_miesieczna": float(result.srednia_miesieczna),
            "sredni_czas_na_klienta": float(result.sredni_czas_na_klienta)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get yearly summary: {str(e)}")
