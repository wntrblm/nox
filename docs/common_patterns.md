# Common Testing Patterns: Real-World Nox Workflows

This guide shows battle-tested Nox patterns from production projects. Copy-paste ready.

## Pattern 1: Multi-Python Version Matrix Testing

**Problem:** Your library needs to support Python 3.8-3.12.

**Solution:**

```python
# noxfile.py
import nox

@nox.session(python=["3.8", "3.9", "3.10", "3.11", "3.12"])
def tests(session):
    """Run tests across all Python versions."""
    session.install("pytest", "pytest-cov")
    session.install("-e", ".")
    session.run(
        "pytest",
        "--cov=myproject",
        "--cov-report=term-missing",
        "--cov-report=html",
        *session.posargs,  # Pass through CLI args
    )
```

**Usage:**
```bash
# Run all versions
nox -s tests

# Run specific version
nox -s tests-3.11

# Run with pytest args
nox -s tests -- -v tests/test_api.py::test_login
```

**Why it works:** Nox creates isolated virtualenvs for each Python version, ensuring no cross-contamination.

---

## Pattern 2: Linting & Formatting Pipeline

**Problem:** You need to run black, isort, flake8, mypy before commits.

**Solution:**

```python
# noxfile.py
import nox

BLACK_PATHS = ["src", "tests", "noxfile.py"]

@nox.session
def format(session):
    """Auto-format code with black and isort."""
    session.install("black", "isort")
    session.run("isort", *BLACK_PATHS)
    session.run("black", *BLACK_PATHS)

@nox.session
def lint(session):
    """Run all linters (flake8, black --check, isort --check, mypy)."""
    session.install("flake8", "black", "isort", "mypy")
    
    # Check formatting
    session.run("black", "--check", "--diff", *BLACK_PATHS)
    session.run("isort", "--check", "--diff", *BLACK_PATHS)
    
    # Lint
    session.run("flake8", "src", "tests")
    session.run("mypy", "src")

@nox.session
def fix(session):
    """Auto-fix all linting issues (runs format first)."""
    session.notify("format")
    session.install("autopep8")
    session.run("autopep8", "--in-place", "--recursive", *BLACK_PATHS)
```

**Usage:**
```bash
# Check everything (CI)
nox -s lint

# Auto-fix (local development)
nox -s fix

# Just format
nox -s format
```

**Pro tip:** Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
nox -s lint
```

---

## Pattern 3: Dependency Matrix Testing

**Problem:** Your project supports multiple versions of Django/FastAPI/SQLAlchemy.

**Solution:**

```python
# noxfile.py
import nox

@nox.session
@nox.parametrize(
    "django",
    ["3.2", "4.0", "4.1", "4.2"],
)
def tests_django(session, django):
    """Test against multiple Django versions."""
    session.install("pytest", "pytest-django")
    session.install(f"django=={django}")
    session.install("-e", ".")
    session.run("pytest", "tests/")

@nox.session
@nox.parametrize(
    "sqlalchemy,postgres",
    [
        ("1.4", "psycopg2-binary==2.9"),
        ("2.0", "psycopg2-binary==2.9"),
        ("2.0", "psycopg[binary]==3.1"),
    ],
)
def tests_db(session, sqlalchemy, postgres):
    """Test with different SQLAlchemy + PostgreSQL driver combos."""
    session.install("pytest")
    session.install(f"sqlalchemy=={sqlalchemy}")
    session.install(postgres)
    session.install("-e", ".")
    session.run("pytest", "tests/db/")
```

**Usage:**
```bash
# Run all Django combinations
nox -s tests_django

# Run specific Django version
nox -s "tests_django(django='4.2')"

# List all parametrized sessions
nox --list
```

**Output:**
```
Sessions defined in noxfile.py:
* tests_django(django='3.2')
* tests_django(django='4.0')
* tests_django(django='4.1')
* tests_django(django='4.2')
* tests_db(sqlalchemy='1.4', postgres='psycopg2-binary==2.9')
* tests_db(sqlalchemy='2.0', postgres='psycopg2-binary==2.9')
* tests_db(sqlalchemy='2.0', postgres='psycopg[binary]==3.1')
```

---

## Pattern 4: Documentation Building & Testing

**Problem:** Build Sphinx docs and check for broken links.

**Solution:**

```python
# noxfile.py
import nox
from pathlib import Path

@nox.session
def docs(session):
    """Build documentation with Sphinx."""
    session.install("sphinx", "sphinx-rtd-theme", "myst-parser")
    session.install("-e", ".")
    
    # Clean old build
    session.run("rm", "-rf", "docs/_build", external=True)
    
    # Build HTML
    session.run(
        "sphinx-build",
        "-W",  # Treat warnings as errors
        "-b", "html",
        "docs/source",
        "docs/_build/html"
    )
    
    # Print success message
    index_file = Path("docs/_build/html/index.html").resolve()
    session.log(f"✅ Docs built successfully!")
    session.log(f"📄 Open: file://{index_file}")

