# Contributing to Aegis

Thank you for your interest in contributing to Aegis! This document
explains how to get set up, how to contribute, and what we expect
from contributors.

---

## Quick Start

```bash
# Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/aegis.git
cd aegis

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Add your OpenRouter API key to .env (optional for static analysis)

# Run the test suite to verify your setup
pytest tests/ -q
# Expected: 212 passed
```

---

## How to Contribute

### Reporting Bugs

Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md).

Please include:
- Your Python version (`python --version`)
- Aegis version (`synexian version`)
- The command you ran
- The full error output
- The smallest code example that triggers the bug

### Requesting Features

Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md).

Describe:
- What problem you are trying to solve
- What behavior you expect
- Whether you are willing to implement it

### Submitting Code

1. **Check existing issues** — comment on the issue you want to work on
   so we can confirm the approach before you invest time.

2. **Create a branch** from `main`:
   ```bash
   git checkout -b fix/your-description
   # or
   git checkout -b feature/your-description
   ```

3. **Make your changes** — see the Development Guide below.

4. **Write or update tests** — all changes require tests.
   Run the test suite before submitting:
   ```bash
   pytest tests/ -q
   ```

5. **Open a pull request** — use the PR template. Link the issue
   your PR resolves.

---

## Development Guide

### Project Structure

```
synexian/
├── cli.py              Entry point — do not add business logic here
├── config.py           Configuration system
├── constants.py        Shared enums and defaults
├── exceptions.py       Custom exception hierarchy
├── analyzers/          One subfolder per analyzer
│   ├── base.py         BaseAnalyzer — extend this for new analyzers
│   └── */analyzer.py   Each analyzer implementation
├── core/
│   ├── analyzer_engine.py   Orchestration
│   ├── scoring_engine.py    Scoring formula
│   └── result_aggregator.py Deduplication
├── ai/                 OpenRouter API client
├── models/             Shared dataclasses
├── input/              File discovery handlers
├── reports/            Output formatters
└── utils/              Shared helpers
```

### Adding a New Analyzer

1. Create a new subfolder: `synexian/analyzers/your_analyzer/`
2. Add `__init__.py` and `analyzer.py`
3. Extend `BaseAnalyzer` from `synexian/analyzers/base.py`
4. Implement the `analyze(context: AnalysisContext) -> AnalysisResult` method
5. Register in `synexian/cli.py` (add instantiation block)
6. Add weight in `synexian/constants.py` DEFAULT_ANALYZER_WEIGHTS
7. Write tests in `tests/test_your_analyzer.py`

### Code Standards

- **Python 3.10+** — use type annotations where practical
- **ruff** for linting (`ruff check synexian/`)
- **black** for formatting (`black synexian/ tests/`)
- **pytest** for tests — all new code needs tests
- **Docstrings** on all public classes and methods

### Running Specific Tests

```bash
# Run all tests
pytest tests/

# Run one test file
pytest tests/test_scoring_engine.py -v

# Run with coverage report
pytest tests/ --cov=synexian --cov-report=html
open htmlcov/index.html
```

---

## What We Are Looking For

The highest-priority contributions right now:

| Priority | Item | Complexity |
|---|---|---|
| 🔴 High | GitHub repository analysis (input/github_repo.py) | Medium |
| 🔴 High | Test coverage for architecture, edge_cases analyzers | Low |
| 🟠 Medium | Named weight presets (security, startup, balanced) | Low |
| 🟠 Medium | Trend tracking across multiple runs (JSON diff) | Medium |
| 🟡 Low | VS Code extension scaffolding | High |
| 🟡 Low | Multi-language support hints | High |

---

## Code of Conduct

Be kind. Be constructive. Be patient with maintainers — this is
an open-source project maintained by a small team.

Harassment of any kind will result in a permanent ban.

---

## Questions?

Open a [Discussion](https://github.com/synexian/aegis/discussions)
or email us at `contact@synexian.dev`.
