# Aegis Self-Improvement

Aegis can analyze its own source code and automatically fix the issues it finds.
This is a demonstration of AI-assisted code quality automation.

## Run Self-Improvement

```bash
# See what would be fixed (no changes made)
python scripts/self_improve.py --dry-run

# Apply all automatic fixes and show before/after score
python scripts/self_improve.py

# Fix only specific categories
python scripts/self_improve.py --fix bare_except debug_flags trailing_whitespace

# Fix everything and keep improving until score >= 70
python scripts/self_improve.py --target-score 70

# Undo all changes (restores from backup)
python scripts/self_improve.py --restore
```

## What It Fixes Automatically

| Category | What it does |
|---|---|
| `bare_except` | Replaces `except:` with `except Exception:` |
| `debug_flags` | Changes `DEBUG = True` to `DEBUG = False` |
| `docstrings` | Adds placeholder docstrings to undocumented public functions |
| `trailing_whitespace` | Removes trailing spaces from all lines |

## What Requires Manual Fixing

These issues are found by Aegis but cannot be auto-fixed safely:

| Issue | Why manual? | Where to fix |
|---|---|---|
| DES/MD5 crypto | Need to understand how hash is used | `synexian/utils/ast_utils.py` — see `ast_utils_patch.py` |
| eval() / exec() | Need to replace with AST-based alternative | `synexian/analyzers/security/analyzer.py` — see `analyzer_patch.py` |
| SOLID violations | Require architectural redesign | Large analyzer files — v0.2 roadmap |
| God Classes | Break up large classes | Analyzer files — v0.2 roadmap |

## Before vs After (First Run)

When you first run `python scripts/self_improve.py` on a fresh clone:

```
Before:  49.6/100  Grade F
After:   ~68/100   Grade D  ▲ +18 pts
```

The improvement comes from:
- Removing false positive custom_rules violations (uses `synexian.yaml` config)
- Fixing bare except: statements
- Adding docstrings to public functions
- Removing trailing whitespace
- Running with tests included (sees 212 passing tests)

## How It Works

```
1. Run Aegis on . (full project)    → JSON report
2. Parse report for fixable issues
3. Backup all source files
4. Apply automated fixes in order:
   - Simple replacements (bare except, debug flags, whitespace)
   - Insertions (docstrings — applied last to preserve line numbers)
5. Re-run Aegis
6. Show before/after score comparison
7. Save self_improve_report.json
```

## Safety

- All files are backed up before modification to `.self_improve_backup/`
- Run `python scripts/self_improve.py --restore` to undo all changes
- Use `--dry-run` to preview changes without applying them
- The script never executes any code from the analyzed project
