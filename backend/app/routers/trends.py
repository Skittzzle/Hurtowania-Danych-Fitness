from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from ..database import get_db

router = APIRouter()

@router.get("/frekwencja-trendy", response_model=List[Dict[str, Any]])
def get_frekwencja_trendy(
    lat: Optional[int] = Query(2, description="Liczba lat analizy"),
    db: Session = Depends(get_db)
):
    """Zwraca trendy frekwencji - wzrost/spadek miesięczny"""
    try:
        query = text("""
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
            LIMIT :lat * 12
        """)
        
        result = db.execute(query, {"lat": lat}).fetchall()
        
        return [
            {
                "rok": row.rok,
                "miesiac": row.miesiac,
                "liczba_wejsc": row.liczba_wejsc,
                "sredni_czas_pobytu": float(row.sredni_czas_pobytu) if row.sredni_czas_pobytu else 0,
                "poprzednia_miesiac": row.poprzednia_miesiac,
                "zmiana_procent": float(row.zmiana_procent) if row.zmiana_procent else 0,
                "trend": row.trend
            }
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attendance trends: {str(e)}")

@router.get("/frekwencja-prognozy", response_model=Dict[str, Any])
def get_frekwencja_prognozy(
    miesice_naprzod: Optional[int] = Query(3, description="Liczba miesięcy do prognozy"),
    db: Session = Depends(get_db)
):
    """Prognozy frekwencji na podstawie historycznych danych"""
    try:
        query = text("""
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
            LIMIT :miesice_naprzod
        """)
        
        result = db.execute(query, {"miesice_naprzod": miesice_naprzod}).fetchall()
        
        return {
            "prognozy": [
                {
                    "miesiac": row.miesiac,
                    "srednia_historyczna": float(row.srednia_wejsc),
                    "prognoza_optymistyczna": float(row.prognoza_wzrost),
                    "prognoza_pesymistyczna": float(row.prognoza_spadek)
                }
                for row in result
            ],
            "metodologia": "Prognozy na podstawie średniej z ostatnich 12 miesięcy z marginesem ±5%"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attendance forecasts: {str(e)}")

@router.get("/frekwencja-porownanie-roczne", response_model=List[Dict[str, Any]])
def get_frekwencja_porownanie_roczne(
    db: Session = Depends(get_db)
):
    """Porównanie frekwencji rok do roku"""
    try:
        query = text("""
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
            ORDER BY rok DESC
        """)
        
        result = db.execute(query).fetchall()
        
        return [
            {
                "rok": row.rok,
                "calkowita_frekwencja": row.calkowita_frekwencja,
                "sredni_czas_roczny": float(row.sredni_czas_roczny) if row.sredni_czas_roczny else 0,
                "liczba_miesiecy_aktywnych": row.liczba_miesiecy_aktywnych,
                "zmiana_roczna_procent": float(row.zmiana_roczna_procent) if row.zmiana_roczna_procent else 0,
                "trend_roczny": row.trend_roczny
            }
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get yearly comparison: {str(e)}")
