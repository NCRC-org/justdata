SELECT DISTINCT
    s.bank_name,
    s.year,
    s.geoid5,
    c.county_state,
    SUM(1) as total_branches,
    SUM(s.br_lmi) as lmict,
    SUM(s.br_minority) as mmct,
    SUM(s.deposits_000s * 1000) as total_deposits
FROM branches.sod s
LEFT JOIN geo.cbsa_to_county c
    USING(geoid5)
WHERE c.county_state = @county
    AND s.year = @year
GROUP BY 1,2,3,4
UNION ALL
SELECT DISTINCT
    s.bank_name,
    s.year,
    s.geoid5,
    c.county_state,
    SUM(1) as total_branches,
    SUM(s.br_lmi) as lmict,
    SUM(s.br_minority) as mmct,
    SUM(s.deposits_000s * 1000) as total_deposits
FROM branches.sod_legacy s
LEFT JOIN geo.cbsa_to_county c
    USING(geoid5)
WHERE c.county_state = @county
    AND s.year = @year
GROUP BY 1,2,3,4
ORDER BY bank_name, county_state, year