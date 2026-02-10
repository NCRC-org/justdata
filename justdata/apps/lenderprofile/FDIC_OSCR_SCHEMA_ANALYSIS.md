# FDIC OSCR API — Schema vs. Live Endpoint Analysis

The official FDIC OSCR (Office of Supervisory Data) schema defines **235 fields** for the `/history` endpoint. However, the live API only returns a subset. This document tracks which fields are available on the live endpoint vs. dormant in the schema, plus the full data dictionary from `events_definitions.csv`.

---

## Critical Field Discrepancies

### Fields IN Schema but NOT Populated on Live `/history` Endpoint

| Schema Field | Description | Status | Workaround |
|---|---|---|---|
| `MSA` | Metropolitan Statistical Area name | **NOT POPULATED** | Use county-to-CBSA crosswalk for metro grouping |
| `MSA_NO` | MSA number | **NOT POPULATED** | Use county-to-CBSA crosswalk for metro grouping |
| `STALP` | Institution state abbreviation | **NOT POPULATED** | Use `PSTALP` for institution state |
| `LOCN_PHY_ST_NUM` | Physical state FIPS number | **NOT POPULATED** | Use `STNUM` for institution state FIPS |

### Fields NOT in Schema but Returned by Live API

| Live Field | Description | Notes |
|---|---|---|
| `OFF_PSTNUM` | Branch-level state FIPS code | Essential for GEOID5 construction. Not in official schema but reliably returned by live API. |

### Fields with Naming Quirks

| Schema Field | Notes |
|---|---|
| `FI_UNINIM` | Official schema has typo — should be `FI_UNINUM`. Use the schema spelling when querying. |

## Confirmed Live Field Mappings

### State Fields
| Need | Use This Field | NOT This |
|---|---|---|
| Institution state (abbrev) | `PSTALP` | ~~`STALP`~~ (not populated) |
| Branch state (abbrev) | `OFF_PSTALP` | — |
| Branch state (full name) | `OFF_PSTATE` | — |
| Institution state FIPS | `STNUM` | ~~`LOCN_PHY_ST_NUM`~~ (not populated) |
| Branch state FIPS | `OFF_PSTNUM` | — (not in schema, but live API returns it) |

### Metro/CBSA Grouping
- **MSA and MSA_NO are NOT populated** on the `/history` endpoint
- County-to-CBSA crosswalk is still required for metro-level grouping
- Use `OFF_CNTYNUM` (branch county FIPS) + crosswalk table to derive CBSA

## Key Takeaway

The official FDIC schema file (235 fields) is useful as a **complete data dictionary** but does NOT reflect actual field availability on the live `/history` endpoint. The live-tested field list (documented from API calls) remains the **authoritative source** for what's actually returned.

When in doubt, test a field on the live endpoint before building logic around it — the API silently drops fields that aren't populated rather than returning nulls.

---

## Full Schema Data Dictionary (from events_definitions.csv)

Source: FDIC official `events_definitions.csv` — 235 fields total.

### Current Institution Fields

