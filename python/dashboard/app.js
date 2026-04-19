const API_BASE   = "";
const REFRESH_MS = 5000;

let statusChart   = null;
let userNameCache = {};
let presenceCache = {};
let filterActive  = false;  

document.addEventListener("DOMContentLoaded", () => {
  initClock();
  initFilter();
  refreshAll();
  setInterval(refreshAll, REFRESH_MS);
  setInterval(updateClock, 1000);
});

async function refreshAll() {
  await fetchAndRenderUsers();
  await Promise.all([
    fetchAndRenderTodayStats(),
    fetchAndRenderAnomalies(),
    fetchLatestScan(),
  ]);
  // Only refresh logs if no filter is active
  if (!filterActive) {
    await fetchAndRenderLogs();
  }
}

// -----------------------------------------------------------------
// Live Clock
// -----------------------------------------------------------------
function initClock() { updateClock(); }

function updateClock() {
  const el = document.getElementById("today-clock");
  if (!el) return;
  el.textContent = new Date().toLocaleString("en-NZ", {
    weekday: "long", day: "2-digit", month: "long", year: "numeric",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  });
}

// -----------------------------------------------------------------
// Today Stats
// -----------------------------------------------------------------
async function fetchAndRenderTodayStats() {
  try {
    const res  = await fetch(`${API_BASE}/api/stats/today`);
    if (!res.ok) return;
    const data = await res.json();
    setText("stat-total",     data.total_scans);
    setText("stat-allowed",   data.total_allowed);
    setText("stat-denied",    data.total_denied);
    setText("stat-anomalies", data.total_anomalies);
    setText("stat-users",     data.unique_users);

    const res2 = await fetch(`${API_BASE}/api/stats`);
    if (res2.ok) {
      const all = await res2.json();
      renderChart(all.total_allowed, all.total_denied);
    }
  } catch (err) {
    console.error("[TodayStats]", err);
  }
}

// -----------------------------------------------------------------
// Chart
// -----------------------------------------------------------------
function renderChart(allowed, denied) {
  const ctx = document.getElementById("statusChart").getContext("2d");
  if (statusChart) {
    statusChart.data.datasets[0].data = [allowed, denied];
    statusChart.update();
    return;
  }
  statusChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Allowed", "Denied"],
      datasets: [{
        data: [allowed, denied],
        backgroundColor: ["#00c853", "#d50000"],
        borderColor:     ["#00e676", "#ff5252"],
        borderWidth: 2, hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom", labels: { color: "#aaa", font: { size: 13 }, padding: 20 } },
      },
      cutout: "65%",
    },
  });
}

// -----------------------------------------------------------------
// Name + Presence
// -----------------------------------------------------------------
function getDisplayName(uid) { return userNameCache[uid] || uid; }
function getPresence(uid)    { return presenceCache[uid] || "OUTSIDE"; }

// -----------------------------------------------------------------
// Live Scan
// -----------------------------------------------------------------
async function fetchLatestScan() {
  try {
    const res = await fetch(`${API_BASE}/api/latest`);
    if (!res.ok) return;
    const log = await res.json();
    if (!log) return;

    const name     = getDisplayName(log.uid);
    const presence = getPresence(log.uid);
    const isDeny   = log.status === "denied";
    const isIn     = log.event === "IN";
    const color    = isDeny ? "#ff5252" : isIn ? "#00e676" : "#448aff";
    const icon     = isDeny ? "🚫" : isIn ? "✅" : "🔄";
    const evtLabel = isDeny ? "DENIED" : log.event;
    const presColor = presence === "INSIDE" ? "#00e676" : "#448aff";
    const presIcon  = presence === "INSIDE" ? "🟢" : "🔵";

    document.getElementById("live-card").innerHTML = `
      <div class="live-scan-card" style="border-left: 4px solid ${color}">
        <div class="live-top-row">
          <div class="live-name">${icon} ${escHtml(name)}</div>
          <div class="live-presence-badge" style="background:${presColor}22; border:1px solid ${presColor}; color:${presColor}">
            ${presIcon} ${presence}
          </div>
        </div>
        <div class="live-uid">UID: <code>${escHtml(log.uid)}</code></div>
        <div class="live-divider"></div>
        <div class="live-detail-row">
          <div class="live-detail-item">
            <div class="live-detail-label">Status</div>
            <span class="badge badge-${log.status}">${log.status.toUpperCase()}</span>
          </div>
          <div class="live-detail-item">
            <div class="live-detail-label">Event</div>
            <span class="live-event" style="color:${color}; font-size:1.1rem; font-weight:700">${evtLabel}</span>
          </div>
          <div class="live-detail-item">
            <div class="live-detail-label">Time</div>
            <span class="live-time">${formatTime(log.timestamp)}</span>
          </div>
        </div>
      </div>
    `;
  } catch (e) { console.error("[LiveScan]", e); }
}

