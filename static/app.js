/* ─────────────────────────────────────────────────────────────────────────
   Research Assistant – frontend logic
   Pure ES2020 fetch-based code.  No framework, no build step.

   Structure
   ---------
   1. API helpers          thin wrappers around fetch()
   2. Auth                 login / session check / logout
   3. Search tab           query + render results
   4. Issues tab           list / create / edit / delete issues
   5. Bootstrap            entry point – check session then show right screen
   ───────────────────────────────────────────────────────────────────────── */

"use strict";

// ─── 1. API helpers ──────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || res.statusText), { status: res.status });
  return data;
}

const api = {
  me:           ()        => apiFetch("/api/me"),
  logout:       ()        => apiFetch("/auth/logout", { method: "POST" }),
  verifyApple:  (payload) => apiFetch("/auth/apple/verify", { method: "POST", body: JSON.stringify(payload) }),
  search:       (q, k=10) => apiFetch(`/api/search?q=${encodeURIComponent(q)}&k=${k}`),
  indexStatus:  ()        => apiFetch("/api/index/status"),
  rebuildIndex: ()        => apiFetch("/api/index/rebuild", { method: "POST" }),
  listIssues:   (status)  => apiFetch(`/api/issues${status ? "?status=" + status : ""}`),
  getIssue:     (id)      => apiFetch(`/api/issues/${id}`),
  createIssue:  (data)    => apiFetch("/api/issues", { method: "POST", body: JSON.stringify(data) }),
  updateIssue:  (id, data)=> apiFetch(`/api/issues/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteIssue:  (id)      => apiFetch(`/api/issues/${id}`, { method: "DELETE" }),
};

// ─── Utility ─────────────────────────────────────────────────────────────────

function el(id) { return document.getElementById(id); }

function showError(elem, msg) {
  elem.textContent = msg;
  elem.classList.remove("hidden");
}

function hideError(elem) {
  elem.textContent = "";
  elem.classList.add("hidden");
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ─── 2. Auth ─────────────────────────────────────────────────────────────────

function showLogin() {
  el("login-screen").classList.remove("hidden");
  el("app-screen").classList.add("hidden");
}

function showApp(user) {
  el("login-screen").classList.add("hidden");
  el("app-screen").classList.remove("hidden");
  el("user-name").textContent = user.name || user.email || user.sub || "";
}

// Called by the Apple JS SDK when sign-in succeeds (popup mode).
function onAppleSignInSuccess(event) {
  const { authorization, user } = event.detail;
  api.verifyApple({ identity_token: authorization.id_token, user: user || {} })
    .then((data) => showApp(data.user))
    .catch((err) => showError(el("login-error"), err.message));
}

// Called by the Apple JS SDK on failure.
function onAppleSignInFailure(event) {
  const msg = event.detail?.error || "Apple Sign In failed";
  showError(el("login-error"), msg);
}

async function handleLogout() {
  await api.logout().catch(() => {});
  showLogin();
}

// ─── 3. Search tab ───────────────────────────────────────────────────────────

async function loadIndexStatus() {
  try {
    const status = await api.indexStatus();
    const banner = el("index-banner");
    const msg = el("index-message");
    if (!status.built) {
      msg.textContent = "Search index has not been built yet. ";
      banner.classList.remove("hidden");
    } else if (status.chunks === 0) {
      msg.textContent = "Index is empty – no markdown files found in the research submodule. ";
      banner.classList.remove("hidden");
    } else {
      banner.classList.add("hidden");
    }
  } catch (_) {
    // Non-fatal; just hide the banner.
  }
}

async function runSearch() {
  const q = el("search-input").value.trim();
  if (!q) return;

  const container = el("search-results");
  container.innerHTML = '<p class="loading">Searching…</p>';

  try {
    const { results } = await api.search(q);
    renderSearchResults(results);
  } catch (err) {
    container.innerHTML = `<p class="error">${escHtml(err.message)}</p>`;
  }
}

function renderSearchResults(results) {
  const container = el("search-results");
  if (!results.length) {
    container.innerHTML = '<p class="empty">No results found.</p>';
    return;
  }

  container.innerHTML = results.map((r) => `
    <div class="result-card">
      <div class="result-meta">
        <span class="result-path">${escHtml(r.path)}</span>
        ${r.heading ? `<span class="result-heading">${escHtml(r.heading)}</span>` : ""}
        <span class="result-score">${(r.score * 100).toFixed(0)}%</span>
      </div>
      <p class="result-excerpt">${escHtml(r.excerpt)}</p>
    </div>
  `).join("");
}

async function triggerRebuild() {
  el("rebuild-btn").disabled = true;
  el("index-message").textContent = "Rebuilding index in background… this may take a minute.";
  try {
    await api.rebuildIndex();
    el("index-message").textContent = "Index rebuild started. Refresh results when complete.";
  } catch (err) {
    el("index-message").textContent = `Rebuild failed: ${err.message}`;
  } finally {
    el("rebuild-btn").disabled = false;
  }
}

// ─── 4. Issues tab ───────────────────────────────────────────────────────────

let _currentIssueFilter = "";  // "", "open", or "closed"
let _editingIssueId = null;    // null → new issue, number → existing

const STATUS_COLORS = { open: "status-open", closed: "status-closed" };

async function loadIssues(statusFilter) {
  _currentIssueFilter = statusFilter !== undefined ? statusFilter : _currentIssueFilter;
  const container = el("issues-list");
  container.innerHTML = '<p class="loading">Loading…</p>';
  try {
    const issues = await api.listIssues(_currentIssueFilter);
    renderIssues(issues);
  } catch (err) {
    container.innerHTML = `<p class="error">${escHtml(err.message)}</p>`;
  }
}

function renderIssues(issues) {
  const container = el("issues-list");
  if (!issues.length) {
    container.innerHTML = '<p class="empty">No issues found.</p>';
    return;
  }

  container.innerHTML = issues.map((issue) => `
    <div class="issue-row" data-id="${issue.id}" role="button" tabindex="0">
      <span class="issue-status ${STATUS_COLORS[issue.status] || ""}">${escHtml(issue.status)}</span>
      <span class="issue-title">${escHtml(issue.title)}</span>
      <span class="issue-labels">
        ${(issue.labels || []).map((l) => `<span class="label-badge">${escHtml(l)}</span>`).join("")}
      </span>
      <span class="issue-date">${new Date(issue.created_at).toLocaleDateString()}</span>
    </div>
  `).join("");

  // Bind click + keyboard on each row
  container.querySelectorAll(".issue-row").forEach((row) => {
    const id = Number(row.dataset.id);
    const open = () => openIssueModal(id);
    row.addEventListener("click", open);
    row.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") open(); });
  });
}

// ─── Issue modal ─────────────────────────────────────────────────────────────

function openNewIssueModal() {
  _editingIssueId = null;
  el("modal-title").textContent = "New issue";
  el("modal-title-input").value = "";
  el("modal-body-input").value = "";
  el("modal-labels-input").value = "";
  document.querySelector('[name="modal-status"][value="open"]').checked = true;
  el("modal-delete-btn").classList.add("hidden");
  hideError(el("modal-error"));
  el("issue-modal").classList.remove("hidden");
  el("modal-title-input").focus();
}

async function openIssueModal(issueId) {
  _editingIssueId = issueId;
  try {
    const issue = await api.getIssue(issueId);
    el("modal-title").textContent = "Edit issue";
    el("modal-title-input").value = issue.title;
    el("modal-body-input").value = issue.body;
    el("modal-labels-input").value = (issue.labels || []).join(", ");
    const statusRadio = document.querySelector(`[name="modal-status"][value="${issue.status}"]`);
    if (statusRadio) statusRadio.checked = true;
    el("modal-delete-btn").classList.remove("hidden");
    hideError(el("modal-error"));
    el("issue-modal").classList.remove("hidden");
    el("modal-title-input").focus();
  } catch (err) {
    alert(`Could not load issue: ${err.message}`);
  }
}

function closeIssueModal() {
  el("issue-modal").classList.add("hidden");
  _editingIssueId = null;
}

async function saveIssue() {
  const title = el("modal-title-input").value.trim();
  if (!title) {
    showError(el("modal-error"), "Title is required.");
    return;
  }

  const labelsRaw = el("modal-labels-input").value;
  const labels = labelsRaw.split(",").map((l) => l.trim()).filter(Boolean);
  const status = document.querySelector('[name="modal-status"]:checked').value;
  const body = el("modal-body-input").value;

  el("modal-save-btn").disabled = true;
  hideError(el("modal-error"));

  try {
    if (_editingIssueId === null) {
      await api.createIssue({ title, body, labels, status });
    } else {
      await api.updateIssue(_editingIssueId, { title, body, labels, status });
    }
    closeIssueModal();
    loadIssues();
  } catch (err) {
    showError(el("modal-error"), err.message);
  } finally {
    el("modal-save-btn").disabled = false;
  }
}

async function deleteIssue() {
  if (!_editingIssueId) return;
  if (!confirm("Delete this issue? This cannot be undone.")) return;
  try {
    await api.deleteIssue(_editingIssueId);
    closeIssueModal();
    loadIssues();
  } catch (err) {
    showError(el("modal-error"), err.message);
  }
}

// ─── Tab navigation ──────────────────────────────────────────────────────────

function activateTab(name) {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === name);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("hidden", panel.id !== `tab-${name}`);
  });
  if (name === "issues") loadIssues();
  if (name === "search") loadIndexStatus();
}

// ─── 5. Bootstrap ────────────────────────────────────────────────────────────

async function init() {
  // Wire up Apple Sign In SDK callbacks (called by the SDK after page load)
  document.addEventListener("AppleIDSignInOnSuccess", onAppleSignInSuccess);
  document.addEventListener("AppleIDSignInOnFailure", onAppleSignInFailure);

  // Tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  });

  // Logout
  el("logout-btn").addEventListener("click", handleLogout);

  // Search
  el("search-btn").addEventListener("click", runSearch);
  el("search-input").addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });
  el("rebuild-btn").addEventListener("click", triggerRebuild);

  // Issues
  el("new-issue-btn").addEventListener("click", openNewIssueModal);
  el("modal-save-btn").addEventListener("click", saveIssue);
  el("modal-cancel-btn").addEventListener("click", closeIssueModal);
  el("modal-delete-btn").addEventListener("click", deleteIssue);

  // Close modal on overlay click
  el("issue-modal").addEventListener("click", (e) => {
    if (e.target === el("issue-modal")) closeIssueModal();
  });

  // Issue filter buttons
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      loadIssues(btn.dataset.status);
    });
  });

  // Check session: show app if authenticated, login screen otherwise.
  try {
    const { authenticated, user } = await api.me();
    if (authenticated) {
      showApp(user);
      loadIndexStatus();
    } else {
      showLogin();
    }
  } catch (err) {
    if (err.status === 401) {
      showLogin();
    } else {
      showLogin();
      console.error("Session check failed:", err);
    }
  }
}

document.addEventListener("DOMContentLoaded", init);
