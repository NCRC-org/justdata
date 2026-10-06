/**
 * JustData platform shell: member-request welcome modal, request-access
 * modal, and pending/grace-period banners.
 *
 * Split from shell.js -- see shell-nav.js's header comment for why.
 *
 * Moved from member_request_modal.html per L5 "JustData -- Frontend
 * buildout spec -- 2026-09-21" Part C step 2. Legacy icon-font `<i>`
 * strings built dynamically (submit-button spinner states) are swapped
 * for Lucide `data-lucide` markup per Part B5, with lucide.createIcons()
 * called after each dynamic insert.
 */

// ---------------------------------------------------------------------
// Member-request welcome modal
// ---------------------------------------------------------------------
function checkMemberPrompt() {
    if (!window.justDataUserType) return;

    const memberTypes = ['member', 'member_premium', 'non_member_org', 'staff', 'senior_executive', 'admin'];
    if (memberTypes.includes(window.justDataUserType)) {
        checkGracePeriodBanner();
        return;
    }

    fetch('/api/auth/member-request/status')
        .then(response => {
            if (!response.ok) return;
            return response.json();
        })
        .then(data => {
            if (!data) return;
            if (data.memberRequestStatus === 'pending') {
                showPendingBanner();
                return;
            }
            if (!data.hasSeenMemberPrompt && data.memberRequestStatus !== 'denied') {
                showWelcomeModal();
            }
        })
        .catch(err => console.error('Error checking member status:', err));
}

function showWelcomeModal() {
    const modal = document.getElementById('welcomeMemberModal');
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

function closeWelcomeModal() {
    const modal = document.getElementById('welcomeMemberModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

function showRequestForm() {
    document.getElementById('welcomeStep1').style.display = 'none';
    document.getElementById('welcomeStep2').style.display = 'block';
    document.getElementById('welcomeStep3').style.display = 'none';
}

function showStep1() {
    document.getElementById('welcomeStep1').style.display = 'block';
    document.getElementById('welcomeStep2').style.display = 'none';
    document.getElementById('welcomeStep3').style.display = 'none';
}

function continueAsGuest() {
    fetch('/api/auth/member-request/dismiss-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    }).catch(err => console.error('Error dismissing prompt:', err));

    closeWelcomeModal();
}

async function submitMemberRequest(event) {
    event.preventDefault();

    const btn = document.getElementById('submitRequestBtn');
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader-circle" class="is-spinning" aria-hidden="true"></i> Submitting...';
    if (window.lucide) window.lucide.createIcons();

    const formData = {
        organization_name: document.getElementById('reqOrgName').value,
        user_role: document.getElementById('reqUserRole').value,
        notes: document.getElementById('reqNotes').value
    };

    try {
        const response = await fetch('/api/auth/member-request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok) {
            document.getElementById('welcomeStep2').style.display = 'none';
            document.getElementById('welcomeStep3').style.display = 'block';
        } else {
            alert(result.error || 'Failed to submit request. Please try again.');
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="send" aria-hidden="true"></i> Submit Request';
            if (window.lucide) window.lucide.createIcons();
        }
    } catch (error) {
        alert('An error occurred. Please try again.');
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="send" aria-hidden="true"></i> Submit Request';
        if (window.lucide) window.lucide.createIcons();
    }
}

// ---------------------------------------------------------------------
// Request-access modal (opened from the user menu)
// ---------------------------------------------------------------------
function openMemberRequestModal() {
    const modal = document.getElementById('requestAccessModal');
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

function closeRequestModal() {
    const modal = document.getElementById('requestAccessModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
    const form = document.getElementById('requestAccessForm');
    if (form) form.reset();
}

async function submitAccessRequest(event) {
    event.preventDefault();

    const btn = document.getElementById('submitAccessBtn');
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader-circle" class="is-spinning" aria-hidden="true"></i> Submitting...';
    if (window.lucide) window.lucide.createIcons();

    const formData = {
        organization_name: document.getElementById('accessOrgName').value,
        user_role: document.getElementById('accessUserRole').value,
        notes: document.getElementById('accessNotes').value
    };

    try {
        const response = await fetch('/api/auth/member-request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok) {
            closeRequestModal();
            alert('Your request has been submitted! An NCRC administrator will review it within 1-2 business days.');
            showPendingBanner();
        } else {
            alert(result.error || 'Failed to submit request. Please try again.');
        }
    } catch (error) {
        alert('An error occurred. Please try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="send" aria-hidden="true"></i> Submit Request';
        if (window.lucide) window.lucide.createIcons();
    }
}

// ---------------------------------------------------------------------
// Pending / grace-period banners
// ---------------------------------------------------------------------
function showPendingBanner() {
    const banner = document.getElementById('pendingRequestBanner');
    if (sessionStorage.getItem('pendingBannerDismissed')) return;
    if (banner) banner.style.display = 'flex';
}

function dismissPendingBanner() {
    const banner = document.getElementById('pendingRequestBanner');
    if (banner) banner.style.display = 'none';
    sessionStorage.setItem('pendingBannerDismissed', 'true');
}

function checkGracePeriodBanner() {
    fetch('/api/auth/member-request/status')
        .then(response => {
            if (!response.ok) return null;
            return response.json();
        })
        .then(data => {
            if (data && data.membershipStatus === 'GRACE PERIOD') {
                showGracePeriodBanner();
            }
        })
        .catch(err => console.error('Error checking grace period:', err));
}

function showGracePeriodBanner() {
    const banner = document.getElementById('gracePeriodBanner');
    if (sessionStorage.getItem('graceBannerDismissed')) return;
    if (banner) banner.style.display = 'flex';
}

function dismissGraceBanner() {
    const banner = document.getElementById('gracePeriodBanner');
    if (banner) banner.style.display = 'none';
    sessionStorage.setItem('graceBannerDismissed', 'true');
}

if (typeof onAuthStateChanged === 'function') {
    onAuthStateChanged(function (user) {
        if (user) {
            setTimeout(checkMemberPrompt, 500);
        }
    });
} else {
    document.addEventListener('DOMContentLoaded', function () {
        setTimeout(function () {
            if (window.justDataUserType) {
                checkMemberPrompt();
            }
        }, 1000);
    });
}
