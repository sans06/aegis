# Aegis

**AI-Powered Software Quality Analysis CLI Tool**

Aegis is Synexian’s autonomous software quality analysis agent. It inspects codebases for complexity, security risks, architectural flaws, test quality, and edge cases, generating actionable, severity-driven reports to help teams ship reliable software.

## Features

### 8 Comprehensive Evaluation Methods Used

1. **Code Complexity Analysis**
   - Cyclomatic complexity (McCabe)
   - Halstead metrics (volume, difficulty, effort)
   - Cognitive complexity
   - Identifies overly complex code that's hard to maintain

2. **Security & Vulnerability Scanning**
   - OWASP Top 10 security checks
   - CWE vulnerability pattern detection
   - Dependency vulnerability scanning
   - Identifies security risks and vulnerabilities

3. **Code Style & Linting**
   - PEP8 compliance checking
   - Naming convention validation
   - Code formatting analysis
   - Ensures code follows Python best practices

4. **Architecture & Design Patterns**
   - SOLID principles validation
   - Design pattern detection (AI-powered ; Mistral: Devstral 2 )
   - Dependency graph analysis
   - Evaluates architectural quality

5. **Edge Cases & Boundary Value Analysis**
   - Boundary condition detection
   - Missing edge case identification
   - Input validation analysis
   - Finds gaps in error handling

6. **Test Quality & Mutation Coverage** 
   - Mutation testing score
   - Test coverage analysis
   - Assertion strength evaluation
   - Test pattern quality assessment
   - Goes beyond simple coverage metrics

7. **Cognitive Load & Maintainability**
   - Code readability metrics
   - Maintainability index calculation
   - Documentation quality vs complexity
   - AI-powered naming clarity analysis
   - Measures how easy code is to understand

8. **Custom Compliance Rules**
   - YAML-based rule definitions
   - AST-based pattern matching
   - Regex-based checks
   - Flexible custom rule engine

### Input Methods

- **Local Directory**: Analyze entire projects
- **Individual Files**: Quick single-file analysis
- **GitHub Repositories**: Clone and analyze remote repos (to be implemented in v2 )

### Output Formats

- **Interactive CLI**: Beautiful terminal output with Rich animations, progress bars, and tables
- **JSON**: Machine-readable format for CI/CD integration
- **HTML**: Interactive reports with visualizations and charts

### AI Integration

- Powered by **mistralai/devstral-2512:free** via OpenRouter
- 123B parameters, 256K context window
- Used for advanced pattern detection and architectural analysis
- Smart caching to reduce API costs

## Installation

### Prerequisites

- Python 3.10 or higher
- OpenRouter API key (free tier available)

### Setup

1. **Clone the repository**

```bash
https://github.com/RyoK3N/Aegis
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv

# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -e .

# Or for development
pip install -e ".[dev]"
```

4. **Set up environment variables**

```bash
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:

```env
OPENROUTER_API_KEY=your_api_key_here
```

To get an API key:
1. Visit [https://openrouter.ai](https://openrouter.ai)
2. Sign up for a free account
3. Generate an API key
4. The `mistralai/devstral-2512:free` model is completely free to use

## Usage

### Quick Start

**Analyze a local directory:**

```bash
aegis analyze ./my-project
```

**Analyze a single file:**

```bash
aegis analyze ./my-project/main.py
```

**Analyze a GitHub repository:**

```bash
aegis analyze https://github.com/username/repository
```

**Analyze with verbose output:**

```bash
aegis analyze ./my-project --verbose
```

### Advanced Usage

**Custom configuration file:**

```bash
aegis analyze ./my-project --config custom-config.yaml
```

**Specify output formats:**

```bash
# Generate JSON and HTML reports in addition to CLI output
aegis analyze ./my-project --output cli,json,html
```

**JSON output only (for CI/CD):**

```bash
aegis analyze ./my-project --output json
```

**View current configuration:**

```bash
aegis config-show
```

**Show version:**

```bash
aegis version
```

### All Available Commands

```bash
# Main analysis command
aegis analyze <path> [OPTIONS]

