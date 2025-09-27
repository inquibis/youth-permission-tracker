// ---------------------------------------------------
// API wrapper for Youth Permission Tracker website
// ---------------------------------------------------

const ENV = window.ENV || "prod";   // "test" or "prod"
const API_BASE = window.API_BASE || "http://localhost:8000"; // backend base URL

// --- Toast-style notification helper ---
function showToast(message, type = "error") {
  // Create container if not exists
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.style.position = "fixed";
    container.style.top = "1rem";
    container.style.right = "1rem";
    container.style.zIndex = "9999";
    document.body.appendChild(container);
  }

  // Create toast
  const toast = document.createElement("div");
  toast.textContent = message;
  toast.style.padding = "10px 15px";
  toast.style.marginBottom = "10px";
  toast.style.borderRadius = "6px";
  toast.style.color = "#fff";
  toast.style.boxShadow = "0 2px 6px rgba(0,0,0,0.2)";
  toast.style.fontFamily = "sans-serif";
  toast.style.fontSize = "14px";
  toast.style.opacity = "0.95";
  toast.style.transition = "opacity 0.5s ease";

  if (type === "error") {
    toast.style.background = "#e74c3c";
  } else if (type === "success") {
    toast.style.background = "#2ecc71";
  } else {
    toast.style.background = "#3498db";
  }

  container.appendChild(toast);

  // Auto-remove after 4s
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => container.removeChild(toast), 500);
  }, 4000);
}

// --- Core fetch wrapper ---
async function fetchData(endpoint, fallbackJson, options = {}) {
  try {
    if (ENV === "test") {
      if (!fallbackJson) {
        throw new Error(`No fallback JSON defined for ${endpoint}`);
      }
      return fetch(`test_data/${fallbackJson}`).then(r => r.json());
    } else {
      const res = await fetch(`${API_BASE}${endpoint}`, options);
      if (!res.ok) {
        const msg = `API error ${res.status}: ${res.statusText}`;
        showToast(msg, "error");
        throw new Error(msg);
      }
      return res.json();
    }
  } catch (err) {
    showToast(err.message || "Unexpected error", "error");
    console.error(err);
    throw err; // rethrow if caller wants to handle
  }
}

// ---------------- USERS ----------------
export function login(username, password) {
  if (ENV === "test") {
    return fetchData("", "login_fallback.json");
  }
  return fetchData("/login", "", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password })
  });
}

export function getUsers() {
  return fetchData("/users", "user-examples.json");
}

export function getUserActivities(userId) {
  return fetchData(`/selectedactivities/user/${userId}`, "user_activities.json");
}

export function getGroupActivities(groupName) {
  return fetchData(`/selectedactivities/group/${groupName}`, "group_activities.json");
}

// ---------------- ACTIVITIES ----------------
export function getAllActivities() {
  return fetchData("/activity-all", "example-activity-list.json");
}

export function getActivityInformation(activityName) {
  return fetchData(
    `/activity-information?activity_name=${encodeURIComponent(activityName)}`,
    "local-activities.json"
  );
}

export function getActivityReview(activityId) {
  return fetchData(`/activity-review?activity_id=${activityId}`, "example-activity-list.json");
}

// ---------------- PERMISSIONS ----------------
export function getActivityPermissions(activityId) {
  return fetchData(`/activity-permissions?activity_id=${activityId}`, "parental-activity-examples.json");
}

// ---------------- NEEDS ----------------
export function getNeeds(groupName) {
  return fetchData(`/identified-needs/${groupName}`, "needs.json");
}


