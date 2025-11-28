# Plan to Flatten Directory Structure

## Current Structure (Confusing)
```
justdata/                          # Project root
├── justdata/                      # Python package (nested - confusing!)
│   ├── apps/
│   │   ├── branchseeker/
│   │   ├── lendsight/
│   │   ├── mergermeter/
│   │   └── bizsight/
│   ├── shared/                    # Shared code
│   │   ├── utils/
│   │   ├── web/
│   │   ├── analysis/
│   │   └── reporting/
│   ├── core/
│   ├── api/
│   └── cli/
├── run_mergermeter.py
├── run_branchseeker.py
├── requirements.txt
└── README.md
```

## Proposed Flattened Structure (Better)
```
justdata/                          # Project root (also the Python package)
├── apps/                          # All applications
│   ├── branchseeker/
│   ├── lendsight/
│   ├── mergermeter/
│   └── bizsight/
├── shared/                        # Shared code (easier to find!)
│   ├── utils/
│   ├── web/
│   ├── analysis/
│   └── reporting/
├── core/                          # Core functionality
├── api/                           # API endpoints
├── cli/                           # CLI tools
├── run_mergermeter.py
├── run_branchseeker.py
├── requirements.txt
└── README.md
```

## Benefits of Flattening

1. **Easier Navigation**: No nested `justdata/justdata/` confusion
2. **Shorter Imports**: `from apps.mergermeter.app` instead of `from apps.mergermeter.app`
3. **Clearer Structure**: Everything at the same level, easier to see relationships
4. **Faster File Finding**: Less directory depth to navigate

## Required Changes

### 1. Move Files
- Move everything from `justdata/justdata/*` to `justdata/*`
- Keep `__init__.py` files to maintain package structure

### 2. Update Imports
Change all imports from:
```python
from apps.mergermeter.app import app
from shared.utils.bigquery_client import get_bigquery_client
```

To:
```python
from apps.mergermeter.app import app
from shared.utils.bigquery_client import get_bigquery_client
```

### 3. Update Path References
Update any hardcoded paths that reference the nested structure:
- `BASE_DIR.parent.parent` → `BASE_DIR.parent`
- `JUSTDATA_BASE = BASE_DIR.parent.parent` → `JUSTDATA_BASE = BASE_DIR.parent`

### 4. Update pyproject.toml
Change package discovery:
```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["apps*", "shared*", "core*", "api*", "cli*"]
```

## Why Current Structure Exists

The nested `justdata/justdata/` structure is a **standard Python package layout** that:
- Allows the package to be installed via `pip install -e .`
- Keeps the package name consistent (`justdata`)
- Separates project files (run scripts, docs) from package code

**However**, for a single-project codebase (not a library), this nesting is unnecessary and confusing.

## Recommendation

**YES, we should flatten it!** The benefits outweigh the costs:
- You're not distributing this as a pip package
- Easier navigation and file finding
- Simpler imports
- Less confusion for developers

The only downside is we need to update imports, but that's a one-time change.



