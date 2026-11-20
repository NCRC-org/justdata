/* /account (spec 14, phase 1): save the display name, send a password reset
   email, sign out of all devices. Text is set with textContent only. */
(function () {
  function post(url, body) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) { d._ok = r.ok; return d; });
    });
  }

  function say(el, text, ok) {
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('is-ok', !!ok);
  }

  var form = document.getElementById('accountNameForm');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var input = document.getElementById('accountDisplayName');
      var status = document.getElementById('accountNameStatus');
      say(status, 'Saving...');
      post('/api/account/profile', { display_name: input.value }).then(function (d) {
        if (!d._ok || !d.success) { say(status, d.error || "We couldn't save your name. Try again."); return; }
        input.value = d.display_name;
        var heading = document.querySelector('[data-account-name]');
        if (heading) heading.textContent = d.display_name;
        say(status, 'Saved.', true);
        // Refresh the browser's Firebase profile, so the next sign-in check
        // sends the new name rather than the old one.
        try {
          var u = window.firebase && firebase.auth().currentUser;
          if (u) u.reload().then(function () { return u.getIdToken(true); }).catch(function () {});
        } catch (err) { /* the server already holds the new name */ }
      }).catch(function () { say(status, "We couldn't save your name. Try again."); });
    });
  }

  var reset = document.getElementById('accountResetPassword');
  if (reset) {
    reset.addEventListener('click', function () {
      var status = document.getElementById('accountResetStatus');
      var email = reset.getAttribute('data-email');
      try {
        firebase.auth().sendPasswordResetEmail(email).then(function () {
          say(status, 'Check your email for a link to set a new password.', true);
        }).catch(function () { say(status, "We couldn't send the email. Try again."); });
      } catch (err) { say(status, "We couldn't send the email. Try again."); }
    });
  }

  var everywhere = document.getElementById('accountSignOutEverywhere');
  if (everywhere) {
    everywhere.addEventListener('click', function () {
      var status = document.getElementById('accountSignOutStatus');
      if (!window.confirm('Sign out on every browser and device, including this one?')) return;
      say(status, 'Signing out...');
      post('/api/account/sign-out-everywhere').then(function (d) {
        if (!d._ok || !d.success) { say(status, d.error || "We couldn't sign you out everywhere. Try again."); return; }
        var done = function () { window.location.href = d.redirect || '/'; };
        try { firebase.auth().signOut().then(done, done); } catch (err) { done(); }
      }).catch(function () { say(status, "We couldn't sign you out everywhere. Try again."); });
    });
  }
})();
