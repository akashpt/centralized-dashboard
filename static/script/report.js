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

function renderRows(data) {
  return Object.keys(data)
    .map(function (key) {
      return `<tr><td>${key}</td><td class="td-val">${data[key]}</td></tr>`;
    })
    .join("");
}

function toNumber(value) {
  var number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function getStat(stats, key) {
  return toNumber(stats[key]);
}

function getPercent(value, total) {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

function renderReportCards(targetId, cards) {
  document.getElementById(targetId).innerHTML = cards
    .map(function (card) {
      return `<article class="report-stat-card report-stat-${card.tone}">
        <div class="report-stat-icon">
          <i class="fa-solid ${card.icon}"></i>
        </div>
        <div class="report-stat-label">${card.label}</div>
        <div class="report-stat-value">${card.value}</div>
        <div class="report-stat-sub">${card.sub}</div>
      </article>`;
    })
    .join("");
}

var reportCharts = {};

function renderChartDonut(chartId, labels, values, colors) {
  var canvas = document.getElementById(chartId);
  var border = "#ffffff";

  if (reportCharts[chartId]) {
    reportCharts[chartId].destroy();
  }

  reportCharts[chartId] = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors,
          borderColor: [border, border, border],
          borderWidth: 3,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 500 },
      cutout: "70%",
      plugins: {
        tooltip: {
          callbacks: {
            label: function (context) {
              var data = context.dataset.data;
              var total = data.reduce(function (sum, value) {
                return sum + value;
              }, 0);
              var value = context.parsed;
              return (
                " " +
                context.label +
                ": " +
                value +
                " (" +
                getPercent(value, total) +
                "%)"
              );
            },
          },
        },
        legend: {
          position: "bottom",
          labels: {
            padding: 14,
            font: { size: 11 },
            color: "#8b95a5",
            usePointStyle: true,
            boxWidth: 10,
            boxHeight: 15,
            pointStyleWidth: 15,
          },
        },
      },
    },
  });
}

function renderReport(machine, report) {
  document.getElementById("report-title").textContent =
    machine.name + " Report";
  document.getElementById("details-link").href =
    "machine-details.html?machineId=" + encodeURIComponent(machine.id);

  var defects = report.defects || [];
  var stats = report.stats || {};
  var totalCops = getStat(stats, "Total Cops");
  var defectCount = getStat(stats, "Defect Count") || defects.length;
  var goodCops = getStat(stats, "Total Good Cops");
  var fullCops = getStat(stats, "Total Full Cops");
  var halfCops = getStat(stats, "Total Half Cops");
  var quarterCops = getStat(stats, "Total Quarter Cops");
  var emptyCops = Math.max(totalCops - goodCops - defectCount, 0);
  var doffCount = toNumber(report.doffNo);

  function renderInfoRows(fields) {
    return fields
      .map(function (f) {
        return (
          '<div class="fr-info-row">' +
          '<span class="fr-info-row-left"><i class="fa-solid ' +
          f.icon +
          '"></i>' +
          f.label +
          "</span>" +
          '<span class="fr-info-row-val">' +
          (f.value || "—") +
          "</span>" +
          "</div>"
        );
      })
      .join("");
  }

  document.getElementById("report-info-left").innerHTML = renderInfoRows([
    { icon: "fa-fingerprint", label: "FR No", value: report.frNo },
    { icon: "fa-server", label: "Machine No", value: report.machineNo },
    { icon: "fa-calendar-days", label: "Date", value: report.date },
    { icon: "fa-hashtag", label: "Doff No", value: report.doffNo },
    { icon: "fa-box", label: "Material", value: report.material },
  ]);

  document.getElementById("report-info-right").innerHTML = renderInfoRows([
    { icon: "fa-rotate", label: "Yarn", value: report.yarn },
    { icon: "fa-list-ol", label: "Count", value: report.count },
    { icon: "fa-play", label: "Start Time", value: report.startTime },
    { icon: "fa-stop", label: "End Time", value: report.endTime },
    { icon: "fa-clock", label: "Duration", value: report.duration },
  ]);

  renderReportCards("cop-status-cards", [
    {
      label: "DOFF Count",
      value: doffCount,
      sub: "Total Doff Count",
      icon: "fa-hashtag",
      tone: "amber",
    },
    {
      label: "Full Cops",
      value: fullCops,
      sub: getPercent(fullCops, totalCops) + "% wound",
      icon: "fa-circle-dot",
      tone: "green",
    },
    {
      label: "Half Cops",
      value: halfCops,
      sub: "~50% wound",
      icon: "fa-circle-half-stroke",
      tone: "orange",
    },
    {
      label: "Quarter Cops",
      value: quarterCops,
      sub: "~25% wound",
      icon: "fa-battery-quarter",
      tone: "red",
    },
  ]);

  renderReportCards("inspection-cards", [
    {
      label: "Total Inspected",
      value: totalCops,
      sub: "units today",
      icon: "fa-boxes-stacked",
      tone: "blue",
    },
    {
      label: "Good Units",
      value: goodCops,
      sub: "passed QC",
      icon: "fa-check",
      tone: "green",
    },
    {
      label: "Defective",
      value: defectCount,
      sub: "rejected",
      icon: "fa-xmark",
      tone: "orange",
    },
    {
      label: "Empty",
      value: emptyCops,
      sub: "no thread",
      icon: "fa-circle",
      tone: "red",
    },
  ]);

  renderChartDonut(
    "unit-status-chart",
    ["Good", "Defective", "Empty"],
    [goodCops, defectCount, emptyCops],
    ["#16a34a", "#cf1f32", "#8b8f96"],
  );

  renderChartDonut(
    "cop-fill-chart",
    ["Full", "Half", "Quarter"],
    [fullCops, halfCops, quarterCops],
    ["#16a34a", "#8b8f96", "#cf1f32"],
  );

  document.getElementById("defect-body").innerHTML = defects.length
    ? defects
        .map(function (defect) {
          return `<tr>
            <td>${defect.id}</td>
            <td>${defect.copNumber}</td>
            <td>${defect.thread}%</td>
           
            <td><span class="badge badge-defect">${defect.result}</span></td>
            <td>${stats["Total Cops"]}</td>
            <td>${stats["Total Good Cops"]}</td>
            <td>${stats["Defect Count"]}</td>
            <td>${stats["Total Full Cops"]}</td>
            <td>${stats["Total Half Cops"]}</td>
            <td>${stats["Total Quarter Cops"]}</td>
             <td>${defect.createdAt}</td>
              <td>${defect.endTime}</td>
          </tr>`;
        })
        .join("")
    : '<tr><td colspan="12">No defects found.</td></tr>';
}

function loadReport() {
  var machineId = getQueryParam("machineId");
  var body = document.getElementById("report-body");

  if (!machineId) {
    body.innerHTML =
      '<div class="empty-state">No machine ID was provided.</div>';
    return;
  }

  callBridge("getReport", machineId)
    .then(function (response) {
      if (!response.ok)
        throw new Error(response.error || "Unable to load report.");
      renderReport(response.machine, response.report);
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
    if (allowed) loadReport();
  });
});
