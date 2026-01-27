/**
 * Firebase Authentication for JustData
 * Handles Google sign-in, sign-out, and token management
 */

// Firebase configuration - justdata-ncrc project
const firebaseConfig = {
    apiKey: "AIzaSyAZxZ4t4kBj9aZre9HfTwrtzriZvh0ab9U",
    authDomain: "justdata-ncrc.firebaseapp.com",
    projectId: "justdata-ncrc",
    storageBucket: "justdata-ncrc.firebasestorage.app",
    messagingSenderId: "854699313651",
    appId: "1:854699313651:web:a40d91691b353b37476a86",
    measurementId: "G-DWS9XPNT7J"
};

// Initialize Firebase
let firebaseApp = null;
let firebaseAuth = null;
let signInInProgress = false;  // Prevent multiple sign-in attempts
let authStateCallbacks = [];   // Callbacks for auth state changes
let lastKnownUser = null;      // Track last known user for new callback registrations

function initFirebase() {
    console.log('[DEBUG] initFirebase called, alreadyInit:', !!firebaseApp, 'path:', window.location.pathname);
    if (firebaseApp) return;

    try {
        firebaseApp = firebase.initializeApp(firebaseConfig);
        firebaseAuth = firebase.auth();

        // Set persistence to LOCAL - auth state persists across browser sessions
        firebaseAuth.setPersistence(firebase.auth.Auth.Persistence.LOCAL)
            .then(() => {
                console.log('[DEBUG] Firebase persistence set to LOCAL');
            })
            .catch((error) => {
                console.warn('[DEBUG] Could not set Firebase persistence:', error);
            });

        // Listen for auth state changes
        firebaseAuth.onAuthStateChanged(handleAuthStateChange);

        console.log('[DEBUG] Firebase initialized successfully');
    } catch (error) {
        console.error('[DEBUG] Firebase initialization error:', error);
    }
}

/**
 * Handle authentication state changes
 */
async function handleAuthStateChange(user) {
    console.log('[DEBUG] handleAuthStateChange:', user ? user.email : 'no user', 'path:', window.location.pathname);
    // Store user with additional info for callbacks
    let userWithType = null;

    if (user) {
        // User is signed in
        console.log('User signed in:', user.email);

        // Get ID token and notify backend
        const idToken = await user.getIdToken();
        const backendResponse = await notifyBackendLogin(idToken, user);

        // Update UI
        updateAuthUI(user);

        // Create user object with type info for callbacks
        userWithType = {
            uid: user.uid,
            email: user.email,
            displayName: user.displayName,
            photoURL: user.photoURL,
            emailVerified: user.emailVerified,
            userType: window.justDataUserType || 'public_registered',
            getIdTokenResult: user.getIdTokenResult.bind(user)
        };
    } else {
        // User is signed out
        console.log('User signed out');
        updateAuthUI(null);
    }

    // Store for new callback registrations
    lastKnownUser = userWithType;

    // Notify all registered callbacks
    authStateCallbacks.forEach(callback => {
        try {
            callback(userWithType);
        } catch (err) {
            console.error('Auth state callback error:', err);
        }
    });
}

/**
 * Register a callback for auth state changes
 * @param {Function} callback - Function to call when auth state changes
 */
function onAuthStateChanged(callback) {
    if (typeof callback !== 'function') {
        console.error('onAuthStateChanged requires a function callback');
        return;
    }

    // Add to callbacks array
    authStateCallbacks.push(callback);

    // If we already have a known user state, call immediately
    if (lastKnownUser !== null || firebaseAuth) {
        // Call with current state (may be null if not logged in)
        setTimeout(() => callback(lastKnownUser), 0);
    }

    console.log('[Auth] Registered auth state callback, total:', authStateCallbacks.length);
}

/**
 * Sign in with Google
 */
async function signInWithGoogle() {
    // Prevent multiple simultaneous sign-in attempts
    if (signInInProgress) {
        console.log('Sign-in already in progress, ignoring click');
        return;
    }

    console.log('signInWithGoogle called');
    console.log('Current origin:', window.location.origin);

    if (!firebaseAuth) {
        console.error('Firebase not initialized - attempting to initialize now');
        initFirebase();
        if (!firebaseAuth) {
            alert('Firebase failed to initialize. Check console for errors.');
            return;
        }
    }

    signInInProgress = true;

    const provider = new firebase.auth.GoogleAuthProvider();
    provider.addScope('email');
    provider.addScope('profile');

    console.log('Attempting signInWithPopup...');

    try {
        const result = await firebaseAuth.signInWithPopup(provider);
        console.log('Google sign-in successful:', result.user.email);
        signInInProgress = false;
        return result.user;
    } catch (error) {
        signInInProgress = false;
        console.error('Google sign-in error code:', error.code);
        console.error('Google sign-in error message:', error.message);

        // Handle specific errors
        if (error.code === 'auth/popup-closed-by-user') {
            console.log('Sign-in popup was closed by user');
        } else if (error.code === 'auth/popup-blocked') {
            alert('Popup was blocked by your browser.\n\nPlease allow popups for this site and try again.');
        } else if (error.code === 'auth/cancelled-popup-request') {
            console.log('Previous popup request cancelled');
        } else if (error.code === 'auth/unauthorized-domain') {
            alert('Domain not authorized: ' + window.location.origin);
        } else {
            alert('Sign-in failed: ' + error.message);
        }
        throw error;
    }
}

