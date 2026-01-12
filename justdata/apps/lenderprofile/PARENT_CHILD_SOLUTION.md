# Parent/Child Corporate Hierarchy Solution

## Problem Statement

For entities like Fifth Third Bank:
- User searches: "Fifth Third Bank"
- Found: Fifth Third Bank, National Association (child entity, LEI: QFROUN1UWUYU0DVIWD51)
- Parent: Fifth Third Bancorp (LEI: THRNG6BD57P9QWTQLG42, Ticker: FITB)
- Children: Multiple affiliates (mortgage companies, etc.)

**Challenge:** Need to analyze the entire corporate family, not just the child entity.

## Solution Implemented

### 1. Corporate Hierarchy Detection ✅

**File:** `apps/lenderprofile/processors/corporate_hierarchy.py`

**Class:** `CorporateHierarchy`

**Key Method:** `get_related_entities(lei)`

**What it does:**
- Detects if entity is parent, child, or standalone
- If child → finds parent and all siblings
- If parent → finds all children
- Returns complete hierarchy information

**Example for Fifth Third:**
```python
hierarchy = CorporateHierarchy()
related = hierarchy.get_related_entities('QFROUN1UWUYU0DVIWD51')

# Returns:
{
    'primary_lei': 'THRNG6BD57P9QWTQLG42',  # Parent (Fifth Third Bancorp)
    'primary_name': 'FIFTH THIRD BANCORP',
    'hierarchy_type': 'child',
    'parent': {
        'lei': 'THRNG6BD57P9QWTQLG42',
        'name': 'FIFTH THIRD BANCORP'
    },
    'children': [
        {'lei': 'QFROUN1UWUYU0DVIWD51', 'name': 'Fifth Third Bank, National Association'},
        # ... other children
    ],
    'all_entities': ['THRNG6BD57P9QWTQLG42', 'QFROUN1UWUYU0DVIWD51', ...]
}
```

### 2. Data Collection Strategy ✅

**File:** `apps/lenderprofile/processors/data_collector.py`

**Changes:**
- Detects hierarchy when LEI is available
- Uses **primary entity (parent)** for consolidated data:
  - SEC filings → Uses parent name → Gets FITB ticker
  - Seeking Alpha → Uses parent name → Gets FITB ticker
  - Financial data → Uses parent (consolidated)
- Includes hierarchy info in collected data

**Flow:**
1. User searches: "Fifth Third Bank"
2. Resolve to LEI: QFROUN1UWUYU0DVIWD51 (child)
3. Detect hierarchy: Child → Parent is THRNG6BD57P9QWTQLG42
4. Use primary: "FIFTH THIRD BANCORP" for SEC/Seeking Alpha
5. Collect data:
   - SEC: Uses "FIFTH THIRD BANCORP" → Gets FITB ticker → Gets 10-K filings
   - Seeking Alpha: Uses "FIFTH THIRD BANCORP" → Gets FITB ticker → Gets financials/ratings
   - Branches: Individual entities (future: aggregate)

### 3. Data Structure

**Collected data includes:**
```python
{
    'institution': {
        'name': 'FIFTH THIRD BANCORP',  # Primary entity
        'original_name': 'Fifth Third Bank',  # What user searched
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
        'entity_map': {...}  # LEI -> name mapping
    },
    'sec': {
        'ticker': 'FITB',  # From parent
        'cik': '...',
        '10k_content': [...]
    },
    'seeking_alpha': {
        'ticker': 'FITB',  # From parent
        'financials': [...],
        'ratings': [...],
        'leading_story': [...]
    }
}
```

## What This Solves

### ✅ Ticker Resolution
- **Before:** Tried to find ticker for "Fifth Third Bank" (child) → Failed
- **After:** Uses "Fifth Third Bancorp" (parent) → Gets FITB ticker → Works!

### ✅ SEC Filings
- **Before:** Child entity may not have SEC filings
- **After:** Uses parent → Gets consolidated 10-K filings

### ✅ Financial Data
- **Before:** Child entity financials (incomplete)
- **After:** Parent consolidated financials (complete)

### ✅ Analyst Ratings
- **Before:** No ratings for child entity
- **After:** Parent company ratings (FITB)

## Future Enhancements

### Branch Aggregation (Planned)
**File:** `apps/lenderprofile/processors/branch_aggregator.py`

**Purpose:** Aggregate branches across all children

**Challenge:** Need RSSD lookup from LEI
- Each child entity has its own RSSD
- Need to map LEI → RSSD for each entity
- Then aggregate branches from all RSSDs

**Example:**
- Fifth Third Bancorp (parent) → No branches (holding company)
- Fifth Third Bank, NA (child) → RSSD 12345 → 1,097 branches
- Fifth Third Mortgage (child) → RSSD 67890 → 50 branches
- **Total:** 1,147 branches across all entities

## Usage

The hierarchy detection happens **automatically** in data collection:

```python
collector = DataCollector()
identifiers = {'lei': 'QFROUN1UWUYU0DVIWD51', ...}
data = collector.collect_all_data(identifiers, 'Fifth Third Bank')

# Hierarchy is automatically detected and used
# SEC/Seeking Alpha use parent entity
# Hierarchy info included in data['hierarchy']
```

## Benefits

1. **Accurate Data:** Uses parent for consolidated financials
2. **Correct Tickers:** Gets FITB instead of failing
3. **Complete Analysis:** Can analyze entire corporate family
4. **Transparent:** Shows hierarchy in collected data
5. **Extensible:** Ready for branch aggregation

## Status

✅ **Implemented:**
- Hierarchy detection
- Primary entity identification
- Use of parent for SEC/Seeking Alpha
- Hierarchy info in collected data

⏳ **Future:**
- Branch aggregation across hierarchy
- RSSD lookup from LEI
- Hierarchy visualization in reports

