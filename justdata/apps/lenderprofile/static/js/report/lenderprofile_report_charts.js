// LenderProfile Report - all data visualizations: branch network bar chart +
// state bubble chart, HMDA stacked bar + state bubbles, CRA small-business
// loans, CFPB complaints by year + category, plus the bubble-chart and
// category-list helpers and the NCRC color palette / state-name lookup.
// Moved verbatim from report_v2.js. Function bodies untouched.
//
// Chart.js is loaded via CDN in report_v2.html and is available as a global.

// =============================================================================


// =============================================================================
// DATA VISUALIZATIONS - Branches, Loans, Complaints
// =============================================================================

// NCRC Colors
export const NCRC_COLORS = {
    primary: '#1a8fc9',
    secondary: '#1a8fc9',
    accent1: '#1a8fc9',
    accent2: '#28a745',
    accent3: '#fb8c00',
    accent4: '#e53935',
    accent5: '#8e24aa',
    accent6: '#00acc1'
};

document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initializeVisualizations, 100);
});

export function initializeVisualizations() {
    var data = window.reportData;
    if (!data) return;
    console.log('Initializing visualizations...');
    renderBranchCharts(data);
    renderLoanCharts(data);
    renderSBLendingCharts(data);
    renderComplaintCharts(data);
}

export function renderBranchCharts(data) {
    var branches = data.branch_network || {};
    var section = document.getElementById('branch-network-section');

    // Hide entire section if no branch data
    if (!branches.has_data) {
        if (section) section.style.display = 'none';
        return;
    }

    var statesByYear = branches.states_by_year || {};
    var nationalByYear = branches.national_by_year || {};
    var stateContainer = document.getElementById('branches-state-bubbles');
    var yearCtx = document.getElementById('branches-year-chart');

    // Track selected year
    var years = [];

    if (yearCtx && branches.trends && branches.trends.by_year) {
        var yearData = branches.trends.by_year;
        years = Object.keys(yearData).sort();
        var counts = years.map(function(y) { return yearData[y]; });

        // Get national branch counts for the same years
        var nationalCounts = years.map(function(y) { return nationalByYear[y] || null; });

        // Calculate indexed values (first year = 100) for trend comparison
        var baseCount = counts[0] || 1;
        var baseNational = nationalCounts[0] || 1;
        var indexedCounts = counts.map(function(c) { return (c / baseCount) * 100; });
        var indexedNational = nationalCounts.map(function(n) { return n ? (n / baseNational) * 100 : null; });

        // Default to 2025 (or most recent year)
        var defaultYear = '2025';
        var defaultIndex = years.indexOf(defaultYear);
        if (defaultIndex === -1) defaultIndex = years.length - 1;

        // Set up colors and borders - orange + black border for selected
        var bgColors = years.map(function(y, i) { return i === defaultIndex ? '#ff9800' : NCRC_COLORS.primary; });
        var borderWidths = years.map(function(y, i) { return i === defaultIndex ? 2 : 0; });
        var borderColors = years.map(function() { return '#000000'; });

        // Build datasets - bar for bank branches (indexed), line for national (indexed)
        var datasets = [{
            label: 'Bank Trend',
            type: 'bar',
            data: indexedCounts,
            backgroundColor: bgColors,
            borderWidth: borderWidths,
            borderColor: borderColors,
            yAxisID: 'y',
            order: 2,
            // Store original counts for tooltips
            originalData: counts
        }];

        // Add national line if we have data
        if (nationalCounts.some(function(v) { return v !== null; })) {
            datasets.push({
                label: 'National Trend',
                type: 'line',
                data: indexedNational,
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                borderWidth: 3,
                pointRadius: 4,
                pointBackgroundColor: '#dc3545',
                fill: false,
                tension: 0.3,
                yAxisID: 'y',
                order: 1,
                // Store original counts for tooltips
                originalData: nationalCounts
            });
        }

        var chart = new Chart(yearCtx, {
            type: 'bar',
            data: {
                labels: years,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: nationalCounts.some(function(v) { return v !== null; }),
                        position: 'top',
                        labels: {
                            boxWidth: 12,
                            font: { size: 10 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return context[0].label;
                            },
                            label: function(context) {
                                // Skip individual labels, we'll use afterBody for custom display
                                return null;
                            },
                            afterBody: function(context) {
                                var index = context[0].dataIndex;
                                var bankCount = counts[index];
                                var nationalCount = nationalCounts[index];
                                var bankIndex = indexedCounts[index].toFixed(1);
                                var natIndex = indexedNational[index] ? indexedNational[index].toFixed(1) : 'N/A';

                                var lines = [
                                    'Bank Branches: ' + bankCount.toLocaleString(),
                                    'National Total: ' + (nationalCount ? nationalCount.toLocaleString() : 'N/A')
                                ];

                                if (nationalCount) {
                                    var pct = ((bankCount / nationalCount) * 100).toFixed(2);
                                    lines.push('');
                                    lines.push('Market Share: ' + pct + '%');
                                    lines.push('Bank Index: ' + bankIndex + ' | National Index: ' + natIndex);
                                }
                                return lines;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        display: true,
                        position: 'right',
                        beginAtZero: false,
                        grid: { display: false },
                        ticks: {
                            font: { size: 9 },
                            callback: function(value) {
                                return value.toFixed(0);
                            }
                        },
                        title: {
                            display: true,
                            text: 'Index (' + years[0] + ' = 100)',
                            font: { size: 9 }
                        }
                    }
                },
                layout: { padding: { top: 20 } },
                onClick: function(evt, elements) {
                    if (elements.length > 0) {
                        var index = elements[0].index;
                        var clickedYear = years[index];

                        // Update colors - orange for selected, primary for others
                        var newColors = years.map(function(y, i) {
                            return i === index ? '#ff9800' : NCRC_COLORS.primary;
                        });
                        // Update border widths - 2px for selected, 0 for others
                        var newBorderWidths = years.map(function(y, i) {
                            return i === index ? 2 : 0;
                        });
                        chart.data.datasets[0].backgroundColor = newColors;
                        chart.data.datasets[0].borderWidth = newBorderWidths;
                        chart.update();

                        // Update bubble chart with states for selected year (animated)
                        if (stateContainer && statesByYear[clickedYear]) {
                            var header = stateContainer.parentElement.querySelector('h4');
                            if (header) header.textContent = 'Branches by State (' + clickedYear + ')';
                            renderBubbleChart(stateContainer, statesByYear[clickedYear], true);
                        }
                    }
                },
                onHover: function(evt, elements) {
                    yearCtx.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                }
            },
            plugins: [{
                afterDatasetsDraw: function(chart) {
                    var ctx = chart.ctx;
                    // Get bar and line metadata
                    var barMeta = chart.getDatasetMeta(0);
                    var dataset = chart.data.datasets[0];
                    // Use original counts for labels
                    var originalData = dataset.originalData || dataset.data;

                    barMeta.data.forEach(function(bar, index) {
                        var dataVal = originalData[index];
                        // Position label at the top of the bar
                        var labelY = bar.y - 6;
                        var labelText = dataVal.toLocaleString();

                        ctx.font = 'bold 11px Arial';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'bottom';

                        // Draw white background/stroke so label appears in front of line
                        ctx.strokeStyle = '#ffffff';
                        ctx.lineWidth = 3;
                        ctx.lineJoin = 'round';
                        ctx.strokeText(labelText, bar.x, labelY);

                        // Draw the label text
                        ctx.fillStyle = '#000000';
                        ctx.fillText(labelText, bar.x, labelY);
                    });
                }
            }]
        });

        // Initialize bubble chart with default year
        var rendered = false;
        if (stateContainer && statesByYear && statesByYear[years[defaultIndex]]) {
            var header = stateContainer.parentElement.querySelector('h4');
            if (header) header.textContent = 'Branches by State (' + years[defaultIndex] + ')';
            renderBubbleChart(stateContainer, statesByYear[years[defaultIndex]]);
            rendered = true;
        }

        // Fallback to top_states if no states_by_year
        if (!rendered && stateContainer && branches.top_states) {
            renderBubbleChart(stateContainer, branches.top_states);
            rendered = true;
        }

        if (!rendered && stateContainer) {
            stateContainer.innerHTML = '<div class="viz-no-data">No state data available</div>';
        }
    } else if (stateContainer) {
        // No year chart but we have container - show top_states
        if (branches.top_states) {
            renderBubbleChart(stateContainer, branches.top_states);
        } else {
            stateContainer.innerHTML = '<div class="viz-no-data">No state data available</div>';
        }
    }
}

