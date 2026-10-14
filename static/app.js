// Transcriber front end. Plain JavaScript, no build step and no internet needed.
"use strict";

// ---------------------------------------------------------------- text ----

const TEXT = {
  en: {
    tagline: "Speech to text and summary · Malay, English, mixed",
    drop: "Drop audio or video files here",
    dropHint: "or click to choose · MP3, WAV, M4A, MP4, MKV, MOV, WEBM and more",
    language: "Language spoken",
    speed: "Speed",
    fast: "Fast",
    accurate: "Accurate",
    model: "Model",
    vocab: "Special words (optional)",
    vocabPlaceholder: "Names or terms to spell correctly, e.g. UMPSA, ROS 2, Encik Hafiz",
    start: "Transcribe",
    startMany: "Transcribe {n} files",
    privacy: "Runs on this computer. Your recordings never leave it.",
    cancel: "Cancel",
    transcript: "Transcript",
    summary: "Summary",
    search: "Search transcript",
    times: "Timestamps",
    follow: "Follow audio",
    copy: "Copy text",
    copied: "Copied!",
    editHint: "Click any line to fix a word. Exports include your edits.",
    quickTitle: "Key sentences",
    quickHint: "The most important sentences, picked instantly. Click a time to listen.",
    aiTitle: "AI summary",
    aiHint: "Written by a free AI model that runs on this computer. The first time, the model is downloaded once.",
    sameLang: "Language: auto",
    aiStart: "Write summary",
    aiAgain: "Write again",
    autoSummary: "AI summary",
    summaryOff: "Off (transcript only)",
    autoSummaryNote: "Written automatically after the transcript is ready.",
    autoSummaryOff: "You can still write one later from the Summary tab.",
    aiWaiting: "The summary is written when the transcript is ready.",
    download: "Download",
    txtTimes: "Text + times",
    srt: "Subtitles (.srt)",
    footer: "Powered by faster-whisper. Free and open source.",
    langs: { mixed: "Mixed (BM + EN)", ms: "Bahasa Melayu", en: "English", auto: "Auto" },
    downloaded: "downloaded",
    recommended: "recommended",
    gpu: "GPU (CUDA)",
    cpu: "CPU",
    waitingText: "Text will appear here as it is transcribed.",
    noSummary: "Not enough speech to summarise yet.",
    left: "left",
    took: "Took {t} for {d} of audio ({x}x real time)",
    detected: "Detected: {l}",
    noMatch: "No lines match your search.",
    stages: {},
  },
  ms: {
    tagline: "Pertuturan ke teks dan ringkasan · BM, English, campur",
    drop: "Letak fail audio atau video di sini",
    dropHint: "atau klik untuk pilih · MP3, WAV, M4A, MP4, MKV, MOV, WEBM dan lain-lain",
    language: "Bahasa yang dituturkan",
    speed: "Kelajuan",
    fast: "Pantas",
    accurate: "Tepat",
    model: "Model",
    vocab: "Perkataan khas (pilihan)",
    vocabPlaceholder: "Nama atau istilah untuk dieja dengan betul, cth. UMPSA, ROS 2, Encik Hafiz",
    start: "Transkrip",
    startMany: "Transkrip {n} fail",
    privacy: "Berjalan di komputer ini. Rakaman anda tidak dihantar ke mana-mana.",
    cancel: "Batal",
    transcript: "Transkrip",
    summary: "Ringkasan",
    search: "Cari dalam transkrip",
    times: "Masa",
    follow: "Ikut audio",
    copy: "Salin teks",
    copied: "Disalin!",
    editHint: "Klik mana-mana baris untuk betulkan perkataan. Muat turun akan ikut suntingan anda.",
    quickTitle: "Ayat penting",
    quickHint: "Ayat paling penting, dipilih serta-merta. Klik masa untuk dengar.",
    aiTitle: "Ringkasan AI",
    aiHint: "Ditulis oleh model AI percuma yang berjalan di komputer ini. Kali pertama, model dimuat turun sekali sahaja.",
    sameLang: "Bahasa: auto",
    aiStart: "Tulis ringkasan",
    aiAgain: "Tulis semula",
    autoSummary: "Ringkasan AI",
    summaryOff: "Tutup (transkrip sahaja)",
    autoSummaryNote: "Ditulis secara automatik selepas transkrip siap.",
    autoSummaryOff: "Anda masih boleh tulis kemudian di tab Ringkasan.",
    aiWaiting: "Ringkasan akan ditulis selepas transkrip siap.",
    download: "Muat turun",
    txtTimes: "Teks + masa",
    srt: "Sarikata (.srt)",
    footer: "Menggunakan faster-whisper. Percuma dan sumber terbuka.",
    langs: { mixed: "Campur (BM + EN)", ms: "Bahasa Melayu", en: "English", auto: "Auto" },
    downloaded: "sudah dimuat turun",
    recommended: "disyorkan",
    gpu: "GPU (CUDA)",
    cpu: "CPU",
    waitingText: "Teks akan muncul di sini semasa ditranskrip.",
    noSummary: "Belum cukup pertuturan untuk diringkaskan.",
    left: "lagi",
    took: "Mengambil {t} untuk {d} audio ({x}x masa sebenar)",
    detected: "Dikesan: {l}",
    noMatch: "Tiada baris yang sepadan.",
    modelNotes: {
      tiny: "Paling pantas. Ketepatan kasar, sesuai untuk semakan cepat.",
      base: "Sangat pantas. OK untuk English yang jelas.",
      small: "Pilihan terbaik untuk CPU laptop.",
      medium: "BM lebih baik. Perlahan pada CPU.",
      "large-v3-turbo": "Hampir setepat large-v3 tetapi ~6x lebih laju. Terbaik dengan GPU.",
      "large-v3": "Model umum paling tepat. Paling perlahan.",
      "malaysian-turbo": "Turbo yang dilatih dengan pertuturan Malaysia (BM, Manglish). Terbaik untuk loghat tempatan.",
    },
    stages: {
      "Waiting in queue": "Menunggu giliran",
      "Reading audio": "Membaca audio",
      "Loading model (the first time it downloads, please wait)":
        "Memuatkan model (kali pertama ia dimuat turun, sila tunggu)",
      "Transcribing": "Sedang transkrip",
      "Done": "Siap",
      "Failed": "Gagal",
      "Cancelled": "Dibatalkan",
      "Starting": "Bermula",
      "Writing summary": "Menulis ringkasan",
      "Loading summary model": "Memuatkan model ringkasan",
    },
  },
};