| Field | Label | Definition |
|---|---|---|
| `CERT` | FDIC Certificate # | Unique number assigned by the FDIC used to identify institutions and for the issuance of insurance certificates. |
| `INSTNAME` | Institution Name | The legal name of the institution. |
| `NAME` | Institution name | The legal title or name of the institution. |
| `ACTIVE` | Institution Status | 1=currently open and insured by FDIC; 0=closed or not insured. |
| `INST_FIN_ACTV_FLG` | Institution Status | Flag indicating whether a financial institution is active. |
| `CLASS` | Bank Charter Class | Major grouping code: N=National/FRS, SM=State/FRS, NM=State non-FRS, SI=Stock/Mutual Savings, SB=Savings Bank, SL=S&L, OI=IBA, CU=Credit Union, NC=Non-insured, NS=Non-insured S&A. |
| `CLCODE` | Numeric Code | Two-digit code identifying major/minor categories (03=National/FRS, 13=State/FRS, 21=State non-FRS, 33-38=Thrifts, etc.). |
| `CHARTER` | OCC Charter Number | Number assigned by OCC for nationally chartered banks. |
| `CHARTAGENT` | Chartering Agency | OCC, OTS, State, or Sover (foreign). |
| `REGAGENT` | Primary Regulator | Federal regulatory agency: OCC, FDIC, FRB, NCUA, or OTS. |
| `REGAGENT2` | Secondary Regulator | Secondary supervision: CFPB or OTS. |
| `DOCKET` | OTS Docket Number | OTS/FHFB identification number. '00000' for non-members. |
| `TRUST` | Trust Powers | Code: 00=Not Known, 10=Full Granted, 11=Full Exercised, 12=Full Not Exercised, 20=Limited, 21=Limited Exercised, 30=Not Granted, 31=Not Granted But Exercised, 40=Grandfathered. |
| `CONSERVE` | Conservatorship | 1=yes, 0=no — institution in government conservatorship. |
| `INSDATE` | Date of Deposit Insurance | Date institution obtained federal deposit insurance. |
| `INSAGENT1` | Insurance Fund Membership | DIF, BIF, or SAIF. |
| `INSAGENT2` | Secondary Insurance Fund | No longer applicable after April 1, 2006 (single DIF). |
| `INSAGNT1` | Primary Insurance Agency | Abbreviated primary insurance agency. |
| `INSAGNT2` | Secondary Insurance Fund | Same as INSAGENT2 (abbreviated). |
| `LAW_SASSER_FLG` | Law Sasser Flag | OTS S&As that converted charter. Not applicable after March 31, 2006. |
| `UNINUM` | FDIC Unique Number | Unique identifier for holding companies, banks, branches, nondeposit subsidiaries. |

### Current Institution Geographic Fields

| Field | Label | Definition |
|---|---|---|
| `ADDRESS` | Street Address | Physical street address of institution or branch. |
| `ADDRESS2` | Street Address Line 2 | Physical street address line 2. |
| `CITY` | City | City where institution or branch is physically located. |
| `STATE` | Physical State | State where institution or branch is physically located. |
| `STALP` | State Alpha Code | State abbreviation of institution's main office. **NOT POPULATED on live API — use PSTALP.** |
| `STNAME` | State Name | Full state name. |
| `STNUM` | State Number | FIPS state code. |
| `LOCN_PHY_ST_NUM` | State Number | FIPS state code for physical address. **NOT POPULATED on live API — use STNUM.** |
| `CNTYNAME` | County | County name (abbreviated if >16 chars). |
| `CNTYNUM` | County Number | FIPS county code. |
| `MSA` | Metropolitan Statistical Area | MSA name (pre-2000 OMB definitions). **NOT POPULATED on live API.** |
| `MSA_NO` | MSA Number | MSA number. **NOT POPULATED on live API.** |
| `ZIP` | Zip Code | First 3-5 digits of postal zip code. |
| `ZIP_RAW` | 5-Digit Zip Code | Full 5-digit postal code. |
| `ZIPREST` | Zip Code Extension | 4-digit zip extension. |
| `PADDR` | Physical Street Address | Physical street address. |
| `PADDR2` | Physical Street Address Line 2 | Physical street address line 2. |
| `PCITY` | Physical City | City of physical location. |
| `PSTALP` | Physical State Alpha Code | State abbreviation of physical location. **USE THIS for institution state.** |
| `PZIP5` | Physical Zip Code | First 3-5 digits of physical location zip. |
| `PZIPREST` | Physical Zip Code Extension | 4-digit zip extension of physical location. |

### Current Institution Mailing Fields

| Field | Label | Definition |
|---|---|---|
| `MADDR` | Mailing Street Address | Mailing address street. |
| `MADDR2` | Mailing Street Address Line 2 | Mailing address street line 2. |
| `MAILING_ADDRESS` | Mailing Address | Mailing address. |
| `MAILING_ADDRESS2` | Mailing Address Line 2 | Mailing address line 2. |
| `MCITY` | Mailing City | Mailing address city. |
| `MAILING_CITY` | Mailing City | Mailing address city (alternate name). |
| `MSTALP` | Mailing State Alpha Code | 2-digit mailing state code. |
| `MAILING_STALP` | Mailing State Alpha Code | 2-digit mailing state code (alternate name). |
| `MSTATE` | Mailing State | Mailing state name. |
| `MAILING_STATE` | Mailing State | Mailing state name (alternate name). |
| `MZIP5` | Mailing Zip Code | Mailing zip (3-5 digits). |
| `MAILING_ZIP` | Mailing Zip Code | Mailing zip (alternate name). |
| `MZIP5_RAW` | Mailing 5-Digit Zip Code | Full 5-digit mailing zip. |
| `MAILING_ZIP5_RAW` | Mailing 5-Digit Zip Code | Full 5-digit mailing zip (alternate name). |
| `MZIPREST` | Mailing Zip Code Extension | 4-digit mailing zip extension. |
| `MAILING_ZIPREST` | Mailing Zip Code Extension | 4-digit mailing zip extension (alternate name). |

