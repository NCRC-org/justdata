# Corporate Hierarchy Implementation

## Overview

Handles parent/child relationships from GLEIF data to provide comprehensive analysis across corporate families.

## Key Components

### 1. CorporateHierarchy Class
**Location:** `apps/lenderprofile/processors/corporate_hierarchy.py`

**Purpose:** Detects and manages parent/child relationships

**Key Methods:**
- `get_related_entities(lei)` - Gets all related entities (parent + children)
- `get_all_entity_leis(lei)` - Gets list of all LEIs in hierarchy
- `get_primary_entity_for_analysis(lei)` - Returns parent if exists, otherwise the entity

### 2. Integration in DataCollector
**Location:** `apps/lenderprofile/processors/data_collector.py`

**Changes:**
- Detects hierarchy when LEI is available
- Uses primary entity (parent) for consolidated data (SEC, Seeking Alpha)
- Includes hierarchy information in collected data

### 3. Branch Aggregator (Planned)
**Location:** `apps/lenderprofile/processors/branch_aggregator.py`

**Purpose:** Aggregates branch data across all entities in hierarchy

## How It Works

### Example: Fifth Third Bank

**User searches:** "Fifth Third Bank"

1. **Identifier Resolution:**
   - Finds: LEI `QFROUN1UWUYU0DVIWD51` (Fifth Third Bank, National Association)

2. **Hierarchy Detection:**
   ```python
   hierarchy = CorporateHierarchy()
   related = hierarchy.get_related_entities('QFROUN1UWUYU0DVIWD51')
   # Returns:
   # {
   #   'primary_lei': 'THRNG6BD57P9QWTQLG42',  # Fifth Third Bancorp
   #   'primary_name': 'FIFTH THIRD BANCORP',
   #   'hierarchy_type': 'child',
   #   'parent': {'lei': 'THRNG6BD57P9QWTQLG42', 'name': 'FIFTH THIRD BANCORP'},
   #   'children': [...],
   #   'all_entities': ['THRNG6BD57P9QWTQLG42', 'QFROUN1UWUYU0DVIWD51', ...]
   # }
   ```

3. **Data Collection:**
   - **SEC Data:** Uses primary name "FIFTH THIRD BANCORP" → Gets ticker FITB
   - **Seeking Alpha:** Uses primary name → Gets FITB ticker → Gets financials/ratings
   - **Branches:** Would aggregate across all children (future enhancement)
   - **FDIC:** Individual data for each entity

4. **Result Structure:**
   ```python
   {
       'institution': {
           'name': 'FIFTH THIRD BANCORP',  # Primary entity
           'original_name': 'Fifth Third Bank',  # What user searched for
           'primary_lei': 'THRNG6BD57P9QWTQLG42',
           'original_lei': 'QFROUN1UWUYU0DVIWD51'
       },
       'hierarchy': {
           'primary_lei': 'THRNG6BD57P9QWTQLG42',
           'primary_name': 'FIFTH THIRD BANCORP',
           'hierarchy_type': 'child',
           'parent': {...},
           'children': [...],
           'all_entities': [...],
           'entity_map': {...}
       },
       'sec': {
           'ticker': 'FITB',  # From parent
           'cik': '...',
           '10k_content': [...]
       },
       'seeking_alpha': {
           'ticker': 'FITB',  # From parent
           'financials': [...],
           'ratings': [...]
       }
   }
   ```

## Data Collection Strategy

### Use Parent For:
- ✅ SEC filings (consolidated financials)
- ✅ Seeking Alpha (parent ticker)
- ✅ Analyst ratings (parent company)
- ✅ Financial data (consolidated)

### Aggregate Across All Entities:
- ⏳ Branch network (future)
- ⏳ Consumer complaints (future)
- ⏳ Litigation (future)

### Keep Individual:
- ✅ FDIC certificates
- ✅ RSSD IDs
- ✅ Institution details

## Current Status

### ✅ Implemented
- Corporate hierarchy detection
- Primary entity identification
- Integration in data collector
- Use of primary entity for SEC/Seeking Alpha

### ⏳ Future Enhancements
- Branch aggregation across hierarchy
- RSSD lookup from LEI for branch aggregation
- Hierarchy visualization in reports
- Aggregated metrics across entities

## Usage

The hierarchy detection happens automatically in `DataCollector.collect_all_data()`:

```python
collector = DataCollector()
identifiers = {'lei': 'QFROUN1UWUYU0DVIWD51', ...}
data = collector.collect_all_data(identifiers, 'Fifth Third Bank')

# Data will include:
# - hierarchy information
# - Primary entity used for SEC/Seeking Alpha
# - All related entities
```

## Benefits

1. **Accurate Financial Data:** Uses parent company for consolidated financials
2. **Correct Ticker Resolution:** Gets FITB instead of trying to find ticker for child entity
3. **Comprehensive Analysis:** Can analyze entire corporate family
4. **Clear Presentation:** Shows hierarchy in reports

