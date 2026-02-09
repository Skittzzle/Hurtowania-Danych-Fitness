from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from ..database import get_db
from ..schemas import FrekwencjaMiesieczna, PopularnoscZajec, EfektywnoscTrenerow, ObciazenieSal

router = APIRouter()

@router.get("/frekwencja-miesieczna", response_model=List[FrekwencjaMiesieczna])
def get_frekwencja_miesieczna(
    rok: Optional[int] = Query(None, description="Rok do filtrowania"),
    db: Session = Depends(get_db)
):
    try:
        where_clause = ""
        params = {}
        if rok:
            where_clause = "WHERE rok = :rok"
            params = {"rok": rok}

        query_text = """
            SELECT rok, miesiac, liczba_wejsc, sredni_czas_pobytu
            FROM fitness_dw.v_frekwencja_miesieczna
            """ + where_clause + """
            ORDER BY rok, miesiac
        """

        query = text(query_text)
        result = db.execute(query, params).fetchall()
        
        return [
            FrekwencjaMiesieczna(
                rok=row.rok,
                miesiac=row.miesiac,
                liczba_wejsc=row.liczba_wejsc,
                calkowity_czas_pobytu=0,  # Brak tej kolumny w widoku
                sredni_czas_pobytu=float(row.sredni_czas_pobytu) if row.sredni_czas_pobytu else None
            )
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monthly attendance: {str(e)}")

@router.get("/popularnosc-zajec", response_model=List[PopularnoscZajec])
def get_popularnosc_zajec(
    limit: Optional[int] = Query(10, description="Limit wyników"),
    db: Session = Depends(get_db)
):
    try:
        query = text("""
            SELECT nazwa_zajec, poziom_trudnosci, liczba_zajec, srednia_ocena, 
                   total_participants, avg_participants
            FROM fitness_dw.v_popularnosc_zajec
            ORDER BY total_participants DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit}).fetchall()
        
        return [
            PopularnoscZajec(
                nazwa_zajec=row.nazwa_zajec,
                poziom_trudnosci=row.poziom_trudnosci,
                liczba_zajec=row.liczba_zajec,
                srednia_ocena=float(row.srednia_ocena) if row.srednia_ocena else None,
                calkowita_liczba_uczestnikow=row.total_participants,
                srednia_liczba_uczestnikow=float(row.avg_participants) if row.avg_participants else None
            )
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get class popularity: {str(e)}")

@router.get("/efektywnosc-trenerow", response_model=List[EfektywnoscTrenerow])
def get_efektywnosc_trenerow(
    limit: Optional[int] = Query(10, description="Limit wyników"),
    db: Session = Depends(get_db)
):
    try:
        query = text("""
            SELECT imie_nazwisko_trenera, specjalizacja, liczba_prowadzonych_zajec, 
                   srednia_ocena_zajec, suma_uczestnikow
            FROM fitness_dw.v_efektywnosc_trenerow
            ORDER BY srednia_ocena_zajec DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit}).fetchall()
        
        return [
            EfektywnoscTrenerow(
                imie_nazwisko_trenera=row.imie_nazwisko_trenera,
                specjalizacja=row.specjalizacja,
                liczba_prowadzonych_zajec=row.liczba_prowadzonych_zajec,
                srednia_ocena_zajec=float(row.srednia_ocena_zajec) if row.srednia_ocena_zajec else None,
                suma_uczestnikow=row.suma_uczestnikow
            )
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trainer effectiveness: {str(e)}")

@router.get("/obciazenie-sal", response_model=List[ObciazenieSal])
def get_obciazenie_sal(
    limit: Optional[int] = Query(10, description="Limit wyników"),
    db: Session = Depends(get_db)
):
    try:
        query = text("""
            SELECT numer_sali, pojemnosc, liczba_unikalnych_klientow, liczba_wejsc, 
                   liczba_roznych_zajec, sredni_czas_pobytu
            FROM fitness_dw.v_obciazenie_sal
            ORDER BY liczba_wejsc DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit}).fetchall()
        
        return [
            ObciazenieSal(
                numer_sali=row.numer_sali,
                pojemnosc=row.pojemnosc,
                liczba_unikalnych_klientow=row.liczba_unikalnych_klientow,
                liczba_wejsc=row.liczba_wejsc,
                liczba_roznych_zajec=row.liczba_roznych_zajec,
                sredni_czas_pobytu=float(row.sredni_czas_pobytu) if row.sredni_czas_pobytu else None
            )
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get room utilization: {str(e)}")
