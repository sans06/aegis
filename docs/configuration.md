# Configuration Guide

## Overview

Aegis uses a flexible, multi-source configuration system that allows customization at multiple levels.

## Configuration Sources

Configuration is loaded in the following order (later sources override earlier ones):

1. **Default Configuration** (built-in)
2. **Default Config File** (`config/default_config.yaml`)
3. **User Config File** (`~/.config/synexian/config.yaml`)
4. **Project Config File** (`./synexian.yaml`)
5. **Environment Variables** (`.env` file)
6. **Command-Line Flags** (highest priority)

## Environment Variables

Create a `.env` file in your project root:

```bash
# API Configuration
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
SYNEXIAN_MODEL=mistralai/devstral-2512:free

# Analysis Settings
SYNEXIAN_CACHE_ENABLED=true
SYNEXIAN_CACHE_DIR=~/.cache/synexian
SYNEXIAN_MAX_WORKERS=4
SYNEXIAN_TIMEOUT_SECONDS=300

# Output Configuration
SYNEXIAN_OUTPUT_DIR=./synexian-reports
SYNEXIAN_VERBOSITY=1

# GitHub Integration (Optional)
GITHUB_TOKEN=your_github_token
```

## YAML Configuration

### Full Configuration Example

```yaml
# config/default_config.yaml

# Analysis Configuration
analysis:
  # File patterns to include
  file_patterns:
    - "**/*.py"
    - "src/**/*.py"

  # Patterns to ignore (gitignore-style)
  ignore_patterns:
    - "**/__pycache__/**"
    - "**/venv/**"
    - "**/.venv/**"
    - "**/node_modules/**"
    - "**/.git/**"
    - "**/dist/**"
    - "**/build/**"

  # Maximum file size to analyze (in KB)
  max_file_size_kb: 1000

# Analyzer Configuration
analyzers:
  # Complexity Analyzer
  complexity:
    enabled: true
    thresholds:
      cyclomatic_complexity: 10
      cognitive_complexity: 15
      halstead_difficulty: 20
    options:
      include_class_methods: true

  # Security Analyzer
  security:
    enabled: true
    thresholds:
      critical_issues: 0
      high_issues: 5
    options:
      check_dependencies: true
      owasp_checks:
        - injection
        - broken_auth
        - sensitive_data
        - security_misconfig

  # Style Analyzer
  style:
    enabled: true
    thresholds:
      pep8_violations_per_kloc: 10
    options:
      max_line_length: 100
      enforce_naming: true

  # Architecture Analyzer (AI)
  architecture:
    enabled: true
    options:
      check_solid: true
      detect_patterns: true

  # Edge Cases Analyzer (AI)
  edge_cases:
    enabled: true
    options:
      check_boundary_values: true
      check_null_handling: true

  # Test Quality Analyzer (UNIQUE)
  test_quality:
    enabled: true
    thresholds:
      code_coverage: 80
      mutation_score: 70

  # Cognitive Load Analyzer (UNIQUE)
  cognitive_load:
    enabled: true
    thresholds:
      maintainability_index: 65
      readability_score: 70

  # Custom Rules Analyzer
  custom_rules:
    enabled: false

# Scoring Configuration
scoring:
  # Weights for each analyzer (must sum to 1.0)
  weights:
    complexity: 0.15
    security: 0.25
    style: 0.10
    architecture: 0.15
    edge_cases: 0.10
    test_quality: 0.15
    cognitive_load: 0.10

  # Grading scale
  grading_scale:
    A+: 95
    A: 90
    B+: 85
    B: 80
    C+: 75
    C: 70
    D: 60
    F: 0

# Output Configuration
output:
  formats:
    - cli
  directory: "./synexian-reports"
  timestamp_format: "%Y%m%d_%H%M%S"

# Performance Configuration
performance:
  parallel_analyzers: true
  max_workers: 4
  timeout_seconds: 300

# Cache Configuration
cache:
  enabled: true
  ttl_hours: 24
  directory: "~/.cache/synexian"

# Logging Configuration
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Command-Line Overrides

Override config with CLI flags:

```bash
# Override output formats
synexian analyze ./project --output json,html

# Use custom config file
synexian analyze ./project --config custom.yaml

# Enable verbose logging
synexian analyze ./project --verbose
```

## Per-Project Configuration

Create `synexian.yaml` in your project root:

```yaml
analyzers:
  complexity:
    thresholds:
      cyclomatic_complexity: 15  # Relax for this project

  security:
    enabled: true  # Enforce security

  test_quality:
    thresholds:
      code_coverage: 90  # Higher standard
```

## Analyzer-Specific Configuration

### Complexity Analyzer

```yaml
complexity:
  enabled: true
  thresholds:
    cyclomatic_complexity: 10  # Max complexity per function
    cognitive_complexity: 15   # Max cognitive complexity
    halstead_difficulty: 20    # Max Halstead difficulty
  options:
    include_class_methods: true
```

### Security Analyzer

```yaml
security:
  enabled: true
  thresholds:
    critical_issues: 0  # No critical issues allowed
    high_issues: 5      # Max 5 high-severity issues
  options:
    check_dependencies: true
    owasp_checks:
      - injection
      - broken_auth
      - sensitive_data
```

### Test Quality Analyzer

```yaml
test_quality:
  enabled: true
  thresholds:
    code_coverage: 80       # Minimum 80% coverage
    mutation_score: 70      # Minimum mutation score
  options:
    run_mutation_testing: true
```

## Configuration Validation

Synexian validates configuration on startup:

```bash
synexian config-show
```

This will show:
- Current configuration values
- Sources of each value
- Validation errors (if any)

## Best Practices

1. **Keep API keys in `.env`** - Never commit `.env` to git
2. **Use project configs for project-specific rules**
3. **Use user config for personal preferences**
4. **Document custom configurations** in your project

## Troubleshooting

### Configuration Not Loading

```bash
# Check config precedence
synexian config-show

# Validate configuration
python -c "from synexian.config import load_config; config = load_config(); print(config.validate())"
```

### API Key Issues

```bash
# Check if API key is set
echo $OPENROUTER_API_KEY

# Verify .env file exists
cat .env | grep OPENROUTER_API_KEY
```

### Analyzer Not Running

Check if analyzer is enabled:

```yaml
analyzers:
  my_analyzer:
    enabled: true  # Must be true
```

## Example Configurations

### Strict Mode (Maximum Quality)

```yaml
analyzers:
  complexity:
    thresholds:
      cyclomatic_complexity: 5  # Very strict

  security:
    thresholds:
      critical_issues: 0
      high_issues: 0  # Zero tolerance

  test_quality:
    thresholds:
      code_coverage: 95  # Near-complete coverage
```

### Fast Mode (Quick Scans)

```yaml
analyzers:
  complexity:
    enabled: true

  security:
    enabled: true

  style:
    enabled: false  # Skip for speed

  architecture:
    enabled: false  # Skip AI (slow)

  edge_cases:
    enabled: false  # Skip AI

performance:
  parallel_analyzers: true
  max_workers: 8  # Use more workers
```

### CI/CD Mode

```yaml
output:
  formats:
    - json  # Machine-readable only

analyzers:
  security:
    thresholds:
      critical_issues: 0  # Fail on critical

  test_quality:
    thresholds:
      code_coverage: 80  # Minimum coverage

performance:
  timeout_seconds: 600  # Longer timeout for CI
```

==========================================================
© 2026 Synexian Labs Private Limited. All rights reserved.
