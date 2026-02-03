/**
 * ElectWatch Sponsor Helper Functions
 * Version: 1.0.0
 * Created: 2026-02-02
 *
 * This file contains verified company name mappings and helper functions
 * for rendering sponsor logos using Google Favicons API.
 *
 * See ELECTWATCH_COMPLETE_RECONSTRUCTION.md section 3.5 for full documentation.
 */

/**
 * DOMAIN_MAP: Maps company names to domains for Google Favicons API
 * This is the authoritative list - verified from FEC data analysis
 */
const DOMAIN_MAP = {
    // ===== MAJOR BANKS =====
    'CAPITAL ONE': 'capitalone.com',
    'JPMORGAN': 'jpmorganchase.com',
    'JPMORGAN CHASE': 'jpmorganchase.com',
    'JP MORGAN': 'jpmorganchase.com',
    'J.P. MORGAN': 'jpmorganchase.com',
    'J P MORGAN': 'jpmorganchase.com',
    'CHASE': 'jpmorganchase.com',
    'CHASE BANK': 'jpmorganchase.com',
    'WASHINGTON MUTUAL': 'jpmorganchase.com',  // Acquired by JPM
    'BANK OF AMERICA': 'bankofamerica.com',
    'BOFA': 'bankofamerica.com',
    'BOFA SECURITIES': 'bankofamerica.com',
    'MERRILL': 'bankofamerica.com',
    'MERRILL LYNCH': 'bankofamerica.com',
    'MERRILL BANK OF AMERICA': 'bankofamerica.com',
    'WELLS FARGO': 'wellsfargo.com',
    'WELLS FARGO ADVISORS': 'wellsfargo.com',
    'WELLS FARGO SECURITIES': 'wellsfargo.com',
    'AG EDWARDS': 'wellsfargo.com',  // Acquired by Wells Fargo
    'WACHOVIA': 'wellsfargo.com',    // Acquired by Wells Fargo
    'CITIGROUP': 'citi.com',
    'CITI': 'citi.com',
    'CITIBANK': 'citi.com',
    'TRAVELERS': 'travelers.com',     // Spun off from Citi, now independent
    'TRAVELERS INSURANCE': 'travelers.com',
    'PRIMERICA': 'primerica.com',     // Spun off from Citi
    'SMITH BARNEY': 'morganstanley.com',  // Now part of Morgan Stanley
    'GOLDMAN SACHS': 'goldmansachs.com',
    'GOLDMAN SACHS GROUP': 'goldmansachs.com',
    'GOLDMAN': 'goldmansachs.com',
    'MORGAN STANLEY': 'morganstanley.com',
    'MORGAN STANLEY SMITH BARNEY': 'morganstanley.com',
    'PNC': 'pnc.com',
    'PNC FINANCIAL': 'pnc.com',
    'NATIONAL CITY': 'pnc.com',       // Acquired by PNC
    'NATIONAL CITY BANK': 'pnc.com',
    'TRUIST': 'truist.com',
    'TRUIST FINANCIAL': 'truist.com',
    'BB&T': 'truist.com',             // Merged to form Truist
    'SUNTRUST': 'truist.com',         // Merged to form Truist
    'US BANK': 'usbank.com',
    'US BANCORP': 'usbank.com',
    'FIFTH THIRD': '53.com',
    'FIFTH THIRD BANK': '53.com',
    'REGIONS': 'regions.com',
    'REGIONS FINANCIAL': 'regions.com',
    'REGIONS BANK': 'regions.com',
    'CITIZENS': 'citizensbank.com',
    'CITIZENS FINANCIAL': 'citizensbank.com',
    'CITIZENS BANK': 'citizensbank.com',
    'HUNTINGTON': 'huntington.com',
    'HUNTINGTON BANK': 'huntington.com',
    'ZIONS': 'zionsbancorporation.com',
    'ZIONS BANCORPORATION': 'zionsbancorporation.com',
    'FIRST HORIZON': 'firsthorizon.com',
    'FIRST HORIZON CORPORATION': 'firsthorizon.com',
    'CADENCE BANK': 'cadencebank.com',
    'M&T BANK': 'mtb.com',
    'ARVEST': 'arvest.com',
    'ARVEST BANK': 'arvest.com',
    'LIVE OAK': 'liveoakbank.com',
    'LIVE OAK BANK': 'liveoakbank.com',
    'BANK OF HAWAII': 'boh.com',
    'INTERNATIONAL BANK OF COMMERCE': 'ibc.com',

    // ===== INSURANCE =====
    'NEW YORK LIFE': 'newyorklife.com',
    'NEW YORK LIFE INSURANCE': 'newyorklife.com',
    'USAA': 'usaa.com',
    'STATE FARM': 'statefarm.com',
    'ALLSTATE': 'allstate.com',
    'PRUDENTIAL': 'prudential.com',
    'PRUDENTIAL FINANCIAL': 'prudential.com',
    'METLIFE': 'metlife.com',
    'AFLAC': 'aflac.com',
    'PROGRESSIVE': 'progressive.com',
    'CIGNA': 'cigna.com',
    'AETNA': 'aetna.com',
    'ANTHEM': 'anthem.com',
    'UNITEDHEALTH': 'uhc.com',
    'UNITEDHEALTH GROUP': 'uhc.com',
    'HUMANA': 'humana.com',
    'NORTHWESTERN MUTUAL': 'northwesternmutual.com',
    'MASSACHUSETTS MUTUAL': 'massmutual.com',
    'MASSMUTUAL': 'massmutual.com',
    'PACIFIC LIFE': 'pacificlife.com',
    'JACKSON NATIONAL': 'jackson.com',
    'JACKSON HOLDINGS': 'jackson.com',
    'THRIVENT': 'thrivent.com',
    'THRIVENT FINANCIAL': 'thrivent.com',
    'THRIVENT FINANCIAL FOR LUTHERANS': 'thrivent.com',
    'SENTRY INSURANCE': 'sentry.com',
    'LIBERTY MUTUAL': 'libertymutual.com',
    'CUNA MUTUAL': 'cunamutual.com',
    'CUNA MUTUAL GROUP': 'cunamutual.com',
    'GEICO': 'geico.com',
    'BERKSHIRE HATHAWAY': 'berkshirehathaway.com',  // Parent of GEICO
    'AMERICAN COUNCIL OF LIFE INSURERS': 'acli.com',
    'KAISER PERMANENTE': 'kaiserpermanente.org',

    // ===== ASSET MANAGERS =====
    'BLACKROCK': 'blackrock.com',
    'BGI': 'blackrock.com',            // Barclays Global Investors, acquired by BlackRock
    'BGI COMPANIES': 'blackrock.com',
    'VANGUARD': 'vanguard.com',
    'FIDELITY': 'fidelity.com',
    'FMR': 'fidelity.com',             // Fidelity Management & Research
    'FMR LLC': 'fidelity.com',
    'CHARLES SCHWAB': 'schwab.com',
    'SCHWAB': 'schwab.com',
    'TD AMERITRADE': 'schwab.com',     // Acquired by Schwab
    'AMERITRADE': 'schwab.com',
    'STATE STREET': 'statestreet.com',
    'STATE STREET BANK': 'statestreet.com',
    'NORTHERN TRUST': 'northerntrust.com',
    'T ROWE PRICE': 'troweprice.com',
    'T. ROWE PRICE': 'troweprice.com',
    'INVESCO': 'invesco.com',
    'FRANKLIN TEMPLETON': 'franklintempleton.com',
    'CAPITAL GROUP': 'capitalgroup.com',
    'CAPITAL GROUP COMPANIES': 'capitalgroup.com',
    'PIMCO': 'pimco.com',
    'TIAA': 'tiaa.org',

    // ===== PRIVATE EQUITY =====
    'BLACKSTONE': 'blackstone.com',
    'KKR': 'kkr.com',
    'KKR & CO': 'kkr.com',
    'CARLYLE': 'carlyle.com',
    'CARLYLE GROUP': 'carlyle.com',
    'APOLLO': 'apollo.com',
    'APOLLO MANAGEMENT': 'apollo.com',
    'BAIN CAPITAL': 'baincapital.com',
    'CITADEL': 'citadel.com',
    'CITADEL LLC': 'citadel.com',
    'LINCOLN INTERNATIONAL': 'lincolninternational.com',

    // ===== PAYMENTS =====
    'VISA': 'visa.com',
    'MASTERCARD': 'mastercard.com',
    'AMERICAN EXPRESS': 'americanexpress.com',
    'AMEX': 'americanexpress.com',
    'PAYPAL': 'paypal.com',
    'DISCOVER': 'discover.com',
    'SYNCHRONY': 'synchrony.com',
    'SYNCHRONY FINANCIAL': 'synchrony.com',

    // ===== FINTECH & MORTGAGE =====
    'ROCKET': 'rocketmortgage.com',
    'ROCKET MORTGAGE': 'rocketmortgage.com',
    'QUICKEN': 'quickenloans.com',
    'QUICKEN LOANS': 'quickenloans.com',
    'UNITED WHOLESALE MORTGAGE': 'uwm.com',
    'UWM': 'uwm.com',
    'COINBASE': 'coinbase.com',
    'ROBINHOOD': 'robinhood.com',
    'STRIPE': 'stripe.com',
    'OPPORTUNITY FINANCIAL': 'opploans.com',

    // ===== WEALTH MANAGEMENT =====
    'EDWARD JONES': 'edwardjones.com',
    'RAYMOND JAMES': 'raymondjames.com',
    'LPL FINANCIAL': 'lpl.com',
    'LPL': 'lpl.com',
    'AMERIPRISE': 'ameriprise.com',
    'AMERIPRISE FINANCIAL': 'ameriprise.com',

    // ===== REAL ESTATE =====
    'NATIONAL ASSOCIATION OF REALTORS': 'nar.realtor',
    'NAR': 'nar.realtor',
    'CBRE': 'cbre.com',
    'JLL': 'jll.com',
    'COLDWELL BANKER': 'coldwellbanker.com',
    'KELLER WILLIAMS': 'kw.com',
    'REMAX': 'remax.com',
    'RE/MAX': 'remax.com',

    // ===== TRADE ASSOCIATIONS =====
    'AMERICAN BANKERS ASSOCIATION': 'aba.com',
    'INDEPENDENT COMMUNITY BANKERS': 'icba.org',
    'ICBA': 'icba.org',
    'MORTGAGE BANKERS ASSOCIATION': 'mba.org',
    'SECURITIES INDUSTRY AND FINANCIAL MARKETS': 'sifma.org',
    'SIFMA': 'sifma.org',
    'INVESTMENT COMPANY INSTITUTE': 'ici.org',
    'ICI': 'ici.org',
    'AMERICAN INVESTMENT COUNCIL': 'investmentcouncil.org',
    'FINANCIAL SERVICES INSTITUTE': 'financialservices.org',

    // ===== CREDIT UNIONS =====
    'CREDIT UNION NATIONAL ASSOCIATION': 'cuna.org',
    'CUNA': 'cuna.org',
    "AMERICA'S CREDIT UNIONS": 'americascreditunions.org'
};

