-- Tract-level demographic data for the choropleth layer.
-- One row per census tract in the requested geography.
-- Year range and loan-scope predicates flow in as BigQuery parameters
-- (@year_start, @year_end) and as a pre-built {loan_scope_predicates}
-- string composed by Python from the validated filter dict.
--
-- Geography is one of:
--   county: geoid5 = @county_fips     (5-digit FIPS)
--   state:  LEFT(geoid5, 2) = @state_fips
--
-- Housing-unit denominator (tract_one_to_four_family_homes) is not present
-- in de_hmda, so housing_units is NULL. Callers fall back to a constant
-- scale in Python.
SELECT
  census_tract,
  ANY_VALUE(tract_minority_population_percent) AS minority_pct,
  ANY_VALUE(tract_to_msa_income_percentage) AS tract_income_pct,
  ANY_VALUE(ffiec_msa_md_median_family_income) AS msa_median_income,
  COUNT(*) AS loan_count,
  CAST(NULL AS INT64) AS housing_units
FROM `{table}`
WHERE
  activity_year BETWEEN @year_start AND @year_end
  AND {geography_predicate}
  AND {loan_scope_predicates}
GROUP BY census_tract
