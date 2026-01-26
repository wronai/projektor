# Projektor 🚀

**LLM-Orchestrated Project Management with DevOps Automation**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Projektor to framework do automatycznego zarządzania projektami programistycznymi z wykorzystaniem LLM do planowania i orkiestracji procesów DevOps.

## 🎯 Filozofia

**LLM planuje. Kod wykonuje. System kontroluje.**

```
┌─────────────────────────────────────────────────────────────────┐
│                         PROJEKTOR                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │   Roadmap    │     │   Tickets    │     │  Milestones  │     │
│  │   & Vision   │────▶│   & Tasks    │────▶│   & Releases │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   LLM Orchestrator                       │    │
│  │              (Grok / Claude / GPT-4)                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │    Code      │     │    Tests     │     │     Git      │     │
│  │   Executor   │     │    Runner    │     │   Manager    │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   DevOps Pipeline                        │    │
│  │           (CI/CD, Deploy, Monitor, Rollback)            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Funkcjonalności

### 🛡️ Monitorowanie Błędów (Nieinwazyjne)
- **Automatyczne przechwytywanie** - globalny exception handler
- **Monitorowanie plików** - wykrywanie błędów składni przy zapisie
- **Integracja z pytest** - automatyczne raportowanie błędów testów
- **Wielopoziomowe raportowanie** - konsola, plik, GitHub Issues
- **Auto-fix z LLM** - automatyczna naprawa błędów

### 🎫 Zarządzanie Projektami
- **Tickets** - Tworzenie, śledzenie i realizacja zadań
- **Roadmap** - Planowanie długoterminowe z wizją projektu
- **Milestones** - Kamienie milowe i wydania
- **Sprints** - Iteracyjne cykle rozwoju

### 🤖 Orkiestracja LLM
- **Planowanie** - LLM analizuje ticket i generuje plan implementacji
- **Dekompozycja** - Rozbicie złożonych zadań na atomowe kroki
- **Code Generation** - Generowanie kodu zgodnego z architekturą
- **Review** - Automatyczna analiza i sugestie ulepszeń

### 🔧 Automatyzacja DevOps
- **Code Execution** - Bezpieczne wykonywanie zmian z walidacją
- **Testing** - Automatyczne uruchamianie testów
- **Git Operations** - Commity, branch'e, merge'e
- **CI/CD** - Integracja z pipeline'ami

### 📊 Analiza Projektu
- **TOON Parser** - Analiza struktury projektu
- **Complexity Metrics** - Śledzenie złożoności kodu
- **Coverage Tracking** - Monitoring pokrycia testami
- **Progress Reports** - Raporty postępu realizacji

## 🚀 Szybki Start

### Instalacja

```bash
# Podstawowa instalacja
pip install projektor

# Z wsparciem LLM
pip install projektor[llm]

# Pełna instalacja (z dev tools)
pip install projektor[all]
```

### Konfiguracja

```bash
# (Rekomendowane) Skopiuj przykład i uzupełnij wartości
cp .env.example .env

# Następnie uzupełnij .env (OPENROUTER_API_KEY, OPENROUTER_MODEL, itp.)

# Alternatywnie możesz ustawić klucz API w shellu
export OPENROUTER_API_KEY="your-key"
# lub
export OPENAI_API_KEY="your-key"
```

### Użycie CLI

```bash
# Inicjalizacja projektu
projektor init

# Status projektu
projektor status

# Monitorowanie plików (file watcher)
projektor watch

# Wyświetl ostatnie błędy
projektor errors -n 10

# Tworzenie ticketu
projektor ticket create "Dodaj obsługę cache Redis" --priority high

# Realizacja ticketu (LLM + DevOps)
projektor work on PROJ-42

# Testy z trackingiem błędów
projektor test run --coverage
```

### Użycie w repo nie-Python (JS/TS, Go)

Jeśli pracujesz nad repozytorium w innym języku niż Python, Projektor może uruchamiać testy jako krok `run_command` (np. `npm test`, `make test`).

```bash
# JS/TS (npm)
projektor init -l typescript

# Go (Makefile)
projektor init -l go
```

Wygenerowany (lub uzupełniony) `projektor.yaml` powinien zawierać:

```yaml
orchestration:
  run_tests: false

extensions:
  test_command: "npm test"  # albo: "make test"
```

Projektor automatycznie dopnie krok testów do planu, jeśli plan nie zawiera testów, a `extensions.test_command` jest ustawione.

### Nieinwazyjne Monitorowanie Błędów

```python
# Najprostsza integracja - w __init__.py projektu:
from projektor import install
install()

