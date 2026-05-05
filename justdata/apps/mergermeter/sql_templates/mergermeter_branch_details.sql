WITH assessment_area_counties AS (
    SELECT DISTINCT geoid5
    FROM UNNEST([{geoid5_str}]) as geoid5
),

-- CBSA crosswalk to get CBSA codes and county info from GEOID5
cbsa_crosswalk AS (
    SELECT
        CAST(geoid5 AS STRING) as county_code,
        CAST(cbsa_code AS STRING) as cbsa_code,
        cbsa as cbsa_name,
        County as county_name,
        State as state_name,
        CONCAT(County, ', ', State) as county_state
    FROM `justdata-ncrc.shared.cbsa_to_county`
),

-- Get individual branch details
filtered_branches AS (
    SELECT 
        CAST(b.rssd AS STRING) as rssd,
        b.bank_name,
        b.branch_name,
        b.address,
        b.city,
        COALESCE(c.state_name, b.state) as state,
        COALESCE(c.county_name, b.county) as county,
        b.zip,
        CAST(b.geoid AS STRING) as census_tract,
        CAST(b.latitude AS FLOAT64) as latitude,
        CAST(b.longitude AS FLOAT64) as longitude,
        CAST(b.geoid5 AS STRING) as geoid5,
        c.county_state,
        b.uninumbr
    FROM `justdata-ncrc.branchsight.sod` b
    LEFT JOIN cbsa_crosswalk c
        ON CAST(b.geoid5 AS STRING) = c.county_code
    WHERE CAST(b.year AS STRING) = '{year}'
        AND CAST(b.geoid5 AS STRING) IN ({geoid5_str})
        AND CAST(b.rssd AS STRING) = '{subject_rssd}'
)

-- Deduplicate branches (use uninumbr as unique identifier) and return individual records
SELECT 
    bank_name,
    branch_name,
    address,
    city,
    state,
    zip,
    county,
    census_tract,
    latitude,
    longitude
FROM (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY uninumbr ORDER BY rssd) as rn
    FROM filtered_branches
)
WHERE rn = 1
ORDER BY state, county, city, branch_name
