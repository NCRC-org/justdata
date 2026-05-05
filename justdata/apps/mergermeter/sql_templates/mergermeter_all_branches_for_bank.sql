    WITH
    -- CBSA crosswalk to get CBSA codes and names from GEOID5 (include all areas for the lookup)
    cbsa_crosswalk AS (
        SELECT
            CAST(geoid5 AS STRING) as geoid5,
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name,
            County as county_name,
            State as state_name,
            CONCAT(County, ', ', State) as county_state
        FROM `{PROJECT_ID}.shared.cbsa_to_county`
    ),

    -- Get all branches for the bank
    bank_branches AS (
        SELECT
            CAST(b.rssd AS STRING) as rssd,
            CAST(b.geoid5 AS STRING) as geoid5,
            b.uninumbr
        FROM `{PROJECT_ID}.branchsight.sod` b
        WHERE CAST(b.year AS STRING) = '{year}'
            AND CAST(b.rssd AS STRING) = '{rssd}'
            AND b.geoid5 IS NOT NULL
    ),

    -- Deduplicate branches (use uninumbr as unique identifier)
    deduplicated_branches AS (
        SELECT
            geoid5
        FROM (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY uninumbr ORDER BY rssd) as rn
            FROM bank_branches
        )
        WHERE rn = 1
    ),

    -- Join with CBSA crosswalk and aggregate by county/CBSA
    branch_counties AS (
        SELECT
            db.geoid5,
            COALESCE(c.county_state, 'Unknown') as county_state,
            COALESCE(c.county_name, 'Unknown') as county_name,
            COALESCE(c.state_name, 'Unknown') as state_name,
            -- For CBSA code, treat 99999 (rural) as N/A
            CASE WHEN COALESCE(c.cbsa_code, 'N/A') = '99999' THEN 'N/A' ELSE COALESCE(c.cbsa_code, 'N/A') END as cbsa_code,
            CASE WHEN COALESCE(c.cbsa_code, 'N/A') = '99999' THEN 'Non-Metro Area' ELSE COALESCE(c.cbsa_name, 'Non-Metro Area') END as cbsa_name,
            COUNT(*) as branch_count
        FROM deduplicated_branches db
        LEFT JOIN cbsa_crosswalk c
            ON db.geoid5 = c.geoid5
        GROUP BY db.geoid5, c.county_state, c.county_name, c.state_name, c.cbsa_code, c.cbsa_name
    )

    SELECT
        geoid5,
        county_state,
        county_name,
        state_name,
        cbsa_code,
        cbsa_name,
        branch_count
    FROM branch_counties
    WHERE cbsa_code != '99999'
    ORDER BY cbsa_code, county_state
