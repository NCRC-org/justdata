/**
 * JustData platform shell: nav sidebar toggle + header user menu.
 *
 * Split from shell.js (2026-09-21, same day it was written) because CI's
 * file-size-check enforces a 500-line limit on JS files with an explicit
 * allowlist in .github/workflows/ci.yml -- a file the buildout spec's
 * do-not-touch list forbids editing. shell.js was 627 lines. Split into
 * shell-nav.js (this file), shell-auth.js, and shell-member.js along the
 * same section boundaries the single file already had; nothing here was
 * rewritten, only relocated. See the step 2 PR/L5 log.
 *
 * Moved from shared_header.html per L5 "JustData -- Frontend buildout
 * spec -- 2026-09-21" Part C step 2. filterNavMenuByAccess() and the
 * inline ACCESS_MATRIX copy are gone -- the nav sidebar is now
 * server-rendered from visible_apps (see main/app.py inject_shell()).
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
// Icons: render every data-lucide element once the DOM is ready.
// (Kept here, first-loaded, so icons in the header/nav paint immediately;
// shell-auth.js and shell-member.js also call createIcons() after their
// own dynamic inserts.)
// ---------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {
    if (window.lucide) window.lucide.createIcons();
});