# Configuration management
aegis config-show [--config PATH]

# Version information
aegis version

# Help
aegis --help
aegis analyze --help
```

### Configuration

Configuration can be provided via:

1. **Environment variables** (`.env` file)
2. **YAML configuration file** (`config/default_config.yaml`)
3. **Command-line flags** (highest priority)

#### Example Configuration

See `config/default_config.yaml` for a complete example. Key sections:

```yaml
analyzers:
  complexity:
    enabled: true
    thresholds:
      cyclomatic_complexity: 10
      cognitive_complexity: 15

  security:
    enabled: true
    thresholds:
      critical_issues: 0

  test_quality:
    enabled: true
    thresholds:
      code_coverage: 80
      mutation_score: 70

scoring:
  weights:
    complexity: 0.15
    security: 0.25
    style: 0.10
    architecture: 0.15
    edge_cases: 0.10
    test_quality: 0.15
    cognitive_load: 0.10
```

## Output Examples

### CLI Output

```
================================================================================
┌─ Summary ──────────────────────────────────────────────────────────────────┐
│ Analysis Complete                                                          │
│                                                                            │
│ Grade: A (92.5/100)                                                        │
│ Files: 45                                                                  │
│ Lines: 3,521                                                               │
│ Issues: 12                                                                 │
│ Time: 15.32s                                                               │
└────────────────────────────────────────────────────────────────────────────┘

Issues by Severity:
┌──────────┬───────┐
│ Severity │ Count │
├──────────┼───────┤
│ HIGH     │ 2     │
│ MEDIUM   │ 5     │
│ LOW      │ 5     │
└──────────┴───────┘

Analyzer Results:
┌─────────────────┬─────────┬────────┬────────┐
│ Analyzer        │ Status  │ Issues │ Time   │
├─────────────────┼─────────┼────────┼────────┤
│ complexity      │ success │ 3      │ 2.15s  │
│ security        │ success │ 2      │ 5.42s  │
│ style           │ success │ 4      │ 1.23s  │
│ architecture    │ success │ 1      │ 3.87s  │
│ test_quality    │ success │ 2      │ 2.65s  │
└─────────────────┴─────────┴────────┴────────┘
================================================================================
```

### JSON Output

Reports are saved to `synexian-reports/` directory:

```json
{
  "project_path": "/path/to/project",
  "timestamp": "2026-01-03T04:00:00",
  "overall_score": 92.5,
  "grade": "A",
  "summary_stats": {
    "total_files": 45,
    "total_lines": 3521,
    "total_issues": 12,
    "critical_issues": 0,
    "high_issues": 2
  },
  "results": [...]
}
```

## Architecture

### Project Structure

```
synexian-agent/
├── synexian/                         # Main package
│   ├── cli.py                        # CLI application 
│   ├── config.py                     # Configuration management
│   ├── constants.py                  # Constants and enums
│   ├── exceptions.py                 # Custom exceptions
│   ├── models/                       # Data models
│   │   ├── analysis_result.py        # Analysis result models
│   │   ├── issue.py                  # Issue models
│   │   └── metric.py                 # Metric models
│   ├── core/                         # Core business logic
│   │   ├── analyzer_engine.py        # Main orchestration
│   │   ├── cache_manager.py          # AI response caching
│   │   ├── result_aggregator.py      # Result aggregation
│   │   └── scoring_engine.py         # Scoring and grading
│   ├── input/                        # Input handlers
│   │   ├── base.py                   # Base input handler interface
│   │   ├── local_directory.py        # Local directory scanning
│   │   ├── single_file.py            # Single file analysis
│   │   └── github_repo.py            # GitHub repo cloning
│   ├── analyzers/                    # All analyzer modules
│   │   ├── base.py                   # Base analyzer interface
│   │   ├── complexity/               # Complexity analysis (radon)
│   │   ├── security/                 # Security scanning (bandit)
│   │   ├── style/                    # Style checking (flake8)
│   │   ├── architecture/             # Architecture analysis (AI)
│   │   ├── edge_cases/               # Edge case detection (AI)
│   │   ├── test_quality/             # Test quality 
│   │   ├── cognitive_load/           # Cognitive load 
│   │   └── custom_rules/             # Custom rules engine
│   ├── ai/                           # AI integration
│   │   ├── client.py                 # OpenRouter API client
│   │   ├── prompts.py                # AI prompt templates
│   │   ├── rate_limiter.py           # API rate limiting
│   │   └── response_parser.py        # AI response parsing
│   ├── reports/                      # Report generation
│   │   ├── base.py                   # Base reporter interface
│   │   ├── json_reporter.py          # JSON report generator
│   │   └── html_reporter.py          # HTML report generator
│   └── utils/                        # Utilities
│       ├── logger.py                 # Logging configuration
│       ├── file_utils.py             # File operations
│       ├── git_utils.py              # Git integration
│       ├── ast_utils.py              # AST parsing
│       └── validators.py             # Input validation
├── config/                           # Configuration files
│   └── default_config.yaml           # Default configuration
├── scripts/                          # Utility scripts
│   ├── setup.py                      # Automated setup script
│   ├── benchmark.py                  # Performance benchmarking
│   ├── generate_demo.py              # Demo report generator
│   └── check_dependencies.py         # Dependency checker
├── tests/                            # Comprehensive test suite
│   ├── conftest.py                   # Pytest fixtures
│   ├── test_models.py                # Data model tests
│   ├── test_utils.py                 # Utility function tests
│   ├── test_config.py                # Configuration tests
│   ├── test_analyzers.py             # Analyzer tests
│   └── test_integration.py           # Integration tests
└── docs/                             # Comprehensive documentation
    ├── architecture.md               # System architecture
    ├── analyzers.md                  # Analyzer details
    ├── configuration.md              # Configuration guide
    └── development.md                # Development guide
