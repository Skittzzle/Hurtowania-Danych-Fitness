from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import *
from ..schemas import *

router = APIRouter()

# CRUD operations dla tabel wymiarów

@router.get("/klienci", response_model=List[Klienci])
def get_klienci(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    try:
        clients = db.query(KlienciModel).offset(skip).limit(limit).all()
        return clients
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get clients: {str(e)}")

@router.get("/klienci/{client_id}", response_model=Klienci)
def get_klient(client_id: int, db: Session = Depends(get_db)):
    try:
        client = db.query(KlienciModel).filter(KlienciModel.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get client: {str(e)}")

@router.post("/klienci", response_model=Klienci)
def create_klient(client: KlienciBase, db: Session = Depends(get_db)):
    try:
        db_client = KlienciModel(**client.model_dump())
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        return db_client
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create client: {str(e)}")

@router.put("/klienci/{client_id}", response_model=Klienci)
def update_klient(client_id: int, client: KlienciBase, db: Session = Depends(get_db)):
    try:
        db_client = db.query(KlienciModel).filter(KlienciModel.id == client_id).first()
        if not db_client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        for key, value in client.model_dump().items():
            setattr(db_client, key, value)
        
        db.commit()
        db.refresh(db_client)
        return db_client
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update client: {str(e)}")

@router.delete("/klienci/{client_id}")
def delete_klient(client_id: int, db: Session = Depends(get_db)):
    try:
        db_client = db.query(KlienciModel).filter(KlienciModel.id == client_id).first()
        if not db_client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        db.delete(db_client)
        db.commit()
        return {"message": "Client deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete client: {str(e)}")

@router.get("/trenerzy", response_model=List[Trenerzy])
def get_trenerzy(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    try:
        trainers = db.query(TrenerzyModel).offset(skip).limit(limit).all()
        return trainers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trainers: {str(e)}")

@router.get("/zajecia", response_model=List[Zajecia])
def get_zajecia(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    try:
        classes = db.query(ZajeciaModel).offset(skip).limit(limit).all()
        return classes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get classes: {str(e)}")

@router.get("/sale", response_model=List[Sale])
def get_sale(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    try:
        rooms = db.query(SaleModel).offset(skip).limit(limit).all()
        return rooms
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rooms: {str(e)}")

# CRUD operations dla tabel faktów

@router.get("/wejscia", response_model=List[Wejscia])
def get_wejscia(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    klient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(WejsciaModel)
        if klient_id:
            query = query.filter(WejsciaModel.klient_id == klient_id)
        entries = query.offset(skip).limit(limit).all()
        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get entries: {str(e)}")

@router.post("/wejscia", response_model=Wejscia)
def create_wejscie(entry: WejsciaBase, db: Session = Depends(get_db)):
    try:
        db_entry = WejsciaModel(**entry.model_dump())
        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)
        return db_entry
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create entry: {str(e)}")

@router.delete("/wejscia/{entry_id}")
def delete_wejscie(entry_id: int, db: Session = Depends(get_db)):
    try:
        db_entry = db.query(WejsciaModel).filter(WejsciaModel.id == entry_id).first()
        if not db_entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        db.delete(db_entry)
        db.commit()
        return {"message": "Entry deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete entry: {str(e)}")

@router.get("/uczestnictwo-zajec", response_model=List[UczestnictwoZajec])
def get_uczestnictwo_zajec(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    trener_id: Optional[int] = Query(None),
    zajecie_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(UczestnictwoZajecModel)
        if trener_id:
            query = query.filter(UczestnictwoZajecModel.trener_id == trener_id)
        if zajecie_id:
            query = query.filter(UczestnictwoZajecModel.zajecie_id == zajecie_id)
        participations = query.offset(skip).limit(limit).all()
        return participations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get class participations: {str(e)}")

# Mapowanie modeli SQLAlchemy do Pydantic
KlienciModel = Klienci
TrenerzyModel = Trenerzy
ZajeciaModel = Zajecia
SaleModel = Sale
WejsciaModel = Wejscia
UczestnictwoZajecModel = UczestnictwoZajec