### Regulatory/Supervisory Fields

| Field | Label | Definition |
|---|---|---|
| `FDICREGION` | Supervisory Region | Two-digit code: 02=New York, 05=Atlanta, 09=Chicago, 11=Kansas City, 13=Dallas, 14=San Francisco, 16=CFI. |
| `FDICREGION_DESC` | Supervisory Region Description | Name of FDIC supervisory region. |
| `SUPRV_FD` | Supervisory Region Number | Same as FDICREGION. |
| `SUPVR_FD_DESC` | Supervisory Region Description | Same as FDICREGION_DESC. |
| `OCCDIST` | OCC District | OCC district: Northeast, Southeast, Central, Midwest, Southwest, West. |
| `CFPBEFFDTE` | CFPB Effective Date | Date institution began CFPB supervision. |
| `CFPBENDDTE` | CFPB End Date | Date institution ended CFPB supervision. |

### Office/Branch Fields (OFF_ prefix)

| Field | Label | Definition |
|---|---|---|
| `OFF_NAME` | Office Name | Legal name of the office. |
| `OFF_NUM` | Branch Number | Branch's corresponding office number. |
| `OFFNAME` | Office Name | Branch office name (alternate). |
| `OFFNUM` | Branch Number | Branch office number used internally by FDIC (alternate). |
| `OFF_CNTYNAME` | Office County Name | County where branch is physically located. |
| `OFF_CNTYNUM` | Office County Number | FIPS county code of branch. **Key field for GEOID5 construction.** |
| `OFF_PADDR` | Office Physical Street Address | Branch physical street address. |
| `OFF_PADDR2` | Office Physical Street Address Line 2 | Branch physical street address line 2. |
| `OFF_PCITY` | Office Physical City | Branch physical city. |
| `OFF_PSTALP` | Office Physical State Alpha Code | Branch 2-digit state code. **USE THIS for branch state.** |
| `OFF_PSTATE` | Office Physical State | Branch full state name. |
| `OFF_PZIP5` | Office Physical Zip Code | Branch zip (3-5 digits). |
| `OFF_PZIPREST` | Office Physical Zip Code Extension | Branch 4-digit zip extension. |
| `OFF_SERVTYPE` | Office Service Type | Service type code: 11=Full brick-and-mortar, 12=Full retail, 13=Full cyber, 21=Limited admin, 22=Limited military, 23=Limited drive-through, 24=Limited LPO, 25=Limited consumer credit, 26=Limited contractual, 27=Limited messenger, 28=Limited retail, 29=Limited mobile, 30=Limited trust. |
| `OFF_SERVTYPE_DESC` | Office Service Type Description | Service type description. |
| `OFF_EFFDATE` | Office Structure Change Effective Date | Date of branch change/event. |
| `FI_UNINIM` | FDIC Unique Number | Maps branch back to parent institution. **Note: typo in schema — should be FI_UNINUM.** |

### Activity/Event Fields

| Field | Label | Definition |
|---|---|---|
| `CHANGECODE` | Activity Event Code | Code identifying the change/event. |
| `CHANGECODE_DESC` | Activity Event Code Description | Description of the change/event. |
| `ACT_EVT_DESC` | Activity Event Description | Description of event causing changes to activities/ownership. |
| `ACT_EVT_NUM` | Activity Event Number | Number indicating a change/event to activities/ownership. |
| `ACT_EVT1_NUM` through `ACT_EVT5_NUM` | Activity Event Numbers | Multiple event numbers for compound events. |
| `TRANSNUM` | System Transaction Number | Unique number identifying the change/event. |
| `ORG_ROLE_CDE` | Organization Role Code | FI=Financial Institution, BR=Branch, PA. |
| `REPORT_TYPE` | Report Type | Type of report. |

### Date Fields