```

### Design Principles

- **Modular Architecture**: Each analyzer is independent and pluggable
- **Async/Await**: Concurrent execution for better performance
- **Hybrid Analysis**: Combines fast static analysis with deep AI insights
- **Caching**: Smart caching of AI responses to reduce costs
- **Graceful Degradation**: Static analysis works even if AI is unavailable

## Development

### Comprehensive Test Suite

The project includes a complete test suite with 80%+ coverage:

**Run all tests:**

```bash
pytest
```

**Run with coverage report:**

```bash
pytest --cov=synexian --cov-report=html --cov-report=term
```

**Run specific test files:**

```bash
# Test data models
pytest tests/test_models.py

# Test analyzers
pytest tests/test_analyzers.py

# Test integration
pytest tests/test_integration.py
```

**Test structure:**
- `tests/conftest.py` - Pytest fixtures for all tests
- `tests/test_models.py` - Tests for MetricValue, Issue, AnalysisResult models
- `tests/test_utils.py` - Tests for file operations, Git utils, AST parsing
- `tests/test_config.py` - Configuration loading and validation tests
- `tests/test_analyzers.py` - Individual analyzer tests (all 8 analyzers)
- `tests/test_integration.py` - End-to-end pipeline tests

### Utility Scripts

Four utility scripts are provided in the `scripts/` directory:

**1. Setup Script - Automated Installation**

```bash
python scripts/setup.py
```

Automatically:
- Installs all dependencies
- Creates virtual environment
- Sets up .env file
- Verifies installation
- Checks dependencies

**2. Benchmark Script - Performance Testing**

```bash
python scripts/benchmark.py
```

Benchmarks:
- Each analyzer's performance
- Overall analysis speed
- Memory usage
- Generates performance report

**3. Demo Generator - Sample Reports**

```bash
python scripts/generate_demo.py
```

Generates:
- Sample analysis reports in all formats (CLI, JSON, HTML)
- Useful for testing report generation
- Demonstrates output capabilities

**4. Dependency Checker**

```bash
python scripts/check_dependencies.py
```

Verifies:
- All required packages are installed
- Package versions are compatible
- Displays missing dependencies
- Color-coded status output

### Code Quality Tools

**Format code:**

```bash
black synexian/
isort synexian/
```

**Type checking:**

```bash
mypy synexian/
```

**Linting:**

```bash
# Using ruff (fast)
ruff check synexian/

