# Corporate Hierarchy Handling Strategy

## Problem

For entities like Fifth Third Bank:
- **Fifth Third Bank, National Association** (child) - LEI: QFROUN1UWUYU0DVIWD51
- **Fifth Third Bancorp** (parent) - LEI: THRNG6BD57P9QWTQLG42, Ticker: FITB
- Multiple child affiliates (mortgage companies, etc.)

When a user searches for "Fifth Third Bank", we need to:
1. Identify it's a child entity
2. Find the parent (Fifth Third Bancorp)
3. Collect data for both parent and all children
4. Aggregate appropriately

## Strategy

### 1. Entity Resolution Phase

**When user searches for "Fifth Third Bank":**

1. **Resolve to LEI** - Get the child entity's LEI
2. **Check GLEIF hierarchy** - Determine if it's a parent, child, or standalone
3. **Identify primary entity**:
   - If child → Use parent as primary for consolidated data
   - If parent → Use as primary
   - If standalone → Use as primary

**Example:**
- Search: "Fifth Third Bank"
- Found: LEI QFROUN1UWUYU0DVIWD51 (child)
- Parent: LEI THRNG6BD57P9QWTQLG42 (Fifth Third Bancorp)
- Primary: Use parent (THRNG6BD57P9QWTQLG42)

### 2. Data Collection Strategy

#### A. Consolidated Data (Use Parent)
- **SEC Filings** - Parent company has 10-K filings (FITB)
- **Seeking Alpha** - Use parent ticker (FITB)
- **Financial Data** - Parent has consolidated financials
- **Analyst Ratings** - Parent company ratings

#### B. Aggregated Data (Parent + All Children)
- **Branch Network** - Aggregate branches from all children
- **Consumer Complaints** - May want to aggregate across entities
- **Litigation** - May want to aggregate across entities

#### C. Individual Data (Keep Separate)
- **FDIC Certificates** - Each bank has its own cert
- **RSSD IDs** - Each entity may have its own
- **Institution Details** - Keep individual entity details

### 3. Implementation Approach

#### Phase 1: Hierarchy Detection
```python
from apps.lenderprofile.processors.corporate_hierarchy import CorporateHierarchy

hierarchy = CorporateHierarchy()
related = hierarchy.get_related_entities(lei)

# Returns:
# {
#   'primary_lei': 'THRNG6BD57P9QWTQLG42',  # Parent
#   'primary_name': 'FIFTH THIRD BANCORP',
#   'hierarchy_type': 'child',
#   'parent': {...},
#   'children': [...],
#   'all_entities': [parent_lei, child1_lei, child2_lei, ...]
# }
```

#### Phase 2: Data Collection
```python
# Use primary LEI for consolidated data
primary_lei = related['primary_lei']

# Get SEC data for parent (has ticker FITB)
sec_data = collector._get_sec_data(primary_name)

# Get Seeking Alpha for parent ticker
seeking_alpha = collector._get_seeking_alpha_data(primary_name)

# Aggregate branches from all entities
all_leis = related['all_entities']
all_branches = []
for entity_lei in all_leis:
    # Get RSSD for each entity
    # Get branches for each RSSD
    # Aggregate
```

#### Phase 3: Report Structure
```python
{
    'primary_entity': {
        'lei': 'THRNG6BD57P9QWTQLG42',
        'name': 'FIFTH THIRD BANCORP',
        'ticker': 'FITB',
        'sec_data': {...},
        'seeking_alpha': {...}
    },
    'related_entities': [
        {
            'lei': 'QFROUN1UWUYU0DVIWD51',
            'name': 'Fifth Third Bank, National Association',
            'type': 'child',
            'fdic_cert': '...',
            'rssd_id': '...'
        },
        ...
    ],
    'aggregated_data': {
        'branches': {
            'total': 1097,
            'by_entity': {...}
        },
        'complaints': {...}
    }
}
```

## Key Decisions

### 1. Which Entity for SEC/Seeking Alpha?
**Answer:** Always use parent (if exists)
- Parent has consolidated financials
- Parent has SEC filings
- Parent has ticker symbol

### 2. Which Entity for Branch Analysis?
**Answer:** Aggregate all children
- Each bank entity has its own branches
- Want total network size
- May want breakdown by entity

### 3. Which Entity for FDIC Data?
**Answer:** Individual entities
- Each bank has its own FDIC cert
- Each has its own financials
- Keep separate but show in hierarchy

### 4. How to Present in Report?
**Answer:** Show hierarchy clearly
- Primary entity section (parent)
- Related entities section (children)
- Aggregated metrics
- Individual entity details

## Implementation Plan

1. ✅ Create `CorporateHierarchy` class (DONE)
2. ⏳ Update `IdentifierResolver` to detect hierarchy
3. ⏳ Update `DataCollector` to use primary entity for consolidated data
4. ⏳ Update branch analysis to aggregate across children
5. ⏳ Update report builder to show hierarchy
6. ⏳ Add hierarchy visualization

## Example: Fifth Third Bank

**User searches:** "Fifth Third Bank"

**Resolution:**
1. Find: LEI QFROUN1UWUYU0DVIWD51 (Fifth Third Bank, National Association)
2. Detect: Child entity
3. Parent: LEI THRNG6BD57P9QWTQLG42 (Fifth Third Bancorp)
4. Children: [QFROUN1UWUYU0DVIWD51, ...]

**Data Collection:**
- SEC: Use parent (FITB ticker)
- Seeking Alpha: Use parent (FITB ticker)
- Branches: Aggregate all children RSSDs
- FDIC: Individual certs for each bank entity

**Report Shows:**
- Primary: Fifth Third Bancorp (FITB)
- Related: Fifth Third Bank, National Association + other affiliates
- Aggregated: Total branches across all entities
- Individual: Each entity's FDIC data

