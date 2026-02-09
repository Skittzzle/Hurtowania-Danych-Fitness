from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db
from .models import *
from .schemas import *
from .routers import analytics, data, etl, trends, segmentation, analytics_extended, analytics_monthly

app = FastAPI(
    title="Fitness Data Warehouse API",
    description="API for fitness club data warehouse analytics",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(analytics_extended.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(analytics_monthly.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(etl.router, prefix="/api/etl", tags=["etl"])
app.include_router(trends.router, prefix="/api/trends", tags=["trends"])
app.include_router(segmentation.router, prefix="/api/segmentation", tags=["segmentation"])

@app.get("/")
def read_root():
    return {"message": "Fitness Data Warehouse API", "version": "1.0.0"}

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.get("/api/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    try:
        # Dzisiejsza frekwencja
        today_query = text("""
            SELECT COUNT(*) as count 
            FROM fitness_dw.wejscia w
            JOIN fitness_dw.daty d ON w.data_id = d.id
            WHERE d.data_pelna = CURRENT_DATE
        """)
        today_visits = db.execute(today_query).scalar() or 0
        
        # Zajęcia dzisiaj
        classes_today_query = text("""
            SELECT COUNT(DISTINCT zajecie_id) as count 
            FROM fitness_dw.uczestnictwo_zajec uz
            JOIN fitness_dw.daty d ON uz.data_id = d.id
            WHERE d.data_pelna = CURRENT_DATE
        """)
        classes_today = db.execute(classes_today_query).scalar() or 0
        
        # Średnia ocena
        avg_rating_query = text("""
            SELECT AVG(ocena_zajec) as avg_rating 
            FROM fitness_dw.uczestnictwo_zajec 
            WHERE ocena_zajec IS NOT NULL
        """)
        avg_rating = db.execute(avg_rating_query).scalar()
        
        # Aktywni klienci (ostatnie 30 dni)
        active_clients_query = text("""
            SELECT COUNT(DISTINCT klient_id) as count 
            FROM fitness_dw.wejscia w
            JOIN fitness_dw.daty d ON w.data_id = d.id
            WHERE d.data_pelna >= CURRENT_DATE - INTERVAL '30 days'
        """)
        active_clients = db.execute(active_clients_query).scalar() or 0
        
        return DashboardStats(
            dzisiejsza_frekwencja=today_visits,
            zajecia_dzis=classes_today,
            srednia_ocena=float(avg_rating) if avg_rating else None,
            aktywni_klienci=active_clients
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
