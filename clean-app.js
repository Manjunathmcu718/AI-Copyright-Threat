const DESK_API = "http://127.0.0.1:8001";
const DESK_HISTORY_KEY = "cineshield.local-history.v1";
const DESK_HISTORY_LIMIT = 24;

const deskState = {
  protectedFile: null,
  candidateFiles: [],
  results: [],
  investigation: null,
  publicSource: null,
  resultNotice: null,
  selectedIndex: 0,
  busy: false,
  history: deskLoadHistory()
};

const desk = (selector) => document.querySelector(selector);

function deskEscape(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#039;", '"': "&quot;"
  }[character]));
}

function deskLoadHistory() {
  try {
    const stored = JSON.parse(localStorage.getItem(DESK_HISTORY_KEY) || "[]");
    return Array.isArray(stored) ? stored.slice(0, DESK_HISTORY_LIMIT) : [];
  } catch {
    return [];
  }
}

function deskSaveHistory() {
  try {
    localStorage.setItem(DESK_HISTORY_KEY, JSON.stringify(deskState.history));
  } catch {
    // History is a convenience only; comparisons remain available if browser storage is disabled.
  }
}

function deskHistoryTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Saved just now" : date.toLocaleString();
}

function deskRenderHistory() {
  const list = desk("#desk-history-list");
  const clearButton = desk("#desk-clear-history");
  if (!list || !clearButton) return;

  clearButton.disabled = deskState.history.length === 0;
  if (!deskState.history.length) {
    list.innerHTML = '<div class="desk-history-empty">No completed checks yet. Your comparisons and public-discovery outcomes will appear here.</div>';
    return;
  }

  list.innerHTML = deskState.history.map((entry) => {
    const sources = Array.isArray(entry.sources) ? entry.sources : [];
    const candidateNames = Array.isArray(entry.candidates) ? entry.candidates.filter(Boolean) : [];
    const candidateText = candidateNames.length
      ? `Candidate${candidateNames.length === 1 ? "" : "s"}: ${candidateNames.join(", ")}`
      : entry.operation === "Web discovery" ? "Public discovery using the uploaded original" : "No candidate filename retained";
    const sourceLinks = sources.map((source, index) => {
      const pageUrl = String(source?.pageUrl || "");
      const mediaUrl = String(source?.mediaUrl || "");
      const target = pageUrl || mediaUrl;
      return target
        ? `<a href="${deskEscape(target)}" target="_blank" rel="noreferrer">Verified match ${index + 1} ↗</a>`
        : "";
    }).filter(Boolean).join(" · ");
    const confidence = Number.isFinite(Number(entry.confidence)) ? `${Number(entry.confidence).toFixed(1)}%` : "—";
    const tone = deskDecisionTone(entry.decision);
    return `<article class="desk-history-entry"><div><h3>${deskEscape(entry.workTitle || entry.original || "Untitled check")}</h3><p>${deskEscape(entry.operation || "Verification")} · Original: ${deskEscape(entry.original || "Unnamed video")}</p><p>${deskEscape(candidateText)}</p>${sourceLinks ? `<small>${sourceLinks}</small>` : ""}<small>${deskEscape(deskHistoryTime(entry.createdAt))}</small></div><div class="desk-history-tags"><span class="desk-history-tag">${deskEscape(entry.operation || "Verification")}</span><span class="desk-history-tag ${tone}">${deskEscape(entry.decision || "Completed")}</span><span class="desk-history-tag">${confidence}</span></div></article>`;
  }).join("");
}

function deskRecordHistory(entry) {
  const record = {
    id: globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    createdAt: new Date().toISOString(),
    operation: "Verification",
    workTitle: "",
    original: "",
    candidates: [],
    decision: "Completed",
    confidence: 0,
    sources: [],
    ...entry
  };
  deskState.history = [record, ...deskState.history].slice(0, DESK_HISTORY_LIMIT);
  deskSaveHistory();
  deskRenderHistory();
}

function deskFormatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "Video selected";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / (1024 ** index)).toFixed(index ? 1 : 0)} ${units[index]}`;
}

function deskInferTitle(fileName) {
  return String(fileName || "")
    .replace(/\.[^.]+$/, "")
    .replace(/[._-]+/g, " ")
    .replace(/\b(copy|final|v\d+)\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}

function deskDisplayUrl(value) {
  try {
    const url = new URL(value);
    return `${url.host}${url.pathname}`;
  } catch {
    return String(value || "—");
  }
}

function deskResultLabel(result, index = 0) {
  if (result?.sourcePage || result?.sourceUrl) return "Verified public video";
  return result?.fileName || `Candidate ${index + 1}`;
}

function deskRenderDiscoveryProof(result = null) {
  const proof = desk("#desk-discovery-proof");
  if (!proof) return;

  const sourceUrl = result?.sourcePage || result?.sourceUrl || "";
  const mediaUrl = result?.sourceMediaUrl || result?.sourceUrl || "";
  if (!sourceUrl) {
    proof.hidden = true;
    return;
  }

  const sourceHost = result?.sourceHost || deskState.publicSource?.host || "Public website";
  const confidence = Number(result?.confidence || 0).toFixed(1);
  const decision = result?.decision || "Verified";
  const tone = deskDecisionTone(decision);
  const pageItem = desk("#desk-proof-page").closest(".desk-proof-item");
  const mediaItem = desk("#desk-proof-media").closest(".desk-proof-item");

  desk("#desk-proof-status").textContent = `${decision} · ${confidence}%`;
  desk("#desk-proof-status").className = `desk-proof-status ${tone}`;
  desk("#desk-proof-summary").textContent = `CineShield found this public video and verified its Content DNA against the uploaded original.`;
  desk("#desk-proof-host").textContent = sourceHost;
  desk("#desk-proof-verification").textContent = `${decision} · ${confidence}%`;

  pageItem.hidden = !sourceUrl;
  desk("#desk-proof-page").href = sourceUrl || "#";
  desk("#desk-proof-page-url").textContent = deskDisplayUrl(sourceUrl);
  desk("#desk-proof-page-url").title = sourceUrl;

  mediaItem.hidden = !mediaUrl;
  desk("#desk-proof-media").href = mediaUrl || "#";
  desk("#desk-proof-media-url").textContent = deskDisplayUrl(mediaUrl);
  desk("#desk-proof-media-url").title = mediaUrl;
  proof.hidden = false;
}

function deskNotify(message) {
  const toast = desk("#desk-toast");
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(deskNotify.timer);
  deskNotify.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 3600);
}

function deskSetActivity(title, detail, tone = "ready") {
  const activity = desk("#desk-activity");
  desk("#desk-activity-title").textContent = title;
  desk("#desk-activity-detail").textContent = detail;
  desk("#desk-live-label").textContent = title;
  desk("#desk-live-copy").textContent = detail;
  activity.classList.toggle("is-working", tone === "working");
  activity.classList.toggle("is-error", tone === "error");
}

function deskSetStatus(label, tone = "") {
  const status = desk("#desk-status");
  status.textContent = label;
  status.className = `desk-status ${tone}`.trim();
}

function deskDecisionTone(decision) {
  const normalized = String(decision || "").toLowerCase();
  if (normalized.includes("match") && !normalized.includes("no")) return "match";
  if (normalized.includes("review")) return "review";
  return "no-match";
}

function deskSetProgress(stage) {
  const steps = ["#desk-command-upload", "#desk-command-compare", "#desk-command-review"];
  steps.forEach((selector, index) => {
    const item = desk(selector);
    item?.classList.toggle("is-active", index === stage);
    item?.classList.toggle("is-done", index < stage);
  });
}

function deskCanScan() {
  return Boolean(deskState.protectedFile && deskState.candidateFiles.length);
}

function deskSetBusy(busy) {
  deskState.busy = busy;
  document.body.classList.toggle("is-busy", busy);
  desk("#desk-run-scan").disabled = busy || !deskCanScan();
  desk("#desk-clear").disabled = busy || !(deskState.protectedFile || deskState.candidateFiles.length);
  desk("#desk-inspect-source").disabled = busy;
  if (desk("#desk-verify-url")) desk("#desk-verify-url").disabled = busy;
  desk("#desk-create-copy").disabled = busy || !deskState.protectedFile;
}

function deskRenderFiles() {
  const protectedName = desk("#desk-protected-name");
  const protectedMeta = desk("#desk-protected-meta");
  const candidateName = desk("#desk-candidate-name");
  const candidateMeta = desk("#desk-candidate-meta");

  if (deskState.protectedFile) {
    protectedName.textContent = deskState.protectedFile.name;
    protectedMeta.textContent = deskFormatBytes(deskState.protectedFile.size);
    desk("#desk-protected-dropzone").classList.add("is-filled");
    if (!desk("#desk-work-title").value) desk("#desk-work-title").value = deskInferTitle(deskState.protectedFile.name);
  } else {
    protectedName.textContent = "Select the video you own";
    protectedMeta.textContent = "MP4, MOV, AVI, MKV, or WebM";
    desk("#desk-protected-dropzone").classList.remove("is-filled");
  }

  desk("#desk-hero-original").textContent = deskState.protectedFile
    ? deskState.protectedFile.name
    : "Waiting for video";

  if (deskState.candidateFiles.length) {
    candidateName.textContent = deskState.candidateFiles.length === 1
      ? deskState.candidateFiles[0].name
      : `${deskState.candidateFiles.length} videos selected`;
    candidateMeta.textContent = deskState.candidateFiles.length === 1
      ? deskFormatBytes(deskState.candidateFiles[0].size)
      : deskState.candidateFiles.map((file) => file.name).join(", ");
    desk("#desk-candidate-dropzone").classList.add("is-filled");
  } else {
    candidateName.textContent = "Select one or more videos";
    candidateMeta.textContent = "Multiple candidates are supported";
    desk("#desk-candidate-dropzone").classList.remove("is-filled");
  }

  desk("#desk-hero-candidate").textContent = deskState.candidateFiles.length
    ? deskState.candidateFiles.length === 1
      ? deskState.candidateFiles[0].name
      : `${deskState.candidateFiles.length} selected videos`
    : "Waiting for video";

  deskSetBusy(deskState.busy);
}

function deskRenderResults() {
  const hasResults = deskState.results.length > 0;
  const empty = desk("#desk-empty");
  empty.hidden = hasResults;
  desk("#desk-results-layout").hidden = !hasResults;
  if (!hasResults) {
    const title = empty.querySelector("strong");
    const detail = empty.querySelector("p");
    if (deskState.resultNotice) {
      title.textContent = deskState.resultNotice.title;
      detail.textContent = deskState.resultNotice.detail;
    } else {
      title.textContent = "Your result will appear here.";
      detail.innerHTML = "Add an original and a candidate video, then choose <em>Compare videos</em>.";
    }
    deskRenderDiscoveryProof();
    return;
  }

  if (deskState.selectedIndex >= deskState.results.length) deskState.selectedIndex = 0;
  const list = desk("#desk-candidate-list");
  list.innerHTML = deskState.results.map((result, index) => {
    const selected = index === deskState.selectedIndex ? "is-selected" : "";
    const label = deskResultLabel(result, index);
    const detail = result.sourceHost ? `${result.decision || "Verified"} · ${result.sourceHost}` : (result.decision || "Pending");
    return `<button class="desk-candidate ${selected}" type="button" data-desk-result-index="${index}">
      <span><strong>${deskEscape(label)}</strong><small>${deskEscape(detail)}</small></span>
      <span class="desk-candidate-score">${Number(result.confidence || 0).toFixed(1)}%</span>
    </button>`;
  }).join("");

  list.querySelectorAll("[data-desk-result-index]").forEach((button) => {
    button.addEventListener("click", () => {
      deskState.selectedIndex = Number(button.dataset.deskResultIndex);
      deskRenderResults();
    });
  });

  const result = deskState.results[deskState.selectedIndex];
  const signals = result.signals || {};
  const signalNames = ["Visual", "Scene", "Temporal", "Duration", "Coverage"];
  const reasons = Array.isArray(result.reasons) ? result.reasons : [];
  const matchingEvidence = Array.isArray(result.matchingEvidence) ? result.matchingEvidence : [];
  const mismatchEvidence = Array.isArray(result.mismatchEvidence) ? result.mismatchEvidence : [];
  const tone = deskDecisionTone(result.decision);
  const sourceUrl = result.sourcePage || result.sourceUrl || deskState.publicSource?.pageUrl || "";
  const sourceHost = result.sourceHost || deskState.publicSource?.host || "";
  const mediaUrl = result.sourceMediaUrl || result.sourceUrl || "";
  const resultLabel = deskResultLabel(result, deskState.selectedIndex);
  const scoreLabel = tone === "no-match" ? "verified copy confidence" : "confidence";
  desk("#desk-selected-result").innerHTML = `
    <div class="desk-result-top">
      <div>
        <h3>${deskEscape(resultLabel)}</h3>
        <p>${sourceUrl ? "Web discovery found this public video and compared its Content DNA with the uploaded original." : "Content DNA comparison from the selected video files."}</p>
      </div>
      <div class="desk-decision ${tone}">
        <strong>${deskEscape(result.decision || "No result")}</strong>
        <span>${Number(result.confidence || 0).toFixed(1)}% ${scoreLabel}</span>
      </div>
    </div>
    <div class="desk-signal-grid">
      ${signalNames.map((name) => `<div class="desk-signal" style="--signal:${Math.max(0, Math.min(100, Number(signals[name] || 0)))}%"><span>${name}</span><strong>${Number(signals[name] || 0)}%</strong></div>`).join("")}
    </div>
    <div class="desk-evidence-breakdown">
      <section class="desk-evidence-support"><span>Supports a copy</span><ul>${matchingEvidence.map((item) => `<li>${deskEscape(item)}</li>`).join("") || "<li>No independent signal met the copy threshold.</li>"}</ul></section>
      <section class="desk-evidence-mismatch"><span>Does not support a copy</span><ul>${mismatchEvidence.map((item) => `<li>${deskEscape(item)}</li>`).join("") || "<li>No material mismatch was detected.</li>"}</ul></section>
    </div>
    <ul class="desk-reasons">
      ${reasons.length ? `<li>${deskEscape(reasons[reasons.length - 1])}</li>` : "<li>The comparison completed without additional notes.</li>"}
    </ul>
    <div class="desk-result-actions"><button class="desk-quiet" id="desk-copy-summary" type="button">Copy summary</button></div>`;

  deskRenderDiscoveryProof({ ...result, sourcePage: sourceUrl, sourceMediaUrl: mediaUrl, sourceHost });

  desk("#desk-copy-summary").addEventListener("click", async () => {
    const summary = [
      `CineShield result: ${result.decision} (${Number(result.confidence || 0).toFixed(1)}%)`,
      `Candidate: ${resultLabel}`,
      ...reasons
    ].join("\n");
    try {
      await navigator.clipboard.writeText(summary);
      deskNotify("Result summary copied.");
    } catch {
      deskNotify("Could not copy the summary in this browser.");
    }
  });
}

async function deskRunScan() {
  if (!deskCanScan() || deskState.busy) return;
  const button = desk("#desk-run-scan");
  const label = button.querySelector("span");
  label.textContent = "Comparing videos...";
  deskSetBusy(true);
  deskSetProgress(1);
  deskSetStatus("Comparing");
  deskSetActivity("Comparing the videos", "Extracting frame signatures and checking their scene order.", "working");

  const formData = new FormData();
  formData.append("protected", deskState.protectedFile);
  deskState.candidateFiles.forEach((file) => formData.append("candidates", file));

  try {
    const response = await fetch(`${DESK_API}/api/scan`, { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "The comparison could not be completed.");
    deskState.results = Array.isArray(payload.results) ? payload.results : [];
    deskState.investigation = payload.investigation || null;
    deskState.publicSource = null;
    deskState.resultNotice = null;
    deskState.selectedIndex = 0;
    const topResult = deskState.results[0] || {};
    deskRecordHistory({
      operation: "Local comparison",
      workTitle: desk("#desk-work-title").value.trim() || deskInferTitle(deskState.protectedFile?.name),
      original: deskState.protectedFile?.name || "Unnamed original",
      candidates: deskState.candidateFiles.map((file) => file.name),
      decision: topResult.decision || "No result",
      confidence: Number(topResult.confidence || 0)
    });
    deskRenderResults();
    deskSetProgress(2);
    const top = deskState.results[0];
    deskSetStatus(top?.decision || "Complete", deskDecisionTone(top?.decision));
    deskSetActivity("Comparison complete", deskState.investigation?.summary || "Select a candidate to review its evidence.");
    desk("#desk-results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    deskSetStatus("Could not compare", "error");
    deskSetProgress(0);
    deskSetActivity("Comparison failed", error.message || "Check that the local API is running.", "error");
    deskNotify(error.message || "Comparison failed.");
  } finally {
    label.textContent = "Compare videos";
    deskSetBusy(false);
  }
}

function deskSourceTitle() {
  return desk("#desk-source-title").value.trim()
    || desk("#desk-work-title").value.trim()
    || deskInferTitle(deskState.protectedFile?.name);
}

function deskSetSourceFeedback(html) {
  desk("#desk-source-feedback").innerHTML = html;
}

function deskSetDiscoveryState(label, tone = "ready") {
  const state = desk("#desk-discovery-state");
  if (!state) return;
  state.className = `desk-discovery-state ${tone}`;
  state.innerHTML = `<i aria-hidden="true"></i>${deskEscape(label)}`;
}

async function deskCreateTestCopy() {
  if (!deskState.protectedFile || deskState.busy) return;
  deskSetBusy(true);
  deskSetActivity("Creating test copy", "Applying a small crop and visible label for your controlled public-site test.", "working");
  try {
    const formData = new FormData();
    formData.append("video", deskState.protectedFile);
    const response = await fetch(`${DESK_API}/api/demo/transformed-copy`, { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "The test copy could not be created.");
    const download = document.createElement("a");
    download.href = `${DESK_API}${payload.downloadUrl}`;
    download.download = payload.fileName || "controlled_test_copy.mp4";
    document.body.appendChild(download);
    download.click();
    download.remove();
    deskSetActivity("Test copy created", "Upload the downloaded copy to your controlled public website, then use Find copy on website.");
    deskNotify("Test copy downloaded.");
  } catch (error) {
    deskSetActivity("Could not create test copy", error.message || "Try another local video.", "error");
    deskNotify(error.message || "Could not create test copy.");
  } finally {
    deskSetBusy(false);
  }
}

async function deskInspectSource() {
  const title = deskSourceTitle();
  if (!deskState.protectedFile) {
    deskSetDiscoveryState("Original video needed", "review");
    deskSetSourceFeedback("<strong>Select the original video before searching your public website.</strong>");
    return;
  }
  if (!desk("#desk-url-authorized").checked) {
    deskSetDiscoveryState("Authorization needed", "review");
    deskSetSourceFeedback("<strong>Confirm authorization before running web discovery.</strong>");
    return;
  }
  const button = desk("#desk-inspect-source");
  const buttonLabel = button.querySelector("strong");
  buttonLabel.textContent = "Searching public video…";
  deskSetBusy(true);
  deskSetProgress(1);
  deskSetStatus("Finding copy");
  deskSetDiscoveryState("Checking public source", "working");
  deskSetActivity("Running web discovery", "Looking for public video evidence and checking its Content DNA.", "working");
  deskSetSourceFeedback("Searching public video evidence...");
  try {
    const formData = new FormData();
    formData.append("protected", deskState.protectedFile);
    formData.append("title", title);
    formData.append("authorization_confirmed", "true");
    const response = await fetch(`${DESK_API}/api/discovery/controlled-verify`, { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "The public website could not be inspected.");
    const checkedMedia = Math.max(0, Number(payload.checkedMedia || 0));
    const matchedMedia = Math.max(0, Number(payload.matchedMedia || 0));
    const checkedLabel = checkedMedia === 1 ? "1 accessible public video" : `${checkedMedia} accessible public videos`;
    if (!payload.foundMatch || !payload.result) {
      deskState.results = [];
      deskState.investigation = null;
      deskState.publicSource = null;
      deskState.resultNotice = {
        title: "No verifiable copy found.",
        detail: "CineShield checked the current public video evidence and found no Content DNA match for this original."
      };
      deskRecordHistory({
        operation: "Web discovery",
        workTitle: title,
        original: deskState.protectedFile?.name || "Unnamed original",
        decision: "No match",
        confidence: 0
      });
      deskRenderResults();
      deskSetProgress(0);
      deskSetStatus("No match", "review");
      deskSetDiscoveryState("No matching public copy", "review");
      const noMatchDetail = "No matching public copy was found through public discovery.";
      deskSetSourceFeedback(`<strong>Web discovery complete.</strong><br>${deskEscape(noMatchDetail)}`);
      deskSetActivity("No verifiable copy found", noMatchDetail, "error");
      return;
    }
    const result = payload.result;
    deskState.results = [result];
    deskState.investigation = payload.investigation || null;
    deskState.resultNotice = null;
    deskState.publicSource = {
      pageUrl: result.sourcePage || "",
      host: result.sourceHost || ""
    };
    deskState.selectedIndex = 0;
    deskRecordHistory({
      operation: "Web discovery",
      workTitle: title,
      original: deskState.protectedFile?.name || "Unnamed original",
      decision: result.decision || "Match",
      confidence: Number(result.confidence || 0),
      sources: Array.isArray(payload.matchedSources) ? payload.matchedSources : []
    });
    deskRenderResults();
    deskSetProgress(2);
    const top = deskState.results[0];
    deskSetStatus(top?.decision || "Complete", deskDecisionTone(top?.decision));
    deskSetDiscoveryState("Matching public video found", "match");
    const matchLabel = matchedMedia === 1 ? "1 matching video" : `${matchedMedia} matching videos`;
    const verifiedSources = Array.isArray(payload.matchedSources) ? payload.matchedSources : [];
    const sourceRows = verifiedSources.map((source, index) => {
      const pageUrl = String(source?.pageUrl || "");
      const mediaUrl = String(source?.mediaUrl || "");
      const confidence = Number(source?.confidence || 0).toFixed(1);
      return `<li><strong>Match ${index + 1} (${confidence}%):</strong> <a href="${deskEscape(pageUrl || mediaUrl)}" target="_blank" rel="noreferrer">${deskEscape(pageUrl || mediaUrl)}</a>${mediaUrl && mediaUrl !== pageUrl ? `<br><a href="${deskEscape(mediaUrl)}" target="_blank" rel="noreferrer">${deskEscape(mediaUrl)}</a>` : ""}</li>`;
    }).join("");
    deskSetSourceFeedback(`<strong>Web discovery found ${deskEscape(matchLabel)}.</strong><ul><li>Public videos checked: ${checkedMedia}</li><li>Decision: ${deskEscape(top.decision || "No result")} (${Number(top.confidence || 0).toFixed(1)}%)</li>${sourceRows || `<li>Video page: ${deskEscape(top.sourcePage || "")}</li><li>Video URL: ${deskEscape(top.sourceMediaUrl || top.sourceUrl || "")}</li>`}</ul>`);
    deskSetActivity("Web discovery found a match", `${matchLabel} verified by Content DNA after checking ${checkedLabel}.`);
    desk("#desk-results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    deskSetStatus("Could not verify", "error");
    deskSetProgress(0);
    deskSetDiscoveryState("Check could not finish", "error");
    deskSetSourceFeedback(`<strong>Could not verify this website.</strong><br>${deskEscape(error.message || "Use a reachable public video page.")}`);
    deskSetActivity("Public website verification failed", error.message || "Use a reachable public video page.", "error");
  } finally {
    buttonLabel.textContent = "Run Web Discovery";
    deskSetBusy(false);
  }
}

async function deskVerifyPublicUrl() {
  const url = desk("#desk-direct-media-url").value.trim() || desk("#desk-source-url").value.trim();
  if (!deskState.protectedFile) {
    deskSetSourceFeedback("<strong>Select the original video before verifying a public direct video URL.</strong>");
    return;
  }
  if (!url || !desk("#desk-url-authorized").checked) {
    deskSetSourceFeedback("<strong>Enter a direct public video URL and confirm authorization.</strong>");
    return;
  }
  deskSetBusy(true);
  deskSetProgress(1);
  deskSetStatus("Verifying");
  deskSetActivity("Verifying the public video", "Downloading the authorized direct file and comparing its Content DNA.", "working");
  try {
    const formData = new FormData();
    formData.append("protected", deskState.protectedFile);
    formData.append("request", JSON.stringify({ candidateUrls: [url], authorizationConfirmed: true }));
    const response = await fetch(`${DESK_API}/api/scan/url-candidates`, { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "The direct video could not be verified.");
    deskState.results = (Array.isArray(payload.results) ? payload.results : []).map((result) => ({ ...result, sourcePage: url }));
    deskState.investigation = payload.investigation || null;
    deskState.publicSource = { pageUrl: url, host: "" };
    deskState.selectedIndex = 0;
    const directTopResult = deskState.results[0] || {};
    deskRecordHistory({
      operation: "Direct URL check",
      workTitle: deskSourceTitle(),
      original: deskState.protectedFile?.name || "Unnamed original",
      decision: directTopResult.decision || "No result",
      confidence: Number(directTopResult.confidence || 0),
      sources: [{ pageUrl: url, mediaUrl: directTopResult.sourceMediaUrl || directTopResult.sourceUrl || url }]
    });
    deskRenderResults();
    deskSetProgress(2);
    const top = deskState.results[0];
    deskSetStatus(top?.decision || "Complete", deskDecisionTone(top?.decision));
    deskSetActivity("Direct video verification complete", deskState.investigation?.summary || "Review the result below.");
    desk("#desk-results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    deskSetStatus("Could not verify", "error");
    deskSetProgress(0);
    deskSetActivity("Public video verification failed", error.message || "Use a direct public video-file URL.", "error");
    deskSetSourceFeedback(`<strong>Verification failed.</strong><br>${deskEscape(error.message || "Use a direct public video-file URL.")}`);
  } finally {
    deskSetBusy(false);
  }
}

function deskClearFiles() {
  if (deskState.busy) return;
  deskState.protectedFile = null;
  deskState.candidateFiles = [];
  deskState.results = [];
  deskState.investigation = null;
  deskState.publicSource = null;
  deskState.resultNotice = null;
  deskState.selectedIndex = 0;
  desk("#desk-protected-input").value = "";
  desk("#desk-candidate-input").value = "";
  desk("#desk-work-title").value = "";
  deskRenderFiles();
  deskRenderResults();
  deskSetProgress(0);
  deskSetStatus("Waiting");
  deskSetDiscoveryState("Ready to check");
  deskSetActivity("Ready to verify", "Add an original video and at least one candidate.");
}

function deskBindDropzone(selector, onFiles) {
  const zone = desk(selector);
  ["dragenter", "dragover"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      if (!deskState.busy) zone.classList.add("is-dragging");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.remove("is-dragging");
    });
  });
  zone.addEventListener("drop", (event) => {
    if (deskState.busy) return;
    const files = Array.from(event.dataTransfer?.files || []).filter((file) => file.type.startsWith("video/"));
    if (!files.length) {
      deskNotify("Drop a video file to add it here.");
      return;
    }
    onFiles(files);
  });
}

function deskBindEvents() {
  desk("#desk-protected-input").addEventListener("change", (event) => {
    deskState.protectedFile = event.target.files?.[0] || null;
    deskRenderFiles();
    if (deskState.protectedFile) deskSetActivity("Original video selected", "Now add the video or videos you want to compare.");
  });
  desk("#desk-candidate-input").addEventListener("change", (event) => {
    deskState.candidateFiles = Array.from(event.target.files || []);
    deskRenderFiles();
    if (deskCanScan()) deskSetActivity("Ready to compare", "Both inputs are present. Start the comparison when you are ready.");
  });
  desk("#desk-run-scan").addEventListener("click", deskRunScan);
  desk("#desk-create-copy").addEventListener("click", deskCreateTestCopy);
  desk("#desk-clear").addEventListener("click", deskClearFiles);
  desk("#desk-clear-history").addEventListener("click", () => {
    deskState.history = [];
    deskSaveHistory();
    deskRenderHistory();
    deskNotify("Local history cleared.");
  });
  desk("#desk-inspect-source").addEventListener("click", deskInspectSource);
  desk("#desk-verify-url")?.addEventListener("click", deskVerifyPublicUrl);
  desk("#desk-open-source").addEventListener("click", () => {
    const sourceCheck = desk("#desk-source-check");
    sourceCheck.open = true;
    sourceCheck.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  document.querySelectorAll('a[href="#desk-source-check"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const sourceCheck = desk("#desk-source-check");
      sourceCheck.open = true;
      sourceCheck.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
  desk("#desk-source-check").addEventListener("toggle", (event) => {
    if (event.target.open && !desk("#desk-source-title").value) desk("#desk-source-title").value = desk("#desk-work-title").value;
  });
  desk("#desk-start").addEventListener("click", () => desk("#desk-verify").scrollIntoView({ behavior: "smooth", block: "start" }));
  document.querySelectorAll("[data-desk-scroll]").forEach((button) => {
    button.addEventListener("click", () => desk(button.dataset.deskScroll)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  });
  deskBindDropzone("#desk-protected-dropzone", (files) => {
    deskState.protectedFile = files[0];
    deskRenderFiles();
    deskSetActivity("Original video selected", "Now add the video or videos you want to compare.");
  });
  deskBindDropzone("#desk-candidate-dropzone", (files) => {
    deskState.candidateFiles = files;
    deskRenderFiles();
    deskSetActivity(deskCanScan() ? "Ready to compare" : "Candidate video selected", deskCanScan() ? "Both inputs are present. Start the comparison when you are ready." : "Add the original video to enable comparison.");
  });
}

deskRenderFiles();
deskRenderResults();
deskRenderHistory();
deskBindEvents();
