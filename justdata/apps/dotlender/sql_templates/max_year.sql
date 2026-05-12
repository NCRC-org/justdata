-- Maximum activity_year currently loaded in de_hmda.
-- Used to resolve the default year range (last 3 years) at runtime.
SELECT MAX(activity_year) AS max_year
FROM `{table}`
