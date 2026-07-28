# Contributing to Aegis

Thank you for your interest in contributing! This guide will get you set up.

## Quick Start

```bash
git clone https://github.com/synexian/aegis.git
cd aegis
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
# Add your OpenRouter API key to .env
pytest tests/ -q
```

## How to Contribute

1. Check existing issues or open a new one
2. Fork the repo and create a branch: `git checkout -b fix/your-description`
3. Make your changes and write tests
4. Run `pytest tests/ -q` - all must pass
5. Open a pull request using the template

## What We Need Help With

| Priority | Item | Complexity |
|---|---|---|
| High | GitHub repository analysis | Medium |
| High | Test coverage for all 8 analyzers | Low |
| Medium | Named weight presets (security/startup/balanced) | Low |
| Medium | Trend tracking across runs | Medium |
| Low | VS Code extension | High |

## Code Standards

- Python 3.10+, type annotations encouraged
- `ruff check synexian/` for linting
- Docstrings on all public functions
- Tests required for all new features

## Questions?

Open a Discussion or email contact@synexian.dev
