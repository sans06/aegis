# Changelog

## [0.1.0] - 2026-07-18

### Added
- 8-analyzer parallel execution pipeline
- AI-powered analysis via Mistral Devstral 2 (123B) on OpenRouter free tier
- CLI, JSON, and HTML output formats
- Three-layer configuration system (env -> YAML -> CLI flags)
- Custom rules engine (YAML-defined rules, AST/regex matching)
- Graceful degradation when API key is absent
- File-based AI response caching (24-hour TTL)
- Token bucket rate limiting for OpenRouter API
- Self-improvement script (scripts/self_improve.py)
- Encoding fix script (scripts/fix_encoding.py)

### Fixed
- Switched to AsyncOpenAI client (restores true parallel execution)
- ScoringEngine wired into AnalyzerEngine (correct 70/30 formula)
- ResultAggregator wired (issue deduplication now applied)
- RateLimiter wired (proactive API throttling)
- is_within_threshold() now direction-aware for coverage metrics
- merge_with() status logic uses explicit priority ordering
- asyncio.gather() uses return_exceptions=True
- CacheManager Path key serialization fixed
- GitHub token passed via HTTP header (not URL)
- FileNotFoundError renamed to SourceNotFoundError
- Bare except: replaced with except Exception: in architecture analyzer
- All emoji removed from source files (Windows encoding compatibility)
- html_reporter and json_reporter use explicit utf-8 encoding
- Custom rules weight increased from 0.0 to 0.05

### Security
- GitHub credential leak fixed: tokens no longer embedded in clone URLs
