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
const copyButton = document.getElementById("copyButton");
const clearButton = document.getElementById("clearButton");
const folderButton = document.getElementById("folderButton");

// Genau die Zeilen, wie sie auch in die Datei geschrieben werden - Kopieren
// soll nicht von der Darstellung im DOM abhaengen.
let transcript = [];

window.addEventListener("pywebviewready", () => {
  startButton.addEventListener("click", () => pywebview.api.toggle_recording(deviceSelect.value));
  refreshButton.addEventListener("click", () => pywebview.api.refresh_devices(deviceSelect.value));
  versionLabel.addEventListener("click", () => pywebview.api.open_url(versionLabel.dataset.url));
  updateBadge.addEventListener("click", () => pywebview.api.open_url(updateBadge.dataset.url));
  folderButton.addEventListener("click", () => pywebview.api.open_output_folder());
});

copyButton.addEventListener("click", async () => {
  const text = transcript.join("\n");
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // WebKit2GTK erlaubt die Clipboard-API nicht in jedem Kontext - der
    // alte Weg ueber ein markiertes Textfeld klappt dort zuverlaessig.
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  flashButton(copyButton, "Kopiert ✓");
});

clearButton.addEventListener("click", () => {
  transcript = [];
  textOutput.innerHTML = "";
  textOutput.appendChild(placeholder);
  updateTextButtons();
});

function flashButton(button, label) {
  const original = button.dataset.label || button.textContent;
  button.dataset.label = original;
  button.textContent = label;
  clearTimeout(button._flashTimer);
  button._flashTimer = setTimeout(() => { button.textContent = original; }, 1500);
}

function updateTextButtons() {
  copyButton.disabled = transcript.length === 0;
  clearButton.disabled = transcript.length === 0;
}

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
  placeholder.remove();
  transcript.push(text);
  const p = document.createElement("p");
  p.textContent = text;
  textOutput.appendChild(p);
  textOutput.scrollTop = textOutput.scrollHeight;
  updateTextButtons();
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
