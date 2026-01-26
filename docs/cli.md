# Projektor CLI — dokumentacja i przykłady

Ten dokument opisuje **wszystkie dostępne komendy CLI** w Projekto­rze oraz podaje przykłady użycia w formie komend shell.

## Instalacja (zalecane: venv)

```bash
# w katalogu repo
python3 -m venv venv
source venv/bin/activate

# instalacja projektu jako paczki (udostępnia komendę `projektor`)
pip install -e .

# opcjonalnie: instalacja wsparcia LLM
pip install -e ".[llm]"
```

## Konfiguracja LLM (OpenRouter)

Projektor czyta konfigurację z `.env` (ładowane automatycznie przez CLI) oraz/lub ze zmiennych środowiskowych.

```bash
# w katalogu, z którego uruchamiasz projektor (albo w katalogu wskazanym przez --project)
cp .env.example .env

# edytuj .env i ustaw prawdziwy klucz
# OPENROUTER_API_KEY=...
```

Wspierane zmienne:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `OPENROUTER_MAX_TOKENS`
- `OPENROUTER_TEMPERATURE`

## Uruchamianie CLI

Jeśli projekt jest zainstalowany (np. `pip install -e .`), używaj:

```bash
projektor --help
```

Jeśli nie instalujesz paczki, możesz uruchamiać bezpośrednio:

```bash
PYTHONPATH=./src python3 src/projektor/cli.py --help
```

## Opcje globalne

Dostępne dla wszystkich komend:

- `--project / -p` — ścieżka do katalogu projektu (domyślnie `.`)
- `--verbose / -v` — tryb verbose

Przykłady:

```bash
# praca na innym katalogu projektu
projektor --project /path/to/my-project project status

# tryb verbose
projektor -v project info
```

---

# Komendy

## `project` — zarządzanie projektem

### `project init`
Inicjalizuje strukturę projektu (`.projektor/`, `projektor.yaml`).

```bash
# inicjalizacja w bieżącym katalogu
projektor project init "my-project" --language python --description "Demo"

# inicjalizacja w innym katalogu
projektor --project /tmp/myproj project init "my-project" --language python
```

### `project info`
Wyświetla metadane projektu.

```bash
projektor project info
```

### `project status`
Wyświetla listę ticketów (skrótowo).

```bash
projektor project status
```

---

## `ticket` — zarządzanie ticketami

### `ticket create`
Tworzy ticket w projekcie.

```bash
# minimalnie
projektor ticket create "Dodaj obsługę cache Redis"

# z typem i priorytetem
projektor ticket create "Napraw błąd logowania" --type bug --priority high \
  --description "Reprodukcja: ..."
```

Dostępne typy: `task`, `bug`, `feature`, `story`, `tech_debt`.

Dostępne priorytety: `critical`, `high`, `medium`, `low`.

### `ticket show`
Pokazuje szczegóły ticketu.

```bash
projektor ticket show PROJ-1
```

### `ticket list`
Listuje tickety z filtrami.

```bash
# lista wszystkich (limit domyślny 20)
projektor ticket list

# filtr po statusie
projektor ticket list --status in_progress

# filtr po typie
projektor ticket list --type bug

# większy limit
projektor ticket list --limit 50
```

### `ticket start`
Ustawia ticket jako „w trakcie”. Jeśli ticket jest w `backlog`, CLI automatycznie przeprowadzi go przez `todo` → `in_progress`.

```bash
projektor ticket start PROJ-1
```

### `ticket complete`
Oznacza ticket jako ukończony. CLI automatycznie przeprowadza statusy aż do `done` (z zachowaniem dozwolonych przejść).

```bash
projektor ticket complete PROJ-1
```

---

## `sprint` — sprinty

### `sprint create`
Tworzy sprint.

```bash
projektor sprint create "Sprint 1" --goal "Dowiezienie MVP" --weeks 2
```

---

## `work` — orkiestracja (LLM + DevOps)

### `work plan`
Generuje plan dla ticketu (bez wykonywania zmian).

```bash
# pokaż plan w terminalu
projektor work plan PROJ-1

# zapisz plan do pliku
projektor work plan PROJ-1 --output plan.json
```

Uwagi:

- Jeśli `litellm` nie jest zainstalowane, planner użyje trybu awaryjnego (fallback) i plan będzie „szablonowy”.
- Dla faktycznego LLM użyj: `pip install -e ".[llm]"` i skonfiguruj `.env`.

### `work on`
Wykonuje pracę nad ticketem (może modyfikować pliki, uruchamiać testy, wykonywać commity).

```bash
# DRY RUN: bez zmian w plikach
projektor work on PROJ-1 --dry-run

# wykonanie bez auto-commit
projektor work on PROJ-1 --no-commit

# wykonanie bez testów
projektor work on PROJ-1 --no-tests
```

---

## `test` — testy

### `test run`
Uruchamia testy projektu.

```bash
# wszystkie testy
projektor test run

# z pokryciem
projektor test run --coverage

# konkretny plik testów
projektor test run --file tests/unit/test_core.py

# filtrowanie po nazwie (pytest -k)
projektor test run --name "planning"
```

---

## `git` — operacje git

### `git status`
Pokazuje status repo.

```bash
projektor git status
```

### `git log`
Pokazuje ostatnie commity.

```bash
projektor git log
projektor git log --count 20
```

---

# Przykładowy workflow end-to-end (shell)

Poniżej minimalny scenariusz, który da się wykonać w 100% z CLI:

```bash
# 1) inicjalizacja projektu w nowym katalogu
mkdir -p /tmp/projektor-demo
projektor --project /tmp/projektor-demo project init "demo" --language python \
  --description "Demo projektu"

# 2) utworzenie ticketu
projektor --project /tmp/projektor-demo ticket create "Dodaj endpoint /health" \
  --type feature --priority medium --description "Zwraca 200 OK"

# 3) podejrzenie ticketu
projektor --project /tmp/projektor-demo ticket list
projektor --project /tmp/projektor-demo ticket show DEMO-1

# 4) start pracy
projektor --project /tmp/projektor-demo ticket start DEMO-1

# 5) plan od LLM
projektor --project /tmp/projektor-demo work plan DEMO-1 --output plan.json

# 6) dry-run wykonania
projektor --project /tmp/projektor-demo work on DEMO-1 --dry-run

# 7) zakończenie ticketu
projektor --project /tmp/projektor-demo ticket complete DEMO-1
```