// -----------------------------------------------------------------
// Users List
// -----------------------------------------------------------------
async function fetchAndRenderUsers() {
  try {
    const res   = await fetch(`${API_BASE}/api/users`);
    if (!res.ok) return;
    const users = await res.json();

    const logsRes = await fetch(`${API_BASE}/api/logs?limit=200`);
    const allLogs = logsRes.ok ? await logsRes.json() : [];

    const latestEvent = {};
    allLogs.forEach(log => {
      if (log.status === "allowed" && !latestEvent[log.uid]) {
        latestEvent[log.uid] = log.event;
      }
    });

    users.forEach(u => {
      userNameCache[u.uid] = u.name;
      presenceCache[u.uid] = latestEvent[u.uid] === "IN" ? "INSIDE" : "OUTSIDE";
    });

    const el = document.getElementById("users-list");
    if (!users || users.length === 0) {
      el.innerHTML = `<p class="empty-msg">No users yet.</p>`;
      return;
    }

    el.innerHTML = users.map(u => {
      const presence  = presenceCache[u.uid] || "OUTSIDE";
      const presColor = presence === "INSIDE" ? "#00e676" : "#448aff";
      const presIcon  = presence === "INSIDE" ? "🟢" : "🔵";
      return `
        <a href="/dashboard/user.html?uid=${encodeURIComponent(u.uid)}" class="user-item">
          <div class="user-avatar">${u.name[0].toUpperCase()}</div>
          <div class="user-info">
            <div class="user-name-row">
              <div class="user-name">${escHtml(u.name)}</div>
              <div class="user-presence" style="color:${presColor}; border-color:${presColor}">
                ${presIcon} ${presence === "INSIDE" ? "Inside" : "Outside"}
              </div>
            </div>
            <div class="user-uid"><code>${escHtml(u.uid)}</code></div>
            <div class="user-meta">Last: ${u.last_seen ? formatTime(u.last_seen) : "—"}</div>
          </div>
          <div class="user-stats">
            <span class="user-stat green">${u.allowed} ✓</span>
            <span class="user-stat red">${u.denied} ✗</span>
          </div>
          <span class="user-arrow">→</span>
        </a>
      `;
    }).join("");
  } catch (err) { console.error("[Users]", err); }
}

// -----------------------------------------------------------------
// Log Filter
// -----------------------------------------------------------------
function initFilter() {
  const today = new Date().toISOString().split("T")[0];
  const dateFromEl = document.getElementById("filter-date-from");
  const dateToEl   = document.getElementById("filter-date-to");
  if (dateFromEl) dateFromEl.value = today;
  if (dateToEl)   dateToEl.value   = today;

  document.getElementById("filter-apply")?.addEventListener("click", applyFilter);
  document.getElementById("filter-reset")?.addEventListener("click", resetFilter);
}