export function renderLoanCharts(data) {
    var footprint = data.lending_footprint || {};
    var section = document.getElementById('hmda-section');

    // Hide entire section if no HMDA data
    if (!footprint.has_data) {
        if (section) section.style.display = 'none';
        return;
    }

    var statesByYear = footprint.states_by_year || {};
    var byPurposeYear = footprint.by_purpose_year || {};
    var nationalByYear = footprint.national_by_year || {};
    var yearCtx = document.getElementById('loans-year-chart');
    var stateContainer = document.getElementById('loans-state-bubbles');
    var years = [];

    // Helper to get top 10 states and full total from a state object
    function getTop10States(statesObj) {
        if (!statesObj) return { top10: {}, total: 0 };
        var entries = Object.entries(statesObj);
        var total = entries.reduce(function(sum, e) { return sum + (parseInt(e[1]) || 0); }, 0);
        // Sort by value descending before slicing
        entries.sort(function(a, b) { return (parseInt(b[1]) || 0) - (parseInt(a[1]) || 0); });
        var top10 = entries.slice(0, 10);
        var result = {};
        top10.forEach(function(e) { result[e[0]] = e[1]; });
        return { top10: result, total: total };
    }

    // Define colors for each loan purpose
    var purposeColors = {
        'Purchase': '#003366',      // NCRC dark blue
        'Refinance': '#4a90a4',     // Lighter blue
        'Home Equity': '#7cb5c4',   // Even lighter blue
        'Other': '#b8d4de'          // Lightest blue
    };

    // Define order for stacking (bottom to top)
    var purposeOrder = ['Purchase', 'Refinance', 'Home Equity', 'Other'];

    if (yearCtx && footprint.by_year) {
        var yearData = footprint.by_year;
        years = Object.keys(yearData).sort();

        // Default to most recent year
        var defaultIndex = years.length - 1;
        var selectedIndex = defaultIndex;  // Track selected year for border highlight

        // Function to generate border widths array (2px for selected, 0 for others)
        function getBorderWidths() {
            return years.map(function(_, i) { return i === selectedIndex ? 2 : 0; });
        }

        // Function to generate border colors array (black for selected, transparent for others)
        function getBorderColors() {
            return years.map(function(_, i) { return i === selectedIndex ? '#000000' : 'transparent'; });
        }

        // Build stacked datasets by purpose
        var datasets = [];
        purposeOrder.forEach(function(purpose) {
            var purposeData = byPurposeYear[purpose] || {};
            var counts = years.map(function(y) { return purposeData[y] || 0; });

            // Only add dataset if it has data
            if (counts.some(function(c) { return c > 0; })) {
                datasets.push({
                    label: purpose,
                    data: counts,
                    backgroundColor: purposeColors[purpose] || '#999999',
                    borderWidth: getBorderWidths(),
                    borderColor: getBorderColors(),
                    stack: 'stack0',
                    yAxisID: 'y',
                    order: 2  // Draw bars first (behind line)
                });
            }
        });

        // Add national trend line (indexed, on hidden second axis)
        var nationalCounts = years.map(function(y) { return nationalByYear[y] || null; });
        var hasNationalData = nationalCounts.some(function(v) { return v !== null; });
        if (hasNationalData) {
            var baseNational = nationalCounts[0] || 1;
            var indexedNational = nationalCounts.map(function(n) { return n ? (n / baseNational) * 100 : null; });
            datasets.push({
                label: 'National Trend',
                type: 'line',
                data: indexedNational,
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                borderWidth: 3,
                pointRadius: 4,
                pointBackgroundColor: '#dc3545',
                fill: false,
                tension: 0.3,
                yAxisID: 'y2',
                order: 1,  // Draw line after bars (on top of colors, under numbers)
                originalData: nationalCounts
            });
        }

        var chart = new Chart(yearCtx, {
            type: 'bar',
            data: { labels: years, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: { boxWidth: 12, font: { size: 10 } }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: function(context) { return context[0].label; },
                            label: function(context) {
                                var label = context.dataset.label || '';
                                var value = context.raw || 0;
                                if (label === 'National Trend') {
                                    var origData = context.dataset.originalData;
                                    var natVal = origData ? origData[context.dataIndex] : null;
                                    return natVal ? 'National: ' + natVal.toLocaleString() : null;
                                }
                                return label + ': ' + value.toLocaleString();
                            },
                            afterBody: function(context) {
                                var index = context[0].dataIndex;
                                var total = yearData[years[index]] || 0;
                                var natTotal = nationalCounts[index];
                                var lines = ['', 'Bank Total: ' + total.toLocaleString()];
                                if (natTotal) {
                                    var pct = ((total / natTotal) * 100).toFixed(2);
                                    lines.push('Market Share: ' + pct + '%');
                                }
                                return lines;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        stacked: true
                    },
                    y: {
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        stacked: true,
                        grid: { display: false },
                        ticks: {
                            font: { size: 9 },
                            callback: function(v) {
                                if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M';
                                if (v >= 1000) return (v / 1000).toFixed(0) + 'K';
                                return v.toLocaleString();
                            }
                        },
                        title: { display: true, text: 'Applications', font: { size: 9 } }
                    },
                    y2: {
                        display: false,
                        position: 'left',
                        beginAtZero: false,
                        grid: { display: false }
                    }
                },
                layout: { padding: { top: 10 } },
                onClick: function(evt, elements) {
                    if (elements.length > 0) {
                        var index = elements[0].index;
                        var clickedYear = years[index];

                        // Update selected index and refresh borders
                        selectedIndex = index;
                        chart.data.datasets.forEach(function(ds) {
                            if (ds.type !== 'line') {
                                ds.borderWidth = getBorderWidths();
                                ds.borderColor = getBorderColors();
                            }
                        });
                        chart.update();

                        if (stateContainer && statesByYear[clickedYear]) {
                            var header = stateContainer.parentElement.querySelector('h4');
                            if (header) header.textContent = 'Top 10 States (' + clickedYear + ')';
                            var stateData = getTop10States(statesByYear[clickedYear]);
                            renderBubbleChart(stateContainer, stateData.top10, true, true, stateData.total);
                        }
                    }
                },
                onHover: function(evt, elements) { yearCtx.style.cursor = elements.length > 0 ? 'pointer' : 'default'; }
            },
            plugins: [{
                afterDatasetsDraw: function(chart) {
                    var ctx = chart.ctx;
                    // Find the last bar dataset (not the line)
                    var barDatasetIndex = -1;
                    for (var i = datasets.length - 1; i >= 0; i--) {
                        if (datasets[i].type !== 'line') {
                            barDatasetIndex = i;
                            break;
                        }
                    }
                    if (barDatasetIndex < 0) return;

                    // Draw total on top of each stacked bar
                    var meta = chart.getDatasetMeta(barDatasetIndex);
                    if (meta && meta.data) {
                        meta.data.forEach(function(bar, index) {
                            var total = yearData[years[index]] || 0;
                            var labelText = total >= 1000 ? (total / 1000).toFixed(0) + 'K' : total.toLocaleString();
                            ctx.font = 'bold 11px Arial';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'bottom';
                            ctx.strokeStyle = '#ffffff';
                            ctx.lineWidth = 3;
                            ctx.lineJoin = 'round';
                            ctx.strokeText(labelText, bar.x, bar.y - 6);
                            ctx.fillStyle = '#000000';
                            ctx.fillText(labelText, bar.x, bar.y - 6);
                        });
                    }
                }
            }]
        });

        // Initialize state list with default year (show as percentage for HMDA, top 10 only)
        if (stateContainer && statesByYear[years[defaultIndex]]) {
            var header = stateContainer.parentElement.querySelector('h4');
            if (header) header.textContent = 'Top 10 States (' + years[defaultIndex] + ')';
            var stateData = getTop10States(statesByYear[years[defaultIndex]]);
            renderBubbleChart(stateContainer, stateData.top10, false, true, stateData.total);
        } else if (stateContainer && footprint.by_state) {
            var stateData = getTop10States(footprint.by_state);
            renderBubbleChart(stateContainer, stateData.top10, false, true, stateData.total);
        } else if (stateContainer) {
            stateContainer.innerHTML = '<div class="viz-no-data">No state data available</div>';
        }
    } else if (stateContainer && footprint.by_state) {
        var stateData = getTop10States(footprint.by_state);
        renderBubbleChart(stateContainer, stateData.top10, false, true, stateData.total);
    } else if (stateContainer) {
        stateContainer.innerHTML = '<div class="viz-no-data">No state data available</div>';
    }
}

