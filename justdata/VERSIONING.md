# JustData Version Management

This document explains how to manage versions for JustData applications.

## Version Registry Location

All application versions are stored in a single file:

```
justdata/shared/utils/versions.py
```

## Version Scheme

We use **Semantic Versioning** (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes or major rewrites
- **MINOR**: New features or significant enhancements
- **PATCH**: Bug fixes and small improvements

### Current Version Range

- **0.x.x**: Pre-release development (current)
- **1.0.0**: First public production release (reserved)

## How to Update Versions

### 1. Find the Version Registry

Open `justdata/shared/utils/versions.py`

### 2. Update the Appropriate Version

```python
VERSIONS = {
    'platform': '0.9.0',      # Update this for platform-wide changes
    'lendsight': '0.9.0',     # Update for LendSight changes
    'branchsight': '0.9.0',   # Update for BranchSight changes
    # ... etc
}
```

### 3. When to Bump Each Number

| Change Type | Example | Action |
|-------------|---------|--------|
| Bug fix | Fix chart not loading | 0.9.0 → 0.9.1 |
| New feature | Add PDF export | 0.9.1 → 0.10.0 |
| Major rewrite | New architecture | 0.10.0 → 1.0.0 |

## Where Versions Appear

1. **Landing Page Footer**: Shows `JustData Platform v0.9.0`
2. **Health Endpoint**: `GET /health` returns version in JSON
3. **Excel Exports**: Notes sheet includes "Application Version: X.X.X"

## Using Versions in Code

### Import the Version Helper

```python
from justdata.shared.utils.versions import get_version

# Get a specific app version
version = get_version('lendsight')  # Returns '0.9.0'

# Get platform version
platform_version = get_version('platform')
```

### Get All Versions

```python
from justdata.shared.utils.versions import get_all_versions

all_versions = get_all_versions()  # Returns dict of all versions
```

## Testing After Version Changes

After updating versions, verify:

1. **Run the platform**: `python run_justdata.py`
2. **Check landing page footer**: Should show updated version
3. **Test health endpoint**: `curl http://localhost:8000/health`
4. **Generate an Excel report**: Notes sheet should show version

## Version History Convention

When making changes, consider adding a brief changelog comment:

```python
# Changelog:
# 0.9.1 - Fixed chart rendering issue
# 0.9.0 - Initial pre-release version
```

## Questions?

Contact the JustData development team or check CLAUDE.md for project guidance.
