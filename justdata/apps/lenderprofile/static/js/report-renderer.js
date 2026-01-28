/**
 * LenderProfile Report Renderer
 * Client-side rendering of all report sections with JavaScript
 * Minimizes AI token usage by handling all data visualization client-side
 */

class ReportRenderer {
    constructor(reportData) {
        this.report = reportData;
        this.sections = reportData?.sections || {};
    }

    /**
     * Render the complete report
     */
    render() {
        const container = document.getElementById('report-content');
        if (!container) return;

        let html = `
            <div class="report-header">
                <h1>Lender Intelligence Report</h1>
                <div class="report-meta">
                    <span><i class="fas fa-calendar"></i> Generated: ${this.formatDate(this.report.metadata?.generated_at)}</span>
                    ${this.report.metadata?.report_focus ? `<span><i class="fas fa-bullseye"></i> Focus: ${this.escapeHtml(this.report.metadata.report_focus)}</span>` : ''}
                </div>
            </div>
        `;

        // Render 7-section architecture
        html += this.renderExecutiveSummary();
        html += this.renderCorporateStructure();
        html += this.renderLeadershipGovernance();
        html += this.renderFinancialPerformance();
        html += this.renderBusinessStrategy();
        html += this.renderMarketPosition();
        html += this.renderRegulatoryRisk();

        container.innerHTML = html;

        // Render charts and visualizations after DOM is ready
        setTimeout(() => {
            this.renderCharts();
            this.renderMaps();
            this.renderOrgCharts();
        }, 100);
    }

