import pandas as pd
from sqlalchemy import create_engine, text
import os
import sys

# Database configuration - standalone
DB_URL = "postgresql://fitness:postgres@localhost:5432/fitness"

def import_from_csv():
    print("📥 Importowanie danych z plików CSV do hurtowni...")
    engine = create_engine(DB_URL)
    
    tables = [
        'adresy', 'daty', 'sale', 'zajecia', 
        'specjalizacje', 'trenerzy', 'klienci', 
        'wejscia', 'uczestnictwo_zajec', 'platnosci'
    ]
    
    with engine.begin() as conn:  # Transactional
        print("🧹 Czyszczenie starych danych...")
        conn.execute(text("TRUNCATE TABLE fitness_dw.wejscia, fitness_dw.uczestnictwo_zajec, fitness_dw.klienci, fitness_dw.trenerzy, fitness_dw.specjalizacje, fitness_dw.zajecia, fitness_dw.sale, fitness_dw.daty, fitness_dw.adresy CASCADE"))
        
        for table in tables:
            path = f'database/seeds/{table}.csv'
            if os.path.exists(path):
                print(f"  - Ładowanie: {table}")
                df = pd.read_csv(path)
                df.to_sql(table, conn, schema='fitness_dw', if_exists='append', index=False)
                print(f"    ✅ Załadowano {len(df)} wierszy.")
            else:
                print(f"  - ⚠️ Brak pliku: {path}, pomijam.")
        
    print("\n🚀 Import zakończony sukcesem!")

if __name__ == "__main__":
    import_from_csv()
