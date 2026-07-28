# Changelog

All notable changes to Aegis will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Planned for v0.2.0
- GitHub repository analysis (clone and analyze remote repos)
- PyPI package publication
- Named weight presets (security-first, startup, balanced)
- Trend tracking across multiple analysis runs
- Configurable grade thresholds

---

## [0.1.0] — 2026-07-17

### Added
- 8-analyzer parallel execution pipeline (complexity, security, style,
  architecture, edge cases, test quality, cognitive load, custom rules)
- AI-powered analysis via Mistral Devstral 2 (123B) on OpenRouter free tier
- CLI output with Rich terminal formatting
- JSON output for CI/CD integration
- HTML output with Jinja2 templates
- Three-layer configuration system (env → YAML → CLI flags)
- Custom rules engine (YAML-defined rules, AST/regex matching)
- Graceful degradation when API key is absent
- Exit code 1 on critical issues for CI/CD integration
- File-based AI response caching (24-hour TTL)
- Token bucket rate limiting for OpenRouter API calls

### Fixed
- Switched to AsyncOpenAI client — restores true parallel execution
- ScoringEngine wired into AnalyzerEngine — correct 70/30 formula now active
- ResultAggregator wired — issue deduplication now applied after analysis
- RateLimiter wired — proactive API throttling prevents 429 errors
- is_within_threshold() now uses higher_is_better direction for coverage metrics
- merge_with() status logic — explicit priority ordering replaces accidental logic
- asyncio.gather() uses return_exceptions=True — one analyzer crash no longer
  cancels all others
- CacheManager Path key serialization — default=str prevents TypeError
- CacheManager write failures are now non-fatal warnings (never crash analysis)
- AnalysisContext no longer receives None config
- GitHub token passed via HTTP header instead of URL (credential leak closed)
- FileNotFoundError renamed to SourceNotFoundError — no longer shadows built-in
- Bare except: in architecture analyzer replaced with except Exception:
- Dead code removed from cli.py (90 lines)

### Security
- GitHub credential leak fixed: tokens no longer embedded in clone URLs

### Known Limitations
- GitHub repository analysis not yet implemented (coming in v0.2)
- Python only — no multi-language support yet
- No web dashboard for trend tracking
