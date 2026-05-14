-- Per-tract race share percentages for a given geography.
-- Source: justdata-ncrc.shared.census (2025 FFIEC vintage). Joined back to
-- the same geo predicate the other DotLender templates use; the CTE
-- aliases the 11-char `geoid` to a derived `geoid5` so unqualified
-- `geoid5` in the injected predicate resolves correctly here too.
--
-- Parameters (BigQuery):
--   @race_field STRING — one of: black, hispanic, black_hispanic, asian,
--                        ai_an, nh_opi, white
--   (plus the geography params built by _build_geography_from_dict)
--
-- Predicates (Python format-string):
--   {geo_predicate} — already validated, references geoid5
--
-- Filters tracts with total_persons < 10 to suppress noise from
-- unpopulated / special-purpose tracts (industrial parcels, water-only
-- polygons, etc.).
--
-- Returns: geoid STRING (11-char), pct FLOAT64 (0-100 scale matching
-- the existing minority_population convention).

WITH c AS (
  SELECT
    geoid,
    LEFT(geoid, 5) AS geoid5,
    total_persons,
    total_black,
    total_hispanic,
    total_asian,
    total_ai_an,
    total_nh_opi,
    total_white
  FROM `justdata-ncrc.shared.census`
  WHERE year = '2025'
    AND total_persons >= 10
)
SELECT
  c.geoid,
  CASE @race_field
    WHEN 'black'
      THEN ROUND(SAFE_DIVIDE(c.total_black, c.total_persons) * 100, 2)
    WHEN 'hispanic'
      THEN ROUND(SAFE_DIVIDE(c.total_hispanic, c.total_persons) * 100, 2)
    WHEN 'black_hispanic'
      THEN ROUND(SAFE_DIVIDE(c.total_black + c.total_hispanic,
                             c.total_persons) * 100, 2)
    WHEN 'asian'
      THEN ROUND(SAFE_DIVIDE(c.total_asian, c.total_persons) * 100, 2)
    WHEN 'ai_an'
      THEN ROUND(SAFE_DIVIDE(c.total_ai_an, c.total_persons) * 100, 2)
    WHEN 'nh_opi'
      THEN ROUND(SAFE_DIVIDE(c.total_nh_opi, c.total_persons) * 100, 2)
    WHEN 'white'
      THEN ROUND(SAFE_DIVIDE(c.total_white, c.total_persons) * 100, 2)
    ELSE NULL
  END AS pct
FROM c
WHERE {geo_predicate}
ORDER BY c.geoid
