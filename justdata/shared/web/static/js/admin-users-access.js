/**
 * /admin/users additions for spec 08 (build step 4).
 *
 * - Role choices come from VALID_USER_TYPES, which the page receives from the
 *   server: the same list the access matrix and the role APIs use.
 * - The Sign-in cell shows each Firebase provider and Firebase's own
 *   emailVerified flag.
 * - The HubSpot cell shows the testing site's tester check and when it ran.
 *
 * Expects the page to define VALID_USER_TYPES, USER_TYPE_LABELS and
 * TESTER_REASON_LABELS before this file loads.
 */

const PROVIDER_LABELS = {
    'google.com': 'Google',
    'password': 'Password',
    'microsoft.com': 'Microsoft'
};

function roleLabel(role) {
    return USER_TYPE_LABELS[role] || role;
}

/** <option> tags for every valid role, the current one selected. */
function roleOptionsHtml(selected) {
    return VALID_USER_TYPES.map(role =>
        `<option value="${escapeHtml(role)}" ${role === selected ? 'selected' : ''}>${escapeHtml(roleLabel(role))}</option>`
    ).join('');
}

/** Fill a <select> that has only its placeholder option with every valid role. */
function fillRoleSelect(select) {
    if (!select) return;
    select.insertAdjacentHTML('beforeend', roleOptionsHtml(null));
}

function signInCell(user) {
    const providers = (user.providerData && user.providerData.length)
        ? user.providerData
        : [user.authMethod === 'google' ? 'google.com' : 'password'];
    const names = providers.map(p => PROVIDER_LABELS[p] || p).join(' + ');
    const verified = user.emailVerified
        ? '<span class="auth-badge verified" title="Firebase emailVerified is true">Verified</span>'
        : '<span class="auth-badge unverified" title="Firebase emailVerified is false">Unverified</span>';
    return `<span class="auth-badge email">${escapeHtml(names)}</span> ${verified}`;
}

function hubspotCell(user) {
    const access = user.testerAccess;
    if (!access || !access.reason) {
        return '<span class="hubspot-status none">Not checked</span>';
    }
    const label = TESTER_REASON_LABELS[access.reason] || access.reason;
    const when = access.checkedAt ? formatCheckTime(access.checkedAt) : '';
    const cls = access.authorized ? 'ok' : 'refused';
    return `<span class="hubspot-status ${cls}">${escapeHtml(label)}</span>`
        + (when ? `<div class="hubspot-checked">${escapeHtml(when)}</div>` : '');
}

function formatCheckTime(iso) {
    const date = new Date(iso);
    if (isNaN(date)) return iso;
    return date.toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit'
    });
}

document.addEventListener('DOMContentLoaded', function () {
    fillRoleSelect(document.getElementById('typeFilter'));
    fillRoleSelect(document.getElementById('userTypeSelect'));
});
