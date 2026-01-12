/**
 * LenderProfile Intelligence Report V2
 * Client-side rendering for intelligence-focused layout
 */

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

function initializeHeader(data) {
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

function initializeBusinessStrategy(data) {
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

function initializeRiskFactors(data) {
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

function initializeFinancialPerformance(data) {
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

function updateGrowthElement(id, value) {
    const el = document.getElementById(id);
    if (el && value !== null && value !== undefined) {
        const formatted = value > 0 ? `+${value.toFixed(1)}%` : `${value.toFixed(1)}%`;
        el.textContent = formatted;
        el.className = 'growth-val ' + (value > 0 ? 'positive' : (value < 0 ? 'negative' : ''));
    }
}

// =============================================================================
// M&A ACTIVITY
// =============================================================================

function initializeMergerActivity(data) {
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

function initializeRegulatoryRisk(data) {
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

function initializeCommunityInvestment(data) {
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

function initializeBranchNetwork(data) {
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

function initializeLendingFootprint(data) {
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

function initializeLeadership(data) {
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

function initializeCongressionalTrading(data) {
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
// CORPORATE STRUCTURE
// =============================================================================

/**
 * Copy entity info to clipboard (name, LEI, GLEIF URL)
 */
function copyEntityInfo(name, lei, gleifUrl) {
      var text = name + '\nLEI: ' + lei + '\n' + gleifUrl;
    navigator.clipboard.writeText(text).then(function() {
        var btn = event.target.closest('.copy-btn');
        if (btn) {
            var originalIcon = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i>';
            btn.classList.add('copied');
            setTimeout(function() {
                btn.innerHTML = originalIcon;
                btn.classList.remove('copied');
            }, 1500);
        }
    }).catch(function(err) {
        console.error('Failed to copy:', err);
    });
}

/**
 * Build entity node HTML with GLEIF link and copy button
 */
function buildEntityNode(entity, options) {
    options = options || {};
    var isCurrent = options.isCurrent || false;
    var isParent = options.isParent || false;
    var relationship = options.relationship || '';

    var hasReport = entity.ticker || entity.cik || entity.fdic_cert;
    var reportLink = hasReport ? buildReportLink(entity) : null;
    var gleifUrl = entity.gleif_url || (entity.lei ? 'https://search.gleif.org/#/record/' + entity.lei : null);

    var nodeClass = 'org-node';
    if (isCurrent) nodeClass += ' current';
    if (isParent) nodeClass += ' parent';
    if (hasReport) nodeClass += ' has-report';

    var icon = isParent ? 'fa-building' : (isCurrent ? 'fa-university' : 'fa-building');

    var html = '<div class="' + nodeClass + '">';
    html += '<i class="fas ' + icon + '"></i>';

    // Name with GLEIF link (if LEI available)
    if (gleifUrl) {
        html += '<a href="' + gleifUrl + '" class="org-name gleif-link" target="_blank" rel="noopener" title="View in GLEIF">' + escapeHtml(entity.name) + '</a>';
    } else if (reportLink) {
        html += '<a href="' + reportLink + '" class="org-name entity-link" title="View report">' + escapeHtml(entity.name) + ' <i class="fas fa-external-link-alt"></i></a>';
    } else {
        html += '<span class="org-name">' + escapeHtml(entity.name) + '</span>';
    }

    // Badges
    if (isCurrent) {
        html += '<span class="org-badge">This Entity</span>';
    }
    if (relationship === 'direct') {
        html += '<span class="org-relationship direct">Direct</span>';
    } else if (relationship === 'ultimate') {
        html += '<span class="org-relationship ultimate">Ultimate</span>';
    }
    if (entity.ticker) {
        html += '<span class="org-ticker">' + escapeHtml(entity.ticker) + '</span>';
    }

    // Copy button (only if LEI available)
    if (entity.lei && gleifUrl) {
        var escapedName = escapeHtml(entity.name).replace(/'/g, "\'");
        html += '<button class="copy-btn" onclick="copyEntityInfo(\'' + escapedName + '\', \'' + entity.lei + '\', \'' + gleifUrl + '\')" title="Copy name, LEI, and GLEIF link"><i class="fas fa-copy"></i></button>';
    }

    html += '</div>';
    return html;
}

function initializeCorporateStructure(data) {
    var structure = data.corporate_structure || {};
    var treeDiv = document.getElementById('org-tree');
    if (!treeDiv) return;

    var MAX_VISIBLE = 10;
    var html = '';

    // Ultimate Parent (top of hierarchy) - always visible
    if (structure.ultimate_parent) {
        html += buildEntityNode(structure.ultimate_parent, { isParent: true });
    }

    // Direct children of parent (includes current entity)
    var directChildren = structure.direct_children || [];
    var ultimateChildren = structure.ultimate_children || [];
    var currentEntity = structure.current_entity;

    // Check if current entity is in direct children
    var currentInDirect = currentEntity && directChildren.some(function(c) {
        return c.lei === currentEntity.lei || c.name === currentEntity.name;
    });

    // Combine all children for counting
    var allChildren = [];

    if (directChildren.length > 0 || currentEntity) {
        html += '<div class="subsidiaries-list direct-children">';

        // Always show current entity first
        if (currentEntity) {
            allChildren.push({ type: 'current', child: currentEntity, isCurrent: true });
            html += '<div class="corp-child">';
            html += buildEntityNode(currentInDirect ?
                directChildren.find(function(c) { return c.lei === currentEntity.lei || c.name === currentEntity.name; }) :
                currentEntity,
                { isCurrent: true, relationship: currentInDirect ? 'direct' : null });
            html += '</div>';
        }

        // Show remaining direct children (excluding current entity)
        directChildren.forEach(function(child, idx) {
            var isCurrent = currentEntity && (child.lei === currentEntity.lei || child.name === currentEntity.name);
            if (isCurrent) return; // Skip - already shown first
            var isHidden = allChildren.length >= MAX_VISIBLE;
            allChildren.push({ type: 'direct', child: child, isCurrent: false });
            html += '<div class="corp-child' + (isHidden ? ' corp-hidden' : '') + '"' + (isHidden ? ' style="display:none;"' : '') + '>';
            html += buildEntityNode(child, { isCurrent: false, relationship: 'direct' });
            html += '</div>';
        });

        html += '</div>';
    }

    // Ultimate children (grandchildren)
    if (ultimateChildren.length > 0) {
        html += '<div class="subsidiaries-list ultimate-children">';
        ultimateChildren.forEach(function(child, idx) {
            var isHidden = allChildren.length >= MAX_VISIBLE;
            allChildren.push({ type: 'ultimate', child: child });
            html += '<div class="corp-child' + (isHidden ? ' corp-hidden' : '') + '"' + (isHidden ? ' style="display:none;"' : '') + '>';
            html += buildEntityNode(child, { relationship: 'ultimate' });
            html += '</div>';
        });
        html += '</div>';
    }

    // Fall back to flat subsidiaries list if no structured data
    if (!directChildren.length && !ultimateChildren.length && Array.isArray(structure.subsidiaries) && structure.subsidiaries.length > 0) {
        html += '<div class="subsidiaries-list">';
        structure.subsidiaries.forEach(function(sub, idx) {
            var isHidden = allChildren.length >= MAX_VISIBLE;
            allChildren.push({ type: 'flat', child: sub });
            html += '<div class="corp-child' + (isHidden ? ' corp-hidden' : '') + '"' + (isHidden ? ' style="display:none;"' : '') + '>';
            html += buildEntityNode(sub);
            html += '</div>';
        });
        html += '</div>';
    }

    // Add expand button if more than MAX_VISIBLE
    var hiddenCount = allChildren.length - MAX_VISIBLE;
    if (hiddenCount > 0) {
        html += '<div class="expand-btn-container" style="text-align: center; padding: 10px 0;">';
        html += '<button id="expand-corp-btn" class="btn-expand" style="background: #f8f9fa; border: 1px solid #ddd; padding: 5px 15px; border-radius: 4px; cursor: pointer; font-size: 0.85em;">';
        html += '<i class="fas fa-chevron-down"></i> Show ' + hiddenCount + ' more';
        html += '</button></div>';
    }

    treeDiv.innerHTML = html || '<p class="no-data">Corporate structure data not available</p>';

    // Add expand button click handler
    if (hiddenCount > 0) {
        var expandBtn = document.getElementById('expand-corp-btn');
        if (expandBtn) {
            expandBtn.addEventListener('click', function() {
                var hiddenItems = treeDiv.querySelectorAll('.corp-hidden');
                var isExpanded = expandBtn.dataset.expanded === 'true';

                hiddenItems.forEach(function(item) {
                    item.style.display = isExpanded ? 'none' : 'block';
                });

                if (isExpanded) {
                    expandBtn.innerHTML = '<i class="fas fa-chevron-down"></i> Show ' + hiddenCount + ' more';
                    expandBtn.dataset.expanded = 'false';
                } else {
                    expandBtn.innerHTML = '<i class="fas fa-chevron-up"></i> Show less';
                    expandBtn.dataset.expanded = 'true';
                }
            });
        }
    }
}

/**
 * Build a report link for a related entity
 * Priority: ticker > fdic_cert > cik > lei > name search
 */
function buildReportLink(entity) {
    // Use ticker if available (most reliable for SEC data)
    if (entity.ticker) {
        return `/report?ticker=${encodeURIComponent(entity.ticker)}`;
    }
    // Use FDIC cert if available (for banks)
    if (entity.fdic_cert) {
        return `/report?fdic_cert=${encodeURIComponent(entity.fdic_cert)}`;
    }
    // Use CIK if available (SEC identifier)
    if (entity.cik) {
        return `/report?cik=${encodeURIComponent(entity.cik)}`;
    }
    // Use LEI if available (GLEIF identifier)
    if (entity.lei) {
        return `/report?lei=${encodeURIComponent(entity.lei)}`;
    }
    // Fall back to name search
    if (entity.name) {
        return `/report?name=${encodeURIComponent(entity.name)}`;
    }
    return null;
}

// =============================================================================
// NEWS
// =============================================================================

function initializeNews(data) {
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

function initializeSeekingAlpha(data) {
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

// =============================================================================
// AI SUMMARY
// =============================================================================

function initializeAISummary(data) {
    const ai = data.ai_summary || {};

    // Hide the executive summary section - we only want key findings
    const summaryDiv = document.getElementById('ai-summary');
    if (summaryDiv) {
        summaryDiv.style.display = 'none';
    }

    const findingsDiv = document.getElementById('key-findings');
    // Handle key_findings - parse bullet format and convert to HTML list
    if (findingsDiv && ai.key_findings) {
        let findingsHtml = '';

        if (typeof ai.key_findings === 'string') {
            // Parse bullet format: "• **Title:** Sentence\n• **Title:** Sentence"
            findingsHtml = parseBulletFindings(ai.key_findings);
        } else if (Array.isArray(ai.key_findings) && ai.key_findings.length > 0) {
            // Array format - convert each item's markdown to HTML
            findingsHtml = '<ul class="key-findings-list">' +
                ai.key_findings.map(f => `<li>${markdownToHtml(f)}</li>`).join('') +
                '</ul>';
        }

        findingsDiv.innerHTML = findingsHtml;
    }
}

// Parse bullet findings format into unordered list
function parseBulletFindings(text) {
    if (!text) return '';

    // Normalize line endings
    text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    // Split by bullet points (•, -, *)
    const findings = [];
    const lines = text.split('\n');
    let currentFinding = '';

    for (const line of lines) {
        const trimmed = line.trim();
        // Check if line starts with a bullet
        if (/^[•\-\*]\s/.test(trimmed)) {
            // Save previous finding if exists
            if (currentFinding.trim()) {
                findings.push(currentFinding.trim());
            }
            // Start new finding (remove the bullet)
            currentFinding = trimmed.replace(/^[•\-\*]\s*/, '');
        } else if (trimmed) {
            // Continue current finding
            currentFinding += ' ' + trimmed;
        }
    }
    // Don't forget last finding
    if (currentFinding.trim()) {
        findings.push(currentFinding.trim());
    }

    if (findings.length === 0) {
        // Fallback: just convert markdown
        return markdownToHtml(text);
    }

    // Build unordered list
    return '<ul class="key-findings-list">' +
        findings.map(f => `<li>${markdownToHtml(f)}</li>`).join('') +
        '</ul>';
}

// Convert markdown to HTML for key findings
function markdownToHtml(text) {
    if (!text) return '';
    return text
        // Remove leading bullet characters (•, -, *, >) at start of text
        .replace(/^[\s]*[•\-\*\>]\s*/g, '')
        // Remove bullet characters after line breaks
        .replace(/\n[\s]*[•\-\*\>]\s*/g, '\n')
        // Fix malformed bold: *text:** or *text** -> **text**
        .replace(/^\*([^*]+)\*\*:/g, '**$1:**')
        .replace(/^\*([^*]+)\*\*/g, '**$1**')
        // Bold: **text** -> <strong>text</strong>
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        // Clean up extra line breaks
        .replace(/\n\n+/g, '<br><br>')
        .replace(/\n/g, ' ');
}

// =============================================================================
// SEC FILINGS ANALYSIS
// =============================================================================

function initializeSECFilingsAnalysis(data) {
    const secData = data.sec_filings_analysis || {};
    const section = document.getElementById('sec-filings-section');
    const findingsDiv = document.getElementById('sec-filings-findings');
    const noDataDiv = document.getElementById('sec-filings-no-data');

    if (!section) return;

    if (!secData.has_data) {
        // Hide main content, show no-data message
        if (findingsDiv) findingsDiv.style.display = 'none';
        if (noDataDiv) {
            noDataDiv.style.display = 'block';
            noDataDiv.innerHTML = '<em>No SEC filing data available for this institution.</em>';
        }
        return;
    }

    // Display the key findings - handle both prose (string) and bullet (array) formats
    if (findingsDiv && secData.key_findings) {
        let fullHtml = '';
        let fullText = '';

        if (typeof secData.key_findings === 'string') {
            // New prose format from SEC_SUMMARY_PROMPT
            // Convert **Title** to <strong>Title</strong> and preserve paragraph structure
            fullText = secData.key_findings;
            fullHtml = secData.key_findings
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                .split('\n\n')  // Split on double newlines for paragraphs
                .filter(p => p.trim())
                .map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`)
                .join('');
        } else if (Array.isArray(secData.key_findings) && secData.key_findings.length > 0) {
            // Legacy bullet format
            fullText = secData.key_findings.join('\n\n');
            fullHtml = '<ul class="key-findings-list">' + secData.key_findings.map(finding => {
                const formatted = finding.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
                return `<li>${formatted}</li>`;
            }).join('') + '</ul>';
        }

        // Create truncated version (first 50 words) with faded last line
        const truncatedHtml = createTruncatedSummary(fullHtml, 50);
        findingsDiv.innerHTML = truncatedHtml;

        // Store full content for modal
        window.fullSummaryHtml = fullHtml;
        window.fullSummaryText = fullText;

        // Initialize modal handlers
        initializeSummaryModal();
    }

    // Update badge with data sources
    if (secData.data_sources && secData.data_sources.length > 0) {
        const badge = section.querySelector('.badge');
        if (badge) {
            badge.textContent = `${secData.data_sources.length} Data Sources`;
        }
    }
}

// =============================================================================
// EXECUTIVE SUMMARY MODAL FUNCTIONS
// =============================================================================

/**
 * Create truncated summary showing first N words with faded last line
 */
function createTruncatedSummary(html, wordLimit) {
    // Create a temporary element to extract text
    const temp = document.createElement('div');
    temp.innerHTML = html;
    const fullText = temp.textContent || temp.innerText;

    // Split into words and get first N words
    const words = fullText.split(/\s+/);
    if (words.length <= wordLimit) {
        // No truncation needed
        return `<div class="sec-analysis-prose">${html}</div>`;
    }

    // Get first 50 words
    const truncatedWords = words.slice(0, wordLimit);
    const truncatedText = truncatedWords.join(' ');

    // Find a good break point (end of sentence or after ~40 words for main text)
    const mainWords = truncatedWords.slice(0, 40);
    const fadeWords = truncatedWords.slice(40);

    const mainText = mainWords.join(' ');
    const fadeText = fadeWords.join(' ') + '...';

    return `<div class="sec-analysis-prose summary-truncated">
        <p>${mainText}</p>
        <p class="summary-fade-line">${fadeText}</p>
    </div>`;
}

/**
 * Initialize summary modal event handlers
 */
function initializeSummaryModal() {
    const viewBtn = document.getElementById('view-summary-btn');
    const modal = document.getElementById('summary-modal');
    const closeBtn = document.getElementById('close-summary-modal');
    const copyBtn = document.getElementById('copy-summary-btn');
    const modalBody = document.getElementById('summary-modal-body');

    if (!viewBtn || !modal) return;

    // Show modal
    viewBtn.addEventListener('click', function() {
        if (window.fullSummaryHtml) {
            modalBody.innerHTML = `<div class="sec-analysis-prose">${window.fullSummaryHtml}</div>`;
        }
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    });

    // Close modal - X button
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        });
    }

    // Close modal - click outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    });

    // Close modal - Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    });

    // Copy button
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            const textToCopy = window.fullSummaryText || '';
            navigator.clipboard.writeText(textToCopy).then(function() {
                // Show feedback
                const originalHtml = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                copyBtn.classList.add('copied');
                setTimeout(function() {
                    copyBtn.innerHTML = originalHtml;
                    copyBtn.classList.remove('copied');
                }, 2000);
            }).catch(function(err) {
                console.error('Failed to copy:', err);
            });
        });
    }
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el && value !== undefined && value !== null) {
        el.textContent = value;
    }
}

function formatNumber(value) {
    if (value === null || value === undefined) return '--';
    return value.toLocaleString();
}

function formatCurrency(value) {
    if (value === null || value === undefined || value === 0) return '--';
    if (value >= 1e12) return '$' + (value / 1e12).toFixed(2) + 'T';
    if (value >= 1e9) return '$' + (value / 1e9).toFixed(2) + 'B';
    if (value >= 1e6) return '$' + (value / 1e6).toFixed(2) + 'M';
    if (value >= 1e3) return '$' + (value / 1e3).toFixed(1) + 'K';
    return '$' + value.toLocaleString();
}

function formatCurrencyShort(value) {
    if (value >= 1e12) return '$' + (value / 1e12).toFixed(1) + 'T';
    if (value >= 1e9) return '$' + (value / 1e9).toFixed(0) + 'B';
    if (value >= 1e6) return '$' + (value / 1e6).toFixed(0) + 'M';
    if (value >= 1e3) return '$' + (value / 1e3).toFixed(0) + 'K';
    return '$' + value;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
        return dateStr;
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function exportToPDF() {
    window.print();
}


// =============================================================================
// DATA VISUALIZATIONS - Branches, Loans, Complaints
// =============================================================================

// NCRC Colors
const NCRC_COLORS = {
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

function initializeVisualizations() {
    var data = window.reportData;
    if (!data) return;
    console.log('Initializing visualizations...');
    renderBranchCharts(data);
    renderLoanCharts(data);
    renderSBLendingCharts(data);
    renderComplaintCharts(data);
}

function renderBranchCharts(data) {
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

function renderLoanCharts(data) {
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

function renderSBLendingCharts(data) {
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

function renderComplaintCharts(data) {
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
function shortenCategoryName(name) {
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

function renderCategoryList(container, categories, animate) {
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
var stateNames = {
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

function getStateName(abbr) {
    return stateNames[abbr] || abbr;
}

function renderBubbleChart(container, data, animate, showAsPercent, totalOverride) {
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

function animateCount(el, from, to, duration) {
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