let uiLang = localStorage.getItem("uiLang") || (navigator.language.startsWith("ms") ? "ms" : "en");
const t = (key) => TEXT[uiLang][key] ?? TEXT.en[key] ?? key;
const fill = (s, values) => s.replace(/\{(\w+)\}/g, (_, k) => values[k]);
function stageText(s) {
  if (!s) return "";
  if (uiLang !== "ms") return s;
  if (TEXT.ms.stages[s]) return TEXT.ms.stages[s];
  return s
    .replace(/^Reading part (\d+) of (\d+)$/, "Membaca bahagian $1 daripada $2")
    .replace(/^Downloading summary model \((.+), first time only\)$/, "Memuat turun model ringkasan ($1, kali pertama sahaja)")
    .replace(/^Summary failed: /, "Ringkasan gagal: ");
}

// --------------------------------------------------------------- state ----

const $ = (sel) => document.querySelector(sel);
const state = {
  config: null,
  files: [],
  language: localStorage.getItem("language") || "mixed",
  quality: localStorage.getItem("quality") || "fast",
  jobs: [], // { id, file, url, data, segments: [] }
  activeId: null,
};

function activeJob() {
  return state.jobs.find((j) => j.id === state.activeId);
}

// ------------------------------------------------------------- helpers ----

function clock(seconds) {
  const s = Math.floor(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

function duration(seconds) {
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function highlight(text, query) {
  const safe = escapeHtml(text);
  if (!query) return safe;
  const pattern = new RegExp(escapeHtml(query).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
  return safe.replace(pattern, (m) => `<mark>${m}</mark>`);
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || `Request failed (${res.status})`);
  return body;
}

// ---------------------------------------------------------- language UI ----

function applyLanguage() {
  document.documentElement.lang = uiLang;
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => (el.placeholder = t(el.dataset.i18nPlaceholder)));
  document.querySelectorAll("[data-ui-lang]").forEach((b) => b.classList.toggle("active", b.dataset.uiLang === uiLang));
  if (state.config) {
    renderLanguageButtons();
    renderModels();
    renderSummaryModels();
    $("#device").textContent = state.config.device === "cuda" ? t("gpu") : t("cpu");
  }
  updateStartButton();
  renderActive(true);
}

document.querySelectorAll("[data-ui-lang]").forEach((b) =>
  b.addEventListener("click", () => {
    uiLang = b.dataset.uiLang;
    localStorage.setItem("uiLang", uiLang);
    applyLanguage();
  })
);

// -------------------------------------------------------------- options ----

function renderLanguageButtons() {
  const box = $("#language");
  box.innerHTML = "";
  for (const code of Object.keys(state.config.languages)) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = t("langs")[code];
    b.classList.toggle("active", code === state.language);
    b.addEventListener("click", () => {
      state.language = code;
      localStorage.setItem("language", code);
      renderLanguageButtons();
    });
    box.append(b);
  }
}

function recommendedModel() {
  return state.config.device === "cuda" ? "large-v3-turbo" : "small";
}

function renderModels() {
  const select = $("#model");
  const current = select.value || localStorage.getItem("model") || recommendedModel();
  select.innerHTML = "";
  for (const m of state.config.models) {
    const tags = [m.size];
    if (state.config.downloaded.includes(m.id)) tags.push("✓ " + t("downloaded"));
    if (m.id === recommendedModel()) tags.push("★ " + t("recommended"));
    const option = new Option(`${m.label}  ·  ${tags.join("  ·  ")}`, m.id);
    select.append(option);
  }
  select.value = state.config.models.some((m) => m.id === current) ? current : recommendedModel();
  showModelNote();
}

function renderSummaryModels() {
  const models = state.config.summary_models;
  const label = (m) => [m.label, m.size, m.downloaded ? "✓ " + t("downloaded") : ""].filter(Boolean).join("  ·  ");

  const auto = $("#auto-summary");
  const autoValue = auto.value || localStorage.getItem("autoSummary") || models[0]?.id || "";
  auto.innerHTML = "";
  auto.append(new Option(t("summaryOff"), ""));
  for (const m of models) auto.append(new Option(label(m), m.id));
  auto.value = autoValue === "" || models.some((m) => m.id === autoValue) ? autoValue : models[0]?.id || "";
  $("#auto-summary-note").textContent = auto.value ? t("autoSummaryNote") : t("autoSummaryOff");

  const manual = $("#ai-model");
  const manualValue = manual.value || auto.value || models[0]?.id;
  manual.innerHTML = "";
  for (const m of models) manual.append(new Option(label(m), m.id));
  if (models.some((m) => m.id === manualValue)) manual.value = manualValue;
}

$("#auto-summary").addEventListener("change", () => {
  localStorage.setItem("autoSummary", $("#auto-summary").value);
  renderSummaryModels();
});

function showModelNote() {
  const m = state.config.models.find((x) => x.id === $("#model").value);
  $("#model-note").textContent = m ? TEXT[uiLang].modelNotes?.[m.id] || m.note : "";
}

$("#model").addEventListener("change", () => {
  localStorage.setItem("model", $("#model").value);
  showModelNote();
});

document.querySelectorAll("#quality button").forEach((b) =>
  b.addEventListener("click", () => {
    state.quality = b.dataset.value;
    localStorage.setItem("quality", state.quality);
    renderQuality();
  })
);

function renderQuality() {
  document.querySelectorAll("#quality button").forEach((b) => b.classList.toggle("active", b.dataset.value === state.quality));
}

// ------------------------------------------------------------ file pick ----

function setFiles(fileList) {
  state.files = [...fileList];
  $("#picked").textContent = state.files.map((f) => f.name).join(", ");
  updateStartButton();
}

function updateStartButton() {
  const n = state.files.length;
  $("#start").disabled = n === 0 || !state.config;
  $("#start").textContent = n > 1 ? fill(t("startMany"), { n }) : t("start");
}

$("#file-input").addEventListener("change", (e) => setFiles(e.target.files));

const dropzone = $("#dropzone");
["dragenter", "dragover"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.add("over");
  })
);
["dragleave", "drop"].forEach((ev) => dropzone.addEventListener(ev, () => dropzone.classList.remove("over")));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  if (e.dataTransfer.files.length) setFiles(e.dataTransfer.files);
});

