# FDIC Branch Service Type Definitions

This document contains the official FDIC Summary of Deposits service type codes and their definitions.

## Service Type Codes

### Full Service Offices

- **11** - Full Service, brick and mortar office
- **12** - Full Service, retail office
- **13** - Full Service, cyber office

### Limited Service Offices

- **21** - Limited Service, administrative office
- **22** - Limited Service, military facility
- **23** - Limited Service, drive-through facility
- **24** - Limited Service, loan production office
- **25** - Limited Service, consumer credit office
- **26** - Limited Service, contractual office
- **27** - Limited Service, messenger office
- **28** - Limited Service, retail office
- **29** - Limited Service, mobile/seasonal office
- **30** - Limited Service, trust office

## Implementation

These definitions are implemented in:
- `justdata/apps/branchseeker/app.py` - Backend API endpoint `/api/branches` maps service_type codes to branch_type descriptions
- The mapping is applied when branch data is returned from the API, converting numeric codes to plain English descriptions
- Frontend applications (BranchMapper) display the `branch_type` field in popups and exports

## Data Source

FDIC Summary of Deposits (SOD) data structure.
Last updated: 2025

