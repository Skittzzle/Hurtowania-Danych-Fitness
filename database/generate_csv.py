import pandas as pd
from sqlalchemy import create_engine, text
import os
import sys

# Database configuration - standalone
DB_URL = "postgresql://fitness:postgres@localhost:5432/fitness"

def export_to_csv():
    print("📤 Eksportowanie danych do plików CSV...")
    engine = create_engine(DB_URL)
    
    # Create directory if not exists
    os.makedirs('database/seeds', exist_ok=True)
    
    tables = [
        'adresy', 'daty', 'sale', 'zajecia', 
        'specjalizacje', 'trenerzy', 'klienci', 
        'wejscia', 'uczestnictwo_zajec', 'platnosci'
    ]
    
    with engine.connect() as conn:
        for table in tables:
            print(f"  - Przetwarzanie tabeli: {table}")
            query = f"SELECT * FROM fitness_dw.{table}"
            df = pd.read_sql(query, conn)
            df.to_csv(f'database/seeds/{table}.csv', index=False)
            print(f"    ✅ Zapisano: database/seeds/{table}.csv ({len(df)} wierszy)")

if __name__ == "__main__":
    export_to_csv()
