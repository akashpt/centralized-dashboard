var SESSION_KEY = "machineMonitoringSession";
var USER_KEY = "machineMonitoringUser";

function parseJson(raw, fallback) {
  try {
    return JSON.parse(raw);
  } catch (error) {
    return fallback || {};
  }
}

function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function bridgeReady() {
  return new Promise(function (resolve) {
    if (!window.qt || !window.qt.webChannelTransport || !window.QWebChannel) {
      resolve(null);
      return;
    }

    new QWebChannel(qt.webChannelTransport, function (channel) {
      resolve(channel.objects.bridge);
    });
  });
}

function callBridge(method) {
  var args = Array.prototype.slice.call(arguments, 1);
  return bridgeReady().then(function (bridge) {
    if (!bridge || typeof bridge[method] !== "function") {
      throw new Error("Python bridge is not available.");
    }

    return new Promise(function (resolve) {
      bridge[method].apply(bridge, args.concat(resolve));
    }).then(function (raw) {
      return parseJson(raw, { ok: false, error: "Invalid bridge response" });
    });
  });
}

function setUserShell() {
  var user = parseJson(localStorage.getItem(USER_KEY), null);
  if (!user) return;

  var nameEl = document.getElementById("user-name");
  var avatarEl = document.getElementById("user-avatar");
  if (nameEl) nameEl.textContent = user.name;
  if (avatarEl) avatarEl.textContent = user.initials;
}

function clearLogin() {
  localStorage.removeItem(SESSION_KEY);
  localStorage.removeItem(USER_KEY);
}

function requireLoginForPage() {
  return bridgeReady().then(function (bridge) {
    if (!bridge) {
      if (!localStorage.getItem(SESSION_KEY)) {
        window.location.href = "index.html";
        return false;
      }
      setUserShell();
      return true;
    }

    return new Promise(function (resolve) {
      bridge.getSessionId(resolve);
    }).then(function (sessionId) {
      var isLoggedIn = localStorage.getItem(SESSION_KEY) === sessionId;
      if (!isLoggedIn) {
        clearLogin();
        window.location.href = "index.html";
        return false;
      }

      setUserShell();
      return true;
    });
  });
}

function safeValue(value) {
  if (value === undefined || value === null || value === "") return "-";
  return value;
}

function renderKeyValueRows(data) {
  return Object.keys(data)
    .map(function (key) {
      return `<div class="detail-row">
        <span>${key}</span>
        <strong>${safeValue(data[key])}</strong>
      </div>`;
    })
    .join("");
}

function renderMetricCards(data) {
  var icons = {
    "Doff No": "fa-hashtag",
    "Full Cop": "fa-circle-dot",
    "Half Cop": "fa-circle-half-stroke",
    "Quater Cop": "fa-chart-pie",
    "Total Inspected": "fa-boxes-stacked",
    Good: "fa-check",
    Defect: "fa-triangle-exclamation",
    Empty: "fa-box-open",
  };
  var tone = {
    "Full Cop": "good",
    Good: "good",
    Defect: "warning",
    Empty: "warning",
  };

  return Object.keys(data)
    .map(function (key) {
      return `<div class="detail-metric ${tone[key] || ""}">
        <span><i class="fa-solid ${icons[key] || "fa-gauge"}"></i></span>
        <small>${key}</small>
        <strong>${safeValue(data[key])}</strong>
      </div>`;
    })
    .join("");
}

function getStat(report, key) {
  return report.stats && report.stats[key] !== undefined ? report.stats[key] : 0;
}

function toNumber(value) {
  var number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function titleCase(value) {
  return String(value || "stopped").charAt(0).toUpperCase() + String(value || "stopped").slice(1);
}

function renderMachineDetails(machine, report) {
  document.getElementById("report-link").href =
    "report.html?machineId=" + encodeURIComponent(machine.id);
  document.getElementById("machine-detail-title").textContent = machine.name;
  document.getElementById("machine-detail-subtitle").textContent =
     safeValue(report.material);
  document.getElementById("machine-photo").src = machine.image || "../static/img/machine_image.jpeg";
  document.getElementById("machine-detail-time-strip").innerHTML = [
    { label: "Start Time", value: report.startTime,  },
    { label: "End Time", value: report.endTime,   },
  ]
    .map(function (item) {
      return `<div class="machine-time-pill">
        <span><i class="fa-solid ${item.icon}"></i>${item.label}</span>
        <strong>${safeValue(item.value)}</strong>
      </div>`;
    })
    .join("");
  document.getElementById("machine-detail-meta").innerHTML = [
    { label: "Machine No " + safeValue(report.machineNo), icon: "fa-hashtag" },
    { label: safeValue(report.date), icon: "fa-calendar-day" },
    { label: "Duration " + safeValue(report.duration), icon: "fa-clock" },
  ]
    .map(function (item) {
      return `<span class="machine-meta-pill"><i class="fa-solid ${item.icon}"></i>${item.label}</span>`;
    })
    .join("");

  var statusEl = document.getElementById("machine-status");
  statusEl.textContent = titleCase(machine.status);
  statusEl.className = "machine-detail-status " + (machine.status === "running" ? "running" : "stopped");

  document.getElementById("detail-kpis").innerHTML = [
    { label: "Inspected", value: getStat(report, "Total Cops"), icon: "fa-magnifying-glass-chart" },
    { label: "Good", value: getStat(report, "Total Good Cops"), icon: "fa-check", tone: "good" },
    { label: "Defect", value: getStat(report, "Defect Count"), icon: "fa-xmark", tone: "warning" },
  ]
    .map(function (item) {
      return `<div class="detail-kpi ${item.tone || ""}">
        <i class="fa-solid ${item.icon}"></i>
        <span>${item.label}</span>
        <strong>${safeValue(item.value)}</strong>
      </div>`;
    })
    .join("");

  document.getElementById("fr-info").innerHTML = renderKeyValueRows({
    "Machine No": report.machineNo,
    Date: report.date,
    Material: report.material,
    Yarn: report.yarn,
    Count: report.count,
    Duration: report.duration,
  });

  var stats = report.stats || {};
  var totalCops = toNumber(stats["Total Cops"]);
  var goodCops = toNumber(stats["Total Good Cops"]);
  var defectCount = toNumber(stats["Defect Count"]);
  var emptyCops = Math.max(totalCops - goodCops - defectCount, 0);

  document.getElementById("production-info").innerHTML = renderMetricCards({
    "Doff No": report.doffNo,
    "Full Cop": stats["Total Full Cops"],
    "Half Cop": stats["Total Half Cops"],
    "Quater Cop": stats["Total Quarter Cops"],
    "Total Inspected": stats["Total Cops"],
    Good: stats["Total Good Cops"],
    Defect: stats["Defect Count"],
    Empty: emptyCops,
  });
}

function loadMachineDetails() {
  var machineId = getQueryParam("machineId");
  var body = document.getElementById("details-body");

  if (!machineId) {
    body.innerHTML = '<div class="empty-state">No machine ID was provided.</div>';
    return;
  }

  callBridge("getMachineDetails", machineId)
    .then(function (response) {
      if (!response.ok) throw new Error(response.error || "Unable to load machine details.");
      renderMachineDetails(response.machine, response.report);
    })
    .catch(function (error) {
      body.innerHTML = `<div class="empty-state">${error.message}</div>`;
    });
}

function handleLogout() {
  clearLogin();
  window.location.href = "index.html";
}

document.addEventListener("DOMContentLoaded", function () {
  requireLoginForPage().then(function (allowed) {
    if (allowed) loadMachineDetails();
  });
});
