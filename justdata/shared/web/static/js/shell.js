/**
 * JustData platform shell: nav sidebar, header user menu, auth modal,
 * member-request modals and banners.
 *
 * Moved from shared_header.html and member_request_modal.html per
 * L5 "JustData -- Frontend buildout spec -- 2026-09-21" Part C step 2.
 * Functions are moved verbatim where the spec says to, except:
 *  - filterNavMenuByAccess() and the inline ACCESS_MATRIX copy are gone --
 *    the nav sidebar is now server-rendered from visible_apps (see
 *    main/app.py inject_shell()), so client-side filtering has nothing
 *    left to do.
 *  - setupAuthListener()/getUserType() are gone too: their only job was
 *    calling filterNavMenuByAccess() on auth-state change. The spec listed
 *    them for verbatim move without noticing they'd call a function the
 *    same paragraph deletes -- moving them as-is would throw a
 *    ReferenceError on every login/logout. Dropping them means the nav
 *    sidebar can show a stale locked/hidden state for the rest of the
 *    current page view after a login that changes the user's access
 *    level, until the next navigation (every route here is a full page
 *    load, so that's the next click) -- a minor, transient staleness,
 *    not a functional break. See the step 2 PR/L5 log for the full note.
 *  - Every FA `<i class="fas fa-...">` string that these functions build
 *    dynamically (success messages, submit-button spinner states) is
 *    swapped for the matching Lucide `data-lucide` markup per Part B5,
 *    with lucide.createIcons() called after each dynamic insert.
 */

// ---------------------------------------------------------------------
// Nav sidebar toggle
// ---------------------------------------------------------------------
const menuToggle = document.getElementById('menuToggle');
const navSidebar = document.getElementById('navSidebar');
const navBackdrop = document.getElementById('navBackdrop');
const navCloseBtn = document.getElementById('navCloseBtn');

function openNavMenu() {
    navSidebar.classList.add('active');
    navBackdrop.classList.add('active');
    document.body.classList.add('nav-open');
    menuToggle.setAttribute('aria-expanded', 'true');
    navBackdrop.setAttribute('aria-hidden', 'false');
}

function closeNavMenu() {
    navSidebar.classList.remove('active');
    navBackdrop.classList.remove('active');
    document.body.classList.remove('nav-open');
    menuToggle.setAttribute('aria-expanded', 'false');
    navBackdrop.setAttribute('aria-hidden', 'true');
}

function toggleNavMenu() {
    if (navSidebar.classList.contains('active')) {
        closeNavMenu();
    } else {
        openNavMenu();
    }
}

if (menuToggle) {
    menuToggle.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        toggleNavMenu();
    });
}

if (navBackdrop) {
    navBackdrop.addEventListener('click', closeNavMenu);
}

if (navCloseBtn) {
    navCloseBtn.addEventListener('click', closeNavMenu);
}

document.querySelectorAll('.nav-sidebar .nav-item').forEach(function (link) {
    link.addEventListener('click', function () {
        setTimeout(closeNavMenu, 100);
    });
});

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && navSidebar.classList.contains('active')) {
        closeNavMenu();
    }
});

// ---------------------------------------------------------------------
// User menu dropdown
// ---------------------------------------------------------------------
function toggleUserMenu() {
    const menu = document.getElementById('userDropdownMenu');
    const toggle = document.getElementById('userMenuToggle');
    if (menu.style.display === 'none' || menu.style.display === '') {
        menu.style.display = 'block';
        toggle.classList.add('open');
        document.addEventListener('click', closeUserMenuOnClickOutside);
    } else {
        closeUserMenu();
    }
}

function closeUserMenu() {
    const menu = document.getElementById('userDropdownMenu');
    const toggle = document.getElementById('userMenuToggle');
    if (menu) menu.style.display = 'none';
    if (toggle) toggle.classList.remove('open');
    document.removeEventListener('click', closeUserMenuOnClickOutside);
}

function closeUserMenuOnClickOutside(e) {
    const container = document.getElementById('userMenuContainer');
    if (container && !container.contains(e.target)) {
        closeUserMenu();
    }
}

function updateUserMenuForType(userType) {
    const requestLink = document.getElementById('requestMemberAccessLink');
    const divider = document.getElementById('dropdownDivider');
    const publicTypes = ['public_registered', 'public_anonymous'];
    const showRequestLink = publicTypes.includes(userType);
    if (requestLink) requestLink.style.display = showRequestLink ? 'flex' : 'none';
    if (divider) divider.style.display = showRequestLink ? 'block' : 'none';
}