/**
 * INDUSTRY_MAP: Classifies companies into financial subsectors
 * Based on SEC SIC (Standard Industrial Classification) codes
 * Division H: Finance, Insurance, and Real Estate (SIC 60-67)
 *
 * SIC Major Groups:
 * 60 - Depository Institutions (Banks, Credit Unions)
 * 61 - Non-Depository Credit Institutions (Mortgage, Consumer Credit)
 * 62 - Security & Commodity Brokers, Dealers, Exchanges
 * 63 - Insurance Carriers
 * 64 - Insurance Agents, Brokers, and Service
 * 65 - Real Estate
 * 67 - Holding and Other Investment Offices
 */
const INDUSTRY_MAP = {
    // ===== SIC 60: DEPOSITORY INSTITUTIONS (Commercial Banks, Savings, Credit Unions) =====
    'CAPITAL ONE': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'JPMORGAN CHASE': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'JPMORGAN': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'BANK OF AMERICA': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'WELLS FARGO': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'CITIGROUP': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'CITI': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'GOLDMAN SACHS': { sector: 'banking', name: 'Inv. Banking', sic: '6211', sicDesc: 'Security Brokers & Dealers' },
    'MORGAN STANLEY': { sector: 'banking', name: 'Inv. Banking', sic: '6211', sicDesc: 'Security Brokers & Dealers' },
    'PNC': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'TRUIST': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'US BANK': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'US BANCORP': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'FIFTH THIRD': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'REGIONS': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'CITIZENS': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'HUNTINGTON': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'ZIONS': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'FIRST HORIZON': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'CADENCE BANK': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'M&T BANK': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'ARVEST': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'LIVE OAK': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'BANK OF HAWAII': { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' },
    'CREDIT UNION NATIONAL ASSOCIATION': { sector: 'banking', name: 'Credit Unions', sic: '6061', sicDesc: 'Credit Unions' },
    'CUNA': { sector: 'banking', name: 'Credit Unions', sic: '6061', sicDesc: 'Credit Unions' },
    "AMERICA'S CREDIT UNIONS": { sector: 'banking', name: 'Credit Unions', sic: '6061', sicDesc: 'Credit Unions' },

    // ===== SIC 61: NON-DEPOSITORY CREDIT (Mortgage, Consumer Credit) =====
    'ROCKET MORTGAGE': { sector: 'mortgage', name: 'Mortgage', sic: '6162', sicDesc: 'Mortgage Bankers' },
    'UNITED WHOLESALE MORTGAGE': { sector: 'mortgage', name: 'Mortgage', sic: '6162', sicDesc: 'Mortgage Bankers' },
    'UWM': { sector: 'mortgage', name: 'Mortgage', sic: '6162', sicDesc: 'Mortgage Bankers' },
    'SYNCHRONY': { sector: 'consumer_credit', name: 'Consumer Credit', sic: '6141', sicDesc: 'Personal Credit Institutions' },
    'DISCOVER': { sector: 'consumer_credit', name: 'Consumer Credit', sic: '6141', sicDesc: 'Personal Credit Institutions' },

    // ===== SIC 62: SECURITY & COMMODITY BROKERS =====
    'BLACKROCK': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'VANGUARD': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'FIDELITY': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'CHARLES SCHWAB': { sector: 'investment', name: 'Brokerage', sic: '6211', sicDesc: 'Security Brokers & Dealers' },
    'STATE STREET': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'NORTHERN TRUST': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'T ROWE PRICE': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'INVESCO': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'FRANKLIN TEMPLETON': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'CAPITAL GROUP': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'PIMCO': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'TIAA': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'INVESTMENT COMPANY INSTITUTE': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'ICI': { sector: 'investment', name: 'Asset Mgmt', sic: '6282', sicDesc: 'Investment Advice' },
    'ELLIOTT INVESTMENT MANAGEMENT': { sector: 'investment', name: 'Hedge Fund', sic: '6282', sicDesc: 'Investment Advice' },
    'ELLIOTT MANAGEMENT': { sector: 'investment', name: 'Hedge Fund', sic: '6282', sicDesc: 'Investment Advice' },
    'ROUTE ONE INVESTMENT': { sector: 'investment', name: 'Hedge Fund', sic: '6282', sicDesc: 'Investment Advice' },
    'CITADEL': { sector: 'investment', name: 'Hedge Fund', sic: '6282', sicDesc: 'Investment Advice' },
    'EDWARD JONES': { sector: 'investment', name: 'Brokerage', sic: '6211', sicDesc: 'Security Brokers & Dealers' },
    'RAYMOND JAMES': { sector: 'investment', name: 'Brokerage', sic: '6211', sicDesc: 'Security Brokers & Dealers' },
    'LPL FINANCIAL': { sector: 'investment', name: 'Brokerage', sic: '6211', sicDesc: 'Security Brokers & Dealers' },
    'LPL': { sector: 'investment', name: 'Brokerage', sic: '6211', sicDesc: 'Security Brokers & Dealers' },
    'AMERIPRISE': { sector: 'investment', name: 'Brokerage', sic: '6211', sicDesc: 'Security Brokers & Dealers' },

    // ===== SIC 63: INSURANCE CARRIERS =====
    'NEW YORK LIFE': { sector: 'insurance', name: 'Life Insurance', sic: '6311', sicDesc: 'Life Insurance' },
    'PRUDENTIAL': { sector: 'insurance', name: 'Life Insurance', sic: '6311', sicDesc: 'Life Insurance' },
    'METLIFE': { sector: 'insurance', name: 'Life Insurance', sic: '6311', sicDesc: 'Life Insurance' },
    'NORTHWESTERN MUTUAL': { sector: 'insurance', name: 'Life Insurance', sic: '6311', sicDesc: 'Life Insurance' },
    'MASSMUTUAL': { sector: 'insurance', name: 'Life Insurance', sic: '6311', sicDesc: 'Life Insurance' },
    'PACIFIC LIFE': { sector: 'insurance', name: 'Life Insurance', sic: '6311', sicDesc: 'Life Insurance' },
    'JACKSON NATIONAL': { sector: 'insurance', name: 'Life Insurance', sic: '6311', sicDesc: 'Life Insurance' },
    'THRIVENT': { sector: 'insurance', name: 'Life Insurance', sic: '6311', sicDesc: 'Life Insurance' },
    'PRINCIPAL': { sector: 'insurance', name: 'Life Insurance', sic: '6311', sicDesc: 'Life Insurance' },
    'PRINCIPAL LIFE': { sector: 'insurance', name: 'Life Insurance', sic: '6311', sicDesc: 'Life Insurance' },
    'AFLAC': { sector: 'insurance', name: 'Health Insurance', sic: '6321', sicDesc: 'Accident & Health Insurance' },
    'CIGNA': { sector: 'insurance', name: 'Health Insurance', sic: '6324', sicDesc: 'Hospital & Medical Service Plans' },
    'AETNA': { sector: 'insurance', name: 'Health Insurance', sic: '6324', sicDesc: 'Hospital & Medical Service Plans' },
    'ANTHEM': { sector: 'insurance', name: 'Health Insurance', sic: '6324', sicDesc: 'Hospital & Medical Service Plans' },
    'UNITEDHEALTH': { sector: 'insurance', name: 'Health Insurance', sic: '6324', sicDesc: 'Hospital & Medical Service Plans' },
    'HUMANA': { sector: 'insurance', name: 'Health Insurance', sic: '6324', sicDesc: 'Hospital & Medical Service Plans' },
    'STATE FARM': { sector: 'insurance', name: 'P&C Insurance', sic: '6331', sicDesc: 'Fire, Marine & Casualty Insurance' },
    'ALLSTATE': { sector: 'insurance', name: 'P&C Insurance', sic: '6331', sicDesc: 'Fire, Marine & Casualty Insurance' },
    'PROGRESSIVE': { sector: 'insurance', name: 'P&C Insurance', sic: '6331', sicDesc: 'Fire, Marine & Casualty Insurance' },
    'LIBERTY MUTUAL': { sector: 'insurance', name: 'P&C Insurance', sic: '6331', sicDesc: 'Fire, Marine & Casualty Insurance' },
    'GEICO': { sector: 'insurance', name: 'P&C Insurance', sic: '6331', sicDesc: 'Fire, Marine & Casualty Insurance' },
    'TRAVELERS': { sector: 'insurance', name: 'P&C Insurance', sic: '6331', sicDesc: 'Fire, Marine & Casualty Insurance' },
    'USAA': { sector: 'insurance', name: 'P&C Insurance', sic: '6331', sicDesc: 'Fire, Marine & Casualty Insurance' },

    // ===== SIC 65: REAL ESTATE =====
    'NAR': { sector: 'real_estate', name: 'Real Estate', sic: '6531', sicDesc: 'Real Estate Agents & Managers' },
    'NATIONAL ASSOCIATION OF REALTORS': { sector: 'real_estate', name: 'Real Estate', sic: '6531', sicDesc: 'Real Estate Agents & Managers' },
    'CBRE': { sector: 'real_estate', name: 'Real Estate', sic: '6531', sicDesc: 'Real Estate Agents & Managers' },
    'JLL': { sector: 'real_estate', name: 'Real Estate', sic: '6531', sicDesc: 'Real Estate Agents & Managers' },

    // ===== SIC 67: HOLDING & INVESTMENT OFFICES (Private Equity, Venture Capital) =====
    'BLACKSTONE': { sector: 'private_equity', name: 'Private Equity', sic: '6726', sicDesc: 'Other Investment Offices' },
    'KKR': { sector: 'private_equity', name: 'Private Equity', sic: '6726', sicDesc: 'Other Investment Offices' },
    'CARLYLE': { sector: 'private_equity', name: 'Private Equity', sic: '6726', sicDesc: 'Other Investment Offices' },
    'APOLLO': { sector: 'private_equity', name: 'Private Equity', sic: '6726', sicDesc: 'Other Investment Offices' },
    'BAIN CAPITAL': { sector: 'private_equity', name: 'Private Equity', sic: '6726', sicDesc: 'Other Investment Offices' },

    // ===== PAYMENTS / FINTECH (Non-traditional SIC, often 6199 or 7389) =====
    'VISA': { sector: 'payments', name: 'Payments', sic: '6199', sicDesc: 'Finance Services' },
    'MASTERCARD': { sector: 'payments', name: 'Payments', sic: '6199', sicDesc: 'Finance Services' },
    'AMERICAN EXPRESS': { sector: 'payments', name: 'Payments', sic: '6199', sicDesc: 'Finance Services' },
    'AMEX': { sector: 'payments', name: 'Payments', sic: '6199', sicDesc: 'Finance Services' },
    'PAYPAL': { sector: 'payments', name: 'Payments', sic: '6199', sicDesc: 'Finance Services' },

    // ===== TRADE ASSOCIATIONS (SIC 8611) =====
    'AMERICAN BANKERS ASSOCIATION': { sector: 'trade_assoc', name: 'Trade Assoc.', sic: '8611', sicDesc: 'Business Associations' },
    'INDEPENDENT COMMUNITY BANKERS': { sector: 'trade_assoc', name: 'Trade Assoc.', sic: '8611', sicDesc: 'Business Associations' },
    'ICBA': { sector: 'trade_assoc', name: 'Trade Assoc.', sic: '8611', sicDesc: 'Business Associations' },
    'MORTGAGE BANKERS ASSOCIATION': { sector: 'trade_assoc', name: 'Trade Assoc.', sic: '8611', sicDesc: 'Business Associations' },
    'SIFMA': { sector: 'trade_assoc', name: 'Trade Assoc.', sic: '8611', sicDesc: 'Business Associations' }
};

/**
 * Get industry classification for a company (with SIC codes)
 * @returns { sector, name, sic, sicDesc }
 */
function getIndustryForCompany(companyName) {
    if (!companyName) return { sector: 'other', name: 'Financial', sic: '6000', sicDesc: 'Finance' };
    const upper = companyName.toUpperCase().trim();

    // Direct match
    if (INDUSTRY_MAP[upper]) return INDUSTRY_MAP[upper];

    // Partial match
    for (const [key, industry] of Object.entries(INDUSTRY_MAP)) {
        if (upper.includes(key) || key.includes(upper)) {
            return industry;
        }
    }

    // Infer from keywords
    if (upper.includes('BANK') || upper.includes('BANCORP')) {
        return { sector: 'banking', name: 'Banking', sic: '6020', sicDesc: 'Commercial Banks' };
    }
    if (upper.includes('INSURANCE') || upper.includes('MUTUAL')) {
        return { sector: 'insurance', name: 'Insurance', sic: '6300', sicDesc: 'Insurance' };
    }
    if (upper.includes('INVESTMENT') || upper.includes('CAPITAL') || upper.includes('ASSET')) {
        return { sector: 'investment', name: 'Investment', sic: '6282', sicDesc: 'Investment Advice' };
    }
    if (upper.includes('MORTGAGE') || upper.includes('LENDING')) {
        return { sector: 'mortgage', name: 'Mortgage', sic: '6162', sicDesc: 'Mortgage Bankers' };
    }
    if (upper.includes('REALTY') || upper.includes('REAL ESTATE') || upper.includes('REALTOR')) {
        return { sector: 'real_estate', name: 'Real Estate', sic: '6531', sicDesc: 'Real Estate' };
    }

    return { sector: 'other', name: 'Financial', sic: '6000', sicDesc: 'Finance' };
}

/**
 * COMPANY_ALIASES: Maps subsidiary/variant names to parent company names
 * Used to normalize employer names before looking up in DOMAIN_MAP
 * Verified from FEC individual contribution data analysis
 */
const COMPANY_ALIASES = {
    // JPMorgan Chase subsidiaries
    'J.P. MORGAN': 'JPMORGAN CHASE',
    'J P MORGAN': 'JPMORGAN CHASE',
    'JP MORGAN': 'JPMORGAN CHASE',
    'CHASE': 'JPMORGAN CHASE',
    'CHASE BANK': 'JPMORGAN CHASE',
    'CHASE GROUP': 'JPMORGAN CHASE',
    'WASHINGTON MUTUAL': 'JPMORGAN CHASE',

    // Bank of America subsidiaries
    'BOFA': 'BANK OF AMERICA',
    'BOFA SECURITIES': 'BANK OF AMERICA',
    'BOFA SECURITIES INC': 'BANK OF AMERICA',
    'BOFA SECURITIES INC.': 'BANK OF AMERICA',
    'MERRILL': 'BANK OF AMERICA',
    'MERRILL LYNCH': 'BANK OF AMERICA',
    'MERRILL BANK OF AMERICA': 'BANK OF AMERICA',
    'LASALLE': 'BANK OF AMERICA',
    'LASALLE BANK': 'BANK OF AMERICA',
    'LASALLE MANAGEMENT': 'BANK OF AMERICA',
    'LASALLE BANK CORPORATION': 'BANK OF AMERICA',
    'FLEET': 'BANK OF AMERICA',

    // Wells Fargo subsidiaries
    'WELLS FARGO ADVISORS': 'WELLS FARGO',
    'WELLS FARGO SECURITIES': 'WELLS FARGO',
    'AG EDWARDS': 'WELLS FARGO',
    'WACHOVIA': 'WELLS FARGO',

    // Citigroup subsidiaries (note: Travelers and Primerica now independent)
    'CITI': 'CITIGROUP',
    'CITIBANK': 'CITIGROUP',
    'SMITH BARNEY': 'MORGAN STANLEY',  // Now part of Morgan Stanley

    // Morgan Stanley
    'MORGAN STANLEY SMITH BARNEY': 'MORGAN STANLEY',

    // PNC subsidiaries
    'NATIONAL CITY': 'PNC',
    'NATIONAL CITY BANK': 'PNC',

    // Truist (BB&T + SunTrust merger)
    'BB&T': 'TRUIST',
    'SUNTRUST': 'TRUIST',
    'TRUIST FINANCIAL': 'TRUIST',
    'TRUIST FINANCIAL CORPORATION': 'TRUIST',

    // Charles Schwab (acquired TD Ameritrade)
    'SCHWAB': 'CHARLES SCHWAB',
    'TD AMERITRADE': 'CHARLES SCHWAB',
    'AMERITRADE': 'CHARLES SCHWAB',

    // Fidelity
    'FMR': 'FIDELITY',
    'FMR LLC': 'FIDELITY',
    'FMR, LLC': 'FIDELITY',

    // BlackRock (acquired BGI)
    'BGI': 'BLACKROCK',
    'BGI COMPANIES': 'BLACKROCK',
    'BLACKROCK INC': 'BLACKROCK',
    'BLACKROCK INC.': 'BLACKROCK',

    // Goldman Sachs
    'GOLDMAN': 'GOLDMAN SACHS',
    'GOLDMAN SACHS GROUP': 'GOLDMAN SACHS',
    'GOLDMAN SACHS GROUP INC': 'GOLDMAN SACHS',
    'GOLDMAN SACHS GROUP INC.': 'GOLDMAN SACHS',
    'GOLDMAN SACHS  CO': 'GOLDMAN SACHS',

    // Regions
    'REGIONS FINANCIAL': 'REGIONS',
    'REGIONS FINANCIAL CORPORATION': 'REGIONS',
    'REGIONS BANK': 'REGIONS',

    // Insurance
    'NEW YORK LIFE INSURANCE': 'NEW YORK LIFE',
    'NEW YORK LIFE INSURANCE COMPANY': 'NEW YORK LIFE',
    'NEW YORK LIFE INSURANCE CO': 'NEW YORK LIFE',
    'NEW YORK LIFE INSURANCE CO.': 'NEW YORK LIFE',
    'BERKSHIRE HATHAWAY': 'GEICO',  // For insurance classification
    'BERKSHIRE HATHAWAY INC': 'GEICO',
    'BERKSHIRE HATHAWAY ASSOCIATES': 'GEICO',
    'TRAVELERS INSURANCE': 'TRAVELERS',
    'THRIVENT FINANCIAL FOR LUTHERANS': 'THRIVENT',
    'THRIVENT FINANCIAL': 'THRIVENT',

    // Apollo
    'APOLLO MANAGEMENT': 'APOLLO',

    // Carlyle
    'CARLYLE GROUP': 'CARLYLE',

    // Quicken/Rocket
    'QUICKEN LOANS': 'ROCKET MORTGAGE',
    'QUICKEN': 'ROCKET MORTGAGE',

    // Trade associations
    'NATIONAL ASSOCIATION OF REALTORS': 'NAR'
};

/**
 * Normalize an employer name to its parent company
 * @param {string} employer - Raw employer name from FEC data
 * @returns {string} - Normalized parent company name
 */
function normalizeEmployer(employer) {
    if (!employer) return '';
    const upper = employer.toUpperCase().trim();

    // Check direct alias match first
    if (COMPANY_ALIASES[upper]) {
        return COMPANY_ALIASES[upper];
    }

    // Check partial matches for known patterns
    for (const [alias, parent] of Object.entries(COMPANY_ALIASES)) {
        if (upper.includes(alias) || alias.includes(upper)) {
            return parent;
        }
    }

    return upper;
}

/**
 * Extract normalized company name from PAC name
 * "MORGAN STANLEY POLITICAL ACTION COMMITTEE" → "MORGAN STANLEY"
 */
function extractCompanyFromPac(pacName) {
    if (!pacName) return '';
    let name = pacName.toUpperCase();

    const suffixes = [
        'POLITICAL ACTION COMMITTEE',
        'FEDERAL POLITICAL ACTION COMMITTEE',
        'FEDERAL PAC',
        'GOOD GOVERNMENT FUND',
        'GOOD GOVERNMENT FEDERAL FUND',
        'EMPLOYEES PAC',
        'EMPLOYEE PAC',
        'VOLUNTARY PUBLIC AFFAIRS COMMITTEE',
        'COMMITTEE FOR RESPONSIBLE GOVERNMENT',
        'PAC',
        '& CO.',
        '& CO',
        'INC.',
        'INC',
        'CORP.',
        'CORP',
        'LLC',
        'NA',
        'N.A.',
        'CORPORATION',
        'II'  // Some PACs have "II" suffix
    ];

    // Remove suffixes iteratively
    let changed = true;
    while (changed) {
        changed = false;
        for (const suffix of suffixes) {
            if (name.endsWith(' ' + suffix) || name.endsWith(suffix)) {
                name = name.slice(0, name.lastIndexOf(suffix)).trim();
                changed = true;
            }
        }
    }

    // Clean up remaining punctuation
    name = name.replace(/[,.\s]+$/, '').trim();

    // Normalize to parent company
    return normalizeEmployer(name);
}

/**
 * Get domain for a company name (checks both raw name and normalized)
 */
function getDomainForCompany(companyName) {
    if (!companyName) return null;
    const upper = companyName.toUpperCase().trim();

    // Direct match first
    if (DOMAIN_MAP[upper]) return DOMAIN_MAP[upper];

    // Try normalized version
    const normalized = normalizeEmployer(upper);
    if (DOMAIN_MAP[normalized]) return DOMAIN_MAP[normalized];

    // Partial match as fallback
    for (const [key, domain] of Object.entries(DOMAIN_MAP)) {
        if (upper.includes(key) || key.includes(upper)) {
            return domain;
        }
    }

    return null;
}

/**
 * Build top sponsors list combining PAC + Individual contributions
 * Returns array of { name, total, pac, individual, domain }
 *
 * VERIFIED: This logic correctly combines contributions like:
 * - Tenney: Morgan Stanley PAC $12,500 + Individual $1,500 = $14,000
 * - Kaine: Visa PAC $10,000 + Individual $6,600 = $16,600
 * - Britt: Regions PAC $15,000 + Individual $3,300 = $18,300
 */
function buildTopSponsors(official) {
    const sponsorMap = new Map();

    // Add PAC contributions
    const pacs = official.top_financial_pacs || [];
    for (const pac of pacs) {
        const rawName = pac.name || pac.pac_name || pac.committee_name || '';

        // Skip if looks like official's own campaign
        const officialName = (official.name || '').toUpperCase();
        if (rawName.toUpperCase().includes(officialName.split(',')[0])) continue;
        if (rawName.includes('FOR CONGRESS') || rawName.includes('FOR SENATE')) continue;

        const companyName = extractCompanyFromPac(rawName);
        if (!companyName) continue;

        const industry = getIndustryForCompany(companyName);
        const existing = sponsorMap.get(companyName) || {
            name: companyName,
            pac: 0,
            individual: 0,
            domain: getDomainForCompany(companyName),
            sector: industry.sector,
            sectorName: industry.name
        };
        existing.pac += pac.amount || 0;
        sponsorMap.set(companyName, existing);
    }

    // Add Individual contributions
    const employers = official.top_financial_employers || [];
    for (const emp of employers) {
        const rawName = (emp.name || emp.employer || '').toUpperCase().trim();
        if (!rawName) continue;

        // Normalize employer to parent company
        const normalizedName = normalizeEmployer(rawName);

        // Try to match with existing PAC company
        let matchedKey = null;

        // First check exact match on normalized name
        if (sponsorMap.has(normalizedName)) {
            matchedKey = normalizedName;
        } else {
            // Then check partial matches
            for (const [key] of sponsorMap) {
                if (normalizedName.includes(key) || key.includes(normalizedName)) {
                    matchedKey = key;
                    break;
                }
            }
        }

        const companyName = matchedKey || normalizedName;
        const industry = getIndustryForCompany(companyName);
        const existing = sponsorMap.get(companyName) || {
            name: companyName,
            pac: 0,
            individual: 0,
            domain: getDomainForCompany(companyName),
            sector: industry.sector,
            sectorName: industry.name
        };
        existing.individual += emp.amount || 0;
        if (!existing.domain) existing.domain = getDomainForCompany(companyName);
        if (!existing.sector || existing.sector === 'other') {
            existing.sector = industry.sector;
            existing.sectorName = industry.name;
        }
        sponsorMap.set(companyName, existing);
    }

    // Convert to array, calculate totals, sort by combined total
    return Array.from(sponsorMap.values())
        .map(s => ({ ...s, total: s.pac + s.individual }))
        .sort((a, b) => b.total - a.total);
}

/**
 * Format currency for display
 */
function formatCurrency(amount) {
    if (amount >= 1000000) {
        return '$' + (amount / 1000000).toFixed(1) + 'M';
    } else if (amount >= 1000) {
        return '$' + Math.round(amount / 1000) + 'K';
    }
    return '$' + Math.round(amount).toLocaleString();
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Render sponsor logos HTML for an official row
 * Returns HTML string with up to 5 sponsor logo elements
 */
function renderSponsorLogos(official, maxLogos = 5) {
    const sponsors = buildTopSponsors(official);

    if (!sponsors.length) {
        return '<span class="no-sponsors">—</span>';
    }

    const html = sponsors.slice(0, maxLogos).map(sponsor => {
        const escapedName = escapeHtml(sponsor.name);
        const sectorLabel = sponsor.sectorName || 'Financial';
        const tooltipLines = [`<strong>${escapedName}</strong>`];
        tooltipLines.push(`<span style="color:#6b7280;font-size:11px;">${sectorLabel}</span>`);
        tooltipLines.push(`Total: ${formatCurrency(sponsor.total)}`);
        if (sponsor.pac > 0) tooltipLines.push(`PAC: ${formatCurrency(sponsor.pac)}`);
        if (sponsor.individual > 0) tooltipLines.push(`Individual: ${formatCurrency(sponsor.individual)}`);
        const tooltip = tooltipLines.join('<br>');

        const firmSlug = sponsor.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');

        if (sponsor.domain) {
            const faviconUrl = `https://www.google.com/s2/favicons?domain=${sponsor.domain}&sz=64`;
            return `
                <a href="/electwatch/firm/${encodeURIComponent(firmSlug)}"
                   class="sponsor-logo"
                   data-tippy-content="${tooltip.replace(/"/g, '&quot;')}"
                   onclick="event.stopPropagation();">
                    <img src="${faviconUrl}"
                         alt="${escapedName}"
                         onerror="this.parentElement.outerHTML='<span class=\\'sponsor-logo-fallback\\' data-tippy-content=\\'${tooltip.replace(/"/g, '&quot;').replace(/'/g, "\\'")}\\' >${escapedName.substring(0,3)}</span>'">
                </a>`;
        } else {
            return `
                <span class="sponsor-logo-fallback"
                      data-tippy-content="${tooltip.replace(/"/g, '&quot;')}">
                    ${escapedName.substring(0, 3)}
                </span>`;
        }
    }).join('');

    // Add count indicator if there are more sponsors
    const moreCount = sponsors.length - maxLogos;
    if (moreCount > 0) {
        return `<div class="sponsor-logos" data-more-count="+${moreCount}">${html}</div>`;
    }

    return `<div class="sponsor-logos">${html}</div>`;
}

/**
 * Initialize Tippy tooltips for sponsor logos
 * Call this after rendering sponsor logos
 */
function initSponsorTooltips() {
    if (typeof tippy !== 'undefined') {
        tippy('[data-tippy-content]', {
            allowHTML: true,
            placement: 'top',
            theme: 'light-border',
            animation: 'fade',
            duration: [200, 150],
            maxWidth: 280
        });
    }
}

/**
 * Get favicon URL for a company
 */
function getFaviconUrl(companyName, size = 64) {
    const domain = getDomainForCompany(companyName);
    if (!domain) return null;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=${size}`;
}

// Export functions for use in templates
if (typeof window !== 'undefined') {
    window.ElectWatchSponsors = {
        DOMAIN_MAP,
        COMPANY_ALIASES,
        INDUSTRY_MAP,
        normalizeEmployer,
        extractCompanyFromPac,
        getDomainForCompany,
        getIndustryForCompany,
        buildTopSponsors,
        formatCurrency,
        renderSponsorLogos,
        initSponsorTooltips,
        getFaviconUrl
    };
}
