"""ElectWatch pipeline: build firms_data from actual trade activity."""
import logging

logger = logging.getLogger(__name__)


def process_firms(coordinator):
    """Build comprehensive firm records from actual trade data."""
    from justdata.apps.electwatch.services.firm_mapper import (
        get_mapper, get_sector_for_ticker, TICKER_TO_SECTOR
    )

    mapper = get_mapper()
    firms_by_ticker = {}

    for official in coordinator.officials_data:
        for trade in official.get('trades', []):
            ticker = trade.get('ticker', '').upper()
            if not ticker:
                continue

            if ticker not in firms_by_ticker:
                sector = get_sector_for_ticker(ticker)
                if not sector:
                    industries = mapper.get_industry_from_ticker(ticker)
                    sector = industries[0] if industries else ''

                firm_record = mapper.get_firm_from_ticker(ticker)
                firm_name = firm_record.name if firm_record else trade.get('company', ticker)

                firms_by_ticker[ticker] = {
                    'ticker': ticker,
                    'name': firm_name,
                    'sector': sector,
                    'industry': sector,
                    'officials': [],
                    'trades': [],
                    'total_value': {'min': 0, 'max': 0},
                    'purchase_count': 0,
                    'sale_count': 0,
                    'officials_count': 0
                }

            firm = firms_by_ticker[ticker]

            if official['name'] not in [o['name'] for o in firm['officials']]:
                firm['officials'].append({
                    'id': official.get('id', ''),
                    'name': official['name'],
                    'party': official.get('party', ''),
                    'state': official.get('state', ''),
                    'chamber': official.get('chamber', 'house'),
                    'photo_url': official.get('photo_url')
                })
                firm['officials_count'] = len(firm['officials'])

            firm['trades'].append({
                'official': official['name'],
                'type': trade.get('type'),
                'amount': trade.get('amount'),
                'date': trade.get('transaction_date')
            })

            if trade.get('type') == 'purchase':
                firm['purchase_count'] += 1
            elif trade.get('type') == 'sale':
                firm['sale_count'] += 1

            amt = trade.get('amount', {})
            if isinstance(amt, dict):
                firm['total_value']['min'] += amt.get('min', 0)
                firm['total_value']['max'] += amt.get('max', 0)
            elif isinstance(amt, (int, float)):
                firm['total_value']['min'] += amt
                firm['total_value']['max'] += amt

    firms_list = []
    for ticker, firm in firms_by_ticker.items():
        firm['total'] = (firm['total_value']['min'] + firm['total_value']['max']) / 2
        firm['stock_trades'] = firm['total']

        firm['trades'] = sorted(
            firm['trades'],
            key=lambda x: x.get('date', ''),
            reverse=True
        )[:50]

        firms_list.append(firm)

    firms_list.sort(key=lambda x: x['total'], reverse=True)

    finnhub_firms = {f.get('ticker', '').upper(): f for f in coordinator.firms_data if f.get('ticker')}
    for firm in firms_list:
        ticker = firm['ticker']
        if ticker in finnhub_firms:
            finnhub_data = finnhub_firms[ticker]
            firm['quote'] = finnhub_data.get('quote')
            firm['news'] = finnhub_data.get('news', [])
            firm['insider_transactions'] = finnhub_data.get('insider_transactions', [])
            firm['sec_filings'] = finnhub_data.get('sec_filings', [])
            firm['market_cap'] = finnhub_data.get('market_cap', 0)

    coordinator.firms_data = firms_list
    logger.info(f"Built {len(coordinator.firms_data)} firms from trade data")