@nox.session
def docs_linkcheck(session):
    """Check for broken links in documentation."""
    session.install("sphinx", "sphinx-rtd-theme")
    session.install("-e", ".")
    session.run(
        "sphinx-build",
        "-b", "linkcheck",
        "docs/source",
        "docs/_build/linkcheck"
    )

@nox.session
def docs_live(session):
    """Live-reload docs server for local development."""
    session.install("sphinx", "sphinx-rtd-theme", "sphinx-autobuild")
    session.install("-e", ".")
    session.run(
        "sphinx-autobuild",
        "--open-browser",
        "--watch", "src/",
        "docs/source",
        "docs/_build/html"
    )
```

**Usage:**
```bash
# Build docs
nox -s docs

# Check links
nox -s docs_linkcheck

# Live preview (auto-reload on changes)
nox -s docs_live
```

---

## Pattern 5: Pre-commit Hooks Integration

**Problem:** Run nox sessions as pre-commit hooks.

**Solution:**

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: nox-lint
        name: Run nox lint
        entry: nox -s lint
        language: system
        pass_filenames: false
        
      - id: nox-tests
        name: Run nox tests (fast)
        entry: nox -s tests-3.11 -- -m "not slow"
        language: system
        pass_filenames: false
```

In `noxfile.py`, add a fast test session:

```python
@nox.session(python="3.11")
def tests_fast(session):
    """Quick tests for pre-commit (skip slow integration tests)."""
    session.install("pytest", "pytest-xdist")
    session.install("-e", ".")
    session.run(
        "pytest",
        "-m", "not slow",  # Skip tests marked with @pytest.mark.slow
        "-n", "auto",      # Parallel execution
        "--tb=short",      # Short tracebacks
    )
```

**Usage:**
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Now every commit runs nox automatically
git commit -m "feat: add new feature"
# (nox runs in background)
```

---

## Pattern 6: CI/CD Optimization

**Problem:** GitHub Actions is slow because it reinstalls everything.

**Solution:**

```python
# noxfile.py
import nox

# Reuse virtualenvs in CI
nox.options.reuse_existing_virtualenvs = True

@nox.session(python="3.11")
def ci(session):
    """Optimized session for CI environments."""
    # Install with cache-friendly constraints
    session.install("--upgrade", "pip", "setuptools", "wheel")
    session.install("pytest", "pytest-cov", "pytest-xdist")
    session.install("-e", ".")
    
    # Run tests with coverage and parallel execution
    session.run(
        "pytest",
        "--cov=myproject",
        "--cov-report=xml",  # For codecov
        "--cov-report=term",
        "-n", "auto",
        "--maxfail=5",  # Stop after 5 failures
        *session.posargs
    )
```

GitHub Actions workflow:

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
      
      - name: Install nox
        run: pip install nox
      
      - name: Run tests
        run: nox -s ci
        
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
```

---

## Pattern 7: Environment-Specific Sessions

**Problem:** Different test requirements for dev vs CI vs production.

**Solution:**

```python
# noxfile.py
import nox
import os

IS_CI = os.environ.get("CI") == "true"
IS_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"

@nox.session
def tests(session):
    """Tests with environment detection."""
    session.install("pytest")
    
    if IS_CI:
        # CI-specific settings
        session.install("pytest-xdist", "pytest-timeout")
        session.run(
            "pytest",
            "-n", "auto",
            "--timeout=300",  # 5min timeout per test
            "--strict-markers",
            *session.posargs
        )
    else:
        # Local development - faster feedback
        session.install("pytest-watch")
        session.run("ptw", "--", "-v", *session.posargs)

@nox.session
def integration(session):
    """Integration tests (requires Docker)."""
    if IS_CI:
        # Use GitHub Actions services
        db_url = "postgresql://postgres:postgres@localhost:5432/test"
    else:
        # Use local Docker
        session.run("docker-compose", "up", "-d", external=True)
        db_url = "postgresql://localhost:5432/test"
    
    session.install("pytest", "sqlalchemy", "psycopg2-binary")
    session.install("-e", ".")
    session.run("pytest", "tests/integration/", env={"DATABASE_URL": db_url})
```

---

## Pattern 8: Reusable Session Components

**Problem:** DRY - multiple sessions need the same setup.

**Solution:**

