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
const settingsToggle = document.getElementById("settingsToggle");
const mainView = document.getElementById("mainView");
const settingsView = document.getElementById("settingsView");
const modelSelect = document.getElementById("modelSelect");
const modelHint = document.getElementById("modelHint");
const languageSelect = document.getElementById("languageSelect");
const outputDir = document.getElementById("outputDir");
const chooseDirButton = document.getElementById("chooseDirButton");
const resetDirButton = document.getElementById("resetDirButton");
const filePerSession = document.getElementById("filePerSession");
const punctuationCommands = document.getElementById("punctuationCommands");
const vocabulary = document.getElementById("vocabulary");
const settingsDone = document.getElementById("settingsDone");
const fileButton = document.getElementById("fileButton");
const card = document.querySelector(".card");

const MODEL_HINT_DEFAULT = "Ein Wechsel lädt das Modell neu, beim ersten Mal mit Download.";
let modelReady = false;
let isRecording = false;
let fileJobRunning = false;

// Genau die Zeilen, wie sie auch in die Datei geschrieben werden - Kopieren
// soll nicht von der Darstellung im DOM abhaengen.
let transcript = [];

window.addEventListener("pywebviewready", () => {
  startButton.addEventListener("click", () => pywebview.api.toggle_recording(deviceSelect.value));
  refreshButton.addEventListener("click", () => pywebview.api.refresh_devices(deviceSelect.value));
  versionLabel.addEventListener("click", () => pywebview.api.open_url(versionLabel.dataset.url));
  updateBadge.addEventListener("click", () => pywebview.api.open_url(updateBadge.dataset.url));
  folderButton.addEventListener("click", () => pywebview.api.open_output_folder());

  modelSelect.addEventListener("change", () => pywebview.api.update_setting("model_size", modelSelect.value));
  languageSelect.addEventListener("change", () => pywebview.api.update_setting("language", languageSelect.value));
  filePerSession.addEventListener("change", () => pywebview.api.update_setting("file_per_session", filePerSession.checked));
  punctuationCommands.addEventListener("change",
    () => pywebview.api.update_setting("punctuation_commands", punctuationCommands.checked));
  // "change" feuert bei einem Textfeld erst beim Verlassen - also nicht bei
  // jedem Tastendruck, aber spaetestens beim Klick auf "Fertig".
  vocabulary.addEventListener("change", () => pywebview.api.update_setting("vocabulary", vocabulary.value));
  chooseDirButton.addEventListener("click", () => pywebview.api.choose_output_dir());
  fileButton.addEventListener("click", () => pywebview.api.file_button());
  resetDirButton.addEventListener("click", () => pywebview.api.reset_output_dir());
});

function showSettings(open) {
  settingsView.hidden = !open;
  mainView.hidden = open;
  settingsToggle.classList.toggle("active", open);
  settingsToggle.setAttribute("aria-label", open ? "Einstellungen schließen" : "Einstellungen öffnen");
}

// Drag & Drop: hier nur Hervorheben und preventDefault (ohne das laesst der
// Browser gar nicht erst ablegen, sondern oeffnet die Datei selbst). Den
// eigentlichen Drop mit vollem Dateipfad bekommt Python (gui.py _on_drop).
// dragenter/dragleave feuern auch beim Wechsel zwischen Kindelementen -
// deshalb mitzaehlen statt bei jedem dragleave die Hervorhebung zu entfernen.
let dragDepth = 0;
function isFileDrag(e) {
  return e.dataTransfer && Array.from(e.dataTransfer.types || []).includes("Files");
}
document.addEventListener("dragenter", (e) => {
  if (!isFileDrag(e)) return;
  e.preventDefault();
  dragDepth++;
  card.classList.add("drag-over");
});
document.addEventListener("dragover", (e) => {
  if (!isFileDrag(e)) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = "copy";
});
document.addEventListener("dragleave", () => {
  dragDepth = Math.max(0, dragDepth - 1);
  if (dragDepth === 0) card.classList.remove("drag-over");
});
document.addEventListener("drop", (e) => {
  e.preventDefault();
  dragDepth = 0;
  card.classList.remove("drag-over");
  showSettings(false);
});

settingsToggle.addEventListener("click", () => showSettings(settingsView.hidden));
settingsDone.addEventListener("click", () => showSettings(false));
modelHint.textContent = MODEL_HINT_DEFAULT;

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

let modelFailed = false;

// Ein Ort fuer alle Sperren - Aufnahme, Modell laden und Audiodatei schliessen
// sich gegenseitig aus, und jede der set...-Funktionen unten aendert nur
// ihren Teil des Zustands.
function updateControls() {
  startButton.disabled = !modelReady || fileJobRunning;
  // Modellwechsel mitten in Aufnahme oder Datei wuerde die Erkennung fuer die
  // Dauer des Ladens anhalten - Sprache, Woerter und Satzzeichen dagegen
  // wirken sofort ab dem naechsten Haeppchen und bleiben frei. Nach einem
  // gescheiterten Laden (ohne Rueckfall) muss die Auswahl frei werden, sonst
  // gaebe es keinen Weg mehr, es erneut oder mit einem anderen zu versuchen.
  modelSelect.disabled = isRecording || fileJobRunning || (!modelReady && !modelFailed);
  // Waehrend eines Auftrags wird der Knopf zum Abbrechen-Knopf
  fileButton.disabled = !fileJobRunning && (!modelReady || isRecording);
  fileButton.textContent = fileJobRunning ? "Abbrechen" : "Audiodatei …";
  deviceSelect.disabled = isRecording;
  refreshButton.disabled = isRecording;
}

function setModelLoading() {
  modelReady = false;
  modelFailed = false;
  modelHint.textContent = "Modell wird geladen … beim ersten Mal mit Download, das kann einige Minuten dauern.";
  updateControls();
}

function setModelReady() {
  modelReady = true;
  modelFailed = false;
  modelHint.textContent = MODEL_HINT_DEFAULT;
  updateControls();
}

// Folgt ein Rueckfall auf ein anderes Modell, kommt gleich setModelLoading
// hinterher und sperrt die Auswahl wieder.
function setModelError(message) {
  modelReady = false;
  modelFailed = true;
  modelHint.textContent = message;
  updateControls();
}

function setFileJobState(running) {
  fileJobRunning = running;
  updateControls();
}

function setSettings(values) {
  modelSelect.value = values.model_size;
  languageSelect.value = values.language;
  filePerSession.checked = values.file_per_session;
  punctuationCommands.checked = values.punctuation_commands;
  // Nicht ueberschreiben, waehrend jemand darin tippt
  if (document.activeElement !== vocabulary) vocabulary.value = values.vocabulary.join("\n");
  outputDir.textContent = values.output_dir_display;
  outputDir.title = values.output_dir_display;
  resetDirButton.hidden = values.output_dir_is_default;
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

function setRecordingState(recording) {
  isRecording = recording;
  startButton.textContent = isRecording ? "Stop" : "Start";
  startButton.classList.toggle("recording", isRecording);
  updateControls();
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
