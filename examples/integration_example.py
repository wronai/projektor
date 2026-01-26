"""
Przykład integracji Projektora z dowolnym projektem Python.

Ten przykład pokazuje jak:
1. Używać dekoratorów do automatycznego przechwytywania błędów
2. Używać context managerów
3. Instalować globalny exception handler
4. Konfigurować workflows podobne do CI/CD

Użycie w dowolnym projekcie:
    pip install projektor

    # W main.py lub __init__.py projektu:
    from projektor.integration import install_global_handler
    install_global_handler(auto_fix=True)
"""

from projektor.integration import (
    catch_errors,
    install_global_handler,
    projektor_guard,
    on_error,
    on_success,
    Hooks,
    HookType,
)
from projektor.core.ticket import Priority


# ==================== Przykład 1: Dekorator ====================

@catch_errors(auto_fix=False, priority=Priority.HIGH)
def risky_function(x: int, y: int) -> int:
    """Funkcja która może rzucić błąd - automatycznie utworzy ticket."""
    if y == 0:
        raise ValueError("Division by zero is not allowed!")
    return x // y


# ==================== Przykład 2: Context Manager ====================

def process_data(data: list) -> list:
    """Przetwarzanie danych z ochroną projektor_guard."""
    results = []
    
    with projektor_guard(auto_fix=True, context={"operation": "data_processing"}):
        for item in data:
            # Jakieś przetwarzanie które może się nie powieść
            if item is None:
                raise TypeError("None values are not supported")
            results.append(item * 2)
    
    return results


# ==================== Przykład 3: Hooki (podobne do CI/CD) ====================

hooks = Hooks()

@hooks.on_error
def notify_on_error(ctx):
    """Hook wywoływany przy każdym błędzie."""
    print(f"[ALERT] Error occurred: {ctx.get('error', 'Unknown')}")
    # Można tu dodać: wysłanie na Slack, email, itp.


@hooks.on_success
async def log_success(ctx):
    """Hook wywoływany po sukcesie."""
    print(f"[OK] Operation completed: {ctx.get('operation', 'Unknown')}")


# ==================== Przykład 4: Globalny Handler ====================

def setup_projektor():
    """Wywołaj na początku aplikacji."""
    install_global_handler(auto_fix=True)
    print("[projektor] Global error handler installed")


# ==================== Przykład dla nlp2cmd ====================

def nlp2cmd_integration_example():
    """
    Przykład integracji z projektem nlp2cmd.
    
    W nlp2cmd/src/nlp2cmd/__init__.py dodaj:
    
    ```python
    from projektor.integration import install_global_handler
    
    # Na początku modułu
    install_global_handler(auto_fix=False)
    ```
    
    Lub dla konkretnych funkcji:
    
    ```python
    from projektor.integration import catch_errors
    
    @catch_errors
    def parse_command(text: str) -> dict:
        # ... parsing logic
        pass
    ```
    """
    pass


# ==================== Konfiguracja przez projektor.yaml ====================

EXAMPLE_PROJEKTOR_YAML = """
# projektor.yaml - przykładowa konfiguracja integracji

project:
  name: my-project
  language: python
  version: 1.0.0

orchestration:
  auto_commit: true
  run_tests: true
  max_iterations: 10

# Konfiguracja integracji (podobna do CI/CD workflows)
integration:
  enabled: true
  global_handler: true
  auto_fix: false
  priority: high
  default_labels:
    - projektor
    - auto-reported
  
  # Workflows - uruchamiane na zdarzeniach
  workflows:
    error-reporter:
      trigger: on_error
      enabled: true
      auto_fix: false
      priority: high
      labels:
        - runtime-error
        - needs-investigation
    
    test-failure-tracker:
      trigger: on_test_fail
      enabled: true
      auto_fix: true
      priority: critical
      labels:
        - test-failure
        - regression
    
    post-commit-check:
      trigger: on_commit
      enabled: true
      labels:
        - committed
"""


# ==================== Konfiguracja przez pyproject.toml ====================

EXAMPLE_PYPROJECT_TOML = """
# pyproject.toml - sekcja [tool.projektor]

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
labels = ["runtime-error", "needs-investigation"]

[tool.projektor.workflows.test-failure-tracker]
trigger = "on_test_fail"
enabled = true
auto_fix = true
priority = "critical"
labels = ["test-failure", "regression"]
"""


if __name__ == "__main__":
    print("=== Projektor Integration Examples ===\n")
    
    # Przykład 1
    print("1. Testing @catch_errors decorator...")
    try:
        result = risky_function(10, 2)
        print(f"   Result: {result}")
        
        # To utworzy ticket
        # risky_function(10, 0)
    except ValueError as e:
        print(f"   Caught error (ticket created): {e}")
    
    # Przykład 2
    print("\n2. Testing projektor_guard context manager...")
    try:
        results = process_data([1, 2, 3])
        print(f"   Results: {results}")
    except TypeError as e:
        print(f"   Caught error (ticket created): {e}")
    
    print("\n3. Configuration examples printed above in docstrings")
    print("\n=== Done ===")