async function applyFilter() {
  const dateFrom = document.getElementById("filter-date-from").value;
  const dateTo   = document.getElementById("filter-date-to").value;
  const timeFrom = document.getElementById("filter-time-from").value || null;
  const timeTo   = document.getElementById("filter-time-to").value   || null;

  if (!dateFrom || !dateTo) {
    alert("Please select a date range.");
    return;
  }

  let url = `${API_BASE}/api/logs/filter?date_from=${dateFrom}&date_to=${dateTo}`;
  if (timeFrom) url += `&time_from=${timeFrom}`;
  if (timeTo)   url += `&time_to=${timeTo}`;

  try {
    const res  = await fetch(url);
    if (!res.ok) return;
    const logs = await res.json();

    filterActive = true;   // ← lock: stop auto-refresh from overwriting
    renderLogsTable(logs);

    const indicator = document.getElementById("filter-indicator");
    if (indicator) {
      const rangeStr = dateFrom === dateTo ? dateFrom : `${dateFrom} → ${dateTo}`;
      const timeStr  = timeFrom || timeTo ? ` | ${timeFrom || "00:00"} – ${timeTo || "23:59"}` : "";
      indicator.textContent = `🔍 Showing ${logs.length} result(s) for ${rangeStr}${timeStr}`;
      indicator.style.display = "block";
    }
  } catch (err) { console.error("[Filter]", err); }
}

function resetFilter() {
  const today = new Date().toISOString().split("T")[0];
  document.getElementById("filter-date-from").value = today;
  document.getElementById("filter-date-to").value   = today;
  document.getElementById("filter-time-from").value = "";
  document.getElementById("filter-time-to").value   = "";

  const indicator = document.getElementById("filter-indicator");
  if (indicator) indicator.style.display = "none";

  filterActive = false;    // ← unlock: auto-refresh resumes
  fetchAndRenderLogs();
}

// -----------------------------------------------------------------
// Logs Table
// -----------------------------------------------------------------
async function fetchAndRenderLogs() {
  try {
    const res  = await fetch(`${API_BASE}/api/logs`);
    if (!res.ok) return;
    renderLogsTable(await res.json());
  } catch (err) { console.error("[Logs]", err); }
}

function renderLogsTable(logs) {
  const tbody = document.getElementById("logs-tbody");
  if (!logs || logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-msg">No logs found.</td></tr>`;
    return;
  }
  tbody.innerHTML = logs.map(log => `
    <tr>
      <td>${log.id}</td>
      <td>
        <a href="/dashboard/user.html?uid=${encodeURIComponent(log.uid)}" class="uid-link">
          <code>${escHtml(log.uid)}</code>
        </a>
      </td>
      <td>${statusBadge(log.status)}</td>
      <td>${eventTag(log.event)}</td>
      <td>${formatTime(log.timestamp)}</td>
      <td>${anomalyBadge(log.is_anomaly)}</td>
    </tr>
  `).join("");
}

// -----------------------------------------------------------------
// Anomaly Alerts
// -----------------------------------------------------------------
async function fetchAndRenderAnomalies() {
  try {
    const res  = await fetch(`${API_BASE}/api/anomalies`);
    if (!res.ok) return;
    const data = await res.json();
    const el   = document.getElementById("anomaly-list");

    if (!data || data.length === 0) {
      el.innerHTML = `<p class="empty-msg">No anomalies detected.</p>`;
      return;
    }

    el.innerHTML = data.slice(0, 5).map(a => `
      <div class="anomaly-item">
        <div class="anomaly-uid">${escHtml(getDisplayName(a.uid))}</div>
        <div class="anomaly-reason">${escHtml(a.anomaly_reason || "Flagged")}</div>
        <div class="anomaly-time">${formatTime(a.timestamp)}</div>
      </div>
    `).join("");
  } catch (err) { console.error("[Anomalies]", err); }
}

// -----------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------
function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "—";
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatTime(isoStr) {
  if (!isoStr) return "—";
  // Parse as local time (DB stores local time now)
  return new Date(isoStr).toLocaleString("en-NZ", {
    day: "2-digit", month: "short",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  });
}

function statusBadge(status) {
  return status === "allowed"
    ? `<span class="badge badge-allowed">Allowed</span>`
    : `<span class="badge badge-denied">Denied</span>`;
}

function eventTag(event) {
  if (event === "IN")  return `<span class="event-in">IN</span>`;
  if (event === "OUT") return `<span class="event-out">OUT</span>`;
  return `<span class="event-none">—</span>`;
}

function anomalyBadge(isAnomaly) {
  return isAnomaly
    ? `<span class="badge badge-anomaly">⚠ Yes</span>`
    : `<span class="badge badge-ok">—</span>`;
}