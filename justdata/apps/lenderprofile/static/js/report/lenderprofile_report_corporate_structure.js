// LenderProfile Report - Corporate structure section: entity-tree rendering
// (with parent / current / children / subsidiaries), GLEIF links, expand/
// collapse, and the copy-to-clipboard helper called from inline onclick.
// Moved verbatim from report_v2.js. Function bodies untouched.

import { escapeHtml } from './lenderprofile_report_utils.js';

// =============================================================================
// CORPORATE STRUCTURE
// =============================================================================

/**
 * Copy entity info to clipboard (name, LEI, GLEIF URL)
 */
export function copyEntityInfo(name, lei, gleifUrl) {
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
export function buildEntityNode(entity, options) {
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

export function initializeCorporateStructure(data) {
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
export function buildReportLink(entity) {
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
