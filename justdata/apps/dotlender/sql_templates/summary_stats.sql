-- Top-line statistics for the data summary panel.
-- LMI tract = tract_to_msa_income_percentage < 80.
-- Majority-minority tract = tract_minority_population_percent >= 50.
-- {lei_predicate} is either "AND lei = @lei" or empty string.
SELECT
  COUNT(*) AS total_loans,
  COUNT(DISTINCT census_tract) AS tracts_with_lending,
  COUNT(DISTINCT lei) AS lender_count,
  COUNTIF(tract_to_msa_income_percentage < 80) AS loans_in_lmi_tracts,
  COUNTIF(tract_minority_population_percent >= 50) AS loans_in_majority_minority_tracts,
  SUM(loan_amount) AS total_loan_amount
FROM `{table}`
WHERE
  activity_year BETWEEN @year_start AND @year_end
  AND {geography_predicate}
  AND {loan_scope_predicates}
  {lei_predicate}
