# ElectWatch Employer Classification Methodology

**Last Updated:** January 31, 2026  
**Author:** Jay Richardson  
**Status:** Production

---

## Overview

ElectWatch tracks financial sector influence on members of Congress through three data dimensions: stock trades, PAC contributions, and individual contributions. This document describes the methodology for classifying individual contribution employers as financial sector firms.

---

## The Problem (Pre-January 2026)

The original `employer_classifier.py` used **broad keyword pattern matching** to identify financial sector employers from FEC individual contribution records. Any employer name containing words like "BANK", "INSURANCE", "INVESTMENT", or "CAPITAL" was flagged as financial sector.

With 58 million individual contribution records containing free-text employer names, this approach generated **massive false positives**:

| Employer | Incorrectly Tagged As | Actually Is |
|----------|----------------------|-------------|
| INDIANA SPINE GROUP | banking | Medical practice |
| UNIVERSITY OF MICHIGAN | insurance | University |
| STATE OF CALIFORNIA | investment | Government |
| NORTH AMERICAN MIDWAY ENTERTAINMENT | banking | Carnival company |
| WELLS ENTERPRISES | banking | Ice cream company |
| US DEPARTMENT OF STATE | investment | Federal agency |

These false positives inflated financial sector influence metrics and undermined data credibility.

---

## The Solution (January 2026)

### Exact Match Against PAC-Connected Organizations Only

The new methodology classifies employers **only if they can be verified through PAC data**:

1. Financial sector PACs have a `connected_organization` field in FEC records
2. Example: "GOLDMAN SACHS GROUP INC PAC" → connected_org = "GOLDMAN SACHS GROUP INC"
3. Only employers that exactly match a known connected organization are classified
4. **Everything else is unclassified** — not assumed to be financial sector

### Why This Approach

- **False positives are worse than false negatives** for advocacy research
- Every claim of financial sector influence must be defensible
- Missing some small financial firms is acceptable; overcounting is not
- The ~441 verified firms capture all major financial institutions

---

## Technical Implementation

### File: `justdata/apps/electwatch/services/firm_matcher.py`

```python
def classify_employer(employer):
    normalized = normalize(employer)
    
    # Only match against verified PAC-connected organizations
    if normalized in verified_pac_connected_orgs:
        return verified_pac_connected_orgs[normalized]  # Returns sector
    
    # Everything else = not classified as financial
    return None
```

### What Was Removed

- Keyword pattern matching (e.g., `['BANK'] → banking`)
- Fuzzy/approximate string matching
- Generic sector inference from partial matches

### What Was Kept

- Exact matching against 441 verified financial firms
- Sector inheritance from PAC classification

---

## Coverage Statistics

| Metric | Value |
|--------|-------|
| Total individual contributions | 58,209,133 |
| Contributions with employer field | 55,923,339 (96.1%) |
| Matched to financial firms | 418,388 (0.7%) |
| Total financial sector amount | $172.6 million |
| Verified financial firms | 441 |

### Firms by Sector

| Sector | Firm Count |
|--------|------------|
| Insurance | 133 |
| Banking | 107 |
| Financial Services | 45 |
| Investment | 40 |
| Real Estate | 29 |
| Credit Unions | 26 |
| Lending | 23 |
| Payments | 18 |
| Securities | 10 |
| Private Equity | 7 |
| Investment Banking | 3 |

---

## What Gets Classified

**Included (verified PAC-connected organizations):**
- Major banks: JPMorgan Chase, Bank of America, Wells Fargo, Citigroup
- Investment banks: Goldman Sachs, Morgan Stanley
- Asset managers: BlackRock, Vanguard, Fidelity, State Street
- Insurance: State Farm, Allstate, MetLife, Prudential
- Credit cards: Visa, Mastercard, American Express
- Private equity: Blackstone, KKR, Carlyle, Bain Capital
- Regional banks with PACs
- Major credit unions with PACs

**Excluded (no longer falsely tagged):**
- Universities and colleges
- Government agencies (federal, state, local)
- Medical practices and hospitals
- Non-financial companies with "bank" in name (food banks, etc.)
- Retired, self-employed, homemaker, etc.
- Any employer without a verified PAC connection

---

## Trade-Offs

### What We Gain
- Zero false positives
- Defensible, auditable methodology
- Clear provenance (every match traces to a classified PAC)
- Simpler, more maintainable code

### What We Lose
- Small regional banks without PACs
- Boutique financial advisors
- Fintech startups
- Solo practitioners

**Assessment:** Acceptable trade-off. Lost coverage represents smaller dollar amounts and harder-to-verify entities. The signal-to-noise ratio improvement is significant.

---

## Alternative Approaches Considered

### Trade Association PAC Member Extraction
Extract employers from contributors TO financial trade association PACs (ABA, CUNA, etc.) and classify those employers.

**Rejected because:** A law professor studying banking regulation might donate to ABA PAC personally — their university would incorrectly be tagged as "banking." Same false positive problem.

### Enhanced Keyword Matching with Exclusions
Keep keyword matching but add extensive exclusion patterns for universities, government, medical, etc.

**Rejected because:** Whack-a-mole problem. With 58M records and free-text employer names, new false positives will always emerge. Not sustainable.

### Fuzzy Matching Against Known Firms
Use approximate string matching (Levenshtein distance, etc.) to catch variations.

**Rejected because:** "WELLS ENTERPRISES" fuzzy-matches to "WELLS FARGO" despite being completely different companies. Too risky.

---

## Validation

### Confirmed Corrections (January 31, 2026)

| Member | Old (False) | New (Correct) |
|--------|-------------|---------------|
| Slotkin | $305K (universities as insurance) | $138K (Bain, Goldman, JPMorgan) |
| Spartz | $22.8K (Indiana Spine as banking) | $1,000 (State Farm) |
| Shreve | $3.3K (Indiana Spine as banking) | $0 |
| Hyde-Smith | $7.4K (carnival as banking) | $0 |
| Tuberville | $9.9K (State Dept as investment) | $1,500 (Cigna) |

### Confirmed True Positives Retained

- Goldman Sachs → investment_banking ✓
- JPMorgan Chase → banking ✓
- Wells Fargo → banking ✓
- Bank of America → banking ✓
- BlackRock → investment ✓
- State Farm → insurance ✓

---

## Code History

| Date | Commit | Change |
|------|--------|--------|
| 2026-01-31 | `043f87d` | Fix employer classification false positives |
| 2026-01-31 | `25c18cb` | Simplify to exact match only |

**Branch:** `Jason_TestApps` (merge to `main` for production)

---

## Related Files

- `justdata/apps/electwatch/services/firm_matcher.py` — Employer matching logic
- `justdata/apps/electwatch/services/pac_classifier.py` — PAC classification (source of truth for sectors)
- `justdata/apps/electwatch/data/cache/financial_firms_list.json` — Cached list of 441 verified firms
- `justdata/apps/electwatch/data/cache/employer_firm_matches.json` — Cached match results

---

## Contact

**Jay Richardson**
Senior Director of Research
National Community Reinvestment Coalition (NCRC)