| Field | Label | Definition |
|---|---|---|
| `EFFDATE` | Last Structure Change Effective Date | When the change/event is effective. |
| `FI_EFFDATE` | Last Structure Change Effective Date | Institution-level effective date. |
| `ENDDATE` | End Effective Date | End/close date for the structural event. |
| `ENDEFYMD` | End Date | Date that closes out last structural event. For closed institutions = inactive date. |
| `PROCDATE` | Last Structure Change Process Date | When the change/event was processed. |
| `ORG_EFF_NUM_DTE` | Effective Date Numerical | Numerical effective date value. |
| `ORG_END_NUM_DTE` | End Date Numerical | Numerical end date value. |
| `SYS_LST_DTETME` | System Last Datetime | Last update to a record. |

### Acquiring Institution Fields (ACQ_ prefix) — 32 fields

Used when one institution acquires another. All follow the same pattern as institution fields but prefixed with `ACQ_`.

| Field | Label |
|---|---|
| `ACQ_CERT` | Acquiring FDIC Certificate # |
| `ACQ_CHANGECODE` | Acquiring Activity Event Code |
| `ACQ_CHARTAGENT` | Acquiring Chartering Agency |
| `ACQ_CHARTER` | Acquiring OCC Charter Number |
| `ACQ_CLASS` | Acquiring Class Designation |
| `ACQ_CLCODE` | Acquiring Numeric Class Code |
| `ACQ_CNTYNAME` | Acquiring County Name |
| `ACQ_CNTYNUM` | Acquiring County Number (FIPS) |
| `ACQ_FDICREGION` | Acquiring Supervisory Region Number |
| `ACQ_FDICREGION_DESC` | Acquiring Supervisory Region Description |
| `ACQ_INSAGENT1` | Acquiring Insurance Fund Membership |
| `ACQ_INSAGENT2` | Acquiring Secondary Insurance Fund |
| `ACQ_INSTNAME` | Acquiring Institution Name |
| `ACQ_MADDR` / `ACQ_MADDR2` | Acquiring Mailing Address |
| `ACQ_MCITY` | Acquiring Mailing City |
| `ACQ_MSTALP` / `ACQ_MSTATE` | Acquiring Mailing State |
| `ACQ_MZIP5` / `ACQ_MZIP5_RAW` / `ACQ_MZIPREST` | Acquiring Mailing Zip |
| `ACQ_ORG_EFF_DTE` | Acquiring Institution Effective Date |
| `ACQ_PADDR` / `ACQ_PADDR2` | Acquiring Physical Address |
| `ACQ_PCITY` | Acquiring Physical City |
| `ACQ_PSTALP` | Acquiring Physical State Alpha Code |
| `ACQ_PZIP5` / `ACQ_PZIP5_RAW` / `ACQ_PZIPREST` | Acquiring Physical Zip |
| `ACQ_REGAGENT` | Acquiring Chartering Agency |
| `ACQ_TRUST` | Acquiring Trust Power |
| `ACQ_UNINUM` | Acquiring FDIC Unique Number |
| `ORG_ACQ_CERT_NUM` | Acquiring FDIC Certificate # (alternate) |

### Outgoing Institution Fields (OUT_ prefix) — 30 fields

The divesting/exiting institution in a merger/acquisition. Same pattern as ACQ_ fields.

| Field | Label |
|---|---|
| `OUT_CERT` | Outgoing FDIC Certificate # |
| `OUT_CHARTAGENT` | Outgoing Chartering Agency |
| `OUT_CHARTER` | Outgoing OCC Charter Number |
| `OUT_CLASS` | Outgoing Class |
| `OUT_CLCODE` | Outgoing Class Code |
| `OUT_CNTYNAME` | Outgoing County Name |
| `OUT_CNTYNUM` | Outgoing County Number (FIPS) |
| `OUT_FDICREGION` / `OUT_FDICREGION_DESC` | Outgoing Supervisory Region |
| `OUT_INSAGENT1` / `OUT_INSAGENT2` | Outgoing Insurance Fund |
| `OUT_INSTNAME` | Outgoing Institution Name |
| `OUT_MADDR` / `OUT_MADDR2` / `OUT_MCITY` / `OUT_MSTALP` / `OUT_MSTATE` | Outgoing Mailing Address |
| `OUT_MZIP5` / `OUT_MZIP5_RAW` / `OUT_MZIPREST` | Outgoing Mailing Zip |
| `OUT_PADDR` / `OUT_PADDR2` / `OUT_PCITY` / `OUT_PSTALP` | Outgoing Physical Address |
| `OUT_PZIP5` / `OUT_PZIP5_RAW` / `OUT_PZIPREST` | Outgoing Physical Zip |
| `OUT_REGAGENT` | Outgoing Chartering Agency |
| `OUT_TRUST` | Outgoing Trust Power |
| `OUT_UNINUM` | Outgoing FDIC Unique Number |

