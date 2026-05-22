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
--
-- Centroids: prefer real tract centroid from shared.tract_centroids (Census
-- 2020 Gazetteer, 85,395 rows). Fall back to the enclosing county centroid
-- via shared.county_centroids when the tract GEOID isn't matched (rare —
-- mostly Connecticut planning-region edge cases).
SELECT
  h.census_tract,
  {derived_race_expr} AS derived_race,
  COUNT(*) AS loan_count,
  CAST(NULL AS INT64) AS housing_units,
  COALESCE(ANY_VALUE(tc.intptlat), ANY_VALUE(cc.latitude))  AS centroid_lat,
  COALESCE(ANY_VALUE(tc.intptlon), ANY_VALUE(cc.longitude)) AS centroid_lng
FROM `{table}` AS h
LEFT JOIN `justdata-ncrc.shared.tract_centroids` AS tc
  ON tc.geoid = h.census_tract
LEFT JOIN `justdata-ncrc.shared.county_centroids` AS cc
  ON LPAD(CAST(cc.county_fips AS STRING), 5, '0') = h.geoid5
WHERE
  h.activity_year BETWEEN @year_start AND @year_end
  AND {geography_predicate}
  -- Drop the ~10M rows where census_tract doesn't match geoid5 (8.5M of
  -- those are Connecticut planning-region tracts that ended up under
  -- non-CT geoid5 values via the de_hmda build SQL, plus ~1.1M NULL and
  -- ~225K literal 'NA' tracts). These rows can't be visualized; the
  -- filter also keeps dots and tooltips from being placed in the wrong
  -- geography.
  AND LEFT(h.census_tract, 5) = h.geoid5
  AND {loan_scope_predicates}
  {lei_predicate}
GROUP BY h.census_tract, derived_race
ORDER BY h.census_tract, derived_race
