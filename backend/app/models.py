from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from .database import Base

class Adresy(Base):
    __tablename__ = "adresy"
    __table_args__ = {"schema": "fitness_dw"}
    
    id = Column(Integer, primary_key=True, index=True)
    miasto = Column(String(50), nullable=False)
    kod_pocztowy = Column(String(10), nullable=False)
    ulica = Column(String(100), nullable=False)
    numer_domu = Column(String(20), nullable=False)
    
    klienci = relationship("Klienci", back_populates="adres")
    trenerzy = relationship("Trenerzy", back_populates="adres")

class Daty(Base):
    __tablename__ = "daty"
    __table_args__ = {"schema": "fitness_dw"}
    
    id = Column(Integer, primary_key=True, index=True)
    dzien = Column(Integer, nullable=False)
    miesiac = Column(Integer, nullable=False)
    rok = Column(Integer, nullable=False)
    data_pelna = Column(Date, nullable=False, unique=True)
    dzien_tygodnia = Column(String(20), nullable=False)
    kwartal = Column(Integer, nullable=False)
    
    wejscia = relationship("Wejscia", back_populates="data")
    uczestnictwo_zajec = relationship("UczestnictwoZajec", back_populates="data")
    platnosci = relationship("Platnosci", back_populates="data")

class Sale(Base):
    __tablename__ = "sale"
    __table_args__ = {"schema": "fitness_dw"}
    
    id = Column(Integer, primary_key=True, index=True)
    numer_sali = Column(String(20), nullable=False)
    pojemnosc = Column(Integer, nullable=False)
    
    wejscia = relationship("Wejscia", back_populates="sala")
    uczestnictwo_zajec = relationship("UczestnictwoZajec", back_populates="sala")

class Zajecia(Base):
    __tablename__ = "zajecia"
    __table_args__ = {"schema": "fitness_dw"}
    
    id = Column(Integer, primary_key=True, index=True)
    nazwa_zajec = Column(String(100), nullable=False)
    poziom_trudnosci = Column(String(20), nullable=False)
    
    __table_args__ = (
        CheckConstraint("poziom_trudnosci IN ('Początkujący', 'Średniozaawansowany', 'Zaawansowany')"),
        {"schema": "fitness_dw"}
    )
    
    uczestnictwo_zajec = relationship("UczestnictwoZajec", back_populates="zajecie")

class Klienci(Base):
    __tablename__ = "klienci"
    __table_args__ = {"schema": "fitness_dw"}
    
    id = Column(Integer, primary_key=True, index=True)
    imie = Column(String(50), nullable=False)
    nazwisko = Column(String(50), nullable=False)
    plec = Column(String(10), nullable=False)
    adres_id = Column(Integer, ForeignKey("fitness_dw.adresy.id"))
    data_urodzenia = Column(Date, nullable=False)
    
    __table_args__ = (
        CheckConstraint("plec IN ('M', 'K')"),
        {"schema": "fitness_dw"}
    )
    
    adres = relationship("Adresy", back_populates="klienci")
    wejscia = relationship("Wejscia", back_populates="klient")
    uczestnictwo_zajec = relationship("UczestnictwoZajec", back_populates="klient")
    platnosci = relationship("Platnosci", back_populates="klient")

class Specjalizacje(Base):
    __tablename__ = "specjalizacje"
    __table_args__ = {"schema": "fitness_dw"}
    
    id = Column(Integer, primary_key=True, index=True)
    nazwa = Column(String(100), nullable=False, unique=True)
    
    trenerzy = relationship("Trenerzy", back_populates="specjalizacja")

class Trenerzy(Base):
    __tablename__ = "trenerzy"
    __table_args__ = {"schema": "fitness_dw"}
    
    id = Column(Integer, primary_key=True, index=True)
    imie = Column(String(50), nullable=False)
    nazwisko = Column(String(50), nullable=False)
    adres_id = Column(Integer, ForeignKey("fitness_dw.adresy.id"))
    specjalizacja_id = Column(Integer, ForeignKey("fitness_dw.specjalizacje.id"))
    
    adres = relationship("Adresy", back_populates="trenerzy")
    specjalizacja = relationship("Specjalizacje", back_populates="trenerzy")
    uczestnictwo_zajec = relationship("UczestnictwoZajec", back_populates="trener")

class Wejscia(Base):
    __tablename__ = "wejscia"
    __table_args__ = {"schema": "fitness_dw"}
    
    id = Column(Integer, primary_key=True, index=True)
    klient_id = Column(Integer, ForeignKey("fitness_dw.klienci.id"), nullable=False)
    data_id = Column(Integer, ForeignKey("fitness_dw.daty.id"), nullable=False)
    sala_id = Column(Integer, ForeignKey("fitness_dw.sale.id"), nullable=False)
    czas_pobytu_min = Column(Integer, nullable=False)
    data_wejscia = Column(DateTime, nullable=False)
    
    __table_args__ = (
        CheckConstraint("czas_pobytu_min > 0"),
        {"schema": "fitness_dw"}
    )
    
    klient = relationship("Klienci", back_populates="wejscia")
    data = relationship("Daty", back_populates="wejscia")
    sala = relationship("Sale", back_populates="wejscia")

class UczestnictwoZajec(Base):
    __tablename__ = "uczestnictwo_zajec"
    __table_args__ = {"schema": "fitness_dw"}
    
    id = Column(Integer, primary_key=True, index=True)
    data_id = Column(Integer, ForeignKey("fitness_dw.daty.id"), nullable=False)
    klient_id = Column(Integer, ForeignKey("fitness_dw.klienci.id"), nullable=False)
    trener_id = Column(Integer, ForeignKey("fitness_dw.trenerzy.id"), nullable=False)
    zajecie_id = Column(Integer, ForeignKey("fitness_dw.zajecia.id"), nullable=False)
    sala_id = Column(Integer, ForeignKey("fitness_dw.sale.id"), nullable=False)
    ocena_zajec = Column(Numeric(3, 2), nullable=True)
    czas_trwania = Column(Integer, nullable=False)
    liczba_uczestnikow = Column(Integer, nullable=False)
    data_zajec = Column(DateTime, nullable=False)
    
    __table_args__ = (
        CheckConstraint("ocena_zajec BETWEEN 1.0 AND 5.0"),
        CheckConstraint("czas_trwania > 0"),
        CheckConstraint("liczba_uczestnikow > 0"),
        {"schema": "fitness_dw"}
    )
    
    data = relationship("Daty", back_populates="uczestnictwo_zajec")
    klient = relationship("Klienci", back_populates="uczestnictwo_zajec")
    trener = relationship("Trenerzy", back_populates="uczestnictwo_zajec")
    zajecie = relationship("Zajecia", back_populates="uczestnictwo_zajec")
    sala = relationship("Sale", back_populates="uczestnictwo_zajec")

class Platnosci(Base):
    __tablename__ = "platnosci"
    __table_args__ = {"schema": "fitness_dw"}
    
    id = Column(Integer, primary_key=True, index=True)
    klient_id = Column(Integer, ForeignKey("fitness_dw.klienci.id"), nullable=False)
    data_id = Column(Integer, ForeignKey("fitness_dw.daty.id"), nullable=False)
    kwota = Column(Numeric(10, 2), nullable=False)
    metoda_platnosci = Column(String(20), nullable=False)
    
    klient = relationship("Klienci", back_populates="platnosci")
    data = relationship("Daty", back_populates="platnosci")
