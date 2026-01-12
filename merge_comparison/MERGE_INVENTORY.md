# Merge Inventory - JD -> JustData

## Apps Comparison

### Existing Apps (need merge)
| App | JD Path | JustData Path |
|-----|---------|---------------|
| BranchSeeker | apps/branchsight/ | justdata/apps/branchseeker/ |
| LendSight | apps/lendsight/ | justdata/apps/lendsight/ |
| BizSight | apps/bizsight/ | justdata/apps/bizsight/ |
| MergerMeter | apps/mergermeter/ | justdata/apps/mergermeter/ |
| BranchMapper | apps/branchmapper/ | justdata/apps/branchmapper/ |

### New Apps (need to add)
| App | JD Path | Status |
|-----|---------|--------|
| DataExplorer | apps/dataexplorer/ | NEW |
| LenderProfile | apps/lenderprofile/ | NEW |
| LoanTrends | apps/loantrends/ | NEW |
| MemberView | apps/memberview/ | NEW |

## Shared Utils - Files to Add
- census_adult_demographics.py
- census_demographic_analysis.py
- census_historical_utils.py
- connecticut_county_mapper.py
- demographic_narrative_generator.py
- env_utils.py
- unified_env.py
- version_manager.py
- CENSUS_ADULT_DEMOGRAPHICS_README.md
- CENSUS_API_REFERENCE.md

## Shared Utils - Files to Merge
- bigquery_client.py (differs)
- progress_tracker.py (differs)

## Shared Services - Files to Add
- export_service.py (NEW)

## Shared Services - Files to Merge
- __init__.py (differs)
- ai_service.py (differs)
- celery_app.py (differs)