```python
# noxfile.py
import nox

def install_test_deps(session):
    """Reusable function for test dependencies."""
    session.install("pytest", "pytest-cov", "pytest-mock")
    session.install("-e", ".")

def run_pytest(session, *args):
    """Reusable pytest runner."""
    session.run(
        "pytest",
        "--cov=myproject",
        "--cov-report=term-missing",
        *args,
        *session.posargs
    )

@nox.session(python=["3.10", "3.11", "3.12"])
def tests(session):
    """Unit tests."""
    install_test_deps(session)
    run_pytest(session, "tests/unit/")

@nox.session
def tests_integration(session):
    """Integration tests."""
    install_test_deps(session)
    session.install("docker")  # Extra dep
    run_pytest(session, "tests/integration/", "-v")

@nox.session
def tests_e2e(session):
    """End-to-end tests."""
    install_test_deps(session)
    session.install("playwright")
    session.run("playwright", "install", "chromium")
    run_pytest(session, "tests/e2e/", "--headed")
```

---

## Troubleshooting Common Issues

### Issue: "No module named 'myproject'"

**Problem:** Package not installed in virtualenv.

**Solution:**
```python
@nox.session
def tests(session):
    session.install("-e", ".")  # ← Install in editable mode
    session.run("pytest")
```

### Issue: Sessions are too slow

**Problem:** Recreating virtualenvs every run.

**Solution:**
```python
# Add to noxfile.py
nox.options.reuse_existing_virtualenvs = True
```

Or use CLI flag:
```bash
nox -r  # Short for --reuse-existing-virtualenvs
```

### Issue: "session not found"

**Problem:** Typo in session name.

**Solution:**
```bash
# List all available sessions
nox --list

# Search for specific session
nox --list | grep test
```

### Issue: Slow pip installs

**Problem:** Re-downloading packages.

**Solution:**
```python
@nox.session
def tests(session):
    # Use constraints file to cache dependencies
    session.install("-r", "requirements-test.txt", "-c", "constraints.txt")
    session.install("-e", ".")
```

Or use pip cache:
```bash
export PIP_CACHE_DIR=~/.cache/pip
nox -s tests
```

---

## Advanced: Custom Session Decorators

```python
# noxfile.py
import nox
from functools import wraps

def install_project(func):
    """Decorator to auto-install project in editable mode."""
    @wraps(func)
    def wrapper(session):
        session.install("-e", ".")
        return func(session)
    return wrapper

def notify_on_failure(func):
    """Decorator to send notification on session failure."""
    @wraps(func)
    def wrapper(session):
        try:
            return func(session)
        except Exception as e:
            session.error(f"❌ Session {session.name} failed: {e}")
            # Could integrate with Slack, email, etc.
            raise
    return wrapper

@nox.session
@install_project
@notify_on_failure
def tests(session):
    """Tests with auto-install and failure notifications."""
    session.run("pytest")
```

---

## Real-World Example: Full Production Noxfile

```python
# noxfile.py - Complete example from a production project
import nox
from pathlib import Path

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["lint", "tests"]  # Default sessions

PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]
SOURCE_PATHS = ["src", "tests", "noxfile.py"]

@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """Run unit and integration tests."""
    session.install("pytest", "pytest-cov", "pytest-xdist")
    session.install("-e", ".")
    session.run(
        "pytest",
        "--cov=myproject",
        "--cov-report=term-missing:skip-covered",
        "--cov-report=html",
        "--cov-report=xml",
        "-n", "auto",
        *session.posargs
    )

@nox.session
def lint(session):
    """Run all linters."""
    session.install("ruff", "mypy", "black", "isort")
    session.run("ruff", "check", *SOURCE_PATHS)
    session.run("black", "--check", *SOURCE_PATHS)
    session.run("isort", "--check", *SOURCE_PATHS)
    session.run("mypy", "src")

@nox.session
def format(session):
    """Auto-format all code."""
    session.install("black", "isort", "ruff")
    session.run("black", *SOURCE_PATHS)
    session.run("isort", *SOURCE_PATHS)
    session.run("ruff", "check", "--fix", *SOURCE_PATHS)

@nox.session
def docs(session):
    """Build documentation."""
    session.install("sphinx", "sphinx-rtd-theme", "myst-parser")
    session.install("-e", ".")
    output_dir = Path("docs/_build/html")
    session.run("sphinx-build", "-W", "-b", "html", "docs", str(output_dir))
    session.log(f"✅ Docs: file://{output_dir.resolve()}/index.html")

@nox.session
def ci(session):
    """Run all CI checks."""
    session.notify("lint")
    session.notify("tests-3.11")
    session.notify("docs")
```

**Usage in CI:**
```bash
# GitHub Actions
nox -s ci

# Local pre-push check
nox
```

---

**More patterns?** Check the [official tutorial](https://nox.readthedocs.io/en/stable/tutorial.html) or [examples repository](https://github.com/wntrblm/nox/tree/main/docs/cookbook).
