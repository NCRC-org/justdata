# Restoring report_builder.py

The file was accidentally overwritten and needs to be restored with:
1. create_county_summary_table
2. create_comparison_table  
3. create_top_lenders_table
4. calculate_hhi_by_year

The backup file has create_county_summary_table and create_top_lenders_table, but is missing create_comparison_table.

I need to reconstruct create_comparison_table from the conversation history - it should:
- Filter to 2024 data (with improved year filtering)
- Calculate county metrics
- Compare to state and national benchmarks
- Include income category breakdowns (Low, Moderate, Middle, Upper)
- Calculate % change since 2018
- Return DataFrame with Metric, County (2024), State (2024), National (2024), % Change Since 2018 columns

