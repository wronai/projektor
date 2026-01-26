# Projektor - Nieinwazyjna Warstwa Monitorowania Błędów

Projektor to biblioteka Python umożliwiająca **nieinwazyjne monitorowanie błędów** w aplikacjach podczas developmentu. Automatycznie przechwytuje błędy i tworzy tickety do naprawy za pomocą LLM.

## Główne Cechy

- ✅ **Minimalna ingerencja** - konfiguracja przez pliki, bez zmian w kodzie
- ✅ **Automatyczne przechwytywanie** - globalny exception handler
- ✅ **Monitorowanie plików** - wykrywanie błędów składni przy zapisie
- ✅ **Integracja z pytest** - automatyczne raportowanie błędów testów
- ✅ **Wielopoziomowe raportowanie** - konsola, plik, GitHub Issues
- ✅ **Auto-fix z LLM** - automatyczna naprawa błędów

## Szybki Start

### 1. Instalacja

```bash
pip install projektor
```

### 2. Inicjalizacja (jednorazowo)

```bash
cd your_project
projektor init
```

### 3. Użycie w kodzie (opcjonalne)

```python
# W __init__.py lub main.py
from projektor import install
install()
```

**To wszystko!** Błędy będą automatycznie przechwytywane i logowane.

---

## Metody Integracji

### 1. Automatyczna Instalacja (najprostsza)

```python
# W głównym __init__.py projektu
from projektor import install
install()
```

**Korzyści:**
- Zero zmian w kodzie aplikacji
- Przechwytuje wszystkie niezłapane wyjątki
- Włącza monitorowanie plików

### 2. Dekoratory (selektywna)

```python
from projektor import track_errors, track_async_errors

@track_errors
def process_data(data):
    # błędy będą logowane
    return transform(data)

@track_async_errors
async def fetch_data(url):
    # działa też z async
    return await http_get(url)

# Z dodatkowymi opcjami
@track_errors(
    reraise=False,               # Nie rzucaj wyjątku dalej
    context={"module": "parser"},# Dodatkowy kontekst
)
def risky_operation():
    pass
```

### 3. Context Manager (dla bloków kodu)

```python
from projektor import ErrorTracker

def process_items(items):
    results = []
    for item in items:
        with ErrorTracker(reraise=False) as tracker:
            result = process_single(item)
            results.append(result)
        
        if tracker.had_error:
            print(f"Error: {tracker.error}")
            results.append(None)
    
    return results
```

### 4. Plugin pytest (dla testów)

```python
# conftest.py
pytest_plugins = ["projektor.pytest_plugin"]
```

Lub w pyproject.toml:
```toml
[tool.pytest.ini_options]
addopts = "-p projektor.pytest_plugin"
```

### 5. Zmienne Środowiskowe

```bash
export PROJEKTOR_ENABLED=true
export PROJEKTOR_AUTO_FIX=false
export PROJEKTOR_WATCH_PATHS="src:tests:examples"
export PROJEKTOR_REPORT_FILE=".projektor/errors.log"
```

## Konfiguracja

### projektor.yaml

```yaml
integration:
  enabled: true
  global_handler: true
  auto_fix: false
  priority: high
  default_labels:
    - projektor
    - auto-reported
  
  workflows:
    error-reporter:
      trigger: on_error
      enabled: true
      auto_fix: false
      priority: high
      labels:
        - runtime-error
    
    test-failure-tracker:
      trigger: on_test_fail
      enabled: true
      auto_fix: true
      priority: critical
      labels:
        - test-failure
```

### pyproject.toml

```toml
[tool.projektor]
enabled = true
global_handler = true
auto_fix = false
priority = "high"
default_labels = ["projektor", "auto-reported"]

[tool.projektor.workflows.error-reporter]
trigger = "on_error"
enabled = true
auto_fix = false
priority = "high"
labels = ["runtime-error"]
```

### Zmienne środowiskowe

