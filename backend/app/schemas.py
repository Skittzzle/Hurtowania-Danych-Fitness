from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

# Schematy dla tabel wymiarów
class AdresyBase(BaseModel):
    miasto: str
    kod_pocztowy: str
    ulica: str
    numer_domu: str

class Adresy(AdresyBase):
    id: int
    
    class Config:
        from_attributes = True

class DatyBase(BaseModel):
    dzien: int
    miesiac: int
    rok: int
    data_pelna: date
    dzien_tygodnia: str
    kwartal: int

class Daty(DatyBase):
    id: int
    
    class Config:
        from_attributes = True

class SaleBase(BaseModel):
    numer_sali: str
    pojemnosc: int

class Sale(SaleBase):
    id: int
    
    class Config:
        from_attributes = True

class ZajeciaBase(BaseModel):
    nazwa_zajec: str
    poziom_trudnosci: str

class Zajecia(ZajeciaBase):
    id: int
    
    class Config:
        from_attributes = True

class KlienciBase(BaseModel):
    imie: str
    nazwisko: str
    plec: str
    adres_id: int
    data_urodzenia: date

class Klienci(KlienciBase):
    id: int
    adres: Optional[Adresy] = None
    
    class Config:
        from_attributes = True

class TrenerzyBase(BaseModel):
    imie: str
    nazwisko: str
    adres_id: int
    specjalizacja: str

class Trenerzy(TrenerzyBase):
    id: int
    adres: Optional[Adresy] = None
    
    class Config:
        from_attributes = True

# Schematy dla tabel faktów
class WejsciaBase(BaseModel):
    klient_id: int
    data_id: int
    sala_id: int
    czas_pobytu_min: int
    data_wejscia: datetime

class Wejscia(WejsciaBase):
    id: int
    klient: Optional[Klienci] = None
    data: Optional[Daty] = None
    sala: Optional[Sale] = None
    
    class Config:
        from_attributes = True

class UczestnictwoZajecBase(BaseModel):
    data_id: int
    klient_id: int
    trener_id: int
    zajecie_id: int
    sala_id: int
    ocena_zajec: Optional[Decimal] = None
    czas_trwania: int
    liczba_uczestnikow: int
    data_zajec: datetime

class UczestnictwoZajec(UczestnictwoZajecBase):
    id: int
    data: Optional[Daty] = None
    klient: Optional[Klienci] = None
    trener: Optional[Trenerzy] = None
    zajecie: Optional[Zajecia] = None
    sala: Optional[Sale] = None
    
    class Config:
        from_attributes = True

# Schematy dla widoków analitycznych
class FrekwencjaMiesieczna(BaseModel):
    rok: int
    miesiac: int
    liczba_wejsc: int
    calkowity_czas_pobytu: int
    sredni_czas_pobytu: Optional[float]

class PopularnoscZajec(BaseModel):
    nazwa_zajec: str
    poziom_trudnosci: str
    liczba_zajec: int
    srednia_ocena: Optional[float]
    calkowita_liczba_uczestnikow: int
    srednia_liczba_uczestnikow: Optional[float]

class EfektywnoscTrenerow(BaseModel):
    trener: str
    specjalizacja: str
    liczba_prowadzonych_zajec: int
    srednia_ocena: Optional[float]
    calkowita_liczba_uczestnikow: int

class ObciazenieSal(BaseModel):
    numer_sali: str
    pojemnosc: int
    liczba_wejsc: int
    liczba_zajec: int
    srednie_obciazenie: Optional[float]

# Schematy dla API
class DashboardStats(BaseModel):
    dzisiejsza_frekwencja: int
    zajecia_dzis: int
    srednia_ocena: Optional[float]
    aktywni_klienci: int
