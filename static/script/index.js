var machines = [];
var activeFilter = "all";
var SESSION_KEY = "machineMonitoringSession";
var USER_KEY = "machineMonitoringUser";

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

function saveLogin(user, sessionId) {
  localStorage.setItem(SESSION_KEY, sessionId);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearLogin() {
  localStorage.removeItem(SESSION_KEY);
  localStorage.removeItem(USER_KEY);
}

function titleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function statusClass(status) {
  return "st-" + String(status || "stopped").toLowerCase();
}

function statusAccent(status) {
  if (status === "running") return "var(--green)";
  return "var(--brand)";
}

function updateCounts() {
  var counts = {
    all: machines.length,
    running: machines.filter((machine) => machine.status === "running").length,
    stopped: machines.filter((machine) => machine.status === "stopped").length,
  };

  document.querySelectorAll("[data-count]").forEach(function (el) {
    el.textContent = counts[el.dataset.count] || 0;
  });
}

function renderMachines(filter) {
  activeFilter = filter || activeFilter;
  var grid = document.getElementById("machine-grid");
  if (!grid) return;

  var list =
    activeFilter === "all"
      ? machines
      : machines.filter((machine) => machine.status === activeFilter);

  if (!list.length) {
    grid.innerHTML = '<div class="empty-state">No machines found.</div>';
    return;
  }

  grid.innerHTML = list
    .map(function (machine) {
      var status = machine.status || "stopped";
      return `<article class="machine-card" style="--mc-accent:${statusAccent(status)}">
        <button class="machine-image-button" type="button" onclick="openMachineDetails('${machine.id}')">
          <img class="machine-image" src="${machine.image}" alt="${machine.name}" />
          <span class="mc-status ${statusClass(status)}">${titleCase(status)}</span>
        </button>
        <div class="mc-content">
          <div>
            <div class="mc-label">Machine No</div>
            <div class="mc-name">${machine.no  }</div>
          </div>
     
        </div>
      </article>`;
    })
    .join("");
}

function filterMachines(filter, btn) {
  document.querySelectorAll(".filter-pill").forEach(function (pill) {
    pill.classList.remove("active");
  });
  if (btn) btn.classList.add("active");
  renderMachines(filter);
}

function openMachineDetails(machineId) {
  window.location.href = "machine-details.html?machineId=" + encodeURIComponent(machineId);
}

function loadMachines() {
  var grid = document.getElementById("machine-grid");
  if (grid) grid.innerHTML = '<div class="empty-state">Loading machines...</div>';

  callBridge("getMachines")
    .then(function (response) {
      if (!response.ok) throw new Error(response.error || "Unable to load machines.");
      machines = response.machines || [];
      updateCounts();
      renderMachines(activeFilter);
    })
    .catch(function (error) {
      if (grid) grid.innerHTML = `<div class="empty-state">${error.message}</div>`;
    });
}

function handleLogin() {
  var usernameEl = document.getElementById("username");
  var passEl = document.getElementById("password");
  var usernameErr = document.getElementById("username-error");
  var passErr = document.getElementById("password-error");

  usernameErr.style.display = "none";
  passErr.style.display = "none";
  usernameEl.classList.remove("err");
  passEl.classList.remove("err");

  var usernameVal = usernameEl.value.trim();
  var passVal = passEl.value;

  if (!usernameVal) {
    usernameErr.style.display = "flex";
    usernameEl.classList.add("err");
    return;
  }
  if (!passVal) {
    passErr.style.display = "flex";
    passEl.classList.add("err");
    return;
  }

  var btn = document.getElementById("signin-btn");
  btn.classList.add("loading");
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Signing in...';

  callBridge("authenticate", usernameVal, passVal)
    .then(function (response) {
      if (!response.ok) throw new Error(response.error || "Login failed.");

      saveLogin(response.user, response.sessionId);
      showApp();
      loadMachines();
    })
    .catch(function (error) {
      btn.classList.remove("loading");
      btn.innerHTML = '<i class="fa-solid fa-arrow-right-to-bracket"></i> Sign In';
      passErr.textContent = error.message;
      passErr.style.display = "flex";
      usernameEl.classList.add("err");
      passEl.classList.add("err");
    });
}

function showApp() {
  setUserShell();
  document.getElementById("login-page").style.display = "none";
  document.getElementById("app").style.display = "flex";
}

function handleLogout() {
  clearLogin();
  bridgeReady().then(function (bridge) {
    if (bridge && bridge.clearLoginSession) bridge.clearLoginSession();
  });

  var loginPage = document.getElementById("login-page");
  if (!loginPage) {
    window.location.href = "index.html";
    return;
  }

  document.getElementById("username").value = "";
  document.getElementById("password").value = "";
  var btn = document.getElementById("signin-btn");
  btn.classList.remove("loading");
  btn.innerHTML = '<i class="fa-solid fa-arrow-right-to-bracket"></i> Sign In';
  document.getElementById("app").style.display = "none";
  loginPage.style.display = "flex";
}

function initDashboard() {
  bridgeReady().then(function (bridge) {
    if (!bridge) {
      if (localStorage.getItem(SESSION_KEY)) {
        showApp();
        loadMachines();
      }
      return;
    }

    bridge.getSessionId(function (sessionId) {
      if (localStorage.getItem(SESSION_KEY) === sessionId) {
        showApp();
        loadMachines();
      } else {
        clearLogin();
      }
    });
  });
}

var passEl = document.getElementById("password");
var usernameInputEl = document.getElementById("username");
if (passEl) {
  passEl.addEventListener("keydown", function (event) {
    if (event.key === "Enter") handleLogin();
  });
}
if (usernameInputEl) {
  usernameInputEl.addEventListener("keydown", function (event) {
    if (event.key === "Enter") document.getElementById("password").focus();
  });
}

document.addEventListener("DOMContentLoaded", initDashboard);
