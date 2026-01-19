/**
 * Population Demographics Chart Module
 * Renders grouped bar charts showing population demographics over time
 */

window.PopulationDemographics = (function() {
    'use strict';

    // Race/ethnicity categories configuration
    const RACE_CATEGORIES = [
        { key: 'white', label: 'White', color: 'rgba(54, 162, 235, 0.8)', borderColor: 'rgba(54, 162, 235, 1)' },
        { key: 'black', label: 'Black', color: 'rgba(255, 99, 132, 0.8)', borderColor: 'rgba(255, 99, 132, 1)' },
        { key: 'hispanic', label: 'Hispanic', color: 'rgba(255, 206, 86, 0.8)', borderColor: 'rgba(255, 206, 86, 1)' },
        { key: 'asian', label: 'Asian', color: 'rgba(75, 192, 192, 0.8)', borderColor: 'rgba(75, 192, 192, 1)' },
        { key: 'native_american', label: 'Native American', color: 'rgba(153, 102, 255, 0.8)', borderColor: 'rgba(153, 102, 255, 1)' },
        { key: 'hawaiian_pi', label: 'Hawaiian/PI', color: 'rgba(255, 159, 64, 0.8)', borderColor: 'rgba(255, 159, 64, 1)' },
        { key: 'multi_racial', label: 'Multi-Racial', color: 'rgba(199, 199, 199, 0.8)', borderColor: 'rgba(199, 199, 199, 1)' }
    ];

    // Time period labels
    const TIME_PERIOD_LABELS = {
        '2010': '2010 Census',
        '2020': '2020 Census',
        'acs': 'Current ACS'
    };

    /**
     * Format number with commas for display
     * @param {number} num - Number to format
     * @returns {string} Formatted number string
     */
    function formatNumber(num) {
        if (num === null || num === undefined || isNaN(num)) return 'N/A';
        return Math.round(num).toLocaleString();
    }

    /**
     * Format percentage for display
     * @param {number} pct - Percentage to format
     * @returns {string} Formatted percentage string
     */
    function formatPercentage(pct) {
        if (pct === null || pct === undefined || isNaN(pct)) return 'N/A';
        return pct.toFixed(1) + '%';
    }

    /**
     * Get population count from percentage and total
     * @param {number} percentage - Percentage value
     * @param {number} totalPopulation - Total population
     * @returns {number} Population count
     */
    function getPopulationCount(percentage, totalPopulation) {
        if (percentage === null || percentage === undefined || isNaN(percentage)) return 0;
        if (totalPopulation === null || totalPopulation === undefined || isNaN(totalPopulation)) return 0;
        return Math.round((percentage / 100) * totalPopulation);
    }

    /**
     * Check if a race category should be included (>= 1% in any time period)
     * @param {string} raceKey - Race category key
     * @param {object} timePeriods - Time periods data
     * @returns {boolean} Whether to include the category
     */
    function shouldIncludeCategory(raceKey, timePeriods) {
        const percentageKey = raceKey + '_percentage';
        for (const period in timePeriods) {
            if (timePeriods.hasOwnProperty(period)) {
                const pct = timePeriods[period][percentageKey];
                if (pct !== null && pct !== undefined && pct >= 1) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * Get available time periods from data, sorted chronologically
     * @param {object} timePeriods - Time periods data object
     * @returns {string[]} Array of time period keys
     */
    function getAvailableTimePeriods(timePeriods) {
        const periods = Object.keys(timePeriods);
        // Sort: numeric years first (ascending), then 'acs' last
        return periods.sort((a, b) => {
            if (a === 'acs') return 1;
            if (b === 'acs') return -1;
            return parseInt(a) - parseInt(b);
        });
    }

    /**
     * Generate datasets for Chart.js
     * @param {object} timePeriods - Time periods data
     * @param {object[]} includedCategories - Categories to include
     * @param {string[]} availablePeriods - Available time periods
     * @returns {object[]} Chart.js datasets array
     */
    function generateDatasets(timePeriods, includedCategories, availablePeriods) {
        const datasets = [];

        availablePeriods.forEach((period, periodIndex) => {
            const periodData = timePeriods[period] || {};
            const totalPopulation = periodData.total_population || 0;

            const data = includedCategories.map(cat => {
                const pct = periodData[cat.key + '_percentage'];
                return getPopulationCount(pct, totalPopulation);
            });

            // Calculate color opacity based on time period (older = lighter)
            const opacityMultiplier = 0.5 + (periodIndex * 0.25);

            datasets.push({
                label: TIME_PERIOD_LABELS[period] || period,
                data: data,
                backgroundColor: includedCategories.map(cat => {
                    // Adjust opacity for each time period
                    return cat.color.replace(/[\d.]+\)$/, (opacityMultiplier) + ')');
                }),
                borderColor: includedCategories.map(cat => cat.borderColor),
                borderWidth: 1,
                // Store period info for tooltips
                _period: period,
                _timePeriods: timePeriods
            });
        });

        return datasets;
    }

    /**
     * Render population demographics chart
     * @param {string} chartId - Canvas element ID
     * @param {object} censusData - Census data object with county/area data
     * @param {object} options - Optional configuration options
     * @returns {Chart|null} Chart.js instance or null if failed
     */
    function renderPopulationDemographicsChart(chartId, censusData, options) {
        options = options || {};

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

        const areaName = options.areaName || areaKeys[0];
        const areaData = censusData[areaName];

        if (!areaData || !areaData.time_periods) {
            console.error('PopulationDemographics: Invalid data structure for area:', areaName);
            return null;
        }

        const timePeriods = areaData.time_periods;
        const availablePeriods = getAvailableTimePeriods(timePeriods);

        if (availablePeriods.length === 0) {
            console.error('PopulationDemographics: No time periods found in data');
            return null;
        }

        // Filter categories to only include those with >= 1% in any period
        const includedCategories = RACE_CATEGORIES.filter(cat =>
            shouldIncludeCategory(cat.key, timePeriods)
        );

        if (includedCategories.length === 0) {
            console.error('PopulationDemographics: No categories meet the 1% threshold');
            return null;
        }

        // Generate datasets
        const datasets = generateDatasets(timePeriods, includedCategories, availablePeriods);

        // Chart configuration
        const chartConfig = {
            type: 'bar',
            data: {
                labels: includedCategories.map(cat => cat.label),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: options.maintainAspectRatio !== false,
                plugins: {
                    title: {
                        display: !!options.title,
                        text: options.title || 'Population Demographics Over Time',
                        font: {
                            size: options.titleFontSize || 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: options.legendPosition || 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const datasetLabel = context.dataset.label || '';
                                const value = context.parsed.y;
                                const period = context.dataset._period;
                                const periodData = timePeriods[period] || {};
                                const totalPop = periodData.total_population || 0;

                                // Calculate percentage
                                const percentage = totalPop > 0 ? (value / totalPop) * 100 : 0;

                                return datasetLabel + ': ' + formatNumber(value) + ' (' + formatPercentage(percentage) + ')';
                            },
                            afterBody: function(tooltipItems) {
                                if (tooltipItems.length === 0) return '';

                                const item = tooltipItems[0];
                                const period = item.dataset._period;
                                const periodData = timePeriods[period] || {};
                                const totalPop = periodData.total_population;

                                if (totalPop) {
                                    return '\nTotal Population: ' + formatNumber(totalPop);
                                }
                                return '';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: options.xAxisLabel || 'Race/Ethnicity'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: options.yAxisLabel || 'Population'
                        },
                        ticks: {
                            callback: function(value) {
                                return formatNumber(value);
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
            return new Chart(ctx, chartConfig);
        } catch (error) {
            console.error('PopulationDemographics: Error creating chart:', error);
            return null;
        }
    }

    /**
     * Generate source caption for census data
     * @param {object} censusData - Census data object
     * @returns {string} Source caption string
     */
    function generateSourceCaption(censusData) {
        if (!censusData) return '';

        const areaKeys = Object.keys(censusData);
        if (areaKeys.length === 0) return '';

        const areaData = censusData[areaKeys[0]];
        if (!areaData || !areaData.time_periods) return '';

        const timePeriods = areaData.time_periods;
        const availablePeriods = getAvailableTimePeriods(timePeriods);

        const sources = [];

        availablePeriods.forEach(period => {
            if (period === '2010') {
                sources.push('2010 Decennial Census');
            } else if (period === '2020') {
                sources.push('2020 Decennial Census');
            } else if (period === 'acs') {
                // Try to get the ACS year from the data
                const acsData = timePeriods[period];
                const acsYear = acsData && acsData.year ? acsData.year : 'Current';
                sources.push(acsYear + ' American Community Survey 5-Year Estimates');
            } else if (/^\d{4}$/.test(period)) {
                sources.push(period + ' Census/ACS Data');
            }
        });

        if (sources.length === 0) return '';

        return 'Sources: ' + sources.join('; ') + '. U.S. Census Bureau.';
    }

    // Public API
    return {
        renderPopulationDemographicsChart: renderPopulationDemographicsChart,
        generateSourceCaption: generateSourceCaption,
        // Expose utilities for testing/extension
        formatNumber: formatNumber,
        formatPercentage: formatPercentage,
        RACE_CATEGORIES: RACE_CATEGORIES,
        TIME_PERIOD_LABELS: TIME_PERIOD_LABELS
    };

})();
