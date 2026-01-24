/**
 * MergerMeter Goals Calculator - Vanilla JavaScript Implementation
 *
 * A lightweight calculator for setting Community Benefits Agreement (CBA)
 * lending goals for bank mergers. Allows users to adjust improvement
 * percentages and agreement length to project lending goals.
 */

(function() {
    'use strict';

    // ========================================================================
    // UTILITY FUNCTIONS
    // ========================================================================

    function formatNumber(num, decimals = 0) {
        if (num === null || num === undefined || isNaN(num)) return '—';
        return num.toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }

    function formatCurrency(num, decimals = 0) {
        if (num === null || num === undefined || isNaN(num)) return '—';
        return '$' + formatNumber(num, decimals);
    }

    function formatCompact(num) {
        if (num === null || num === undefined || isNaN(num)) return '—';
        if (num >= 1e9) return '$' + (num / 1e9).toFixed(1) + 'B';
        if (num >= 1e6) return '$' + (num / 1e6).toFixed(1) + 'M';
        if (num >= 1e3) return '$' + (num / 1e3).toFixed(0) + 'K';
        return '$' + num.toLocaleString();
    }

    /**
     * Calculate goal from baseline
     * Formula: ((baseline / dataYears) * (1 + percent/100)) * agreementLength
     */
    function calculateGoal(baseline, dataYears, percent, agreementLength) {
        if (!baseline || !dataYears) return 0;
        const annualized = baseline / dataYears;
        const withIncrease = annualized * (1 + percent / 100);
        return Math.round(withIncrease * agreementLength);
    }

    // ========================================================================
    // GOALS CALCULATOR CLASS
    // ========================================================================

    function GoalsCalculator(options) {
        this.container = document.getElementById(options.containerId);
        this.mortgageData = options.mortgageData || {};
        this.sbData = options.sbData || {};
        this.bankName = options.bankName || 'Combined Entity';
        this.onExport = options.onExport || null;
        this.onSave = options.onSave || null;

        // State
        this.dataYears = options.defaultDataYears || 3;
        this.agreementLength = 5;
        this.hpPercent = 5;
        this.refiPercent = 5;
        this.hiPercent = 5;
        this.sbPercent = 5;
        this.activeTab = 'summary';

        // Get regions from data
        this.regions = this._getRegions();

        this.init();
    }

    GoalsCalculator.prototype._getRegions = function() {
        var mortgageRegions = Object.keys(this.mortgageData).filter(function(k) {
            return k !== 'Grand Total';
        });
        var sbRegions = Object.keys(this.sbData).filter(function(k) {
            return k !== 'Grand Total';
        });
        var allRegions = mortgageRegions.concat(sbRegions);
        var unique = [];
        allRegions.forEach(function(r) {
            if (unique.indexOf(r) === -1) unique.push(r);
        });
        return unique.sort();
    };

    GoalsCalculator.prototype.init = function() {
        this.render();
        this.bindEvents();
    };

    GoalsCalculator.prototype.getConfig = function() {
        return {
            dataYears: this.dataYears,
            agreementLength: this.agreementLength,
            hpPercent: this.hpPercent,
            refiPercent: this.refiPercent,
            hiPercent: this.hiPercent,
            sbPercent: this.sbPercent
        };
    };

    GoalsCalculator.prototype.render = function() {
        var self = this;
        var html = '';

        // Header
        html += '<div class="gc-header">';
        html += '<h2 class="gc-title">CBA Goals Calculator &mdash; ' + this._escapeHtml(this.bankName) + '</h2>';
        html += '<p class="gc-subtitle">Set improvement targets and agreement length to calculate Community Benefits Agreement lending goals</p>';
        html += '</div>';

        // Controls Panel
        html += '<div class="gc-controls">';
        html += this._renderControls();
        html += '</div>';

        // Tabs
        html += '<div class="gc-tabs">';
        html += this._renderTabs();
        html += '</div>';

        // Content
        html += '<div class="gc-content" id="gcContent">';
        html += this._renderTabContent();
        html += '</div>';

        // Action Buttons
        html += '<div class="gc-actions">';
        html += '<button class="gc-btn gc-btn-secondary" id="gcSaveBtn">Save Configuration</button>';
        html += '<button class="gc-btn gc-btn-primary" id="gcExportBtn">Export to Excel</button>';
        html += '</div>';

        this.container.innerHTML = html;
    };

    GoalsCalculator.prototype._renderControls = function() {
        var html = '';

        // Data Years dropdown
        html += '<div class="gc-control-group">';
        html += '<label class="gc-label">Baseline Data Years</label>';
        html += '<select id="gcDataYears" class="gc-select">';
        for (var y = 1; y <= 6; y++) {
            var selected = y === this.dataYears ? ' selected' : '';
            html += '<option value="' + y + '"' + selected + '>' + y + ' year' + (y > 1 ? 's' : '') + '</option>';
        }
        html += '</select>';
        html += '</div>';

        // Agreement Length dropdown
        html += '<div class="gc-control-group">';
        html += '<label class="gc-label">Agreement Length</label>';
        html += '<select id="gcAgreementLength" class="gc-select">';
        for (var y = 3; y <= 7; y++) {
            var selected = y === this.agreementLength ? ' selected' : '';
            html += '<option value="' + y + '"' + selected + '>' + y + ' years</option>';
        }
        html += '</select>';
        html += '</div>';

        // Sliders
        html += this._renderSlider('gcHpPercent', 'Home Purchase Improvement', this.hpPercent, '#034ea0');
        html += this._renderSlider('gcRefiPercent', 'Refinance Improvement', this.refiPercent, '#034ea0');
        html += this._renderSlider('gcHiPercent', 'Home Improvement', this.hiPercent, '#034ea0');
        html += this._renderSlider('gcSbPercent', 'Small Business Improvement', this.sbPercent, '#2e7d32');

        return html;
    };

    GoalsCalculator.prototype._renderSlider = function(id, label, value, color) {
        var html = '<div class="gc-control-group">';
        html += '<label class="gc-label">' + label + '</label>';
        html += '<input type="range" id="' + id + '" min="0" max="25" step="1" value="' + value + '" class="gc-slider" style="accent-color: ' + color + ';">';
        html += '<span class="gc-slider-value" id="' + id + 'Value" style="color: ' + color + ';">+' + value + '%</span>';
        html += '</div>';
        return html;
    };

    GoalsCalculator.prototype._renderTabs = function() {
        var self = this;
        var tabs = [
            { id: 'summary', label: 'Summary' },
            { id: 'grand-total', label: 'Grand Total' }
        ];

        this.regions.forEach(function(r) {
            tabs.push({ id: r, label: r });
        });

        var html = '';
        tabs.forEach(function(tab) {
            var activeClass = tab.id === self.activeTab ? ' gc-tab-active' : '';
            html += '<button class="gc-tab' + activeClass + '" data-tab="' + tab.id + '">' + self._escapeHtml(tab.label) + '</button>';
        });

        return html;
    };

    GoalsCalculator.prototype._renderTabContent = function() {
        if (this.activeTab === 'summary') {
            return this._renderSummaryTab();
        } else if (this.activeTab === 'grand-total') {
            return this._renderDetailTab('Grand Total');
        } else {
            return this._renderDetailTab(this.activeTab);
        }
    };

    GoalsCalculator.prototype._renderSummaryTab = function() {
        var grandTotal = this.mortgageData['Grand Total'] || {};
        var sbGrandTotal = this.sbData['Grand Total'] || {};

        // Calculate key goals
        var hpLoansGoal = calculateGoal(grandTotal.hp_loans, this.dataYears, this.hpPercent, this.agreementLength);
        var hpAmountGoal = calculateGoal(grandTotal.hp_amount, this.dataYears, this.hpPercent, this.agreementLength);
        var refiLoansGoal = calculateGoal(grandTotal.refi_loans, this.dataYears, this.refiPercent, this.agreementLength);
        var refiAmountGoal = calculateGoal(grandTotal.refi_amount, this.dataYears, this.refiPercent, this.agreementLength);
        var hiLoansGoal = calculateGoal(grandTotal.hi_loans, this.dataYears, this.hiPercent, this.agreementLength);
        var sbLoansGoal = calculateGoal(sbGrandTotal.sb_loans, this.dataYears, this.sbPercent, this.agreementLength);
        var sbAmountGoal = calculateGoal(sbGrandTotal.sb_amount, this.dataYears, this.sbPercent, this.agreementLength);

        var totalMortgageLoans = hpLoansGoal + refiLoansGoal + hiLoansGoal;
        var totalMortgageAmount = hpAmountGoal + refiAmountGoal;

        var html = '<h3 class="gc-section-title">Mortgage Lending Goals</h3>';
        html += '<div class="gc-summary-grid">';
        html += this._renderSummaryCard('Total Mortgage Loans', formatNumber(totalMortgageLoans), this.agreementLength + '-year commitment');
        html += this._renderSummaryCard('Total Mortgage Amount', formatCompact(totalMortgageAmount), 'HP: ' + formatCompact(hpAmountGoal) + ' | Refi: ' + formatCompact(refiAmountGoal));
        html += this._renderSummaryCard('Home Purchase Loans', formatNumber(hpLoansGoal), '+' + this.hpPercent + '% annual increase');
        html += this._renderSummaryCard('Refinance Loans', formatNumber(refiLoansGoal), '+' + this.refiPercent + '% annual increase');
        html += '</div>';

        html += '<h3 class="gc-section-title gc-section-title-sb">Small Business Lending Goals</h3>';
        html += '<div class="gc-summary-grid">';
        html += this._renderSummaryCard('Total SB Loans', formatNumber(sbLoansGoal), this.agreementLength + '-year commitment', '#2e7d32');
        html += this._renderSummaryCard('Total SB Amount', formatCompact(sbAmountGoal), '+' + this.sbPercent + '% annual increase', '#2e7d32');
        html += '</div>';

        return html;
    };

    GoalsCalculator.prototype._renderSummaryCard = function(title, value, subtext, color) {
        color = color || '#034ea0';
        var html = '<div class="gc-summary-card">';
        html += '<div class="gc-card-header">' + title + '</div>';
        html += '<div class="gc-card-value" style="color: ' + color + ';">' + value + '</div>';
        if (subtext) {
            html += '<div class="gc-card-subtext">' + subtext + '</div>';
        }
        html += '</div>';
        return html;
    };

    GoalsCalculator.prototype._renderDetailTab = function(stateName) {
        var mortgage = this.mortgageData[stateName] || {};
        var sb = this.sbData[stateName] || {};

        var html = '<h3 class="gc-section-title">Mortgage Lending Goals &mdash; ' + this._escapeHtml(stateName) + '</h3>';
        html += this._renderMortgageTable(mortgage);

        html += '<h3 class="gc-section-title gc-section-title-sb" style="margin-top: 40px;">Small Business Lending Goals &mdash; ' + this._escapeHtml(stateName) + '</h3>';
        html += this._renderSBTable(sb);

        return html;
    };

    GoalsCalculator.prototype._renderMortgageTable = function(data) {
        var self = this;
        var metrics = [
            { key: 'hp_loans', label: 'Home Purchase Loans', percent: this.hpPercent, isCurrency: false },
            { key: 'hp_amount', label: 'Home Purchase Amount', percent: this.hpPercent, isCurrency: true },
            { key: 'hp_lmi_loans', label: 'HP Loans to LMI Borrowers', percent: this.hpPercent, isCurrency: false },
            { key: 'hp_lmi_amount', label: 'HP Amount to LMI Borrowers', percent: this.hpPercent, isCurrency: true },
            { key: 'refi_loans', label: 'Refinance Loans', percent: this.refiPercent, isCurrency: false },
            { key: 'refi_amount', label: 'Refinance Amount', percent: this.refiPercent, isCurrency: true },
            { key: 'refi_lmi_loans', label: 'Refi Loans to LMI Borrowers', percent: this.refiPercent, isCurrency: false },
            { key: 'refi_lmi_amount', label: 'Refi Amount to LMI Borrowers', percent: this.refiPercent, isCurrency: true },
            { key: 'hi_loans', label: 'Home Improvement Loans', percent: this.hiPercent, isCurrency: false },
            { key: 'hi_amount', label: 'Home Improvement Amount', percent: this.hiPercent, isCurrency: true },
            { key: 'hi_lmi_loans', label: 'HI Loans to LMI Borrowers', percent: this.hiPercent, isCurrency: false }
        ];

        var html = '<div class="gc-table-wrapper"><table class="gc-table">';
        html += '<thead><tr>';
        html += '<th>Metric</th>';
        html += '<th class="gc-th-right">Baseline (' + this.dataYears + ' yr)</th>';
        html += '<th class="gc-th-right">Annual Avg</th>';
        html += '<th class="gc-th-right">Improvement</th>';
        html += '<th class="gc-th-right gc-th-goal">' + this.agreementLength + '-Year Goal</th>';
        html += '</tr></thead><tbody>';

        metrics.forEach(function(metric) {
            var baseline = data[metric.key] || 0;
            var annualAvg = baseline / self.dataYears;
            var goal = calculateGoal(baseline, self.dataYears, metric.percent, self.agreementLength);
            var formatter = metric.isCurrency ? formatCurrency : formatNumber;

            html += '<tr>';
            html += '<td class="gc-td-bold">' + metric.label + '</td>';
            html += '<td class="gc-td-right">' + formatter(baseline) + '</td>';
            html += '<td class="gc-td-right">' + formatter(annualAvg) + '</td>';
            html += '<td class="gc-td-right gc-td-blue">+' + metric.percent + '%</td>';
            html += '<td class="gc-td-right gc-td-goal">' + formatter(goal) + '</td>';
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        return html;
    };

    GoalsCalculator.prototype._renderSBTable = function(data) {
        var self = this;
        var metrics = [
            { key: 'sb_loans', label: 'Small Business Loans', isCurrency: false },
            { key: 'sb_amount', label: 'Small Business Amount', isCurrency: true },
            { key: 'sb_lmi_loans', label: 'SB Loans in LMI Tracts', isCurrency: false },
            { key: 'sb_lmi_amount', label: 'SB Amount in LMI Tracts', isCurrency: true },
            { key: 'sb_minority_loans', label: 'SB Loans in Minority Tracts', isCurrency: false },
            { key: 'sb_minority_amount', label: 'SB Amount in Minority Tracts', isCurrency: true }
        ];

        var html = '<div class="gc-table-wrapper"><table class="gc-table">';
        html += '<thead><tr>';
        html += '<th>Metric</th>';
        html += '<th class="gc-th-right">Baseline (' + this.dataYears + ' yr)</th>';
        html += '<th class="gc-th-right">Annual Avg</th>';
        html += '<th class="gc-th-right">Improvement</th>';
        html += '<th class="gc-th-right gc-th-goal-sb">' + this.agreementLength + '-Year Goal</th>';
        html += '</tr></thead><tbody>';

        metrics.forEach(function(metric) {
            var baseline = data[metric.key] || 0;
            var annualAvg = baseline / self.dataYears;
            var goal = calculateGoal(baseline, self.dataYears, self.sbPercent, self.agreementLength);
            var formatter = metric.isCurrency ? formatCurrency : formatNumber;

            html += '<tr>';
            html += '<td class="gc-td-bold">' + metric.label + '</td>';
            html += '<td class="gc-td-right">' + formatter(baseline) + '</td>';
            html += '<td class="gc-td-right">' + formatter(annualAvg) + '</td>';
            html += '<td class="gc-td-right gc-td-green">+' + self.sbPercent + '%</td>';
            html += '<td class="gc-td-right gc-td-goal-sb">' + formatter(goal) + '</td>';
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        return html;
    };

    GoalsCalculator.prototype.bindEvents = function() {
        var self = this;

        // Dropdowns
        document.getElementById('gcDataYears').addEventListener('change', function(e) {
            self.dataYears = parseInt(e.target.value);
            self.updateContent();
        });

        document.getElementById('gcAgreementLength').addEventListener('change', function(e) {
            self.agreementLength = parseInt(e.target.value);
            self.updateContent();
        });

        // Sliders
        var sliders = [
            { id: 'gcHpPercent', prop: 'hpPercent' },
            { id: 'gcRefiPercent', prop: 'refiPercent' },
            { id: 'gcHiPercent', prop: 'hiPercent' },
            { id: 'gcSbPercent', prop: 'sbPercent' }
        ];

        sliders.forEach(function(slider) {
            var el = document.getElementById(slider.id);
            var valueEl = document.getElementById(slider.id + 'Value');

            el.addEventListener('input', function(e) {
                var val = parseInt(e.target.value);
                self[slider.prop] = val;
                valueEl.textContent = '+' + val + '%';
                self.updateContent();
            });
        });

        // Tabs
        this.container.querySelectorAll('.gc-tab').forEach(function(tab) {
            tab.addEventListener('click', function(e) {
                self.activeTab = e.target.getAttribute('data-tab');
                self.updateTabs();
                self.updateContent();
            });
        });

        // Action buttons
        document.getElementById('gcExportBtn').addEventListener('click', function() {
            if (self.onExport) {
                self.onExport(self.getConfig());
            }
        });

        document.getElementById('gcSaveBtn').addEventListener('click', function() {
            if (self.onSave) {
                self.onSave(self.getConfig());
            } else {
                // Default: save to localStorage
                localStorage.setItem('mergerMeterGoalsConfig', JSON.stringify(self.getConfig()));
                alert('Configuration saved to local storage.');
            }
        });
    };

    GoalsCalculator.prototype.updateTabs = function() {
        var self = this;
        this.container.querySelectorAll('.gc-tab').forEach(function(tab) {
            if (tab.getAttribute('data-tab') === self.activeTab) {
                tab.classList.add('gc-tab-active');
            } else {
                tab.classList.remove('gc-tab-active');
            }
        });
    };

    GoalsCalculator.prototype.updateContent = function() {
        var contentEl = document.getElementById('gcContent');
        if (contentEl) {
            contentEl.innerHTML = this._renderTabContent();
        }
    };

    GoalsCalculator.prototype._escapeHtml = function(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    };

    // Export to global scope
    window.GoalsCalculator = GoalsCalculator;

})();
