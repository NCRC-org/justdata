-- CBSA crosswalk to get CBSA codes and names from GEOID5 (counties in assessment areas)
WITH cbsa_crosswalk AS (
    SELECT DISTINCT
        CAST(geoid5 AS STRING) as geoid5,
        CAST(cbsa_code AS STRING) as cbsa_code,
        CBSA as cbsa_name,
        State as state_name,
        -- Extract state FIPS code from geoid5 (first 2 digits) for Goals Calculator state tabs
        LPAD(SUBSTR(CAST(geoid5 AS STRING), 1, 2), 2, '0') as state_code
    FROM `justdata-ncrc.shared.cbsa_to_county`
    WHERE CAST(geoid5 AS STRING) IN ('{geoid5_list}')
),
filtered_sb_data AS (
    SELECT
        CAST(d.year AS STRING) as year,
        COALESCE(c.cbsa_code, 'N/A') as cbsa_code,
        COALESCE(c.cbsa_name,
            CASE
                WHEN c.state_name IS NOT NULL THEN CONCAT(c.state_name, ' Non-MSA')
                ELSE 'Non-MSA'
            END
        ) as cbsa_name,
        c.state_code,
        COALESCE(d.total_loans, d.num_under_100k + d.num_100k_250k + d.num_250k_1m) as sb_loans_count,
        -- SB amounts are stored in thousands of dollars, convert to actual dollars
        (d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m) * 1000 as sb_loans_amount,
        -- LMICT: Use pre-computed lmi_tract_loans from summary table
        COALESCE(d.lmi_tract_loans, 0) as lmict_loans_count,
        -- Estimate LMICT amount proportionally (lmi_tract_loans / total_loans * total_amount)
        SAFE_MULTIPLY(
            SAFE_DIVIDE(COALESCE(d.lmi_tract_loans, 0), NULLIF(COALESCE(d.total_loans, d.num_under_100k + d.num_100k_250k + d.num_250k_1m), 0)),
            (d.amt_under_100k + d.amt_100k_250k + d.amt_250k_1m) * 1000
        ) as lmict_loans_amount,
        COALESCE(d.numsbrev_under_1m, 0) as loans_rev_under_1m,
        COALESCE(d.amtsbrev_under_1m, 0) * 1000 as amount_rev_under_1m
    FROM `justdata-ncrc.bizsight.sb_county_summary` d
    LEFT JOIN cbsa_crosswalk c
        ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = c.geoid5
    WHERE CAST(d.year AS STRING) IN ('{years_list}')
        AND LPAD(CAST(d.geoid5 AS STRING), 5, '0') IN ('{geoid5_list}')
        AND d.respondent_id IN ('{id_list}')
        AND c.cbsa_code IS NOT NULL  -- Only include counties that have a CBSA mapping (in assessment areas)
),
aggregated_sb_metrics AS (
    SELECT
        year,
        state_code,
        cbsa_code,
        MAX(cbsa_name) as cbsa_name,  -- Get CBSA name (should be same for all rows with same cbsa_code)
        SUM(sb_loans_count) as sb_loans_total,
        SUM(sb_loans_amount) as sb_loans_amount,
        SUM(lmict_loans_count) as lmict_count,
        SUM(lmict_loans_amount) as lmict_loans_amount,
        SUM(loans_rev_under_1m) as loans_rev_under_1m_count,
        SUM(amount_rev_under_1m) as amount_rev_under_1m,
        -- Calculate averages directly in the query
        SAFE_DIVIDE(SUM(lmict_loans_amount), SUM(lmict_loans_count)) as avg_sb_lmict_loan_amount,
        SAFE_DIVIDE(SUM(amount_rev_under_1m), SUM(loans_rev_under_1m)) as avg_loan_amt_rum_sb
    FROM filtered_sb_data
    GROUP BY year, state_code, cbsa_code
)
SELECT * FROM aggregated_sb_metrics
ORDER BY year, state_code, cbsa_code