    /**
     * Section 1: Executive Summary
     */
    renderExecutiveSummary() {
        const section = this.sections.executive_summary;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-file-alt"></i> 1. Executive Summary
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.institution_name ? `<p><strong>Institution:</strong> ${this.escapeHtml(section.institution_name)}</p>` : ''}
                    ${section.institution_type ? `<p><strong>Type:</strong> ${this.escapeHtml(section.institution_type)}</p>` : ''}
                    ${section.location ? `<p><strong>Location:</strong> ${this.escapeHtml(section.location)}</p>` : ''}
                    ${section.assets ? `<p><strong>Assets:</strong> ${this.formatCurrency(section.assets)}</p>` : ''}
                    ${section.summary ? `<div class="ai-summary">${this.formatMarkdown(section.summary)}</div>` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 2: Corporate Structure & Ownership
     */
    renderCorporateStructure() {
        const section = this.sections.corporate_structure;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-sitemap"></i> 2. Corporate Structure & Ownership
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.legal_name ? `<p><strong>Legal Name:</strong> ${this.escapeHtml(section.legal_name)}</p>` : ''}
                    ${section.lei ? `<p><strong>LEI:</strong> ${this.escapeHtml(section.lei)}</p>` : ''}
                    ${section.headquarters && (section.headquarters.city || section.headquarters.state) ? 
                        `<p><strong>Headquarters:</strong> ${this.escapeHtml(section.headquarters.city || '')}, ${this.escapeHtml(section.headquarters.state || '')}</p>` : ''}
                    ${section.direct_parent && section.direct_parent.name ? 
                        `<p><strong>Direct Parent:</strong> ${this.escapeHtml(section.direct_parent.name)} (LEI: ${this.escapeHtml(section.direct_parent.lei || 'N/A')})</p>` : ''}
                    ${section.ultimate_parent && section.ultimate_parent.name ? 
                        `<p><strong>Ultimate Parent:</strong> ${this.escapeHtml(section.ultimate_parent.name)} (LEI: ${this.escapeHtml(section.ultimate_parent.lei || 'N/A')})</p>` : ''}
                    ${section.subsidiaries && (section.subsidiaries.direct?.length > 0 || section.subsidiaries.ultimate?.length > 0) ? 
                        this.renderSubsidiaries(section.subsidiaries) : ''}
                    ${section.geographic_footprint && Object.keys(section.geographic_footprint).length > 0 ? 
                        `<h3>Geographic Footprint</h3><p>Branch network data available</p>` : ''}
                    ${section.recent_changes && section.recent_changes.length > 0 ? 
                        `<h3>Recent Organizational Changes</h3><p>${section.recent_changes.length} changes identified</p>` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 3: Leadership & Governance
     */
    renderLeadershipGovernance() {
        const section = this.sections.leadership_governance;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-users"></i> 3. Leadership & Governance
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.executives && section.executives.length > 0 ? 
                        `<h3>Executive Team</h3>
                        <table class="data-table">
                            <thead>
                                <tr><th>Name</th><th>Title</th><th>Total Compensation</th></tr>
                            </thead>
                            <tbody>
                                ${section.executives.map(exec => `
                                    <tr>
                                        <td>${this.escapeHtml(exec.name || 'N/A')}</td>
                                        <td>${this.escapeHtml(exec.title || 'N/A')}</td>
                                        <td>${exec.total_comp ? this.formatCurrency(exec.total_comp) : 'N/A'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>` : '<p>Executive data not available.</p>'}
                    ${section.board && section.board.length > 0 ? 
                        `<h3>Board of Directors</h3>
                        <p>${section.board.length} board members identified</p>` : ''}
                    ${section.compensation && section.compensation.ceo_total ? 
                        `<h3>Compensation Summary</h3>
                        <p><strong>CEO Total Compensation:</strong> ${this.formatCurrency(section.compensation.ceo_total)}</p>
                        ${section.compensation.top_5_total ? 
                            `<p><strong>Top 5 Executives Total:</strong> ${this.formatCurrency(section.compensation.top_5_total)}</p>` : ''}` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 4: Financial Performance
     */
    renderFinancialPerformance() {
        const section = this.sections.financial_performance;
        if (!section || !section.available) {
            return `
                <div class="report-section">
                    <h2 class="section-header" onclick="toggleSection(this)">
                        <i class="fas fa-chart-line"></i> 4. Financial Performance
                        <i class="fas fa-chevron-down section-icon"></i>
                    </h2>
                    <div class="section-content">
                        <p>${section?.message || 'Financial data not available.'}</p>
                    </div>
                </div>
            `;
        }

        const trends = section.trends || {};
        const metrics = section.metrics || {};
        const growth = section.growth || {};

        return `
            <div class="report-section magazine-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-chart-line"></i> 4. Financial Performance
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    <div class="magazine-layout">
                        <div class="magazine-main">
                            ${metrics.assets ? `
                                <div class="stat-cards-grid">
                                    <div class="stat-card">
                                        <div class="stat-value">${this.formatCurrency(metrics.assets)}</div>
                                        <div class="stat-label">Total Assets</div>
                                    </div>
                                    ${metrics.roa ? `
                                        <div class="stat-card">
                                            <div class="stat-value">${metrics.roa.toFixed(2)}%</div>
                                            <div class="stat-label">ROA</div>
                                        </div>
                                    ` : ''}
                                    ${metrics.roe ? `
                                        <div class="stat-card">
                                            <div class="stat-value">${metrics.roe.toFixed(2)}%</div>
                                            <div class="stat-label">ROE</div>
                                        </div>
                                    ` : ''}
                                </div>
                            ` : ''}
                            
                            ${trends.assets && trends.assets.length > 0 ? `
                                <div class="chart-container">
                                    <canvas id="financial-trends-chart"></canvas>
                                </div>
                            ` : ''}
                            
                            ${growth.asset_cagr ? `
                                <h3>Growth Metrics</h3>
                                <p><strong>Asset CAGR:</strong> ${growth.asset_cagr.toFixed(2)}%</p>
                                ${growth.deposit_cagr ? `<p><strong>Deposit CAGR:</strong> ${growth.deposit_cagr.toFixed(2)}%</p>` : ''}
                                ${growth.income_cagr ? `<p><strong>Income CAGR:</strong> ${growth.income_cagr.toFixed(2)}%</p>` : ''}
                            ` : ''}
                        </div>
                        <div class="magazine-sidebar">
                            ${metrics ? this.renderFinancialMetrics(metrics) : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Section 5: Business Strategy & Operations
     */
    renderBusinessStrategy() {
        const section = this.sections.business_strategy;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-bullseye"></i> 5. Business Strategy & Operations
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.strategy_analysis ? `
                        <h3>Strategic Priorities</h3>
                        <div class="ai-summary">${this.formatMarkdown(JSON.stringify(section.strategy_analysis, null, 2))}</div>
                    ` : ''}
                    ${section.risk_factors && section.risk_factors.length > 0 ? `
                        <h3>Key Risk Factors</h3>
                        <ul>
                            ${section.risk_factors.map(risk => `
                                <li><strong>${this.escapeHtml(risk.category_name || 'Risk')}:</strong> ${this.escapeHtml(risk.description || '')}</li>
                            `).join('')}
                        </ul>
                    ` : ''}
                    ${section.mda_insights ? `
                        <h3>Management Discussion & Analysis Insights</h3>
                        <div class="ai-summary">${this.formatMarkdown(JSON.stringify(section.mda_insights, null, 2))}</div>
                    ` : ''}
                    ${section.acquisitions && section.acquisitions.length > 0 ? `
                        <h3>Recent Acquisitions</h3>
                        <ul>
                            ${section.acquisitions.map(acq => `
                                <li>${this.escapeHtml(acq.target || acq.details || 'Acquisition')} (${this.escapeHtml(acq.year || 'N/A')})</li>
                            `).join('')}
                        </ul>
                    ` : ''}
                    ${section.branch_expansion ? `
                        <h3>Branch Network Strategy</h3>
                        <p>${section.branch_expansion.overall_trend || 'Trend data available'}</p>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 6: Market Position & Analyst Views
     */
    renderMarketPosition() {
        const section = this.sections.market_position;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-chart-bar"></i> 6. Market Position & Analyst Views
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.analyst_ratings && section.analyst_ratings.distribution ? `
                        <h3>Analyst Ratings</h3>
                        <p><strong>Buy:</strong> ${section.analyst_ratings.distribution.buy || 0} | 
                           <strong>Hold:</strong> ${section.analyst_ratings.distribution.hold || 0} | 
                           <strong>Sell:</strong> ${section.analyst_ratings.distribution.sell || 0}</p>
                        ${section.analyst_ratings.quant_rating ? 
                            `<p><strong>Quantitative Rating:</strong> ${this.escapeHtml(section.analyst_ratings.quant_rating)}</p>` : ''}
                    ` : '<p>Analyst ratings not available.</p>'}
                    ${section.price_targets && section.price_targets.current ? `
                        <h3>Price Targets</h3>
                        <p><strong>Current Price:</strong> $${section.price_targets.current.toFixed(2)}</p>
                        ${section.price_targets.average ? 
                            `<p><strong>Average Target:</strong> $${section.price_targets.average.toFixed(2)}</p>` : ''}
                        ${section.price_targets.high ? 
                            `<p><strong>High Target:</strong> $${section.price_targets.high.toFixed(2)}</p>` : ''}
                        ${section.price_targets.low ? 
                            `<p><strong>Low Target:</strong> $${section.price_targets.low.toFixed(2)}</p>` : ''}
                    ` : ''}
                    ${section.earnings ? `
                        <h3>Earnings</h3>
                        <p>Earnings data available</p>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 7: Regulatory & Reputational Risk
     */
    renderRegulatoryRisk() {
        const section = this.sections.regulatory_risk;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-shield-alt"></i> 7. Regulatory & Reputational Risk
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.complaints && section.complaints.summary ? `
                        <h3>Consumer Complaints</h3>
                        <p><strong>Total Complaints:</strong> ${section.complaints.summary.total || 0}</p>
                        ${section.complaints.top_issues && section.complaints.top_issues.length > 0 ? `
                            <h4>Top Issues</h4>
                            <ul>
                                ${section.complaints.top_issues.slice(0, 5).map(issue => `
                                    <li>${this.escapeHtml(issue.issue || 'N/A')}: ${issue.count || 0} complaints</li>
                                `).join('')}
                            </ul>
                        ` : ''}
                    ` : '<p>Consumer complaints data not available.</p>'}
                    ${section.litigation && section.litigation.summary ? `
                        <h3>Litigation</h3>
                        <p><strong>Total Cases:</strong> ${section.litigation.summary.total_cases || 0}</p>
                        <p><strong>Active Cases:</strong> ${section.litigation.summary.active_cases || 0}</p>
                    ` : '<p>Litigation data not available.</p>'}
                    ${section.news_sentiment ? `
                        <h3>News Sentiment</h3>
                        <p><strong>Overall Sentiment:</strong> ${this.escapeHtml(section.news_sentiment.overall_sentiment || 'N/A')}</p>
                        ${section.news_sentiment.summary ? 
                            `<p>${this.escapeHtml(section.news_sentiment.summary)}</p>` : ''}
                    ` : ''}
                    ${section.recent_articles && section.recent_articles.length > 0 ? `
                        <h3>Recent News Articles</h3>
                        <ul>
                            ${section.recent_articles.slice(0, 5).map(article => `
                                <li><a href="${this.escapeHtml(article.url || '#')}" target="_blank">${this.escapeHtml(article.title || 'Article')}</a></li>
                            `).join('')}
                        </ul>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 3: Financial Profile
     */
    renderFinancialProfile() {
        const section = this.sections.financial_profile;
        if (!section) return '';

        // Get processed financial data if available
        const financialData = this.report?.metadata?.institution_data?.financial;
        const processed = financialData?.processed;
        const trends = processed?.trends || section.trends || {};
        const metrics = processed?.metrics || section.metrics || {};

        return `
            <div class="report-section magazine-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-chart-line"></i> 3. Financial Profile
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    <div class="magazine-layout">
                        <div class="magazine-main">
                            ${metrics.assets ? `
                                <div class="stat-cards-grid">
                                    <div class="stat-card">
                                        <div class="stat-value">${this.formatCurrency(metrics.assets)}</div>
                                        <div class="stat-label">Total Assets</div>
                                    </div>
                                    ${metrics.roa ? `
                                        <div class="stat-card">
                                            <div class="stat-value">${metrics.roa.toFixed(2)}%</div>
                                            <div class="stat-label">ROA</div>
                                        </div>
                                    ` : ''}
                                    ${metrics.roe ? `
                                        <div class="stat-card">
                                            <div class="stat-value">${metrics.roe.toFixed(2)}%</div>
                                            <div class="stat-label">ROE</div>
                                        </div>
                                    ` : ''}
                                </div>
                            ` : ''}
                            
                            ${trends.assets && trends.assets.length > 0 ? `
                                <div class="chart-container">
                                    <canvas id="financial-trends-chart"></canvas>
                                </div>
                            ` : ''}
                            
                            ${trends.assets && trends.assets.length > 0 ? `
                                <div class="chart-container">
                                    <canvas id="profitability-chart"></canvas>
                                </div>
                            ` : ''}
                        </div>
                        <div class="magazine-sidebar">
                            ${metrics ? this.renderFinancialMetrics(metrics) : ''}
                            ${section.peer_comparison ? this.renderPeerComparison(section.peer_comparison) : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Section 4: Branch Network
     */
    renderBranchNetwork() {
        const section = this.sections.branch_network;
        if (!section) return '';

        return `
            <div class="report-section magazine-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-map-marker-alt"></i> 4. Branch Network and Market Presence
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    <div class="magazine-layout">
                        <div class="magazine-main">
                            ${section.total_branches ? `<div class="stat-card"><div class="stat-value">${section.total_branches.toLocaleString()}</div><div class="stat-label">Total Branches</div></div>` : ''}
                            
                            ${section.total_branches_by_year ? `
                                <div class="chart-container">
                                    <canvas id="branch-trend-chart"></canvas>
                                </div>
                            ` : ''}
                            
                            ${section.trends ? this.renderBranchTrends(section.trends) : ''}
                            
                            <div id="branch-map-container" class="map-container">
                                <div id="branch-map" style="height: 500px; width: 100%;"></div>
                            </div>
                        </div>
                        <div class="magazine-sidebar">
                            ${section.by_state ? this.renderStateBreakdown(section.by_state) : ''}
                            ${section.by_cbsa ? this.renderCBSABreakdown(section.by_cbsa) : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Section 5: CRA Performance
     */
    renderCRAPerformance() {
        const section = this.sections.cra_performance;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-star"></i> 5. CRA Performance
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.current_rating ? `<p><strong>Current Rating:</strong> <span class="rating-badge rating-${section.current_rating.toLowerCase()}">${section.current_rating}</span></p>` : ''}
                    ${section.rating_history ? this.renderRatingHistory(section.rating_history) : ''}
                    ${section.test_ratings ? this.renderTestRatings(section.test_ratings) : ''}
                    ${section.examiner_findings ? this.renderExaminerFindings(section.examiner_findings) : ''}
                    ${section.ai_summary ? `<div class="ai-summary">${this.formatMarkdown(section.ai_summary)}</div>` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 6: Regulatory and Legal History
     */
    renderRegulatoryHistory() {
        const section = this.sections.regulatory_history;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-gavel"></i> 6. Regulatory and Legal History
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.actions_by_agency ? this.renderEnforcementActions(section.actions_by_agency) : ''}
                    ${section.violation_types ? this.renderViolationTypes(section.violation_types) : ''}
                    ${section.consumer_complaints ? this.renderConsumerComplaints(section.consumer_complaints) : ''}
                    ${section.litigation_cases ? this.renderLitigationCases(section.litigation_cases) : ''}
                    ${section.ai_summary ? `<div class="ai-summary">${this.formatMarkdown(section.ai_summary)}</div>` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Render Consumer Complaints with Trends and Topics
     */
    renderConsumerComplaints(complaints) {
        if (!complaints || complaints.total === 0) {
            return '<p>No consumer complaints data available.</p>';
        }

        let html = `
            <div class="complaints-section">
                <h3>Consumer Complaints</h3>
                <p><strong>Total Complaints:</strong> ${this.formatNumber(complaints.total)}</p>
        `;

        // Trend Analysis
        if (complaints.trends) {
            const trends = complaints.trends;
            html += `
                <div class="trend-analysis">
                    <h4>Complaint Trends</h4>
                    <p><strong>Recent Trend:</strong> <span class="trend-${trends.recent_trend}">${trends.recent_trend.toUpperCase()}</span></p>
                    ${trends.by_year ? `
                        <div class="chart-container" style="height: 300px;">
                            <canvas id="complaints-trend-chart"></canvas>
                        </div>
                        <div class="year-breakdown">
                            <h5>Complaints by Year:</h5>
                            <table class="data-table">
                                <thead>
                                    <tr><th>Year</th><th>Complaints</th><th>Change</th></tr>
                                </thead>
                                <tbody>
                                    ${this.renderYearBreakdown(trends.by_year, trends.year_over_year_changes)}
                                </tbody>
                            </table>
                        </div>
                    ` : ''}
                </div>
            `;
        }

        // Main Topics
        if (complaints.main_topics && complaints.main_topics.length > 0) {
            html += `
                <div class="main-topics">
                    <h4>Main Complaint Topics</h4>
                    <div class="chart-container" style="height: 300px;">
                        <canvas id="complaints-topics-chart"></canvas>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr><th>Topic</th><th>Count</th><th>Percentage</th></tr>
                        </thead>
                        <tbody>
                            ${complaints.main_topics.map(topic => `
                                <tr>
                                    <td>${this.escapeHtml(topic.issue)}</td>
                                    <td>${this.formatNumber(topic.count)}</td>
                                    <td>${topic.percentage.toFixed(1)}%</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        // Main Products
        if (complaints.main_products && complaints.main_products.length > 0) {
            html += `
                <div class="main-products">
                    <h4>Main Products with Complaints</h4>
                    <table class="data-table">
                        <thead>
                            <tr><th>Product</th><th>Count</th><th>Percentage</th></tr>
                        </thead>
                        <tbody>
                            ${complaints.main_products.map(product => `
                                <tr>
                                    <td>${this.escapeHtml(product.product)}</td>
                                    <td>${this.formatNumber(product.count)}</td>
                                    <td>${product.percentage.toFixed(1)}%</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        html += '</div>';
        return html;
    }

    /**
     * Render year breakdown table
     */
    renderYearBreakdown(byYear, yoyChanges) {
        const sortedYears = Object.keys(byYear).sort();
        return sortedYears.map((year, index) => {
            const count = byYear[year];
            const change = yoyChanges?.[year];
            let changeHtml = '-';
            if (change) {
                const changePct = change.change;
                const direction = changePct > 0 ? '↑' : changePct < 0 ? '↓' : '→';
                changeHtml = `<span class="change-${changePct > 0 ? 'up' : changePct < 0 ? 'down' : 'stable'}">${direction} ${Math.abs(changePct).toFixed(1)}%</span>`;
            }
            return `<tr><td>${year}</td><td>${this.formatNumber(count)}</td><td>${changeHtml}</td></tr>`;
        }).join('');
    }

    /**
     * Section 7: Strategic Positioning
     */
    renderStrategicPositioning() {
        const section = this.sections.strategic_positioning;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-bullseye"></i> 7. Strategic Positioning
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.business_description ? `<div class="business-description">${this.formatMarkdown(section.business_description)}</div>` : ''}
                    ${section.executives ? this.renderExecutives(section.executives) : ''}
                    ${section.risk_factors ? this.renderRiskFactors(section.risk_factors) : ''}
                    ${section.ai_summary ? `<div class="ai-summary">${this.formatMarkdown(section.ai_summary)}</div>` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 7B: Organizational Analysis
     */
    renderOrganizationalAnalysis() {
        const section = this.sections.organizational_analysis;
        if (!section || !section.available) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-users"></i> 7B. Organizational Analysis
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.total_people ? `<p><strong>Total People in Database:</strong> ${section.total_people}</p>` : ''}
                    ${section.departments ? this.renderDepartments(section.departments) : ''}
                    ${section.org_chart ? '<div id="theorg-chart-viz"></div>' : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 8: Merger Activity
     */
    renderMergerActivity() {
        const section = this.sections.merger_activity;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-handshake"></i> 8. Merger and Acquisition Activity
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.historical_acquisitions ? this.renderMergers(section.historical_acquisitions, 'Historical') : ''}
                    ${section.pending_applications ? this.renderMergers(section.pending_applications, 'Pending') : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 9: Market Context
     */
    renderMarketContext() {
        const section = this.sections.market_context;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-chart-bar"></i> 9. Market Context and Competitive Position
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.asset_ranking ? this.renderAssetRanking(section.asset_ranking) : ''}
                    ${section.deposit_market_share ? this.renderDepositMarketShare(section.deposit_market_share) : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 10: Recent Developments
     */
    renderRecentDevelopments() {
        const section = this.sections.recent_developments;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-newspaper"></i> 10. Recent Developments and News
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.news_articles ? this.renderNewsArticles(section.news_articles) : ''}
                    ${section.regulatory_proposals ? this.renderRegulatoryProposals(section.regulatory_proposals) : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 11: Regulatory Engagement
     */
    renderRegulatoryEngagement() {
        const section = this.sections.regulatory_engagement;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-comments"></i> 11. Regulatory Engagement and Policy Positions
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.comment_letters ? this.renderCommentLetters(section.comment_letters) : ''}
                    ${section.topics ? this.renderPolicyTopics(section.topics) : ''}
                    ${section.ai_summary ? `<div class="ai-summary">${this.formatMarkdown(section.ai_summary)}</div>` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Section 12: Advocacy Intelligence
     */
    renderAdvocacyIntelligence() {
        const section = this.sections.advocacy_intelligence;
        if (!section) return '';

        return `
            <div class="report-section">
                <h2 class="section-header" onclick="toggleSection(this)">
                    <i class="fas fa-lightbulb"></i> 12. Advocacy Intelligence Summary
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${section.ai_analysis ? `<div class="ai-summary">${this.formatMarkdown(section.ai_analysis)}</div>` : ''}
                    ${section.cba_opportunity ? this.renderCBAOpportunity(section.cba_opportunity) : ''}
                    ${section.merger_opposition ? this.renderMergerOpposition(section.merger_opposition) : ''}
                    ${section.partnership_opportunities ? this.renderPartnershipOpportunities(section.partnership_opportunities) : ''}
                </div>
            </div>
        `;
    }

    // ========== Helper Rendering Functions ==========

    renderInstitutionSummary(section) {
        return `
            <div class="institution-summary-grid">
                <div class="summary-item">
                    <span class="label">Institution:</span>
                    <span class="value">${this.escapeHtml(section.institution_name || 'N/A')}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Type:</span>
                    <span class="value">${this.escapeHtml(section.institution_type || 'N/A')}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Location:</span>
                    <span class="value">${this.escapeHtml(section.location || 'N/A')}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Assets:</span>
                    <span class="value">${this.escapeHtml(section.assets || 'N/A')}</span>
                </div>
            </div>
        `;
    }

    renderKeyFindings(findings) {
        if (typeof findings === 'string') {
            // Parse markdown-style findings
            const items = findings.split(/[•\-\*]/).filter(f => f.trim());
            return `
                <h3>Key Findings</h3>
                <ul class="key-findings">
                    ${items.map(item => `<li>${this.formatMarkdown(item.trim())}</li>`).join('')}
                </ul>
            `;
        }
        return '';
    }

    renderEnforcementActions(actionsByAgency) {
        let html = '<h3>Enforcement Actions by Agency</h3>';
        for (const [agency, actions] of Object.entries(actionsByAgency)) {
            if (actions && actions.length > 0) {
                html += `
                    <div class="agency-section">
                        <h4>${agency}</h4>
                        <table class="data-table">
                            <thead>
                                <tr><th>Date</th><th>Action</th><th>Type</th></tr>
                            </thead>
                            <tbody>
                                ${actions.map(action => `
                                    <tr>
                                        <td>${this.formatDate(action.date)}</td>
                                        <td>${this.escapeHtml(action.title || action.action || 'N/A')}</td>
                                        <td>${this.escapeHtml(action.type || 'N/A')}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            }
        }
        return html;
    }

    renderViolationTypes(violationTypes) {
        let html = '<h3>Violation Categories</h3>';
        for (const [category, actions] of Object.entries(violationTypes)) {
            if (actions && actions.length > 0) {
                html += `
                    <div class="violation-category">
                        <h4>${category.replace('_', ' ').toUpperCase()}</h4>
                        <p>${actions.length} action(s)</p>
                    </div>
                `;
            }
        }
        return html;
    }

    renderLitigationCases(cases) {
        if (!cases || cases.length === 0) return '';
        return `
            <h3>Litigation Cases</h3>
            <table class="data-table">
                <thead>
                    <tr><th>Case</th><th>Court</th><th>Date</th><th>Status</th></tr>
                </thead>
                <tbody>
                    ${cases.map(c => `
                        <tr>
                            <td>${this.escapeHtml(c.title || c.case_name || 'N/A')}</td>
                            <td>${this.escapeHtml(c.court || 'N/A')}</td>
                            <td>${this.formatDate(c.date || c.filed_date)}</td>
                            <td>${this.escapeHtml(c.status || 'N/A')}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    // ========== Chart Rendering ==========

    renderCharts() {
        // Financial Trends Chart
        const financialSection = this.sections.financial_profile;
        const financialData = this.report?.metadata?.institution_data?.financial;
        const processed = financialData?.processed;
        const trends = processed?.trends || financialSection?.trends;
        
        if (trends && trends.assets && trends.assets.length > 0) {
            this.renderFinancialChart(trends);
        }
        
        // Profitability Chart
        if (trends && trends.roa && trends.roa.length > 0) {
            this.renderProfitabilityChart(trends);
        }

        // Branch Trends Chart
        const branchSection = this.sections.branch_network;
        if (branchSection && branchSection.total_branches_by_year) {
            this.renderBranchTrendsChart(branchSection.total_branches_by_year);
        }

        // Complaints Trend Chart
        const regulatorySection = this.sections.regulatory_history;
        if (regulatorySection?.consumer_complaints?.trends) {
            this.renderComplaintsTrendChart(regulatorySection.consumer_complaints.trends);
        }

        // Complaints Topics Chart
        if (regulatorySection?.consumer_complaints?.main_topics) {
            this.renderComplaintsTopicsChart(regulatorySection.consumer_complaints.main_topics);
        }
    }

    renderFinancialChart(trends) {
        const canvas = document.getElementById('financial-trends-chart');
        if (!canvas) return;

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: trends.years || [],
                datasets: [
                    {
                        label: 'Assets',
                        data: trends.assets || [],
                        borderColor: 'rgb(85, 45, 135)',
                        backgroundColor: 'rgba(85, 45, 135, 0.1)',
                        tension: 0.1
                    },
                    {
                        label: 'Equity',
                        data: trends.equity || [],
                        borderColor: 'rgb(47, 173, 227)',
                        backgroundColor: 'rgba(47, 173, 227, 0.1)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: '5-Year Financial Trends' },
                    legend: { display: true }
                },
                scales: {
                    y: { beginAtZero: false }
                }
            }
        });
    }

    renderComplaintsTrendChart(trends) {
        const canvas = document.getElementById('complaints-trend-chart');
        if (!canvas || !trends.by_year) return;

        const sortedYears = Object.keys(trends.by_year).sort();
        const counts = sortedYears.map(year => trends.by_year[year]);

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: sortedYears,
                datasets: [{
                    label: 'Complaints',
                    data: counts,
                    backgroundColor: 'rgba(232, 46, 46, 0.6)',
                    borderColor: 'rgb(232, 46, 46)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Consumer Complaints by Year' },
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }

    renderComplaintsTopicsChart(topics) {
        const canvas = document.getElementById('complaints-topics-chart');
        if (!canvas) return;

        const top10 = topics.slice(0, 10);
        const labels = top10.map(t => t.issue.length > 30 ? t.issue.substring(0, 30) + '...' : t.issue);
        const data = top10.map(t => t.count);

        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        'rgba(85, 45, 135, 0.8)',
                        'rgba(47, 173, 227, 0.8)',
                        'rgba(232, 46, 46, 0.8)',
                        'rgba(235, 47, 137, 0.8)',
                        'rgba(255, 194, 58, 0.8)',
                        'rgba(3, 78, 160, 0.8)',
                        'rgba(129, 131, 144, 0.8)',
                        'rgba(85, 45, 135, 0.6)',
                        'rgba(47, 173, 227, 0.6)',
                        'rgba(232, 46, 46, 0.6)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Top Complaint Topics' },
                    legend: { position: 'right' }
                }
            }
        });
    }

    // ========== Utility Functions ==========

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatMarkdown(text) {
        if (!text) return '';
        // Simple markdown conversion
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
        text = text.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
        text = text.replace(/\n\n/g, '</p><p>');
        text = text.replace(/\n/g, '<br>');
        return `<p>${text}</p>`;
    }

    formatNumber(num) {
        if (!num && num !== 0) return 'N/A';
        return num.toLocaleString();
    }

    formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
        } catch {
            return dateStr;
        }
    }

    // Placeholder functions for other sections (to be implemented)
    renderEntityHierarchy() { return '<p>Entity hierarchy visualization coming soon.</p>'; }
    renderSubsidiaries() { return ''; }
    renderPeerComparison() { return ''; }
    renderGeographicDistribution() { return ''; }
    renderMarketShare() { return ''; }
    renderRatingHistory() { return ''; }
    renderTestRatings() { return ''; }
    renderExaminerFindings() { return ''; }
    renderExecutives() { return ''; }
    renderRiskFactors() { return ''; }
    renderDepartments() { return ''; }
    renderMergers() { return ''; }
    renderAssetRanking() { return ''; }
    renderDepositMarketShare() { return ''; }
    renderNewsArticles() { return ''; }
    renderRegulatoryProposals() { return ''; }
    renderCommentLetters() { return ''; }
    renderPolicyTopics() { return ''; }
    renderCBAOpportunity() { return ''; }
    renderMergerOpposition() { return ''; }
    renderPartnershipOpportunities() { return ''; }
    renderMaps() {
        // Render branch network map
        const branchSection = this.sections.branch_network;
        if (branchSection && branchSection.cbsa_coordinates) {
            this.renderBranchMap(branchSection.cbsa_coordinates, branchSection.by_cbsa);
        }
    }
    
    renderBranchMap(cbsaCoordinates, byCbsa) {
        const mapContainer = document.getElementById('branch-map');
        if (!mapContainer || !cbsaCoordinates || Object.keys(cbsaCoordinates).length === 0) {
            if (mapContainer) {
                mapContainer.innerHTML = '<p style="text-align: center; padding: 40px; color: #666;">Branch location data not available for map visualization.</p>';
            }
            return;
        }
        
        // Initialize map centered on US
        const map = L.map('branch-map').setView([39.8283, -98.5795], 4);
        
        // Add Mapbox tile layer
        const MAPBOX_TOKEN = 'pk.eyJ1IjoiZXhhbXBsZXMiLCJhIjoiY2xxeTBib3pyMGsxcTJpbXQ3bmo4YXU0ZiJ9.wvqlBMQSxTHgvAh6l9OXXw';
        L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/light-v11/tiles/256/{z}/{x}/{y}@2x?access_token=' + MAPBOX_TOKEN, {
            attribution: '&copy; <a href="https://www.mapbox.com/">Mapbox</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            tileSize: 256,
            maxZoom: 19
        }).addTo(map);
        
        // Add markers for each CBSA
        let bounds = [];
        for (const [cbsaName, data] of Object.entries(cbsaCoordinates)) {
            if (data.lat && data.lon) {
                const count = byCbsa[cbsaName] || data.count || 1;
                const radius = Math.min(Math.max(count / 10, 5), 30);
                const marker = L.circleMarker([data.lat, data.lon], {
                    radius: radius,
                    fillColor: '#552d87',
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.6
                }).addTo(map);
                
                marker.bindPopup(`
                    <strong>${this.escapeHtml(cbsaName)}</strong><br>
                    ${count} branch${count !== 1 ? 'es' : ''}
                `);
                
                bounds.push([data.lat, data.lon]);
            }
        }
        
        // Fit map to show all markers
        if (bounds.length > 0) {
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }
    
    renderBranchTrends(trends) {
        if (!trends || !trends.overall_trend) return '';
        
        return `
            <div class="trend-summary">
                <h3>Network Trend: ${this.formatTrend(trends.overall_trend)}</h3>
                <p>Average ${trends.avg_net_change_per_year >= 0 ? 'growth' : 'shrinkage'}: ${Math.abs(trends.avg_net_change_per_year).toFixed(1)} branches per year</p>
                <p>Total closures: ${trends.total_closures || 0} | Total openings: ${trends.total_openings || 0}</p>
            </div>
        `;
    }
    
    formatTrend(trend) {
        const trendMap = {
            'significant_shrinkage': 'Significant Shrinkage',
            'moderate_shrinkage': 'Moderate Shrinkage',
            'stable': 'Stable',
            'moderate_growth': 'Moderate Growth',
            'significant_growth': 'Significant Growth'
        };
        return trendMap[trend] || trend;
    }
    
    renderStateBreakdown(byState) {
        const sorted = Object.entries(byState).sort((a, b) => b[1] - a[1]).slice(0, 10);
        if (sorted.length === 0) return '';
        return `
            <div class="sidebar-card">
                <h4>Top States</h4>
                <ul class="breakdown-list">
                    ${sorted.map(([state, count]) => `
                        <li>
                            <span class="breakdown-label">${this.escapeHtml(state)}</span>
                            <span class="breakdown-value">${count.toLocaleString()}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }
    
    renderCBSABreakdown(byCbsa) {
        const sorted = Object.entries(byCbsa).sort((a, b) => b[1] - a[1]).slice(0, 10);
        if (sorted.length === 0) return '';
        return `
            <div class="sidebar-card">
                <h4>Top Metro Areas</h4>
                <ul class="breakdown-list">
                    ${sorted.map(([cbsa, count]) => `
                        <li>
                            <span class="breakdown-label">${this.escapeHtml(cbsa.length > 25 ? cbsa.substring(0, 25) + '...' : cbsa)}</span>
                            <span class="breakdown-value">${count.toLocaleString()}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }
    
    formatCurrency(value) {
        if (!value || value === 0) return 'N/A';
        if (value >= 1000000000) return `$${(value / 1000000000).toFixed(2)}B`;
        if (value >= 1000000) return `$${(value / 1000000).toFixed(2)}M`;
        return `$${value.toLocaleString()}`;
    }
    
    renderFinancialMetrics(metrics) {
        if (!metrics) return '';
        return `
            <div class="sidebar-card">
                <h4>Key Metrics</h4>
                <ul class="breakdown-list">
                    ${metrics.assets ? `
                        <li>
                            <span class="breakdown-label">Assets</span>
                            <span class="breakdown-value">${this.formatCurrency(metrics.assets)}</span>
                        </li>
                    ` : ''}
                    ${metrics.deposits ? `
                        <li>
                            <span class="breakdown-label">Deposits</span>
                            <span class="breakdown-value">${this.formatCurrency(metrics.deposits)}</span>
                        </li>
                    ` : ''}
                    ${metrics.roa !== undefined ? `
                        <li>
                            <span class="breakdown-label">ROA</span>
                            <span class="breakdown-value">${metrics.roa.toFixed(2)}%</span>
                        </li>
                    ` : ''}
                    ${metrics.roe !== undefined ? `
                        <li>
                            <span class="breakdown-label">ROE</span>
                            <span class="breakdown-value">${metrics.roe.toFixed(2)}%</span>
                        </li>
                    ` : ''}
                </ul>
            </div>
        `;
    }
    renderOrgCharts() { /* D3.js org chart rendering */ }
}

// Global function for section toggling
function toggleSection(element) {
    const content = element.nextElementSibling;
    const icon = element.querySelector('.section-icon');
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    } else {
        content.classList.add('collapsed');
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    }
}



