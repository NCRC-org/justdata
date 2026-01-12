#!/usr/bin/env python3
"""
Generate static HTML page for LoanTrends.
Reads data from JSON files and creates a standalone HTML page.
"""

import json
from pathlib import Path
from datetime import datetime

def generate_static_html():
    """Generate static HTML page."""
    
    static_dir = Path(__file__).parent / 'static_site'
    data_dir = static_dir / 'data'
    
    # Load data
    with open(data_dir / 'chart_data.json', 'r') as f:
        chart_data = json.load(f)
    
    with open(data_dir / 'metadata.json', 'r') as f:
        metadata = json.load(f)
    
    # Read CSS file
    css_file = Path(__file__).parent / 'static' / 'css' / 'style.css'
    css_content = ''
    if css_file.exists():
        with open(css_file, 'r') as f:
            css_content = f.read()
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LoanTrends Dashboard - JustData</title>
    <meta name="description" content="National mortgage lending trends dashboard with quarterly data">
    
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    
    <style>
        {css_content}
        
        .dashboard-container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .dashboard-header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .dashboard-header h1 {{
            color: var(--ncrc-dark-blue);
            margin-bottom: 10px;
        }}
        .dashboard-header p {{
            color: #666;
            font-size: 0.95rem;
        }}
        .loading-message {{
            text-align: center;
            padding: 40px;
            color: var(--ncrc-gray);
        }}
        .chart-section {{
            margin-bottom: 40px;
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .chart-section h2 {{
            color: var(--ncrc-dark-blue);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--ncrc-light-blue);
        }}
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
            margin-top: 20px;
        }}
        .chart-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #e0e0e0;
        }}
        .chart-card h3 {{
            color: var(--ncrc-dark-blue);
            margin-bottom: 15px;
            font-size: 1.1rem;
        }}
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        .chart-subtitle {{
            font-size: 0.85rem;
            color: #666;
            margin-top: 10px;
            font-style: italic;
        }}
    </style>