// ---------------------------------------------------------------- start ----

$("#start").addEventListener("click", async () => {
  const files = state.files;
  if (!files.length) return;
  $("#setup-error").hidden = true;
  $("#start").disabled = true;

  for (const file of files) {
    const form = new FormData();
    form.append("file", file);
    form.append("model", $("#model").value);
    form.append("language", state.language);
    form.append("quality", state.quality);
    form.append("vocabulary", $("#vocabulary").value);
    form.append("summary_model", $("#auto-summary").value);
    try {
      const { id } = await api("/api/jobs", { method: "POST", body: form });
      state.jobs.push({ id, file, url: URL.createObjectURL(file), data: null, segments: [] });
      if (!state.activeId || activeJob()?.data?.status === "done") selectJob(id);
      renderJobList();
    } catch (err) {
      $("#setup-error").textContent = `${file.name}: ${err.message}`;
      $("#setup-error").hidden = false;
    }
  }
  setFiles([]);
  $("#file-input").value = "";
  poll();
});

// -------------------------------------------------------------- polling ----

let pollTimer = null;

async function poll() {
  clearTimeout(pollTimer);
  const pending = state.jobs.filter(
    (j) => !j.data || ["queued", "working"].includes(j.data.status) || j.data.ai_status === "working"
  );
  for (const job of pending) {
    try {
      const data = await api(`/api/jobs/${job.id}?since=${job.segments.length}`);
      const newSegments = data.segments.slice(job.segments.length - data.since);
      job.segments.push(...newSegments);
      job.data = data;
      if (job.id === state.activeId) renderActive(false, newSegments);
    } catch (err) {
      job.data = { ...(job.data || {}), status: "error", error: err.message, segments: [] };
      if (job.id === state.activeId) renderActive(true);
    }
  }
  renderJobList();
  const stillRunning = state.jobs.some(
    (j) => !j.data || ["queued", "working"].includes(j.data.status) || j.data.ai_status === "working"
  );
  if (stillRunning) pollTimer = setTimeout(poll, 1000);
}

