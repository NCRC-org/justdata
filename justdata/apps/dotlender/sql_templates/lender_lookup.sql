-- Typeahead query for lender name search.
-- Returns lei, lender_name (aliased respondent_name for API contract), and loan_count.
-- Params: @search_term (STRING), @year_start (INT64), @year_end (INT64)
-- The @search_term value already includes the literal '%' prefix/suffix
-- (added by the Python caller in lender_search), so the LIKE pattern works
-- as a substring match.
SELECT
  lei,
  lender_name AS respondent_name,
  COUNT(*) AS loan_count
FROM `{table}`
WHERE
  activity_year BETWEEN @year_start AND @year_end
  AND LOWER(lender_name) LIKE LOWER(@search_term)
  AND action_taken = '1'
GROUP BY lei, lender_name
ORDER BY loan_count DESC
LIMIT 20