# Using flake8
flake8 synexian/
```

**Run all quality checks:**

```bash
# Format
black synexian/ tests/
isort synexian/ tests/

# Lint
ruff check synexian/
flake8 synexian/

# Type check
mypy synexian/

# Test
pytest --cov=synexian
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

### 📖 Architecture Guide (`docs/architecture.md`)

Complete system architecture documentation covering:
- High-level architecture diagram
- Component descriptions (CLI, Config, Analyzers, AI, Reports)
- Data flow and processing pipeline
- Extension points for adding new analyzers
- Design principles and patterns
- Technology stack details

### 🔍 Analyzer Documentation (`docs/analyzers.md`)

Detailed documentation for all 8 analyzers:
- **Complexity Analyzer** - Cyclomatic, Halstead, Cognitive metrics
- **Security Analyzer** - OWASP Top 10, CWE checks, vulnerability scanning
- **Style Analyzer** - PEP8 compliance, naming conventions
- **Architecture Analyzer** - SOLID principles, design pattern detection (AI)
- **Edge Cases Analyzer** - Boundary values, missing edge cases (AI)
- **Test Quality Analyzer** - Coverage, mutation testing (UNIQUE)
- **Cognitive Load Analyzer** - Maintainability index, readability (UNIQUE)
- **Custom Rules Analyzer** - Extensible rule engine

Includes:
- Metrics and thresholds for each analyzer
- Configuration examples
- Sample output
- Performance tips
- Comparison table

### ⚙️ Configuration Guide (`docs/configuration.md`)

Complete configuration reference:
- Configuration sources and precedence
- Environment variables reference
- Full YAML configuration examples
- Analyzer-specific settings
- Per-project configuration
- CI/CD mode configuration
- Strict mode vs fast mode examples
- Troubleshooting guide

### 🛠️ Development Guide (`docs/development.md`)

Development and contribution guide:
- Development environment setup
- Running tests (all variations)
- Code quality tools (black, ruff, mypy)
- Adding new analyzers (step-by-step)
- Adding new report formats
- Debugging tips
- Commit message conventions
- Pull request process
- Release process
- Troubleshooting common issues

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Analyze Code Quality
  run: |
    pip install aegis-analyzer
    aegis analyze . --output json --config .synexian.yaml

- name: Check for Critical Issues
  run: |
    if [ $(jq '.summary_stats.critical_issues' synexian-reports/latest.json) -gt 0 ]; then
      echo "Critical issues found!"
      exit 1
    fi
```

## Technical References

### Research Sources

- [Software Quality Assurance Best Practices 2026](https://monday.com/blog/rnd/software-quality-assurance/)
- [Code Review Best Practices](https://www.qodo.ai/blog/code-review-best-practices/)
- [Code Complexity Metrics](https://daily.dev/blog/7-code-complexity-metrics-developers-must-track)
- [Devstral 2 2512 API](https://openrouter.ai/mistralai/devstral-2512:free)
- [Boundary Value Analysis](https://www.geeksforgeeks.org/software-testing/software-testing-boundary-value-analysis/)


## License

© 2026 Synexian Labs Private Limited. All rights reserved.

## Support

- **Issues**: [GitHub Issues](https://github.com/synexian/synexian-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/synexian/synexian-agent/discussions)
- **Email**: contact@synexian.com

## Acknowledgments

- Powered by [OpenRouter](https://openrouter.ai) and [Mistral AI](https://mistral.ai)
- Built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/)
- Inspired by industry-leading code quality tools

---

==========================================================
© 2026 Synexian Labs Private Limited. All rights reserved.