export function renderSBLendingCharts(data) {
    var sbLending = data.sb_lending || {};
    var section = document.getElementById('sb-lending-section');

    // Hide entire section if no CRA small business data
    if (!sbLending.has_data) {
        if (section) section.style.display = 'none';
        return;
    }

    var statesByYear = sbLending.states_by_year || {};
    var yearCtx = document.getElementById('sb-lending-year-chart');
    var stateContainer = document.getElementById('sb-lending-state-bubbles');

    var years = sbLending.years || [];
    // Use loan amounts (in thousands) instead of counts
    var lenderAmounts = sbLending.lender_loan_amounts || [];
    var nationalAmounts = sbLending.national_loan_amounts || [];

    if (yearCtx && years.length > 0) {
        // Calculate indexed values (first year = 100) for trend comparison
        var baseLender = lenderAmounts[0] || 1;
        var baseNational = nationalAmounts[0] || 1;
        var indexedLender = lenderAmounts.map(function(c) { return (c / baseLender) * 100; });
        var indexedNational = nationalAmounts.map(function(n) { return n ? (n / baseNational) * 100 : null; });

        // Default to most recent year
        var defaultIndex = years.length - 1;

        // Set up colors and borders - orange + black border for selected
        var bgColors = years.map(function(y, i) { return i === defaultIndex ? '#ff9800' : NCRC_COLORS.primary; });
        var borderWidths = years.map(function(y, i) { return i === defaultIndex ? 2 : 0; });
        var borderColors = years.map(function() { return '#000000'; });

        // Build datasets - bars for lender, line for national
        var datasets = [{
            label: 'Bank Volume',
            type: 'bar',
            data: indexedLender,
            backgroundColor: bgColors,
            borderWidth: borderWidths,
            borderColor: borderColors,
            yAxisID: 'y',
            order: 2,
            originalData: lenderAmounts
        }];

        // Add national line if we have data
        if (nationalAmounts.some(function(v) { return v > 0; })) {
            datasets.push({
                label: 'National Trend',
                type: 'line',
                data: indexedNational,
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                borderWidth: 3,
                pointRadius: 4,
                pointBackgroundColor: '#dc3545',
                fill: false,
                tension: 0.3,
                yAxisID: 'y',
                order: 1,
                originalData: nationalAmounts
            });
        }

        // Helper to format dollar amounts (in thousands -> display as $M or $B)
        function formatDollarAmount(amtThousands) {
            if (!amtThousands) return 'N/A';
            var amtMillions = amtThousands / 1000;
            if (amtMillions >= 1000) {
                return '$' + (amtMillions / 1000).toFixed(1) + 'B';
            }
            return '$' + amtMillions.toFixed(0) + 'M';
        }

        var chart = new Chart(yearCtx, {
            type: 'bar',
            data: { labels: years, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: nationalAmounts.some(function(v) { return v > 0; }),
                        position: 'top',
                        labels: { boxWidth: 12, font: { size: 10 } }
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) { return context[0].label; },
                            label: function() { return null; },
                            afterBody: function(context) {
                                var index = context[0].dataIndex;
                                var lenderAmt = lenderAmounts[index];
                                var nationalAmt = nationalAmounts[index];
                                var lines = [
                                    'Bank SB Volume: ' + formatDollarAmount(lenderAmt),
                                    'National Total: ' + formatDollarAmount(nationalAmt)
                                ];
                                if (lenderAmt && nationalAmt) {
                                    var pct = ((lenderAmt / nationalAmt) * 100).toFixed(3);
                                    lines.push('');
                                    lines.push('Market Share: ' + pct + '%');
                                }
                                return lines;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        display: true,
                        position: 'right',
                        beginAtZero: false,
                        grid: { display: false },
                        ticks: {
                            font: { size: 9 },
                            callback: function(value) { return value.toFixed(0); }
                        },
                        title: {
                            display: true,
                            text: 'Index (' + years[0] + ' = 100)',
                            font: { size: 9 }
                        }
                    }
                },
                layout: { padding: { top: 20 } },
                onClick: function(evt, elements) {
                    if (elements.length > 0) {
                        var index = elements[0].index;
                        var clickedYear = years[index];

                        // Update colors - orange for selected, primary for others
                        var newColors = years.map(function(y, i) {
                            return i === index ? '#ff9800' : NCRC_COLORS.primary;
                        });
                        // Update border widths - 2px for selected, 0 for others
                        var newBorderWidths = years.map(function(y, i) {
                            return i === index ? 2 : 0;
                        });
                        chart.data.datasets[0].backgroundColor = newColors;
                        chart.data.datasets[0].borderWidth = newBorderWidths;
                        chart.update();

                        // Update bubble chart with states for selected year (as percentages)
                        if (stateContainer && statesByYear[clickedYear]) {
                            var header = stateContainer.parentElement.querySelector('h4');
                            if (header) header.textContent = 'Top States (% of Volume, ' + clickedYear + ')';
                            // Convert to percentages
                            var yearStateData = statesByYear[clickedYear];
                            var yearTotal = Object.values(yearStateData).reduce(function(a, b) { return a + b; }, 0);
                            var pctData = {};
                            Object.keys(yearStateData).forEach(function(state) {
                                pctData[state] = yearTotal > 0 ? Math.round((yearStateData[state] / yearTotal) * 1000) / 10 : 0;
                            });
                            renderBubbleChart(stateContainer, pctData, true, true);
                        }
                    }
                },
                onHover: function(evt, elements) {
                    yearCtx.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                }
            },
            plugins: [{
                afterDatasetsDraw: function(chart) {
                    var ctx = chart.ctx;
                    var barMeta = chart.getDatasetMeta(0);
                    var originalData = lenderAmounts;

                    barMeta.data.forEach(function(bar, index) {
                        var dataVal = originalData[index];
                        var labelY = bar.y - 6;
                        // Format as $M or $B (amounts are in thousands)
                        var amtMillions = dataVal / 1000;
                        var labelText = amtMillions >= 1000 ? '$' + (amtMillions / 1000).toFixed(1) + 'B' : '$' + amtMillions.toFixed(0) + 'M';

                        ctx.font = 'bold 11px Arial';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'bottom';
                        ctx.strokeStyle = '#ffffff';
                        ctx.lineWidth = 3;
                        ctx.lineJoin = 'round';
                        ctx.strokeText(labelText, bar.x, labelY);
                        ctx.fillStyle = '#000000';
                        ctx.fillText(labelText, bar.x, labelY);
                    });
                }
            }]
        });

        // Initialize state chart with default year (as percentages)
        var defaultYear = years[defaultIndex];
        if (stateContainer && statesByYear[defaultYear]) {
            var header = stateContainer.parentElement.querySelector('h4');
            if (header) header.textContent = 'Top States (% of Volume, ' + defaultYear + ')';
            // Convert to percentages
            var defaultStateData = statesByYear[defaultYear];
            var defaultTotal = Object.values(defaultStateData).reduce(function(a, b) { return a + b; }, 0);
            var defaultPctData = {};
            Object.keys(defaultStateData).forEach(function(state) {
                defaultPctData[state] = defaultTotal > 0 ? Math.round((defaultStateData[state] / defaultTotal) * 1000) / 10 : 0;
            });
            renderBubbleChart(stateContainer, defaultPctData, false, true);
        } else if (stateContainer) {
            // Fallback to top_states percentages if no states_by_year
            var topStates = sbLending.top_states || [];
            var statePercentages = sbLending.state_percentages || [];
            if (topStates.length > 0) {
                var stateData = {};
                topStates.forEach(function(state, i) {
                    stateData[state] = statePercentages[i] || 0;
                });
                renderBubbleChart(stateContainer, stateData, false, true);
            } else {
                stateContainer.innerHTML = '<div class="viz-no-data">No state data available</div>';
            }
        }
    } else if (stateContainer) {
        stateContainer.innerHTML = '<div class="viz-no-data">No state data available</div>';
    }
}

