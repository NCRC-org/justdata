SELECT
    s.bank_name,
    s.year,
    s.geoid5,
    c.county_state,
    s.uninumbr,
    1 as total_branches,
    MAX(s.br_lmi) as lmict,
    MAX(s.br_minority) as mmct,
    COALESCE(SUM(COALESCE(s.deposits_000s, 0) * 1000), 0) as total_deposits,
    MAX(s.address) as address,
    MAX(s.city) as city,
    MAX(s.county) as county,
    MAX(s.state) as state,
    MAX(s.state_abbrv) as state_abbrv,
    MAX(s.zip) as zip,
    MAX(s.service_type) as service_type,
    MAX(s.branch_name) as branch_name,
    MAX(s.latitude) as latitude,
    MAX(s.longitude) as longitude,
    MAX(s.rssd) as rssd,
    MAX(s.assets_000s) as assets_000s
FROM branches.sod s
LEFT JOIN geo.cbsa_to_county c
    USING(geoid5)
WHERE c.county_state = @county
    AND s.year = @year
GROUP BY 1,2,3,4,5
UNION ALL
SELECT
    s.bank_name,
    s.year,
    s.geoid5,
    c.county_state,
    s.uninumbr,
    1 as total_branches,
    MAX(s.br_lmi) as lmict,
    MAX(s.br_minority) as mmct,
    COALESCE(SUM(COALESCE(s.deposits_000s, 0) * 1000), 0) as total_deposits,
    MAX(s.address) as address,
    MAX(s.city) as city,
    MAX(s.county) as county,
    MAX(s.state) as state,
    MAX(s.state_abbrv) as state_abbrv,
    MAX(s.zip) as zip,
    MAX(s.service_type) as service_type,
    MAX(s.branch_name) as branch_name,
    MAX(s.latitude) as latitude,
    MAX(s.longitude) as longitude,
    MAX(s.rssd) as rssd,
    MAX(s.assets_000s) as assets_000s
FROM branches.sod_legacy s
LEFT JOIN geo.cbsa_to_county c
    USING(geoid5)
WHERE c.county_state = @county
    AND s.year = @year
GROUP BY 1,2,3,4,5
UNION ALL
SELECT
    s.bank_name,
    s.year,
    s.geoid5,
    c.county_state,
    s.uninumbr,
    1 as total_branches,
    MAX(s.br_lmi) as lmict,
    MAX(s.br_minority) as mmct,
    COALESCE(SUM(COALESCE(s.deposits_000s, 0) * 1000), 0) as total_deposits,
    MAX(s.address) as address,
    MAX(s.city) as city,
    MAX(s.county) as county,
    MAX(s.state) as state,
    MAX(s.state_abbrv) as state_abbrv,
    MAX(s.zip) as zip,
    MAX(s.service_type) as service_type,
    MAX(s.branch_name) as branch_name,
    MAX(s.latitude) as latitude,
    MAX(s.longitude) as longitude,
    MAX(s.rssd) as rssd,
    MAX(s.assets_000s) as assets_000s
FROM branches.sod25 s
LEFT JOIN geo.cbsa_to_county c
    USING(geoid5)
WHERE c.county_state = @county
    AND s.year = @year
GROUP BY 1,2,3,4,5
ORDER BY bank_name, county_state, year
