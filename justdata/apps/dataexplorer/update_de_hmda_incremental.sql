-- ============================================================================
-- Incremental Update for justdata.de_hmda
-- ============================================================================
-- This query automatically adds new years to de_hmda when they become available
-- in the source HMDA table.
--
-- Usage:
--   1. Set up as BigQuery Scheduled Query (monthly recommended)
--   2. Destination: justdata.de_hmda
--   3. Write preference: WRITE_APPEND
--   4. This will only process years that don't exist in de_hmda yet
-- ============================================================================

INSERT INTO `hdma1-242116.justdata.de_hmda`
SELECT
  -- Identifiers
  h.lei,
  CAST(h.activity_year AS INT64) as activity_year,
  h.county_code,
  c.county_state,
  -- geoid5: Normalize Connecticut data to planning region codes
  COALESCE(
    CASE 
      WHEN CAST(h.county_code AS STRING) LIKE '09%' 
           AND CAST(h.county_code AS STRING) NOT LIKE '091%'
           AND h.census_tract IS NOT NULL
           AND ct_tract.geoid IS NOT NULL THEN
        SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
      ELSE NULL
    END,
    CAST(h.county_code AS STRING)
  ) as geoid5,
  h.census_tract,
  h.census_tract as tract_code,
  
  -- Lender information (pre-joined)
  l.respondent_name as lender_name,
  l.type_name as lender_type,
  
  -- Loan characteristics
  h.loan_purpose,
  h.loan_type,
  h.action_taken,
  h.occupancy_type,
  h.total_units,
  h.construction_method,
  h.reverse_mortgage,
  
  -- Loan amounts and values
  h.loan_amount,
  h.property_value,
  h.interest_rate,
  h.total_loan_costs,
  h.origination_charges,
  h.income,
  
  -- Tract characteristics
  h.tract_minority_population_percent,
  h.tract_to_msa_income_percentage,
  h.ffiec_msa_md_median_family_income,
  
  -- Pre-computed race/ethnicity flags
  -- Hispanic: Check if ANY ethnicity field indicates Hispanic
  (
    h.applicant_ethnicity_1 IN ('1','11','12','13','14')
    OR h.applicant_ethnicity_2 IN ('1','11','12','13','14')
    OR h.applicant_ethnicity_3 IN ('1','11','12','13','14')
    OR h.applicant_ethnicity_4 IN ('1','11','12','13','14')
    OR h.applicant_ethnicity_5 IN ('1','11','12','13','14')
  ) as is_hispanic,
  
  -- Black: First valid race code is '3', AND NOT Hispanic, AND NOT multi-racial
  (
    (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
    AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
    AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
    AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
    AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
    AND COALESCE(
      CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
           THEN h.applicant_race_1 ELSE NULL END,
      CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
           THEN h.applicant_race_2 ELSE NULL END,
      CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
           THEN h.applicant_race_3 ELSE NULL END,
      CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
           THEN h.applicant_race_4 ELSE NULL END,
      CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
           THEN h.applicant_race_5 ELSE NULL END
    ) = '3'
    AND (
      SELECT COUNT(DISTINCT main_cat)
      FROM UNNEST([
        CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_1 = '1' THEN '1'
                       WHEN h.applicant_race_1 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_1 = '3' THEN '3'
                       WHEN h.applicant_race_1 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_1 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_2 = '1' THEN '1'
                       WHEN h.applicant_race_2 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_2 = '3' THEN '3'
                       WHEN h.applicant_race_2 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_2 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_3 = '1' THEN '1'
                       WHEN h.applicant_race_3 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_3 = '3' THEN '3'
                       WHEN h.applicant_race_3 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_3 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_4 = '1' THEN '1'
                       WHEN h.applicant_race_4 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_4 = '3' THEN '3'
                       WHEN h.applicant_race_4 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_4 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_5 = '1' THEN '1'
                       WHEN h.applicant_race_5 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_5 = '3' THEN '3'
                       WHEN h.applicant_race_5 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_5 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END
      ]) AS main_cat
      WHERE main_cat IS NOT NULL
    ) < 2
  ) as is_black,
  
  -- Asian: First valid race code is '2' or '21'-'27', AND NOT Hispanic, AND NOT multi-racial
  (
    (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
    AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
    AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
    AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
    AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
    AND COALESCE(
      CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
           THEN h.applicant_race_1 ELSE NULL END,
      CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
           THEN h.applicant_race_2 ELSE NULL END,
      CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
           THEN h.applicant_race_3 ELSE NULL END,
      CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
           THEN h.applicant_race_4 ELSE NULL END,
      CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
           THEN h.applicant_race_5 ELSE NULL END
    ) IN ('2','21','22','23','24','25','26','27')
    AND (
      SELECT COUNT(DISTINCT main_cat)
      FROM UNNEST([
        CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_1 = '1' THEN '1'
                       WHEN h.applicant_race_1 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_1 = '3' THEN '3'
                       WHEN h.applicant_race_1 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_1 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_2 = '1' THEN '1'
                       WHEN h.applicant_race_2 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_2 = '3' THEN '3'
                       WHEN h.applicant_race_2 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_2 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_3 = '1' THEN '1'
                       WHEN h.applicant_race_3 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_3 = '3' THEN '3'
                       WHEN h.applicant_race_3 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_3 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_4 = '1' THEN '1'
                       WHEN h.applicant_race_4 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_4 = '3' THEN '3'
                       WHEN h.applicant_race_4 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_4 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_5 = '1' THEN '1'
                       WHEN h.applicant_race_5 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_5 = '3' THEN '3'
                       WHEN h.applicant_race_5 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_5 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END
      ]) AS main_cat
      WHERE main_cat IS NOT NULL
    ) < 2
  ) as is_asian,
  
  -- White: First valid race code is '5', AND NOT Hispanic, AND NOT multi-racial
  (
    (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
    AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
    AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
    AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
    AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
    AND COALESCE(
      CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
           THEN h.applicant_race_1 ELSE NULL END,
      CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
           THEN h.applicant_race_2 ELSE NULL END,
      CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
           THEN h.applicant_race_3 ELSE NULL END,
      CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
           THEN h.applicant_race_4 ELSE NULL END,
      CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
           THEN h.applicant_race_5 ELSE NULL END
    ) = '5'
    AND (
      SELECT COUNT(DISTINCT main_cat)
      FROM UNNEST([
        CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_1 = '1' THEN '1'
                       WHEN h.applicant_race_1 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_1 = '3' THEN '3'
                       WHEN h.applicant_race_1 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_1 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_2 = '1' THEN '1'
                       WHEN h.applicant_race_2 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_2 = '3' THEN '3'
                       WHEN h.applicant_race_2 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_2 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_3 = '1' THEN '1'
                       WHEN h.applicant_race_3 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_3 = '3' THEN '3'
                       WHEN h.applicant_race_3 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_3 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_4 = '1' THEN '1'
                       WHEN h.applicant_race_4 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_4 = '3' THEN '3'
                       WHEN h.applicant_race_4 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_4 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_5 = '1' THEN '1'
                       WHEN h.applicant_race_5 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_5 = '3' THEN '3'
                       WHEN h.applicant_race_5 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_5 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END
      ]) AS main_cat
      WHERE main_cat IS NOT NULL
    ) < 2
  ) as is_white,
  
  -- Native American: First valid race code is '1', AND NOT Hispanic, AND NOT multi-racial
  (
    (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
    AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
    AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
    AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
    AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
    AND COALESCE(
      CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
           THEN h.applicant_race_1 ELSE NULL END,
      CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
           THEN h.applicant_race_2 ELSE NULL END,
      CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
           THEN h.applicant_race_3 ELSE NULL END,
      CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
           THEN h.applicant_race_4 ELSE NULL END,
      CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
           THEN h.applicant_race_5 ELSE NULL END
    ) = '1'
    AND (
      SELECT COUNT(DISTINCT main_cat)
      FROM UNNEST([
        CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_1 = '1' THEN '1'
                       WHEN h.applicant_race_1 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_1 = '3' THEN '3'
                       WHEN h.applicant_race_1 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_1 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_2 = '1' THEN '1'
                       WHEN h.applicant_race_2 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_2 = '3' THEN '3'
                       WHEN h.applicant_race_2 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_2 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_3 = '1' THEN '1'
                       WHEN h.applicant_race_3 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_3 = '3' THEN '3'
                       WHEN h.applicant_race_3 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_3 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_4 = '1' THEN '1'
                       WHEN h.applicant_race_4 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_4 = '3' THEN '3'
                       WHEN h.applicant_race_4 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_4 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_5 = '1' THEN '1'
                       WHEN h.applicant_race_5 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_5 = '3' THEN '3'
                       WHEN h.applicant_race_5 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_5 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END
      ]) AS main_cat
      WHERE main_cat IS NOT NULL
    ) < 2
  ) as is_native_american,
  
  -- HoPI: First valid race code is '4' or '41'-'44', AND NOT Hispanic, AND NOT multi-racial
  (
    (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
    AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
    AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
    AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
    AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
    AND COALESCE(
      CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
           THEN h.applicant_race_1 ELSE NULL END,
      CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
           THEN h.applicant_race_2 ELSE NULL END,
      CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
           THEN h.applicant_race_3 ELSE NULL END,
      CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
           THEN h.applicant_race_4 ELSE NULL END,
      CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
           THEN h.applicant_race_5 ELSE NULL END
    ) IN ('4','41','42','43','44')
    AND (
      SELECT COUNT(DISTINCT main_cat)
      FROM UNNEST([
        CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_1 = '1' THEN '1'
                       WHEN h.applicant_race_1 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_1 = '3' THEN '3'
                       WHEN h.applicant_race_1 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_1 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_2 = '1' THEN '1'
                       WHEN h.applicant_race_2 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_2 = '3' THEN '3'
                       WHEN h.applicant_race_2 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_2 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_3 = '1' THEN '1'
                       WHEN h.applicant_race_3 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_3 = '3' THEN '3'
                       WHEN h.applicant_race_3 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_3 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_4 = '1' THEN '1'
                       WHEN h.applicant_race_4 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_4 = '3' THEN '3'
                       WHEN h.applicant_race_4 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_4 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_5 = '1' THEN '1'
                       WHEN h.applicant_race_5 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_5 = '3' THEN '3'
                       WHEN h.applicant_race_5 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_5 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END
      ]) AS main_cat
      WHERE main_cat IS NOT NULL
    ) < 2
  ) as is_hopi,
  
  -- Multi-racial: Non-Hispanic with 2+ DISTINCT main race categories
  (
    (h.applicant_ethnicity_1 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_1 IS NULL)
    AND (h.applicant_ethnicity_2 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_2 IS NULL)
    AND (h.applicant_ethnicity_3 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_3 IS NULL)
    AND (h.applicant_ethnicity_4 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_4 IS NULL)
    AND (h.applicant_ethnicity_5 NOT IN ('1','11','12','13','14') OR h.applicant_ethnicity_5 IS NULL)
    AND (
      SELECT COUNT(DISTINCT main_cat)
      FROM UNNEST([
        CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_1 = '1' THEN '1'
                       WHEN h.applicant_race_1 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_1 = '3' THEN '3'
                       WHEN h.applicant_race_1 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_1 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_2 = '1' THEN '1'
                       WHEN h.applicant_race_2 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_2 = '3' THEN '3'
                       WHEN h.applicant_race_2 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_2 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_3 = '1' THEN '1'
                       WHEN h.applicant_race_3 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_3 = '3' THEN '3'
                       WHEN h.applicant_race_3 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_3 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_4 = '1' THEN '1'
                       WHEN h.applicant_race_4 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_4 = '3' THEN '3'
                       WHEN h.applicant_race_4 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_4 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END,
        CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
             THEN CASE WHEN h.applicant_race_5 = '1' THEN '1'
                       WHEN h.applicant_race_5 IN ('2','21','22','23','24','25','26','27') THEN '2'
                       WHEN h.applicant_race_5 = '3' THEN '3'
                       WHEN h.applicant_race_5 IN ('4','41','42','43','44') THEN '4'
                       WHEN h.applicant_race_5 = '5' THEN '5'
                       ELSE NULL END
             ELSE NULL END
      ]) AS main_cat
      WHERE main_cat IS NOT NULL
    ) >= 2
  ) as is_multi_racial,
  
  -- Has demographic data: Either Hispanic ethnicity OR explicit race selection
  (
    (h.applicant_ethnicity_1 IN ('1','11','12','13','14')
     OR h.applicant_ethnicity_2 IN ('1','11','12','13','14')
     OR h.applicant_ethnicity_3 IN ('1','11','12','13','14')
     OR h.applicant_ethnicity_4 IN ('1','11','12','13','14')
     OR h.applicant_ethnicity_5 IN ('1','11','12','13','14'))
    OR COALESCE(
      CASE WHEN h.applicant_race_1 IS NOT NULL AND h.applicant_race_1 != '' AND h.applicant_race_1 NOT IN ('6','7','8') 
           THEN h.applicant_race_1 ELSE NULL END,
      CASE WHEN h.applicant_race_2 IS NOT NULL AND h.applicant_race_2 != '' AND h.applicant_race_2 NOT IN ('6','7','8') 
           THEN h.applicant_race_2 ELSE NULL END,
      CASE WHEN h.applicant_race_3 IS NOT NULL AND h.applicant_race_3 != '' AND h.applicant_race_3 NOT IN ('6','7','8') 
           THEN h.applicant_race_3 ELSE NULL END,
      CASE WHEN h.applicant_race_4 IS NOT NULL AND h.applicant_race_4 != '' AND h.applicant_race_4 NOT IN ('6','7','8') 
           THEN h.applicant_race_4 ELSE NULL END,
      CASE WHEN h.applicant_race_5 IS NOT NULL AND h.applicant_race_5 != '' AND h.applicant_race_5 NOT IN ('6','7','8') 
           THEN h.applicant_race_5 ELSE NULL END
    ) IS NOT NULL
  ) as has_demographic_data,
  
  -- Pre-computed income category flags
  -- LMI Borrower (<= 80% of MSA median)
  (
    h.income IS NOT NULL
    AND h.ffiec_msa_md_median_family_income IS NOT NULL
    AND h.ffiec_msa_md_median_family_income > 0
    AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
  ) as is_lmib,
  
  -- Low Income Borrower (<= 50% of MSA median)
  (
    h.income IS NOT NULL
    AND h.ffiec_msa_md_median_family_income IS NOT NULL
    AND h.ffiec_msa_md_median_family_income > 0
    AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 50.0
  ) as is_low_income_borrower,
  
  -- Moderate Income Borrower (> 50% and <= 80% of MSA median)
  (
    h.income IS NOT NULL
    AND h.ffiec_msa_md_median_family_income IS NOT NULL
    AND h.ffiec_msa_md_median_family_income > 0
    AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 > 50.0
    AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
  ) as is_moderate_income_borrower,
  
  -- Middle Income Borrower (> 80% and <= 120% of MSA median)
  (
    h.income IS NOT NULL
    AND h.ffiec_msa_md_median_family_income IS NOT NULL
    AND h.ffiec_msa_md_median_family_income > 0
    AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 > 80.0
    AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 120.0
  ) as is_middle_income_borrower,
  
  -- Upper Income Borrower (> 120% of MSA median)
  (
    h.income IS NOT NULL
    AND h.ffiec_msa_md_median_family_income IS NOT NULL
    AND h.ffiec_msa_md_median_family_income > 0
    AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 > 120.0
  ) as is_upper_income_borrower,
  
  -- Pre-computed tract income category flags
  -- LMICT (<= 80% of MSA median)
  (
    h.tract_to_msa_income_percentage IS NOT NULL
    AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 80
  ) as is_lmict,
  
  -- Low Income Tract (<= 50% of MSA median)
  (
    h.tract_to_msa_income_percentage IS NOT NULL
    AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 50
  ) as is_low_income_tract,
  
  -- Moderate Income Tract (> 50% and <= 80% of MSA median)
  (
    h.tract_to_msa_income_percentage IS NOT NULL
    AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) > 50
    AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 80
  ) as is_moderate_income_tract,
  
  -- Middle Income Tract (> 80% and <= 120% of MSA median)
  (
    h.tract_to_msa_income_percentage IS NOT NULL
    AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) > 80
    AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) <= 120
  ) as is_middle_income_tract,
  
  -- Upper Income Tract (> 120% of MSA median)
  (
    h.tract_to_msa_income_percentage IS NOT NULL
    AND CAST(h.tract_to_msa_income_percentage AS FLOAT64) > 120
  ) as is_upper_income_tract,
  
  -- Pre-computed tract minority flag
  -- MMCT (>= 50% minority)
  (
    h.tract_minority_population_percent IS NOT NULL
    AND CAST(h.tract_minority_population_percent AS FLOAT64) >= 50
  ) as is_mmct

FROM `hdma1-242116.hmda.hmda` h
-- For 2022-2023 Connecticut data, join to geo.census to get planning region from tract
LEFT JOIN `hdma1-242116.geo.census` ct_tract
  ON CAST(h.county_code AS STRING) LIKE '09%'
  AND CAST(h.county_code AS STRING) NOT LIKE '091%'  -- Legacy county codes only (2022-2023)
  AND h.census_tract IS NOT NULL
  -- Match on tract portion (last 6 digits) - tract numbers are stable
  AND SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 6, 6) = SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 6, 6)
-- Join to geo.cbsa_to_county for county_state
LEFT JOIN `hdma1-242116.geo.cbsa_to_county` c
  ON COALESCE(
    -- For 2022-2023: Use planning region from tract (extracted above)
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
-- Join to lenders18 for lender name and type
LEFT JOIN `hdma1-242116.hmda.lenders18` l
  ON h.lei = l.lei
WHERE CAST(h.activity_year AS INT64) > (
  -- Only process years that don't exist in de_hmda yet
  SELECT COALESCE(MAX(activity_year), 2017)
  FROM `hdma1-242116.justdata.de_hmda`
)
-- This ensures we only add new years, not duplicate existing ones