# To wszystko! Błędy będą automatycznie przechwytywane.
```

Lub selektywnie z dekoratorami:

```python
from projektor import track_errors, track_async_errors

@track_errors
def process_data(data):
    return transform(data)

@track_async_errors(context={"component": "api"})
async def fetch_data(url):
    return await http_get(url)
```

Lub z context managerem:

```python
from projektor import ErrorTracker

with ErrorTracker(reraise=False) as tracker:
    result = risky_operation()

if tracker.had_error:
    print(f"Error logged: {tracker.ticket.id}")
```

### Użycie jako biblioteka

```python
from projektor import Project, Ticket, Orchestrator
from projektor.planning import Roadmap, Milestone, Sprint

# Załaduj projekt
project = Project.load("/path/to/project")

# Utwórz roadmap
roadmap = Roadmap(
    vision="System NLP do generowania komend DSL",
    milestones=[
        Milestone(
            name="v1.0 - Core",
            description="Podstawowa funkcjonalność",
            deadline="2025-03-01",
            tickets=["PROJ-1", "PROJ-2", "PROJ-3"]
        ),
        Milestone(
            name="v1.1 - Thermodynamic",
            description="Optymalizacja termodynamiczna",
            deadline="2025-06-01"
        )
    ]
)

# Utwórz sprint
sprint = Sprint(
    name="Sprint 1",
    goal="Redukcja złożoności cyklomatycznej",
    tickets=[
        Ticket(
            id="PROJ-42",
            title="Refaktoryzacja _prepare_shell_entities",
            description="Zredukuj CC z 91 do <15",
            priority="high",
            labels=["refactor", "complexity"]
        )
    ]
)

# Uruchom orkiestrator
orchestrator = Orchestrator(project, model="openrouter/x-ai/grok-3-fast")

# Realizuj ticket automatycznie
result = await orchestrator.work_on_ticket("PROJ-42")

print(f"Status: {result.status}")
print(f"Commits: {len(result.commits)}")
print(f"Tests: {result.test_results.passed}/{result.test_results.total}")
```

## 📁 Struktura Projektu

```
projektor/
├── src/projektor/
│   ├── __init__.py          # Główne eksporty
│   ├── cli.py               # Interfejs CLI
│   ├── core/                # Podstawowe modele
│   │   ├── project.py       # Model projektu
│   │   ├── ticket.py        # Model ticketu
│   │   ├── config.py        # Konfiguracja
│   │   └── events.py        # System zdarzeń
│   ├── planning/            # Planowanie
│   │   ├── roadmap.py       # Roadmapa projektu
│   │   ├── milestone.py     # Kamienie milowe
│   │   ├── sprint.py        # Sprinty
│   │   └── backlog.py       # Backlog
│   ├── orchestration/       # Orkiestracja LLM
│   │   ├── orchestrator.py  # Główny orkiestrator
│   │   ├── planner.py       # Planowanie zadań
│   │   └── executor.py      # Wykonawca planów
│   ├── devops/              # Automatyzacja DevOps
│   │   ├── git_ops.py       # Operacje Git
│   │   ├── test_runner.py   # Uruchamianie testów
│   │   ├── code_executor.py # Wykonywanie kodu
│   │   └── ci_cd.py         # Integracja CI/CD
│   ├── analysis/            # Analiza projektu
│   │   ├── toon_parser.py   # Parser TOON
│   │   ├── metrics.py       # Metryki kodu
│   │   └── reports.py       # Generowanie raportów
│   └── integrations/        # Integracje zewnętrzne
│       ├── github.py        # GitHub API
│       ├── jira.py          # Jira API
│       └── slack.py         # Slack notifications
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── getting-started.md
│   ├── configuration.md
│   ├── api-reference.md
│   └── examples/
├── examples/
│   ├── basic_usage.py
│   ├── sprint_workflow.py
│   └── ci_integration.py
├── pyproject.toml
└── README.md
```

## 🔄 Workflow

### 1. Planowanie (Planning)

```python
from projektor.planning import Roadmap, Milestone

# Zdefiniuj wizję projektu
roadmap = Roadmap(
    vision="Stworzenie najszybszego systemu NLP w Polsce",
    goals=[
        "Osiągnięcie <30ms latencji",
        "95% dokładność dla polskiego NLP",
        "Integracja z Bielik"
    ]
)

