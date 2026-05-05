            WITH
            -- Get CBSA codes for counties (exclude rural areas with code 99999)
            cbsa_crosswalk AS (
                SELECT DISTINCT
                    CAST(geoid5 AS STRING) as geoid5,
                    CAST(cbsa_code AS STRING) as cbsa_code,
                    CBSA as cbsa_name,
                    State as state_name
                FROM `{PROJECT_ID}.shared.cbsa_to_county`
                WHERE CAST(cbsa_code AS STRING) != '99999'
            ),
            
            -- Get bank's loans by county
            -- HMDA county_code is already GEOID5 (5-digit state+county FIPS code)
            bank_loans_by_county AS (
                SELECT 
                    LPAD(CAST(h.county_code AS STRING), 5, '0') as geoid5,
                    COUNT(*) as loan_count
                FROM `{PROJECT_ID}.shared.de_hmda` h
                WHERE CAST(h.activity_year AS STRING) = '{year}'
                    AND CAST(h.lei AS STRING) = '{lei}'
                    AND h.county_code IS NOT NULL
                    AND h.action_taken = '1'  -- Originations only
                GROUP BY geoid5
            ),
            
            -- Calculate total national loans
            total_national_loans AS (
                SELECT SUM(loan_count) as total_loans
                FROM bank_loans_by_county
            ),
            
            -- Aggregate loans by CBSA
            bank_loans_by_cbsa AS (
                SELECT 
                    CASE 
                        WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                        THEN CONCAT('NON-METRO-', c.state_name)
                        ELSE CAST(c.cbsa_code AS STRING)
                    END as cbsa_code,
                    CASE 
                        WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                        THEN CONCAT(c.state_name, ' Non-Metro Area')
                        ELSE COALESCE(c.cbsa_name, 'Non-Metro Area')
                    END as cbsa_name,
                    SUM(bl.loan_count) as cbsa_loans,
                    MAX(c.state_name) as state_name
                FROM bank_loans_by_county bl
                LEFT JOIN cbsa_crosswalk c
                    ON bl.geoid5 = c.geoid5
                GROUP BY 
                    CASE 
                        WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                        THEN CONCAT('NON-METRO-', c.state_name)
                        ELSE CAST(c.cbsa_code AS STRING)
                    END,
                    CASE 
                        WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                        THEN CONCAT(c.state_name, ' Non-Metro Area')
                        ELSE COALESCE(c.cbsa_name, 'Non-Metro Area')
                    END,
                    c.state_name
                HAVING SUM(bl.loan_count) > 0
            )
            
            SELECT 
                blc.cbsa_code,
                blc.cbsa_name,
                blc.cbsa_loans,
                SAFE_DIVIDE(blc.cbsa_loans, tnl.total_loans) * 100 as national_loan_share_pct,
                tnl.total_loans as total_national_loans,
                blc.state_name
            FROM bank_loans_by_cbsa blc
            CROSS JOIN total_national_loans tnl
            WHERE tnl.total_loans > 0
            ORDER BY national_loan_share_pct DESC, blc.cbsa_code
