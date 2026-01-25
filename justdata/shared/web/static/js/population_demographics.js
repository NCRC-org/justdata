/**
 * Population Demographics Chart Module
 * Renders grouped bar charts showing population demographics over time
 * Layout: X-axis = time periods, bars grouped by race within each period
 * Matches LendSight report format
 */

window.PopulationDemographics = (function() {
    'use strict';

    // Race/ethnicity categories configuration with colors matching LendSight
    const RACE_GROUPS = [
        { key: 'white_percentage', label: 'White', bg: 'rgba(65, 105, 225, 0.7)', border: 'rgb(65, 105, 225)' },
        { key: 'black_percentage', label: 'Black', bg: 'rgba(34, 139, 34, 0.7)', border: 'rgb(34, 139, 34)' },
        { key: 'hispanic_percentage', label: 'Hispanic', bg: 'rgba(255, 140, 0, 0.7)', border: 'rgb(255, 140, 0)' },
        { key: 'asian_percentage', label: 'Asian', bg: 'rgba(220, 20, 60, 0.7)', border: 'rgb(220, 20, 60)' },
        { key: 'native_american_percentage', label: 'Native Am.', bg: 'rgba(148, 103, 189, 0.7)', border: 'rgb(148, 103, 189)' },
        { key: 'hopi_percentage', label: 'Hawaiian/PI', bg: 'rgba(23, 190, 207, 0.7)', border: 'rgb(23, 190, 207)' },
        { key: 'multi_racial_percentage', label: 'Multi-Racial', bg: 'rgba(188, 189, 34, 0.7)', border: 'rgb(188, 189, 34)' }
    ];

    /**
     * Format number with commas for display
     */
    function formatNumber(num) {
        if (num === null || num === undefined || isNaN(num)) return 'N/A';
        return Math.round(num).toLocaleString();
    }

    /**
     * Calculate population count from percentage and total
     */
    function getPopulationCount(totalPop, percentage) {
        if (!totalPop || !percentage) return 0;
        return Math.round((percentage / 100) * totalPop);
    }

    /**
     * Render population demographics chart (LendSight format)
     * X-axis: Time periods (2010 Census, 2020 Census, ACS)
     * Bars: Grouped by race within each time period
     *
     * @param {string} chartId - Canvas element ID
     * @param {object} censusData - Census data object with county/area data
     * @param {object} options - Optional configuration options
     * @returns {Chart|null} Chart.js instance or null if failed
     */
    function renderPopulationDemographicsChart(chartId, censusData, options) {
        options = options || {};

        console.log('[PopulationDemographics] Rendering chart with data:', censusData);

        const canvas = document.getElementById(chartId);
        if (!canvas) {
            console.error('PopulationDemographics: Canvas element not found:', chartId);
            return null;
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            console.error('PopulationDemographics: Could not get canvas context');
            return null;
        }

        // Get the first (and typically only) geographic area from the data
        const areaKeys = Object.keys(censusData);
        if (areaKeys.length === 0) {
            console.error('PopulationDemographics: No census data provided');
            return null;
        }

        const areaKey = areaKeys[0];
        const areaData = censusData[areaKey];

        if (!areaData || !areaData.time_periods) {
            console.error('PopulationDemographics: Invalid data structure for area:', areaKey);
            return null;
        }

        const timePeriods = areaData.time_periods;
        console.log('[PopulationDemographics] Time periods:', Object.keys(timePeriods));

        // Determine which race groups to show (>= 1% in any time period)
        const visibleGroups = RACE_GROUPS.filter(group => {
            const vals = [];
            if (timePeriods.census2010?.demographics) vals.push(timePeriods.census2010.demographics[group.key] || 0);
            if (timePeriods.census2020?.demographics) vals.push(timePeriods.census2020.demographics[group.key] || 0);
            if (timePeriods.acs?.demographics) vals.push(timePeriods.acs.demographics[group.key] || 0);
            return Math.max(...vals) >= 1;
        });

        console.log('[PopulationDemographics] Visible groups:', visibleGroups.map(g => g.label));

        if (visibleGroups.length === 0) {
            console.error('PopulationDemographics: No race groups meet the 1% threshold');
            return null;
        }

        // Track max population count for dynamic Y-axis scaling
        let maxPopCount = 0;

        // Build vintage labels with population totals (X-axis)
        const vintageLabels = [];
        const vintageData = {};

        if (timePeriods.census2010?.demographics) {
            const demo = timePeriods.census2010.demographics;
            const totalPop = demo.total_population || 0;
            const label = `2010 Census\n(Pop: ${totalPop.toLocaleString()})`;
            vintageLabels.push(label);
            vintageData['2010'] = { demo, totalPop, label: '2010 Census' };
        }

        if (timePeriods.census2020?.demographics) {
            const demo = timePeriods.census2020.demographics;
            const totalPop = demo.total_population || 0;
            const label = `2020 Census\n(Pop: ${totalPop.toLocaleString()})`;
            vintageLabels.push(label);
            vintageData['2020'] = { demo, totalPop, label: '2020 Census' };
        }

        if (timePeriods.acs?.demographics) {
            const acsLabel = timePeriods.acs.year || 'Current ACS';
            const demo = timePeriods.acs.demographics;
            const totalPop = demo.total_population || 0;
            const label = `${acsLabel}\n(Pop: ${totalPop.toLocaleString()})`;
            vintageLabels.push(label);
            vintageData['acs'] = { demo, totalPop, label: acsLabel };
        }

        console.log('[PopulationDemographics] Vintage labels:', vintageLabels);

        if (vintageLabels.length === 0) {
            console.error('PopulationDemographics: No time period data available');
            return null;
        }

        // Build datasets - one dataset per race, with data points for each vintage
        const datasets = [];
        const vintageKeys = Object.keys(vintageData);

        visibleGroups.forEach(group => {
            const dataPoints = [];
            const percentages = [];

            vintageKeys.forEach(key => {
                const { demo, totalPop } = vintageData[key];
                const pct = parseFloat((demo[group.key] || 0).toFixed(1));
                const popCount = getPopulationCount(totalPop, demo[group.key] || 0);
                if (popCount > maxPopCount) maxPopCount = popCount;
                dataPoints.push(popCount);  // Use raw population count as data point
                percentages.push(pct);      // Store percentage for tooltip
            });

            datasets.push({
                label: group.label,
                data: dataPoints,
                backgroundColor: group.bg,
                borderColor: group.border,
                borderWidth: 1,
                percentages: percentages  // Store percentages for tooltip
            });
        });

        // Calculate dynamic Y-axis max: 10% above highest population count, rounded to nice number
        const yAxisMax = Math.ceil((maxPopCount * 1.10) / 10000) * 10000 || 10000;

        // Get area name for title
        const areaName = areaData.county_name || options.areaName || areaKey;

        // Chart configuration (matches LendSight format)
        const chartConfig = {
            type: 'bar',
            data: {
                labels: vintageLabels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: options.maintainAspectRatio !== false,
                plugins: {
                    legend: {
                        display: true,
                        position: options.legendPosition || 'top'
                    },
                    title: {
                        display: !!options.showTitle,
                        text: options.title || `Population Demographics Over Time: ${areaName}`,
                        font: { size: 16, weight: 'bold' }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const dataset = context.dataset;
                                const count = context.raw;  // Raw data is population count
                                const percentage = dataset.percentages ? dataset.percentages[context.dataIndex] : 0;
                                return `${dataset.label}: ${count.toLocaleString()} persons (${percentage}%)`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: yAxisMax,
                        title: {
                            display: true,
                            text: options.yAxisLabel || 'Population'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString();
                            }
                        }
                    }
                }
            }
        };

        // Destroy existing chart if it exists
        if (window.Chart && Chart.getChart && Chart.getChart(chartId)) {
            Chart.getChart(chartId).destroy();
        }

        // Create and return the chart
        try {
            console.log('[PopulationDemographics] Creating chart with', datasets.length, 'datasets');
            return new Chart(ctx, chartConfig);
        } catch (error) {
            console.error('PopulationDemographics: Error creating chart:', error);
            return null;
        }
    }

    /**
     * Generate source caption for census data
     * @param {object} censusData - Census data object
     * @param {string} areaName - Optional area name to include
     * @returns {string} Source caption string
     */
    function generateSourceCaption(censusData, areaName) {
        if (!censusData) return '';

        const areaKeys = Object.keys(censusData);
        if (areaKeys.length === 0) return '';

        const areaData = censusData[areaKeys[0]];
        if (!areaData || !areaData.time_periods) return '';

        const timePeriods = areaData.time_periods;
        const sources = [];

        if (timePeriods.census2010) sources.push('2010 Decennial Census');
        if (timePeriods.census2020) sources.push('2020 Decennial Census');
        if (timePeriods.acs) sources.push('American Community Survey');

        if (sources.length === 0) return '';

        const area = areaName || areaData.county_name || areaKeys[0];
        return `<strong>Source:</strong> U.S. Census Bureau - ${sources.join(', ')}. Population figures represent ${area}.`;
    }

    // Public API
    return {
        renderPopulationDemographicsChart: renderPopulationDemographicsChart,
        generateSourceCaption: generateSourceCaption,
        formatNumber: formatNumber,
        RACE_GROUPS: RACE_GROUPS
    };

})();
