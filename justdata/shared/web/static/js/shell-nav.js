// Never load this file and shared_header.html's inline script on the same page: both declare top-level const menuToggle/navSidebar, and the second throws a redeclaration SyntaxError.
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
 * inline ACCESS_MATRIX copy are gone -- the nav drawer is now
 * server-rendered from nav_groups (shared/web/registry.py, resolved in
 * main/app.py inject_shell()).
 */

// ---------------------------------------------------------------------
// Nav sidebar toggle
// ---------------------------------------------------------------------
const menuToggle = document.getElementById('menuToggle');
const navSidebar = document.getElementById('navSidebar');
const navBackdrop = document.getElementById('navBackdrop');
const navCloseBtn = document.getElementById('navCloseBtn');

// Focusable elements inside the drawer, in DOM order, skipping hidden ones
// (e.g. #navSidebarUser when signed out or above 768px).
function navFocusables() {
    return Array.prototype.filter.call(
        navSidebar.querySelectorAll('a[href], button:not([disabled])'),
        function (el) { return el.offsetParent !== null; }
    );
}

function openNavMenu() {
    navSidebar.classList.add('active');
    navBackdrop.classList.add('active');
    document.body.classList.add('nav-open');
    menuToggle.setAttribute('aria-expanded', 'true');
    navBackdrop.setAttribute('aria-hidden', 'false');
    var firstItem = navSidebar.querySelector('.nav-item');
    if (firstItem) firstItem.focus();
}

function closeNavMenu() {
    var wasOpen = navSidebar.classList.contains('active');
    navSidebar.classList.remove('active');
    navBackdrop.classList.remove('active');
    document.body.classList.remove('nav-open');
    menuToggle.setAttribute('aria-expanded', 'false');
    navBackdrop.setAttribute('aria-hidden', 'true');
    if (wasOpen && navSidebar.contains(document.activeElement)) menuToggle.focus();
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

// Escape closes; Tab and Shift+Tab wrap inside the open drawer.
document.addEventListener('keydown', function (e) {
    if (!navSidebar || !navSidebar.classList.contains('active')) return;
    if (e.key === 'Escape') {
        closeNavMenu();
        return;
    }
    if (e.key !== 'Tab') return;
    var items = navFocusables();
    if (!items.length) return;
    var first = items[0];
    var last = items[items.length - 1];
    if (e.shiftKey && (document.activeElement === first || !navSidebar.contains(document.activeElement))) {
        e.preventDefault();
        last.focus();
    } else if (!e.shiftKey && (document.activeElement === last || !navSidebar.contains(document.activeElement))) {
        e.preventDefault();
        first.focus();
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
