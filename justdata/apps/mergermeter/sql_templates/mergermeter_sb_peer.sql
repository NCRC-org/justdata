-- CBSA crosswalk to get CBSA codes and names from GEOID5 (counties in assessment areas)
WITH cbsa_crosswalk AS (
    SELECT DISTINCT
        CAST(geoid5 AS STRING) as geoid5,
        CAST(cbsa_code AS STRING) as cbsa_code,
        CBSA as cbsa_name,
        State as state_name
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
        d.respondent_id as sb_resid,
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
        AND c.cbsa_code IS NOT NULL  -- Only include counties that have a CBSA mapping (in assessment areas)
),
subject_sb_volume AS (
    SELECT
        year,
        cbsa_code,
        SUM(sb_loans_count) as subject_sb_vol
    FROM filtered_sb_data
    WHERE sb_resid IN ('{id_list}')
    GROUP BY year, cbsa_code
),
all_lenders_sb_volume AS (
    SELECT
        year,
        cbsa_code,
        sb_resid,
        SUM(sb_loans_count) as lender_sb_vol
    FROM filtered_sb_data
    GROUP BY year, cbsa_code, sb_resid
),
peers AS (
    SELECT DISTINCT
        al.year,
        al.cbsa_code,
        al.sb_resid
    FROM all_lenders_sb_volume al
    INNER JOIN subject_sb_volume sv
        ON al.year = sv.year
        AND al.cbsa_code = sv.cbsa_code
    LEFT JOIN (
        -- Count volume-matched peers per CBSA/year
        SELECT al2.year, al2.cbsa_code, COUNT(DISTINCT al2.sb_resid) as peer_count
        FROM all_lenders_sb_volume al2
        INNER JOIN subject_sb_volume sv2
            ON al2.year = sv2.year
            AND al2.cbsa_code = sv2.cbsa_code
        WHERE al2.sb_resid NOT IN ('{id_list}')
            AND al2.lender_sb_vol >= sv2.subject_sb_vol * 0.5
            AND al2.lender_sb_vol <= sv2.subject_sb_vol * 2.0
        GROUP BY al2.year, al2.cbsa_code
    ) vpc ON al.year = vpc.year AND al.cbsa_code = vpc.cbsa_code
    WHERE al.sb_resid NOT IN ('{id_list}')
      AND (
          -- Volume peers exist for this CBSA: apply volume filter
          (vpc.peer_count > 0 AND al.lender_sb_vol >= sv.subject_sb_vol * 0.5 AND al.lender_sb_vol <= sv.subject_sb_vol * 2.0)
          OR
          -- No volume peers for this CBSA: fall back to all other lenders
          (vpc.peer_count IS NULL OR vpc.peer_count = 0)
      )
),
peer_sb AS (
    SELECT f.*
    FROM filtered_sb_data f
    INNER JOIN peers p
        ON f.year = p.year
        AND f.cbsa_code = p.cbsa_code
        AND f.sb_resid = p.sb_resid
),
aggregated_peer_sb_metrics AS (
    SELECT
        year,
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
    FROM peer_sb
    GROUP BY year, cbsa_code
)
SELECT * FROM aggregated_peer_sb_metrics
ORDER BY year, cbsa_code
