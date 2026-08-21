const startButton = document.getElementById("startButton");
const status = document.getElementById("status");
const levelFill = document.getElementById("levelFill");
const textOutput = document.getElementById("textOutput");
const placeholder = document.getElementById("placeholder");
const deviceSelect = document.getElementById("deviceSelect");
const refreshButton = document.getElementById("refreshButton");
const versionLabel = document.getElementById("versionLabel");
const updateBadge = document.getElementById("updateBadge");
const themeToggle = document.getElementById("themeToggle");

window.addEventListener("pywebviewready", () => {
  startButton.addEventListener("click", () => pywebview.api.toggle_recording(deviceSelect.value));
  refreshButton.addEventListener("click", () => pywebview.api.refresh_devices(deviceSelect.value));
  versionLabel.addEventListener("click", () => pywebview.api.open_url(versionLabel.dataset.url));
  updateBadge.addEventListener("click", () => pywebview.api.open_url(updateBadge.dataset.url));
});

// Unabhaengig von pywebviewready registriert (kein Python-Aufruf noetig) -
// das Umschalten selbst ist reines CSS/localStorage, die Klasse wurde vom
// blockierenden Inline-Script oben schon vor dem ersten Paint gesetzt.
const THEMES = ["light", "dark", "glass"];
const THEME_LABELS = {
  light: "Helles Design",
  dark: "Dunkles Design",
  glass: "Glass-Design (Indigo/Pink)",
};

function currentTheme() {
  if (document.body.classList.contains("dark")) return "dark";
  if (document.body.classList.contains("glass")) return "glass";
  return "light";
}

updateThemeToggleLabel();
themeToggle.addEventListener("click", () => {
  const next = THEMES[(THEMES.indexOf(currentTheme()) + 1) % THEMES.length];
  document.body.classList.remove("dark", "glass");
  if (next !== "light") document.body.classList.add(next);
  localStorage.setItem("theme", next);
  updateThemeToggleLabel();
});

function updateThemeToggleLabel() {
  const current = currentTheme();
  const next = THEMES[(THEMES.indexOf(current) + 1) % THEMES.length];
  themeToggle.setAttribute("aria-label", `Zu "${THEME_LABELS[next]}" wechseln`);
  themeToggle.title = THEME_LABELS[current];
}

// Ab hier: Funktionen, die Python per evaluate_js() aufruft.

function setStatus(text) {
  status.textContent = text;
}

function setModelReady() {
  startButton.disabled = false;
}

function setLevel(fraction) {
  levelFill.style.width = Math.max(0, Math.min(1, fraction)) * 100 + "%";
}

function appendText(text) {
  placeholder?.remove();
  const p = document.createElement("p");
  p.textContent = text;
  textOutput.appendChild(p);
  textOutput.scrollTop = textOutput.scrollHeight;
}

function setRecordingState(isRecording) {
  startButton.textContent = isRecording ? "Stop" : "Start";
  startButton.classList.toggle("recording", isRecording);
  deviceSelect.disabled = isRecording;
  refreshButton.disabled = isRecording;
}

function setDeviceList(labels, selected) {
  deviceSelect.innerHTML = "";
  for (const label of labels) {
    const option = document.createElement("option");
    option.value = label;
    option.textContent = label;
    if (label === selected) option.selected = true;
    deviceSelect.appendChild(option);
  }
}

function setVersion(version, releasesUrl) {
  versionLabel.textContent = "v" + version;
  versionLabel.dataset.url = releasesUrl;
}

function showUpdateBadge(version, releaseUrl) {
  updateBadge.textContent = "Update verfügbar: v" + version;
  updateBadge.dataset.url = releaseUrl;
  updateBadge.hidden = false;
}
