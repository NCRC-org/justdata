"""AI insight generation for the ElectWatch weekly pipeline."""
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def generate_summaries(coordinator):
    """Generate AI summaries using Claude."""
    logger.info("\n--- Generating AI Summaries ---")

    try:
        from anthropic import Anthropic
        api_key = os.getenv('CLAUDE_API_KEY')

        if not api_key:
            logger.warning("CLAUDE_API_KEY not set - skipping AI summaries")
            coordinator.summaries = {'status': 'skipped', 'reason': 'No API key'}
            return

        client = Anthropic(api_key=api_key)

        # Generate weekly overview
        coordinator.summaries['weekly_overview'] = _generate_weekly_overview(coordinator, client)

        # Generate top movers summary
        coordinator.summaries['top_movers'] = _generate_top_movers(coordinator, client)

        # Generate industry highlights
        coordinator.summaries['industry_highlights'] = _generate_industry_highlights(coordinator, client)

        coordinator.summaries['status'] = 'generated'
        coordinator.summaries['generated_at'] = datetime.now().isoformat()

        logger.info("AI summaries generated successfully")

    except Exception as e:
        logger.error(f"AI summary generation failed: {e}")
        coordinator.warnings.append(f"AI Summaries: {e}")
        coordinator.summaries = {'status': 'failed', 'error': str(e)}


def _generate_weekly_overview(coordinator, client) -> str:
    """Generate weekly overview summary."""
    try:
        # Build context from data
        top_officials = coordinator.officials_data[:10]
        top_traders = "\n".join([
            f"- {o['name']} ({o['party']}-{o['state']}): {o['total_trades']} trades, {o['stock_trades_display']}"
            for o in top_officials
        ])

        recent_news = "\n".join([
            f"- {n.get('title', '')[:80]}..."
            for n in coordinator.news_data[:10]
        ])

        prompt = f"""Summarize this week's key developments in congressional financial activity in 2-3 paragraphs. Be factual and neutral.

TOP TRADERS THIS WEEK:
{top_traders}

RECENT NEWS:
{recent_news}

Write a concise summary suitable for a dashboard overview."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    except Exception as e:
        logger.warning(f"Weekly overview generation failed: {e}")
        return "Weekly summary unavailable."


def _generate_top_movers(coordinator, client) -> str:
    """Generate summary of notable trading activity."""
    try:
        top_officials = coordinator.officials_data[:5]
        context = "\n".join([
            f"- {o['name']}: {o['purchase_count']} purchases, {o['sale_count']} sales, total value {o['stock_trades_display']}"
            for o in top_officials
        ])

        prompt = f"""Based on this congressional trading data, write 2-3 bullet points highlighting the most notable trading activity:

{context}

Be factual and avoid speculation."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    except Exception as e:
        logger.warning(f"Top movers generation failed: {e}")
        return "Top movers summary unavailable."


def _generate_industry_highlights(coordinator, client) -> str:
    """Generate industry-focused summary."""
    try:
        # Find most-traded sectors
        sector_trades = {}
        for official in coordinator.officials_data:
            for trade in official.get('trades', [])[:10]:
                ticker = trade.get('ticker', '')
                # Simple sector mapping
                if ticker in ['WFC', 'JPM', 'BAC', 'C', 'GS', 'MS']:
                    sector = 'banking'
                elif ticker in ['COIN', 'HOOD']:
                    sector = 'crypto'
                else:
                    sector = 'other'
                sector_trades[sector] = sector_trades.get(sector, 0) + 1

        prompt = f"""Based on congressional trading patterns showing {sector_trades.get('banking', 0)} banking trades and {sector_trades.get('crypto', 0)} crypto trades, write 2 sentences about industry focus."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    except Exception as e:
        logger.warning(f"Industry highlights generation failed: {e}")
        return "Industry highlights unavailable."


def generate_pattern_insights(coordinator) -> List[Dict[str, Any]]:
    """Generate AI pattern insights for the dashboard using the app's insight generator."""
    try:
        # Import the insight generator from the app
        from justdata.apps.electwatch.services.ai_pattern_insights import generate_ai_pattern_insights

        logger.info("Calling AI to generate pattern insights...")
        insights = generate_ai_pattern_insights()

        if insights and len(insights) > 0:
            logger.info(f"Generated {len(insights)} pattern insights")
            return insights
        else:
            logger.warning("AI returned no insights")
            return []

    except Exception as e:
        logger.error(f"Pattern insight generation failed: {e}")
        import traceback
        traceback.print_exc()
        return []
