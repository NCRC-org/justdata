-- Tract+race aggregation for the dot-density layer.
-- The {derived_race_expr} placeholder is filled with NCRC's standard
-- race/ethnicity hierarchy SQL snippet from queries.DERIVED_RACE_SQL.
-- Final dot_count is computed in Python after this query returns.
--
-- Geography is one of:
--   county: geoid5 = @county_fips     (5-digit FIPS)
--   state:  LEFT(geoid5, 2) = @state_fips
--
-- Optional {lei_predicate} is either "AND lei = @lei" or empty string.
-- Housing-unit denominator is unavailable in de_hmda — housing_units is NULL.
SELECT
  census_tract,
  {derived_race_expr} AS derived_race,
  COUNT(*) AS loan_count,
  CAST(NULL AS INT64) AS housing_units
FROM `{table}`
WHERE
  activity_year BETWEEN @year_start AND @year_end
  AND {geography_predicate}
  AND {loan_scope_predicates}
  {lei_predicate}
GROUP BY census_tract, derived_race
ORDER BY census_tract, derived_race
