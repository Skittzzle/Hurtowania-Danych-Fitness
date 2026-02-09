from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..database import get_db
from ..services.etl_service_final import ETLService
from ..services.csv_service import CSVService

router = APIRouter()

@router.post("/generate-sample-data")
async def generate_sample_data(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        etl_service = ETLService(db)
        background_tasks.add_task(etl_service.generate_sample_data)
        return {"message": "Sample data generation started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start data generation: {str(e)}")

@router.post("/load-csv-data")
async def load_csv_data(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        csv_service = CSVService(db)
        # We run it in background because loading many CSVs might take some time
        background_tasks.add_task(csv_service.load_all_csvs)
        return {"message": "CSV data loading started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start CSV loading: {str(e)}")

@router.post("/clear-data")
def clear_data(db: Session = Depends(get_db)):
    try:
        # Czyszczenie tabel faktów
        db.execute(text("DELETE FROM fitness_dw.uczestnictwo_zajec"))
        db.execute(text("DELETE FROM fitness_dw.wejscia"))
        
        # Czyszczenie tabel wymiarów
        db.execute(text("DELETE FROM fitness_dw.klienci"))
        db.execute(text("DELETE FROM fitness_dw.trenerzy"))
        db.execute(text("DELETE FROM fitness_dw.zajecia"))
        db.execute(text("DELETE FROM fitness_dw.sale"))
        db.execute(text("DELETE FROM fitness_dw.daty"))
        db.execute(text("DELETE FROM fitness_dw.adresy"))
        
        # Resetowanie sekwencji
        db.execute(text("ALTER SEQUENCE fitness_dw.adresy_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE fitness_dw.daty_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE fitness_dw.sale_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE fitness_dw.zajecia_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE fitness_dw.klienci_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE fitness_dw.trenerzy_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE fitness_dw.wejscia_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE fitness_dw.uczestnictwo_zajec_id_seq RESTART WITH 1"))
        
        db.commit()
        return {"message": "All data cleared successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")

@router.get("/data-status")
def get_data_status(db: Session = Depends(get_db)):
    try:
        status = {}
        
        # Liczba rekordów w każdej tabeli
        tables = [
            'adresy', 'daty', 'sale', 'zajecia', 'klienci', 
            'trenerzy', 'wejscia', 'uczestnictwo_zajec'
        ]
        
        for table in tables:
            result = db.execute(text(f"SELECT COUNT(*) FROM fitness_dw.{table}")).scalar()
            status[table] = result
        
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data status: {str(e)}")
