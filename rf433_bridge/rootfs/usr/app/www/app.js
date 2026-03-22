let DEVICE_TYPES = [];

let DEVICE_SORT = {
  column: "name",
  direction: 1  // 1 = ascending, -1 = descending
};

function sortDevices(column) {
  if (DEVICE_SORT.column === column) {
    DEVICE_SORT.direction *= -1;
  } else {
    DEVICE_SORT.column = column;
    DEVICE_SORT.direction = 1;
  }

  loadDevices().then(updateSortArrows);
}

function updateSortArrows() {
  const headers = document.querySelectorAll("th.sortable");

  headers.forEach(th => {
    const col = th.getAttribute("onclick").match(/'(.*?)'/)[1];
    const arrow = th.querySelector(".arrow");

    if (col === DEVICE_SORT.column) {
      arrow.classList.remove("hidden");
      arrow.textContent = DEVICE_SORT.direction === 1 ? "▲" : "▼";
    } else {
      arrow.classList.add("hidden");
    }
  });
}

function showToast(message, duration = 3000) {
  const container = document.getElementById("toast-container");

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;

  container.appendChild(toast);

  // Trigger fade-in
  requestAnimationFrame(() => {
    toast.classList.add("show");
  });

  // Auto-remove after duration
  const autoRemove = setTimeout(() => {
    hideToast(toast);
  }, duration);

  // Remove immediately if clicked
  toast.addEventListener("click", () => {
    clearTimeout(autoRemove);
    hideToast(toast);
  });
}

function hideToast(toast) {
  toast.classList.remove("show");
  setTimeout(() => toast.remove(), 400);
}

function showSerialOfflinePopup() {
    document.getElementById("serial-offline").classList.remove("hidden");
}

function hideSerialOfflinePopup() {
    document.getElementById("serial-offline").classList.add("hidden");
}

function typeName(id) {
  let t = DEVICE_TYPES.find(x => x.id === id);
  return t ? t.name : id;  // fallback to id if unknown
}

function formatLastSeen(timestamp) {
  if (!timestamp) return "Never";

  const now = Date.now() / 1000; // seconds
  const diff = now - timestamp;

  if (diff < 5) {
    return "Just now";
  }

  if (diff < 86400) { // 24 hours
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = Math.floor(diff % 60);

    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
  }

  const days = Math.floor(diff / 86400);
  return `${days} Day${days === 1 ? "" : "s"}`;
}

function updateLastSeenCells() {
  const rows = document.querySelectorAll("tr[data-timestamp]");

  rows.forEach(row => {
    const ts = parseFloat(row.dataset.timestamp);
    const cell = row.querySelector(".last-seen");
    if (cell) {
      cell.textContent = formatLastSeen(ts);
    }
  });
}

async function loadDevices() {
  let base = window.location.pathname;
  let res = await fetch(base + "api/devices");
  let data = await res.json();

  let tbody = document.getElementById("devices");
  tbody.innerHTML = "";

  // Convert dict → array and sort by friendly name
  const sorted = Object.entries(data).sort((a, b) => {
    const [codeA, devA] = a;
    const [codeB, devB] = b;

    let valA, valB;

    switch (DEVICE_SORT.column) {
      case "code":
        valA = codeA;
        valB = codeB;
        break;

      case "lastSeen":
        valA = devA.timestamp || 0;
        valB = devB.timestamp || 0;
        break;

      case "name":
      default:
        valA = `${devA.name} ${typeName(devA.type)}`.toLowerCase();
        valB = `${devB.name} ${typeName(devB.type)}`.toLowerCase();
        break;
    }

    if (valA < valB) return -1 * DEVICE_SORT.direction;
    if (valA > valB) return 1 * DEVICE_SORT.direction;
    return 0;
  });

  // Render sorted rows
  for (const [code, d] of sorted) {
    let tr = document.createElement("tr");
    tr.dataset.code = code;   // <-- highlight target
	tr.dataset.timestamp = d.timestamp || 0;
	
    let tdName = document.createElement("td");
    tdName.textContent = `${d.name} ${typeName(d.type)}`;
    tr.appendChild(tdName);

    let tdCode = document.createElement("td");
    tdCode.textContent = code;
    tr.appendChild(tdCode);

	let tdLastSeen = document.createElement("td");
	tdLastSeen.classList.add("last-seen");
	tdLastSeen.textContent = formatLastSeen(d.timestamp);
	tr.appendChild(tdLastSeen);

    let tdActions = document.createElement("td");
    tdActions.innerHTML = `
      <button class="tx-btn disable-when-offline" onclick="addFromDevices('${code}','${d.type}','${d.name}')">Edit</button>
      <button class="tx-btn secondary disable-when-offline" onclick="removeDevice('${code}')">Remove</button>
    `;
    tr.appendChild(tdActions);

    tbody.appendChild(tr);
  }
}

async function loadTypes() {
  let base = window.location.pathname;
  let res = await fetch(base + "api/types");
  DEVICE_TYPES = await res.json();

  let list = document.getElementById("edit-type");
  list.innerHTML = "";

  DEVICE_TYPES.forEach(t => {
    list.innerHTML += `<option value="${t.id}">${t.name}</option>`;
  });
  document.getElementById("edit-type").value = "";
}

async function resetEditor() {
  document.getElementById("edit-code").value = "";
  document.getElementById("edit-type").value = "";
  document.getElementById("edit-name").value = "";
}