/**
 * Sign in with email and password
 */
async function signInWithEmail(email, password) {
    if (!firebaseAuth) {
        console.error('Firebase not initialized');
        return;
    }

    try {
        const result = await firebaseAuth.signInWithEmailAndPassword(email, password);
        console.log('Email sign-in successful:', result.user.email);
        return result.user;
    } catch (error) {
        console.error('Email sign-in error:', error);
        throw error;
    }
}

/**
 * Sign up with email and password
 * Automatically sends verification email after signup
 */
async function signUpWithEmail(email, password, firstName = null, lastName = null, organization = null) {
    if (!firebaseAuth) {
        console.error('Firebase not initialized');
        return;
    }

    try {
        // Store registration data in session storage BEFORE creating user
        // (Firebase triggers auth state change immediately on user creation)
        if (organization) {
            sessionStorage.setItem('pendingUserOrganization', organization);
        }
        if (firstName) {
            sessionStorage.setItem('pendingUserFirstName', firstName);
        }
        if (lastName) {
            sessionStorage.setItem('pendingUserLastName', lastName);
        }

        const result = await firebaseAuth.createUserWithEmailAndPassword(email, password);
        console.log('Email sign-up successful:', result.user.email);

        // Combine first and last name for display
        const displayName = [firstName, lastName].filter(Boolean).join(' ') || null;

        // Update display name if provided
        if (displayName) {
            await result.user.updateProfile({ displayName: displayName });
        }

        // Send verification email
        await sendVerificationEmail(result.user);
        console.log('Verification email sent to:', result.user.email);

        return result.user;
    } catch (error) {
        console.error('Email sign-up error:', error);
        // Clear session storage on error
        sessionStorage.removeItem('pendingUserOrganization');
        sessionStorage.removeItem('pendingUserFirstName');
        sessionStorage.removeItem('pendingUserLastName');
        throw error;
    }
}

/**
 * Send email verification to current user or specified user
 */
async function sendVerificationEmail(user = null) {
    const targetUser = user || (firebaseAuth ? firebaseAuth.currentUser : null);

    if (!targetUser) {
        console.error('No user to send verification email to');
        throw new Error('No user signed in');
    }

    if (targetUser.emailVerified) {
        console.log('Email already verified');
        return { alreadyVerified: true };
    }

    try {
        // Configure action code settings for the verification email
        const actionCodeSettings = {
            url: window.location.origin + '/email-verified',
            handleCodeInApp: false
        };

        await targetUser.sendEmailVerification(actionCodeSettings);
        console.log('Verification email sent successfully');
        return { sent: true };
    } catch (error) {
        console.error('Error sending verification email:', error);
        throw error;
    }
}

/**
 * Check if current user needs email verification for staff access
 */
async function checkVerificationNeeded() {
    try {
        const response = await fetch('/api/auth/verification-status');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error checking verification status:', error);
        return { needs_verification: false };
    }
}

/**
 * Refresh user's email verification status
 * Call this after user clicks verification link
 */
