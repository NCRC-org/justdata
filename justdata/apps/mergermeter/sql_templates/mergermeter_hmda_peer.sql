WITH cbsa_crosswalk AS (
    SELECT
        CAST(geoid5 AS STRING) as county_code,
        -- Treat NULL/empty cbsa_code as '99999' for rural areas
        COALESCE(NULLIF(CAST(cbsa_code AS STRING), ''), '99999') as cbsa_code,
        COALESCE(cbsa, CONCAT(State, ' Non-MSA')) as cbsa_name
    FROM `justdata-ncrc.shared.cbsa_to_county`
),
-- Filter HMDA data to user-selected assessment area counties (includes all lenders for peer comparison)
-- Note: de_hmda has pre-computed race/ethnicity and income flags as BOOL columns
filtered_hmda AS (
    SELECT
        CAST(h.activity_year AS STRING) as activity_year,
        -- Use COALESCE to treat NULL cbsa_code as '99999' for rural areas
        COALESCE(c.cbsa_code, '99999') as cbsa_code,
        -- State code for Goals Calculator state tabs (derived from county_code, first 2 digits are state FIPS)
        LPAD(SUBSTR(CAST(h.county_code AS STRING), 1, 2), 2, '0') as state_code,
        -- Loan purpose category for HP/Refi/HI breakdown
        -- HMDA codes: 1=Home Purchase, 2=Home Improvement, 31=Refinancing, 32=Cash-out Refi, 4=Home Equity, 5=N/A
        -- NCRC methodology: Home Equity = loan purposes 2 (Home Improvement) + 4 (Other/Home Equity)
        CASE
            WHEN h.loan_purpose = '1' THEN 'hp'
            WHEN h.loan_purpose IN ('2', '4') THEN 'hi'
            WHEN h.loan_purpose IN ('31', '32') THEN 'refi'
            ELSE 'other'
        END as loan_purpose_cat,
        h.lei,
        h.loan_amount,
        -- Use pre-computed flags from de_hmda table (convert BOOL to INT for aggregation)
        CASE WHEN h.is_lmict THEN 1 ELSE 0 END as is_lmict,
        CASE WHEN h.is_lmib THEN 1 ELSE 0 END as is_lmib,
        CASE WHEN h.is_mmct THEN 1 ELSE 0 END as is_mmct,
        CASE WHEN h.is_hispanic THEN 1 ELSE 0 END as is_hispanic,
        CASE WHEN h.is_black THEN 1 ELSE 0 END as is_black,
        CASE WHEN h.is_asian THEN 1 ELSE 0 END as is_asian,
        CASE WHEN h.is_native_american THEN 1 ELSE 0 END as is_native_american,
        CASE WHEN h.is_hopi THEN 1 ELSE 0 END as is_hopi
    FROM `justdata-ncrc.shared.de_hmda` h
    LEFT JOIN cbsa_crosswalk c
        ON h.geoid5 = c.county_code
    WHERE CAST(h.activity_year AS STRING) IN ('{years_list}')
        {action_taken_filter}
        {occupancy_filter}
        {reverse_filter}
        {construction_filter}
        {units_filter}
        {loan_purpose_filter}
        -- Filter to user-selected assessment area counties (use geoid5 which is already normalized)
        AND h.geoid5 IN ('{geoid5_list}')
),
subject_volume AS (
    SELECT 
        activity_year,
        cbsa_code,
        COUNT(*) as subject_vol
    FROM filtered_hmda
    WHERE lei = '{subject_lei}'
    GROUP BY activity_year, cbsa_code
),
all_lenders_volume AS (
    SELECT
        activity_year,
        cbsa_code,
        lei,
        COUNT(*) as lender_vol
    FROM filtered_hmda
    GROUP BY activity_year, cbsa_code, lei
),
peers AS (
    SELECT DISTINCT
        al.activity_year,
        al.cbsa_code,
        al.lei
    FROM all_lenders_volume al
    INNER JOIN subject_volume sv
        ON al.activity_year = sv.activity_year
        AND al.cbsa_code = sv.cbsa_code
    LEFT JOIN (
        -- Count volume-matched peers per CBSA/year
        SELECT al2.activity_year, al2.cbsa_code, COUNT(DISTINCT al2.lei) as peer_count
        FROM all_lenders_volume al2
        INNER JOIN subject_volume sv2
            ON al2.activity_year = sv2.activity_year
            AND al2.cbsa_code = sv2.cbsa_code
        WHERE al2.lei != '{subject_lei}'
            AND al2.lender_vol >= sv2.subject_vol * 0.5
            AND al2.lender_vol <= sv2.subject_vol * 2.0
        GROUP BY al2.activity_year, al2.cbsa_code
    ) vpc ON al.activity_year = vpc.activity_year AND al.cbsa_code = vpc.cbsa_code
    WHERE al.lei != '{subject_lei}'
      AND (
          -- Volume peers exist for this CBSA: apply volume filter
          (vpc.peer_count > 0 {volume_filter})
          OR
          -- No volume peers for this CBSA: fall back to all other lenders
          (vpc.peer_count IS NULL OR vpc.peer_count = 0)
      )
      {peer_type_filter}
),
peer_hmda AS (
    SELECT f.*
    FROM filtered_hmda f
    INNER JOIN peers p
        ON f.activity_year = p.activity_year
        AND f.cbsa_code = p.cbsa_code
        AND f.lei = p.lei
),
aggregated_peer_metrics AS (
    SELECT
        activity_year,
        cbsa_code,
        state_code,
        loan_purpose_cat,
        COUNT(*) as total_loans,
        SUM(loan_amount) as total_amount,
        COUNTIF(is_lmict = 1) as lmict_loans,
        SAFE_DIVIDE(COUNTIF(is_lmict = 1), COUNT(*)) * 100 as lmict_percentage,
        COUNTIF(is_lmib = 1) as lmib_loans,
        SAFE_DIVIDE(COUNTIF(is_lmib = 1), COUNT(*)) * 100 as lmib_percentage,
        SUM(CASE WHEN is_lmib = 1 THEN loan_amount END) as lmib_amount,
        COUNTIF(is_mmct = 1) as mmct_loans,
        SAFE_DIVIDE(COUNTIF(is_mmct = 1), COUNT(*)) * 100 as mmct_percentage,
        COUNTIF(is_hispanic = 1 OR is_black = 1 OR is_asian = 1
                OR is_native_american = 1 OR is_hopi = 1) as minb_loans,
        SAFE_DIVIDE(COUNTIF(is_hispanic = 1 OR is_black = 1 OR is_asian = 1
                           OR is_native_american = 1 OR is_hopi = 1), COUNT(*)) * 100 as minb_percentage,
        -- Individual race/ethnicity counts (using total loans as denominator)
        COUNTIF(is_asian = 1) as asian_loans,
        SAFE_DIVIDE(COUNTIF(is_asian = 1), COUNT(*)) * 100 as asian_percentage,
        COUNTIF(is_black = 1) as black_loans,
        SAFE_DIVIDE(COUNTIF(is_black = 1), COUNT(*)) * 100 as black_percentage,
        COUNTIF(is_native_american = 1) as native_american_loans,
        SAFE_DIVIDE(COUNTIF(is_native_american = 1), COUNT(*)) * 100 as native_american_percentage,
        COUNTIF(is_hopi = 1) as hopi_loans,
        SAFE_DIVIDE(COUNTIF(is_hopi = 1), COUNT(*)) * 100 as hopi_percentage,
        COUNTIF(is_hispanic = 1) as hispanic_loans,
        SAFE_DIVIDE(COUNTIF(is_hispanic = 1), COUNT(*)) * 100 as hispanic_percentage
    FROM peer_hmda
    GROUP BY activity_year, cbsa_code, state_code, loan_purpose_cat
)
SELECT * FROM aggregated_peer_metrics
ORDER BY activity_year, state_code, cbsa_code, loan_purpose_cat