// ------------------------------------------------------------- job list ----

function renderJobList() {
  const nav = $("#job-list");
  nav.hidden = state.jobs.length < 2;
  nav.innerHTML = "";
  for (const job of state.jobs) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "job-chip" + (job.id === state.activeId ? " active" : "");
    chip.innerHTML = `<span class="dot ${job.data?.status || "queued"}"></span><span class="name"></span>`;
    chip.querySelector(".name").textContent = job.file.name;
    chip.addEventListener("click", () => selectJob(job.id));
    nav.append(chip);
  }
}

function selectJob(id) {
  state.activeId = id;
  const job = activeJob();
  const isVideo = job.file.type.startsWith("video/") || /\.(mp4|mkv|mov|webm|avi|3gp|mpeg)$/i.test(job.file.name);
  const media = document.createElement(isVideo ? "video" : "audio");
  media.controls = true;
  media.preload = "metadata";
  media.src = job.url;
  media.addEventListener("timeupdate", followPlayback);
  $("#player").replaceChildren(media);
  $("#search").value = "";
  $("#ai-output").innerHTML = "";
  renderActive(true);
  renderJobList();
  $("#result").hidden = false;
}

// --------------------------------------------------------------- render ----

function renderActive(full, newSegments = []) {
  const job = activeJob();
  if (!job) return;
  const d = job.data || { status: "queued", stage: "Waiting in queue", progress: 0 };
  const running = ["queued", "working"].includes(d.status);

  $("#result-title").textContent = job.file.name;
  $("#cancel").hidden = !running;

  // Progress and meta line.
  $("#progress-box").hidden = !running;
  const indeterminate = running && d.stage !== "Transcribing";
  $("#progress-box").classList.toggle("indeterminate", indeterminate);
  $("#progress-bar").style.width = `${Math.round((d.progress || 0) * 100)}%`;
  let percent = "";
  if (d.stage === "Transcribing" && d.progress > 0.02) {
    const remaining = (d.elapsed / d.progress) * (1 - d.progress);
    percent = `${Math.round(d.progress * 100)}% · ~${duration(remaining)} ${t("left")}`;
  }
  $("#stage").textContent = stageText(d.stage);
  $("#percent").textContent = percent;

  const meta = [];
  if (d.status === "done" && d.duration) {
    meta.push(fill(t("took"), { t: duration(d.elapsed), d: duration(d.duration), x: (d.duration / Math.max(d.elapsed, 0.1)).toFixed(1) }));
  }
  if (d.language) meta.push(fill(t("detected"), { l: d.language === "ms" ? "Bahasa Melayu" : d.language === "en" ? "English" : d.language }));
  $("#result-meta").textContent = meta.join(" · ");

  $("#job-error").hidden = !d.error;
  $("#job-error").textContent = d.error ? stageText(d.stage) + ": " + d.error : "";

  // Transcript.
  const done = d.status === "done";
  $("#edit-hint").hidden = !done;
  if (full) renderSegments(job.segments, true);
  else if (newSegments.length || done) renderSegments(newSegments, false);
  if (done) document.querySelectorAll("#segments .text").forEach((el) => (el.contentEditable = "true"));

  $(".downloads").classList.toggle("disabled", !done);
  document.querySelectorAll(".downloads .btn").forEach((a) => {
    a.href = done ? `/api/jobs/${job.id}/export/${a.dataset.format}` : "#";
  });

  renderSummary(job);
}

