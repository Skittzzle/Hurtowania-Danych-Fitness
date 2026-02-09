from sqlalchemy.orm import Session
from sqlalchemy import text
from faker import Faker
from datetime import datetime, timedelta
import random
from typing import List

class ETLService:
    def __init__(self, db: Session):
        self.db = db
        self.fake = Faker('pl_PL')
        
    def generate_sample_data(self):
        """Generuje przykładowe dane dla hurtowni"""
        try:
            # 1. Generowanie adresów
            adresy_ids = self._generate_adresy(50)
            
            # 2. Generowanie dat (ostatnie 2 lata)
            daty_ids = self._generate_daty(730)
            
            # 3. Generowanie sal
            sale_ids = self._generate_sale(10)
            
            # 4. Generowanie zajęć
            zajecia_ids = self._generate_zajecia(15)
            
            # 5. Generowanie specjalizacji (Snowflake)
            spec_ids = self._generate_specjalizacje()
            
            # 6. Generowanie trenerów
            trenerzy_ids = self._generate_trenerzy(20, adresy_ids, spec_ids)
            
            # 7. Generowanie klientów
            klienci_ids = self._generate_klienci(200, adresy_ids)
            
            # 8. Generowanie wejść
            self._generate_wejscia(klienci_ids, daty_ids, sale_ids, 5000)
            
            # 9. Generowanie uczestnictwa w zajęciach
            self._generate_uczestnictwo_zajec(
                klienci_ids, trenerzy_ids, zajecia_ids, 
                sale_ids, daty_ids, 3000
            )

            # 10. Generowanie płatności (3. fakt - Konstelacja)
            self._generate_platnosci(klienci_ids, daty_ids, 800)
            
            self.db.commit()
            print("Sample data generated successfully")
            
        except Exception as e:
            self.db.rollback()
            print(f"Error generating sample data: {str(e)}")
            raise
    
    def _generate_adresy(self, count: int) -> List[int]:
        """Generuje adresy"""
        miasta = ['Warszawa', 'Kraków', 'Łódź', 'Wrocław', 'Poznań', 'Gdańsk', 'Szczecin', 'Bydgoszcz', 'Lublin', 'Katowice']
        
        adresy_ids = []
        for _ in range(count):
            miasto = random.choice(miasta)
            kod_pocztowy = f"{random.randint(10, 99)}-{random.randint(100, 999)}"
            ulica = self.fake.street_name()
            numer_domu = str(random.randint(1, 200))
            
            result = self.db.execute(text("""
                INSERT INTO fitness_dw.adresy (miasto, kod_pocztowy, ulica, numer_domu)
                VALUES (:miasto, :kod_pocztowy, :ulica, :numer_domu)
                RETURNING id
            """), {
                'miasto': miasto,
                'kod_pocztowy': kod_pocztowy,
                'ulica': ulica,
                'numer_domu': numer_domu
            })
            
            adresy_ids.append(result.scalar())
        
        return adresy_ids
    
    def _generate_daty(self, days: int) -> List[int]:
        """Generuje daty"""
        daty_ids = []
        start_date = datetime.now() - timedelta(days=days)
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            dzien_tygodnia = current_date.strftime('%A')
            kwartal = (current_date.month - 1) // 3 + 1
            
            result = self.db.execute(text("""
                INSERT INTO fitness_dw.daty (dzien, miesiac, rok, data_pelna, dzien_tygodnia, kwartal)
                VALUES (:dzien, :miesiac, :rok, :data_pelna, :dzien_tygodnia, :kwartal)
                RETURNING id
            """), {
                'dzien': current_date.day,
                'miesiac': current_date.month,
                'rok': current_date.year,
                'data_pelna': current_date.date(),
                'dzien_tygodnia': dzien_tygodnia,
                'kwartal': kwartal
            })
            
            daty_ids.append(result.scalar())
        
        return daty_ids
    
    def _generate_sale(self, count: int) -> List[int]:
        """Generuje sale treningowe"""
        sale_ids = []
        
        for i in range(1, count + 1):
            numer_sali = f"Sala {i}"
            pojemnosc = random.choice([10, 15, 20, 25, 30, 40, 50])
            
            result = self.db.execute(text("""
                INSERT INTO fitness_dw.sale (numer_sali, pojemnosc)
                VALUES (:numer_sali, :pojemnosc)
                RETURNING id
            """), {
                'numer_sali': numer_sali,
                'pojemnosc': pojemnosc
            })
            
            sale_ids.append(result.scalar())
        
        return sale_ids
    
    def _generate_zajecia(self, count: int) -> List[int]:
        """Generuje zajęcia"""
        nazwy_zajec = [
            'Joga', 'Pilates', 'Crossfit', 'Spinning', 'Boxing',
            'Aerobik', 'Taniec', 'MMA', 'Jiu Jitsu', 'Kalistenika',
            'Siłownia', 'Fitness', 'Stretching'
        ]
        poziomy = ['Poczatkujacy', 'Sredniozaawansowany', 'Zaawansowany']
        
        zajecia_ids = []
        
        for i in range(count):
            nazwa = random.choice(nazwy_zajec)
            poziom = random.choice(poziomy)
            
            result = self.db.execute(text("""
                INSERT INTO fitness_dw.zajecia (nazwa_zajec, poziom_trudnosci)
                VALUES (:nazwa_zajec, :poziom_trudnosci)
                RETURNING id
            """), {
                'nazwa_zajec': nazwa,
                'poziom_trudnosci': poziom
            })
            
            zajecia_ids.append(result.scalar())
        
        return zajecia_ids
    
    def _generate_specjalizacje(self) -> List[int]:
        """Generuje unikalne specjalizacje"""
        specjalizacje = [
            'Fitness', 'Joga', 'Pilates', 'Siłownia', 'Kardio', 'Boks',
            'Taniec', 'Pływanie', 'CrossFit', 'Rehabilitacja'
        ]
        spec_ids = []
        for s in specjalizacje:
            result = self.db.execute(text("""
                INSERT INTO fitness_dw.specjalizacje (nazwa)
                VALUES (:nazwa)
                ON CONFLICT (nazwa) DO UPDATE SET nazwa = EXCLUDED.nazwa
                RETURNING id
            """), {'nazwa': s})
            spec_ids.append(result.scalar())
        return spec_ids

    def _generate_trenerzy(self, count: int, adresy_ids: List[int], spec_ids: List[int]) -> List[int]:
        """Generuje trenerów z kluczami obcymi do specjalizacji"""
        trenerzy_ids = []
        for _ in range(count):
            imie = self.fake.first_name_male()
            nazwisko = self.fake.last_name()
            adres_id = random.choice(adresy_ids)
            spec_id = random.choice(spec_ids)
            
            result = self.db.execute(text("""
                INSERT INTO fitness_dw.trenerzy (imie, nazwisko, adres_id, specjalizacja_id)
                VALUES (:imie, :nazwisko, :adres_id, :spec_id)
                RETURNING id
            """), {
                'imie': imie,
                'nazwisko': nazwisko,
                'adres_id': adres_id,
                'spec_id': spec_id
            })
            trenerzy_ids.append(result.scalar())
        return trenerzy_ids
    
    def _generate_klienci(self, count: int, adresy_ids: List[int]) -> List[int]:
        """Generuje klientów"""
        klienci_ids = []
        
        for _ in range(count):
            plec = random.choice(['M', 'K'])
            if plec == 'M':
                imie = self.fake.first_name_male()
            else:
                imie = self.fake.first_name_female()
            
            nazwisko = self.fake.last_name()
            adres_id = random.choice(adresy_ids)
            data_urodzenia = self.fake.date_of_birth(minimum_age=16, maximum_age=70)
            
            result = self.db.execute(text("""
                INSERT INTO fitness_dw.klienci (imie, nazwisko, plec, adres_id, data_urodzenia)
                VALUES (:imie, :nazwisko, :plec, :adres_id, :data_urodzenia)
                RETURNING id
            """), {
                'imie': imie,
                'nazwisko': nazwisko,
                'plec': plec,
                'adres_id': adres_id,
                'data_urodzenia': data_urodzenia
            })
            
            klienci_ids.append(result.scalar())
        
        return klienci_ids
    
    def _generate_wejscia(self, klienci_ids: List[int], daty_ids: List[int], 
                          sale_ids: List[int], count: int):
        """Generuje wejścia do klubu"""
        
        for _ in range(count):
            klient_id = random.choice(klienci_ids)
            data_id = random.choice(daty_ids)
            sala_id = random.choice(sale_ids)
            czas_pobytu = random.randint(30, 180)  # 30-180 minut
            
            # Generuj timestamp w ciągu dnia
            data_wejscia = datetime.now() - timedelta(days=random.randint(0, 730))
            data_wejscia = data_wejscia.replace(
                hour=random.randint(6, 22),
                minute=random.randint(0, 59),
                second=0,
                microsecond=0
            )
            
            self.db.execute(text("""
                INSERT INTO fitness_dw.wejscia 
                (klient_id, data_id, sala_id, czas_pobytu_min, data_wejscia)
                VALUES (:klient_id, :data_id, :sala_id, :czas_pobytu_min, :data_wejscia)
            """), {
                'klient_id': klient_id,
                'data_id': data_id,
                'sala_id': sala_id,
                'czas_pobytu_min': czas_pobytu,
                'data_wejscia': data_wejscia
            })
    
    def _generate_uczestnictwo_zajec(self, klienci_ids: List[int], trenerzy_ids: List[int],
                                    zajecia_ids: List[int], sale_ids: List[int],
                                    daty_ids: List[int], count: int):
        """Generuje uczestnictwo w zajęciach"""
        
        for _ in range(count):
            data_id = random.choice(daty_ids)
            klient_id = random.choice(klienci_ids)
            trener_id = random.choice(trenerzy_ids)
            zajecie_id = random.choice(zajecia_ids)
            sala_id = random.choice(sale_ids)
            ocena_zajec = round(random.uniform(1.0, 5.0), 1)
            czas_trwania = random.choice([45, 60, 90, 120])
            liczba_uczestnikow = random.randint(5, 30)
            
            # Generuj timestamp w ciągu dnia
            data_zajec = datetime.now() - timedelta(days=random.randint(0, 730))
            data_zajec = data_zajec.replace(
                hour=random.randint(6, 22),
                minute=random.randint(0, 59),
                second=0,
                microsecond=0
            )
            
            self.db.execute(text("""
                INSERT INTO fitness_dw.uczestnictwo_zajec 
                (data_id, klient_id, trener_id, zajecie_id, sala_id, 
                 ocena_zajec, czas_trwania, liczba_uczestnikow, data_zajec)
                VALUES (:data_id, :klient_id, :trener_id, :zajecie_id, :sala_id,
                        :ocena_zajec, :czas_trwania, :liczba_uczestnikow, :data_zajec)
            """), {
                'data_id': data_id,
                'klient_id': klient_id,
                'trener_id': trener_id,
                'zajecie_id': zajecie_id,
                'sala_id': sala_id,
                'ocena_zajec': ocena_zajec,
                'czas_trwania': czas_trwania,
                'liczba_uczestnikow': liczba_uczestnikow,
                'data_zajec': data_zajec
            })

    def _generate_platnosci(self, klienci_ids: List[int], daty_ids: List[int], count: int):
        """Generuje płatności (trzecia tabela faktów dla Konstelacji)"""
        import random
        metody = ['Karta', 'Gotówka', 'Przelew']
        kwoty = [99.00, 149.00, 199.00, 249.00, 49.00]
        
        for _ in range(count):
            klient_id = random.choice(klienci_ids)
            data_id = random.choice(daty_ids)
            kwota = random.choice(kwoty)
            metoda = random.choice(metody)
            
            self.db.execute(text("""
                INSERT INTO fitness_dw.platnosci (klient_id, data_id, kwota, metoda_platnosci)
                VALUES (:klient_id, :data_id, :kwota, :metoda)
            """), {
                'klient_id': klient_id,
                'data_id': data_id,
                'kwota': kwota,
                'metoda': metoda
            })
