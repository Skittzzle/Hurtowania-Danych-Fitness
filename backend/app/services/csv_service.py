import pandas as pd
import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

class CSVService:
    def __init__(self, db: Session, seed_dir: str = "database/seeds"):
        self.db = db
        self.seed_dir = seed_dir

    def load_all_csvs(self):
        """Loads all CSV files in the correct order to respect FK constraints."""
        files_and_tables = [
            ("adresy.csv", "fitness_dw.adresy"),
            ("daty.csv", "fitness_dw.daty"),
            ("sale.csv", "fitness_dw.sale"),
            ("zajecia.csv", "fitness_dw.zajecia"),
            ("specjalizacje.csv", "fitness_dw.specjalizacje"),
            ("trenerzy.csv", "fitness_dw.trenerzy"),
            ("klienci.csv", "fitness_dw.klienci"),
            ("wejscia.csv", "fitness_dw.wejscia"),
            ("uczestnictwo_zajec.csv", "fitness_dw.uczestnictwo_zajec"),
            ("platnosci.csv", "fitness_dw.platnosci")
        ]

        try:
            for file_name, table_name in files_and_tables:
                file_path = os.path.join(self.seed_dir, file_name)
                if os.path.exists(file_path):
                    print(f"Loading {file_name} into {table_name}...")
                    self._load_csv_to_table(file_path, table_name)
            
            self.db.commit()
            return {"status": "success", "message": "All CSVs loaded successfully"}
        except Exception as e:
            self.db.rollback()
            print(f"Error loading CSVs: {e}")
            raise e

    def _load_csv_to_table(self, file_path: str, table_name: str):
        df = pd.read_csv(file_path)
        
        # PostgreSQL handles SERIAL IDs, but if CSV has IDs we might need to reset sequence later
        # However, for simplicity and ensuring FKs match the CSVs, we include IDs if they are in CSV
        
        # Prepare the column names and place-holders
        cols = ", ".join(df.columns)
        placeholders = ", ".join([f":{col}" for col in df.columns])
        
        query = text(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING")
        
        for _, row in df.iterrows():
            # Convert row to dict, handling NaT/NaN for dates/numbers
            row_dict = row.to_dict()
            for k, v in row_dict.items():
                if pd.isna(v):
                    row_dict[k] = None
            
            self.db.execute(query, row_dict)