function renderSegments(segments, replace) {
  const box = $("#segments");
  const job = activeJob();
  if (replace) box.innerHTML = "";
  box.querySelector(".empty")?.remove();
  const start = replace ? 0 : job.segments.length - segments.length;
  const query = $("#search").value.trim();

  segments.forEach((seg, k) => {
    const index = start + k;
    const row = document.createElement("div");
    row.className = "segment";
    row.dataset.index = index;
    row.innerHTML = `<button type="button" class="time">${clock(seg.start)}</button><div class="text" spellcheck="false"></div>`;
    row.querySelector(".time").addEventListener("click", () => seek(seg.start));
    const text = row.querySelector(".text");
    text.innerHTML = highlight(seg.text, query);
    text.addEventListener("focus", () => (text.textContent = job.segments[index].text));
    text.addEventListener("blur", () => saveEdit(index, text));
    text.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        text.blur();
      }
    });
    if (query && !seg.text.toLowerCase().includes(query.toLowerCase())) row.classList.add("hidden");
    box.append(row);
  });

  if (!job.segments.length) box.innerHTML = `<p class="empty">${escapeHtml(t("waitingText"))}</p>`;
  else if ($("#follow").checked && !replace && segments.length && !query) box.scrollTop = box.scrollHeight;
}

async function saveEdit(index, el) {
  const job = activeJob();
  const text = el.textContent.trim();
  const query = $("#search").value.trim();
  if (text === job.segments[index].text) {
    el.innerHTML = highlight(text, query);
    return;
  }
  job.segments[index].text = text;
  el.innerHTML = highlight(text, query);
  try {
    const res = await api(`/api/jobs/${job.id}/segments`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texts: { [index]: text } }),
    });
    job.data.quick_summary = res.quick_summary;
    renderSummary(job);
  } catch (err) {
    $("#job-error").textContent = err.message;
    $("#job-error").hidden = false;
  }
}

// ----------------------------------------------------- playback / search ----

function seek(seconds) {
  const media = $("#player audio, #player video");
  if (!media) return;
  media.currentTime = seconds;
  media.play();
}

let lastCurrent = null;
function followPlayback(e) {
  const job = activeJob();
  if (!job) return;
  const time = e.target.currentTime;
  // Last segment that started before the current time (segments are in order).
  let lo = 0, hi = job.segments.length - 1, found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (job.segments[mid].start <= time) { found = mid; lo = mid + 1; } else hi = mid - 1;
  }
  const row = found >= 0 ? $(`#segments .segment[data-index="${found}"]`) : null;
  if (row === lastCurrent) return;
  lastCurrent?.classList.remove("current");
  row?.classList.add("current");
  lastCurrent = row;
  const editing = document.activeElement?.classList.contains("text");
  if (row && $("#follow").checked && !editing && !e.target.paused) {
    row.scrollIntoView({ block: "center", behavior: "smooth" });
  }
}

$("#search").addEventListener("input", () => {
  const job = activeJob();
  if (!job) return;
  renderSegments(job.segments, true);
  if (job.data?.status === "done") document.querySelectorAll("#segments .text").forEach((el) => (el.contentEditable = "true"));
  const visible = document.querySelectorAll("#segments .segment:not(.hidden)").length;
  if (job.segments.length && !visible) $("#segments").insertAdjacentHTML("beforeend", `<p class="empty">${escapeHtml(t("noMatch"))}</p>`);
});