async function refreshEmailVerification() {
    if (!firebaseAuth || !firebaseAuth.currentUser) {
        return { verified: false };
    }

    try {
        // Reload user to get fresh email_verified status
        await firebaseAuth.currentUser.reload();
        const isVerified = firebaseAuth.currentUser.emailVerified;

        if (isVerified) {
            // Notify backend that email is verified
            const response = await fetch('/api/auth/email-verified', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();

            if (data.success) {
                // Update local state
                window.justDataUserType = data.user_type;
                window.justDataPermissions = data.permissions;

                // Trigger auth state update
                handleAuthStateChange(firebaseAuth.currentUser);
            }

            return { verified: true, ...data };
        }

        return { verified: false };
    } catch (error) {
        console.error('Error refreshing verification status:', error);
        return { verified: false, error: error.message };
    }
}

/**
 * Sign out
 */
async function signOut() {
    if (!firebaseAuth) {
        console.error('Firebase not initialized');
        return;
    }

    try {
        // Notify backend first
        await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        // Then sign out of Firebase
        await firebaseAuth.signOut();
        console.log('Sign-out successful');

        // Reload page to reset state
        window.location.reload();
    } catch (error) {
        console.error('Sign-out error:', error);
    }
}

/**
 * Get current user's ID token for API calls
 */
async function getToken() {
    if (!firebaseAuth || !firebaseAuth.currentUser) {
        return null;
    }

    try {
        return await firebaseAuth.currentUser.getIdToken();
    } catch (error) {
        console.error('Error getting token:', error);
        return null;
    }
}

/**
 * Get current user
 */
function getCurrentUser() {
    return firebaseAuth ? firebaseAuth.currentUser : null;
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return getCurrentUser() !== null;
}

/**
 * Notify backend of login
 */
async function notifyBackendLogin(idToken, user) {
    try {
        // Check for pending registration data from session storage
        const pendingOrganization = sessionStorage.getItem('pendingUserOrganization');
        const pendingFirstName = sessionStorage.getItem('pendingUserFirstName');
        const pendingLastName = sessionStorage.getItem('pendingUserLastName');

        // Clear session storage after retrieving
        sessionStorage.removeItem('pendingUserOrganization');
        sessionStorage.removeItem('pendingUserFirstName');
        sessionStorage.removeItem('pendingUserLastName');

        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                idToken: idToken,
                user: {
                    uid: user.uid,
                    email: user.email,
                    displayName: user.displayName,
                    photoURL: user.photoURL,
                    organization: pendingOrganization || null,
                    firstName: pendingFirstName || null,
                    lastName: pendingLastName || null
                }
            })
        });

        const data = await response.json();
        if (data.success) {
            console.log('Backend login successful, user type:', data.user_type);
            // Store user type for UI updates
            window.justDataUserType = data.user_type;
            window.justDataPermissions = data.permissions;

            // Update app visibility if switchUserType function exists (on landing page)
            if (typeof switchUserType === 'function') {
                switchUserType(data.user_type);
                console.log('Applied visibility for user type:', data.user_type);
            }
            
            // Check if user needs to provide organization (non-NCRC users on first login)
            if (data.needs_organization) {
                console.log('User needs to provide organization');
                showOrganizationPrompt();
            }
        }
        return data;
    } catch (error) {
        console.error('Backend login notification failed:', error);
    }
}

/**
 * Show organization prompt modal for non-NCRC users on first login
 */
