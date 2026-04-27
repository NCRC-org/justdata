    WITH
    -- CBSA crosswalk to get CBSA codes and names from GEOID5 (exclude rural areas with code 99999)
    cbsa_crosswalk AS (
        SELECT
            CAST(geoid5 AS STRING) as geoid5,
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name
        FROM `{PROJECT_ID}.shared.cbsa_to_county`
        WHERE CAST(cbsa_code AS STRING) != '99999'
    ),
    
    -- Get all branch deposits by county for the subject bank
    bank_deposits_by_county AS (
        SELECT 
            CAST(b.geoid5 AS STRING) as geoid5,
            SUM(b.deposits_000s * 1000) as bank_deposits  -- Convert from thousands to actual amount
        FROM `{PROJECT_ID}.branchsight.sod` b
        WHERE CAST(b.year AS STRING) = '{year}'
            AND CAST(b.rssd AS STRING) = '{rssd}'
            AND b.geoid5 IS NOT NULL
            AND b.deposits_000s IS NOT NULL
            AND b.deposits_000s > 0
        GROUP BY geoid5
    ),
    
    -- Calculate total national deposits for the bank
    total_national_deposits AS (
        SELECT SUM(bank_deposits) as total_deposits
        FROM bank_deposits_by_county
    ),
    
    -- Get state info for non-metro counties
    state_crosswalk AS (
        SELECT
            CAST(geoid5 AS STRING) as geoid5,
            State as state_name
        FROM `{PROJECT_ID}.shared.cbsa_to_county`
    ),
    
    -- Aggregate bank deposits by CBSA (for metro areas) and by State (for non-metro)
    bank_deposits_by_cbsa AS (
        SELECT 
            CASE 
                WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                THEN CONCAT('NON-METRO-', s.state_name)
                ELSE CAST(c.cbsa_code AS STRING)
            END as cbsa_code,
            CASE 
                WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                THEN CONCAT(s.state_name, ' Non-Metro Area')
                ELSE COALESCE(c.cbsa_name, 'Non-Metro Area')
            END as cbsa_name,
            SUM(bd.bank_deposits) as cbsa_deposits,
            MAX(s.state_name) as state_name  -- For non-metro areas, track the state
        FROM bank_deposits_by_county bd
        LEFT JOIN cbsa_crosswalk c
            ON bd.geoid5 = c.geoid5
        LEFT JOIN state_crosswalk s
            ON bd.geoid5 = s.geoid5
        GROUP BY 
            CASE 
                WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                THEN CONCAT('NON-METRO-', s.state_name)
                ELSE CAST(c.cbsa_code AS STRING)
            END,
            CASE 
                WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                THEN CONCAT(s.state_name, ' Non-Metro Area')
                ELSE COALESCE(c.cbsa_name, 'Non-Metro Area')
            END,
            s.state_name
        HAVING SUM(bd.bank_deposits) > 0
    )
    
    -- Calculate percentage of national deposits in each CBSA
    SELECT 
        bdc.cbsa_code,
        bdc.cbsa_name,
        bdc.cbsa_deposits,
        SAFE_DIVIDE(bdc.cbsa_deposits, tnd.total_deposits) * 100 as national_deposit_share_pct,
        tnd.total_deposits as total_national_deposits,
        bdc.state_name
    FROM bank_deposits_by_cbsa bdc
    CROSS JOIN total_national_deposits tnd
    WHERE tnd.total_deposits > 0
    ORDER BY national_deposit_share_pct DESC, cbsa_code