// ---------------------------------------------------------------------
// Login / register modal
// ---------------------------------------------------------------------
function openLoginModal(tab = 'signin') {
    document.getElementById('loginModal').style.display = 'flex';
    switchAuthTab(tab);
    if (tab === 'signin') {
        document.getElementById('loginEmail').focus();
    } else {
        document.getElementById('registerFirstName').focus();
    }
    document.getElementById('loginError').style.display = 'none';
    document.getElementById('registerError').style.display = 'none';
    document.getElementById('registerSuccess').style.display = 'none';
}

function closeLoginModal() {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('loginEmail').value = '';
    document.getElementById('loginPassword').value = '';
    document.getElementById('registerFirstName').value = '';
    document.getElementById('registerLastName').value = '';
    document.getElementById('registerEmail').value = '';
    document.getElementById('registerOrganization').value = '';
    document.getElementById('registerPassword').value = '';
    document.getElementById('registerPasswordConfirm').value = '';
}

function switchAuthTab(tab) {
    const signInTab = document.getElementById('signInTab');
    const registerTab = document.getElementById('registerTab');
    const signInView = document.getElementById('signInView');
    const registerView = document.getElementById('registerView');

    if (tab === 'signin') {
        signInTab.classList.add('is-active');
        registerTab.classList.remove('is-active');
        signInView.style.display = 'block';
        registerView.style.display = 'none';
    } else {
        registerTab.classList.add('is-active');
        signInTab.classList.remove('is-active');
        registerView.style.display = 'block';
        signInView.style.display = 'none';
    }
}

document.getElementById('loginModal')?.addEventListener('click', function (e) {
    if (e.target === this) closeLoginModal();
});

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && document.getElementById('loginModal')?.style.display === 'flex') {
        closeLoginModal();
    }
});

async function handleEmailLogin(event) {
    event.preventDefault();
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    const loginText = document.getElementById('emailLoginText');
    const loginSpinner = document.getElementById('emailLoginSpinner');
    const loginBtn = document.getElementById('emailLoginBtn');

    loginText.style.display = 'none';
    loginSpinner.style.display = 'inline';
    loginBtn.disabled = true;
    errorDiv.style.display = 'none';

    try {
        await JustDataAuth.signInWithEmail(email, password);
        closeLoginModal();
    } catch (error) {
        console.error('Email login error:', error);
        let errorMessage = 'Sign in failed. Please try again.';
        switch (error.code) {
            case 'auth/user-not-found': errorMessage = 'No account found with this email address.'; break;
            case 'auth/wrong-password': errorMessage = 'Incorrect password. Please try again.'; break;
            case 'auth/invalid-email': errorMessage = 'Please enter a valid email address.'; break;
            case 'auth/user-disabled': errorMessage = 'This account has been disabled. Contact support.'; break;
            case 'auth/too-many-requests': errorMessage = 'Too many failed attempts. Please try again later.'; break;
            case 'auth/invalid-credential': errorMessage = 'Invalid email or password. Please check and try again.'; break;
        }
        errorDiv.textContent = errorMessage;
        errorDiv.style.display = 'block';
    } finally {
        loginText.style.display = 'inline';
        loginSpinner.style.display = 'none';
        loginBtn.disabled = false;
    }
}

async function handleGoogleLogin() {
    const loginText = document.getElementById('googleLoginText');
    const loginSpinner = document.getElementById('googleLoginSpinner');
    const loginBtn = document.getElementById('googleLoginBtn');
    const errorDiv = document.getElementById('loginError');

    loginText.style.display = 'none';
    loginSpinner.style.display = 'inline';
    loginBtn.disabled = true;
    errorDiv.style.display = 'none';

    try {
        await JustDataAuth.signInWithGoogle();
        closeLoginModal();
    } catch (error) {
        if (error.code !== 'auth/popup-closed-by-user' && error.code !== 'auth/cancelled-popup-request') {
            errorDiv.textContent = 'Google sign-in failed. Please try again.';
            errorDiv.style.display = 'block';
        }
    } finally {
        loginText.style.display = 'inline';
        loginSpinner.style.display = 'none';
        loginBtn.disabled = false;
    }
}

