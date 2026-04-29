// LenderProfile Report - AI summary + SEC filings analysis + executive-summary
// modal. These three subsystems share state via window.fullSummaryHtml /
// window.fullSummaryText (runtime stashes, not module exports), so they live
// in one module. Moved verbatim from report_v2.js. Function bodies untouched.

// =============================================================================
// AI SUMMARY
// =============================================================================

export function initializeAISummary(data) {
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
export function parseBulletFindings(text) {
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
export function markdownToHtml(text) {
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

export function initializeSECFilingsAnalysis(data) {
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
export function createTruncatedSummary(html, wordLimit) {
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
export function initializeSummaryModal() {
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