async function resetTX() {
  document.getElementById("tx-code").value = "";
}

async function addFromDevices(code,type,name) {
  document.getElementById("edit-code").value = code;
  document.getElementById("edit-type").value = type;
  document.getElementById("edit-name").value = name;
  removeDevice(code);
}

async function addFromLiveFeed(code) {
  resetEditor();
  document.getElementById("edit-code").value = code;
}

async function testDevice() {
  let code = document.getElementById("edit-code").value;
  let type = document.getElementById("edit-type").value;
  let name = document.getElementById("edit-name").value;
  
  if (!code) {
    showToast("Please enter an RF code first.");
    return;
  } else {
    let parts = code.split(":");
	if (parts.length !== 3 || !parts.every(p => /^\d+$/.test(p))) {
	  showToast("Invalid RF code entered.");
      return;
	}
  }
  
  if (!type) {
    showToast("Please select a device type.");
    return;
  }
  
  if (!name) {
    showToast("Please enter a name.");
    return;
  }

  let payload = {
    code: code,
    type: type,
    name: name
  };

  let base = window.location.pathname;
  await fetch(base + "api/test_device", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
}

async function addDevice() {
  let code = document.getElementById("edit-code").value;
  let type = document.getElementById("edit-type").value;
  let name = document.getElementById("edit-name").value;
  
  if (!code) {
    showToast("Please enter an RF code first.");
    return;
  } else {
    let parts = code.split(":");
	if (parts.length !== 3 || !parts.every(p => /^\d+$/.test(p))) {
	  showToast("Invalid RF code entered.");
      return;
	}
  }
  
  if (!type) {
    showToast("Please select a device type.");
    return;
  }
  
  if (!name) {
    showToast("Please enter a name.");
    return;
  }

  let payload = {
    code: code,
    type: type,
    name: name
  };

  let base = window.location.pathname;
  await fetch(base + "api/add_device", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  loadDevices();
  resetEditor();
}

async function removeDevice(code) {
  let base = window.location.pathname;
  await fetch(base + "api/remove_device", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({code: code})
  });

  loadDevices();
}

async function sendTx() {
  let code = document.getElementById("tx-code").value;
  
  if (!code) {
    showToast("Please enter an RF code first.");
    return;
  } else {
    let parts = code.split(":");
	if (parts.length !== 3 || !parts.every(p => /^\d+$/.test(p))) {
	  showToast("Invalid RF code entered.");
      return;
	}
  }
  
  let payload = {
    code: code
  };

  let base = window.location.pathname;
  await fetch(base + "api/send", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  
  showToast("RF Code Trasmitted.");
}

function highlightDevice(code) {
	if (DEVICE_SORT.column === "lastSeen") {
        loadDevices().then(() => {
            // Wait for DOM to update
            requestAnimationFrame(() => {
                const el = document.querySelector(`[data-code="${code}"]`);
                if (!el) return;

                // Update timestamp in DOM
                el.dataset.timestamp = Math.floor(Date.now() / 1000);

                // Apply highlight
                el.classList.add("active");
                setTimeout(() => el.classList.remove("active"), 1000);
            });
        });
        return;
    }
	
    const el = document.querySelector(`[data-code="${code}"]`);
    if (!el) return;

	// Update timestamp in the DOM
    el.dataset.timestamp = Math.floor(Date.now() / 1000);
    el.classList.add("active");
	
    setTimeout(() => {
        el.classList.remove("active");
    }, 1000);
}

async function pollEvents() {
  try {
    let base = window.location.pathname;
    let res = await fetch(base + "api/events");
    let data = await res.json();

	const offline = !data.serial_ready;

    // Disable all elements with the class
    document.querySelectorAll(".disable-when-offline").forEach(el => {
        el.disabled = offline;
    });

    if (offline) {
        showSerialOfflinePopup();
    } else {
        hideSerialOfflinePopup();
    }
	  
    let list = document.getElementById("rf-list");
    list.innerHTML = "";

    // Convert dict → array → sort by timestamp DESC
    let sorted = Object.entries(data.events)
      .sort((a, b) => b[1].timestamp - a[1].timestamp);

    sorted.forEach(([code, ev]) => {
      let li = document.createElement("li");
      li.innerHTML = `${code} <button class="disable-when-offline" onclick="addFromLiveFeed('${code}')">Add</button>`;
      list.appendChild(li);
    });
	
    res = await fetch(base + "api/latest_event");
    last_event = await res.json();

    if (last_event && last_event.code && last_event.timestamp) {
		highlightDevice(last_event.code)
		await fetch(base + "api/ack_event", { method: "POST" });
	}	
  } catch (err) {
    console.error("Error polling events:", err);
  }
}

/* ---------------------------------------------------------
   CLEAR EVENTS
--------------------------------------------------------- */

async function clearRecentCodes() {
  try {
    let base = window.location.pathname;
    await fetch(base + "api/clear_events", {
      method: "POST"
    });

    // Clear monitor
    document.getElementById("rf-list").innerHTML = "";

  } catch (err) {
    console.error("Error clearing codes:", err);
  }
}

/* ---------------------------------------------------------
   INITIAL LOAD + EVENT POLLING
--------------------------------------------------------- */

loadTypes();
loadDevices().then(updateSortArrows);
pollEvents()
setInterval(pollEvents, 500);
setInterval(updateLastSeenCells, 1000);