</head>
<body style="background: var(--ncrc-gray-light); min-height: 100vh;">
    <!-- Header -->
    <header class="header">
        <div class="header-content">
            <div class="header-layout">
                <div class="logo">
                    <a href="https://ncrc.org" target="_blank" rel="noopener noreferrer" aria-label="Visit NCRC.org (opens in new window)">
                        <img src="https://ncrc.org/wp-content/uploads/2020/03/NCRC-Logo-300x300.png" alt="NCRC Logo" style="max-height: 90px; width: auto;" onerror="this.style.display='none';">
                    </a>
                </div>
                <div class="header-title-section">
                    <h1>LoanTrends</h1>
                    <p class="just-data-subtitle">A Just Data Tool by NCRC</p>
                </div>
                <div class="header-tagline">
                    <div class="tagline-box">
                        <p>Data drives the <em>movement</em></p>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Return to JustData Home Button -->
    <div style="max-width: 1400px; margin: 0 auto; padding: 10px 20px;">
        <a href="https://justdata-landing.onrender.com" class="btn btn-primary" style="display: inline-block; padding: 10px 20px; background: var(--ncrc-primary-blue); color: white; text-decoration: none; border-radius: 6px; font-size: 0.95rem; margin-bottom: 10px;">
            <i class="fas fa-arrow-left"></i> Return to JustData Home
        </a>
    </div>

    <div class="dashboard-container">
        <div class="dashboard-header">
            <h1><i class="fas fa-chart-line"></i> National Mortgage Lending Trends Dashboard</h1>
            <p>Quarterly trends from CFPB HMDA Quarterly Data Graph API</p>
            <p id="timePeriodDisplay" style="font-size: 0.9em; color: #666; margin-top: 10px;">Time Period: {metadata['time_period']}</p>
            <p style="font-size: 0.85em; color: #999; margin-top: 5px;">Last updated: {metadata['generated_at'][:10]}</p>
        </div>

        <div id="loadingMessage" class="loading-message">
            <i class="fas fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 10px;"></i>
            <p>Loading dashboard data...</p>
        </div>

        <div id="dashboardContent" style="display: none;">
            <!-- Charts will be dynamically inserted here -->
        </div>
    </div>

    <script>
        // NCRC Color Palette
        const NCRC_COLORS = [
            '#552d87',  // Primary Blue (Purple)
            '#2fade3',  // Secondary Blue
            '#e82e2e',  // Accent Red
            '#eb2f89',  // Pink
            '#034ea0',  // Dark Blue
            '#ffc23a',  // Gold
            '#818390'   // Gray
        ];

        let colorIndex = 0;
        function getNextColor() {{
            const color = NCRC_COLORS[colorIndex % NCRC_COLORS.length];
            colorIndex++;
            return color;
        }}

        function resetColorIndex() {{
            colorIndex = 0;
        }}

        // Chart data loaded from JSON
        const chartData = {json.dumps(chart_data).replace('</script>', '<\\/script>')};
        const categories = {json.dumps(metadata['categories']).replace('</script>', '<\\/script>')};

        // Load dashboard data on page load
        $(document).ready(function() {{
            console.log('Loading dashboard data...');
            $('#loadingMessage').hide();
            $('#dashboardContent').show();
            renderDashboard({{ chart_data: chartData, categories: categories }});
        }});

        function renderDashboard(data) {{
            const chartData = data.chart_data;
            const categories = data.categories;
            const dashboardContent = $('#dashboardContent');
            
            // Render charts by category
            Object.keys(categories).forEach(categoryName => {{
                const endpoints = categories[categoryName];
                const sectionDiv = $('<div class="chart-section"></div>');
                sectionDiv.append(`<h2>${{categoryName}}</h2>`);
                
                const chartGrid = $('<div class="chart-grid"></div>');
                
                endpoints.forEach(endpoint => {{
                    if (chartData[endpoint]) {{
                        const chartCard = createChartCard(endpoint, chartData[endpoint]);
                        chartGrid.append(chartCard);
                    }}
                }});
                
                if (chartGrid.children().length > 0) {{
                    sectionDiv.append(chartGrid);
                    dashboardContent.append(sectionDiv);
                }}
            }});
        }}

        function createChartCard(endpoint, chartInfo) {{
            resetColorIndex();
            
            const card = $('<div class="chart-card"></div>');
            const title = chartInfo.title || endpoint.replace(/-/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
            card.append(`<h3>${{title}}</h3>`);
            
            if (chartInfo.subtitle) {{
                card.append(`<p class="chart-subtitle">${{chartInfo.subtitle}}</p>`);
            }}
            
            const canvas = $('<canvas></canvas>');
            const container = $('<div class="chart-container"></div>');
            container.append(canvas);
            card.append(container);
            
            // Prepare Chart.js data - support both quarterly and yearly
            const quarters = chartInfo.quarters || [];
            const years = chartInfo.years || [];
            const seriesData = chartInfo.series_data || {{}};
            const seriesNames = Object.keys(seriesData);
            
            // Determine if we're using quarters or years
            const isQuarterly = quarters.length > 0;
            const labels = isQuarterly ? quarters : years;
            const xAxisLabel = isQuarterly ? 'Quarter' : 'Year';
            
            const datasets = seriesNames.map(seriesName => {{
                const data = labels.map(label => seriesData[seriesName][label] || null);
                return {{
                    label: seriesName,
                    data: data,
                    borderColor: getNextColor(),
                    backgroundColor: getNextColor() + '20', // Add transparency
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1
                }};
            }});
            
            const chart = new Chart(canvas[0], {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'top',
                            labels: {{
                                usePointStyle: true,
                                padding: 15,
                                font: {{
                                    size: 11
                                }}
                            }}
                        }},
                        tooltip: {{
                            mode: 'index',
                            intersect: false
                        }}
                    }},
                    scales: {{
                        x: {{
                            title: {{
                                display: true,
                                text: xAxisLabel,
                                font: {{
                                    size: 12,
                                    weight: 'bold'
                                }}
                            }},
                            grid: {{
                                display: true,
                                color: '#e0e0e0'
                            }},
                            ticks: {{
                                maxRotation: isQuarterly ? 45 : 0,
                                minRotation: isQuarterly ? 45 : 0
                            }}
                        }},
                        y: {{
                            title: {{
                                display: true,
                                text: chartInfo.yLabel || 'Value',
                                font: {{
                                    size: 12,
                                    weight: 'bold'
                                }}
                            }},
                            grid: {{
                                display: true,
                                color: '#e0e0e0'
                            }},
                            beginAtZero: false
                        }}
                    }}
                }}
            }});
            
            return card;
        }}
    </script>
</body>
</html>"""
    
    # Save HTML file
    html_file = static_dir / 'index.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Static HTML generated: {html_file}")
    print(f"\nStatic site ready at: {static_dir}")
    print(f"\nTo deploy:")
    print(f"  1. Upload the 'static_site' folder to your hosting")
    print(f"  2. Or use: cd {static_dir} && python -m http.server 8000")
    print()

if __name__ == '__main__':
    generate_static_html()