```bash
PROJEKTOR_ENABLED=true
PROJEKTOR_AUTO_FIX=false
PROJEKTOR_GLOBAL_HANDLER=true
PROJEKTOR_PRIORITY=high
```

## Workflows (podobne do CI/CD)

Workflows to akcje uruchamiane automatycznie na zdarzeniach:

| Trigger | Kiedy uruchamiany |
|---------|-------------------|
| `on_error` | Przy wystąpieniu błędu |
| `on_test_fail` | Gdy testy nie przejdą |
| `on_commit` | Po commicie |
| `on_start` | Przy starcie aplikacji |
| `on_success` | Po pomyślnym zakończeniu |

### Przykład własnego hooka

```python
from projektor.integration import Hooks, HookType

hooks = Hooks()

@hooks.on_error
def notify_slack(ctx):
    """Wysyłaj notyfikację na Slack przy błędzie."""
    error = ctx.get('error')
    ticket_id = ctx.get('ticket_id')
    send_slack_message(f"Bug {ticket_id}: {error}")

@hooks.on_success
async def log_success(ctx):
    """Loguj sukces."""
    await log_to_database(ctx)
```

## Komendy CLI

```bash
# Inicjalizacja projektu
projektor init
projektor project init my-project

# Status projektu
projektor project status

# Inicjalizuj integrację
projektor integrate init --auto-fix --global-handler

# Status integracji
projektor integrate status

# Dodaj workflow
projektor integrate add-workflow my-workflow --trigger on_error --auto-fix

# Ręcznie zgłoś błąd
projektor integrate report-error "Database connection failed" -f src/db.py -l 42

# Monitorowanie plików (file watcher)
projektor watch

# Wyświetl ostatnie błędy
projektor errors -n 10

# Uruchom testy z trackingiem
projektor test run --coverage

# Praca nad ticketem z LLM
projektor work on TICKET-1 --auto-fix
projektor work on NLP2-2 --auto-fix
```

## Integracja z nlp2cmd (przykład)

### 1. Konfiguracja

W `nlp2cmd/projektor.yaml`:

```yaml
integration:
  enabled: true
  global_handler: true
  auto_fix: false
  
  workflows:
    nlp-error-tracker:
      trigger: on_error
      labels:
        - nlp2cmd
        - parsing-error
```

### 2. Kod

W `nlp2cmd/src/nlp2cmd/__init__.py`:

```python
from projektor.integration import install_global_handler

# Włącz śledzenie błędów
install_global_handler()
```

Lub dla konkretnych funkcji:

```python
from projektor.integration import catch_errors

@catch_errors
def parse_command(text: str) -> dict:
    # Błędy będą automatycznie rejestrowane
    return parser.parse(text)
```

### 3. Efekt

Gdy w nlp2cmd wystąpi błąd:
1. Projektor automatycznie utworzy ticket BUG
2. Ticket zawiera traceback, lokalizację błędu, kontekst
3. Jeśli `auto_fix=True`, projektor spróbuje naprawić błąd automatycznie

## API Programistyczne

```python
from projektor.integration import (
    ErrorHandler,
    catch_errors,
    projektor_guard,
    install_global_handler,
    uninstall_global_handler,
    Hooks,
    HookType,
    on_error,
    on_success,
    IntegrationConfig,
    load_integration_config,
)
```

### ErrorHandler

```python
handler = ErrorHandler(
    project_path="/path/to/project",
    auto_fix=True,
    priority=Priority.HIGH,
    labels=["custom-label"],
)

# Ręczne zgłoszenie błędu
try:
    risky_operation()
except Exception as e:
    ticket = handler.handle_exception(e, context={"user": "john"})
    print(f"Created ticket: {ticket.id}")
```

### IntegrationConfig

```python
from projektor.integration import load_integration_config, IntegrationConfig

# Załaduj z projektu
config = load_integration_config("/path/to/project")

# Lub utwórz ręcznie
config = IntegrationConfig(
    enabled=True,
    auto_fix=True,
    global_handler=True,
)
```