export function renderComplaintCharts(data) {
    var regulatory = data.regulatory_risk || {};
    var complaints = regulatory.complaints || {};
    var section = document.getElementById('complaints-section');

    // Hide entire section if no complaint data
    // Check complaints.total since has_data is on regulatory_risk level, not complaints
    if (!complaints.total || complaints.total === 0) {
        if (section) section.style.display = 'none';
        return;
    }

    var nationalByYear = complaints.national_by_year || {};
    var categoriesByYear = complaints.categories_by_year || {};
    var yearCtx = document.getElementById('complaints-year-chart');
    var categoryContainer = document.getElementById('complaints-category-bubbles');
    var years = [];

    // Display the latest complaint date in the header (just the date, not full timestamp)
    var asOfEl = document.getElementById('complaints-as-of');
    if (asOfEl && complaints.latest_complaint_date) {
        var dateOnly = complaints.latest_complaint_date.split('T')[0];
        asOfEl.textContent = '(as of ' + dateOnly + ')';
    }

    // Build list of ALL unique categories across all years
    var allCategories = {};
    Object.keys(categoriesByYear).forEach(function(year) {
        var cats = categoriesByYear[year] || [];
        cats.forEach(function(cat) {
            var name = cat.product || cat.name || 'Unknown';
            if (!allCategories[name]) {
                allCategories[name] = true;
            }
        });
    });
    var allCategoryNames = Object.keys(allCategories);

    // Helper function to get categories for a year with all categories (0 for missing)
    function getCategoriesForYear(year) {
        var yearCats = categoriesByYear[year] || [];
        var catMap = {};
        yearCats.forEach(function(cat) {
            var name = cat.product || cat.name || 'Unknown';
            catMap[name] = cat.count || 0;
        });
        // Build complete list with all categories
        var result = allCategoryNames.map(function(name) {
            return { product: name, count: catMap[name] || 0 };
        });
        // Sort by count descending (categories with 0 go to bottom)
        result.sort(function(a, b) { return b.count - a.count; });
        return result;
    }

    if (yearCtx && complaints.by_year) {
        var yearData = complaints.by_year;
        years = Object.keys(yearData).sort();
        var counts = years.map(function(y) { return yearData[y]; });

        // Default to most recent year
        var defaultIndex = years.length - 1;

        // Calculate projected data for current (partial) year
        var projectedData = years.map(function() { return 0; });  // All zeros by default
        var hasProjection = false;
        var projectionInfo = null;

        // Check if last year is current year and we have at least 30 days of data
        if (years.length > 0 && complaints.latest_complaint_date) {
            var currentYear = new Date().getFullYear().toString();
            var lastYearInData = years[years.length - 1];

            if (lastYearInData === currentYear) {
                var latestDate = new Date(complaints.latest_complaint_date);
                var yearStart = new Date(currentYear, 0, 1);
                var daysElapsed = Math.floor((latestDate - yearStart) / (1000 * 60 * 60 * 24)) + 1;

                // Only show projection if we have at least 30 days of data
                if (daysElapsed >= 30) {
                    var actualCount = counts[counts.length - 1];
                    var projectedTotal = Math.round(actualCount * (365 / daysElapsed));
                    var projectedAddition = projectedTotal - actualCount;

                    // Set the projected addition for the last year only
                    projectedData[projectedData.length - 1] = projectedAddition;
                    hasProjection = true;
                    projectionInfo = {
                        actual: actualCount,
                        projected: projectedTotal,
                        daysElapsed: daysElapsed
                    };
                }
            }
        }

        // Set up colors - match branches chart (primary blue, orange for selected)
        var bgColors = years.map(function(y, i) { return i === defaultIndex ? '#ff9800' : NCRC_COLORS.primary; });
        var borderWidths = years.map(function(y, i) { return i === defaultIndex ? 2 : 0; });

        // Projected bar colors (50% opacity of the actual colors)
        var projectedColors = years.map(function(y, i) {
            return i === defaultIndex ? 'rgba(255, 152, 0, 0.5)' : 'rgba(0, 51, 102, 0.5)';
        });

        // Build datasets - actual + projected (stacked)
        var datasets = [{
            label: 'Complaints',
            data: counts,
            backgroundColor: bgColors,
            borderWidth: borderWidths,
            borderColor: '#000000'
        }];

        if (hasProjection) {
            datasets.push({
                label: 'Projected',
                data: projectedData,
                backgroundColor: projectedColors,
                borderWidth: 0,
                borderColor: 'transparent'
            });
        }

        var chart = new Chart(yearCtx, {
            type: 'bar',
            data: {
                labels: years,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                var year = years[context.dataIndex];
                                var currentYear = new Date().getFullYear().toString();
                                if (year === currentYear && projectionInfo) {
                                    if (context.datasetIndex === 0) {
                                        return 'Actual (YTD): ' + context.parsed.y.toLocaleString();
                                    } else {
                                        return 'Projected Total: ' + projectionInfo.projected.toLocaleString() + ' (based on ' + projectionInfo.daysElapsed + ' days)';
                                    }
                                }
                                return 'Complaints: ' + context.parsed.y.toLocaleString();
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false }, stacked: true },
                    y: { display: false, stacked: true }
                },
                layout: { padding: { top: 20 } },
                onClick: function(evt, elements) {
                    if (elements.length > 0) {
                        var index = elements[0].index;
                        var clickedYear = years[index];
                        var newColors = years.map(function(y, i) { return i === index ? '#ff9800' : NCRC_COLORS.primary; });
                        var newBorderWidths = years.map(function(y, i) { return i === index ? 2 : 0; });
                        chart.data.datasets[0].backgroundColor = newColors;
                        chart.data.datasets[0].borderWidth = newBorderWidths;
                        chart.update();
                        // Update category list for selected year (include all categories, 0 for missing)
                        if (categoryContainer) {
                            var header = categoryContainer.parentElement.querySelector('h4');
                            if (header) header.textContent = 'Complaints by Category (' + clickedYear + ')';
                            renderCategoryList(categoryContainer, getCategoriesForYear(clickedYear), true);
                        }
                    }
                },
                onHover: function(evt, elements) { yearCtx.style.cursor = elements.length > 0 ? 'pointer' : 'default'; }
            },
            plugins: [{
                afterDatasetsDraw: function(chart) {
                    var ctx = chart.ctx;
                    var actualMeta = chart.getDatasetMeta(0);
                    var projectedMeta = hasProjection ? chart.getDatasetMeta(1) : null;
                    var currentYear = new Date().getFullYear().toString();

                    actualMeta.data.forEach(function(bar, index) {
                        var actualVal = chart.data.datasets[0].data[index];
                        var projectedVal = hasProjection && chart.data.datasets[1] ? chart.data.datasets[1].data[index] : 0;
                        var year = years[index];

                        // For current year with projection, show projected total at top of stacked bar
                        var labelVal = actualVal;
                        var labelY = bar.y;

                        if (year === currentYear && projectionInfo && projectedMeta) {
                            // Use projected total and get Y position from top of stacked bar
                            labelVal = projectionInfo.projected;
                            var projectedBar = projectedMeta.data[index];
                            if (projectedBar) {
                                labelY = projectedBar.y;
                            }
                        }

                        var labelText = labelVal >= 1000 ? (labelVal/1000).toFixed(1) + 'K' : labelVal.toLocaleString();

                        // Add asterisk for projected values
                        if (year === currentYear && projectionInfo) {
                            labelText = labelText + '*';
                        }

                        ctx.font = 'bold 11px Arial';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'bottom';
                        ctx.strokeStyle = '#ffffff';
                        ctx.lineWidth = 3;
                        ctx.lineJoin = 'round';
                        ctx.strokeText(labelText, bar.x, labelY - 6);
                        ctx.fillStyle = '#000000';
                        ctx.fillText(labelText, bar.x, labelY - 6);
                    });
                }
            }]
        });

        // Initialize category list with default year (include all categories, 0 for missing)
        if (categoryContainer) {
            var defaultYear = years[defaultIndex];
            if (allCategoryNames.length > 0) {
                var header = categoryContainer.parentElement.querySelector('h4');
                if (header) header.textContent = 'Complaints by Category (' + defaultYear + ')';
                renderCategoryList(categoryContainer, getCategoriesForYear(defaultYear), false);
            } else if (complaints.main_categories && complaints.main_categories.length > 0) {
                renderCategoryList(categoryContainer, complaints.main_categories, false);
            } else {
                categoryContainer.innerHTML = '<div class="viz-no-data">No category data available</div>';
            }
        }
    } else if (categoryContainer && complaints.main_categories && complaints.main_categories.length > 0) {
        renderCategoryList(categoryContainer, complaints.main_categories, false);
    } else if (categoryContainer) {
        categoryContainer.innerHTML = '<div class="viz-no-data">No category data available</div>';
    }
}

