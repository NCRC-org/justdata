/**
 * LenderProfile Intelligence Report V2
 * Client-side rendering for intelligence-focused layout
 */

import {
    updateElement,
    updateGrowthElement,
    formatNumber,
    formatCurrency,
    formatCurrencyShort,
    formatDate,
    escapeHtml,
    exportToPDF,
} from './report/lenderprofile_report_utils.js';
import {
    copyEntityInfo,
    buildEntityNode,
    initializeCorporateStructure,
    buildReportLink,
} from './report/lenderprofile_report_corporate_structure.js';
import {
    initializeAISummary,
    parseBulletFindings,
    markdownToHtml,
    initializeSECFilingsAnalysis,
    createTruncatedSummary,
    initializeSummaryModal,
} from './report/lenderprofile_report_summary.js';
// Charts module owns its own DOMContentLoaded handler that kicks off all
// visualizations after a short setTimeout — importing it here is sufficient
// to register that handler.
import './report/lenderprofile_report_charts.js';

document.addEventListener('DOMContentLoaded', function() {
    const reportData = window.reportData;
    console.log('Report data:', reportData);
    if (!reportData) {
        console.warn('No report data available');
        return;
    }

    // Initialize all sections
    console.log('Initializing header with:', reportData.header);
    initializeHeader(reportData);
    initializeBusinessStrategy(reportData);
    initializeRiskFactors(reportData);
    initializeFinancialPerformance(reportData);
    initializeMergerActivity(reportData);
    initializeRegulatoryRisk(reportData);
    initializeCommunityInvestment(reportData);
    initializeBranchNetwork(reportData);
    initializeLendingFootprint(reportData);
    initializeLeadership(reportData);
    initializeCongressionalTrading(reportData);
    initializeCorporateStructure(reportData);
    initializeNews(reportData);
    initializeSeekingAlpha(reportData);
    initializeAISummary(reportData);
    initializeSECFilingsAnalysis(reportData);

    // Export button
    document.getElementById('export-pdf-btn')?.addEventListener('click', exportToPDF);
});

// =============================================================================
// HEADER
// =============================================================================

export function initializeHeader(data) {
    const header = data.header || {};

    // Update inst-name but preserve headquarters span
    const instNameEl = document.getElementById('inst-name');
    if (instNameEl && header.institution_name) {
        const hqSpan = instNameEl.querySelector('.inst-headquarters');
        if (hqSpan) {
            // Preserve the headquarters span
            instNameEl.childNodes[0].textContent = header.institution_name + ' ';
        } else {
            instNameEl.textContent = header.institution_name;
        }
    }

    // Update headquarters
    updateElement('inst-headquarters', header.headquarters);

    updateElement('ticker', header.ticker);
    updateElement('inst-type', header.institution_type);
    updateElement('total-assets', header.total_assets);
    updateElement('cra-rating', header.cra_rating);
    updateElement('stock-price', header.stock_price);

    if (header.identifiers) {
        updateElement('fdic-cert', header.identifiers.fdic_cert);
    }
}

// =============================================================================
// BUSINESS STRATEGY (SEC 10-K)
// =============================================================================

export function initializeBusinessStrategy(data) {
    const strategy = data.business_strategy || {};
    if (!strategy.has_data) return;

    // Business segments
    const segmentsList = document.querySelector('#business-segments .segment-list');
    if (segmentsList && Array.isArray(strategy.business_segments) && strategy.business_segments.length > 0) {
        segmentsList.innerHTML = strategy.business_segments
            .map(seg => `<span class="segment-badge">${escapeHtml(seg.name)}</span>`)
            .join('');
    }

    // Growth areas
    const growthList = document.querySelector('#growth-areas .insight-list');
    if (growthList && Array.isArray(strategy.growth_areas) && strategy.growth_areas.length > 0) {
        growthList.innerHTML = strategy.growth_areas
            .map(item => `<li>${escapeHtml(item)}</li>`)
            .join('');
    }

    // Contraction areas
    const contractionList = document.querySelector('#contraction-areas .insight-list');
    if (contractionList && Array.isArray(strategy.contraction_areas) && strategy.contraction_areas.length > 0) {
        contractionList.innerHTML = strategy.contraction_areas
            .map(item => `<li>${escapeHtml(item)}</li>`)
            .join('');
    }
}

