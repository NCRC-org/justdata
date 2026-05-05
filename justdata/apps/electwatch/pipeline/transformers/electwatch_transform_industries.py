"""ElectWatch pipeline: aggregate firms + officials data into industry-level summaries."""
import logging

logger = logging.getLogger(__name__)


def process_industries(coordinator):
    """Build industry aggregations from firms and officials data."""
    from justdata.apps.electwatch.services.firm_mapper import FINANCIAL_SECTORS

    industries = []
    for sector_id, sector_info in FINANCIAL_SECTORS.items():
        sector_firms = [
            {
                'ticker': f.get('ticker'),
                'name': f.get('name'),
                'total': f.get('total', 0),
                'officials_count': f.get('officials_count', 0),
                'trade_count': len(f.get('trades', []))
            }
            for f in coordinator.firms_data
            if f.get('sector') == sector_id or f.get('industry') == sector_id
        ]

        sector_firms = sorted(sector_firms, key=lambda x: x['total'], reverse=True)[:20]

        officials_set = {}
        total_trades = 0
        total_value_min = 0
        total_value_max = 0

        for firm in coordinator.firms_data:
            if firm.get('sector') != sector_id and firm.get('industry') != sector_id:
                continue

            total_trades += len(firm.get('trades', []))
            total_value_min += firm.get('total_value', {}).get('min', 0)
            total_value_max += firm.get('total_value', {}).get('max', 0)

            for official in firm.get('officials', []):
                if official['name'] not in officials_set:
                    officials_set[official['name']] = {
                        'id': official.get('id', ''),
                        'name': official['name'],
                        'party': official.get('party', ''),
                        'state': official.get('state', ''),
                        'chamber': official.get('chamber', 'house'),
                        'photo_url': official.get('photo_url')
                    }

        sector_officials = list(officials_set.values())[:30]

        industry = {
            'sector': sector_id,
            'name': sector_info.get('name', sector_id.title()),
            'description': sector_info.get('description', ''),
            'color': sector_info.get('color', '#6b7280'),
            'firms': sector_firms,
            'officials': sector_officials,
            'firms_count': len(sector_firms),
            'officials_count': len(officials_set),
            'total_trades': total_trades,
            'total_value': {
                'min': total_value_min,
                'max': total_value_max,
                'display': f"${total_value_min:,.0f} - ${total_value_max:,.0f}"
            },
            'news': []
        }

        keywords = sector_info.get('keywords', [sector_id])
        for article in coordinator.news_data:
            title = article.get('title', '').lower()
            if any(kw.lower() in title for kw in keywords):
                industry['news'].append(article)
                if len(industry['news']) >= 10:
                    break

        industries.append(industry)

    industries.sort(key=lambda x: x['total_trades'], reverse=True)

    coordinator.industries_data = industries
    logger.info(f"Processed {len(coordinator.industries_data)} industries with {sum(i['firms_count'] for i in industries)} total firm entries and {sum(i['officials_count'] for i in industries)} unique officials")