// Shorten long CFPB category names
export function shortenCategoryName(name) {
    var shortNames = {
        'Checking or savings account': 'Checking/Savings',
        'Credit card or prepaid card': 'Credit Card',
        'Credit card': 'Credit Card',
        'Credit reporting, credit repair services, or other personal consumer reports': 'Credit Reporting',
        'Credit reporting or other personal consumer reports': 'Credit Reporting',
        'Credit reporting': 'Credit Reporting',
        'Debt collection': 'Debt Collection',
        'Money transfer, virtual currency, or money service': 'Money Transfer',
        'Money transfer': 'Money Transfer',
        'Mortgage': 'Mortgage',
        'Payday loan, title loan, or personal loan': 'Other Loans',
        'Payday loan, title loan, personal loan, or advance loan': 'Other Loans',
        'Payday loan': 'Payday Loan',
        'Student loan': 'Student Loan',
        'Vehicle loan or lease': 'Vehicle Loan',
        'Prepaid card': 'Prepaid Card',
        'Bank account or service': 'Bank Account',
        'Consumer Loan': 'Consumer Loan',
        'Other financial service': 'Other Services'
    };
    return shortNames[name] || name;
}

export function renderCategoryList(container, categories, animate) {
    if (!categories || categories.length === 0) {
        container.innerHTML = '<div class="viz-no-data">No category data available</div>';
        return;
    }

    var rowHeight = 32;

    // Calculate total for percentages
    var total = categories.reduce(function(sum, cat) { return sum + (cat.count || 0); }, 0);

    // Helper to format as percentage with count (count not bold)
    function formatPctCount(count) {
        if (total === 0) return '0% <span class="count-light">(0)</span>';
        var pct = (count / total * 100).toFixed(1);
        return pct + '% <span class="count-light">(' + count.toLocaleString() + ')</span>';
    }

    // Check if we can animate existing rows
    var existingRows = container.querySelectorAll('.state-row[data-category]');
    var canAnimate = animate && existingRows.length > 0;

    if (canAnimate) {
        // Build map of existing rows
        var existingMap = {};
        existingRows.forEach(function(el) {
            existingMap[el.getAttribute('data-category')] = el;
        });

        var wrapper = container.querySelector('.state-list');

        categories.slice(0, 10).forEach(function(cat, index) {
            var name = cat.product || cat.name || 'Unknown';
            var displayName = shortenCategoryName(name);
            var count = cat.count || 0;
            var rank = index + 1;
            var topPos = index * rowHeight;
            var el = existingMap[name];

            if (el) {
                // Check if position is changing
                var currentTop = parseInt(el.style.top) || 0;
                var isMoving = currentTop !== topPos;

                // Animate existing row to new position
                el.style.top = topPos + 'px';
                el.querySelector('.state-rank').textContent = rank + '.';
                el.querySelector('.state-name').textContent = displayName;

                // If moving, animate the background color
                if (isMoving) {
                    el.style.backgroundColor = '#2fade3';
                    setTimeout(function() { el.style.backgroundColor = 'white'; }, 400);
                }

                // Update the count display (percentage with count)
                var countEl = el.querySelector('.state-count');
                countEl.innerHTML = formatPctCount(count);

                delete existingMap[name];
            } else {
                // Create new row
                var div = document.createElement('div');
                div.className = 'state-row';
                div.setAttribute('data-category', name);
                div.style.top = topPos + 'px';
                div.style.opacity = '0';
                div.innerHTML = '<span class="state-rank">' + rank + '.</span>' +
                    '<span class="state-name">' + displayName + '</span>' +
                    '<span class="state-count">' + formatPctCount(count) + '</span>';
                wrapper.appendChild(div);
                setTimeout(function() { div.style.opacity = '1'; }, 50);
            }
        });

        // Fade out removed rows
        Object.values(existingMap).forEach(function(el) {
            el.style.opacity = '0';
            setTimeout(function() { el.remove(); }, 400);
        });
    } else {
        // Initial render with absolute positioning (same as state list)
        var html = '<div class="state-list">';
        categories.slice(0, 10).forEach(function(cat, index) {
            var name = cat.product || cat.name || 'Unknown';
            var displayName = shortenCategoryName(name);
            var count = cat.count || 0;
            var rank = index + 1;
            var topPos = index * rowHeight;
            html += '<div class="state-row" data-category="' + name + '" style="top:' + topPos + 'px">' +
                '<span class="state-rank">' + rank + '.</span>' +
                '<span class="state-name">' + displayName + '</span>' +
                '<span class="state-count">' + formatPctCount(count) + '</span>' +
                '</div>';
        });
        html += '</div>';
        container.innerHTML = html;
    }
}

