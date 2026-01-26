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

## Repozytoria nie-Python (JS/TS, Go)

Jeśli używasz Projektora w repozytorium nie będącym Pythonem, testy mogą być uruchamiane jako krok `run_command` skonfigurowany w `projektor.yaml`.

Przykład:

```yaml
orchestration:
  run_tests: false

extensions:
  test_command: "npm test"  # albo: "make test"
```

Wyniki tego kroku są zapisywane w `.projektor/runs/<TICKET_timestamp>/` jako:

- `plan_test_command.json`
- `plan_test_command_stdout.txt`
- `plan_test_command_stderr.txt`

I można je podejrzeć przez CLI:

```bash
projektor work logs TICKET-1 --show plan_test_command_stdout
projektor work logs TICKET-1 --show plan_test_command_stderr
```

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

## Troubleshooting

### 401 Unauthorized (OpenRouter) / "No cookie auth credentials found"

Ten błąd prawie zawsze oznacza, że **proces `projektor` nie widzi klucza API** albo używasz innej wersji `projektor` niż tej z repo.

1. **Sprawdź co widzi projektor**:

```bash
projektor -p . doctor
```

2. **Upewnij się, że `.env` jest w katalogu projektu** (np. `nlp2cmd/.env`), a nie tylko w repo `projektor/`:

```env
OPENROUTER_API_KEY=sk-or-v1-...
```

3. **Upewnij się, że uruchamiasz poprawną wersję projektora**.

Jeśli widzisz stacktrace typu:

```
.../venv/lib/.../site-packages/projektor/...
```

to uruchamiasz **zainstalowaną paczkę** z venv. Żeby używać wersji z repo (z najnowszymi poprawkami), zainstaluj ją w trybie editable w tym samym venv:

```bash
# uruchom w aktywnym venv projektu (np. nlp2cmd/venv)
pip uninstall -y projektor
pip install -e /home/tom/github/wronai/projektor[llm]
```

4. **Szybki test klucza**:

```bash
python -c "import os; print('OPENROUTER_API_KEY set:', bool(os.getenv('OPENROUTER_API_KEY')))"
```

## Przykłady Integracji z Projektami

### nlp2cmd - Natural Language to Commands

```yaml
# projektor.yaml
project:
  name: nlp2cmd
  version: "1.0.40"
  description: "Natural Language to Domain-Specific Commands"
  language: python

integration:
  enabled: true
  global_handler: true
  auto_fix: false
  watch_paths:
    - src/nlp2cmd
    - tests
  workflows:
    error-reporter:
      trigger: on_error
      labels: [nlp2cmd, runtime-error]
    test-failure-tracker:
      trigger: on_test_fail
      priority: critical
```

```python
# src/nlp2cmd/__init__.py
try:
    from projektor import install
    install()
except ImportError:
    pass
```

### devix - Automated Development System

```yaml
# projektor.yaml
project:
  name: devix
  version: "2.1.8"
  description: "Automated development and code repair system"
  language: python

integration:
  enabled: true
  global_handler: true
  watch_paths:
    - src/devix
    - tests
  workflows:
    code-analysis-error:
      trigger: on_error
      labels: [devix, analysis-error]
    supervisor-error:
      trigger: on_error
      labels: [supervisor, critical]
      conditions:
        file_pattern: "*/supervisor.py"
```

### curllm - Browser Automation with LLM

```yaml
# projektor.yaml
project:
  name: curllm
  version: "1.0.40"
  description: "Browser Automation with Local LLM"
  language: python

integration:
  enabled: true
  global_handler: true
  watch_paths:
    - curllm_core
    - functions
  workflows:
    browser-error:
      trigger: on_error
      labels: [curllm, browser-automation]
    llm-error:
      trigger: on_error
      labels: [llm, inference-error]
      conditions:
        file_pattern: "*/llm/*"
```

### text2dsl - Voice CLI Navigation

```yaml
# projektor.yaml
project:
  name: text2dsl
  version: "0.2.1"
  description: "Głosowa nawigacja CLI z kontekstowym wsparciem"
  language: python

integration:
  enabled: true
  global_handler: true
  watch_paths:
    - text2dsl
    - tests
  workflows:
    voice-error:
      trigger: on_error
      labels: [text2dsl, voice-processing]
    dsl-parsing-error:
      trigger: on_error
      labels: [dsl, parsing]
```

### Uniwersalny szablon dla dowolnego projektu

```yaml
# projektor.yaml - skopiuj i dostosuj
project:
  name: YOUR_PROJECT_NAME
  version: "1.0.0"
  language: python

integration:
  enabled: true
  global_handler: true
  auto_fix: false
  priority: high
  
  watch_paths:
    - src
    - tests
  
  ignore_patterns:
    - "*.pyc"
    - "__pycache__"
    - ".git"
    - ".venv"
  
  report_to_console: true
  report_to_file: true
  report_file: .projektor/errors.log
  
  workflows:
    error-reporter:
      trigger: on_error
      enabled: true
      labels:
        - runtime-error
        - auto-reported
    
    test-failure-tracker:
      trigger: on_test_fail
      enabled: true
      priority: critical
      labels:
        - test-failure

orchestration:
  auto_commit: false
  run_tests: true

targets:
  max_complexity: 15
  min_coverage: 85
```

### Efekt integracji

Po skonfigurowaniu, gdy w projekcie wystąpi błąd:

```
$ python my_script.py
Traceback (most recent call last):
  File "my_script.py", line 10, in process
    return data / 0
ZeroDivisionError: division by zero

[projektor] Bug ticket created: PROJ-42
[projektor] Title: [Auto] ZeroDivisionError: division by zero
```

Ticket automatycznie zawiera:
- Pełny traceback
- Lokalizację błędu (plik, linia, funkcja)
- Zmienne lokalne (opcjonalnie)
- Kontekst wywołania

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