# Dodaj kamienie milowe
roadmap.add_milestone(Milestone(
    name="MVP",
    deadline="2025-02-01",
    acceptance_criteria=[
        "5 adapterów DSL działa",
        "Testy pokrywają 80% kodu",
        "Dokumentacja kompletna"
    ]
))
```

### 2. Tickety (Tickets)

```python
from projektor import Ticket, TicketType, Priority

# Utwórz ticket
ticket = Ticket(
    id="PROJ-42",
    type=TicketType.TASK,
    title="Zrefaktoryzuj wysoką złożoność w templates.py",
    description="""
    ## Problem
    Funkcja `_prepare_shell_entities` ma CC=91, co utrudnia utrzymanie.
    
    ## Rozwiązanie
    1. Wyodrębnij helper functions
    2. Użyj Strategy Pattern
    3. Dodaj testy jednostkowe
    
    ## Acceptance Criteria
    - [ ] CC < 15
    - [ ] 100% backward compatibility
    - [ ] Testy pokrywają nowe funkcje
    """,
    priority=Priority.HIGH,
    labels=["refactor", "complexity", "tech-debt"],
    story_points=5
)
```

### 3. Orkiestracja (Orchestration)

```python
from projektor import Orchestrator

# Uruchom orkiestrator
orchestrator = Orchestrator(project)

# LLM analizuje ticket i generuje plan
plan = await orchestrator.plan_ticket(ticket)

print(f"Plan: {plan.description}")
print(f"Kroki: {len(plan.steps)}")
for step in plan.steps:
    print(f"  - {step.action}: {step.description}")

# Wykonaj plan (z kontrolą)
result = await orchestrator.execute_plan(
    plan,
    auto_commit=True,
    run_tests=True,
    require_review=False  # True dla PR workflow
)
```

### 4. DevOps Pipeline

```python
from projektor.devops import Pipeline, Stage

# Zdefiniuj pipeline
pipeline = Pipeline(
    stages=[
        Stage("lint", commands=["ruff check ."]),
        Stage("test", commands=["pytest tests/"]),
        Stage("build", commands=["python -m build"]),
        Stage("deploy", commands=["./deploy.sh"], 
              condition="branch == 'main'")
    ]
)

# Uruchom po commicie
result = await pipeline.run()
```

## ⚙️ Konfiguracja

### projektor.yaml

```yaml
project:
  name: nlp2cmd
  version: 0.2.0
  language: python
  
llm:
  model: openrouter/x-ai/grok-3-fast
  temperature: 0.1
  max_tokens: 4000
  
orchestration:
  auto_commit: true
  run_tests: true
  max_iterations: 10
  
targets:
  max_complexity: 15
  min_coverage: 85
  
devops:
  git:
    branch_prefix: "feature/"
    commit_style: conventional
  ci:
    provider: github-actions
  notifications:
    slack_webhook: ${SLACK_WEBHOOK}
```

## 🧪 Testowanie

```bash
# Uruchom wszystkie testy
pytest

# Z pokryciem
pytest --cov=projektor --cov-report=html

# Tylko unit testy
pytest tests/unit/

# Testy integracyjne
pytest tests/integration/
```

## 📚 Dokumentacja

- [CLI](docs/cli.md)
- [Integration](docs/integration.md)

## 🤝 Integracje

| Platforma | Status | Opis |
|-----------|--------|------|
| GitHub | ✅ | Issues, PRs, Actions |
| GitLab | 🔄 | Issues, MRs, CI |
| Jira | ✅ | Tickets sync |
| Linear | 🔄 | Issues sync |
| Slack | ✅ | Notifications |
| Discord | 🔄 | Notifications |

## 📊 Metryki

Projektor śledzi:

- **Velocity** - Story points per sprint
- **Cycle Time** - Czas od ticketu do deploy
- **Code Quality** - Complexity, coverage, lint
- **LLM Efficiency** - Tokens, latency, cost
- **DevOps Health** - Build time, deploy frequency

## 🛡️ Bezpieczeństwo

- Kod generowany przez LLM jest walidowany przed wykonaniem
- Backup przed każdą modyfikacją
- Rollback w przypadku błędów
- `run_command` jest ograniczone do allowlisty bezpiecznych komend oraz (opcjonalnie) dokładnie do `extensions.test_command`
- Kontrola uprawnień dla operacji git

## 📄 Licencja

Apache 2.0 License - zobacz [LICENSE](LICENSE)

## 🙏 Podziękowania

- [LiteLLM](https://github.com/BerriAI/litellm) - Unified LLM interface
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