function showOrganizationPrompt() {
    // Create modal if it doesn't exist
    let modal = document.getElementById('organization-prompt-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'organization-prompt-modal';
        modal.innerHTML = `
            <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center;">
                <div style="background: white; padding: 30px; border-radius: 12px; max-width: 450px; width: 90%; box-shadow: 0 4px 20px rgba(0,0,0,0.15);">
                    <h2 style="margin: 0 0 15px 0; font-size: 1.5rem; color: #1a1a1a;">Welcome to JustData!</h2>
                    <p style="margin: 0 0 20px 0; color: #666; line-height: 1.5;">Please enter your organization name to complete your profile.</p>
                    <input type="text" id="org-prompt-input" placeholder="Organization Name" 
                           style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 1rem; margin-bottom: 20px; box-sizing: border-box;">
                    <div style="display: flex; gap: 10px; justify-content: flex-end;">
                        <button id="org-prompt-skip" style="padding: 10px 20px; background: #f5f5f5; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;">Skip for now</button>
                        <button id="org-prompt-submit" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;">Continue</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Handle submit
        document.getElementById('org-prompt-submit').addEventListener('click', async () => {
            const org = document.getElementById('org-prompt-input').value.trim();
            if (org) {
                try {
                    const token = await getToken();
                    const response = await fetch('/api/auth/set-organization', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({ organization: org })
                    });
                    const data = await response.json();
                    if (data.success) {
                        console.log('Organization set:', org);
                        modal.remove();
                    } else {
                        alert(data.error || 'Failed to save organization');
                    }
                } catch (error) {
                    console.error('Error setting organization:', error);
                    alert('Failed to save organization. Please try again.');
                }
            } else {
                alert('Please enter your organization name');
            }
        });
        
        // Handle skip
        document.getElementById('org-prompt-skip').addEventListener('click', () => {
            modal.remove();
        });
        
        // Handle enter key
        document.getElementById('org-prompt-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('org-prompt-submit').click();
            }
        });
    }
}

/**
 * Get auth status from backend
 */
async function getAuthStatus() {
    try {
        const token = await getToken();
        const headers = {
            'Content-Type': 'application/json'
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch('/api/auth/status', {
            method: 'GET',
            headers: headers
        });

        return await response.json();
    } catch (error) {
        console.error('Error getting auth status:', error);
        return { authenticated: false };
    }
}

/**
 * Make authenticated API request
 */
async function authFetch(url, options = {}) {
    const token = await getToken();

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    return fetch(url, {
        ...options,
        headers: headers
    });
}

/**
 * Update UI based on auth state
 */
function updateAuthUI(user) {
    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const userInfo = document.getElementById('userInfo');
    const userMenuContainer = document.getElementById('userMenuContainer');
    const userEmail = document.getElementById('userEmail');
    const userAvatar = document.getElementById('userAvatar');
    const userTypeBadge = document.getElementById('userTypeBadge');

    if (user) {
        // User is signed in
        if (loginBtn) loginBtn.style.display = 'none';

        // Show user menu dropdown (new) or legacy logout button
        if (userMenuContainer) {
            userMenuContainer.style.display = 'flex';
            if (logoutBtn) logoutBtn.style.display = 'none';  // Hide legacy button
        } else if (logoutBtn) {
            logoutBtn.style.display = 'inline-flex';
        }

        // Legacy userInfo (if present on older pages)
        if (userInfo && !userMenuContainer) userInfo.style.display = 'flex';

        if (userEmail) userEmail.textContent = user.email;
        if (userAvatar) {
            if (user.photoURL) {
                userAvatar.src = user.photoURL;
                userAvatar.style.display = 'block';
            } else {
                userAvatar.style.display = 'none';
            }
        }
        // Show user type badge
        if (userTypeBadge && window.justDataUserType) {
            const typeLabels = {
                'admin': 'Administrator',
                'senior_executive': 'Executive',
                'staff': 'Staff',
                'member': 'Member',
                'member_premium': 'Premium Member',
                'non_member_org': 'Institutional',
                'just_economy_club': 'Economy Club',
                'public_registered': 'Registered',
                'public_anonymous': 'Guest'
            };
            userTypeBadge.textContent = typeLabels[window.justDataUserType] || window.justDataUserType;
        }

        // Update user menu dropdown visibility based on user type
        if (typeof updateUserMenuForType === 'function' && window.justDataUserType) {
            updateUserMenuForType(window.justDataUserType);
        }
    } else {
        // User is signed out
        if (loginBtn) loginBtn.style.display = 'inline-flex';
        if (logoutBtn) logoutBtn.style.display = 'none';
        if (userInfo) userInfo.style.display = 'none';
        if (userMenuContainer) userMenuContainer.style.display = 'none';
        if (userEmail) userEmail.textContent = '';
        if (userAvatar) userAvatar.style.display = 'none';
        if (userTypeBadge) userTypeBadge.textContent = '';
    }
}

// Initialize Firebase when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    // First, check backend session state to restore UI immediately
    // This prevents flash of unauthenticated state when navigating between apps
    try {
        const response = await fetch('/api/auth/status');
        const data = await response.json();
        if (data.authenticated && data.user) {
            console.log('Backend session found:', data.user.email, '| User type:', data.user_type);
            // Update UI immediately from backend session
            updateAuthUI({
                email: data.user.email,
                displayName: data.user.name,
                photoURL: data.user.picture
            });
            // Store user type for UI updates
            window.justDataUserType = data.user_type;
            window.justDataPermissions = data.permissions;

            // Set lastKnownUser for callbacks registered later
            lastKnownUser = {
                uid: data.user.uid,
                email: data.user.email,
                displayName: data.user.name,
                photoURL: data.user.picture,
                emailVerified: data.user.email_verified || false,
                userType: data.user_type
            };

            // Notify any already-registered callbacks
            authStateCallbacks.forEach(callback => {
                try {
                    callback(lastKnownUser);
                } catch (err) {
                    console.error('Auth state callback error:', err);
                }
            });
        }
    } catch (error) {
        console.log('Backend session check skipped:', error.message);
    }

    // Then initialize Firebase (will sync with backend if needed)
    if (typeof firebase !== 'undefined') {
        initFirebase();
    } else {
        console.warn('Firebase SDK not loaded');
    }
});

// Export functions for global access
window.JustDataAuth = {
    signInWithGoogle,
    signInWithEmail,
    signUpWithEmail,
    signOut,
    getToken,
    getCurrentUser,
    isAuthenticated,
    getAuthStatus,
    authFetch,
    onAuthStateChanged,
    sendVerificationEmail,
    checkVerificationNeeded,
    refreshEmailVerification
};
