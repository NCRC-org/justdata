/**
 * escapeHtml(value): text that is safe to put into HTML, element content or
 * a quoted attribute. Loaded by base_app.html before every page's scripts.
 *
 * Use it on every user-supplied value (names, emails, organizations, and
 * anything a request can carry into a log) before it reaches innerHTML.
 * It does not make a value safe inside an inline event handler
 * (onclick="..."): the browser decodes the entities before running the
 * script. Pass an ID there and look the value up instead.
 */
function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
