/**
 * MergerMeter Goals Calculator - Vanilla JavaScript Implementation
 * Matches the React design with full metric breakdowns
 */

(function() {
    'use strict';

    // ========================================================================
    // UTILITY FUNCTIONS
    // ========================================================================

    function formatNum(v) {
        if (v === null || v === undefined || isNaN(v)) return '—';
        return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Math.round(v));
    }

    function formatCurrency(v) {
        if (v === null || v === undefined || isNaN(v)) return '—';
        if (v >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B';
        if (v >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M';
        if (v >= 1e3) return '$' + (v / 1e3).toFixed(0) + 'K';
        return '$' + Math.round(v);
    }

    function formatFullCurrency(v) {
        if (v === null || v === undefined || isNaN(v)) return '—';
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v);
    }

    function formatAssets(v) {
        if (!v) return '—';
        return v >= 1e9 ? '$' + (v / 1e9).toFixed(1) + 'B' : '$' + (v / 1e6).toFixed(0) + 'M';
    }

    /**
     * Calculate goal from baseline
     * Formula: ((baseline / dataYears) * (1 + percent/100)) * agreementLength
     */
    function calcGoal(baseline, dataYears, percent, agreementLength) {
        if (!baseline || !dataYears) return 0;
        return ((baseline / dataYears) * (1 + percent / 100)) * agreementLength;
    }

    function calcBaseline(baseline, dataYears, agreementLength) {
        if (!baseline || !dataYears) return 0;
        return (baseline / dataYears) * agreementLength;
    }

    // ========================================================================
    // GOALS CALCULATOR CLASS
    // ========================================================================

    function GoalsCalculator(options) {
        this.container = document.getElementById(options.containerId);
        this.mortgageData = options.mortgageData || {};
        this.sbData = options.sbData || {};
        this.bankName = options.bankName || 'Combined Entity';
        this.bankInfo = options.bankInfo || {};
        this.singleBankMode = options.singleBankMode || false;
        this.onExport = options.onExport || null;
        this.onSave = options.onSave || null;

        // State
        this.dataYears = options.defaultDataYears || 3;
        this.agreementLength = 5;
        this.hpPercent = 10;
        this.refiPercent = 25;
        this.hiPercent = 0;
        this.sbPercent = 20;
        this.activeTab = 'summary';
        this.activeSubTab = 'mortgage';

        // Get regions from data
        this.regions = this._getRegions();

        // Metric definitions
        this.metricLabels = {
            'Loans': 'Loans',
            '~LMICT': 'Low-Mod Income Census Tracts',
            '~LMIB': 'Low-Mod Income Borrowers',
            'LMIB$': 'LMI Borrower Dollars',
            '~MMCT': 'Majority-Minority Census Tracts',
            '~MINB': 'Minority Borrowers',
            '~Asian': 'Asian Borrowers',
            '~Black': 'Black Borrowers',
            '~Native American': 'Native American Borrowers',
            '~HoPI': 'Hawaiian/Pacific Islander',
            '~Hispanic': 'Hispanic Borrowers'
        };

        this.metricOrder = ['Loans', '~LMICT', '~LMIB', 'LMIB$', '~MMCT', '~MINB', '~Asian', '~Black', '~Native American', '~HoPI', '~Hispanic'];

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

    // ========================================================================
    // RENDER METHODS
    // ========================================================================

    GoalsCalculator.prototype.render = function() {
        var html = '';

        // Note: Header is now provided by shared_header.html in the template
        // This component only renders the content area

        // Bank Info
        html += this._renderBankInfo();

        // Main content
        html += '<main style="max-width: 1200px; margin: 0 auto; padding: 20px;">';

        // Controls
        html += this._renderControls();

        // Tabs
        html += this._renderTabs();

        // Content
        html += '<div id="gcContent">';
        html += this._renderTabContent();
        html += '</div>';

        // Actions
        html += '<div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px;">';
        html += '<button id="gcExportBtn" style="padding: 10px 20px; background: white; border: 1px solid #034ea0; color: #034ea0; border-radius: 4px; font-weight: 500; font-size: 13px; cursor: pointer;">Export to Excel</button>';
        html += '<button id="gcSaveBtn" style="padding: 10px 20px; background: #034ea0; border: none; color: white; border-radius: 4px; font-weight: 500; font-size: 13px; cursor: pointer;">Save Configuration</button>';
        html += '</div>';

        html += '</main>';

        // Slider styles
        html += '<style>';
        html += 'input[type="range"]::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%; background: white; border: 2px solid currentColor; cursor: pointer; box-shadow: 0 1px 2px rgba(0,0,0,0.2); }';
        html += 'input[type="range"]::-moz-range-thumb { width: 16px; height: 16px; border-radius: 50%; background: white; border: 2px solid currentColor; cursor: pointer; }';
        html += '</style>';

        this.container.innerHTML = html;
    };

    GoalsCalculator.prototype._renderBankInfo = function() {
        var bankA = this.bankInfo.acquirer || {};
        var bankB = this.bankInfo.target || {};
        var isSingleBank = this.singleBankMode;

        var html = '<div style="background: white; border-bottom: 1px solid #e0e0e0;">';
        html += '<div style="max-width: 1200px; margin: 0 auto; padding: 14px 20px;">';

        // Banner - different messaging for single bank vs merger
        html += '<div style="background: linear-gradient(135deg, #e3f2fd 0%, #fff3e0 100%); border: 1px solid #90caf9; border-radius: 6px; padding: 12px 16px; margin-bottom: 14px;">';
        html += '<div style="display: flex; align-items: center; gap: 10px;">';
        html += '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#034ea0" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>';
        html += '<div>';
        if (isSingleBank) {
            html += '<div style="font-size: 13px; font-weight: 600; color: #034ea0;">CBA Goals Calculator</div>';
            html += '<div style="font-size: 12px; color: #555;">These goals reflect <strong>lending commitments</strong> for the institution, calculated from historical lending over the baseline data period.</div>';
        } else {
            html += '<div style="font-size: 13px; font-weight: 600; color: #034ea0;">Combined Entity CBA Goals</div>';
            html += '<div style="font-size: 12px; color: #555;">These goals reflect the <strong>combined lending commitments</strong> for the merged institution, calculated from the historical lending of <strong>both banks</strong> over the baseline data period.</div>';
        }
        html += '</div></div></div>';

        // Bank info - single column for single bank, grid for merger
        if (isSingleBank) {
            // Single bank layout - centered
            html += '<div style="max-width: 400px; margin: 0 auto;">';
            html += '<div style="background: #f8f9fa; border-radius: 6px; padding: 12px;">';
            html += '<div style="font-size: 10px; text-transform: uppercase; color: #888; margin-bottom: 4px;">Subject Bank</div>';
            html += '<div style="font-size: 15px; font-weight: 600; color: #034ea0; margin-bottom: 6px;">' + this._escapeHtml(bankA.name || 'N/A') + '</div>';
            html += '<div style="font-size: 12px; color: #555; line-height: 1.6;">';
            if (bankA.city || bankA.state) {
                html += '<div>';
                if (bankA.city) html += this._escapeHtml(bankA.city);
                if (bankA.state) html += (bankA.city ? ', ' : '') + this._escapeHtml(bankA.state);
                html += '</div>';
            }
            if (bankA.totalAssets) html += '<div>Assets: ' + formatAssets(bankA.totalAssets) + '</div>';
            if (bankA.lei) html += '<div style="font-size: 11px; color: #777;">LEI: ' + this._escapeHtml(bankA.lei) + '</div>';
            if (bankA.rssd) html += '<div style="font-size: 11px; color: #777;">RSSD: ' + this._escapeHtml(bankA.rssd) + '</div>';
            if (bankA.respondentId) html += '<div style="font-size: 11px; color: #777;">Respondent ID: ' + this._escapeHtml(bankA.respondentId) + '</div>';
            html += '</div></div></div>';
        } else {
            // Merger layout - two banks with plus symbol
            html += '<div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 24px; align-items: start;">';

            // Acquirer
            html += '<div style="background: #f8f9fa; border-radius: 6px; padding: 12px;">';
            html += '<div style="font-size: 10px; text-transform: uppercase; color: #888; margin-bottom: 4px;">Acquiring Bank</div>';
            html += '<div style="font-size: 15px; font-weight: 600; color: #034ea0; margin-bottom: 6px;">' + this._escapeHtml(bankA.name || 'N/A') + '</div>';
            html += '<div style="font-size: 12px; color: #555; line-height: 1.6;">';
            if (bankA.city || bankA.state) {
                html += '<div>';
                if (bankA.city) html += this._escapeHtml(bankA.city);
                if (bankA.state) html += (bankA.city ? ', ' : '') + this._escapeHtml(bankA.state);
                html += '</div>';
            }
            if (bankA.totalAssets) html += '<div>Assets: ' + formatAssets(bankA.totalAssets) + '</div>';
            if (bankA.lei) html += '<div style="font-size: 11px; color: #777;">LEI: ' + this._escapeHtml(bankA.lei) + '</div>';
            if (bankA.rssd) html += '<div style="font-size: 11px; color: #777;">RSSD: ' + this._escapeHtml(bankA.rssd) + '</div>';
            if (bankA.respondentId) html += '<div style="font-size: 11px; color: #777;">Respondent ID: ' + this._escapeHtml(bankA.respondentId) + '</div>';
            html += '</div></div>';

            // Plus symbol
            html += '<div style="font-size: 28px; color: #034ea0; font-weight: 300; padding-top: 30px;">+</div>';

            // Target
            html += '<div style="background: #f8f9fa; border-radius: 6px; padding: 12px;">';
            html += '<div style="font-size: 10px; text-transform: uppercase; color: #888; margin-bottom: 4px;">Target Bank</div>';
            html += '<div style="font-size: 15px; font-weight: 600; color: #034ea0; margin-bottom: 6px;">' + this._escapeHtml(bankB.name || 'N/A') + '</div>';
            html += '<div style="font-size: 12px; color: #555; line-height: 1.6;">';
            if (bankB.city || bankB.state) {
                html += '<div>';
                if (bankB.city) html += this._escapeHtml(bankB.city);
                if (bankB.state) html += (bankB.city ? ', ' : '') + this._escapeHtml(bankB.state);
                html += '</div>';
            }
            if (bankB.totalAssets) html += '<div>Assets: ' + formatAssets(bankB.totalAssets) + '</div>';
            if (bankB.lei) html += '<div style="font-size: 11px; color: #777;">LEI: ' + this._escapeHtml(bankB.lei) + '</div>';
            if (bankB.rssd) html += '<div style="font-size: 11px; color: #777;">RSSD: ' + this._escapeHtml(bankB.rssd) + '</div>';
            if (bankB.respondentId) html += '<div style="font-size: 11px; color: #777;">Respondent ID: ' + this._escapeHtml(bankB.respondentId) + '</div>';
            html += '</div></div>';

            html += '</div>';
        }

        html += '</div></div>';
        return html;
    };

    GoalsCalculator.prototype._renderControls = function() {
        var self = this;
        var html = '<div style="background: white; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); padding: 20px; margin-bottom: 20px;">';

        html += '<div style="display: grid; grid-template-columns: 160px 100px 1fr; gap: 24px; align-items: end;">';

        // Agreement Length buttons
        html += '<div>';
        html += '<label style="display: block; font-size: 11px; font-weight: 500; margin-bottom: 8px; color: #444;">Agreement Length</label>';
        html += '<div style="display: flex; gap: 4px;">';
        [3, 4, 5, 6, 7].forEach(function(y) {
            var isActive = y === self.agreementLength;
            html += '<button class="gc-agreement-btn" data-years="' + y + '" style="flex: 1; padding: 8px 4px; border-radius: 4px; border: ' + (isActive ? '2px solid #034ea0' : '1px solid #ddd') + '; background: ' + (isActive ? '#034ea0' : 'white') + '; color: ' + (isActive ? 'white' : '#333') + '; font-weight: 500; font-size: 12px; cursor: pointer;">' + y + '</button>';
        });
        html += '</div></div>';

        // Data Years dropdown
        html += '<div>';
        html += '<label style="display: block; font-size: 11px; font-weight: 500; margin-bottom: 8px; color: #444;">Data Years</label>';
        html += '<select id="gcDataYears" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #ddd; font-size: 13px;">';
        for (var y = 1; y <= 6; y++) {
            var selected = y === this.dataYears ? ' selected' : '';
            html += '<option value="' + y + '"' + selected + '>' + y + ' year' + (y > 1 ? 's' : '') + '</option>';
        }
        html += '</select></div>';

        // Sliders
        html += '<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">';
        html += this._renderSlider('gcHpPercent', 'Home Purchase', this.hpPercent, '#034ea0');
        html += this._renderSlider('gcRefiPercent', 'Refinance', this.refiPercent, '#034ea0');
        html += this._renderSlider('gcHiPercent', 'Home Improvement', this.hiPercent, '#034ea0');
        html += this._renderSlider('gcSbPercent', 'Small Business', this.sbPercent, '#2e7d32');
        html += '</div>';

        html += '</div>';

        // Info text - different for single bank vs merger
        html += '<div style="margin-top: 12px; font-size: 12px; color: #666;">';
        if (this.singleBankMode) {
            html += 'Baseline data reflects <strong>historical lending</strong> over <strong>' + this.dataYears + ' year' + (this.dataYears > 1 ? 's' : '') + '</strong>. ';
            html += 'Goals represent commitments over a <strong>' + this.agreementLength + '-year</strong> agreement period.';
        } else {
            html += 'Baseline data reflects <strong>combined lending from both institutions</strong> over <strong>' + this.dataYears + ' year' + (this.dataYears > 1 ? 's' : '') + '</strong>. ';
            html += 'Goals represent commitments for the <strong>merged entity</strong> over a <strong>' + this.agreementLength + '-year</strong> agreement period.';
        }
        html += '</div>';

        html += '</div>';
        return html;
    };

    GoalsCalculator.prototype._renderSlider = function(id, label, value, color) {
        var pct = (value / 25) * 100;
        var html = '<div>';
        html += '<label style="display: block; font-size: 11px; font-weight: 500; margin-bottom: 6px; color: #444;">' + label + '</label>';
        html += '<div style="display: flex; align-items: center; gap: 10px;">';
        html += '<input type="range" id="' + id + '" min="0" max="25" value="' + value + '" style="flex: 1; height: 6px; border-radius: 3px; background: linear-gradient(to right, ' + color + ' ' + pct + '%, #ddd ' + pct + '%); appearance: none; -webkit-appearance: none; cursor: pointer;">';
        html += '<span id="' + id + 'Value" style="min-width: 42px; font-weight: 700; font-size: 14px; color: ' + color + '; text-align: right;">' + value + '%</span>';
        html += '</div></div>';
        return html;
    };

    GoalsCalculator.prototype._renderTabs = function() {
        var self = this;
        var tabs = [
            { id: 'summary', label: 'Summary' },
            { id: 'grand-total', label: 'Grand Total' }
        ];

        this.regions.forEach(function(r) {
            tabs.push({ id: r.toLowerCase().replace(/ /g, '-'), label: r });
        });

        var html = '<div class="gc-tabs-container" style="display: flex; gap: 2px; border-bottom: 2px solid #ddd; margin-bottom: 20px; overflow-x: auto; flex-wrap: nowrap; -webkit-overflow-scrolling: touch; scrollbar-width: thin;">';
        tabs.forEach(function(tab) {
            var isActive = tab.id === self.activeTab;
            html += '<button class="gc-tab" data-tab="' + tab.id + '" style="padding: 10px 16px; background: ' + (isActive ? 'white' : '#f0f0f0') + '; border: ' + (isActive ? '1px solid #ddd' : 'none') + '; border-bottom: ' + (isActive ? '2px solid white' : 'none') + '; border-radius: 4px 4px 0 0; margin-bottom: ' + (isActive ? '-2px' : '0') + '; color: ' + (isActive ? '#034ea0' : '#666') + '; font-weight: ' + (isActive ? '600' : '400') + '; font-size: 13px; cursor: pointer; flex-shrink: 0; white-space: nowrap;">' + self._escapeHtml(tab.label) + '</button>';
        });
        html += '</div>';
        return html;
    };

    GoalsCalculator.prototype._renderTabContent = function() {
        if (this.activeTab === 'summary') {
            return this._renderSummaryTab();
        } else if (this.activeTab === 'grand-total') {
            return this._renderDetailTab('Grand Total');
        } else {
            // Find matching region
            var self = this;
            var region = this.regions.find(function(r) {
                return r.toLowerCase().replace(/ /g, '-') === self.activeTab;
            });
            return this._renderDetailTab(region || 'Grand Total');
        }
    };

    // ========================================================================
    // SUMMARY TAB
    // ========================================================================

    GoalsCalculator.prototype._renderSummaryTab = function() {
        var grandMortgage = this.mortgageData['Grand Total'] || {};
        var grandSB = this.sbData['Grand Total'] || {};

        // Calculate LMIB$ totals
        var lmibData = grandMortgage['LMIB$'] || { hp: 0, refi: 0, hi: 0 };
        var lmibBaseline = (lmibData.hp || 0) + (lmibData.refi || 0) + (lmibData.hi || 0);
        var lmibGoal = calcGoal(lmibData.hp || 0, this.dataYears, this.hpPercent, this.agreementLength) +
                       calcGoal(lmibData.refi || 0, this.dataYears, this.refiPercent, this.agreementLength) +
                       calcGoal(lmibData.hi || 0, this.dataYears, this.hiPercent, this.agreementLength);
        var lmibBaselineOverPeriod = calcBaseline(lmibBaseline, this.dataYears, this.agreementLength);
        var lmibIncrease = lmibGoal - lmibBaselineOverPeriod;

        // Calculate SB totals
        var sbLmictTotal = (grandSB['#LMICT'] || 0) * (grandSB['Avg SB LMICT Loan Amount'] || 0);
        var sbRevTotal = (grandSB['Loans Rev Under $1m'] || 0) * (grandSB['Avg Loan Amt for <$1M GAR SB'] || 0);
        var sbBaseline = sbLmictTotal + sbRevTotal;
        var sbGoal = calcGoal(sbBaseline, this.dataYears, this.sbPercent, this.agreementLength);
        var sbBaselineOverPeriod = calcBaseline(sbBaseline, this.dataYears, this.agreementLength);
        var sbIncrease = sbGoal - sbBaselineOverPeriod;

        var html = '';

        // Context banner - different messaging for single bank vs merger
        html += '<div style="background: #f8f9fa; border-left: 4px solid #034ea0; padding: 12px 16px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">';
        if (this.singleBankMode) {
            html += '<div style="font-size: 13px; color: #444;"><strong>Summary of Proposed CBA Goals</strong> — These totals represent lending commitments based on ' + this.dataYears + '-year historical data from ' + this._escapeHtml((this.bankInfo.acquirer || {}).name || 'the subject bank') + '.</div>';
        } else {
            html += '<div style="font-size: 13px; color: #444;"><strong>Summary of Proposed CBA Goals</strong> — These totals represent lending commitments for the combined entity, based on ' + this.dataYears + '-year historical data from both ' + this._escapeHtml((this.bankInfo.acquirer || {}).name || 'the acquiring bank') + ' and ' + this._escapeHtml((this.bankInfo.target || {}).name || 'the target bank') + '.</div>';
        }
        html += '</div>';

        html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">';

        // Mortgage Card - LMI BORROWERS (not census tracts)
        html += '<div style="background: white; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow: hidden;">';
        html += '<div style="background: #034ea0; color: white; padding: 14px 20px;">';
        html += '<div style="font-size: 14px; font-weight: 600;">Mortgage Lending to LMI Borrowers</div>';
        html += '<div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">Loans to borrowers earning ≤80% of area median income</div>';
        html += '</div>';
        html += '<div style="padding: 28px 24px; text-align: center;">';
        html += '<div style="font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Total Increase Over ' + this.agreementLength + ' Years</div>';
        html += '<div style="font-size: 48px; font-weight: 700; color: #034ea0; line-height: 1;">' + formatCurrency(lmibIncrease) + '</div>';
        html += '<div style="margin-top: 24px; background: #f5f7fa; border-radius: 4px; padding: 14px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; text-align: left;">';
        html += '<div><div style="font-size: 10px; color: #666; text-transform: uppercase;">Baseline (' + this.agreementLength + ' yr)</div>';
        html += '<div style="font-size: 20px; font-weight: 600; color: #666;">' + formatCurrency(lmibBaselineOverPeriod) + '</div></div>';
        html += '<div><div style="font-size: 10px; color: #666; text-transform: uppercase;">NCRC Proposal</div>';
        html += '<div style="font-size: 20px; font-weight: 700; color: #034ea0;">' + formatCurrency(lmibGoal) + '</div></div>';
        html += '</div></div></div>';

        // SB Card - Show breakdown of LMICT vs <$1M Revenue
        var sbLmictIncrease = calcGoal(sbLmictTotal, this.dataYears, this.sbPercent, this.agreementLength) - calcBaseline(sbLmictTotal, this.dataYears, this.agreementLength);
        var sbRevIncrease = calcGoal(sbRevTotal, this.dataYears, this.sbPercent, this.agreementLength) - calcBaseline(sbRevTotal, this.dataYears, this.agreementLength);

        html += '<div style="background: white; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow: hidden;">';
        html += '<div style="background: #2e7d32; color: white; padding: 14px 20px;">';
        html += '<div style="font-size: 14px; font-weight: 600;">Small Business Lending</div>';
        html += '<div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">LMI census tracts + businesses &lt;$1M revenue</div>';
        html += '</div>';
        html += '<div style="padding: 28px 24px; text-align: center;">';
        html += '<div style="font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Total Increase Over ' + this.agreementLength + ' Years</div>';
        html += '<div style="font-size: 48px; font-weight: 700; color: #2e7d32; line-height: 1;">' + formatCurrency(sbIncrease) + '</div>';

        // Breakdown section
        html += '<div style="margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; text-align: left; font-size: 12px;">';
        html += '<div style="background: #e8f5e9; padding: 8px 10px; border-radius: 4px;"><div style="color: #666; font-size: 10px;">LMI Census Tracts</div><div style="color: #2e7d32; font-weight: 600;">+' + formatCurrency(sbLmictIncrease) + '</div></div>';
        html += '<div style="background: #e8f5e9; padding: 8px 10px; border-radius: 4px;"><div style="color: #666; font-size: 10px;">Businesses &lt;$1M Rev</div><div style="color: #2e7d32; font-weight: 600;">+' + formatCurrency(sbRevIncrease) + '</div></div>';
        html += '</div>';

        html += '<div style="margin-top: 16px; background: #f5f7fa; border-radius: 4px; padding: 14px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; text-align: left;">';
        html += '<div><div style="font-size: 10px; color: #666; text-transform: uppercase;">Baseline (' + this.agreementLength + ' yr)</div>';
        html += '<div style="font-size: 20px; font-weight: 600; color: #666;">' + formatCurrency(sbBaselineOverPeriod) + '</div></div>';
        html += '<div><div style="font-size: 10px; color: #666; text-transform: uppercase;">NCRC Proposal</div>';
        html += '<div style="font-size: 20px; font-weight: 700; color: #2e7d32;">' + formatCurrency(sbGoal) + '</div></div>';
        html += '</div></div></div>';

        html += '</div>';
        return html;
    };

    // ========================================================================
    // DETAIL TAB (with sub-tabs)
    // ========================================================================

    GoalsCalculator.prototype._renderDetailTab = function(stateName) {
        var self = this;
        var html = '<div>';

        html += '<h3 style="font-size: 18px; font-weight: 600; margin-bottom: 8px; color: #333;">';
        html += stateName === 'Grand Total' ? 'All States Combined' : this._escapeHtml(stateName);
        html += '</h3>';

        // Context note - different for single bank vs merger
        html += '<p style="font-size: 12px; color: #666; margin: 0 0 16px 0;">';
        if (this.singleBankMode) {
            html += 'Goals based on ' + this.dataYears + '-year historical lending data.';
        } else {
            html += 'Goals for the combined entity based on ' + this.dataYears + '-year lending data from both institutions.';
        }
        html += '</p>';

        // Sub-tabs
        html += '<div style="display: flex; gap: 4px; margin-bottom: 20px;">';
        html += '<button class="gc-subtab" data-subtab="mortgage" style="padding: 10px 20px; background: ' + (this.activeSubTab === 'mortgage' ? '#034ea0' : '#f0f0f0') + '; color: ' + (this.activeSubTab === 'mortgage' ? 'white' : '#666') + '; border: none; border-radius: 4px; font-weight: 500; font-size: 13px; cursor: pointer;">Mortgage Goals</button>';
        html += '<button class="gc-subtab" data-subtab="sb" style="padding: 10px 20px; background: ' + (this.activeSubTab === 'sb' ? '#2e7d32' : '#f0f0f0') + '; color: ' + (this.activeSubTab === 'sb' ? 'white' : '#666') + '; border: none; border-radius: 4px; font-weight: 500; font-size: 13px; cursor: pointer;">Small Business Goals</button>';
        html += '</div>';

        if (this.activeSubTab === 'mortgage') {
            html += this._renderMortgageTable(stateName);
        } else {
            html += this._renderSBTable(stateName);
        }

        html += '</div>';
        return html;
    };

    // ========================================================================
    // MORTGAGE GOALS TABLE
    // ========================================================================

    GoalsCalculator.prototype._renderMortgageTable = function(stateName) {
        var self = this;
        var data = this.mortgageData[stateName] || this.mortgageData['Grand Total'] || {};

        var html = '<div style="background: white; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow: hidden;">';
        html += '<div style="overflow-x: auto;">';
        html += '<table style="width: 100%; border-collapse: collapse; font-size: 13px; min-width: 900px;">';

        // Header row 1
        html += '<thead><tr style="background: #034ea0; color: white;">';
        html += '<th style="padding: 12px 14px; text-align: left; font-weight: 600; position: sticky; left: 0; background: #034ea0; z-index: 1;">Metric</th>';
        html += '<th colspan="3" style="padding: 10px 14px; text-align: center; font-weight: 600; border-left: 1px solid rgba(255,255,255,0.2);">Baseline (Data)</th>';
        html += '<th style="padding: 10px 14px; text-align: center; font-weight: 600; border-left: 1px solid rgba(255,255,255,0.2);">Total</th>';
        html += '<th colspan="3" style="padding: 10px 14px; text-align: center; font-weight: 600; border-left: 1px solid rgba(255,255,255,0.2);">' + this.agreementLength + '-Year Goals</th>';
        html += '<th style="padding: 10px 14px; text-align: center; font-weight: 600; border-left: 1px solid rgba(255,255,255,0.2);">NCRC Proposal</th>';
        html += '</tr>';

        // Header row 2
        html += '<tr style="background: #f0f4f8;">';
        html += '<th style="padding: 8px 14px; text-align: left; font-weight: 500; font-size: 11px; color: #666; position: sticky; left: 0; background: #f0f4f8; z-index: 1;"></th>';
        html += '<th style="padding: 8px 10px; text-align: right; font-weight: 500; font-size: 11px; color: #666;">Home Purch</th>';
        html += '<th style="padding: 8px 10px; text-align: right; font-weight: 500; font-size: 11px; color: #666;">Refinance</th>';
        html += '<th style="padding: 8px 10px; text-align: right; font-weight: 500; font-size: 11px; color: #666;">Home Improv</th>';
        html += '<th style="padding: 8px 10px; text-align: right; font-weight: 500; font-size: 11px; color: #666; border-left: 1px solid #ddd;"></th>';
        html += '<th style="padding: 8px 10px; text-align: right; font-weight: 500; font-size: 11px; color: #034ea0;">HP (' + this.hpPercent + '%)</th>';
        html += '<th style="padding: 8px 10px; text-align: right; font-weight: 500; font-size: 11px; color: #034ea0;">Refi (' + this.refiPercent + '%)</th>';
        html += '<th style="padding: 8px 10px; text-align: right; font-weight: 500; font-size: 11px; color: #034ea0;">HI (' + this.hiPercent + '%)</th>';
        html += '<th style="padding: 8px 10px; text-align: right; font-weight: 500; font-size: 11px; color: #034ea0; border-left: 1px solid #ddd;">Total</th>';
        html += '</tr></thead>';

        // Body
        html += '<tbody>';
        this.metricOrder.forEach(function(metric, idx) {
            var row = data[metric] || { hp: 0, refi: 0, hi: 0 };
            var total = (row.hp || 0) + (row.refi || 0) + (row.hi || 0);
            var hpGoal = calcGoal(row.hp || 0, self.dataYears, self.hpPercent, self.agreementLength);
            var refiGoal = calcGoal(row.refi || 0, self.dataYears, self.refiPercent, self.agreementLength);
            var hiGoal = calcGoal(row.hi || 0, self.dataYears, self.hiPercent, self.agreementLength);
            var totalGoal = hpGoal + refiGoal + hiGoal;
            var isCurrency = metric === 'LMIB$';
            var fmt = isCurrency ? formatFullCurrency : formatNum;
            var bgColor = idx % 2 === 0 ? 'white' : '#fafafa';

            html += '<tr style="background: ' + bgColor + ';">';
            html += '<td style="padding: 10px 14px; font-weight: 500; border-bottom: 1px solid #eee; position: sticky; left: 0; background: ' + bgColor + '; z-index: 1;">' + self.metricLabels[metric] + '</td>';
            html += '<td style="padding: 10px 10px; text-align: right; border-bottom: 1px solid #eee;">' + fmt(row.hp || 0) + '</td>';
            html += '<td style="padding: 10px 10px; text-align: right; border-bottom: 1px solid #eee;">' + fmt(row.refi || 0) + '</td>';
            html += '<td style="padding: 10px 10px; text-align: right; border-bottom: 1px solid #eee;">' + fmt(row.hi || 0) + '</td>';
            html += '<td style="padding: 10px 10px; text-align: right; border-bottom: 1px solid #eee; font-weight: 600; border-left: 1px solid #eee;">' + fmt(total) + '</td>';
            html += '<td style="padding: 10px 10px; text-align: right; border-bottom: 1px solid #eee; color: #034ea0;">' + fmt(hpGoal) + '</td>';
            html += '<td style="padding: 10px 10px; text-align: right; border-bottom: 1px solid #eee; color: #034ea0;">' + fmt(refiGoal) + '</td>';
            html += '<td style="padding: 10px 10px; text-align: right; border-bottom: 1px solid #eee; color: #034ea0;">' + fmt(hiGoal) + '</td>';
            html += '<td style="padding: 10px 10px; text-align: right; border-bottom: 1px solid #eee; font-weight: 600; color: #034ea0; border-left: 1px solid #eee;">' + fmt(totalGoal) + '</td>';
            html += '</tr>';
        });
        html += '</tbody></table></div>';

        // LMIB$ Summary
        var lmibData = data['LMIB$'] || { hp: 0, refi: 0, hi: 0 };
        var lmibBaseline = (lmibData.hp || 0) + (lmibData.refi || 0) + (lmibData.hi || 0);
        var lmibGoal = calcGoal(lmibData.hp || 0, this.dataYears, this.hpPercent, this.agreementLength) +
                       calcGoal(lmibData.refi || 0, this.dataYears, this.refiPercent, this.agreementLength) +
                       calcGoal(lmibData.hi || 0, this.dataYears, this.hiPercent, this.agreementLength);
        var lmibBaselineOverPeriod = calcBaseline(lmibBaseline, this.dataYears, this.agreementLength);
        var lmibIncrease = lmibGoal - lmibBaselineOverPeriod;

        html += '<div style="background: #e3f2fd; padding: 16px 20px; border-top: 2px solid #034ea0;">';
        html += '<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">';
        html += '<div><span style="font-size: 13px; color: #666;">LMI Borrower Lending Increase: </span>';
        html += '<span style="font-size: 20px; font-weight: 700; color: #034ea0;">' + formatFullCurrency(lmibIncrease) + '</span></div>';
        html += '<div style="font-size: 12px; color: #666;">Baseline: ' + formatFullCurrency(lmibBaselineOverPeriod) + ' → Goal: ' + formatFullCurrency(lmibGoal) + '</div>';
        html += '</div></div>';

        html += '</div>';
        return html;
    };

    // ========================================================================
    // SMALL BUSINESS GOALS TABLE
    // ========================================================================

    GoalsCalculator.prototype._renderSBTable = function(stateName) {
        var self = this;
        var data = this.sbData[stateName] || this.sbData['Grand Total'] || {};

        // Total SB Loans (for display - no dollar goals, just count)
        var totalSBLoans = data['SB Loans'] || 0;

        var lmictCount = data['#LMICT'] || 0;
        var lmictAvg = data['Avg SB LMICT Loan Amount'] || 0;
        var lmictTotal = lmictCount * lmictAvg;

        var revCount = data['Loans Rev Under $1m'] || 0;
        var revAvg = data['Avg Loan Amt for <$1M GAR SB'] || 0;
        var revTotal = revCount * revAvg;

        var grandTotal = lmictTotal + revTotal;

        var rows = [
            { label: 'Total Small Business Loans', count: totalSBLoans, avg: null, total: null, isCountOnly: true },
            { label: 'Loans in LMI Census Tracts', count: lmictCount, avg: lmictAvg, total: lmictTotal },
            { label: 'Loans to Businesses <$1M Revenue', count: revCount, avg: revAvg, total: revTotal }
        ];

        var html = '<div style="background: white; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow: hidden;">';
        html += '<div style="overflow-x: auto;">';
        html += '<table style="width: 100%; border-collapse: collapse; font-size: 13px;">';

        // Header
        html += '<thead><tr style="background: #2e7d32; color: white;">';
        html += '<th style="padding: 12px 14px; text-align: left; font-weight: 600;">Category</th>';
        html += '<th style="padding: 12px 14px; text-align: right; font-weight: 600;">Loans</th>';
        html += '<th style="padding: 12px 14px; text-align: right; font-weight: 600;">Avg Amount</th>';
        html += '<th style="padding: 12px 14px; text-align: right; font-weight: 600;">Total Baseline</th>';
        html += '<th style="padding: 12px 14px; text-align: right; font-weight: 600;">' + this.agreementLength + '-Yr Goal (' + this.sbPercent + '%)</th>';
        html += '<th style="padding: 12px 14px; text-align: right; font-weight: 600;">Increase</th>';
        html += '</tr></thead>';

        // Body
        html += '<tbody>';
        rows.forEach(function(row, idx) {
            var bgColor = idx % 2 === 0 ? 'white' : '#fafafa';

            if (row.isCountOnly) {
                // Total SB Loans row - just show count, no dollar calculations
                html += '<tr style="background: ' + bgColor + '; font-weight: 600;">';
                html += '<td style="padding: 12px 14px; font-weight: 600; border-bottom: 1px solid #eee;">' + row.label + '</td>';
                html += '<td style="padding: 12px 14px; text-align: right; border-bottom: 1px solid #eee; font-weight: 600;">' + formatNum(row.count) + '</td>';
                html += '<td style="padding: 12px 14px; text-align: center; border-bottom: 1px solid #eee; color: #999;" colspan="4">—</td>';
                html += '</tr>';
            } else {
                var goal = calcGoal(row.total, self.dataYears, self.sbPercent, self.agreementLength);
                var baseline = calcBaseline(row.total, self.dataYears, self.agreementLength);
                var increase = goal - baseline;

                html += '<tr style="background: ' + bgColor + ';">';
                html += '<td style="padding: 12px 14px; font-weight: 500; border-bottom: 1px solid #eee;">' + row.label + '</td>';
                html += '<td style="padding: 12px 14px; text-align: right; border-bottom: 1px solid #eee;">' + formatNum(row.count) + '</td>';
                html += '<td style="padding: 12px 14px; text-align: right; border-bottom: 1px solid #eee;">' + formatFullCurrency(row.avg) + '</td>';
                html += '<td style="padding: 12px 14px; text-align: right; border-bottom: 1px solid #eee;">' + formatFullCurrency(row.total) + '</td>';
                html += '<td style="padding: 12px 14px; text-align: right; border-bottom: 1px solid #eee; color: #2e7d32;">' + formatFullCurrency(goal) + '</td>';
                html += '<td style="padding: 12px 14px; text-align: right; border-bottom: 1px solid #eee; color: #2e7d32; font-weight: 600;">' + formatFullCurrency(increase) + '</td>';
                html += '</tr>';
            }
        });

        // Total row
        var totalGoal = calcGoal(grandTotal, this.dataYears, this.sbPercent, this.agreementLength);
        var totalBaseline = calcBaseline(grandTotal, this.dataYears, this.agreementLength);
        var totalIncrease = totalGoal - totalBaseline;

        html += '<tr style="background: #e8f5e9; font-weight: 600;">';
        html += '<td style="padding: 14px; border-top: 2px solid #2e7d32;" colspan="3">TOTAL</td>';
        html += '<td style="padding: 14px; text-align: right; border-top: 2px solid #2e7d32;">' + formatFullCurrency(grandTotal) + '</td>';
        html += '<td style="padding: 14px; text-align: right; border-top: 2px solid #2e7d32; color: #2e7d32;">' + formatFullCurrency(totalGoal) + '</td>';
        html += '<td style="padding: 14px; text-align: right; border-top: 2px solid #2e7d32; color: #2e7d32; font-size: 15px;">' + formatFullCurrency(totalIncrease) + '</td>';
        html += '</tr></tbody></table></div>';

        // Summary
        html += '<div style="background: #e8f5e9; padding: 16px 20px; border-top: 2px solid #2e7d32;">';
        html += '<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">';
        html += '<div><span style="font-size: 13px; color: #666;">Small Business Lending Increase: </span>';
        html += '<span style="font-size: 20px; font-weight: 700; color: #2e7d32;">' + formatFullCurrency(totalIncrease) + '</span></div>';
        html += '<div style="font-size: 12px; color: #666;">Baseline: ' + formatFullCurrency(totalBaseline) + ' → Goal: ' + formatFullCurrency(totalGoal) + '</div>';
        html += '</div></div>';

        html += '</div>';
        return html;
    };

    // ========================================================================
    // EVENT BINDING
    // ========================================================================

    GoalsCalculator.prototype.bindEvents = function() {
        var self = this;

        // Data Years dropdown
        var dataYearsEl = document.getElementById('gcDataYears');
        if (dataYearsEl) {
            dataYearsEl.addEventListener('change', function(e) {
                self.dataYears = parseInt(e.target.value);
                self.render();
                self.bindEvents();
            });
        }

        // Agreement Length buttons
        this.container.querySelectorAll('.gc-agreement-btn').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                self.agreementLength = parseInt(e.target.getAttribute('data-years'));
                self.render();
                self.bindEvents();
            });
        });

        // Sliders
        var sliders = [
            { id: 'gcHpPercent', prop: 'hpPercent', color: '#034ea0' },
            { id: 'gcRefiPercent', prop: 'refiPercent', color: '#034ea0' },
            { id: 'gcHiPercent', prop: 'hiPercent', color: '#034ea0' },
            { id: 'gcSbPercent', prop: 'sbPercent', color: '#2e7d32' }
        ];

        sliders.forEach(function(slider) {
            var el = document.getElementById(slider.id);
            var valueEl = document.getElementById(slider.id + 'Value');
            if (el && valueEl) {
                el.addEventListener('input', function(e) {
                    var val = parseInt(e.target.value);
                    self[slider.prop] = val;
                    valueEl.textContent = val + '%';
                    // Update gradient
                    var pct = (val / 25) * 100;
                    el.style.background = 'linear-gradient(to right, ' + slider.color + ' ' + pct + '%, #ddd ' + pct + '%)';
                    self.updateContent();
                });
            }
        });

        // Tabs
        this.container.querySelectorAll('.gc-tab').forEach(function(tab) {
            tab.addEventListener('click', function(e) {
                self.activeTab = e.target.getAttribute('data-tab');
                self.render();
                self.bindEvents();
            });
        });

        // Sub-tabs
        this.container.querySelectorAll('.gc-subtab').forEach(function(tab) {
            tab.addEventListener('click', function(e) {
                self.activeSubTab = e.target.getAttribute('data-subtab');
                self.updateContent();
            });
        });

        // Action buttons
        var exportBtn = document.getElementById('gcExportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', function() {
                if (self.onExport) {
                    self.onExport(self.getConfig());
                }
            });
        }

        var saveBtn = document.getElementById('gcSaveBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', function() {
                if (self.onSave) {
                    self.onSave(self.getConfig());
                } else {
                    localStorage.setItem('mergerMeterGoalsConfig', JSON.stringify(self.getConfig()));
                    alert('Configuration saved to local storage.');
                }
            });
        }
    };

    GoalsCalculator.prototype.updateContent = function() {
        var contentEl = document.getElementById('gcContent');
        if (contentEl) {
            contentEl.innerHTML = this._renderTabContent();
            // Re-bind sub-tab events
            var self = this;
            this.container.querySelectorAll('.gc-subtab').forEach(function(tab) {
                tab.addEventListener('click', function(e) {
                    self.activeSubTab = e.target.getAttribute('data-subtab');
                    self.updateContent();
                });
            });
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