### Surviving Institution Fields (SUR_ prefix) — 29 fields

The surviving entity after a merger/acquisition. Same pattern as ACQ_/OUT_ fields.

| Field | Label |
|---|---|
| `SUR_CERT` | Surviving FDIC Certificate # |
| `SUR_CHANGECODE` | Surviving Activity Event Code |
| `SUR_CHARTAGENT` | Surviving Chartering Agency |
| `SUR_CHARTER` | Surviving OCC Charter Number |
| `SUR_CLASS` | Surviving Class |
| `SUR_CLCODE` | Surviving Class Code |
| `SUR_CNTYNAME` | Surviving County |
| `SUR_CNTYNUM` | Surviving County Number (FIPS) |
| `SUR_FDICREGION` / `SUR_FDICREGION_DESC` | Surviving Supervisory Region |
| `SUR_INSAGENT1` / `SUR_INSAGENT2` | Surviving Insurance Fund |
| `SUR_INSTNAME` | Surviving Institution Name |
| `SUR_MADDR` / `SUR_MADDR2` / `SUR_MCITY` / `SUR_MSTALP` / `SUR_MSTATE` | Surviving Mailing Address |
| `SUR_MZIP5` / `SUR_MZIP5_RAW` | Surviving Mailing Zip |
| `SUR_PADDR` / `SUR_PADDR2` / `SUR_PCITY` / `SUR_PSTALP` | Surviving Physical Address |
| `SUR_PZIP5` / `SUR_PZIP5_RAW` / `SUR_PZIPREST` | Surviving Physical Zip |
| `SUR_REGAGENT` | Surviving Chartering Agency |
| `SUR_TRUST` | Surviving Trust Power |

### Previous/Former Fields (FRM_ prefix) — 36 fields

Historical state of institution/branch before a change event.

**Institution-level (FRM_):**

| Field | Label |
|---|---|
| `FRM_CERT` | Previous FDIC Certificate # |
| `FRM_CHARTAGENT` | Previous Chartering Agency |
| `FRM_CLASS` | Previous Bank Charter Class |
| `FRM_CLCODE` | Previous Numeric Code |
| `FRM_CNTYNAME` | Previous County |
| `FRM_CNTYNUM` | Previous County Number (FIPS) |
| `FRM_INSTNAME` | Previous Institution Name |
| `FRM_PADDR` / `FRM_PADDR2` / `FRM_PCITY` / `FRM_PSTALP` | Previous Physical Address |
| `FRM_PZIP5` / `FRM_PZIP5_RAW` / `FRM_PZIPREST` | Previous Physical Zip |
| `FRM_REGAGENT` | Previous Chartering Agency |
| `FRM_TRUST` | Previous Trust Power |

**Office-level (FRM_OFF_):**

| Field | Label |
|---|---|
| `FRM_OFF_CHARTAGENT` | Previous Office Chartering Agency |
| `FRM_OFF_CLASS` | Previous Office Class |
| `FRM_OFF_CLCODE` | Previous Office Numeric Code |
| `FRM_OFF_CNTYNAME` | Previous Office County |
| `FRM_OFF_CNTYNUM` | Previous Office County Number (FIPS) |
| `FRM_OFF_NAME` / `FRM_OFFNAME` | Previous Office/Branch Name |
| `FRM_OFF_NUM` / `FRM_OFFNUM` | Previous Office/Branch Number |
| `FRM_OFF_PADDR` / `FRM_OFF_PADDR2` / `FRM_OFF_PCITY` / `FRM_OFF_PSTALP` | Previous Office Physical Address |
| `FRM_OFF_PZIP5` / `FRM_OFF_PZIP5_RAW` / `FRM_OFF_PZIPREST` | Previous Office Physical Zip |
| `FRM_OFF_REGAGENT` | Previous Office Regulator |
| `FRM_OFF_SERVTYPE` / `FRM_OFF_SERVTYPE_DESC` | Previous Office Service Type |
| `FRM_OFF_STATE` | Previous Office State |
| `FRM_OFF_TRUST` | Previous Office Trust Power |