$("#show-times").addEventListener("change", (e) => $("#segments").classList.toggle("no-times", !e.target.checked));

$("#copy").addEventListener("click", async () => {
  const job = activeJob();
  if (!job) return;
  const withTimes = $("#show-times").checked;
  const text = job.segments.map((s) => (withTimes ? `[${clock(s.start)}] ` : "") + s.text).join("\n");
  await navigator.clipboard.writeText(text);
  $("#copy").textContent = t("copied");
  setTimeout(() => ($("#copy").textContent = t("copy")), 1500);
});

$("#cancel").addEventListener("click", () => {
  const job = activeJob();
  if (job) api(`/api/jobs/${job.id}/cancel`, { method: "POST" }).catch(() => {});
});

document.querySelectorAll(".tabs button").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((x) => x.classList.toggle("active", x === b));
    $("#tab-transcript").hidden = b.dataset.tab !== "transcript";
    $("#tab-summary").hidden = b.dataset.tab !== "summary";
  })
);

// -------------------------------------------------------------- summary ----

function renderSummary(job) {
  const quick = job.data?.quick_summary;
  const keywords = $("#keywords");
  const list = $("#key-points");
  keywords.innerHTML = "";
  list.innerHTML = "";
  if (!quick || !quick.key_points.length) {
    list.innerHTML = `<li class="empty" style="list-style:none">${escapeHtml(
      job.data?.status === "done" ? t("noSummary") : t("waitingText")
    )}</li>`;
  } else {
    for (const word of quick.keywords) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = word;
      keywords.append(chip);
    }
    for (const point of quick.key_points) {
      const li = document.createElement("li");
      li.innerHTML = `<button type="button" class="time">${clock(point.start)}</button><span></span>`;
      li.querySelector("span").textContent = point.text;
      li.querySelector("button").addEventListener("click", () => seek(point.start));
      list.append(li);
    }
  }

  // AI summary.
  const done = job.data?.status === "done";
  const aiStatus = job.data?.ai_status;
  const working = aiStatus === "working";
  $("#ai-start").disabled = !done || working;
  $("#ai-start").textContent = aiStatus === "done" ? t("aiAgain") : t("aiStart");
  $("#ai-progress").hidden = !working;
  $("#ai-stage").textContent = working ? stageText(job.data.ai_stage) : "";
  $("#ai-error").hidden = aiStatus !== "error";
  $("#ai-error").textContent = aiStatus === "error" ? stageText(job.data.ai_stage) : "";
  const output = $("#ai-output");
  output.classList.toggle("writing", working && !!job.data.ai_summary);
  if (job.data?.ai_summary) output.innerHTML = markdown(job.data.ai_summary);
  else output.innerHTML = !done && job.data?.options?.summary_model ? `<p class="hint">${escapeHtml(t("aiWaiting"))}</p>` : "";
}

function markdown(md) {
  // Enough Markdown for the summary: headings, bullet lists, bold.
  let html = "";
  let inList = false;
  for (const raw of md.split("\n")) {
    const line = raw.trim();
    const bullet = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)/);
    if (inList && !bullet) { html += "</ul>"; inList = false; }
    const inline = (s) => escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    if (!line) continue;
    if (line.startsWith("#")) html += `<h4>${inline(line.replace(/^#+\s*/, ""))}</h4>`;
    else if (bullet) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inline(bullet[1])}</li>`;
    } else html += `<p>${inline(line)}</p>`;
  }
  return html + (inList ? "</ul>" : "");
}

$("#ai-start").addEventListener("click", async () => {
  const job = activeJob();
  if (!job) return;
  try {
    await api(`/api/jobs/${job.id}/summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: $("#ai-model").value, language: $("#ai-language").value }),
    });
    job.data.ai_status = "working";
    job.data.ai_stage = "Starting";
    job.data.ai_summary = null;
    renderSummary(job);
    poll();
  } catch (err) {
    $("#ai-error").textContent = err.message;
    $("#ai-error").hidden = false;
  }
});

// ----------------------------------------------------------------- boot ----

async function boot() {
  try {
    state.config = await api("/api/config");
  } catch (err) {
    $("#setup-error").textContent = "Could not reach the Transcriber server. Is app.py running?";
    $("#setup-error").hidden = false;
    return;
  }
  renderQuality();
  applyLanguage();
}

applyLanguage();
boot();
