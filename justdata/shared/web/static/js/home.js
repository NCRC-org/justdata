// Home page platform stats. Moved verbatim (format/fetch logic) from
// justdata_landing_page.html's inline script; see L5 "JustData -- Frontend
// buildout spec -- 2026-09-21" Part C step 3.
document.addEventListener('DOMContentLoaded', async function () {
    try {
        const statsResponse = await fetch('/api/platform-stats');
        if (!statsResponse.ok) return;

        const stats = await statsResponse.json();
        const formatNumber = (num) => {
            if (num >= 1000000) {
                return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M+';
            } else if (num >= 1000) {
                return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K+';
            }
            return num.toLocaleString();
        };

        const mortgageEl = document.getElementById('mortgageRecords');
        const lendersEl = document.getElementById('lendersTracked');
        const reportsEl = document.getElementById('reportsGenerated');
        const researchersEl = document.getElementById('activeResearchers');

        if (mortgageEl && stats.mortgage_records !== undefined) {
            mortgageEl.textContent = formatNumber(stats.mortgage_records);
        }
        if (lendersEl && stats.lenders_tracked !== undefined) {
            lendersEl.textContent = formatNumber(stats.lenders_tracked);
        }
        if (reportsEl && stats.reports_generated !== undefined) {
            reportsEl.textContent = stats.reports_generated.toLocaleString();
        }
        if (researchersEl && stats.active_researchers !== undefined) {
            researchersEl.textContent = stats.active_researchers.toLocaleString();
        }
    } catch (error) {
        console.log('Stats fetch failed:', error);
    }
});
