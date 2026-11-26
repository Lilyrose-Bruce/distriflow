/*
Handle login form submission (login.html)

Handle logout button (on every other page)

Provide shared helpers used by every other JS file:
- apiFetch() → fetch wrapper that redirects on 401
- apiJson() → same, but also parses/validates JSON
- toast() → small notification popup

On load of any page:
- Fetch current user (/auth/me)
- If on login page & already logged in → go to dashboard
- If on a protected page & not logged in → go to login
*/

/* SHARED FETCH HELPERS */
async function apiFetch(url, options = {}) {
  const opts = {
    credentials: 'include',              // send JWT cookie
    ...options,
    headers: {
      // Only set JSON content-type when body is NOT FormData
      ...(options.body && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...(options.headers || {}),
    },
  };

  const response = await fetch(url, opts);

  // Global auth-expiry handling: 401 → back to login
  if (response.status === 401) {
    // Don't loop on login page
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login';
    }
    throw new Error('Unauthorized');
  }

  return response;
}


async function apiJson(url, options = {}) {
  const response = await apiFetch(url, options);

  if (!response.ok) {
    // FastAPI typically returns { detail: "..." }
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body && body.detail) {
        // detail can be string OR list of validation errors
        message = typeof body.detail === 'string'
          ? body.detail
          : body.detail.map(e => e.msg || JSON.stringify(e)).join('; ');
      }
    } catch { /* ignore parse errors */ }
    throw new Error(message);
  }

  if (response.status === 204) return null;   // no content
  return response.json();
}


function toast(message, kind = '') {
  let el = document.getElementById('toast');
  if (!el) {
    // Create on demand so login.html doesn't need to include it
    el = document.createElement('div');
    el.id = 'toast';
    el.className = 'toast hidden';
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.className = 'toast ' + kind;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), 3000);
}

/* Expose helpers globally so other <script> files can use them.
   (Plain <script> files share the window scope, but being explicit
   makes it obvious and avoids confusion.) */
window.apiFetch = apiFetch;
window.apiJson  = apiJson;
window.toast    = toast;


/* LOGIN FORM HANDLING */
(function setupLoginForm() {
  const form = document.getElementById('login-form');
  if (!form) return;                       // not on login page

  const errorBox = document.getElementById('login-error');
  const submitBtn = form.querySelector('button[type="submit"]');

  /**
   * Show or hide the inline error message under the password field.
   */
  function showError(message) {
    if (!errorBox) return;
    if (!message) {
      errorBox.hidden = true;
      errorBox.textContent = '';
      return;
    }
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  /*
  Lock the form while a request is in-flight so users can't
  double-submit.
   */
  function setBusy(busy) {
    submitBtn.disabled = busy;
    submitBtn.textContent = busy ? 'Signing in…' : 'Sign in';
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    showError('');

    // Read values (trim username but NOT password)
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    // Client-side empty check (server also validates)
    if (!username || !password) {
      showError('Please enter both your username and password.');
      return;
    }

    setBusy(true);
    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        // FastAPI: 401 → invalid credentials, 400 → validation error
        let msg = 'Login failed. Please check your details.';
        try {
          const body = await response.json();
          if (body && body.detail) {
            msg = typeof body.detail === 'string'
              ? body.detail
              : 'Invalid username or password.';
          }
        } catch { /* leave default */ }
        showError(msg);
        return;
      }

      // Success — redirect to dashboard
      window.location.href = '/dashboard';

    } catch (err) {
      // Network failure or unexpected error
      showError('Cannot reach the server. Check your connection and try again.');
      console.error('Login error:', err);
    } finally {
      setBusy(false);
    }
  });
})();


/* LOGOUT BUTTON HANDLING */
(function setupLogoutButton() {
  const btn = document.getElementById('btn-logout');
  if (!btn) return;                        // not on a page with logout

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    try {
      await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch { /* even if network fails, redirect anyway */ }
    window.location.href = '/login';
  });
})();

/* 4. SESSION BOOTSTRAP (runs on every page load) */

(async function bootstrapSession() {
  const onLoginPage = window.location.pathname.startsWith('/login');

  let user = null;
  try {
    user = await apiJson('/auth/me');
  } catch (err) {
    // apiJson throws on 401 — user is not logged in.
    // apiFetch already redirected to /login in that case.
    if (onLoginPage) {
      // Fine — stay on the login page.
      return;
    }
    // On any other page, apiFetch handled the redirect.
    return;
  }

  // ---- We now know the user IS authenticated ----

  // If logged in and on login page → go to dashboard
  if (onLoginPage && user) {
    window.location.href = '/dashboard';
    return;
  }

  // Otherwise, fill in the username in the header if present
  const currentUserEl = document.getElementById('current-user');
  if (currentUserEl && user) {
    currentUserEl.textContent = user.full_name || user.username || 'User';
  }
})();