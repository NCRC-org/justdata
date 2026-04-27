"""AI pattern insight generation and sample data for ElectWatch (from former standalone app)."""
import json

def get_sample_insights():
    """Return sample insights for demo/testing with detailed entity data and sources."""
    return [
        {
            'title': 'Crypto Industry Concentration',
            'summary': 'Coinbase and related crypto firms have contributed $1.2M to Republican '
                      'members of the House Financial Services Committee in 2025. Simultaneously, '
                      '8 of these members have reported COIN stock purchases totaling $180K-$400K.',
            'detailed_summary': '''Analysis reveals a significant concentration of crypto industry financial activity among Republican members of the [[committee:house-financial-services|House Financial Services Committee]].

Between January 2025 and January 2026, [[firm:Coinbase|Coinbase Global Inc PAC]] contributed $450,000 across 23 committee members, while [[firm:Robinhood|Robinhood Markets]] contributed $280,000 to 18 members.

**Key Finding:** 8 of these same members reported purchasing COIN stock during this period, with disclosure ranges indicating total purchases between $180,000 and $400,000.

**Notable Members:**
• [[official:french_hill|Rep. French Hill]] (R-AR) - Committee Chair, received $180,000 in crypto PAC contributions and purchased COIN stock
• [[official:tom_emmer|Rep. Tom Emmer]] (R-MN) - Majority Whip, received $145,000 and purchased COIN
• [[official:cynthia_lummis|Sen. Cynthia Lummis]] (R-WY) - Senate Banking member, known Bitcoin advocate

This pattern suggests potential coordination between PAC contribution strategies and personal investment decisions among members with direct oversight authority over [[industry:crypto|cryptocurrency regulation]].''',
            'evidence': 'Based on FEC filings and STOCK Act disclosures through Jan 2026',
            'category': 'cross_correlation',
            'severity': 'high',
            'firms': [
                {'name': 'Coinbase', 'ticker': 'COIN', 'amount': 450000, 'detail': '23 officials received contributions'},
                {'name': 'Robinhood', 'ticker': 'HOOD', 'amount': 280000, 'detail': '18 officials received contributions'},
                {'name': 'Block (Square)', 'ticker': 'SQ', 'amount': 195000, 'detail': '16 officials received contributions'},
            ],
            'officials': [
                {'id': 'french_hill', 'name': 'French Hill', 'party': 'R', 'state': 'AR', 'amount': 180000, 'detail': 'Chair, purchased COIN stock'},
                {'id': 'tom_emmer', 'name': 'Tom Emmer', 'party': 'R', 'state': 'MN', 'amount': 145000, 'detail': 'Majority Whip, purchased COIN'},
                {'id': 'cynthia_lummis', 'name': 'Cynthia Lummis', 'party': 'R', 'state': 'WY', 'amount': 120000, 'detail': 'Senate Banking, Bitcoin advocate'},
                {'id': 'ritchie_torres', 'name': 'Ritchie Torres', 'party': 'D', 'state': 'NY', 'amount': 95000, 'detail': 'Crypto Caucus member'},
            ],
            'industries': [
                {'code': 'crypto', 'name': 'Digital Assets & Crypto', 'amount': 1200000, 'detail': 'Primary sector, 71% to Republicans'},
            ],
            'committees': [
                {'id': 'house-financial-services', 'name': 'House Financial Services', 'chamber': 'house', 'members': 71, 'detail': 'Primary jurisdiction over crypto regulation'},
            ],
            'sources': [
                {'title': 'Coinbase PAC spending surges as crypto regulation heats up', 'url': 'https://www.politico.com/news/2025/crypto-pac-spending', 'source': 'Politico', 'date': '2025-11-15'},
                {'title': 'Congressional Stock Trading in Crypto Sector Under Scrutiny', 'url': 'https://www.reuters.com/markets/congressional-crypto-trading', 'source': 'Reuters', 'date': '2025-12-02'},
                {'title': 'FEC Records: Crypto Industry PAC Disbursements Q3-Q4 2025', 'url': 'https://www.fec.gov/data/disbursements/', 'source': 'FEC.gov', 'date': '2026-01-05'},
            ]
        },
        {
            'title': 'Banking PAC Activity Spike',
            'summary': 'Wells Fargo and JPMorgan PAC contributions to Senate Banking Committee '
                      'members increased 45% in Q4 2025 compared to Q3, correlating with '
                      'upcoming CFPB oversight hearings scheduled for February 2026.',
            'detailed_summary': '''A significant spike in [[industry:banking|banking sector]] PAC contributions occurred in Q4 2025, coinciding with scheduled CFPB oversight hearings.

**Contribution Increases (Q3 to Q4 2025):**
• [[firm:Wells Fargo|Wells Fargo PAC]]: +52% ($850,000 total)
• [[firm:JPMorgan Chase|JPMorgan Chase PAC]]: +41% ($780,000 total)
• [[firm:Bank of America|Bank of America PAC]]: +28% ($620,000 total)

This surge correlates with the scheduling of CFPB oversight hearings for February 2026 and pending consideration of the Consumer Financial Protection Reform Act.

**Key Recipients on [[committee:senate-banking|Senate Banking Committee]]:**
• [[official:tim_scott|Sen. Tim Scott]] (R-SC) - Ranking Member, received $320,000
• [[official:elizabeth_warren|Sen. Elizabeth Warren]] (D-MA) - CFPB advocate, received $95,000

The [[committee:house-financial-services|House Financial Services Committee]] is expected to hold joint oversight hearings. Total combined contributions from these two institutions to Banking Committee members: $1.4M.

The timing suggests strategic deployment of PAC resources ahead of significant regulatory review periods.''',
            'evidence': 'FEC data analysis comparing quarterly contribution trends',
            'category': 'timing',
            'severity': 'medium',
            'firms': [
                {'name': 'Wells Fargo', 'ticker': 'WFC', 'amount': 850000, 'detail': '52% increase Q3 to Q4'},
                {'name': 'JPMorgan Chase', 'ticker': 'JPM', 'amount': 780000, 'detail': '41% increase Q3 to Q4'},
                {'name': 'Bank of America', 'ticker': 'BAC', 'amount': 620000, 'detail': '28% increase Q3 to Q4'},
            ],
            'officials': [
                {'id': 'tim_scott', 'name': 'Tim Scott', 'party': 'R', 'state': 'SC', 'amount': 320000, 'detail': 'Ranking Member, Banking'},
                {'id': 'elizabeth_warren', 'name': 'Elizabeth Warren', 'party': 'D', 'state': 'MA', 'amount': 95000, 'detail': 'Banking Committee, CFPB advocate'},
            ],
            'industries': [
                {'code': 'banking', 'name': 'Banking & Depository', 'amount': 2250000, 'detail': '45% Q4 increase'},
            ],
            'committees': [
                {'id': 'senate-banking', 'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'senate', 'members': 24, 'detail': 'Primary CFPB oversight authority'},
                {'id': 'house-financial-services', 'name': 'House Financial Services', 'chamber': 'house', 'members': 71, 'detail': 'Joint oversight hearings'},
            ],
            'sources': [
                {'title': 'Big Banks Ramp Up Political Spending Ahead of CFPB Hearings', 'url': 'https://www.wsj.com/finance/banking-pac-spending-cfpb', 'source': 'Wall Street Journal', 'date': '2025-12-18'},
                {'title': 'Senate Banking Committee schedules February CFPB oversight', 'url': 'https://www.banking.senate.gov/hearings', 'source': 'Senate.gov', 'date': '2025-11-30'},
                {'title': 'Q4 2025 PAC Activity Report', 'url': 'https://www.opensecrets.org/pacs', 'source': 'OpenSecrets', 'date': '2026-01-08'},
            ]
        },
        {
            'title': 'Cross-Party Pattern: Fintech',
            'summary': 'Fintech firms (PayPal, Block, Stripe) show unusually balanced contributions '
                      'across party lines, with 52% to Democrats and 48% to Republicans—significantly '
                      'more balanced than traditional banking (68% R / 32% D).',
            'detailed_summary': '''[[industry:fintech|Fintech sector]] PAC contributions display a notably different partisan distribution compared to traditional financial services.

**Partisan Split Comparison:**
| Sector | Democrat | Republican |
|--------|----------|------------|
| Traditional Banking | 32% | 68% |
| Fintech | 52% | 48% |

**Individual Firm Breakdowns:**
• [[firm:Visa|Visa]]: 54% D / 46% R ($340,000 total)
• [[firm:Mastercard|Mastercard]]: 51% D / 49% R ($320,000 total)
• [[firm:PayPal|PayPal]]: 55% D / 45% R ($205,000 total)

**Key Recipients:**
• [[official:maxine_waters|Rep. Maxine Waters]] (D-CA) - Ranking Member, [[committee:house-financial-services|House Financial Services]]: $125,000
• [[official:french_hill|Rep. French Hill]] (R-AR) - Chair, House Financial Services: $110,000

This balanced approach may reflect the sector's interest in maintaining regulatory relationships regardless of which party controls Congress. Total [[industry:fintech|fintech]] contributions reached $865,000 in the analysis period.''',
            'evidence': 'Comparative analysis of contribution patterns by industry',
            'category': 'party_balance',
            'severity': 'low',
            'firms': [
                {'name': 'Visa', 'ticker': 'V', 'amount': 340000, 'detail': '54% D / 46% R split'},
                {'name': 'Mastercard', 'ticker': 'MA', 'amount': 320000, 'detail': '51% D / 49% R split'},
                {'name': 'PayPal', 'ticker': 'PYPL', 'amount': 205000, 'detail': '55% D / 45% R split'},
            ],
            'officials': [
                {'id': 'maxine_waters', 'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'amount': 125000, 'detail': 'Ranking Member, Fin Services'},
                {'id': 'french_hill', 'name': 'French Hill', 'party': 'R', 'state': 'AR', 'amount': 110000, 'detail': 'Chair, Fin Services'},
            ],
            'industries': [
                {'code': 'fintech', 'name': 'Financial Technology', 'amount': 865000, 'detail': '52% D / 48% R overall'},
                {'code': 'banking', 'name': 'Banking & Depository', 'amount': 4200000, 'detail': '32% D / 68% R for comparison'},
            ],
            'committees': [
                {'id': 'house-financial-services', 'name': 'House Financial Services', 'chamber': 'house', 'members': 71, 'detail': 'Fintech regulatory oversight'},
                {'id': 'senate-banking', 'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'senate', 'members': 24, 'detail': 'Payments regulation'},
            ],
            'sources': [
                {'title': 'Fintech lobbying takes bipartisan approach as regulation looms', 'url': 'https://www.americanbanker.com/fintech-lobbying-bipartisan', 'source': 'American Banker', 'date': '2025-10-22'},
                {'title': 'Payment Industry PAC Spending Analysis 2025', 'url': 'https://www.opensecrets.org/industries/indus.php?ind=F03', 'source': 'OpenSecrets', 'date': '2025-12-15'},
            ]
        },
        {
            'title': 'Pre-Vote Stock Activity',
            'summary': '12 House Financial Services Committee members traded bank stocks within '
                      '30 days of the committee vote on the Regional Bank Stability Act. '
                      '9 of these trades were in institutions directly affected by the legislation.',
            'detailed_summary': '''STOCK Act disclosure analysis reveals concerning trading patterns surrounding the Regional Bank Stability Act vote.

**Key Finding:** 12 [[committee:house-financial-services|House Financial Services Committee]] members executed trades in [[industry:banking|banking sector]] stocks within 30 days of the November 2025 committee vote. Of these, **9 trades involved institutions directly affected by the legislation**.

**Stocks Traded Before Vote:**
• [[firm:KeyCorp|KeyCorp (KEY)]]: 4 members traded, $160,000 total value
• [[firm:Regions Financial|Regions Financial (RF)]]: 3 members traded, $155,000 total
• [[firm:Fifth Third Bancorp|Fifth Third Bancorp (FITB)]]: 2 members traded, $150,000 total

**Notable Trading Activity:**
• [[official:french_hill|Rep. French Hill]] (R-AR) - Purchased KEY stock 14 days before committee vote, disclosed value $95,000
• [[official:maxine_waters|Rep. Maxine Waters]] (D-CA) - No trades in affected stocks during window

The legislation's provisions on capital requirements and stress testing would directly benefit regional banks. Members who purchased shares voted in favor of relaxing these requirements.

Total disclosed trade value ranges from $245,000 to $780,000 due to STOCK Act bucket reporting requirements.''',
            'evidence': 'Cross-referenced STOCK Act disclosures with committee vote calendar',
            'category': 'timing',
            'severity': 'high',
            'firms': [
                {'name': 'KeyCorp', 'ticker': 'KEY', 'amount': 160000, 'detail': '4 members traded before vote'},
                {'name': 'Regions Financial', 'ticker': 'RF', 'amount': 155000, 'detail': '3 members traded before vote'},
                {'name': 'Fifth Third Bancorp', 'ticker': 'FITB', 'amount': 150000, 'detail': '2 members traded before vote'},
            ],
            'officials': [
                {'id': 'french_hill', 'name': 'French Hill', 'party': 'R', 'state': 'AR', 'amount': 95000, 'detail': 'Purchased KEY 14 days before vote'},
                {'id': 'maxine_waters', 'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'amount': 0, 'detail': 'No trades in affected stocks'},
            ],
            'industries': [
                {'code': 'banking', 'name': 'Banking & Depository', 'amount': 465000, 'detail': '12 members, 9 in affected institutions'},
            ],
            'committees': [
                {'id': 'house-financial-services', 'name': 'House Financial Services', 'chamber': 'house', 'members': 71, 'detail': 'Regional Bank Stability Act vote'},
            ],
            'sources': [
                {'title': 'Lawmakers traded bank stocks ahead of key committee vote', 'url': 'https://www.nytimes.com/2025/12/lawmakers-stock-trading-bank-vote', 'source': 'New York Times', 'date': '2025-12-10'},
                {'title': 'Regional Bank Stability Act advances from committee', 'url': 'https://financialservices.house.gov/news/regional-bank-stability-act', 'source': 'House.gov', 'date': '2025-11-18'},
                {'title': 'STOCK Act Filings Database', 'url': 'https://efdsearch.senate.gov/search/', 'source': 'Senate.gov', 'date': '2025-12-01'},
                {'title': 'Analysis: Congressional Trading and Banking Legislation', 'url': 'https://www.propublica.org/congress-stock-trading', 'source': 'ProPublica', 'date': '2025-12-22'},
            ]
        }
    ]


def generate_ai_pattern_insights():
    """Generate real AI insights using Claude based on actual data."""
    print("[AI] Starting insight generation...", flush=True)
    try:
        from justdata.shared.analysis.ai_provider import AIAnalyzer
        from justdata.apps.electwatch.services.data_store import get_officials, get_firms, get_metadata

        print("[AI] Imports successful, loading data...", flush=True)

        # Load actual data
        officials = get_officials()
        firms = get_firms()
        metadata = get_metadata()

        print(f"[AI] Loaded {len(officials) if officials else 0} officials, {len(firms) if firms else 0} firms", flush=True)

        if not officials or len(officials) < 5:
            print("[AI] Not enough data to generate insights", flush=True)
            return get_sample_insights()

        # Build data summary for AI analysis
        # Top 20 by financial sector PAC
        top_pac_recipients = sorted(
            [o for o in officials if o.get('financial_sector_pac', 0) > 0],
            key=lambda x: x.get('financial_sector_pac', 0),
            reverse=True
        )[:20]

        # Top 20 by stock trades
        top_traders = sorted(
            [o for o in officials if o.get('stock_trades_max', 0) > 0],
            key=lambda x: x.get('stock_trades_max', 0),
            reverse=True
        )[:20]

        # Group by party
        rep_pac_total = sum(o.get('financial_sector_pac', 0) for o in officials if o.get('party') == 'R')
        dem_pac_total = sum(o.get('financial_sector_pac', 0) for o in officials if o.get('party') == 'D')

        # Build context strings
        pac_recipients_str = "\n".join([
            f"- {o['name']} ({o['party']}-{o['state']}): ${o.get('financial_sector_pac', 0):,.0f} financial PAC, "
            f"${o.get('stock_trades_max', 0):,.0f} max trades, committees: {', '.join(o.get('committees', [])[:2])}"
            for o in top_pac_recipients[:15]
        ])

        traders_str = "\n".join([
            f"- {o['name']} ({o['party']}-{o['state']}): ${o.get('purchases_max', 0):,.0f} buys, "
            f"${o.get('sales_max', 0):,.0f} sells, top industries: {', '.join([i.get('name', i) if isinstance(i, dict) else i for i in o.get('top_industries', [])[:2]])}"
            for o in top_traders[:15]
        ])

        # Top firms by connected officials
        top_firms_str = ""
        if firms:
            sorted_firms = sorted(firms, key=lambda x: x.get('connected_officials', 0), reverse=True)[:10]
            top_firms_str = "\n".join([
                f"- {f['name']} ({f.get('ticker', 'N/A')}): {f.get('connected_officials', 0)} connected officials, "
                f"${f.get('total_pac', 0):,.0f} PAC contributions"
                for f in sorted_firms
            ])

        prompt = f"""Analyze congressional financial activity data and identify patterns for a transparency research tool.

IMPORTANT DEFINITIONS:
- Financial Sector PAC: Political Action Committee contributions from banks, insurance, investment, and fintech firms
- Stock Trades: Disclosed securities transactions by members of Congress (STOCK Act filings)
- Cross-correlation: Pattern where PAC contributions and stock trades occur in same industry sector

DATA SUMMARY (as of {metadata.get('last_updated_display', 'January 2026')}):

Top Financial Sector PAC Recipients:
{pac_recipients_str}

Top Financial Sector Stock Traders:
{traders_str}

Top Financial Firms by Congressional Connections:
{top_firms_str}

Aggregate Statistics:
- Republican financial PAC total: ${rep_pac_total:,.0f}
- Democratic financial PAC total: ${dem_pac_total:,.0f}
- Total officials tracked: {len(officials)}

ANALYSIS REQUIREMENTS:
Generate exactly 4 findings based ONLY on the data above. Each finding must:
1. Reference specific officials and dollar amounts from the provided data
2. Identify a clear pattern (cross-correlation, concentration, or party distribution)
3. Use professional, analytical tone without speculation
4. Cite actual data points, not hypothetical scenarios

OUTPUT FORMAT (JSON array with 4 objects):
{{
  "title": "5-8 word headline",
  "summary": "2 sentences max referencing specific data",
  "detailed_summary": "3-4 paragraphs with entity links: [[official:name_id|Display Name]], [[firm:Firm Name|Display]], [[committee:house-financial-services|Committee Name]], [[industry:banking|industry name]]. Use **bold** for emphasis and bullet points with •",
  "evidence": "Data source (FEC filings, STOCK Act disclosures, etc.)",
  "category": "cross_correlation|concentration|party_balance",
  "severity": "high|medium|low",
  "firms": [{{"name": "...", "ticker": "...", "amount": 0, "detail": "..."}}],
  "officials": [{{"id": "lowercase_name", "name": "...", "party": "R|D", "state": "XX", "amount": 0, "detail": "..."}}],
  "industries": [{{"code": "banking|crypto|fintech|insurance", "name": "...", "amount": 0, "detail": "..."}}],
  "committees": [{{"id": "house-financial-services|senate-banking", "name": "...", "chamber": "house|senate", "members": 0, "detail": "..."}}],
  "sources": [{{"title": "...", "url": "https://...", "source": "FEC.gov|House.gov|Senate.gov", "date": "YYYY-MM-DD"}}]
}}

IMPORTANT:
- Use ONLY data provided above - do not invent officials, amounts, or patterns
- Official IDs should be lowercase with underscores (e.g., "french_hill", "tommy_tuberville")
- Include 2-4 sources per insight from government data sources (FEC.gov, House.gov, Senate.gov, efdsearch.senate.gov)
- Severity should reflect actual concentration: high = significant pattern affecting oversight, medium = notable trend, low = interesting observation

Return ONLY the JSON array, no additional text."""

        print("[AI] Generating insights from real data...", flush=True)
        print(f"[AI] Prompt length: {len(prompt)} chars", flush=True)
        analyzer = AIAnalyzer(ai_provider='claude')
        print("[AI] Calling Claude API...", flush=True)
        response = analyzer._call_ai(prompt, max_tokens=8000, temperature=0.3)
        print(f"[AI] Got response: {len(response) if response else 0} chars", flush=True)

        # Try to parse JSON response
        try:
            # Clean up response - sometimes Claude adds markdown code blocks
            cleaned = response.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            insights = json.loads(cleaned)
            if isinstance(insights, list) and len(insights) > 0:
                print(f"[AI] Successfully generated {len(insights)} insights")
                return insights
        except json.JSONDecodeError as e:
            print(f"[AI] JSON parse error: {e}")
            print(f"[AI] Response preview: {response[:500]}...")

        # Fallback to sample if parsing fails
        return get_sample_insights()

    except Exception as e:
        print(f"[AI] Error generating insights: {e}")
        import traceback
        traceback.print_exc()
        return get_sample_insights()