// =============================================================================
// RISK FACTORS (SEC 10-K Item 1A)
// =============================================================================

export function initializeRiskFactors(data) {
    const risks = data.risk_factors || {};
    if (!risks.has_data) return;

    const riskGrid = document.getElementById('risk-categories');
    if (riskGrid && risks.risk_categories && typeof risks.risk_categories === 'object') {
        const categoryLabels = {
            'credit_risk': 'Credit Risk',
            'market_risk': 'Market Risk',
            'operational_risk': 'Operational Risk',
            'regulatory_risk': 'Regulatory Risk',
            'competitive_risk': 'Competitive Risk',
            'economic_risk': 'Economic Risk'
        };

        const entries = Object.entries(risks.risk_categories);
        if (entries.length > 0) {
            riskGrid.innerHTML = entries
                .sort((a, b) => b[1] - a[1])
                .map(([key, count]) => `
                    <span class="risk-badge ${key}">
                        ${categoryLabels[key] || key}
                        <span class="risk-count">${count}</span>
                    </span>
                `).join('');
        }
    }
}

// =============================================================================
// FINANCIAL PERFORMANCE - Total Assets & Deposits (5 Year Trend)
// =============================================================================

export function initializeFinancialPerformance(data) {
    const financial = data.financial_performance || {};
    const section = document.getElementById('fdic-financials-section');

    // Hide entire section if no FDIC financial data
    if (!financial.has_data) {
        if (section) section.style.display = 'none';
        return;
    }

    // Financial trend chart - Dual axis for Assets and Deposits (5 years)
    const canvas = document.getElementById('financial-chart');
    // Use trends_chronological (already in chronological order) or fall back to reversing trends
    const trendData = financial.trends_chronological || (financial.trends ? [...financial.trends].reverse() : []);

    if (canvas && Array.isArray(trendData) && trendData.length > 0) {
        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: trendData.map((t, idx) => {
                    // Show year label only at Q1, other quarters get empty label (hash marks only)
                    if (t.period && t.period.length >= 7) {
                        const year = t.period.substring(0, 4);
                        const month = parseInt(t.period.substring(5, 7), 10);
                        const isQ1 = month >= 1 && month <= 3;

                        // Check if this is the first occurrence of this year in the data
                        const prevYear = idx > 0 ? trendData[idx-1].period?.substring(0, 4) : null;
                        const isFirstOfYear = year !== prevYear;

                        // Show year label only at Q1 or first occurrence of year
                        if (isQ1 || isFirstOfYear) {
                            return year;
                        }
                        return '';  // Empty label for Q2, Q3, Q4 (grid shows hash marks)
                    }
                    // Handle year-only format (e.g., "2024")
                    if (t.period && t.period.length === 4) {
                        return t.period;
                    }
                    return t.period;
                }),
                // Store full period data for tooltips
                _fullPeriods: trendData.map(t => t.period),
                datasets: [
                    {
                        label: 'Total Assets',
                        data: trendData.map(t => t.assets),
                        borderColor: '#003366',
                        backgroundColor: 'rgba(0, 51, 102, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.3,
                        yAxisID: 'y-assets',
                        pointRadius: 2,
                        pointHoverRadius: 5
                    },
                    {
                        label: 'Total Deposits',
                        data: trendData.map(t => t.deposits),
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.3,
                        yAxisID: 'y-deposits',
                        pointRadius: 2,
                        pointHoverRadius: 5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                // Show full month and year in tooltip title
                                const idx = context[0].dataIndex;
                                const fullPeriod = context[0].chart.data._fullPeriods?.[idx];
                                if (fullPeriod && fullPeriod.length >= 7) {
                                    const date = new Date(fullPeriod + '-01');
                                    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                                }
                                return fullPeriod || context[0].label;
                            },
                            label: function(context) {
                                return context.dataset.label + ': ' + formatCurrencyShort(context.raw);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    'y-assets': {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Total Assets',
                            color: '#003366'
                        },
                        ticks: {
                            color: '#003366',
                            callback: value => formatCurrencyShort(value)
                        },
                        grid: {
                            drawOnChartArea: true
                        }
                    },
                    'y-deposits': {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Total Deposits',
                            color: '#28a745'
                        },
                        ticks: {
                            color: '#28a745',
                            callback: value => formatCurrencyShort(value)
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
    }
}


// =============================================================================
// M&A ACTIVITY
// =============================================================================

export function initializeMergerActivity(data) {
    const mergers = data.merger_activity || {};

    // Pending acquisitions
    const pendingList = document.querySelector('#pending-mergers .merger-list');
    const noPending = document.getElementById('no-pending');

    if (pendingList && Array.isArray(mergers.pending_acquisitions) && mergers.pending_acquisitions.length > 0) {
        if (noPending) noPending.style.display = 'none';
        pendingList.innerHTML = mergers.pending_acquisitions
            .map(m => `
                <div class="merger-item pending">
                    <span class="merger-target">${escapeHtml(m.target || m.name)}</span>
                    <span class="merger-date">${m.date || 'Pending'}</span>
                </div>
            `).join('');
    }

    // Historical acquisitions
    const historicalList = document.querySelector('#historical-mergers .merger-list');
    const noHistorical = document.getElementById('no-historical');

    if (historicalList && Array.isArray(mergers.historical_acquisitions) && mergers.historical_acquisitions.length > 0) {
        if (noHistorical) noHistorical.style.display = 'none';
        historicalList.innerHTML = mergers.historical_acquisitions
            .map(m => `
                <div class="merger-item">
                    <span class="merger-target">${escapeHtml(m.target || m.name)}</span>
                    <span class="merger-year">${m.year || '--'}</span>
                </div>
            `).join('');
    }
}

// =============================================================================
// REGULATORY RISK
// =============================================================================

export function initializeRegulatoryRisk(data) {
    const regulatory = data.regulatory_risk || {};

    // Enforcement
    if (regulatory.enforcement) {
        updateElement('enforcement-count', regulatory.enforcement.total_actions);
        updateElement('enforcement-recent', regulatory.enforcement.recent_count);

        const enfList = document.getElementById('enforcement-list');
        if (enfList && Array.isArray(regulatory.enforcement.recent_actions) && regulatory.enforcement.recent_actions.length > 0) {
            enfList.innerHTML = regulatory.enforcement.recent_actions
                .slice(0, 5)
                .map(a => `
                    <div class="enforcement-item">
                        <span class="enf-agency">${escapeHtml(a.agency || 'Unknown')}</span>
                        <span class="enf-date">${a.date || '--'}</span>
                        <span class="enf-type">${escapeHtml(a.type || '')}</span>
                    </div>
                `).join('');
        }
    }

    // Complaints
    if (regulatory.complaints) {
        updateElement('complaint-total', formatNumber(regulatory.complaints.total));

        const trendEl = document.getElementById('complaint-trend');
        if (trendEl) {
            trendEl.textContent = regulatory.complaints.trend;
            trendEl.className = 'trend-badge ' + regulatory.complaints.trend;
        }

        // Yearly breakdown
        const yearlyDiv = document.getElementById('complaint-yearly');
        if (yearlyDiv && regulatory.complaints.by_year) {
            const years = Object.keys(regulatory.complaints.by_year).sort();
            if (years.length > 0) {
                yearlyDiv.innerHTML = '<div class="yearly-header">Complaints by Year:</div>' +
                    years.map(year => {
                        const count = regulatory.complaints.by_year[year];
                        return `<span class="year-count">${year}: ${formatNumber(count)}</span>`;
                    }).join('');
            }
        }

        // Top categories (products)
        const categoriesDiv = document.getElementById('complaint-categories');
        if (categoriesDiv && Array.isArray(regulatory.complaints.main_categories) && regulatory.complaints.main_categories.length > 0) {
            categoriesDiv.innerHTML = '<div class="categories-header">Top Categories:</div>' +
                regulatory.complaints.main_categories.map(cat => {
                    const name = cat.product || cat.name || 'Unknown';
                    const count = cat.count || 0;
                    const pct = cat.percentage ? cat.percentage.toFixed(1) : '0';
                    return `<div class="category-item"><span class="cat-name">${escapeHtml(name)}</span><span class="cat-count">${formatNumber(count)} (${pct}%)</span></div>`;
                }).join('');
        }

        // Issues (main_issues) - fallback display
        const issuesDiv = document.getElementById('complaint-issues');
        if (issuesDiv && Array.isArray(regulatory.complaints.main_issues) && regulatory.complaints.main_issues.length > 0) {
            issuesDiv.innerHTML = regulatory.complaints.main_issues
                .map(issue => {
                    const name = typeof issue === 'object' ? (issue.name || issue.issue) : issue;
                    const count = typeof issue === 'object' ? issue.count : '';
                    return `<span class="issue-badge">${escapeHtml(name)} ${count ? '(' + formatNumber(count) + ')' : ''}</span>`;
                }).join('');
        }
    }

    // CRA
    if (regulatory.cra) {
        updateElement('cra-rating-display', regulatory.cra.current_rating);
        updateElement('cra-exam-date', regulatory.cra.exam_date || '--');
    }
}

// =============================================================================
// COMMUNITY INVESTMENT
// =============================================================================

export function initializeCommunityInvestment(data) {
    const community = data.community_investment || {};

    if (!community.has_data) return;

    // CRA Rating
    if (community.cra) {
        const ratingEl = document.getElementById('community-cra-rating');
        if (ratingEl && community.cra.rating) {
            ratingEl.textContent = community.cra.rating;
            // Add rating class for styling
            ratingEl.className = 'cra-rating-badge ' + community.cra.rating.toLowerCase().replace(/\s+/g, '-');
        }
        updateElement('community-cra-date', community.cra.exam_date || '--');
    }

    // Community Development metrics
    if (community.community_development) {
        updateElement('cd-loans', community.community_development.loans || '--');
        updateElement('cd-investments', community.community_development.investments || '--');
    }

    // Affordable Housing (XBRL data)
    if (community.affordable_housing) {
        const ahSection = document.getElementById('affordable-housing-section');
        const taxCredits = community.affordable_housing.tax_credits;
        const investmentCredits = community.affordable_housing.investment_tax_credit;

        // Show section if we have any affordable housing data
        if (taxCredits || investmentCredits) {
            if (ahSection) {
                ahSection.style.display = 'block';
            }
            updateElement('ah-tax-credits', taxCredits || '--');
            updateElement('ah-investment-credits', investmentCredits || '--');
        }
    }

    // Philanthropy
    if (community.philanthropy) {
        updateElement('charitable-contributions', community.philanthropy.charitable_contributions || '--');

        // Foundation info
        if (community.philanthropy.foundation && community.philanthropy.foundation.name) {
            const foundationDiv = document.getElementById('foundation-info');
            if (foundationDiv) {
                foundationDiv.style.display = 'flex';
                updateElement('foundation-name', community.philanthropy.foundation.name);
                updateElement('foundation-assets', community.philanthropy.foundation.assets || '--');
            }
        }
    }

    // Community Commitments
    if (Array.isArray(community.commitments) && community.commitments.length > 0) {
        const section = document.getElementById('commitments-section');
        const list = document.getElementById('commitments-list');

        if (section && list) {
            section.style.display = 'block';
            list.innerHTML = community.commitments.map(c => `
                <div class="commitment-item">
                    <span class="commitment-amount">${escapeHtml(c.amount || '--')}</span>
                    <span class="commitment-purpose">${escapeHtml(c.purpose || '')}</span>
                </div>
            `).join('');
        }
    }
}

// =============================================================================
// BRANCH NETWORK
// =============================================================================

export function initializeBranchNetwork(data) {
    const branches = data.branch_network || {};

    updateElement('branch-count', branches.total_branches ? `${formatNumber(branches.total_branches)} branches` : '-- branches');

    // Top states
    const summaryDiv = document.getElementById('branch-summary');
    if (summaryDiv && branches.top_states && typeof branches.top_states === 'object') {
        const entries = Object.entries(branches.top_states);
        if (entries.length > 0) {
            summaryDiv.innerHTML = entries
                .map(([state, count]) => `<span class="branch-state"><strong>${state}</strong>: ${count}</span>`)
                .join('');
        }
    }

    // Trend
    const trendDiv = document.getElementById('branch-trend');
    if (trendDiv && branches.trends) {
        const trend = branches.trends.trend || 'stable';
        trendDiv.innerHTML = `<span class="branch-trend-indicator ${trend}">
            <i class="fas fa-${trend === 'expanding' ? 'arrow-up' : (trend === 'contracting' ? 'arrow-down' : 'minus')}"></i>
            ${trend.charAt(0).toUpperCase() + trend.slice(1)}
        </span>`;
    }
}

// =============================================================================
// LENDING FOOTPRINT (HMDA)
// =============================================================================

export function initializeLendingFootprint(data) {
    const footprint = data.lending_footprint || {};

    // Update year badge
    if (footprint.year) {
        updateElement('footprint-year', `HMDA ${footprint.year}`);
    }

    // Description
    const descDiv = document.getElementById('footprint-description');
    if (descDiv && footprint.footprint_description) {
        descDiv.textContent = footprint.footprint_description;
    } else if (descDiv) {
        descDiv.style.display = 'none';
    }

    // Top metros
    const metroList = document.querySelector('#top-metros .metro-list');
    if (metroList && Array.isArray(footprint.top_metros) && footprint.top_metros.length > 0) {
        metroList.innerHTML = footprint.top_metros
            .map(metro => `
                <div class="metro-item">
                    <span class="metro-name">${escapeHtml(metro.name)}</span>
                    <div class="metro-stats">
                        <span class="metro-apps">${formatNumber(metro.applications)} apps</span>
                        <span class="metro-pct">${metro.pct_of_total}%</span>
                    </div>
                </div>
            `).join('');
    } else if (metroList) {
        metroList.innerHTML = '<p class="no-data">No lending data available</p>';
    }

    // Concentration metrics
    const concDiv = document.getElementById('footprint-concentration');
    if (concDiv && footprint.concentration) {
        const conc = footprint.concentration;
        let scopeClass = 'local';
        let scopeLabel = 'Local';

        if (conc.is_national) {
            scopeClass = 'national';
            scopeLabel = 'National';
        } else if (footprint.total_states >= 20) {
            scopeClass = 'regional';
            scopeLabel = 'Multi-Regional';
        } else if (footprint.total_states >= 5) {
            scopeClass = 'regional';
            scopeLabel = 'Regional';
        }

        concDiv.innerHTML = `
            <div class="conc-item">
                <div class="conc-value">${footprint.total_states || 0}</div>
                <div class="conc-label">States</div>
            </div>
            <div class="conc-item">
                <div class="conc-value">${conc.top_5_metros_pct || 0}%</div>
                <div class="conc-label">Top 5 Markets</div>
            </div>
            <div class="conc-item">
                <span class="conc-badge ${scopeClass}">${scopeLabel}</span>
            </div>
        `;
    }
}

// =============================================================================
// LEADERSHIP
// =============================================================================

export function initializeLeadership(data) {
    const leadership = data.leadership || {};

    // CEO
    if (leadership.ceo) {
        updateElement('ceo-name', leadership.ceo.name);
        updateElement('ceo-title', leadership.ceo.title);
        updateElement('ceo-comp', `Total Comp: ${leadership.ceo.total_compensation || '--'}`);
    }

    // Board - hide if no data
    const boardSummary = document.getElementById('board-summary');
    if (leadership.board_size && leadership.board_size > 0) {
        updateElement('board-size', leadership.board_size);
    } else {
        // Hide the board section entirely if no board size data
        if (boardSummary) boardSummary.style.display = 'none';
    }

    // Executives table
    const tbody = document.getElementById('executives-tbody');
    if (tbody && Array.isArray(leadership.top_executives) && leadership.top_executives.length > 0) {
        // Dedupe by name and filter out Board of Directors members
        const seenNames = new Set();
        const filteredExecs = leadership.top_executives.filter(exec => {
            const name = (exec.name || '').trim().toLowerCase();
            const title = (exec.title || '').toLowerCase();

            // Skip if already seen
            if (seenNames.has(name)) return false;
            seenNames.add(name);

            // Skip Board of Directors members
            if (title.includes('board of director') || title.includes('director') && !title.includes('executive') && !title.includes('chief') && !title.includes('president') && !title.includes('officer')) {
                return false;
            }

            return true;
        });

        tbody.innerHTML = filteredExecs
            .map(exec => `
                <tr>
                    <td>${escapeHtml(exec.name)}</td>
                    <td>${escapeHtml(exec.title)}</td>
                    <td>${exec.total || '--'}</td>
                </tr>
            `).join('');
    }
}

// =============================================================================
// CONGRESSIONAL TRADING
// =============================================================================

export function initializeCongressionalTrading(data) {
    const congress = data.congressional_trading || {};

    // Timeframe display
    const timeframeDiv = document.getElementById('congress-timeframe');
    if (timeframeDiv) {
        if (congress.date_range) {
            timeframeDiv.innerHTML = `<i class="fas fa-calendar-alt"></i> ${congress.date_range}`;
        } else if (!congress.has_data) {
            timeframeDiv.textContent = 'No data available';
        } else {
            timeframeDiv.textContent = 'Last 2 years';
        }
    }

    // AI Sentiment Summary (at the top of the section)
    const aiSummaryDiv = document.getElementById('congress-ai-summary');
    if (aiSummaryDiv) {
        if (congress.ai_sentiment_summary && congress.ai_sentiment_summary.trim()) {
            aiSummaryDiv.innerHTML = congress.ai_sentiment_summary;
            aiSummaryDiv.style.display = 'block';
        } else {
            aiSummaryDiv.style.display = 'none';
        }
    }

    // Politician Profiles with committees
    const profilesList = document.getElementById('politician-profiles-list');
    if (profilesList) {
        const profiles = congress.politician_profiles || congress.notable_traders || [];
        const MAX_VISIBLE = 10;
        const hasMore = profiles.length > MAX_VISIBLE;

        if (profiles && profiles.length > 0) {
            const renderProfile = (pol, index) => {
                // Status badge styling
                let statusClass = '';
                let statusIcon = '';
                switch (pol.status) {
                    case 'Accumulating':
                        statusClass = 'status-accumulating';
                        statusIcon = '<i class="fas fa-arrow-up" style="color: #28a745;"></i>';
                        break;
                    case 'Likely Holder':
                        statusClass = 'status-holder';
                        statusIcon = '<i class="fas fa-hand-holding-usd" style="color: #17a2b8;"></i>';
                        break;
                    case 'Divesting':
                    case 'Exited':
                        statusClass = 'status-divesting';
                        statusIcon = '<i class="fas fa-arrow-down" style="color: #dc3545;"></i>';
                        break;
                    default:
                        statusClass = 'status-active';
                        statusIcon = '<i class="fas fa-exchange-alt" style="color: #6c757d;"></i>';
                }

                // Committees display
                let committeesHtml = '';
                if (pol.committees && pol.committees.length > 0) {
                    const shortCommittees = pol.committees.map(c =>
                        c.replace('House Committee on ', '')
                         .replace('Senate Committee on ', '')
                         .replace('Committee on ', '')
                    ).slice(0, 2);
                    committeesHtml = `<div class="pol-committees" style="font-size: 0.75em; color: #666; margin-top: 2px;">
                        <i class="fas fa-users" style="margin-right: 3px;"></i>${shortCommittees.join(', ')}
                    </div>`;
                }

                // Finance committee flag
                let financeFlag = '';
                if (pol.is_finance_member) {
                    financeFlag = `<span style="background: #fff3cd; color: #856404; padding: 1px 5px; border-radius: 3px; font-size: 0.7em; margin-left: 5px;">
                        <i class="fas fa-university"></i> Finance
                    </span>`;
                }

                // Trade counts
                const tradeInfo = `${pol.purchases} buy${pol.purchases !== 1 ? 's' : ''}, ${pol.sales} sell${pol.sales !== 1 ? 's' : ''}`;

                const hiddenClass = index >= MAX_VISIBLE ? 'congress-hidden' : '';
                return `
                    <div class="politician-profile ${hiddenClass}" style="padding: 8px 0; border-bottom: 1px solid #eee;${index >= MAX_VISIBLE ? ' display: none;' : ''}">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div class="pol-info" style="flex: 1;">
                                <div class="pol-name" style="font-weight: 600; font-size: 0.9em;">
                                    ${escapeHtml(pol.name)}${financeFlag}
                                </div>
                                <div class="pol-details" style="font-size: 0.8em; color: #555;">
                                    ${escapeHtml(pol.chamber || '')} ${pol.party ? `(${pol.party})` : ''} - ${escapeHtml(pol.state || '')}
                                </div>
                                ${committeesHtml}
                            </div>
                            <div class="pol-status" style="text-align: right;">
                                <div class="status-badge ${statusClass}" style="font-size: 0.75em; margin-bottom: 2px;">
                                    ${statusIcon} ${pol.status}
                                </div>
                                <div class="trade-count" style="font-size: 0.7em; color: #666;">
                                    ${tradeInfo}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            };

            // Render all profiles
            let html = profiles.map((pol, i) => renderProfile(pol, i)).join('');

            // Add expand button if there are more than MAX_VISIBLE
            if (hasMore) {
                html += `
                    <div class="expand-btn-container" style="text-align: center; padding: 10px 0;">
                        <button id="expand-congress-btn" class="btn-expand" style="background: #f8f9fa; border: 1px solid #ddd; padding: 5px 15px; border-radius: 4px; cursor: pointer; font-size: 0.85em;">
                            <i class="fas fa-chevron-down"></i> Show ${profiles.length - MAX_VISIBLE} more
                        </button>
                    </div>
                `;
            }

            profilesList.innerHTML = html;

            // Add expand button click handler
            if (hasMore) {
                const expandBtn = document.getElementById('expand-congress-btn');
                if (expandBtn) {
                    expandBtn.addEventListener('click', function() {
                        const hiddenItems = profilesList.querySelectorAll('.congress-hidden');
                        const isExpanded = expandBtn.dataset.expanded === 'true';

                        hiddenItems.forEach(item => {
                            item.style.display = isExpanded ? 'none' : 'block';
                        });

                        if (isExpanded) {
                            expandBtn.innerHTML = `<i class="fas fa-chevron-down"></i> Show ${profiles.length - MAX_VISIBLE} more`;
                            expandBtn.dataset.expanded = 'false';
                        } else {
                            expandBtn.innerHTML = `<i class="fas fa-chevron-up"></i> Show less`;
                            expandBtn.dataset.expanded = 'true';
                        }
                    });
                }
            }
        } else if (!congress.has_data) {
            profilesList.innerHTML = '<p class="no-data">No congressional trading data available</p>';
        } else {
            profilesList.innerHTML = '<p class="no-data">No trading activity found</p>';
        }
    }
}


// =============================================================================
// NEWS
// =============================================================================

export function initializeNews(data) {
    const news = data.recent_news || {};

    // Category counts
    if (news.by_category) {
        updateElement('news-regulatory', `${news.by_category.regulatory || 0} Regulatory`);
        updateElement('news-merger', `${news.by_category.merger || 0} M&A`);
        updateElement('news-leadership', `${news.by_category.leadership || 0} Leadership`);
    }

    const feedDiv = document.getElementById('news-feed');
    if (!feedDiv) return;

    if (!news.has_data || !Array.isArray(news.articles) || news.articles.length === 0) {
        feedDiv.innerHTML = '<p class="no-data">No recent news available.</p>';
        return;
    }

    feedDiv.innerHTML = news.articles.map(article => `
        <div class="news-item ${article.category || ''}">
            <span class="news-category-tag ${article.category || ''}">${article.category || 'other'}</span>
            <div class="news-title">
                <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener">${escapeHtml(article.title)}</a>
            </div>
            ${article.summary ? `<div class="news-summary">${escapeHtml(article.summary)}</div>` : ''}
            <div class="news-meta">
                ${escapeHtml(article.source)} | ${formatDate(article.published_at)}
            </div>
        </div>
    `).join('');
}

// =============================================================================
// SEEKING ALPHA
// =============================================================================

export function initializeSeekingAlpha(data) {
    const sa = data.seeking_alpha || {};
    const section = document.getElementById('seeking-alpha-section');
    const articlesDiv = document.getElementById('sa-articles');
    const ratingsDiv = document.getElementById('sa-ratings');

    if (!section || !articlesDiv) return;

    // Show section only if we have data
    if (!sa.has_data) {
        section.style.display = 'none';
        return;
    }

    // Show ratings if available
    if (ratingsDiv && (sa.quant_rating || sa.wall_st_rating)) {
        ratingsDiv.style.display = 'block';
        const quantEl = document.getElementById('sa-quant-rating');
        const wallStEl = document.getElementById('sa-wallst-rating');
        if (quantEl && sa.quant_rating) {
            quantEl.textContent = `Quant Rating: ${sa.quant_rating}`;
            quantEl.style.display = 'inline-block';
        }
        if (wallStEl && sa.wall_st_rating) {
            wallStEl.textContent = `Wall St Rating: ${sa.wall_st_rating}`;
            wallStEl.style.display = 'inline-block';
        }
    }

    // Show articles
    if (!Array.isArray(sa.articles) || sa.articles.length === 0) {
        articlesDiv.innerHTML = '<p class="no-data">No Seeking Alpha articles available.</p>';
        return;
    }

    articlesDiv.innerHTML = sa.articles.map(article => `
        <div class="news-item sa-article">
            <div class="news-title">
                <a href="${escapeHtml(article.url || '#')}" target="_blank" rel="noopener">${escapeHtml(article.title || 'Untitled')}</a>
            </div>
            ${article.summary ? `<div class="news-summary">${escapeHtml(article.summary)}</div>` : ''}
            <div class="news-meta">
                ${escapeHtml(article.source || 'Seeking Alpha')} ${article.published_at ? '| ' + formatDate(article.published_at) : ''}
            </div>
        </div>
    `).join('');
}



// ----------------------------------------------------------------------------
// Window exports for inline onclick handlers — remove when onclick= is replaced
// with event listeners. Only includes symbols referenced from inline HTML event
// attributes (in templates and in HTML strings rendered by JS), nothing else.
// ----------------------------------------------------------------------------
window.copyEntityInfo = copyEntityInfo;
