# 🏋️‍♂️ Fitness Data Warehouse
 
System analityczny dla sieci klubów fitness, zrealizowany jako **hurtownia danych (PostgreSQL, schemat konstelacji)** z interfejsem w Pythonie (Streamlit) oraz trybem desktopowym (pywebview).
 
Model danych: **Galaxy Schema (konstelacja)** – 3 tabele faktów współdzielą wymiary (czas/klient/sala), co umożliwia analizy przekrojowe i porównania.

## 🚀 Szybki start

### 1. Wymagania
- Python 3.10+
- PostgreSQL (działający lokalnie na porcie 5432)
- (opcjonalnie) klient DB np. pgAdmin / DBeaver

### 2. Instalacja
Zainstaluj wymagane biblioteki:
```bash
pip install -r backend/requirements.txt
```

### 3. Konfiguracja bazy
Upewnij się, że Twoja baza PostgreSQL jest dostępna pod adresem (domyślnie):
 
`postgresql://fitness:postgres@localhost:5432/fitness`
 
Możesz zmienić te ustawienia w pliku `backend/app/settings.py` lub przez `.env`.
 
Następnie utwórz strukturę hurtowni (schemat `fitness_dw`):
 
- uruchom skrypt: `database/init.sql`

### 4. Uruchomienie
Uruchom dashboard za pomocą skryptu:
```bash
python run.py
```
Aplikacja otworzy się w przeglądarce pod adresem `http://localhost:8501`.
 
Tryb desktopowy (okno aplikacji):
```bash
python run_desktop.py
```
 
Zasilenie danych (ETL):
 
- w aplikacji: sidebar → **„⚙️ Administracja (ETL)”** → „Załaduj dane z CSV”
- alternatywnie: `python database/import_csv.py`

## 📊 Funkcje
- **Dashboard**: szybki przegląd KPI.
- **Frekwencja i obłożenie**: trendy czasowe, czas pobytu, analiza sal.
- **Trenerzy i zajęcia**: efektywność trenerów, oceny, popularność.
- **Finanse**: analiza przychodów i metod płatności.
- **OLAP**: slicing/dicing, pivot/rotation, drill-down.
- **Zaawansowane agregacje SQL**: ROLLUP / CUBE / GROUPING SETS.
- **Transakcje (write-back)**: dodanie klienta i rejestracja wejścia.

## 🛠 Struktura projektu
- `app.py`: Główna aplikacja Streamlit.
- `backend/app/`: Logika biznesowa, modele SQLAlchemy i schematy Pydantic.
- `database/`: Skrypty SQL i dane.
- `run.py`: Skrypt pomocniczy do uruchamiania aplikacji.
- `run_desktop.py`: Uruchomienie w oknie desktop (pywebview).
- `docs/`: dokumentacja projektu, ERD i zapytania.

## 📚 Dokumentacja
- `docs/DOKUMENTACJA.md` – dokumentacja projektu (model, ETL, OLAP, zapytania)
- `docs/erd.png` – podgląd diagramu ERD
- `docs/HD_Sudol_Dawid.drawio` – źródłowy diagram ERD
- `docs/zapytania_hurtownicze.md` – pełny katalog zapytań SQL użytych w projekcie

## 🔐 Konfiguracja `.env` (opcjonalnie)
Projekt wspiera `.env` (patrz `backend/app/settings.py`). Minimalny przykład:
 
```bash
DATABASE_URL=postgresql://fitness:postgres@localhost:5432/fitness
```

## ✅ Publikacja na GitHub
W repo znajduje się plik `.gitignore` (ignoruje m.in. `.venv/`, `backend/venv/`, `__pycache__/`, `.env`, pliki IDE).

Przykładowa sekwencja komend:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <URL_DO_REPO>
git push -u origin main
```

---
*Projekt wykonany w ramach przedmiotu Hurtownie Danych.*
