WITH assessment_area_counties AS (
    SELECT DISTINCT geoid5
    FROM UNNEST([{geoid5_str}]) as geoid5
),

-- CBSA crosswalk to get CBSA codes from GEOID5
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

-- Filter branches to assessment area counties and year
filtered_branches AS (
    SELECT
        CAST(b.rssd AS STRING) as rssd,
        b.bank_name as institution_name,
        COALESCE(c.cbsa_code, 'N/A') as cbsa_code,
        COALESCE(c.cbsa_name, CONCAT(c.state_name, ' Non-MSA')) as cbsa_name,
        CAST(b.geoid5 AS STRING) as county_code,
        c.county_state,
        c.county_name,
        COALESCE(c.state_name, b.state) as state_name,
        b.geoid,
        b.br_lmi,
        b.br_minority as cr_minority,
        b.uninumbr
    FROM `justdata-ncrc.branchsight.sod` b
    LEFT JOIN cbsa_crosswalk c
        ON CAST(b.geoid5 AS STRING) = c.county_code
    WHERE CAST(b.year AS STRING) = '{year}'
        AND CAST(b.geoid5 AS STRING) IN ({geoid5_str})
        AND CAST(b.rssd AS STRING) = '{subject_rssd}'
),

-- Deduplicate branches (use uninumbr as unique identifier)
deduplicated_branches AS (
    SELECT 
        rssd,
        institution_name,
        cbsa_code,
        cbsa_name,
        county_code,
        county_state,
        county_name,
        state_name,
        geoid,
        br_lmi,
        cr_minority
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (PARTITION BY uninumbr ORDER BY rssd) as rn
        FROM filtered_branches
    )
    WHERE rn = 1
),

-- Prepare grouping key for Non-MSA areas
grouped_branches AS (
    SELECT 
        *,
        CASE 
            WHEN cbsa_code = 'N/A' OR cbsa_code IS NULL THEN CONCAT(state_name, ' Non-MSA')
            ELSE cbsa_code
        END as group_key,
        CASE 
            WHEN cbsa_code = 'N/A' OR cbsa_code IS NULL THEN CONCAT(state_name, ' Non-MSA')
            ELSE COALESCE(cbsa_name, cbsa_code)
        END as group_name
    FROM deduplicated_branches
)

-- Aggregate by CBSA for subject bank
-- For Non-MSA areas (cbsa_code = 'N/A'), group by state name
SELECT 
    group_key as cbsa_code,
    group_name as cbsa_name,
    COUNT(*) as total_branches,
    COUNTIF(br_lmi = 1) as branches_in_lmict,
    SAFE_DIVIDE(COUNTIF(br_lmi = 1), COUNT(*)) * 100 as pct_lmict,
    COUNTIF(cr_minority = 1) as branches_in_mmct,
    SAFE_DIVIDE(COUNTIF(cr_minority = 1), COUNT(*)) * 100 as pct_mmct,
    -- Count branches that are both LMICT and MMCT
    COUNTIF(br_lmi = 1 AND cr_minority = 1) as branches_lmict_mmct,
    -- Count branches that are LMI only (not MMCT)
    COUNTIF(br_lmi = 1 AND cr_minority = 0) as branches_lmi_only,
    -- Count branches that are MMCT only (not LMI)
    COUNTIF(br_lmi = 0 AND cr_minority = 1) as branches_mmct_only
FROM grouped_branches
GROUP BY group_key, group_name
ORDER BY group_key
