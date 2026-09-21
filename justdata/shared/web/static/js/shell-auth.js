/**
 * JustData platform shell: sign-in/register modal + email-verification banner.
 *
 * Split from shell.js -- see shell-nav.js's header comment for why.
 *
 * Moved from shared_header.html per L5 "JustData -- Frontend buildout
 * spec -- 2026-09-21" Part C step 2. FA `<i class="fas fa-...">` strings
 * built dynamically (the account-created success message) are swapped
 * for Lucide `data-lucide` markup per Part B5, with lucide.createIcons()
 * called after the insert.
 */

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
