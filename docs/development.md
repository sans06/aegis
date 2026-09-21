# Development Guide

## Setting Up Development Environment

### Prerequisites

- Python 3.12 or higher
- pip
- virtualenv (recommended)
- Git

### Setup Steps

1. **Clone the repository**

```bash
git clone https://github.com/synexian/synexian-agent.git
cd synexian-agent
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**

```bash
pip install -e ".[dev]"
```

4. **Set up pre-commit hooks** (optional)

```bash
pre-commit install
```

5. **Configure environment**

```bash
cp .env.example .env
# Edit .env and add your API key
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=synexian --cov-report=html --cov-report=term
```

### Run Specific Test File

```bash
pytest tests/test_models.py
```

### Run Specific Test

```bash
pytest tests/test_models.py::TestMetricValue::test_metric_value_creation
```

### Run Integration Tests Only

```bash
pytest tests/test_integration.py
```

## Code Quality

### Format Code

```bash
# Format with black
black synexian/

# Sort imports
isort synexian/
```

### Lint Code

```bash
# Check with flake8
flake8 synexian/

# Check with ruff
ruff check synexian/
```

### Type Checking

```bash
mypy synexian/
```

### Run All Quality Checks

```bash
# Format
black synexian/ tests/
isort synexian/ tests/

# Lint
flake8 synexian/
ruff check synexian/

# Type check
mypy synexian/

# Test
pytest --cov=synexian
```

## Project Structure

```
synexian-agent/
├── synexian/           # Main package
│   ├── analyzers/      # All analyzer implementations
│   ├── ai/             # AI integration
│   ├── core/           # Core engine and processing
│   ├── input/          # Input handlers
│   ├── models/         # Data models
│   ├── reports/        # Report generators
│   ├── utils/          # Utility functions
│   ├── cli.py          # CLI application
│   └── config.py       # Configuration
├── tests/              # Test suite
├── scripts/            # Utility scripts
├── docs/               # Documentation
└── config/             # Configuration files
```

## Adding a New Analyzer

### 1. Create Analyzer File

```bash
mkdir -p synexian/analyzers/my_analyzer
touch synexian/analyzers/my_analyzer/__init__.py
touch synexian/analyzers/my_analyzer/analyzer.py
```

### 2. Implement Analyzer

```python
# synexian/analyzers/my_analyzer/analyzer.py

from synexian.analyzers.base import BaseAnalyzer, AnalysisContext
from synexian.constants import ResultStatus
from synexian.models import AnalysisResult


class MyAnalyzer(BaseAnalyzer):
    """My custom analyzer."""

    @property
    def name(self) -> str:
        return "my_analyzer"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def analyze(self, context: AnalysisContext) -> AnalysisResult:
        # Your analysis logic here
        issues = []
        metrics = {}

        # Process files
        for file_path in context.files:
            if not self.should_analyze_file(file_path):
                continue

            # Analyze file...

        return AnalysisResult(
            analyzer_name=self.name,
            analyzer_version=self.version,
            status=ResultStatus.SUCCESS,
            issues=issues,
            metrics=metrics,
        )
```

### 3. Register Analyzer

```python
# synexian/cli.py

from synexian.analyzers.my_analyzer.analyzer import MyAnalyzer

# In the analyze function:
if config.analyzers.get("my_analyzer", {}).enabled:
    analyzers.append(MyAnalyzer(config.analyzers["my_analyzer"]))
```

### 4. Add Configuration

```yaml
# config/default_config.yaml

analyzers:
  my_analyzer:
    enabled: true
    thresholds:
      my_metric: 10
    options:
      my_option: value
```

### 5. Write Tests

```python
# tests/test_my_analyzer.py

import pytest
from synexian.analyzers.my_analyzer.analyzer import MyAnalyzer


class TestMyAnalyzer:
    @pytest.mark.asyncio
    async def test_basic_analysis(self, sample_python_file, test_config):
        analyzer = MyAnalyzer(test_config.analyzers["my_analyzer"])
        # ... test logic
```

## Adding a New Report Format

### 1. Create Reporter

```python
# synexian/reports/my_reporter.py

from pathlib import Path
from synexian.models import AnalysisReport
from synexian.reports.base import BaseReporter


class MyReporter(BaseReporter):
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def generate(self, report: AnalysisReport) -> Path:
        # Generate report
        output_path = self.output_dir / "report.xyz"
        # ... write report
        return output_path
```

### 2. Register in CLI

```python
# synexian/cli.py

from synexian.reports.my_reporter import MyReporter

# In analyze function:
if "xyz" in config.output_formats:
    reporter = MyReporter(config.output_dir)
    path = reporter.generate(report)
```

## Debugging

### Enable Debug Logging

```bash
synexian analyze ./project --verbose
```

### Use Python Debugger

```python
import pdb; pdb.set_trace()
```

### Check Diagnostics

```python
from synexian.config import load_config

config = load_config()
errors = config.validate()
print(errors)
```

## Contributing

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public APIs
- Keep functions focused and small
- Max line length: 100 characters

### Commit Messages

```
type(scope): subject

body

footer
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(analyzer): add performance analyzer

Implement new analyzer for detecting performance issues
including N+1 queries and inefficient loops.

Closes #123
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Update documentation
6. Run quality checks
7. Submit pull request

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run tests
4. Build package: `python -m build`
5. Tag release: `git tag v0.1.0`
6. Push to PyPI: `python -m twine upload dist/*`

## Useful Commands

```bash
# Check dependencies
python scripts/check_dependencies.py

# Run benchmarks
python scripts/benchmark.py

# Generate demo reports
python scripts/generate_demo.py

# Setup environment
python scripts/setup.py
```

## Troubleshooting

### Import Errors

```bash
# Reinstall in development mode
pip install -e .
```

### Test Failures

```bash
# Run with verbose output
pytest -vv

# Run specific test
pytest tests/test_models.py -k test_metric_value_creation
```

### Type Errors

```bash
# Check specific file
mypy synexian/cli.py

# Ignore missing imports
mypy --ignore-missing-imports synexian/
```


==========================================================
© 2026 Synexian Labs Private Limited. All rights reserved.
