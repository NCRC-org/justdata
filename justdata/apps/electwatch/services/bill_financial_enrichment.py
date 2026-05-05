"""
Financial conflict enrichment for bill JSON from Congress API.

Used by the /api/bills/<bill_id> endpoint to attach sample involvement
data to sponsors, cosponsors, and vote positions.
"""


def enrich_bill_with_financial_data(bill: dict) -> dict:
    """
    Add financial involvement data for sponsors, cosponsors, and voters.

    For each official involved with the bill, we add:
    - Their financial involvement in the bill's industries
    - Stock trades in related sectors
    - PAC contributions from related firms

    This creates the conflict-of-interest analysis.
    """
    # Get industries this bill relates to
    bill_industries = bill.get('industries', [])

    # Sample financial involvement data (would come from database in production)
    involvement_data = {
        'hill_j_french': {
            'total_involvement': 815000,
            'by_industry': {
                'crypto': {'contributions': 80000, 'stock_trades': 100000, 'total': 180000},
                'banking': {'contributions': 350000, 'stock_trades': 75000, 'total': 425000},
            },
            'related_firms': ['Coinbase', 'Robinhood', 'Wells Fargo']
        },
        'waters_maxine': {
            'total_involvement': 520000,
            'by_industry': {
                'banking': {'contributions': 280000, 'stock_trades': 25000, 'total': 305000},
                'consumer_lending': {'contributions': 120000, 'stock_trades': 10000, 'total': 130000},
            },
            'related_firms': ['Bank of America', 'JPMorgan Chase']
        },
        'emmer_tom': {
            'total_involvement': 580000,
            'by_industry': {
                'crypto': {'contributions': 180000, 'stock_trades': 120000, 'total': 300000},
                'fintech': {'contributions': 80000, 'stock_trades': 40000, 'total': 120000},
            },
            'related_firms': ['Coinbase', 'Block', 'Robinhood']
        },
        'mchenry_patrick': {
            'total_involvement': 480000,
            'by_industry': {
                'crypto': {'contributions': 95000, 'stock_trades': 50000, 'total': 145000},
                'banking': {'contributions': 200000, 'stock_trades': 35000, 'total': 235000},
            },
            'related_firms': ['Coinbase', 'JPMorgan Chase', 'Bank of America']
        },
        'torres_ritchie': {
            'total_involvement': 410000,
            'by_industry': {
                'crypto': {'contributions': 65000, 'stock_trades': 30000, 'total': 95000},
                'fintech': {'contributions': 80000, 'stock_trades': 25000, 'total': 105000},
            },
            'related_firms': ['Coinbase', 'Circle']
        },
        'pelosi_nancy': {
            'total_involvement': 890000,
            'by_industry': {
                'investment': {'contributions': 80000, 'stock_trades': 350000, 'total': 430000},
                'fintech': {'contributions': 60000, 'stock_trades': 180000, 'total': 240000},
            },
            'related_firms': ['NVIDIA', 'Apple', 'Microsoft', 'Visa']
        },
        'davidson_warren': {
            'total_involvement': 395000,
            'by_industry': {
                'crypto': {'contributions': 120000, 'stock_trades': 95000, 'total': 215000},
                'fintech': {'contributions': 60000, 'stock_trades': 20000, 'total': 80000},
            },
            'related_firms': ['Coinbase', 'Marathon Digital']
        },
        'lummis_cynthia': {
            'total_involvement': 520000,
            'by_industry': {
                'crypto': {'contributions': 85000, 'stock_trades': 200000, 'total': 285000},
                'banking': {'contributions': 120000, 'stock_trades': 15000, 'total': 135000},
            },
            'related_firms': ['Bitcoin (direct holdings)', 'Coinbase']
        },
    }

    # Enrich sponsors
    for sponsor in bill.get('sponsors', []):
        official_id = sponsor.get('official_id', '').lower().replace(' ', '_')
        if official_id in involvement_data:
            sponsor['financial_involvement'] = involvement_data[official_id]
            # Calculate industry-specific involvement for this bill
            relevant_amount = sum(
                involvement_data[official_id]['by_industry'].get(ind, {}).get('total', 0)
                for ind in bill_industries
            )
            sponsor['relevant_involvement'] = relevant_amount
            sponsor['has_conflict'] = relevant_amount > 50000

    # Enrich cosponsors
    for cosponsor in bill.get('cosponsors', []):
        official_id = cosponsor.get('official_id', '').lower().replace(' ', '_')
        if official_id in involvement_data:
            cosponsor['financial_involvement'] = involvement_data[official_id]
            relevant_amount = sum(
                involvement_data[official_id]['by_industry'].get(ind, {}).get('total', 0)
                for ind in bill_industries
            )
            cosponsor['relevant_involvement'] = relevant_amount
            cosponsor['has_conflict'] = relevant_amount > 50000

    # Enrich vote positions
    for vote in bill.get('votes', []):
        for position in vote.get('positions', []):
            official_id = position.get('official_id', '').lower().replace(' ', '_')
            if official_id in involvement_data:
                position['financial_involvement'] = involvement_data[official_id]
                relevant_amount = sum(
                    involvement_data[official_id]['by_industry'].get(ind, {}).get('total', 0)
                    for ind in bill_industries
                )
                position['relevant_involvement'] = relevant_amount
                position['has_conflict'] = relevant_amount > 50000

    # Add summary statistics
    total_with_conflicts = 0
    total_conflict_amount = 0

    for vote in bill.get('votes', []):
        for position in vote.get('positions', []):
            if position.get('has_conflict'):
                total_with_conflicts += 1
                total_conflict_amount += position.get('relevant_involvement', 0)

    bill['conflict_summary'] = {
        'voters_with_industry_ties': total_with_conflicts,
        'total_industry_involvement': total_conflict_amount,
        'industries_affected': bill_industries
    }

    return bill
