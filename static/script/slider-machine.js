var SESSION_KEY = "machineMonitoringSession";
var USER_KEY = "machineMonitoringUser";
var allSliderMachines = [];
var sliderMachines = [];
var activeSlide = 0;
var autoSlideTimer = null;
var activeSliderFilter = "all";

function parseJson(raw, fallback) {
  try {
    return JSON.parse(raw);
  } catch (error) {
    return fallback || {};
  }
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

function titleCase(value) {
  value = String(value || "stopped");
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function stat(report, key) {
  return report.stats && report.stats[key] !== undefined
    ? report.stats[key]
    : 0;
}

function row(label, value) {
  return `<div class="detail-row"><span>${label}</span><strong>${safeValue(value)}</strong></div>`;
}

function renderKeyValueRows(data) {
  return Object.keys(data)
    .map(function (key) {
      return row(key, data[key]);
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

function toNumber(value) {
  var number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function getMachineStatus(item) {
  return item && item.machine && item.machine.status === "running"
    ? "running"
    : "stopped";
}

function filteredSliderMachines(filter) {
  if (filter === "all") return allSliderMachines.slice();
  return allSliderMachines.filter(function (item) {
    return getMachineStatus(item) === filter;
  });
}

function normalizeSliderFilter(filter) {
  if (filter === "stoped") return "stopped";
  return filter || "all";
}

function updateSliderFilterCounts() {
  var counts = {
    all: allSliderMachines.length,
    running: allSliderMachines.filter(function (item) {
      return getMachineStatus(item) === "running";
    }).length,
    stopped: allSliderMachines.filter(function (item) {
      return getMachineStatus(item) === "stopped";
    }).length,
  };

  Object.keys(counts).forEach(function (key) {
    document
      .querySelectorAll('[data-slider-count="' + key + '"]')
      .forEach(function (node) {
        node.textContent = counts[key];
      });
  });
}

function setActiveFilterButton(filter, button) {
  document
    .querySelectorAll(".slider-filter-btn")
    .forEach(function (filterButton) {
      filterButton.classList.toggle(
        "active",
        filterButton === button ||
          filterButton.getAttribute("data-slider-filter") === filter,
      );
    });
}

function slideMarkup(item, index) {
  var machine = item.machine;
  var report = item.report;
  var statusClass = machine.status === "running" ? "running" : "stopped";
  var totalCops = toNumber(stat(report, "Total Cops"));
  var goodCops = toNumber(stat(report, "Total Good Cops"));
  var defectCount = toNumber(stat(report, "Defect Count"));
  var emptyCops = Math.max(totalCops - goodCops - defectCount, 0);

  return `<article class="machine-slide ${index === 0 ? "active" : ""}">
    <section class="machine-detail-overview">
      <div class="machine-detail-visual d-none"></div>
      <div class="machine-detail-intro">
    <div  class="machine_div_heading">
      <div class="mr-15">
        <div class="machine-detail-eyebrow">Machine Overview</div>
        <h1>${machine.name}</h1>
      </div>
        <div class="machine-detail-time-strip">
          <div class="machine-time-pill">
            <span> Start Time</span>
            <strong>${safeValue(report.startTime)}</strong>
          </div>
          <div class="machine-time-pill">
            <span>End Time</span>
            <strong>${safeValue(report.endTime)}</strong>
          </div>
        </div>
      </div>
        <div class="machine_div_side_align">
          <p   class="machine-detail-status machine_status ${statusClass}">${titleCase(machine.status)}</p>
          <p style="height: 65px"></p>
          <p style="font-size: 18px; font-weight: 600">${safeValue(report.material)}</p>
        </div>

        <div class="d-none">
          <div class="machine-detail-meta">
            <span class="machine-meta-pill"><i class="fa-solid fa-hashtag"></i>Machine No ${safeValue(report.machineNo)}</span>
            <span class="machine-meta-pill"><i class="fa-solid fa-calendar-day"></i>${safeValue(report.date)}</span>
            <span class="machine-meta-pill"><i class="fa-solid fa-clock"></i>Duration ${safeValue(report.duration)}</span>
          </div>
          <div class="machine-detail-kpis">
            <div class="detail-kpi"><i class="fa-solid fa-boxes-stacked"></i><span>Inspected</span><strong>${stat(report, "Total Cops")}</strong></div>
            <div class="detail-kpi good"><i class="fa-solid fa-check"></i><span>Good</span><strong>${stat(report, "Total Good Cops")}</strong></div>
            <div class="detail-kpi warning"><i class="fa-solid fa-xmark"></i><span>Defect</span><strong>${stat(report, "Defect Count")}</strong></div>
          </div>
        </div>
      </div>
    </section>

    <section class="detail-info-grid">
      <article class="detail-panel detail-panel-wide">
        <div class="detail-panel-head"><span><i class="fa-solid fa-chart-bar"></i></span><strong>Production Summary</strong></div>
        <div class="detail-metric-grid">${renderMetricCards({
          "Doff No": report.doffNo,
          "Full Cop": stat(report, "Total Full Cops"),
          "Half Cop": stat(report, "Total Half Cops"),
          "Quater Cop": stat(report, "Total Quarter Cops"),
          "Total Inspected": stat(report, "Total Cops"),
          Good: stat(report, "Total Good Cops"),
          Defect: stat(report, "Defect Count"),
          Empty: emptyCops,
        })}</div>
      </article>
      <article class="detail-panel d-none">
        <div class="detail-panel-head"><span><i class="fa-solid fa-file-lines"></i></span><strong>FR Information</strong></div>
        <div class="detail-row-list">${renderKeyValueRows({
          "Machine No": report.machineNo,
          Date: report.date,
          Material: report.material,
          Yarn: report.yarn,
          Count: report.count,
          Duration: report.duration,
        })}</div>
      </article>
    </section>
  </article>`;
}

function showSlide(index) {
  if (!sliderMachines.length) return;
  activeSlide = (index + sliderMachines.length) % sliderMachines.length;
  document
    .querySelectorAll(".machine-slide")
    .forEach(function (slide, slideIndex) {
      slide.classList.toggle("active", slideIndex === activeSlide);
    });
  document.querySelectorAll(".slider-dot").forEach(function (dot, dotIndex) {
    dot.classList.toggle("active", dotIndex === activeSlide);
  });
  var counter = document.getElementById("slider-counter");
  if (counter)
    counter.textContent =
      "Machine " + (activeSlide + 1) + " of " + sliderMachines.length;
  var activeItem = sliderMachines[activeSlide];
  var sliderPhoto = document.getElementById("slider-machine-photo");
  if (activeItem && sliderPhoto) {
    sliderPhoto.src =
      activeItem.machine.image || "../static/img/machine_image.jpeg";
  }
}

function nextSlide() {
  showSlide(activeSlide + 1);
}

function previousSlide() {
  showSlide(activeSlide - 1);
}

function renderSliderSlides(items) {
  var body = document.getElementById("slider-body");
  sliderMachines = items || [];
  activeSlide = 0;

  if (autoSlideTimer) {
    window.clearInterval(autoSlideTimer);
    autoSlideTimer = null;
  }

  if (!sliderMachines.length) {
    body.innerHTML =
      '<div class="empty-state">No machines found for this filter.</div>';
    return;
  }

  body.innerHTML = `<div class="machine-slider-shell">
    <div class="machine-slider-track">
      ${sliderMachines.map(slideMarkup).join("")}
    </div>
    <div class="slider-dots">
      <span class="slider-counter" id="slider-counter">Machine 1 of ${sliderMachines.length}</span>
      ${sliderMachines
        .map(function (_, index) {
          return `<button class="slider-dot ${index === 0 ? "active" : ""}" type="button" aria-label="Show machine ${index + 1}" onclick="showSlide(${index})"></button>`;
        })
        .join("")}
    </div>
  </div>`;

  showSlide(0);

  if (sliderMachines.length > 1) {
    autoSlideTimer = window.setInterval(nextSlide, 10000);
  }
}

function filterSliderMachines(filter, button) {
  activeSliderFilter = normalizeSliderFilter(filter);
  setActiveFilterButton(activeSliderFilter, button);
  renderSliderSlides(filteredSliderMachines(activeSliderFilter));
}

function renderSlider(items) {
  allSliderMachines = items || [];
  updateSliderFilterCounts();
  filterSliderMachines(activeSliderFilter);
}

function loadSliderMachines() {
  callBridge("getAllMachineDetails")
    .then(function (response) {
      if (!response.ok)
        throw new Error(response.error || "Unable to load machine slider.");
      renderSlider(response.machines || []);
    })
    .catch(function (error) {
      document.getElementById("slider-body").innerHTML =
        `<div class="empty-state">${error.message}</div>`;
    });
}

function handleLogout() {
  clearLogin();
  window.location.href = "index.html";
}

document.addEventListener("DOMContentLoaded", function () {
  requireLoginForPage().then(function (allowed) {
    if (allowed) loadSliderMachines();
  });
});
