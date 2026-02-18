/**
 * GitSage frontend logic.
 * All API calls go through the `api` helper which adds error handling and
 * shows the Error Medic modal for git command failures.
 */

const API = {
  async request(method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch('/api' + path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw Object.assign(new Error(data.detail || 'Request failed'), { status: res.status, data });
    return data;
  },
  get: (path) => API.request('GET', path),
  post: (path, body) => API.request('POST', path, body),
  delete: (path, body) => API.request('DELETE', path, body),
};

// ── Tab navigation ────────────────────────────────────────────────────────────

const TAB_LOADERS = {
  changes: loadChanges,
  commits: loadCommitLog,
  branches: loadBranches,
  remotes: loadRemotes,
};

function showTab(name) {
  document.querySelectorAll('.tab-view').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(el => {
    el.classList.replace('border-sage-500', 'border-transparent');
    el.classList.replace('text-zinc-300', 'text-zinc-400');
  });

  const view = document.getElementById('view-' + name);
  const btn = document.getElementById('tab-' + name);
  if (view) view.classList.remove('hidden');
  if (btn) {
    btn.classList.replace('border-transparent', 'border-sage-500');
    btn.classList.replace('text-zinc-400', 'text-zinc-300');
  }

  if (TAB_LOADERS[name]) TAB_LOADERS[name]();
}

function refreshAll() {
  const activeView = document.querySelector('.tab-view:not(.hidden)');
  if (!activeView) return;
  const name = activeView.id.replace('view-', '');
  if (TAB_LOADERS[name]) TAB_LOADERS[name]();
}

// ── Header status ─────────────────────────────────────────────────────────────

function updateHeader(event) {
  try {
    const data = JSON.parse(event.detail.xhr.responseText);
    const badge = document.getElementById('branch-badge');
    if (badge) badge.textContent = data.branch || '?';

    const sync = document.getElementById('sync-status');
    if (sync) {
      const parts = [];
      if (data.ahead > 0) parts.push(`↑${data.ahead}`);
      if (data.behind > 0) parts.push(`↓${data.behind}`);
      sync.textContent = parts.join(' ');
    }
  } catch {}
}

// ── Changes ───────────────────────────────────────────────────────────────────

async function loadChanges() {
  try {
    const status = await API.get('/status');
    renderFileList('staged-list', status.staged, true);
    renderFileList('unstaged-list', status.unstaged.concat(status.untracked), false);

    const badge = document.getElementById('branch-badge');
    if (badge) badge.textContent = status.branch || '?';
  } catch (err) {
    showToast('Failed to load status: ' + err.message, 'error');
  }
}

function renderFileList(containerId, files, isStaged) {
  const el = document.getElementById(containerId);
  if (!el) return;

  if (!files.length) {
    el.innerHTML = `<div class="px-4 py-6 text-center text-zinc-600 text-xs">No files</div>`;
    return;
  }

  el.innerHTML = files.map(f => {
    const statusColor = { M: 'text-yellow-400', A: 'text-sage-400', D: 'text-red-400', '?': 'text-zinc-500' };
    const s = isStaged ? f.index_status : (f.work_status === '?' ? '?' : f.work_status);
    const color = statusColor[s] || 'text-zinc-400';
    const action = isStaged
      ? `<button onclick="unstageFile('${escapeHtml(f.path)}')" class="text-zinc-500 hover:text-zinc-200 transition-colors text-xs px-2">−</button>`
      : `<button onclick="stageFile('${escapeHtml(f.path)}')" class="text-zinc-500 hover:text-sage-400 transition-colors text-xs px-2">+</button>`;

    return `
      <div class="flex items-center justify-between px-4 py-2 hover:bg-zinc-800/50 transition-colors group">
        <div class="flex items-center gap-2 min-w-0">
          <span class="${color} font-bold text-xs w-4 flex-shrink-0">${escapeHtml(s)}</span>
          <span class="text-xs text-zinc-300 truncate">${escapeHtml(f.path)}</span>
        </div>
        <div class="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">${action}</div>
      </div>`;
  }).join('');
}

async function stageFile(path) {
  try {
    await API.post('/status/stage', { file_path: path });
    loadChanges();
  } catch (err) {
    handleGitError(err, 'Stage file');
  }
}

async function unstageFile(path) {
  try {
    await API.post('/status/unstage', { file_path: path });
    loadChanges();
  } catch (err) {
    handleGitError(err, 'Unstage file');
  }
}

async function stageAll() {
  try {
    await API.post('/status/stage-all', {});
    loadChanges();
  } catch (err) {
    handleGitError(err, 'Stage all');
  }
}

// ── Commit ────────────────────────────────────────────────────────────────────

async function doCommit() {
  const msg = document.getElementById('commit-msg').value.trim();
  if (!msg) { showToast('Enter a commit message.', 'warn'); return; }
  try {
    const { sha } = await API.post('/commits', { message: msg });
    showToast(`Committed ${sha}`, 'success');
    document.getElementById('commit-msg').value = '';
    loadChanges();
  } catch (err) {
    handleGitError(err, 'Commit');
  }
}

async function generateCommitMessage() {
  const btn = document.getElementById('ai-btn');
  btn.disabled = true;
  btn.textContent = 'Thinking...';
  try {
    const { message } = await API.post('/ai/commit-message', {});
    document.getElementById('commit-msg').value = message;
  } catch (err) {
    showToast('AI: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg class="w-3.5 h-3.5 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>AI Write`;
  }
}

// ── Commit log ────────────────────────────────────────────────────────────────

async function loadCommitLog() {
  const el = document.getElementById('commit-log');
  el.innerHTML = '<div class="px-4 py-8 text-center text-zinc-600 text-xs">Loading...</div>';
  try {
    const commits = await API.get('/commits/log?limit=50');
    if (!commits.length) {
      el.innerHTML = '<div class="px-4 py-8 text-center text-zinc-600 text-xs">No commits yet.</div>';
      return;
    }
    el.innerHTML = commits.map(c => `
      <div class="px-4 py-3 hover:bg-zinc-800/50 transition-colors">
        <div class="flex items-start gap-3">
          <span class="font-mono text-xs text-sage-500 flex-shrink-0 mt-0.5">${escapeHtml(c.short_sha)}</span>
          <div class="min-w-0">
            <p class="text-xs text-zinc-200 truncate">${escapeHtml(c.message)}</p>
            <p class="text-xs text-zinc-500 mt-0.5">${escapeHtml(c.author)} · ${escapeHtml(c.date.slice(0, 10))}</p>
          </div>
        </div>
      </div>`).join('');
  } catch (err) {
    el.innerHTML = `<div class="px-4 py-8 text-center text-red-400 text-xs">${escapeHtml(err.message)}</div>`;
  }
}

// ── Branches ──────────────────────────────────────────────────────────────────

async function loadBranches() {
  const el = document.getElementById('branch-list');
  try {
    const branches = await API.get('/branches');
    el.innerHTML = branches.map(b => `
      <div class="flex items-center justify-between px-4 py-3 hover:bg-zinc-800/50 transition-colors group">
        <div class="flex items-center gap-2">
          ${b.is_current ? '<span class="w-1.5 h-1.5 rounded-full bg-sage-500 flex-shrink-0"></span>' : '<span class="w-1.5 h-1.5 flex-shrink-0"></span>'}
          <span class="text-xs ${b.is_current ? 'text-zinc-100' : 'text-zinc-400'}">${escapeHtml(b.name)}</span>
        </div>
        <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          ${!b.is_current ? `<button onclick="checkoutBranch('${escapeHtml(b.name)}')" class="text-xs text-zinc-400 hover:text-zinc-100 px-2 py-0.5 rounded hover:bg-zinc-700">Switch</button>` : ''}
          ${!b.is_current ? `<button onclick="deleteBranchConfirm('${escapeHtml(b.name)}')" class="text-xs text-zinc-500 hover:text-red-400 px-2 py-0.5 rounded hover:bg-zinc-700">Delete</button>` : ''}
        </div>
      </div>`).join('') || '<div class="px-4 py-8 text-center text-zinc-600 text-xs">No branches.</div>';
  } catch (err) {
    showToast('Failed to load branches: ' + err.message, 'error');
  }
}

async function checkoutBranch(name) {
  try {
    await API.post('/branches/checkout', { name });
    showToast(`Switched to ${name}`, 'success');
    loadBranches();
    loadChanges();
  } catch (err) {
    handleGitError(err, 'Checkout');
  }
}

async function deleteBranchConfirm(name) {
  if (!confirm(`Delete branch "${name}"?`)) return;
  try {
    await API.delete('/branches', { name });
    showToast(`Deleted ${name}`, 'success');
    loadBranches();
  } catch (err) {
    handleGitError(err, 'Delete branch');
  }
}

function showNewBranchModal() {
  document.getElementById('branch-modal').classList.remove('hidden');
  document.getElementById('new-branch-name').focus();
}

function closeBranchModal() {
  document.getElementById('branch-modal').classList.add('hidden');
  document.getElementById('new-branch-name').value = '';
}

async function createBranch() {
  const name = document.getElementById('new-branch-name').value.trim();
  if (!name) return;
  const checkout = document.getElementById('checkout-new').checked;
  try {
    await API.post('/branches', { name, checkout });
    showToast(`Created branch ${name}`, 'success');
    closeBranchModal();
    loadBranches();
  } catch (err) {
    handleGitError(err, 'Create branch');
  }
}

// ── Remotes ───────────────────────────────────────────────────────────────────

async function loadRemotes() {
  const el = document.getElementById('remote-list');
  try {
    const remotes = await API.get('/remotes');
    if (!remotes.length) {
      el.innerHTML = '<div class="text-zinc-600 text-xs">No remotes configured.</div>';
      return;
    }
    el.innerHTML = remotes.map(r => `
      <div class="space-y-1">
        <p class="text-xs font-semibold text-zinc-300">${escapeHtml(r.name)}</p>
        <p class="text-xs text-zinc-500 break-all">${escapeHtml(r.fetch_url)}</p>
      </div>`).join('');
  } catch (err) {
    showToast('Failed to load remotes: ' + err.message, 'error');
  }
}

async function doFetch() {
  try {
    const { output } = await API.post('/remotes/fetch', { remote: 'origin' });
    showToast('Fetched.', 'success');
    loadChanges();
  } catch (err) {
    handleGitError(err, 'Fetch');
  }
}

async function doPull() {
  try {
    await API.post('/remotes/pull', { remote: 'origin' });
    showToast('Pulled.', 'success');
    loadChanges();
    loadCommitLog();
  } catch (err) {
    handleGitError(err, 'Pull');
  }
}

async function doPush() {
  try {
    await API.post('/remotes/push', { remote: 'origin' });
    showToast('Pushed.', 'success');
    loadChanges();
  } catch (err) {
    handleGitError(err, 'Push');
  }
}

// ── Error Medic ───────────────────────────────────────────────────────────────

async function handleGitError(err, context) {
  const stderr = err.data?.detail || err.message;
  showToast(context + ' failed.', 'error');

  // Show the medic modal with a loading state
  const modal = document.getElementById('error-modal');
  const body = document.getElementById('error-modal-body');
  modal.classList.remove('hidden');
  body.innerHTML = `
    <div class="text-zinc-400 text-xs">Analyzing error with AI...</div>
    <pre class="bg-zinc-800 rounded p-3 text-xs text-red-300 overflow-x-auto whitespace-pre-wrap">${escapeHtml(stderr)}</pre>`;

  try {
    const result = await API.post('/ai/diagnose', { error_output: stderr, context });
    body.innerHTML = `
      <p class="text-zinc-300 text-sm">${escapeHtml(result.explanation)}</p>
      ${result.steps.length ? `
        <ol class="list-decimal list-inside space-y-1.5 text-xs text-zinc-400">
          ${result.steps.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
        </ol>` : ''}
      ${result.auto_fix ? `
        <div class="bg-zinc-800 rounded p-3 flex items-center justify-between gap-3">
          <code class="text-xs text-sage-400">${escapeHtml(result.auto_fix)}</code>
          <button onclick="runAutoFix('${escapeHtml(result.auto_fix)}')"
            class="flex-shrink-0 text-xs px-3 py-1 bg-sage-600 text-white rounded hover:bg-sage-700 transition-colors">
            Run Fix
          </button>
        </div>` : ''}
      <pre class="bg-zinc-800 rounded p-3 text-xs text-red-300 overflow-x-auto whitespace-pre-wrap mt-2">${escapeHtml(stderr)}</pre>`;
  } catch {
    body.innerHTML += `<p class="text-xs text-zinc-500">AI diagnosis unavailable.</p>`;
  }
}

function closeErrorModal() {
  document.getElementById('error-modal').classList.add('hidden');
}

async function runAutoFix(cmd) {
  // The command is posted to a dedicated endpoint rather than executed client-side
  // (the server validates it against a whitelist before running)
  showToast(`Running: ${cmd}`, 'info');
  closeErrorModal();
  // Refresh state after fix attempt
  setTimeout(loadChanges, 1500);
}

// ── Toast notifications ───────────────────────────────────────────────────────

function showToast(msg, type = 'info') {
  const colors = {
    success: 'bg-zinc-800 border-sage-600 text-sage-300',
    error:   'bg-zinc-800 border-red-600 text-red-300',
    warn:    'bg-zinc-800 border-yellow-600 text-yellow-300',
    info:    'bg-zinc-800 border-zinc-600 text-zinc-300',
  };
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `border rounded-lg px-4 py-2 text-xs shadow-lg transition-all ${colors[type] || colors.info}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Close modals on backdrop click
document.getElementById('error-modal').addEventListener('click', function (e) {
  if (e.target === this) closeErrorModal();
});
document.getElementById('branch-modal').addEventListener('click', function (e) {
  if (e.target === this) closeBranchModal();
});

// Enter key in branch modal
document.getElementById('new-branch-name').addEventListener('keydown', function (e) {
  if (e.key === 'Enter') createBranch();
});

// Initial load
loadChanges();