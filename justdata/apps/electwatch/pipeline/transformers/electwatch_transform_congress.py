"""ElectWatch pipeline: officials processing + the top-level process_data orchestrator.

`process_officials` enriches the officials list with bioguide photos, top
industries, scores, and trade flags. It then delegates to
`_build_top_donors` and `_normalize_scores_to_zscore`.

`process_data` is the orchestrator — runs officials, firms, industries,
committees in order. It's kept here next to `process_officials` because
the coordinator's `process_data` method is the canonical entry into
this whole transformer subsystem.
"""
import logging
from datetime import datetime

from justdata.apps.electwatch.pipeline.coordinator import (
    NAME_ALIASES,
    convert_last_first_to_first_last,
    fetch_bioguide_photo,
)
from justdata.apps.electwatch.pipeline.transformers.electwatch_transform_donors import (
    _build_top_donors,
)
from justdata.apps.electwatch.pipeline.transformers.electwatch_transform_scores import (
    _normalize_scores_to_zscore,
)
from justdata.apps.electwatch.pipeline.transformers.electwatch_transform_firms import (
    process_firms,
)
from justdata.apps.electwatch.pipeline.transformers.electwatch_transform_industries import (
    process_industries,
)
from justdata.apps.electwatch.pipeline.transformers.electwatch_transform_committees import (
    process_committees,
)

logger = logging.getLogger(__name__)


def process_data(coordinator):
    """Process and aggregate fetched data."""
    logger.info("\n--- Processing Officials Data ---")
    process_officials(coordinator)

    logger.info("\n--- Processing Firms Data ---")
    process_firms(coordinator)

    logger.info("\n--- Processing Industries Data ---")
    process_industries(coordinator)

    logger.info("\n--- Processing Committees Data ---")
    process_committees(coordinator)