// State abbreviation to full name mapping
export var stateNames = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia', 'PR': 'Puerto Rico', 'VI': 'Virgin Islands', 'GU': 'Guam'
};

export function getStateName(abbr) {
    return stateNames[abbr] || abbr;
}

export function renderBubbleChart(container, data, animate, showAsPercent, totalOverride) {
    if (!data || Object.keys(data).length === 0) { container.innerHTML = '<div class="viz-no-data">No data available</div>'; return; }
    // Show ALL states (no limit), sorted by value descending
    var items = Object.entries(data).map(function(e) { return { label: e[0], value: parseInt(e[1]) || 0 }; }).filter(function(i) { return i.value > 0; }).sort(function(a, b) { return b.value - a.value; });
    if (items.length === 0) { container.innerHTML = '<div class="viz-no-data">No data available</div>'; return; }

    // Calculate total for percentages (use override if provided for correct % when showing subset)
    var total = totalOverride || items.reduce(function(sum, item) { return sum + item.value; }, 0);

    // Helper to format value (percentage or raw number)
    function formatValue(value) {
        if (showAsPercent) {
            if (total === 0) return '0.0%';
            return ((value / total) * 100).toFixed(1) + '%';
        }
        return value.toLocaleString();
    }

    var rowHeight = 32; // Height of each row including gap

    // Check if we can animate existing rows
    var existingRows = container.querySelectorAll('.state-row[data-state]');
    var canAnimate = animate && existingRows.length > 0;

    if (canAnimate) {
        // Build map of existing rows
        var existingMap = {};
        existingRows.forEach(function(el) {
            existingMap[el.getAttribute('data-state')] = el;
        });

        var wrapper = container.querySelector('.state-list');

        // Update positions and values
        items.forEach(function(item, index) {
            var el = existingMap[item.label];
            var rank = index + 1;
            var fullName = getStateName(item.label);
            var topPos = index * rowHeight;

            if (el) {
                // Check if position is changing
                var currentTop = parseInt(el.style.top) || 0;
                var isMoving = currentTop !== topPos;

                // Animate existing row to new position
                el.style.top = topPos + 'px';
                el.querySelector('.state-rank').textContent = rank + '.';

                // If moving, animate the background color
                if (isMoving) {
                    el.style.backgroundColor = '#2fade3';
                    setTimeout(function() {
                        el.style.backgroundColor = 'white';
                    }, 400);
                }

                // Update the value display
                var countEl = el.querySelector('.state-count');
                countEl.textContent = formatValue(item.value);

                delete existingMap[item.label];
            } else {
                // Create new row
                var div = document.createElement('div');
                div.className = 'state-row';
                div.setAttribute('data-state', item.label);
                div.style.top = topPos + 'px';
                div.style.opacity = '0';
                div.innerHTML = '<span class="state-rank">' + rank + '.</span>' +
                    '<span class="state-name">' + fullName + '</span>' +
                    '<span class="state-count">' + formatValue(item.value) + '</span>';
                wrapper.appendChild(div);
                setTimeout(function() { div.style.opacity = '1'; }, 50);
            }
        });

        // Fade out removed rows
        Object.values(existingMap).forEach(function(el) {
            el.style.opacity = '0';
            setTimeout(function() { el.remove(); }, 400);
        });
    } else {
        // Initial render with absolute positioning
        var listHeight = items.length * rowHeight;
        var html = '<div class="state-list" style="height:' + listHeight + 'px">';
        items.forEach(function(item, index) {
            var rank = index + 1;
            var fullName = getStateName(item.label);
            var topPos = index * rowHeight;
            html += '<div class="state-row" data-state="' + item.label + '" style="top:' + topPos + 'px">' +
                '<span class="state-rank">' + rank + '.</span>' +
                '<span class="state-name">' + fullName + '</span>' +
                '<span class="state-count">' + formatValue(item.value) + '</span>' +
                '</div>';
        });
        html += '</div>';
        container.innerHTML = html;
    }

    // Update the state-list height for animation case too
    var stateList = container.querySelector('.state-list');
    if (stateList) {
        stateList.style.height = (items.length * rowHeight) + 'px';
    }
}

export function animateCount(el, from, to, duration) {
    var start = performance.now();
    var diff = to - from;

    function update(now) {
        var elapsed = now - start;
        var progress = Math.min(elapsed / duration, 1);
        // Ease out
        progress = 1 - Math.pow(1 - progress, 3);
        var current = Math.round(from + diff * progress);
        el.textContent = current.toLocaleString();
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    requestAnimationFrame(update);
}
