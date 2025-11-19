# Assessment Area File Format Guide

MergerMeter supports multiple formats for assessment area files. The **recommended format** uses state FIPS codes and county FIPS codes for precise county matching.

## Recommended Format: State Code + County Code

This format uses state FIPS codes (2 digits) and county FIPS codes (3 digits) to create GEOID5 (5 digits total) for precise matching.

### Example JSON File

```json
[
  {
    "cbsa_name": "Tampa-St. Petersburg-Clearwater, FL",
    "counties": [
      {
        "state_code": "12",
        "county_code": "057"
      },
      {
        "state_code": "12",
        "county_code": "103"
      },
      {
        "geoid5": "12101"
      }
    ]
  },
  {
    "name": "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD",
    "counties": [
      {
        "state_code": "42",
        "county_code": "101"
      },
      {
        "state_code": "10",
        "county_code": "003"
      }
    ]
  }
]
```

### Alternative: Direct GEOID5

You can also provide GEOID5 directly (5 digits: state FIPS + county FIPS):

```json
[
  {
    "assessment_area": "Metro Area 1",
    "counties": [
      {"geoid5": "12057"},
      {"geoid5": "12103"},
      {"geoid5": "12101"}
    ]
  }
]
```

## Legacy Format: County Names

The tool still supports the legacy format using county names, but this is less precise:

```json
[
  {
    "cbsa_name": "Tampa-St. Petersburg-Clearwater, FL",
    "counties": [
      "Hillsborough County, Florida",
      "Pinellas County, Florida",
      "Pasco County, Florida"
    ]
  }
]
```

## Mixed Format

You can mix formats within the same file:

```json
[
  {
    "name": "Assessment Area 1",
    "counties": [
      {"state_code": "12", "county_code": "057"},
      "Hillsborough County, Florida",
      {"geoid5": "12103"}
    ]
  }
]
```

## Finding State and County FIPS Codes

### Option 1: Use BigQuery

Query the `geo.cbsa_to_county` table:

```sql
SELECT 
  State,
  County,
  SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
  SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 3, 3) as county_fips,
  CAST(geoid5 AS STRING) as geoid5
FROM `your-project.geo.cbsa_to_county`
WHERE State = 'Florida' AND County = 'Hillsborough'
```

### Option 2: Use Census Bureau Resources

- [FIPS State Codes](https://www.census.gov/library/reference/code-lists/ansi.html)
- [FIPS County Codes](https://www.census.gov/library/reference/code-lists/ansi.html)

### Option 3: GEOID5 Lookup

GEOID5 = State FIPS (2 digits) + County FIPS (3 digits)

Example:
- Florida state FIPS: `12`
- Hillsborough County FIPS: `057`
- GEOID5: `12057`

## File Structure

### Top-Level Array (Recommended)

```json
[
  {
    "cbsa_name": "Assessment Area 1",
    "counties": [...]
  },
  {
    "name": "Assessment Area 2",
    "counties": [...]
  }
]
```

### Nested Structure

```json
{
  "assessment_areas": [
    {
      "cbsa_name": "Assessment Area 1",
      "counties": [...]
    }
  ]
}
```

### Single Assessment Area

```json
{
  "cbsa_name": "Assessment Area 1",
  "counties": [...]
}
```

## Field Names

The tool accepts multiple field names for assessment area names:
- `cbsa_name` (preferred)
- `name`
- `assessment_area`
- `aa_name`

For counties:
- `counties` (preferred)
- `county_list`
- `county`

## Benefits of State/County Code Format

1. **Precision**: Eliminates ambiguity from county name variations
2. **Performance**: Faster lookups using numeric codes
3. **Reliability**: No issues with "County" vs "Parish" vs "Borough" suffixes
4. **Consistency**: Standardized FIPS codes across all data sources

## MSA Code Support

You can also include MSA codes in the counties list:

```json
{
  "name": "Assessment Area with MSA",
  "counties": [
    "MSA 45300",
    {"state_code": "12", "county_code": "057"}
  ]
}
```

The tool will automatically expand MSA codes to their constituent counties.



