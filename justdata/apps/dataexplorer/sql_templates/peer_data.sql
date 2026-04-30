        SELECT 
            CAST(c.cbsa_code AS STRING) as cbsa_code,
            c.CBSA as cbsa_name,
            h.activity_year as year,
            MAX(l.respondent_name) as lender_name,
            h.lei,
            COUNT(*) as applications
        FROM `{PROJECT_ID}.shared.de_hmda` h
        -- For 2022-2023 Connecticut data, join to shared.census to get planning region from tract
        LEFT JOIN `{PROJECT_ID}.shared.census` ct_tract
            ON CAST(h.county_code AS STRING) LIKE '09%'
            AND CAST(h.county_code AS STRING) NOT LIKE '091%'
            AND h.census_tract IS NOT NULL
            AND SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 6, 6) = SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 6, 6)
        LEFT JOIN `{PROJECT_ID}.shared.cbsa_to_county` c
            ON COALESCE(
                -- For 2022-2023: Use planning region from tract
                CASE 
                    WHEN CAST(h.county_code AS STRING) LIKE '09%' 
                         AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                         AND ct_tract.geoid IS NOT NULL THEN
                        SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
                    ELSE NULL
                END,
                -- For 2024: Use planning region code directly from county_code
                CAST(h.county_code AS STRING)
            ) = CAST(c.geoid5 AS STRING)
        LEFT JOIN `{PROJECT_ID}.lendsight.lenders18` l
            ON h.lei = l.lei
        WHERE CAST(c.geoid5 AS STRING) IN ('{counties_list}')
          AND h.lei IN ('{peer_leis_str}')
          AND h.activity_year IN ({years_int_str})
          AND {action_taken_clause}
          AND {occupancy_clause}
          AND {total_units_clause}
          AND {construction_clause}
          AND {loan_type_clause}
          AND {reverse_clause}
          AND c.cbsa_code IS NOT NULL
          AND c.CBSA IS NOT NULL
        GROUP BY cbsa_code, cbsa_name, year, h.lei
        ORDER BY cbsa_name, year, lender_name
