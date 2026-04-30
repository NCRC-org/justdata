"""ElectWatch weekly pipeline package.

Implementation of the weekly data update pipeline split into stages:
- fetchers/   external API data fetch (Congress, FMP, Quiver, FEC, Finnhub, SEC, News)
- transformers/ data normalization / aggregation between fetch and load
- loaders/    BigQuery write operations
- insights    AI-generated summaries and pattern insights
- coordinator WeeklyDataUpdate class that orchestrates the stages

The public entry point is exposed as `WeeklyDataUpdate` from
justdata.apps.electwatch.weekly_update (a thin shim) so the Cloud Run Job
import path remains unchanged.
"""