async function handleEmailRegister(event) {
    event.preventDefault();
    const firstName = document.getElementById('registerFirstName').value.trim();
    const lastName = document.getElementById('registerLastName').value.trim();
    const email = document.getElementById('registerEmail').value.trim();
    const organization = document.getElementById('registerOrganization').value.trim();
    const password = document.getElementById('registerPassword').value;
    const passwordConfirm = document.getElementById('registerPasswordConfirm').value;
    const errorDiv = document.getElementById('registerError');
    const successDiv = document.getElementById('registerSuccess');
    const registerText = document.getElementById('emailRegisterText');
    const registerSpinner = document.getElementById('emailRegisterSpinner');
    const registerBtn = document.getElementById('emailRegisterBtn');

    if (password !== passwordConfirm) {
        errorDiv.textContent = 'Passwords do not match.';
        errorDiv.style.display = 'block';
        successDiv.style.display = 'none';
        return;
    }

    registerText.style.display = 'none';
    registerSpinner.style.display = 'inline';
    registerBtn.disabled = true;
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';

    try {
        await JustDataAuth.signUpWithEmail(email, password, firstName, lastName, organization);

        const isNcrcEmail = email.toLowerCase().endsWith('@ncrc.org');
        if (isNcrcEmail) {
            successDiv.innerHTML = '<i data-lucide="circle-check" aria-hidden="true"></i> Account created! Check your email for a verification link to activate your staff access.';
        } else {
            successDiv.innerHTML = '<i data-lucide="circle-check" aria-hidden="true"></i> Account created! Check your email to verify your account.';
        }
        successDiv.style.display = 'block';
        if (window.lucide) window.lucide.createIcons();

        setTimeout(() => {
            closeLoginModal();
            if (isNcrcEmail) {
                showVerificationBanner();
            }
        }, 2000);

    } catch (error) {
        console.error('Registration error:', error);
        let errorMessage = 'Registration failed. Please try again.';
        switch (error.code) {
            case 'auth/email-already-in-use':
                errorMessage = 'An account with this email already exists. Try signing in instead.';
                break;
            case 'auth/invalid-email':
                errorMessage = 'Please enter a valid email address.';
                break;
            case 'auth/weak-password':
                errorMessage = 'Password is too weak. Please use at least 6 characters.';
                break;
            case 'auth/operation-not-allowed':
                errorMessage = 'Email/password registration is not enabled. Please contact support.';
                break;
        }
        errorDiv.textContent = errorMessage;
        errorDiv.style.display = 'block';
    } finally {
        registerText.style.display = 'inline';
        registerSpinner.style.display = 'none';
        registerBtn.disabled = false;
    }
}

// ---------------------------------------------------------------------
// Email verification banner
// ---------------------------------------------------------------------
function showVerificationBanner() {
    const banner = document.getElementById('emailVerificationBanner');
    if (banner && !sessionStorage.getItem('verificationBannerDismissed')) {
        banner.style.display = 'flex';
    }
}

function dismissVerificationBanner() {
    const banner = document.getElementById('emailVerificationBanner');
    if (banner) {
        banner.style.display = 'none';
        sessionStorage.setItem('verificationBannerDismissed', 'true');
    }
}

async function resendVerificationEmail() {
    const btn = document.getElementById('resendVerificationBtn');
    const text = document.getElementById('resendVerificationText');
    const spinner = document.getElementById('resendVerificationSpinner');

    text.style.display = 'none';
    spinner.style.display = 'inline';
    btn.disabled = true;

    try {
        const result = await JustDataAuth.sendVerificationEmail();
        if (result.alreadyVerified) {
            alert('Your email is already verified! Refreshing your access...');
            await checkEmailVerified();
        } else {
            alert('Verification email sent! Please check your inbox.');
        }
    } catch (error) {
        console.error('Error sending verification email:', error);
        if (error.code === 'auth/too-many-requests') {
            alert('Too many requests. Please wait a few minutes before trying again.');
        } else {
            alert('Failed to send verification email. Please try again later.');
        }
    } finally {
        text.style.display = 'inline';
        spinner.style.display = 'none';
        btn.disabled = false;
    }
}

async function checkEmailVerified() {
    try {
        const result = await JustDataAuth.refreshEmailVerification();
        if (result.verified) {
            dismissVerificationBanner();
            alert(result.message || 'Email verified! Your access has been upgraded.');
            window.location.reload();
        } else {
            alert('Email not yet verified. Please click the link in the verification email.');
        }
    } catch (error) {
        console.error('Error checking verification:', error);
        alert('Could not check verification status. Please try again.');
    }
}

function checkVerificationBannerOnLoad() {
    if (typeof JustDataAuth !== 'undefined' && JustDataAuth.checkVerificationNeeded) {
        JustDataAuth.checkVerificationNeeded().then(status => {
            if (status.needs_verification) {
                showVerificationBanner();
            }
        }).catch(err => console.log('Verification check skipped:', err));
    }
}

document.addEventListener('DOMContentLoaded', function () {
    setTimeout(checkVerificationBannerOnLoad, 1500);
});

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

// ---------------------------------------------------------------------
// Icons: render every data-lucide element once the DOM is ready.
// ---------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {
    if (window.lucide) window.lucide.createIcons();
});
