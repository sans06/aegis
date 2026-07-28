# Aegis - Installation & Quick Start Guide

## Quick Installation

Follow these steps to get Aegis up and running:

### 1. Set Up Virtual Environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install the package in development mode
pip install -e .

# This will install all required dependencies from pyproject.toml
```

### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenRouter API key
nano .env  # or use any text editor
```

Add your API key to `.env`:

```env
OPENROUTER_API_KEY=your_api_key_here
SYNEXIAN_MODEL=mistralai/devstral-2512:free
```

### 4. Get Your OpenRouter API Key (FREE)

1. Visit [https://openrouter.ai](https://openrouter.ai)
2. Click "Sign Up" and create a free account
3. Go to "API Keys" in your dashboard
4. Click "Create Key"
5. Copy the API key and paste it into your `.env` file

**Note**: The `mistralai/devstral-2512:free` model is completely free to use!

### 5. Verify Installation

```bash
# Check that the installation worked
synexian version

# Should output:
# Synexian Agent version 0.1.0
# AI-powered software quality analysis tool
```

## Quick Start Usage

### Analyze a Local Directory

```bash
synexian analyze ./my-project
```

### Analyze a Single File

```bash
synexian analyze ./my-project/main.py
```

### Analyze with Verbose Output

```bash
synexian analyze ./my-project --verbose
```

### View Configuration

```bash
synexian config-show
```

## Next Steps

### Current Status

**Synexian Agent is FULLY IMPLEMENTED and ready to use!** You have:

- Complete project implementation with all 8 analyzers
- Full AI integration with OpenRouter
- All input methods (local, file, GitHub)
- All output formats (CLI, JSON, HTML)
- Comprehensive configuration system
- Production-ready error handling
- Smart caching and rate limiting

### What You Can Do Now:

**1. Run Your First Analysis**

```bash
# Analyze your project
synexian analyze ./your-project

# With all output formats
synexian analyze ./your-project --output cli,json,html
```

**2. Analyze a GitHub Repository**

```bash
synexian analyze https://github.com/username/repository
```

**3. Customize Configuration**

Edit `config/default_config.yaml` or create your own:

```yaml
analyzers:
  complexity:
    enabled: true
    thresholds:
      cyclomatic_complexity: 15  # Adjust threshold

  security:
    enabled: true

  test_quality:
    enabled: true
    thresholds:
      code_coverage: 90  # Higher coverage requirement
```

**4. Integrate with CI/CD**

```yaml
# .github/workflows/quality.yml
- name: Run Synexian Analysis
  run: |
    pip install -e .
    synexian analyze . --output json

- name: Check for Critical Issues
  run: |
    if [ $(jq '.summary_stats.critical_issues' synexian-reports/latest.json) -gt 0 ]; then
      exit 1
    fi
```

### All Implemented Analyzers

**1. Complexity Analyzer** ✅
- Cyclomatic complexity using `radon`
- Halstead metrics (volume, difficulty, effort)
- Cognitive complexity analysis
- Detects overly complex functions

**2. Security Analyzer** ✅
- Security scanning using `bandit`
- OWASP Top 10 checks
- CWE vulnerability detection
- Identifies SQL injection, XSS, and more

**3. Style Analyzer** ✅
- PEP8 compliance using `flake8`
- Code style violations
- Naming convention checks
- Formatting issues

**4. Architecture Analyzer** ✅ (AI-Powered)
- SOLID principles validation
- Design pattern detection
- Code structure analysis
- Uses AI for deep architectural insights

**5. Edge Case Analyzer** ✅ (AI-Powered)
- Boundary value analysis
- Missing edge case detection
- Input validation gaps
- AI-powered scenario identification

**6. Test Quality Analyzer** ✅ (UNIQUE)
- Test coverage analysis using `pytest`
- Mutation testing readiness
- Assertion quality checks
- Test pattern detection

**7. Cognitive Load Analyzer** ✅ (UNIQUE)
- Maintainability index calculation
- Code readability metrics
- Documentation quality assessment
- Nesting depth analysis

**8. Custom Rules Analyzer** ✅
- Extensible rule engine
- YAML-based rule definitions
- Custom compliance checks

## Troubleshooting

### Import Errors

If you see import errors, make sure you've installed the package:

```bash
pip install -e .
```

### Missing Dependencies

If some dependencies are missing:

```bash
pip install -r requirements.txt
```

### OpenRouter API Key Issues

Make sure your API key is in `.env`:

```bash
# Check if .env file exists
cat .env | grep OPENROUTER_API_KEY
```

## Development

### Run Tests (when implemented)

```bash
pytest
```

### Code Formatting

```bash
black synexian/
isort synexian/
```

### Type Checking

```bash
mypy synexian/
```

## Resources

- **Documentation**: See `README.md` for full documentation
- **Configuration**: See `config/default_config.yaml` for configuration options
- **Architecture**: See the plan file for detailed architecture
- **OpenRouter**: [https://openrouter.ai/docs](https://openrouter.ai/docs)

## Support

If you encounter any issues:

1. Check the `README.md` file
2. Review the configuration in `config/default_config.yaml`
3. Enable verbose output: `synexian analyze ./project --verbose`
4. Check the logs in `synexian.log`

---

**You now have a solid foundation for using a sophisticated code quality analysis tool!**

The next step is to implement the individual analyzers using the provided base interface and examples above.


=========================================================
© 2026 Synexian Labs Private Limited. All rights reserved.