def process_officials(coordinator):
    """Process and enrich officials data."""
    from justdata.apps.electwatch.services.firm_mapper import FirmMapper, FINANCIAL_SECTORS

    mapper = FirmMapper()

    # Bioguide IDs for photos - source: https://bioguide.congress.gov
    BIOGUIDE_IDS = {
        'Jefferson Shreve': 'S001229',
        'Dave McCormick': 'M001243',
        'David McCormick': 'M001243',
        'Tim Moore': 'M001236',
        'Ro Khanna': 'K000389',
        'Nancy Pelosi': 'P000197',
        'Josh Gottheimer': 'G000583',
        'Michael McCaul': 'M001157',
        'Marjorie Taylor Greene': 'G000596',
        'Tommy Tuberville': 'T000278',
        'Kevin Hern': 'H001082',
        'French Hill': 'H001072',
        'James French Hill': 'H001072',
        'Ted Cruz': 'C001098',
        'Angus King': 'K000383',
        'John Fetterman': 'F000479',
        'Lisa McClain': 'M001136',
        'Byron Donalds': 'D000632',
        'Dan Newhouse': 'N000189',
        'Rick Larsen': 'L000560',
        'Thomas H. Kean': 'K000394',
        'Thomas Kean': 'K000394',
        'Bruce Westerman': 'W000821',
        'John Kennedy': 'K000393',
        'Markwayne Mullin': 'M001190',
        'Debbie Dingell': 'D000624',
        'Ritchie Torres': 'T000481',
        'Daniel Meuser': 'M001204',
        'Neal P. Dunn': 'D000628',
        'Neal Dunn': 'D000628',
        'Carol Devine Miller': 'M001205',
        'Carol Miller': 'M001205',
        'Val Hoyle': 'H001092',
        'Valerie Hoyle': 'H001092',
        'Jake Auchincloss': 'A000376',
        'Greg Landsman': 'L000601',
        'Dwight Evans': 'E000296',
        'James Comer': 'C001108',
        'Richard W. Allen': 'A000372',
        'William R. Keating': 'K000375',
        'Shelley Moore Capito': 'C001047',
        'John Boozman': 'B001236',
        'Tina Smith': 'S001203',
        'Sheldon Whitehouse': 'W000802',
        'Mitch McConnell': 'M000355',
        'Adam Smith': 'S000510',
        'Rich McCormick': 'M001211',
        'Jared Moskowitz': 'M001217',
        'Cleo Fields': 'F000477',
        'Scott Franklin': 'F000472',
        'Scott Mr Franklin': 'F000472',
        'Gilbert Cisneros': 'C001123',
        'Jonathan Jackson': 'J000309',
        'George Whitesides': 'W000830',
        'Rob Bresnahan': 'B001327',
        'Robert Bresnahan': 'B001327',
        'Julie Johnson': 'J000310',
        'Tony Wied': 'W000829',
        'Richard McCormick': 'M001218',
        'April Delaney': 'M001232',
        'April McClain Delaney': 'M001232',
        'Sheri Biggs': 'B001325',
        'David Taylor': 'T000490',
        'Dave Taylor': 'T000490',
        'Ashley Moody': 'M001244',
        'Susan Collins': 'C001035',
        'Susan M. Collins': 'C001035',
        'Joshua Gottheimer': 'G000583',
        'Daniel Newhouse': 'N000189',
        'Deborah Dingell': 'D000624',
        'Jacob Auchincloss': 'A000148',
        'Laurel Lee': 'L000597',
        'Rohit Khanna': 'K000389',
        'Gregory Landsman': 'L000601',
        'Peter Sessions': 'S000250',
        'Pete Sessions': 'S000250',
        'Morgan McGarvey': 'M001220',
        'Anthony Wied': 'W000829',
        'Roger Williams': 'W000816',
        'Lance Gooden': 'G000589',
        'Stephen Cohen': 'C001068',
        'Steve Cohen': 'C001068',
        'Shrikant Thanedar': 'T000488',
        'Shri Thanedar': 'T000488',
        'Christine Smith': 'S001203',
        'Earl Blumenauer': 'B000574',
        'Kathy Manning': 'M001135',
        'Addison McConnell': 'M000355',
        'Julia Letlow': 'L000595',
        'John Delaney': 'D000620',
        'Paul Mitchell': 'M001201',
        'Emily Randall': 'R000621',
        'Thomas R. Carper': 'C000174',
        'Tom Carper': 'C000174',
        'Gary Peters': 'P000595',
        'David Smith': 'S000510',
    }

    # Wikipedia photo URLs for Senate members (no House Clerk photos available)
    WIKIPEDIA_PHOTOS = {
        'Dave McCormick': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/McCormick_Portrait_%28HR%29.jpg/330px-McCormick_Portrait_%28HR%29.jpg',
        'David McCormick': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/McCormick_Portrait_%28HR%29.jpg/330px-McCormick_Portrait_%28HR%29.jpg',
        'Angus King': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Angus_King%2C_official_portrait%2C_113th_Congress.jpg/330px-Angus_King%2C_official_portrait%2C_113th_Congress.jpg',
        'Angus S. King': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Angus_King%2C_official_portrait%2C_113th_Congress.jpg/330px-Angus_King%2C_official_portrait%2C_113th_Congress.jpg',
        'Ted Cruz': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg/330px-Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg',
        'Rafael Cruz': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg/330px-Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg',
        'Markwayne Mullin': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Markwayne_Mullin_official_Senate_photo.jpg/330px-Markwayne_Mullin_official_Senate_photo.jpg',
        'Shelley Moore Capito': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Shelley_Moore_Capito_official_Senate_photo.jpg/330px-Shelley_Moore_Capito_official_Senate_photo.jpg',
        'John Boozman': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Senator_John_Boozman_Official_Portrait_%28115th_Congress%29.jpg/330px-Senator_John_Boozman_Official_Portrait_%28115th_Congress%29.jpg',
        'Tina Smith': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Tina_Smith%2C_official_portrait%2C_116th_congress.jpg/330px-Tina_Smith%2C_official_portrait%2C_116th_congress.jpg',
        'John Kennedy': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/John_Kennedy%2C_official_portrait%2C_115th_Congress_%28cropped%29.jpg/330px-John_Kennedy%2C_official_portrait%2C_115th_Congress_%28cropped%29.jpg',
        'Tommy Tuberville': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Tommy_tuberville.jpg/330px-Tommy_tuberville.jpg',
        'Thomas Tuberville': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Tommy_tuberville.jpg/330px-Tommy_tuberville.jpg',
        'Sheldon Whitehouse': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Sheldon_Whitehouse%2C_official_portrait%2C_116th_congress.jpg/330px-Sheldon_Whitehouse%2C_official_portrait%2C_116th_congress.jpg',
        'Mitch McConnell': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Mitch_McConnell_2016_official_photo_%281%29.jpg/330px-Mitch_McConnell_2016_official_photo_%281%29.jpg',
        'John Fetterman': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/John_Fetterman_official_portrait.jpg/330px-John_Fetterman_official_portrait.jpg',
        'Ashley Moody': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Official_Portrait_of_Senator_Ashley_Moody_%28cropped%29.jpg/330px-Official_Portrait_of_Senator_Ashley_Moody_%28cropped%29.jpg',
        'Susan Collins': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Senator_Susan_Collins_official_photo%2C_117th_Congress_%28cropped%29.jpeg/330px-Senator_Susan_Collins_official_photo%2C_117th_Congress_%28cropped%29.jpeg',
        'Susan M. Collins': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Senator_Susan_Collins_official_photo%2C_117th_Congress_%28cropped%29.jpeg/330px-Senator_Susan_Collins_official_photo%2C_117th_Congress_%28cropped%29.jpeg',
        'Christine Smith': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Tina_Smith%2C_official_portrait%2C_116th_congress.jpg/330px-Tina_Smith%2C_official_portrait%2C_116th_congress.jpg',
        'Addison McConnell': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Mitch_McConnell_2016_official_photo_%281%29.jpg/330px-Mitch_McConnell_2016_official_photo_%281%29.jpg',
        'Gary Peters': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Gary_Peters%2C_official_portrait%2C_115th_congress.jpg/330px-Gary_Peters%2C_official_portrait%2C_115th_congress.jpg',
        'Thomas R. Carper': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Senator_Thomas_R._Carper_official_portrait%2C_117th_Congress.jpg/330px-Senator_Thomas_R._Carper_official_portrait%2C_117th_Congress.jpg',
        'Tom Carper': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Senator_Thomas_R._Carper_official_portrait%2C_117th_Congress.jpg/330px-Senator_Thomas_R._Carper_official_portrait%2C_117th_Congress.jpg',
    }

    # Known member data: name -> (first_elected_year, chamber, party)
    MEMBER_DATA = {
        'Ro Khanna': (2017, 'house', 'D'),
        'Nancy Pelosi': (1987, 'house', 'D'),
        'Josh Gottheimer': (2017, 'house', 'D'),
        'Michael McCaul': (2005, 'house', 'R'),
        'Marjorie Taylor Greene': (2021, 'house', 'R'),
        'Daniel Goldman': (2023, 'house', 'D'),
        'Tommy Tuberville': (2021, 'senate', 'R'),
        'Dave McCormick': (2025, 'senate', 'R'),
        'John Curtis': (2017, 'house', 'R'),
        'Gilbert Cisneros': (2019, 'house', 'D'),
        'French Hill': (2015, 'house', 'R'),
        'James French Hill': (2015, 'house', 'R'),
        'John Rose': (2019, 'house', 'R'),
        'Alan Lowenthal': (2013, 'house', 'D'),
        'Lisa McClain': (2021, 'house', 'R'),
        'Diana Harshbarger': (2021, 'house', 'R'),
        'Michael Burgess': (2003, 'house', 'R'),
        'Blake Moore': (2021, 'house', 'R'),
        'Mark Green': (2019, 'house', 'R'),
        'Pete Sessions': (1997, 'house', 'R'),
        'Dan Crenshaw': (2019, 'house', 'R'),
        'Brian Higgins': (2005, 'house', 'D'),
        'Kevin Hern': (2018, 'house', 'R'),
        'Bill Huizenga': (2011, 'house', 'R'),
        'Earl Blumenauer': (1996, 'house', 'D'),
        'John Boozman': (2011, 'senate', 'R'),
        'Shelley Moore Capito': (2015, 'senate', 'R'),
        'Gary Peters': (2015, 'senate', 'D'),
        'Debbie Stabenow': (2001, 'senate', 'D'),
        'Cynthia Lummis': (2021, 'senate', 'R'),
        'Steve Daines': (2015, 'senate', 'R'),
        'Tim Scott': (2013, 'senate', 'R'),
        'Roger Wicker': (2007, 'senate', 'R'),
        'Jefferson Shreve': (2025, 'house', 'R'),
        'Dan Newhouse': (2015, 'house', 'R'),
        'Rick Larsen': (2001, 'house', 'D'),
        'Thomas H. Kean': (2023, 'house', 'R'),
        'Thomas Kean': (2023, 'house', 'R'),
        'Bruce Westerman': (2015, 'house', 'R'),
        'Ted Cruz': (2013, 'senate', 'R'),
        'Angus King': (2013, 'senate', 'I'),
        'John Kennedy': (2017, 'senate', 'R'),
        'Markwayne Mullin': (2023, 'senate', 'R'),
        'John Fetterman': (2023, 'senate', 'D'),
        'Byron Donalds': (2021, 'house', 'R'),
        'Tim Moore': (2025, 'house', 'R'),
        'Daniel Meuser': (2019, 'house', 'R'),
        'Debbie Dingell': (2015, 'house', 'D'),
        'Neal P. Dunn': (2017, 'house', 'R'),
        'Neal Dunn': (2017, 'house', 'R'),
        'Carol Devine Miller': (2019, 'house', 'R'),
        'Carol Miller': (2019, 'house', 'R'),
        'Ritchie Torres': (2021, 'house', 'D'),
        'Val Hoyle': (2023, 'house', 'D'),
        'Valerie Hoyle': (2023, 'house', 'D'),
        'Jonathan Jackson': (2023, 'house', 'D'),
        'Julie Johnson': (2025, 'house', 'D'),
        'Jared Moskowitz': (2023, 'house', 'D'),
        'Rich McCormick': (2023, 'house', 'R'),
        'Jake Auchincloss': (2021, 'house', 'D'),
        'Greg Landsman': (2023, 'house', 'D'),
        'Dwight Evans': (2016, 'house', 'D'),
        'James Comer': (2016, 'house', 'R'),
        'Cleo Fields': (2023, 'house', 'D'),
        'Sheri Biggs': (2025, 'house', 'R'),
        'Richard W. Allen': (2017, 'house', 'R'),
        'David Taylor': (2025, 'house', 'R'),
        'Scott Franklin': (2021, 'house', 'R'),
        'Tony Wied': (2025, 'house', 'R'),
        'Rob Bresnahan': (2025, 'house', 'R'),
        'George Whitesides': (2025, 'house', 'D'),
        'William R. Keating': (2011, 'house', 'D'),
        'April Delaney': (2025, 'house', 'D'),
        'Sheldon Whitehouse': (2007, 'senate', 'D'),
        'Tina Smith': (2018, 'senate', 'D'),
        'Adam Smith': (1997, 'house', 'D'),
        'Mitch McConnell': (1985, 'senate', 'R'),
        'John Kennedy': (2017, 'senate'),
        'Mark Warner': (2009, 'senate'),
    }

    # Committee assignments for known officials
    COMMITTEE_ASSIGNMENTS = {
        'James French Hill': ['Financial Services (Chair)', 'Intelligence'],
        'French Hill': ['Financial Services (Chair)', 'Intelligence'],
        'Nancy Pelosi': ['Intelligence', 'Democratic Steering and Policy'],
        'Maxine Waters': ['Financial Services (Ranking)', 'Capital Markets'],
        'Josh Gottheimer': ['Financial Services', 'Homeland Security'],
        'Ro Khanna': ['Armed Services', 'Oversight and Reform'],
        'Michael McCaul': ['Foreign Affairs (Chair)', 'Homeland Security'],
        'Marjorie Taylor Greene': ['Homeland Security', 'Oversight'],
        'Tommy Tuberville': ['Agriculture', 'Armed Services', 'Veterans Affairs'],
        'Dave McCormick': ['Banking (Vice Chair)', 'Finance', 'Commerce'],
        'Tim Scott': ['Banking (Chair)', 'Finance', 'Health'],
        'Shelley Moore Capito': ['Appropriations', 'Commerce', 'Environment'],
        'Ted Cruz': ['Commerce (Chair)', 'Foreign Relations', 'Judiciary'],
        'Mitch McConnell': ['Appropriations', 'Agriculture', 'Rules'],
        'John Kennedy': ['Banking', 'Judiciary', 'Appropriations'],
        'Angus King': ['Armed Services', 'Intelligence', 'Energy'],
        'Markwayne Mullin': ['Armed Services', 'Environment', 'Health'],
        'John Fetterman': ['Agriculture', 'Banking', 'Environment'],
        'Sheldon Whitehouse': ['Budget', 'Environment', 'Judiciary'],
        'Kevin Hern': ['Budget', 'Ways and Means'],
        'Byron Donalds': ['Financial Services', 'Oversight', 'Small Business'],
        'Ritchie Torres': ['Financial Services', 'Homeland Security'],
        'Jake Auchincloss': ['Financial Services', 'Transportation'],
        'Greg Landsman': ['Financial Services', 'Small Business'],
        'Rich McCormick': ['Foreign Affairs', 'Armed Services'],
        'Lisa McClain': ['Armed Services', 'Oversight'],
        'Daniel Meuser': ['Financial Services', 'Small Business'],
        'Debbie Dingell': ['Energy and Commerce', 'Natural Resources'],
        'Dan Newhouse': ['Appropriations', 'Select Intelligence'],
        'Rick Larsen': ['Armed Services', 'Transportation'],
        'William R. Keating': ['Armed Services', 'Foreign Affairs'],
        'James Comer': ['Oversight (Chair)', 'Agriculture'],
        'Jared Moskowitz': ['Foreign Affairs', 'Oversight'],
        'Jefferson Shreve': ['Small Business', 'Transportation'],
        'Bruce Westerman': ['Natural Resources (Chair)', 'Transportation'],
        'Neal P. Dunn': ['Agriculture', 'Veterans Affairs'],
        'Neal Dunn': ['Agriculture', 'Veterans Affairs'],
        'Carol Miller': ['Ways and Means', 'Energy Commerce'],
        'Carol Devine Miller': ['Ways and Means', 'Energy Commerce'],
    }

    current_year = datetime.now().year

    # Normalize names and merge duplicates
    officials_by_name = {}
    for official in coordinator.officials_data:
        name = official.get('name', '')
        # Convert "Last, First" to "First Last" format for dictionary lookups
        name = convert_last_first_to_first_last(name)
        # Apply name aliases to normalize
        canonical_name = NAME_ALIASES.get(name, name)
        official['name'] = canonical_name

        if canonical_name in officials_by_name:
            # Merge with existing official
            existing = officials_by_name[canonical_name]
            existing['trades'] = existing.get('trades', []) + official.get('trades', [])
            existing['contributions'] = max(
                existing.get('contributions', 0) or 0,
                official.get('contributions', 0) or 0
            )
            existing['financial_sector_pac'] = max(
                existing.get('financial_sector_pac', 0) or 0,
                official.get('financial_sector_pac', 0) or 0
            )
        else:
            officials_by_name[canonical_name] = official

    coordinator.officials_data = list(officials_by_name.values())
    logger.info(f"After deduplication: {len(coordinator.officials_data)} unique officials")

    for official in coordinator.officials_data:
        # Get committee assignments (name should already be in "First Last" format)
        name = official.get('name', '')
        lookup_name = convert_last_first_to_first_last(name)
        if lookup_name in COMMITTEE_ASSIGNMENTS:
            official['committees'] = COMMITTEE_ASSIGNMENTS[lookup_name]
        else:
            official.setdefault('committees', [])
        official.setdefault('contributions', 0)
        official.setdefault('contributions_list', [])

        # Create trades_list from trades for template compatibility
        trades = official.get('trades', [])
        official['trades_list'] = [
            {
                'ticker': t.get('ticker', ''),
                'company': t.get('company', ''),
                'type': t.get('type', 'trade'),
                'transaction_type': t.get('type', 'trade'),
                'amount': t.get('amount', {}),
                'date': t.get('transaction_date', ''),
            }
            for t in trades
        ]
        official['trades_count'] = len(trades)

        # Add years in Congress data, party info, and photo URL
        name = official.get('name', '')
        lookup_name = convert_last_first_to_first_last(name)
        if lookup_name in MEMBER_DATA:
            member_info = MEMBER_DATA[lookup_name]
            first_elected = member_info[0]
            chamber = member_info[1] if len(member_info) > 1 else None
            party = member_info[2] if len(member_info) > 2 else None
            official['first_elected'] = first_elected
            official['years_in_congress'] = current_year - first_elected
            if party:
                official['party'] = party

        # Add bioguide ID and photo URL
        bioguide_id = BIOGUIDE_IDS.get(name)
        if bioguide_id:
            official['bioguide_id'] = bioguide_id

        # Get photo URL - Wikipedia for Senate, House Clerk for House
        try:
            chamber = official.get('chamber', 'house')

            if name in WIKIPEDIA_PHOTOS:
                official['photo_url'] = WIKIPEDIA_PHOTOS[name]
                official['photo_source'] = 'wikipedia'
            else:
                photo_url = fetch_bioguide_photo(name, bioguide_id, chamber)
                if photo_url:
                    official['photo_url'] = photo_url
                    official['photo_source'] = 'house_clerk'
        except Exception as e:
            logger.debug(f"Could not fetch photo for {name}: {e}")

        if lookup_name not in MEMBER_DATA:
            # Estimate from trades if available (rough approximation)
            trades = official.get('trades', [])
            if trades:
                earliest_trade = min(t.get('transaction_date', '9999') for t in trades if t.get('transaction_date'))
                if earliest_trade != '9999':
                    first_year = int(earliest_trade[:4]) if earliest_trade else current_year
                    official['first_elected'] = first_year
                    official['years_in_congress'] = current_year - first_year
                else:
                    official['years_in_congress'] = None
                    official['first_elected'] = None
            else:
                official['years_in_congress'] = None
                official['first_elected'] = None
        official.setdefault('legislation', [])
        official.setdefault('recent_news', [])

        # Calculate top industries from traded stocks
        industry_counts = {}
        industry_amounts = {}

        for trade in official.get('trades', []):
            ticker = trade.get('ticker', '').upper()
            if not ticker:
                continue

            industries = mapper.get_industry_from_ticker(ticker)
            if not industries:
                company = trade.get('company', '') or ''
                company_lower = company.lower()
                if any(kw in company_lower for kw in ['bank', 'financial', 'credit']):
                    industries = ['banking']
                elif any(kw in company_lower for kw in ['coin', 'crypto', 'bitcoin']):
                    industries = ['crypto']
                elif any(kw in company_lower for kw in ['insurance', 'insur']):
                    industries = ['insurance']
                elif any(kw in company_lower for kw in ['payment', 'pay', 'visa', 'master']):
                    industries = ['fintech']

            for industry in industries:
                industry_counts[industry] = industry_counts.get(industry, 0) + 1
                amt = trade.get('amount', {})
                if isinstance(amt, dict):
                    min_amt = amt.get('min', 0) or 0
                    max_amt = amt.get('max', 0) or 0
                    trade_amt = (min_amt + max_amt) / 2 if max_amt > 0 else min_amt
                else:
                    trade_amt = float(amt) if amt else 0
                industry_amounts[industry] = industry_amounts.get(industry, 0) + trade_amt

        sorted_industries = sorted(
            industry_amounts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        top_industries = []
        for ind_code, amount in sorted_industries[:3]:
            sector_info = FINANCIAL_SECTORS.get(ind_code, {})
            top_industries.append({
                'code': ind_code,
                'name': sector_info.get('name', ind_code.title().replace('_', ' ')),
                'trade_count': industry_counts.get(ind_code, 0),
                'amount': amount
            })

        official['top_industries'] = top_industries
        official['industry_breakdown'] = {
            code: {
                'count': industry_counts.get(code, 0),
                'amount': industry_amounts.get(code, 0)
            }
            for code in industry_counts
        }

        involvement_by_industry = {}
        for code, amount in industry_amounts.items():
            involvement_by_industry[code] = {
                'contributions': 0,
                'stock_trades': amount,
                'total': amount,
                'trade_count': industry_counts.get(code, 0)
            }
        official['involvement_by_industry'] = involvement_by_industry

        # Build firms list from trades - aggregate by ticker
        firm_data = {}
        for trade in official.get('trades', []):
            ticker = trade.get('ticker', '').upper()
            if not ticker:
                continue

            company = trade.get('company', '') or ticker
            amt = trade.get('amount', {})
            if isinstance(amt, dict):
                trade_amt = amt.get('max', 0) or amt.get('min', 0) or 0
            else:
                trade_amt = float(amt) if amt else 0

            trade_type = trade.get('type', '').lower()
            is_buy = trade_type in ('purchase', 'buy')
            is_sell = trade_type in ('sale', 'sell')

            if ticker not in firm_data:
                firm_data[ticker] = {
                    'name': company,
                    'ticker': ticker,
                    'total': 0,
                    'buys': 0,
                    'sells': 0,
                    'trade_count': 0,
                    'type': 'trades'
                }

            firm_data[ticker]['total'] += trade_amt
            firm_data[ticker]['trade_count'] += 1
            if is_buy:
                firm_data[ticker]['buys'] += trade_amt
            elif is_sell:
                firm_data[ticker]['sells'] += trade_amt

        sorted_firms = sorted(firm_data.values(), key=lambda x: x['total'], reverse=True)
        official['firms'] = sorted_firms[:10]

        # Get net worth data for display
        from justdata.apps.electwatch.services.net_worth_client import get_net_worth, get_wealth_tier

        net_worth_data = get_net_worth(official.get('name', ''))
        official['net_worth'] = net_worth_data
        tier_code, tier_display = get_wealth_tier(net_worth_data['midpoint'])
        official['wealth_tier'] = tier_code
        official['wealth_tier_display'] = tier_display

        # Scoring system: trade activity + contributions weighted by finance %
        trade_score = official.get('trade_score', 0)

        total_pac = official.get('contributions', 0) or 0
        total_individual = official.get('individual_contributions_total', 0) or 0
        contribution_total = total_pac + total_individual

        financial_pac = official.get('financial_sector_pac', 0) or 0
        financial_individual = official.get('individual_financial_total', 0) or 0
        financial_total = financial_pac + financial_individual

        finance_pct = (financial_total / contribution_total) if contribution_total > 0 else 0

        contrib_score = (contribution_total / 1000) * finance_pct

        official['involvement_score'] = round(trade_score + contrib_score)

        official['score_breakdown'] = {
            'trade_score': round(trade_score, 1),
            'contributions_score': round(contrib_score, 1),
            'total_contributions': contribution_total,
            'finance_contributions': financial_total,
            'finance_pct': round(finance_pct * 100, 1),
            'total_trades': official.get('total_trades', 0)
        }

        combined_financial_pct = round(finance_pct * 100, 1)
        pac_pct = round((financial_pac / total_pac) * 100, 1) if total_pac > 0 else 0
        individual_pct = round((financial_individual / total_individual) * 100, 1) if total_individual > 0 else 0

        official['financial_sector_pct'] = combined_financial_pct
        official['contributions_display'] = {
            'total': contribution_total,
            'financial': financial_total,
            'financial_pct': combined_financial_pct,
            'pac_total': total_pac,
            'pac_financial': financial_pac,
            'pac_pct': pac_pct,
            'individual_total': total_individual,
            'individual_financial': financial_individual,
            'individual_pct': individual_pct
        }

    # Build top_donors by merging PAC and individual contributions
    _build_top_donors(coordinator)

    # Convert raw scores to Z-scores normalized to 1-100
    _normalize_scores_to_zscore(coordinator)

    # Re-sort by involvement score
    coordinator.officials_data.sort(key=lambda x: x.get('involvement_score', 0), reverse=True)

    with_activity = len([o for o in coordinator.officials_data if o.get('top_industries') or o.get('contributions', 0) > 0])
    without_activity = len(coordinator.officials_data) - with_activity
    logger.info(f"Processed {len(coordinator.officials_data)} total officials ({with_activity} with financial activity, {without_activity} without)")

