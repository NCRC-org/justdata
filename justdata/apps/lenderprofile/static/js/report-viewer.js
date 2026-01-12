/**
 * LenderProfile Report Viewer
 * Uses ReportRenderer for client-side rendering to minimize AI token usage
 */

document.addEventListener('DOMContentLoaded', function() {
    const reportContent = document.getElementById('report-content');
    
    // Try to get report from sessionStorage first (from generate-report redirect)
    let reportData = null;
    const storedReport = sessionStorage.getItem('lenderprofile_report');
    if (storedReport) {
        try {
            reportData = JSON.parse(storedReport);
            sessionStorage.removeItem('lenderprofile_report'); // Clear after use
        } catch (e) {
            console.error('Error parsing stored report:', e);
        }
    }
    
    // If not in sessionStorage, try to get from global (template variable)
    if (!reportData && typeof window.reportData !== 'undefined' && window.reportData !== null) {
        reportData = window.reportData;
    }
    
    if (!reportData) {
        reportContent.innerHTML = `
            <div class="error-message">
                <p>Report data not available. Please generate a new report.</p>
                <a href="/" class="btn btn-primary" style="margin-top: 15px; display: inline-block;">
                    <i class="fas fa-arrow-left"></i> Back to Search
                </a>
            </div>
        `;
        return;
    }
    
    // Use ReportRenderer for client-side rendering
    const renderer = new ReportRenderer(reportData);
    renderer.render();
});

function renderReport(report) {
    const reportContent = document.getElementById('report-content');
    const sections = report.sections || {};
    const metadata = report.metadata || {};
    
    let html = '';
    
    // Section 1: Executive Summary
    if (sections.executive_summary) {
        const es = sections.executive_summary;
        html += `
            <div class="report-section">
                <h2 class="section-collapsible" onclick="toggleSection(this)">
                    <i class="fas fa-file-alt"></i> 1. Executive Summary
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    <div class="lender-summary-content" style="margin-bottom: 25px;">
                        <div class="lender-summary-item">
                            <span class="lender-summary-label">Institution</span>
                            <span class="lender-summary-value">${es.institution_name || 'N/A'}</span>
                        </div>
                        <div class="lender-summary-item">
                            <span class="lender-summary-label">Type</span>
                            <span class="lender-summary-value">${es.institution_type || 'N/A'}</span>
                        </div>
                        <div class="lender-summary-item">
                            <span class="lender-summary-label">Location</span>
                            <span class="lender-summary-value">${es.location || 'N/A'}</span>
                        </div>
                        <div class="lender-summary-item">
                            <span class="lender-summary-label">Assets</span>
                            <span class="lender-summary-value">${es.assets || 'N/A'}</span>
                        </div>
                    </div>
                    
                    ${es.ai_summary ? `<div class="ai-summary">${formatMarkdown(es.ai_summary)}</div>` : ''}
                    
                    ${es.key_findings ? `
                        <h3>Key Findings</h3>
                        <ul class="key-findings">${formatKeyFindings(es.key_findings)}</ul>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    // Section 2: Corporate Structure
    if (sections.corporate_structure) {
        const cs = sections.corporate_structure;
        html += `
            <div class="report-section">
                <h2 class="section-collapsible" onclick="toggleSection(this)">
                    <i class="fas fa-sitemap"></i> 2. Corporate Structure
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${cs.has_org_chart ? `
                        <div id="org-chart-container"></div>
                        <p>Organizational chart visualization will be rendered here.</p>
                    ` : '<p>Organizational data not available for this institution.</p>'}
                </div>
            </div>
        `;
    }
    
    // Section 3: Financial Profile
    if (sections.financial_profile) {
        const fp = sections.financial_profile;
        html += `
            <div class="report-section">
                <h2 class="section-collapsible" onclick="toggleSection(this)">
                    <i class="fas fa-chart-line"></i> 3. Financial Profile
                    <i class="fas fa-chevron-down section-icon"></i>
                </h2>
                <div class="section-content">
                    ${fp.trends && fp.trends.years ? `
                        <div class="chart-container">
                            <canvas id="financial-trends-chart"></canvas>
                        </div>
                    ` : '<p>Financial data not available.</p>'}
                </div>
            </div>
        `;
    }
    
    // Add remaining sections...
    // (Sections 4-12 will be added similarly)
    
    reportContent.innerHTML = html;
    
    // Render charts if data available
    if (sections.financial_profile && sections.financial_profile.trends) {
        renderFinancialChart(sections.financial_profile.trends);
    }
}

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

function formatMarkdown(text) {
    if (!text) return '';
    
    // Simple markdown to HTML conversion
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
    text = text.replace(/\n\n/g, '</p><p>');
    text = text.replace(/\n/g, '<br>');
    
    return `<p>${text}</p>`;
}

function formatKeyFindings(text) {
    if (!text) return '';
    
    // Parse key findings format: • **Title:** Sentence
    const findings = text.split('•').filter(f => f.trim());
    return findings.map(f => {
        const match = f.match(/\*\*(.*?)\*\*:\s*(.*)/);
        if (match) {
            return `<li><strong>${match[1]}:</strong> ${match[2]}</li>`;
        }
        return `<li>${f.trim()}</li>`;
    }).join('');
}

function renderFinancialChart(trends) {
    const ctx = document.getElementById('financial-trends-chart');
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: trends.years || [],
            datasets: [
                {
                    label: 'Assets',
                    data: trends.assets || [],
                    borderColor: 'rgb(85, 45, 135)',
                    tension: 0.1
                },
                {
                    label: 'Equity',
                    data: trends.equity || [],
                    borderColor: 'rgb(47, 173, 227)',
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: '5-Year Financial Trends'
                }
            }
        }
    });
}

