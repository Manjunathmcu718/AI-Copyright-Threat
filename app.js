const dnaSignals = [
  { name: "Visual", value: 97, tone: "Frame hashes and embeddings" },
  { name: "Audio", value: 94, tone: "Acoustic fingerprint" },
  { name: "Scene", value: 96, tone: "Sequence similarity" },
  { name: "Temporal", value: 92, tone: "Timing pattern" },
  { name: "OCR/Text", value: 88, tone: "Subtitle and text traces" },
  { name: "Metadata", value: 91, tone: "Duration, language, codec" },
  { name: "Semantic", value: 93, tone: "Narrative embedding" }
];

const fusionWeights = [
  { name: "Audio reliability", value: 32, detail: "Raised under crop and watermark transformations" },
  { name: "Scene sequence", value: 26, detail: "Stable across compression and resolution changes" },
  { name: "Visual fingerprint", value: 24, detail: "Partially discounted after crop detection" },
  { name: "Text and metadata", value: 18, detail: "Supplementary corroboration only" }
];

const labTransforms = [
  {
    id: "compression",
    name: "Compression",
    detail: "codec loss",
    baselinePenalty: 18,
    adaptivePenalty: 4,
    profile: { Visual: -6, Audio: 3, Scene: 3, Temporal: 1, Text: -1, Metadata: 0 }
  },
  {
    id: "crop",
    name: "Crop",
    detail: "frame edge loss",
    baselinePenalty: 28,
    adaptivePenalty: 9,
    profile: { Visual: -14, Audio: 9, Scene: 7, Temporal: 2, Text: -3, Metadata: -1 }
  },
  {
    id: "watermark",
    name: "Watermark",
    detail: "visual overlay",
    baselinePenalty: 22,
    adaptivePenalty: 6,
    profile: { Visual: -10, Audio: 5, Scene: 5, Temporal: 1, Text: -2, Metadata: 0 }
  },
  {
    id: "audio",
    name: "Audio noise",
    detail: "pitch and noise",
    baselinePenalty: 20,
    adaptivePenalty: 12,
    profile: { Visual: 7, Audio: -14, Scene: 6, Temporal: 3, Text: 0, Metadata: 0 }
  },
  {
    id: "subtitles",
    name: "Subtitle edit",
    detail: "text mismatch",
    baselinePenalty: 10,
    adaptivePenalty: 5,
    profile: { Visual: 2, Audio: 2, Scene: 2, Temporal: 1, Text: -11, Metadata: 0 }
  },
  {
    id: "partial",
    name: "Partial clip",
    detail: "short segment",
    baselinePenalty: 36,
    adaptivePenalty: 17,
    profile: { Visual: -5, Audio: -3, Scene: 8, Temporal: -12, Text: -4, Metadata: -4 }
  }
];

const labState = {
  active: new Set(["crop", "watermark"])
};

const timelineSteps = [
  { id: "register", title: "Register", detail: "Owner adds Project X and authorized sources" },
  { id: "dna", title: "DNA", detail: "Visual, audio, scene, text, metadata profile" },
  { id: "discover", title: "Discover", detail: "Controlled candidate corpus scanned" },
  { id: "verify", title: "Verify", detail: "Adaptive fusion compares transformed copies" },
  { id: "graph", title: "Map", detail: "Related variants become source clusters" },
  { id: "investigate", title: "Explain", detail: "AI investigator summarizes evidence" },
  { id: "evidence", title: "Evidence", detail: "Case package prepared for review" },
  { id: "monitor", title: "Monitor", detail: "New related copies update the case" }
];

const candidates = [
  {
    id: "SRC-A7",
    name: "Source Cluster A7",
    category: "high",
    confidence: 96.8,
    transformation: "Compression + crop + watermark",
    variants: 9,
    sources: 17,
    risk: "Critical",
    signals: { Visual: 93, Audio: 98, Scene: 96, Temporal: 94, "OCR/Text": 88, Metadata: 91 },
    reasons: [
      "Audio fingerprint survived video crop and watermark",
      "Scene ordering matches 16 of 17 sampled transitions",
      "Three variants share the same transformed visual profile",
      "No match in authorized distribution registry"
    ],
    summary:
      "A high-confidence suspected copy was detected across a connected cluster. The strongest evidence comes from audio and scene continuity, with visual evidence partially degraded by crop and watermark transforms."
  },
  {
    id: "SRC-B2",
    name: "Mirror Ring B2",
    category: "high",
    confidence: 94.1,
    transformation: "Resolution change + subtitle edit",
    variants: 6,
    sources: 11,
    risk: "High",
    signals: { Visual: 95, Audio: 92, Scene: 95, Temporal: 93, "OCR/Text": 79, Metadata: 86 },
    reasons: [
      "Visual and scene similarity remain high after downscale",
      "Subtitle text diverges while shot sequence remains stable",
      "Metadata pattern appears on six related sources"
    ],
    summary:
      "The candidate appears to be a lower-resolution variant. Subtitle evidence is weak, so the fusion engine relies on visual, scene, and temporal signals."
  },
  {
    id: "SRC-C4",
    name: "Partial Clip C4",
    category: "review",
    confidence: 82.6,
    transformation: "Partial extraction",
    variants: 3,
    sources: 5,
    risk: "Review",
    signals: { Visual: 83, Audio: 87, Scene: 81, Temporal: 72, "OCR/Text": 64, Metadata: 51 },
    reasons: [
      "Only a short scene window matches the protected work",
      "Temporal coverage is too limited for automatic escalation",
      "Recommended action is human review"
    ],
    summary:
      "This candidate contains a partial match. CineShield keeps it below the high-confidence threshold because the evidence window is narrow."
  },
  {
    id: "SRC-D9",
    name: "Audio Altered D9",
    category: "review",
    confidence: 78.4,
    transformation: "Audio noise + pitch shift",
    variants: 4,
    sources: 6,
    risk: "Review",
    signals: { Visual: 88, Audio: 61, Scene: 85, Temporal: 84, "OCR/Text": 71, Metadata: 69 },
    reasons: [
      "Audio channel has been heavily modified",
      "Visual and temporal evidence suggest a likely relation",
      "Confidence remains bounded because one major modality is weak"
    ],
    summary:
      "The video channel looks related, but the audio fingerprint is degraded. The system escalates instead of over-claiming."
  }
];

const graphNodes = [
  { id: "work", label: "Movie", x: 380, y: 76, type: "work", candidate: "SRC-A7" },
  { id: "a", label: "A7", x: 228, y: 182, type: "source", candidate: "SRC-A7" },
  { id: "b", label: "B2", x: 380, y: 196, type: "source", candidate: "SRC-B2" },
  { id: "c", label: "C4", x: 536, y: 178, type: "source", candidate: "SRC-C4" },
  { id: "d", label: "D9", x: 142, y: 316, type: "source", candidate: "SRC-D9" },
  { id: "e", label: "E1", x: 278, y: 338, type: "source", candidate: "SRC-A7" },
  { id: "f", label: "F3", x: 450, y: 332, type: "source", candidate: "SRC-B2" },
  { id: "g", label: "G6", x: 618, y: 316, type: "source", candidate: "SRC-C4" }
];

const graphEdges = [
  {
    id: "edge-work-a",
    from: "work",
    to: "a",
    type: "dna",
    relation: "Content DNA match",
    confidence: 96.8,
    evidence: ["18 scene windows matched", "Audio fingerprint 98%", "Visual signal degraded by crop"],
    why: "Both records appear to contain the same transformed segment of Project Monsoon, with audio and scene evidence compensating for visual degradation."
  },
  {
    id: "edge-work-b",
    from: "work",
    to: "b",
    type: "dna",
    relation: "Content DNA match",
    confidence: 94.1,
    evidence: ["Resolution-normalized visual match", "Scene order preserved", "Subtitle evidence discounted"],
    why: "The candidate is linked because downscaled frames still preserve the protected work's scene order and temporal structure."
  },
  {
    id: "edge-work-c",
    from: "work",
    to: "c",
    type: "dna",
    relation: "Partial content match",
    confidence: 82.6,
    evidence: ["Short scene window matched", "Limited temporal coverage", "Review gate required"],
    why: "The link is plausible but bounded because only a short content window matches; CineShield routes it to review."
  },
  {
    id: "edge-a-d",
    from: "a",
    to: "d",
    type: "pattern",
    relation: "Related distribution pattern",
    confidence: 78.4,
    evidence: ["Shared release timestamp pattern", "Similar transformed visual profile", "Audio channel mismatch"],
    why: "These sources are not treated as the same content with high confidence; they are linked as a pattern-level lead for investigation."
  },
  {
    id: "edge-a-e",
    from: "a",
    to: "e",
    type: "dna",
    relation: "Same transformed variant",
    confidence: 95.3,
    evidence: ["Crop and watermark profile reused", "Same audio fingerprint", "Scene sequence stable"],
    why: "The same crop and watermark profile appears with matching audio, suggesting a reused transformed variant."
  },
  {
    id: "edge-b-f",
    from: "b",
    to: "f",
    type: "dna",
    relation: "Same lower-resolution variant",
    confidence: 92.4,
    evidence: ["Downscaled frame embeddings", "Temporal profile match", "Metadata family match"],
    why: "Both candidates preserve the same lower-resolution frame and timing signature."
  },
  {
    id: "edge-c-g",
    from: "c",
    to: "g",
    type: "pattern",
    relation: "Partial clip cluster",
    confidence: 80.2,
    evidence: ["Overlapping scene segment", "Short clip duration", "Escalated for review"],
    why: "The overlap is limited to a short scene segment, so the graph keeps it visible without treating it as an automatic action case."
  },
  {
    id: "edge-e-f",
    from: "e",
    to: "f",
    type: "pattern",
    relation: "Cross-cluster distribution signal",
    confidence: 74.7,
    evidence: ["Similar variant naming pattern", "Near-identical observation window", "Different content transform"],
    why: "This is an investigative relationship based on distribution pattern, not a direct same-copy conclusion."
  }
];

const benchmarks = [
  { transformation: "Filename change", baseline: 34, cineshield: 99, note: "Metadata ignored when content DNA is strong" },
  { transformation: "Compression", baseline: 76, cineshield: 97, note: "Scene and audio evidence stay stable" },
  { transformation: "Resolution change", baseline: 72, cineshield: 95, note: "Visual embeddings normalize downscale" },
  { transformation: "Watermark", baseline: 66, cineshield: 92, note: "Visual discounted, audio raised" },
  { transformation: "Cropping", baseline: 58, cineshield: 89, note: "Adaptive fusion shifts trust to audio and scenes" },
  { transformation: "Audio modification", baseline: 61, cineshield: 86, note: "Scene and temporal evidence compensate" },
  { transformation: "Partial clip", baseline: 46, cineshield: 81, note: "Bounded confidence with review threshold" }
];

const state = {
  selectedCandidateId: "SRC-A7",
  selectedNodeId: "a",
  selectedEdgeId: null,
  filter: "all",
  caseStatus: "Human review",
  stage: "register"
};

const localScanState = {
  protectedFile: null,
  candidateFiles: [],
  protectedDna: null,
  results: [],
  investigation: null,
  downloadedUrlCandidates: [],
  rejectedUrlCandidates: [],
  selectedResultIndex: 0,
  resultSource: "",
  status: "Waiting",
  statusTone: "",
  busy: false,
  error: ""
};

const webDiscoveryState = {
  candidates: [],
  excludedCandidates: [],
  sourcesScanned: [],
  query: "",
  status: "Waiting",
  statusTone: "",
  busy: false,
  error: "",
  summary: "Waiting for seed URLs.",
  mediaReferenceCount: 0,
  verifiedMediaCount: 0,
  authorizedExcluded: 0,
  provider: "seed",
  providerStatus: "seed_only",
  setupRequired: false,
  setupMessage: "",
  searchQueries: [],
  searchResultCount: 0,
  searchErrors: [],
  sourceFocusDomains: [],
  providerResults: [],
  coverage: null,
  expansionUrls: [],
  contentVerifiedCount: 0,
  monitorActive: false,
  monitorRuns: [],
  monitorStartedAt: null,
  monitorTimer: null,
  lastRunAt: null
};

const LOCAL_FRAME_SAMPLES = 8;
const LOCAL_FRAME_WIDTH = 20;
const LOCAL_FRAME_HEIGHT = 12;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    };
    return replacements[character];
  });
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value >= 10 || index === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`;
}

function formatDuration(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "unknown";
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remaining}`;
}

function setLocalStatus(status, tone = "", error = "") {
  localScanState.status = status;
  localScanState.statusTone = tone;
  localScanState.error = error;
  renderLocalScanner();
}

function setWebDiscoveryStatus(status, tone = "", error = "") {
  webDiscoveryState.status = status;
  webDiscoveryState.statusTone = tone;
  webDiscoveryState.error = error;
  renderWebDiscovery();
}

function parseListInput(value) {
  return String(value || "")
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function uniqueList(values) {
  const seen = new Set();
  return values.filter((value) => {
    const key = String(value || "").trim();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function collectUrlsFromFeedValue(value, urls) {
  if (typeof value === "string") {
    parseListInput(value).forEach((item) => urls.push(item));
    return;
  }

  if (Array.isArray(value)) {
    value.forEach((item) => collectUrlsFromFeedValue(item, urls));
    return;
  }

  if (!value || typeof value !== "object") return;

  ["url", "href", "sourceUrl", "pageUrl"].forEach((key) => {
    if (typeof value[key] === "string") urls.push(value[key]);
  });
  ["urls", "seedUrls", "sourceUrls", "pages", "items", "sources"].forEach((key) => {
    if (value[key]) collectUrlsFromFeedValue(value[key], urls);
  });
}

function parsePartnerSourceFeed(value) {
  const raw = String(value || "").trim();
  if (!raw) return [];

  const urls = [];
  if (/^[\[{]/.test(raw)) {
    try {
      collectUrlsFromFeedValue(JSON.parse(raw), urls);
      return uniqueList(urls);
    } catch {
      return uniqueList(parseListInput(raw));
    }
  }

  return uniqueList(parseListInput(raw));
}

function readNumberInput(selector, fallback, min, max) {
  const raw = Number($(selector)?.value);
  if (!Number.isFinite(raw)) return fallback;
  return Math.max(min, Math.min(max, Math.round(raw)));
}

function inferTitleFromFilename(fileName) {
  const withoutExtension = String(fileName || "").replace(/\.[a-z0-9]{2,5}$/i, "");
  const cleaned = withoutExtension
    .replace(/[_+.]+/g, " ")
    .replace(/\b(144p|240p|360p|480p|720p|1080p|2160p|4k|hd|hdrip|webrip|webdl|web-dl|dvdscr|camrip|bluray|x264|x265|h264|h265|aac|ddp|yts|rarbg)\b/gi, " ")
    .replace(/\b(hindi|telugu|tamil|malayalam|kannada|english|dubbed|dual audio)\b/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
  const inferred = cleaned || withoutExtension.trim();
  return /^\d+$/.test(inferred) ? "" : inferred;
}

function getProtectedDiscoveryTitle() {
  const protectedTitle = $("#protected-title-input")?.value.trim() || "";
  const webTitle = $("#web-title-input")?.value.trim() || "";
  const fileTitle = inferTitleFromFilename(localScanState.protectedFile?.name || "");
  if (protectedTitle) return protectedTitle;
  if (webTitle && webTitle !== "Project Monsoon") return webTitle;
  return fileTitle || webTitle;
}

function syncProtectedWorkToDiscovery() {
  const inferredTitle = getProtectedDiscoveryTitle();
  const protectedTitleInput = $("#protected-title-input");
  const webTitleInput = $("#web-title-input");
  const protectedAliasInput = $("#protected-alias-input");
  const webAliasInput = $("#web-alias-input");

  if (protectedTitleInput && inferredTitle && !protectedTitleInput.value.trim()) {
    protectedTitleInput.value = inferredTitle;
  }
  if (webTitleInput && inferredTitle) {
    webTitleInput.value = inferredTitle;
  }
  if (protectedAliasInput && webAliasInput && protectedAliasInput.value.trim()) {
    webAliasInput.value = protectedAliasInput.value.trim();
  }

  return inferredTitle;
}

function hashString(input) {
  let hash = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).toUpperCase().padStart(8, "0");
}

function buildDnaId(vectors, duration) {
  const signature = vectors
    .map((vector) => vector.slice(0, 42).map((value) => Math.round((value + 1) * 99)).join(","))
    .join("|");
  const hash = hashString(`${signature}|${duration.toFixed(2)}`);
  return `CS-DNA ${hash.slice(0, 4)} ${hash.slice(4, 8)} ${hashString(signature).slice(0, 4)}`;
}

function loadVideoForSampling(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement("video");
    const cleanup = () => {
      video.removeEventListener("loadedmetadata", onLoaded);
      video.removeEventListener("error", onError);
      window.clearTimeout(timer);
    };
    const onLoaded = () => {
      cleanup();
      if (!Number.isFinite(video.duration) || video.duration <= 0 || !video.videoWidth || !video.videoHeight) {
        URL.revokeObjectURL(url);
        reject(new Error("The browser could not read this video's duration or frames."));
        return;
      }
      resolve({ video, url });
    };
    const onError = () => {
      cleanup();
      URL.revokeObjectURL(url);
      reject(new Error("This video format could not be decoded here. Try MP4/H.264 or WebM."));
    };
    const timer = window.setTimeout(() => {
      cleanup();
      URL.revokeObjectURL(url);
      reject(new Error("Video metadata took too long to load."));
    }, 12000);

    video.muted = true;
    video.preload = "metadata";
    video.playsInline = true;
    video.addEventListener("loadedmetadata", onLoaded, { once: true });
    video.addEventListener("error", onError, { once: true });
    video.src = url;
    video.load();
  });
}

function seekVideo(video, time) {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      video.removeEventListener("seeked", onSeeked);
      video.removeEventListener("error", onError);
      window.clearTimeout(timer);
    };
    const onSeeked = () => {
      cleanup();
      resolve();
    };
    const onError = () => {
      cleanup();
      reject(new Error("A frame could not be sampled from this video."));
    };
    const timer = window.setTimeout(() => {
      cleanup();
      resolve();
    }, 2600);

    video.addEventListener("seeked", onSeeked, { once: true });
    video.addEventListener("error", onError, { once: true });
    video.currentTime = clamp(time, 0, Math.max(0, video.duration - 0.04));
  });
}

function canvasVector(context) {
  const image = context.getImageData(0, 0, LOCAL_FRAME_WIDTH, LOCAL_FRAME_HEIGHT).data;
  const values = [];
  let sum = 0;
  for (let index = 0; index < image.length; index += 4) {
    const luminance = (0.2126 * image[index] + 0.7152 * image[index + 1] + 0.0722 * image[index + 2]) / 255;
    values.push(luminance);
    sum += luminance;
  }

  const mean = sum / values.length;
  const centered = values.map((value) => value - mean);
  const norm = Math.sqrt(centered.reduce((total, value) => total + value * value, 0)) || 1;
  return centered.map((value) => value / norm);
}

function buildTemporalProfile(vectors) {
  const profile = [];
  for (let index = 1; index < vectors.length; index += 1) {
    profile.push(1 - cosineSimilarity(vectors[index - 1], vectors[index]));
  }
  return profile;
}

async function extractLocalDna(file) {
  const { video, url } = await loadVideoForSampling(file);
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  canvas.width = LOCAL_FRAME_WIDTH;
  canvas.height = LOCAL_FRAME_HEIGHT;

  try {
    const sampleCount = Math.min(LOCAL_FRAME_SAMPLES, Math.max(4, Math.floor(video.duration)));
    const frames = [];
    for (let index = 0; index < sampleCount; index += 1) {
      const progress = (index + 1) / (sampleCount + 1);
      await seekVideo(video, video.duration * progress);
      context.drawImage(video, 0, 0, LOCAL_FRAME_WIDTH, LOCAL_FRAME_HEIGHT);
      frames.push(canvasVector(context));
    }

    return {
      fileName: file.name,
      fileSize: file.size,
      duration: video.duration,
      width: video.videoWidth,
      height: video.videoHeight,
      sampleCount: frames.length,
      visualVectors: frames,
      temporalProfile: buildTemporalProfile(frames),
      dnaId: buildDnaId(frames, video.duration)
    };
  } finally {
    URL.revokeObjectURL(url);
  }
}

function cosineSimilarity(first, second) {
  const length = Math.min(first.length, second.length);
  if (!length) return 0;
  let dot = 0;
  for (let index = 0; index < length; index += 1) {
    dot += first[index] * second[index];
  }
  return clamp(dot, 0, 1);
}

function resampleArray(values, length) {
  if (!values.length) return Array.from({ length }, () => 0);
  if (length <= 1) return [values[0]];
  return Array.from({ length }, (_, index) => {
    const position = (index / (length - 1)) * (values.length - 1);
    const left = Math.floor(position);
    const right = Math.min(values.length - 1, left + 1);
    const mix = position - left;
    return values[left] * (1 - mix) + values[right] * mix;
  });
}

function temporalSimilarity(protectedDna, candidateDna) {
  const length = Math.max(protectedDna.temporalProfile.length, candidateDna.temporalProfile.length, 1);
  const first = resampleArray(protectedDna.temporalProfile, length);
  const second = resampleArray(candidateDna.temporalProfile, length);
  const averageDelta = first.reduce((total, value, index) => total + Math.abs(value - second[index]), 0) / length;
  return clamp(1 - averageDelta * 2.2, 0, 1);
}

function alignFrames(protectedDna, candidateDna) {
  const matches = candidateDna.visualVectors.map((candidateVector) => {
    let bestScore = 0;
    let bestIndex = 0;
    protectedDna.visualVectors.forEach((protectedVector, index) => {
      const score = cosineSimilarity(protectedVector, candidateVector);
      if (score > bestScore) {
        bestScore = score;
        bestIndex = index;
      }
    });
    return { score: bestScore, index: bestIndex };
  });

  const mean = matches.reduce((total, item) => total + item.score, 0) / Math.max(matches.length, 1);
  const orderedPairs = matches.slice(1).filter((item, index) => item.index >= matches[index].index).length;
  const order = matches.length > 1 ? orderedPairs / (matches.length - 1) : 1;
  const coverage = new Set(matches.map((item) => item.index)).size / Math.max(protectedDna.visualVectors.length, 1);
  const scene = clamp(mean * 0.72 + order * 0.2 + coverage * 0.08, 0, 1);

  return { mean, order, coverage, scene };
}

function compareLocalDna(protectedDna, candidateDna) {
  const alignment = alignFrames(protectedDna, candidateDna);
  const durationScore = Math.min(protectedDna.duration, candidateDna.duration) / Math.max(protectedDna.duration, candidateDna.duration);
  const temporalScore = temporalSimilarity(protectedDna, candidateDna);

  const weights = {
    visual: 0.48,
    scene: 0.28,
    temporal: 0.14,
    metadata: 0.1
  };

  if (durationScore < 0.76 && alignment.scene > 0.72) {
    weights.scene += 0.08;
    weights.visual -= 0.04;
    weights.metadata -= 0.04;
  }

  if (alignment.mean < 0.76 && temporalScore > 0.72) {
    weights.scene += 0.06;
    weights.temporal += 0.04;
    weights.visual -= 0.1;
  }

  const confidence =
    alignment.mean * weights.visual +
    alignment.scene * weights.scene +
    temporalScore * weights.temporal +
    durationScore * weights.metadata;
  const lowCoverageOnly = alignment.coverage < 0.45 && alignment.mean < 0.93;
  const boundedConfidence = lowCoverageOnly ? Math.min(confidence, 0.84) : confidence;
  const decision = boundedConfidence >= 0.86 ? "Match" : boundedConfidence >= 0.72 ? "Review" : "No match";
  const signals = {
    Visual: Math.round(alignment.mean * 100),
    Scene: Math.round(alignment.scene * 100),
    Temporal: Math.round(temporalScore * 100),
    Duration: Math.round(durationScore * 100),
    Coverage: Math.round(alignment.coverage * 100)
  };
  const reasons = [
    `Visual frame signature ${signals.Visual}%`,
    `Scene order and coverage ${signals.Scene}%`,
    `Temporal motion profile ${signals.Temporal}%`,
    durationScore < 0.76 ? "Duration mismatch keeps the decision gated" : "Duration profile supports the comparison",
    decision === "Match"
      ? "Candidate crossed the high-confidence threshold"
      : decision === "Review"
        ? "Evidence is meaningful but needs human review"
        : "Evidence is below same-content threshold"
  ];

  return {
    fileName: candidateDna.fileName,
    fileSize: candidateDna.fileSize,
    duration: candidateDna.duration,
    dnaId: candidateDna.dnaId,
    confidence: Math.round(boundedConfidence * 1000) / 10,
    decision,
    signals,
    weights: Object.fromEntries(Object.entries(weights).map(([key, value]) => [key, Math.round(value * 100)])),
    reasons
  };
}

async function generateLocalDna() {
  if (!localScanState.protectedFile) {
    setLocalStatus("Needs original", "warning", "Select the protected video first.");
    return;
  }

  localScanState.busy = true;
  state.stage = "dna";
  setLocalStatus("Extracting DNA", "warning");

  try {
    localScanState.protectedDna = await extractLocalDna(localScanState.protectedFile);
    localScanState.error = "";
    state.stage = "dna";
    setLocalStatus("DNA ready", "ready");
  } catch (error) {
    localScanState.protectedDna = null;
    setLocalStatus("Decode failed", "danger", error.message);
  } finally {
    localScanState.busy = false;
    renderTimeline();
    renderLocalScanner();
  }
}

async function runBackendLocalScan() {
  const backendBase = "http://127.0.0.1:8001";
  const formData = new FormData();
  formData.append("protected", localScanState.protectedFile);
  localScanState.candidateFiles.forEach((file) => formData.append("candidates", file));

  const response = await fetch(`${backendBase}/api/scan`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(`Backend scan failed (${response.status})`);
  }

  const payload = await response.json();
  const analysesByName = new Map(
    (payload.investigation?.candidateAnalyses || []).map((item) => [item.fileName, item.analysis])
  );
  const results = (payload.results || []).map((item) => ({
    fileName: item.fileName || "unknown",
    fileSize: item.fileSize || 0,
    duration: Number(item.duration || 0),
    dnaId: item.dnaId || "API-DNA",
    sampledFrames: item.sampledFrames || 0,
    confidence: Number(item.confidence || 0),
    decision: item.decision || "Review",
    signals: item.signals || { Visual: 0, Scene: 0, Temporal: 0, Duration: 0, Coverage: 0 },
    weights: item.weights || { visual: 0, scene: 0, temporal: 0, metadata: 0 },
    reasons: item.reasons || ["Computed by the CineShield backend scan pipeline."],
    sourceUrl: item.sourceUrl || "",
    sourceBytes: Number(item.sourceBytes || 0),
    accessType: item.accessType || "Uploaded candidate file",
    evidenceLevel: Number(item.evidenceLevel || 4),
    evidenceLevelLabel: item.evidenceLevelLabel || "Multimodal match",
    analysis: analysesByName.get(item.fileName) || null
  }));

  localScanState.results = results.sort((first, second) => second.confidence - first.confidence);
  localScanState.investigation = payload.investigation || null;
  localScanState.resultSource = "local";
  if (localScanState.results.length) {
    state.selectedCandidateId = "live-0";
    state.selectedNodeId = "live-0";
    state.selectedEdgeId = null;
  }
  localScanState.error = "";
  state.stage = localScanState.results.some((item) => item.decision !== "No match") ? "investigate" : "verify";
  setLocalStatus("Real scan complete", "ready");
  return true;
}

function hasNumericValue(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function hasContentVerification(lead) {
  return hasNumericValue(lead?.contentMatchScore);
}

function countContentVerifiedDiscoveryCandidates() {
  return webDiscoveryState.candidates.filter((lead) => hasContentVerification(lead)).length;
}

function selectFirstVerifiedDiscoveryCandidate() {
  const index = webDiscoveryState.candidates.findIndex((lead) => hasContentVerification(lead));
  if (index < 0) return false;

  state.selectedCandidateId = `disc-${index}`;
  state.selectedNodeId = `disc-${index}`;
  state.selectedEdgeId = null;
  state.stage = "investigate";
  state.caseStatus = "Human review";
  return true;
}

function dedupeReasons(reasons) {
  return Array.from(new Set((reasons || []).filter(Boolean)));
}

function contentVerificationBoundary(decision) {
  if (decision === "Match") {
    return "Content DNA verified a high-confidence same-work candidate, but response still requires authorized human review.";
  }
  if (decision === "Review") {
    return "Content DNA found meaningful evidence, but confidence stays in the human-review band before any response.";
  }
  return "Content DNA rejected this candidate as below the same-content threshold; keep only as a monitored lead.";
}

function attachUrlVerificationToDiscovery(discoveryTargets, payload, results) {
  if (!Array.isArray(discoveryTargets) || !discoveryTargets.length) return;

  const targetByUrl = new Map();
  const targetByFileName = new Map();
  discoveryTargets.forEach((target) => {
    if (target.url) targetByUrl.set(target.url, target);
  });

  (payload.downloadedCandidates || []).forEach((downloaded) => {
    const target = targetByUrl.get(downloaded.url);
    if (!target) return;
    if (downloaded.finalUrl) targetByUrl.set(downloaded.finalUrl, target);
    if (downloaded.fileName) targetByFileName.set(downloaded.fileName, target);
  });

  (payload.rejectedCandidates || []).forEach((rejected) => {
    const target = targetByUrl.get(rejected.url);
    const lead = target ? webDiscoveryState.candidates[target.candidateIndex] : null;
    if (!lead) return;

    lead.mediaAccessStatus = "MEDIA_REFERENCE_BLOCKED";
    lead.verificationStatus = "Media verification blocked";
    lead.rejectedMediaError = rejected.error || "Candidate media was rejected by the verification boundary.";
    lead.evidenceLevel = Math.max(Number(lead.evidenceLevel || 2), 2);
    lead.evidenceLevelLabel = "Media reference";
    lead.evidenceBoundary = "A public media reference was discovered, but CineShield did not ingest it because the verification boundary blocked it.";
    lead.reasons = dedupeReasons([
      ...(Array.isArray(lead.reasons) ? lead.reasons : []),
      lead.rejectedMediaError
    ]);
  });

  results.forEach((result) => {
    const target =
      targetByFileName.get(result.fileName) ||
      targetByUrl.get(result.sourceUrl) ||
      discoveryTargets.find((item) => item.url === result.sourceUrl);
    const lead = target ? webDiscoveryState.candidates[target.candidateIndex] : null;
    if (!lead) return;

    const confidence = Number(result.confidence || 0);
    const decision = result.decision || "Review";
    const priorRisk = Number(lead.riskScore ?? lead.score ?? 0);
    const nextRisk =
      decision === "Match"
        ? Math.max(priorRisk, 90)
        : decision === "Review"
          ? Math.max(Math.min(priorRisk, 69), 45)
          : Math.min(priorRisk, 24);

    lead.contentMatchScore = confidence;
    lead.finalDecisionStage = "CONTENT_VERIFIED";
    lead.decision = decision;
    lead.riskScore = nextRisk;
    lead.score = nextRisk;
    lead.riskLevel = decision === "Match" ? "Critical" : decision === "Review" ? "Review" : "Low";
    lead.sourceClass = decision === "Match" ? "VERIFIED_CANDIDATE" : lead.sourceClass || "UNKNOWN";
    lead.mediaAccessStatus = "MEDIA_VERIFIED";
    lead.verificationStatus = `Content DNA ${decision}`;
    lead.accessType = result.accessType || "Authorized direct public media URL";
    lead.evidenceLevel = 4;
    lead.evidenceLevelLabel = "Multimodal match";
    lead.candidateFileName = result.fileName;
    lead.candidateDnaId = result.dnaId;
    lead.verifiedMediaUrl = result.sourceUrl || target.url;
    lead.sourceBytes = Number(result.sourceBytes || result.fileSize || 0);
    lead.contentSignals = result.signals || {};
    lead.contentWeights = result.weights || {};
    lead.contentReasons = Array.isArray(result.reasons) ? result.reasons : [];
    lead.contentAnalysis = result.analysis || null;
    lead.contentVerifiedAt = new Date().toISOString();
    lead.evidenceBoundary = contentVerificationBoundary(decision);
    lead.reasons = dedupeReasons([
      ...(Array.isArray(lead.reasons) ? lead.reasons : []),
      ...(Array.isArray(result.reasons) ? result.reasons : []),
      lead.evidenceBoundary
    ]);
  });

  webDiscoveryState.contentVerifiedCount = countContentVerifiedDiscoveryCandidates();
  if (webDiscoveryState.coverage) {
    webDiscoveryState.coverage = {
      ...webDiscoveryState.coverage,
      contentVerified: webDiscoveryState.contentVerifiedCount,
      verifiedMatches: webDiscoveryState.candidates.filter((lead) => hasContentVerification(lead) && lead.decision === "Match").length,
      mediaCandidates: discoveryTargets.length
    };
  }

  const matches = webDiscoveryState.candidates.filter((lead) => hasContentVerification(lead) && lead.decision === "Match").length;
  const reviews = webDiscoveryState.candidates.filter((lead) => hasContentVerification(lead) && lead.decision === "Review").length;
  const rejects = webDiscoveryState.candidates.filter((lead) => hasContentVerification(lead) && lead.decision === "No match").length;
  webDiscoveryState.summary =
    `${webDiscoveryState.candidates.length} non-authorized candidate lead${webDiscoveryState.candidates.length === 1 ? "" : "s"} queued; ` +
    `${discoveryTargets.length} direct public media reference${discoveryTargets.length === 1 ? "" : "s"} entered authorized Content DNA verification; ` +
    `${matches} match${matches === 1 ? "" : "es"}, ${reviews} review, ${rejects} reject${rejects === 1 ? "" : "s"}.`;
}

async function runBackendUrlCandidateScan(candidateUrls, authorizationConfirmed, options = {}) {
  const backendBase = "http://127.0.0.1:8001";
  const formData = new FormData();
  formData.append("protected", localScanState.protectedFile);
  formData.append(
    "request",
    JSON.stringify({
      candidateUrls,
      authorizationConfirmed
    })
  );

  const response = await fetch(`${backendBase}/api/scan/url-candidates`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    let detail = `URL candidate scan failed (${response.status})`;
    try {
      const errorPayload = await response.json();
      detail = errorPayload.detail || detail;
    } catch {
      detail = `URL candidate scan failed (${response.status})`;
    }
    throw new Error(detail);
  }

  const payload = await response.json();
  const analysesByName = new Map(
    (payload.investigation?.candidateAnalyses || []).map((item) => [item.fileName, item.analysis])
  );
  const results = (payload.results || []).map((item) => ({
    fileName: item.fileName || "url candidate",
    fileSize: Number(item.sourceBytes || item.fileSize || 0),
    duration: Number(item.duration || 0),
    dnaId: item.dnaId || "URL-DNA",
    sampledFrames: item.sampledFrames || 0,
    confidence: Number(item.confidence || 0),
    decision: item.decision || "Review",
    signals: item.signals || { Visual: 0, Scene: 0, Temporal: 0, Duration: 0, Coverage: 0 },
    weights: item.weights || { visual: 0, scene: 0, temporal: 0, metadata: 0 },
    reasons: item.reasons || ["Computed from authorized direct URL candidate media."],
    sourceUrl: item.sourceUrl || "",
    sourceBytes: Number(item.sourceBytes || 0),
    accessType: item.accessType || "Authorized direct public media URL",
    evidenceLevel: Number(item.evidenceLevel || 4),
    evidenceLevelLabel: item.evidenceLevelLabel || "Multimodal match",
    analysis: analysesByName.get(item.fileName) || null
  }));

  localScanState.results = results.sort((first, second) => second.confidence - first.confidence);
  localScanState.investigation = payload.investigation || null;
  localScanState.downloadedUrlCandidates = payload.downloadedCandidates || [];
  localScanState.rejectedUrlCandidates = payload.rejectedCandidates || [];
  localScanState.resultSource = Array.isArray(options.discoveryTargets) && options.discoveryTargets.length ? "discovery-url" : "url";
  if (Array.isArray(options.discoveryTargets) && options.discoveryTargets.length) {
    attachUrlVerificationToDiscovery(options.discoveryTargets, payload, localScanState.results);
  }
  localScanState.selectedResultIndex = 0;
  if (localScanState.results.length) {
    if (!selectFirstVerifiedDiscoveryCandidate()) {
      state.selectedCandidateId = "live-0";
      state.selectedNodeId = "live-0";
      state.selectedEdgeId = null;
    }
  }
  localScanState.error = localScanState.rejectedUrlCandidates.length
    ? `${localScanState.rejectedUrlCandidates.length} URL candidate${localScanState.rejectedUrlCandidates.length === 1 ? "" : "s"} blocked by verification boundary.`
    : "";
  state.stage = localScanState.results.some((item) => item.decision !== "No match") ? "investigate" : "verify";
  setLocalStatus(localScanState.results.length ? "URL scan complete" : "No URL media", localScanState.results.length ? "ready" : "warning");
  return true;
}

async function runLocalScan() {
  if (!localScanState.protectedFile) {
    setLocalStatus("Needs original", "warning", "Select the protected video first.");
    return;
  }

  if (!localScanState.candidateFiles.length) {
    setLocalStatus("Needs candidates", "warning", "Select one or more candidate videos.");
    return;
  }

  localScanState.busy = true;
  localScanState.results = [];
  localScanState.downloadedUrlCandidates = [];
  localScanState.rejectedUrlCandidates = [];
  localScanState.selectedResultIndex = 0;
  localScanState.resultSource = "";
  state.stage = "discover";
  setLocalStatus("Preparing scan", "warning");

  try {
    await runBackendLocalScan();
  } catch (error) {
    setLocalStatus("Backend unavailable", "danger", "Start the local backend to run the real scan. The dashboard will not silently fall back to demo data.");
  } finally {
    localScanState.busy = false;
    renderTimeline();
    renderLocalScanner();
  }
}

async function runUrlCandidateScan() {
  if (!localScanState.protectedFile) {
    setLocalStatus("Needs original", "warning", "Select the protected video first.");
    return;
  }

  const candidateUrls = parseListInput($("#candidate-url-input")?.value || "");
  if (!candidateUrls.length) {
    setLocalStatus("Needs URL media", "warning", "Paste one or more direct public candidate video URLs.");
    return;
  }

  const authorizationConfirmed = Boolean($("#url-auth-confirm")?.checked);
  if (!authorizationConfirmed) {
    setLocalStatus("Needs permission", "warning", "Confirm you are authorized to process the candidate media URLs.");
    return;
  }

  localScanState.busy = true;
  localScanState.results = [];
  localScanState.downloadedUrlCandidates = [];
  localScanState.rejectedUrlCandidates = [];
  localScanState.selectedResultIndex = 0;
  localScanState.resultSource = "";
  state.stage = "discover";
  setLocalStatus("Fetching URL media", "warning");
  $("#scan-status").textContent = "Verifying URLs";
  $("#scan-status").className = "status-pill warning";
  setScanProgress(35, "URL candidates entering Content DNA", "Direct public media files are being fetched under the authorization boundary.");
  renderTimeline();

  try {
    await runBackendUrlCandidateScan(candidateUrls, authorizationConfirmed);
    setScanProgress(100, "URL candidate verification complete", "Accessible candidates were compared with the protected work using Content DNA.");
    $("#scan-status").textContent = localScanState.results.length ? "Complete" : "No media";
    $("#scan-status").className = `status-pill ${localScanState.results.length ? "ready" : "warning"}`;
  } catch (error) {
    setScanProgress(100, "URL candidate verification blocked", error.message);
    $("#scan-status").textContent = "Blocked";
    $("#scan-status").className = "status-pill danger";
    setLocalStatus("URL scan blocked", "danger", error.message);
  } finally {
    localScanState.busy = false;
    renderAll();
  }
}

function getDiscoveredDirectMediaTargets() {
  const directVideoPattern = /\.(mp4|m4v|mov|webm|mkv|avi)(?:[?#]|$)/i;
  const targets = [];
  const seen = new Set();
  webDiscoveryState.candidates.forEach((lead, candidateIndex) => {
    (lead.mediaReferences || []).forEach((reference, referenceIndex) => {
      const url = reference.url || "";
      if (directVideoPattern.test(url) && !seen.has(url)) {
        seen.add(url);
        targets.push({
          url,
          candidateIndex,
          referenceIndex,
          candidateId: lead.id || `DISC-${candidateIndex + 1}`,
          pageUrl: lead.url || "",
          host: lead.host || reference.host || ""
        });
      }
    });
  });
  return targets;
}

function getDiscoveredDirectMediaUrls() {
  return getDiscoveredDirectMediaTargets().map((target) => target.url);
}

async function searchInternetForProtectedWork() {
  const title = syncProtectedWorkToDiscovery();
  if (!title) {
    setLocalStatus("Needs title", "warning", "Upload a protected video or enter the internet discovery title.");
    return;
  }

  setLocalStatus("Searching internet", "warning", "Web discovery uses the title and aliases first; Content DNA verification runs after candidate media is available.");
  $("#scan-status").textContent = "Searching";
  $("#scan-status").className = "status-pill warning";
  setScanProgress(22, "Internet discovery starting", `Searching public indexes for ${title} and filtering authorized domains.`);
  document.querySelector("#discovery")?.scrollIntoView({ behavior: "smooth", block: "start" });
  await runWebSearch({ blind: true });

  const blindVerifyRequested = Boolean($("#blind-verify-confirm")?.checked);
  const discoveredMediaTargets = getDiscoveredDirectMediaTargets();
  const discoveredMediaUrls = discoveredMediaTargets.map((target) => target.url);
  if (blindVerifyRequested && !localScanState.protectedFile) {
    setLocalStatus("Needs original", "warning", "Blind media verification needs the protected video upload.");
    return;
  }
  if (blindVerifyRequested && localScanState.protectedFile && discoveredMediaUrls.length) {
    setLocalStatus("Verifying discovered media", "warning", `${discoveredMediaUrls.length} direct public media reference${discoveredMediaUrls.length === 1 ? "" : "s"} discovered by CineShield.`);
    setScanProgress(72, "Content DNA verification running", "Discovered direct media references are being compared against the protected work.");
    try {
      await runBackendUrlCandidateScan(discoveredMediaUrls, true, { discoveryTargets: discoveredMediaTargets });
      setScanProgress(100, localScanState.results.length ? "Blind media verification complete" : "No discovered media verified", "CineShield only verified direct public media URLs that passed the authorization boundary.");
      renderAll();
      return;
    } catch (error) {
      setLocalStatus("Blind verification blocked", "danger", error.message);
      setScanProgress(100, "Blind media verification blocked", error.message);
      return;
    }
  }

  if (webDiscoveryState.setupRequired) {
    setLocalStatus("Search key needed", "warning", webDiscoveryState.setupMessage);
  } else if (webDiscoveryState.candidates.length) {
    const mediaCopy = blindVerifyRequested && !discoveredMediaUrls.length
      ? " No direct public media reference was found for automatic DNA verification."
      : "";
    setLocalStatus("Internet leads ready", "ready", `${webDiscoveryState.candidates.length} candidate lead${webDiscoveryState.candidates.length === 1 ? "" : "s"} found in public discovery.${mediaCopy}`);
  } else if (webDiscoveryState.searchErrors.length) {
    setLocalStatus("Provider error", "warning", webDiscoveryState.searchErrors[0]);
  } else if (webDiscoveryState.error) {
    setLocalStatus("Internet search blocked", "danger", webDiscoveryState.error);
  } else {
    setLocalStatus("No web leads", "warning", webDiscoveryState.summary || "No public leads were returned for this title.");
  }
}

async function runBackendWebDiscovery(payload) {
  const backendBase = "http://127.0.0.1:8001";
  const response = await fetch(`${backendBase}/api/discovery/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Discovery scan failed (${response.status})`);
  }

  return response.json();
}

async function runBackendWebSearch(payload) {
  const backendBase = "http://127.0.0.1:8001";
  const response = await fetch(`${backendBase}/api/discovery/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Web index discovery failed (${response.status})`);
  }

  return response.json();
}

function readDiscoveryForm() {
  const protectedTitle = $("#protected-title-input")?.value.trim() || "";
  const webTitle = $("#web-title-input")?.value.trim() || "";
  const protectedAliases = parseListInput($("#protected-alias-input")?.value || "");
  const rawWebAliases = $("#web-alias-input")?.value || "";
  const seedUrls = uniqueList([
    ...parseListInput($("#web-seed-input")?.value || ""),
    ...parsePartnerSourceFeed($("#partner-source-input")?.value || "")
  ]);
  const webAliases =
    protectedTitle && rawWebAliases.trim() === "Monsoon, Project X"
      ? []
      : parseListInput(rawWebAliases);

  return {
    title: protectedTitle && (!webTitle || webTitle === "Project Monsoon") ? protectedTitle : webTitle,
    aliases: protectedAliases.length ? protectedAliases : webAliases,
    authorizedDomains: parseListInput($("#authorized-domain-input")?.value || ""),
    sourceDomains: parseListInput($("#source-domain-input")?.value || ""),
    riskTerms: parseListInput($("#risk-term-input")?.value || "movierulz, netmirror, ibomma, tamilrockers, filmyzilla, 9xmovies, telegram, torrent"),
    providers: parseListInput($("#discovery-provider-input")?.value || "brave, bing, google, commoncrawl"),
    expandDepth: readNumberInput("#expand-depth-input", 1, 0, 2),
    expandPages: readNumberInput("#expand-pages-input", 16, 0, 32),
    perDomainPageLimit: readNumberInput("#per-domain-pages-input", 4, 1, 10),
    seedUrls
  };
}

function resetWebDiscoveryRun(summary) {
  webDiscoveryState.busy = true;
  localScanState.results = [];
  localScanState.investigation = null;
  localScanState.downloadedUrlCandidates = [];
  localScanState.rejectedUrlCandidates = [];
  localScanState.selectedResultIndex = 0;
  localScanState.resultSource = "";
  webDiscoveryState.candidates = [];
  webDiscoveryState.excludedCandidates = [];
  webDiscoveryState.sourcesScanned = [];
  webDiscoveryState.mediaReferenceCount = 0;
  webDiscoveryState.verifiedMediaCount = 0;
  webDiscoveryState.authorizedExcluded = 0;
  webDiscoveryState.searchQueries = [];
  webDiscoveryState.searchResultCount = 0;
  webDiscoveryState.searchErrors = [];
  webDiscoveryState.sourceFocusDomains = [];
  webDiscoveryState.providerResults = [];
  webDiscoveryState.coverage = null;
  webDiscoveryState.expansionUrls = [];
  webDiscoveryState.contentVerifiedCount = 0;
  webDiscoveryState.setupRequired = false;
  webDiscoveryState.setupMessage = "";
  webDiscoveryState.summary = summary;
  webDiscoveryState.error = "";
  state.stage = "discover";
  renderTimeline();
}

function applyDiscoveryPayload(payload, fallbackTitle) {
  webDiscoveryState.candidates = payload.candidates || [];
  webDiscoveryState.excludedCandidates = payload.excludedCandidates || [];
  webDiscoveryState.sourcesScanned = payload.sourcesScanned || [];
  webDiscoveryState.query = payload.query || fallbackTitle;
  webDiscoveryState.mediaReferenceCount = Number(payload.mediaReferenceCount || 0);
  webDiscoveryState.verifiedMediaCount = Number(payload.verifiedMediaCount || 0);
  webDiscoveryState.authorizedExcluded = Number(payload.authorizedExcluded || 0);
  webDiscoveryState.provider = payload.provider || "seed";
  webDiscoveryState.providerStatus = payload.providerStatus || "seed_only";
  webDiscoveryState.setupRequired = Boolean(payload.setupRequired);
  webDiscoveryState.setupMessage = payload.setupMessage || "";
  webDiscoveryState.searchQueries = payload.searchQueries || [];
  webDiscoveryState.searchResultCount = Number(payload.searchResultCount || 0);
  webDiscoveryState.searchErrors = payload.searchErrors || [];
  webDiscoveryState.sourceFocusDomains = payload.sourceFocusDomains || [];
  webDiscoveryState.providerResults = payload.providerResults || [];
  webDiscoveryState.coverage = payload.coverage || null;
  webDiscoveryState.expansionUrls = payload.expansionUrls || [];
  webDiscoveryState.contentVerifiedCount = Number(payload.contentVerifiedCount || 0);
  webDiscoveryState.lastRunAt = new Date();

  const seedCount = Number(payload.seedCount || webDiscoveryState.sourcesScanned.length || 0);
  const candidateCount = Number(payload.candidateCount || webDiscoveryState.candidates.length || 0);
  const seedCopy = seedCount
    ? `${seedCount} public page${seedCount === 1 ? "" : "s"} deep-scanned`
    : "no public pages deep-scanned yet";
  const searchCopy = webDiscoveryState.searchResultCount
    ? `${webDiscoveryState.searchResultCount} search result${webDiscoveryState.searchResultCount === 1 ? "" : "s"} collected`
    : webDiscoveryState.searchErrors.length
      ? `${webDiscoveryState.searchErrors.length} provider/query error${webDiscoveryState.searchErrors.length === 1 ? "" : "s"}`
      : "search index not queried";
  const coverageCopy = webDiscoveryState.coverage
    ? `${webDiscoveryState.coverage.domainsEvaluated || 0} domain${webDiscoveryState.coverage.domainsEvaluated === 1 ? "" : "s"} evaluated with ${webDiscoveryState.coverage.highRiskLeads || 0} high-risk lead${webDiscoveryState.coverage.highRiskLeads === 1 ? "" : "s"}`
    : "";

  webDiscoveryState.summary = webDiscoveryState.setupRequired
    ? webDiscoveryState.setupMessage
    : `${candidateCount} non-authorized candidate lead${candidateCount === 1 ? "" : "s"} queued; ${searchCopy}; ${seedCopy}; ${coverageCopy ? `${coverageCopy}; ` : ""}${webDiscoveryState.authorizedExcluded} authorized source${webDiscoveryState.authorizedExcluded === 1 ? "" : "s"} excluded.`;

  if (webDiscoveryState.monitorActive) {
    recordMonitorRun();
  }

  state.stage = webDiscoveryState.candidates.length ? "verify" : "discover";
  if (webDiscoveryState.candidates.length) {
    state.selectedCandidateId = "disc-0";
    state.selectedNodeId = "disc-0";
    state.selectedEdgeId = null;
    state.caseStatus = "Human review";
  }
}

async function runWebDiscovery() {
  const { title, aliases, authorizedDomains, seedUrls } = readDiscoveryForm();

  if (!title) {
    setWebDiscoveryStatus("Needs title", "warning", "Add the protected title.");
    return;
  }

  if (!seedUrls.length) {
    setWebDiscoveryStatus("Needs seeds", "warning", "Paste one or more public source URLs.");
    return;
  }

  webDiscoveryState.query = title;
  resetWebDiscoveryRun("Scanning public source metadata...");
  state.stage = "discover";
  setWebDiscoveryStatus("Scanning", "warning");
  $("#scan-status").textContent = "Scanning";
  $("#scan-status").className = "status-pill warning";
  setScanProgress(30, "Public source discovery running", "Fetching public HTML metadata and extracting candidate links.");
  renderTimeline();

  try {
    const payload = await runBackendWebDiscovery({ title, aliases, authorizedDomains, seedUrls, maxPages: 8 });
    applyDiscoveryPayload(payload, title);
    setScanProgress(100, "Public discovery complete", webDiscoveryState.summary);
    $("#scan-status").textContent = "Complete";
    $("#scan-status").className = "status-pill ready";
    setWebDiscoveryStatus("Complete", "ready");
  } catch (error) {
    webDiscoveryState.summary = "Discovery connector could not complete.";
    setScanProgress(100, "Public discovery blocked", "Check backend status, network access, or seed URLs.");
    $("#scan-status").textContent = "Blocked";
    $("#scan-status").className = "status-pill danger";
    setWebDiscoveryStatus("Blocked", "danger", error.message);
  } finally {
    webDiscoveryState.busy = false;
    renderAll();
  }
}

async function runWebSearch(options = {}) {
  const { title, aliases, authorizedDomains, sourceDomains, riskTerms, providers, expandDepth, expandPages, perDomainPageLimit } = readDiscoveryForm();
  const blindSearch = Boolean(options.blind);
  const activeSourceDomains = blindSearch ? [] : sourceDomains;

  if (!title) {
    setWebDiscoveryStatus("Needs title", "warning", "Add the protected title.");
    return;
  }

  webDiscoveryState.query = title;
  resetWebDiscoveryRun("Searching public web index...");
  setWebDiscoveryStatus("Searching", "warning");
  $("#scan-status").textContent = "Searching";
  $("#scan-status").className = "status-pill warning";
  setScanProgress(
    24,
    blindSearch ? "Blind public web discovery running" : "Public web-index discovery running",
    blindSearch
      ? "Searching generated title and alias queries across configured public indexes, then expanding reachable public links."
      : "Querying indexed public pages, excluding authorized domains, and preparing a verification queue."
  );

  try {
    const payload = await runBackendWebSearch({
      title,
      aliases,
      authorizedDomains,
      sourceDomains: activeSourceDomains,
      riskTerms,
      providers,
      maxResults: 12,
      deepScanPages: 6,
      expandDepth,
      expandPages,
      perDomainPageLimit,
      country: "IN",
      searchLang: "en"
    });
    applyDiscoveryPayload(payload, title);

    if (webDiscoveryState.setupRequired) {
      setScanProgress(100, "Search provider needs key", webDiscoveryState.setupMessage);
      $("#scan-status").textContent = "Key needed";
      $("#scan-status").className = "status-pill warning";
      setWebDiscoveryStatus("Needs key", "warning");
      return;
    }

    const label = webDiscoveryState.candidates.length ? "Web discovery complete" : "No public leads found";
    setScanProgress(100, label, webDiscoveryState.summary);
    $("#scan-status").textContent = webDiscoveryState.candidates.length ? "Complete" : "No leads";
    $("#scan-status").className = `status-pill ${webDiscoveryState.candidates.length ? "ready" : "warning"}`;
    setWebDiscoveryStatus(webDiscoveryState.searchErrors.length ? "Partial" : "Complete", webDiscoveryState.searchErrors.length ? "warning" : "ready");
  } catch (error) {
    webDiscoveryState.summary = "Search connector could not complete.";
    setScanProgress(100, "Web-index discovery blocked", "Check backend status, network access, or the search provider key.");
    $("#scan-status").textContent = "Blocked";
    $("#scan-status").className = "status-pill danger";
    setWebDiscoveryStatus("Blocked", "danger", error.message);
  } finally {
    webDiscoveryState.busy = false;
    renderAll();
  }
}

function runDiscoveryCycle() {
  if (webDiscoveryState.busy) {
    return Promise.resolve();
  }
  const { seedUrls } = readDiscoveryForm();
  if (seedUrls.length) {
    return runWebDiscovery();
  }
  return runWebSearch();
}

function recordMonitorRun() {
  const coverage = webDiscoveryState.coverage || {};
  const snapshot = {
    time: new Date(),
    providerStatus: webDiscoveryState.providerStatus || "manual",
    results: Number(coverage.searchResults ?? webDiscoveryState.searchResultCount ?? 0),
    candidates: webDiscoveryState.candidates.length,
    pages: Number(coverage.pagesEvaluated ?? webDiscoveryState.sourcesScanned.length ?? 0),
    domains: Number(coverage.domainsEvaluated ?? 0),
    unknown: Number(coverage.unknownDomains ?? 0),
    blocked: Number(coverage.blockedUnreachable ?? webDiscoveryState.sourcesScanned.filter((source) => !source.ok && !source.skipped).length),
    mediaRefs: Number(coverage.mediaReferences ?? webDiscoveryState.mediaReferenceCount ?? 0),
    verified: countContentVerifiedDiscoveryCandidates(),
    matches: webDiscoveryState.candidates.filter((lead) => hasContentVerification(lead) && lead.decision === "Match").length
  };

  webDiscoveryState.monitorRuns = [snapshot, ...webDiscoveryState.monitorRuns].slice(0, 8);
}

function toggleWebMonitor() {
  if (webDiscoveryState.monitorTimer) {
    window.clearInterval(webDiscoveryState.monitorTimer);
    webDiscoveryState.monitorTimer = null;
    webDiscoveryState.monitorActive = false;
    setWebDiscoveryStatus(webDiscoveryState.candidates.length ? "Monitor paused" : "Waiting", webDiscoveryState.candidates.length ? "ready" : "");
    renderWebDiscovery();
    return;
  }

  webDiscoveryState.monitorActive = true;
  webDiscoveryState.monitorStartedAt = new Date();
  webDiscoveryState.monitorRuns = [];
  runDiscoveryCycle();
  webDiscoveryState.monitorTimer = window.setInterval(() => {
    runDiscoveryCycle();
  }, 45000);
  setWebDiscoveryStatus("Monitor active", "ready");
}

function decisionClass(decision) {
  if (decision === "Match") return "match";
  if (decision === "Review") return "review";
  return "no-match";
}

function formatCandidateMetric(candidate) {
  if (candidate.scoreLabel === "Risk score") {
    return `${candidate.confidence.toFixed(0)}/100`;
  }
  return `${candidate.confidence.toFixed(1)}%`;
}

function formatEdgeMetric(edge) {
  if (edge.type === "pattern") {
    return `${edge.confidence.toFixed(0)}/100 risk`;
  }
  return `${edge.confidence.toFixed(1)}%`;
}

function renderLocalScanner() {
  const status = $("#local-scan-status");
  if (!status) return;

  status.textContent = localScanState.status;
  status.className = `status-pill ${localScanState.statusTone}`;
  $$("[data-action='generate-local-dna'], [data-action='run-local-scan'], [data-action='run-url-candidate-scan'], [data-action='search-internet-for-work']").forEach((button) => {
    button.disabled = localScanState.busy;
  });

  const protectedLabel = document.querySelector("label[for='protected-video-input']");
  const candidateLabel = document.querySelector("label[for='candidate-video-input']");
  protectedLabel?.classList.toggle("ready", Boolean(localScanState.protectedFile));
  candidateLabel?.classList.toggle("ready", Boolean(localScanState.candidateFiles.length));

  $("#protected-file-name").textContent = localScanState.protectedFile?.name || "Select original video";
  $("#protected-file-meta").textContent = localScanState.protectedFile
    ? formatBytes(localScanState.protectedFile.size)
    : "MP4 or WebM recommended";
  $("#candidate-file-name").textContent = localScanState.candidateFiles.length
    ? `${localScanState.candidateFiles.length} candidate video${localScanState.candidateFiles.length === 1 ? "" : "s"} selected`
    : "Select suspected copies";
  $("#candidate-file-meta").textContent = localScanState.candidateFiles.length
    ? localScanState.candidateFiles.map((file) => file.name).join(", ")
    : "Multiple local videos supported";

  if (localScanState.protectedDna) {
    const dna = localScanState.protectedDna;
    $("#local-dna-title").textContent = dna.dnaId;
    $("#local-dna-summary").innerHTML = `
      <div class="local-dna-stats">
        <span><strong>${dna.sampleCount}</strong> sampled frames</span>
        <span><strong>${formatDuration(dna.duration)}</strong> duration</span>
        <span><strong>${dna.width}x${dna.height}</strong> source frame</span>
        <span><strong>${formatBytes(dna.fileSize)}</strong> file size</span>
      </div>
      ${localScanState.error ? `<div class="empty-state">${escapeHtml(localScanState.error)}</div>` : ""}
    `;
  } else {
    $("#local-dna-title").textContent = "No local DNA yet";
    $("#local-dna-summary").innerHTML = `
      <div class="empty-state">${escapeHtml(localScanState.error || "Waiting for a protected video.")}</div>
    `;
  }

  if (!localScanState.results.length) {
    $("#local-results-list").innerHTML = `<div class="empty-state">${escapeHtml(localScanState.error || "Run a local scan to rank candidates.")}</div>${renderUrlCandidateAudit()}`;
    $("#local-case-title").textContent = "No candidate selected";
    $("#local-case-decision").textContent = "Idle";
    $("#local-case-decision").className = "status-pill";
    $("#local-case-detail").innerHTML = `<div class="empty-state">The highest scoring candidate appears here after scanning.</div>`;
    return;
  }

  $("#local-results-list").innerHTML = localScanState.results
    .map(
      (result, index) => `
        <button class="local-result-card ${index === localScanState.selectedResultIndex ? "active" : ""}" type="button" data-local-result="${index}">
          <span>
            <h4>${escapeHtml(result.fileName)}</h4>
            <p>${result.decision} / ${formatDuration(result.duration)} / ${formatBytes(result.fileSize)}</p>
          </span>
          <span class="local-score">${result.confidence.toFixed(1)}%</span>
        </button>
      `
    )
    .join("") + renderUrlCandidateAudit();

  $$("[data-local-result]").forEach((button) => {
    button.addEventListener("click", () => {
      localScanState.selectedResultIndex = Number(button.dataset.localResult);
      renderLocalScanner();
    });
  });

  const selected = localScanState.results[localScanState.selectedResultIndex] || localScanState.results[0];
  const investigationSummary =
    localScanState.investigation?.summary ||
    selected.analysis?.summary ||
    "Investigator summary is generated after the backend scan completes.";
  const signalRows = Object.entries(selected.signals)
    .map(
      ([name, value]) => `
        <div class="signal-row">
          <span>${name}</span>
          <span class="bar"><i style="--value: ${value}%"></i></span>
          <strong>${value}%</strong>
        </div>
      `
    )
    .join("");
  const weightRows = Object.entries(selected.weights)
    .map(
      ([name, value]) => `
        <div class="signal-row">
          <span>${name}</span>
          <span class="bar"><i style="--value: ${value * 2.4}%"></i></span>
          <strong>${value}%</strong>
        </div>
      `
    )
    .join("");

  $("#local-case-title").textContent = selected.fileName;
  $("#local-case-decision").textContent = selected.decision;
  $("#local-case-decision").className = `status-pill ${selected.decision === "Match" ? "ready" : selected.decision === "Review" ? "warning" : "danger"}`;
  $("#local-case-detail").innerHTML = `
    <span class="decision-pill ${decisionClass(selected.decision)}">${selected.decision}</span>
    <div class="empty-state">${escapeHtml(investigationSummary)}</div>
    <div class="detail-row"><span>Adaptive match</span><strong>${selected.confidence.toFixed(1)}%</strong></div>
    <div class="detail-row"><span>Candidate DNA</span><strong>${selected.dnaId}</strong></div>
    <div class="detail-row"><span>Access type</span><strong>${escapeHtml(selected.accessType || "Uploaded candidate file")}</strong></div>
    <div class="detail-row"><span>Sampled frames</span><strong>${selected.sampledFrames || "Measured"}</strong></div>
    ${selected.sourceUrl ? `<span class="path-chip">${escapeHtml(selected.sourceUrl)}</span>` : ""}
    <div class="local-case-metrics">${signalRows}</div>
    <div class="local-case-metrics">${weightRows}</div>
    <ul class="reason-list">
      ${selected.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
    </ul>
  `;
}

function renderUrlCandidateAudit() {
  const downloaded = localScanState.downloadedUrlCandidates || [];
  const rejected = localScanState.rejectedUrlCandidates || [];
  if (!downloaded.length && !rejected.length) return "";

  const downloadedRows = downloaded
    .map(
      (item) => `
        <li>
          <strong>Verified</strong>
          <span>${escapeHtml(item.fileName || item.url)}${item.bytes ? ` / ${formatBytes(Number(item.bytes))}` : ""}</span>
        </li>
      `
    )
    .join("");
  const rejectedRows = rejected
    .map(
      (item) => `
        <li>
          <strong>Blocked</strong>
          <span>${escapeHtml(item.error || "URL candidate was rejected")}<br /><code>${escapeHtml(item.url || "")}</code></span>
        </li>
      `
    )
    .join("");

  return `
    <div class="url-audit-card">
      <p class="eyebrow">URL Candidate Audit</p>
      <ul>${downloadedRows}${rejectedRows}</ul>
    </div>
  `;
}

function renderDirectMediaQueue(directMediaTargets) {
  if (!directMediaTargets.length && !webDiscoveryState.mediaReferenceCount) return "";

  const rows = directMediaTargets.length
    ? directMediaTargets
        .slice(0, 8)
        .map(
          (target) => `
            <article>
              <div>
                <strong>${escapeHtml(target.host || "public media")}</strong>
                <span>direct public video file / candidate ${escapeHtml(target.candidateId)}</span>
              </div>
              <code>${escapeHtml(target.url)}</code>
              <p>${escapeHtml(target.pageUrl ? `found on ${target.pageUrl}` : "discovered from public source metadata")}</p>
            </article>
          `
        )
        .join("")
    : `
      <article>
        <div>
          <strong>No direct video file URL</strong>
          <span>media hints found, but nothing eligible for automatic DNA ingestion</span>
        </div>
        <p>Pages may expose players, scripts, HLS/DASH playlists, blocked embeds, or non-video links. CineShield keeps those as discovery leads instead of bypassing access controls.</p>
      </article>
    `;

  return `
    <details class="discovery-evidence">
      <summary>Direct Media Queue</summary>
      <div class="discovery-evidence-list">${rows}</div>
    </details>
  `;
}

function renderSourceAudit() {
  if (!webDiscoveryState.sourcesScanned.length) return "";

  const rows = webDiscoveryState.sourcesScanned.slice(0, 14).map((source) => {
    const stateLabel = source.skipped ? "AUTHORIZED / skipped" : source.ok ? "REACHED" : "BLOCKED / unreachable";
    const detail = source.ok
      ? `${source.linksFound || 0} links / ${source.mediaReferences || 0} media refs / ${(source.discoveredLinks || []).length} expansion URLs`
      : source.error || "Source could not be reached";
    return `
      <article>
        <div>
          <strong>${escapeHtml(source.host || source.title || "unknown source")}</strong>
          <span>${escapeHtml(stateLabel)} / ${escapeHtml(source.sourceClass || "UNKNOWN")}</span>
        </div>
        <code>${escapeHtml(source.url || "")}</code>
        <p>${escapeHtml(detail)}</p>
      </article>
    `;
  }).join("");

  return `
    <details class="discovery-evidence">
      <summary>Source Audit</summary>
      <div class="discovery-evidence-list">${rows}</div>
    </details>
  `;
}

function renderMonitorHistory() {
  if (!webDiscoveryState.monitorRuns.length) return "";

  const rows = webDiscoveryState.monitorRuns
    .map(
      (run, index) => `
        <article>
          <div>
            <strong>${index === 0 ? "Latest run" : `Run ${index + 1}`}</strong>
            <span>${run.time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })} / ${escapeHtml(run.providerStatus)}</span>
          </div>
          <p>${run.results} results, ${run.pages} pages, ${run.domains} domains, ${run.unknown} unknown, ${run.blocked} blocked, ${run.mediaRefs} media refs, ${run.verified} DNA verified, ${run.matches} matches.</p>
        </article>
      `
    )
    .join("");

  return `
    <details class="discovery-evidence" open>
      <summary>Monitor Runs</summary>
      <div class="discovery-evidence-list">${rows}</div>
    </details>
  `;
}

function renderWebDiscovery() {
  const status = $("#web-discovery-status");
  if (!status) return;

  status.textContent = webDiscoveryState.status;
  status.className = `status-pill ${webDiscoveryState.statusTone}`;
  $$("[data-action='run-web-discovery'], [data-action='run-web-search']").forEach((button) => {
    button.disabled = webDiscoveryState.busy;
  });
  const monitorButton = $("#web-monitor-button");
  if (monitorButton) {
    const label = monitorButton.querySelector("span");
    if (label) label.textContent = webDiscoveryState.monitorTimer ? "Stop Monitor" : "Start Monitor";
  }

  const okSources = webDiscoveryState.sourcesScanned.filter((source) => source.ok).length;
  const failedSources = webDiscoveryState.sourcesScanned.length - okSources;
  const candidateCount = webDiscoveryState.candidates.length;
  const lastRun = webDiscoveryState.lastRunAt ? webDiscoveryState.lastRunAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "not started";
  const summary = webDiscoveryState.error || webDiscoveryState.summary;
  const coverage = webDiscoveryState.coverage || {};
  const resultsCount = Number(coverage.searchResults ?? webDiscoveryState.searchResultCount ?? 0);
  const pagesEvaluated = Number(coverage.pagesEvaluated ?? webDiscoveryState.sourcesScanned.length ?? 0);
  const domainsEvaluated = Number(coverage.domainsEvaluated ?? 0);
  const unknownDomains = Number(coverage.unknownDomains ?? 0);
  const highRiskLeads = Number(coverage.highRiskLeads ?? webDiscoveryState.candidates.filter((lead) => Number(lead.riskScore ?? lead.score ?? 0) >= 70).length);
  const blockedCount = Number(coverage.blockedUnreachable ?? failedSources);
  const mediaRefs = Number(coverage.mediaReferences ?? webDiscoveryState.mediaReferenceCount ?? 0);
  const contentVerified = countContentVerifiedDiscoveryCandidates();
  const verifiedMatches = webDiscoveryState.candidates.filter((lead) => hasContentVerification(lead) && lead.decision === "Match").length;
  const directMediaTargets = getDiscoveredDirectMediaTargets();
  const expansionQueued = Number(coverage.expansionQueued ?? webDiscoveryState.expansionUrls.length ?? 0);
  const queriesIssued = Number(coverage.queriesIssued ?? webDiscoveryState.searchQueries.length ?? 0);
  const uniqueUrls = Number(coverage.uniqueUrls ?? resultsCount);
  const totalDiscoveryMs = Number(coverage.totalDiscoveryMs ?? 0);
  const providerNames = {
    brave: "Brave",
    bing: "Bing",
    google: "Google CSE",
    commoncrawl: "Common Crawl",
    seed: "Seed",
    test: "Test",
    "multi-index": "Multi-index"
  };
  const providerLabel = providerNames[webDiscoveryState.provider] || "Multi-index";
  const providerState = webDiscoveryState.setupRequired
    ? "key needed"
    : webDiscoveryState.providerStatus === "partial"
      ? "partial"
      : webDiscoveryState.providerStatus === "ready"
        ? "ready"
        : "manual";
  const providerStack = webDiscoveryState.providerResults.length
    ? `
      <div class="provider-stack">
        ${webDiscoveryState.providerResults.map((item) => {
          const statusName = String(item.status || "manual").toLowerCase().replace(/[^a-z0-9_-]/g, "");
          const name = providerNames[item.provider] || String(item.provider || "provider");
          const count = Number(item.resultCount || 0);
          const errors = Number(item.errors || 0);
          const detail = errors ? `${count} results / ${errors} errors` : `${count} results`;
          return `<span class="provider-chip ${statusName}">${escapeHtml(name)} - ${escapeHtml(item.status || "manual")} - ${escapeHtml(detail)}</span>`;
        }).join("")}
      </div>
    `
    : "";
  const queryPlan = webDiscoveryState.searchQueries.length
    ? `
      <div class="query-plan">
        <span class="label">Search query plan</span>
        <div>
          ${webDiscoveryState.searchQueries.slice(0, 8).map((query) => `<code>${escapeHtml(query)}</code>`).join("")}
        </div>
      </div>
    `
    : "";
  const searchErrors = webDiscoveryState.searchErrors.length
    ? `<div class="empty-state warning-note">${escapeHtml(webDiscoveryState.searchErrors.slice(0, 3).join(" | "))}</div>`
    : "";
  const directMediaQueue = renderDirectMediaQueue(directMediaTargets);
  const sourceAudit = renderSourceAudit();
  const monitorHistory = renderMonitorHistory();
  const discoveryEvidence = webDiscoveryState.candidates.length
    ? `
      <details class="discovery-evidence" open>
        <summary>Discovery Evidence</summary>
        <div class="discovery-evidence-list">
          ${webDiscoveryState.candidates.slice(0, 10).map((lead) => `
            <article>
              <div>
                <strong>${escapeHtml(lead.host || "unknown domain")}</strong>
                <span>${
                  hasContentVerification(lead)
                    ? `${escapeHtml(lead.decision || "Review")} / DNA ${Number(lead.contentMatchScore || 0).toFixed(1)}% / ${escapeHtml(lead.mediaAccessStatus || "MEDIA_VERIFIED")}`
                    : `${escapeHtml(lead.riskLevel || lead.decision || "Investigate")} / risk ${Number(lead.riskScore ?? lead.score ?? 0)} / metadata ${Number(lead.metadataScore ?? 0)} / ${escapeHtml(lead.mediaAccessStatus || "MEDIA_REFERENCE_NOT_FOUND")} / ${escapeHtml(lead.verificationStatus || "DNA verification pending")}`
                }</span>
              </div>
              <code>${escapeHtml(lead.url || "")}</code>
              ${lead.verifiedMediaUrl ? `<code>media: ${escapeHtml(lead.verifiedMediaUrl)}</code>` : ""}
              <p>${escapeHtml(lead.provider ? `${lead.provider} / ${lead.query || "query unavailable"}` : lead.sourceType || "public discovery")}</p>
              <ul>
                ${(lead.reasons || ["Public discovery lead"]).slice(0, 3).map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
              </ul>
            </article>
          `).join("")}
        </div>
      </details>
    `
    : "";

  $("#web-discovery-summary").innerHTML = `
    <div class="web-summary-grid">
      <article>
        <span class="metric-label">Provider</span>
        <strong>${providerLabel}</strong>
        <small>${providerState}</small>
      </article>
      <article>
        <span class="metric-label">Searched</span>
        <strong>${resultsCount}</strong>
        <small>${queriesIssued} queries</small>
      </article>
      <article>
        <span class="metric-label">Queries</span>
        <strong>${queriesIssued}</strong>
        <small>${uniqueUrls} unique URLs</small>
      </article>
      <article>
        <span class="metric-label">Pages</span>
        <strong>${pagesEvaluated}</strong>
        <small>${okSources} reached / ${blockedCount} blocked</small>
      </article>
      <article>
        <span class="metric-label">Reached</span>
        <strong>${okSources}</strong>
        <small>public pages</small>
      </article>
      <article>
        <span class="metric-label">Blocked</span>
        <strong>${blockedCount}</strong>
        <small>unreachable or denied</small>
      </article>
      <article>
        <span class="metric-label">Domains</span>
        <strong>${domainsEvaluated}</strong>
        <small>${unknownDomains} unknown</small>
      </article>
      <article>
        <span class="metric-label">Matches</span>
        <strong>${verifiedMatches}</strong>
        <small>${highRiskLeads} risk leads</small>
      </article>
      <article>
        <span class="metric-label">Queue</span>
        <strong>${candidateCount}</strong>
        <small>non-authorized leads</small>
      </article>
      <article>
        <span class="metric-label">Media refs</span>
        <strong>${mediaRefs}</strong>
        <small>${contentVerified} DNA verified</small>
      </article>
      <article>
        <span class="metric-label">DNA verified</span>
        <strong>${contentVerified}</strong>
        <small>authorized media only</small>
      </article>
      <article>
        <span class="metric-label">Expansion</span>
        <strong>${expansionQueued}</strong>
        <small>public links queued</small>
      </article>
      <article>
        <span class="metric-label">Runtime</span>
        <strong>${totalDiscoveryMs ? `${Math.max(1, Math.round(totalDiscoveryMs / 1000))}s` : "0s"}</strong>
        <small>measured</small>
      </article>
      <article>
        <span class="metric-label">Monitor</span>
        <strong>${webDiscoveryState.monitorActive ? "On" : "Off"}</strong>
        <small>${webDiscoveryState.monitorRuns.length} run${webDiscoveryState.monitorRuns.length === 1 ? "" : "s"} / 45s</small>
      </article>
    </div>
    <div class="evidence-ladder" aria-label="Candidate evidence ladder">
      <span class="${webDiscoveryState.searchResultCount || candidateCount ? "active" : ""}">0 Search lead</span>
      <span class="${candidateCount || webDiscoveryState.sourcesScanned.length ? "active" : ""}">1 Page evidence</span>
      <span class="${webDiscoveryState.mediaReferenceCount ? "active" : ""}">2 Media reference</span>
      <span class="${contentVerified ? "active" : ""}">3 Content fingerprint</span>
      <span class="${contentVerified ? "active" : ""}">4 Multimodal match</span>
    </div>
    <div class="empty-state">${escapeHtml(summary)}</div>
    ${providerStack}
    ${searchErrors}
    ${discoveryEvidence}
    ${directMediaQueue}
    ${sourceAudit}
    ${monitorHistory}
    ${queryPlan}
    <p class="small-copy">Last discovery: ${escapeHtml(lastRun)}</p>
  `;

  if (!candidateCount) {
    const sourceRows = webDiscoveryState.sourcesScanned.length
      ? webDiscoveryState.sourcesScanned
          .map(
            (source) => `
              <article class="web-lead-card">
                <span>
                  <h4>${escapeHtml(source.title || source.host || source.url)}</h4>
                  <p>${escapeHtml(source.sourceClass || "UNKNOWN")} / ${escapeHtml(source.skipped ? "authorized source skipped" : source.ok ? `${source.linksFound || 0} links inspected / ${source.mediaReferences || 0} media refs / ${(source.discoveredLinks || []).length} queued` : source.error || "Source blocked")}</p>
                  <span class="path-chip">${escapeHtml(source.url)}</span>
                </span>
                <span class="decision-pill ${source.skipped ? "match" : source.ok ? "review" : "no-match"}">${source.skipped ? "Excluded" : source.ok ? "Scanned" : "Blocked"}</span>
              </article>
            `
          )
          .join("")
      : `<div class="empty-state">Use Search Web Index with a backend provider key, or paste public seed URLs and scan those pages directly.</div>`;
    const excludedRows = renderExcludedDiscoveryRows();
    $("#web-lead-list").innerHTML = `${sourceRows}${excludedRows}`;
    return;
  }

  $("#web-lead-list").innerHTML = webDiscoveryState.candidates
    .map((lead, index) => {
      const verified = hasContentVerification(lead);
      const dnaScore = Number(lead.contentMatchScore || 0);
      const scoreCopy = verified ? `${dnaScore.toFixed(1)}% DNA` : `${Number(lead.riskScore ?? lead.score ?? 0)} risk`;
      const stateCopy = verified
        ? `${lead.decision || "Review"} / Content DNA / ${escapeHtml(lead.mediaAccessStatus || "MEDIA_VERIFIED")}`
        : `${lead.riskLevel || "Investigate"} / metadata ${Number(lead.metadataScore ?? 0)} / ${lead.sourceClass || "UNKNOWN"} / ${lead.sourceType || "public discovery"} / L${lead.evidenceLevel || 1}: ${lead.evidenceLevelLabel || "Page evidence"}`;
      return `
        <button class="web-lead-card ${verified ? "verified" : ""} ${state.selectedCandidateId === `disc-${index}` ? "active" : ""}" type="button" data-web-lead="${index}">
          <span>
            <h4>${escapeHtml(lead.title)}</h4>
            <p>${escapeHtml(stateCopy)}</p>
            <span class="path-chip">${escapeHtml(lead.url)}</span>
            ${lead.verifiedMediaUrl ? `<span class="path-chip">Media: ${escapeHtml(lead.verifiedMediaUrl)}</span>` : ""}
          </span>
          <span class="confidence-badge">${scoreCopy}</span>
        </button>
      `;
    })
    .join("") + renderExcludedDiscoveryRows();

  $$("[data-web-lead]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.webLead);
      state.selectedCandidateId = `disc-${index}`;
      state.selectedNodeId = `disc-${index}`;
      state.selectedEdgeId = null;
      state.stage = "verify";
      renderAll();
    });
  });
}

function renderExcludedDiscoveryRows() {
  if (!webDiscoveryState.excludedCandidates.length) return "";

  return webDiscoveryState.excludedCandidates
    .map(
      (lead) => `
        <article class="web-lead-card authorized">
          <span>
            <h4>${escapeHtml(lead.title)}</h4>
            <p>AUTHORIZED / excluded before verification / ${escapeHtml(lead.host)}</p>
            <span class="path-chip">${escapeHtml(lead.url)}</span>
          </span>
          <span class="decision-pill match">Excluded</span>
        </article>
      `
    )
    .join("");
}

function bindLocalScanner() {
  const protectedInput = $("#protected-video-input");
  const candidateInput = $("#candidate-video-input");
  if (!protectedInput || !candidateInput) return;

  protectedInput.addEventListener("change", () => {
    localScanState.protectedFile = protectedInput.files[0] || null;
    localScanState.protectedDna = null;
    localScanState.results = [];
    localScanState.investigation = null;
    localScanState.downloadedUrlCandidates = [];
    localScanState.rejectedUrlCandidates = [];
    localScanState.selectedResultIndex = 0;
    localScanState.resultSource = "";
    localScanState.error = "";
    if (localScanState.protectedFile) {
      const inferredTitle = inferTitleFromFilename(localScanState.protectedFile.name);
      const protectedTitleInput = $("#protected-title-input");
      const webTitleInput = $("#web-title-input");
      const webAliasInput = $("#web-alias-input");
      if (protectedTitleInput && !protectedTitleInput.value.trim()) {
        protectedTitleInput.value = inferredTitle;
      }
      if (webTitleInput && (!webTitleInput.value.trim() || webTitleInput.value.trim() === "Project Monsoon")) {
        webTitleInput.value = inferredTitle;
      }
      if (webAliasInput && webAliasInput.value.trim() === "Monsoon, Project X") {
        webAliasInput.value = "";
      }
    }
    setLocalStatus(localScanState.protectedFile ? "Original loaded" : "Waiting", localScanState.protectedFile ? "ready" : "");
  });

  candidateInput.addEventListener("change", () => {
    localScanState.candidateFiles = Array.from(candidateInput.files || []);
    localScanState.results = [];
    localScanState.investigation = null;
    localScanState.downloadedUrlCandidates = [];
    localScanState.rejectedUrlCandidates = [];
    localScanState.selectedResultIndex = 0;
    localScanState.resultSource = "";
    localScanState.error = "";
    setLocalStatus(localScanState.candidateFiles.length ? "Candidates loaded" : "Waiting", localScanState.candidateFiles.length ? "ready" : "");
  });

  $$("[data-action='generate-local-dna']").forEach((button) => button.addEventListener("click", generateLocalDna));
  $$("[data-action='run-local-scan']").forEach((button) => button.addEventListener("click", runLocalScan));
}

function getCandidate(id = state.selectedCandidateId) {
  const workingCandidates = getWorkingCandidates();
  return workingCandidates.find((candidate) => candidate.id === id) || workingCandidates[0] || candidates[0];
}

function renderDnaSignals() {
  $("#dna-signals").innerHTML = dnaSignals
    .map(
      (signal) => `
        <div class="signal-row" title="${signal.tone}">
          <span>${signal.name}</span>
          <span class="bar"><i style="--value: ${signal.value}%"></i></span>
          <strong>${signal.value}%</strong>
        </div>
      `
    )
    .join("");
}

function renderFusionStack() {
  $("#fusion-stack").innerHTML = fusionWeights
    .map(
      (item) => `
        <div class="fusion-item">
          <div class="fusion-title">
            <span>${item.name}</span>
            <strong>${item.value}%</strong>
          </div>
          <span class="bar"><i style="--value: ${item.value * 2.6}%"></i></span>
          <p class="small-copy">${item.detail}</p>
        </div>
      `
    )
    .join("");
}

function renderTimeline() {
  const activeIndex = timelineSteps.findIndex((step) => step.id === state.stage);
  const completedIndex = activeIndex === -1 ? 0 : activeIndex;

  $("#timeline-steps").innerHTML = timelineSteps
    .map((step, index) => {
      const status = index < completedIndex ? "done" : index === completedIndex ? "active" : "";
      return `
        <div class="timeline-step ${status}">
          <strong>${step.title}</strong>
          <span>${step.detail}</span>
        </div>
      `;
    })
    .join("");

  const isAuthorized = state.caseStatus === "Authorized";
  $("#timeline-status").textContent = isAuthorized ? "Loop armed" : "In progress";
  $("#timeline-status").className = `status-pill ${isAuthorized ? "ready" : "warning"}`;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function renderLab() {
  $("#lab-toggles").innerHTML = labTransforms
    .map(
      (item) => `
        <label class="transform-toggle">
          <input type="checkbox" data-transform="${item.id}" ${labState.active.has(item.id) ? "checked" : ""} />
          <span class="toggle-visual" aria-hidden="true"></span>
          <span>
            <strong>${item.name}</strong>
            <small>${item.detail}</small>
          </span>
        </label>
      `
    )
    .join("");

  const activeTransforms = labTransforms.filter((item) => labState.active.has(item.id));
  const baseline = clamp(98 - activeTransforms.reduce((sum, item) => sum + item.baselinePenalty, 0), 24, 99);
  const cineshield = clamp(98 - activeTransforms.reduce((sum, item) => sum + item.adaptivePenalty, 0), 58, 99);
  const trust = { Visual: 27, Audio: 24, Scene: 23, Temporal: 12, Text: 8, Metadata: 6 };

  activeTransforms.forEach((item) => {
    Object.entries(item.profile).forEach(([signal, shift]) => {
      trust[signal] = clamp(trust[signal] + shift, 4, 44);
    });
  });

  const total = Object.values(trust).reduce((sum, value) => sum + value, 0);
  const normalized = Object.entries(trust).map(([name, value]) => ({
    name,
    value: Math.round((value / total) * 100)
  }));
  const dominant = [...normalized].sort((a, b) => b.value - a.value)[0];
  const decision = cineshield >= 88 ? "Match" : cineshield >= 78 ? "Review" : "Weak";

  $("#lab-baseline").textContent = `${baseline}%`;
  $("#lab-cineshield").textContent = `${cineshield}%`;
  $("#lab-decision").textContent = decision;
  $("#lab-profile").textContent = activeTransforms.length ? `${dominant.name} led fusion` : "Balanced evidence";
  $("#lab-profile").className = `status-pill ${decision === "Match" ? "ready" : "warning"}`;

  $("#lab-trust").innerHTML = normalized
    .map(
      (item) => `
        <div class="fusion-item">
          <div class="fusion-title">
            <span>${item.name}</span>
            <strong>${item.value}%</strong>
          </div>
          <span class="bar"><i style="--value: ${item.value * 2.2}%"></i></span>
        </div>
      `
    )
    .join("");

  $$("[data-transform]").forEach((input) => {
    input.addEventListener("change", () => {
      if (input.checked) {
        labState.active.add(input.dataset.transform);
      } else {
        labState.active.delete(input.dataset.transform);
      }
      renderLab();
    });
  });
}

function normalizeLiveScanResult(result, index) {
  const confidence = Number(result.confidence || 0);
  const decision = result.decision || "Review";
  const signals = result.signals || {};
  const signalEntries = Object.entries(signals).map(([name, value]) => [name, Number(value || 0)]);

  return {
    id: `live-${index}`,
    name: result.fileName || `Candidate ${index + 1}`,
    category: decision === "Match" ? "high" : decision === "Review" ? "review" : "low",
    confidence,
    transformation: decision === "Match" ? "Adaptive local scan" : decision === "Review" ? "Review threshold" : "Low-confidence local match",
    variants: 1,
    sources: 1,
    risk: decision === "Match" ? "Critical" : decision === "Review" ? "Review" : "Low",
    signals: Object.fromEntries(signalEntries),
    reasons: Array.isArray(result.reasons) && result.reasons.length ? result.reasons : [`Local backend result scored ${confidence.toFixed(1)}%`],
    summary:
      result.analysis?.summary ||
      `${result.fileName || `Candidate ${index + 1}`} returned ${confidence.toFixed(1)}% confidence with a ${decision.toLowerCase()} classification from the live backend scan.`,
    recommendedPriority: result.analysis?.recommendedPriority || (decision === "Match" ? "Critical" : decision === "Review" ? "Review" : "Low"),
    failureBoundary:
      result.analysis?.failureBoundary ||
      (decision === "Match"
        ? "Above high-confidence threshold, but still requires authorized human review before action."
        : decision === "Review"
          ? "Below automatic-response threshold. The system keeps the case in review instead of making a stronger claim."
          : "Below same-content threshold. No evidence package should be generated unless new evidence appears."),
    fileSize: Number(result.fileSize || 0),
    duration: Number(result.duration || 0),
    sourceUrl: result.sourceUrl || "",
    accessType: result.accessType || "Uploaded candidate file",
    evidenceLevel: Number(result.evidenceLevel || 4),
    evidenceLevelLabel: result.evidenceLevelLabel || "Multimodal match",
    decision
  };
}

function normalizeDiscoveryLead(lead, index) {
  const riskScore = Number(lead.riskScore ?? lead.score ?? 0);
  const metadataScore = Number(lead.metadataScore ?? lead.relevanceScore ?? 0);
  const verified = hasContentVerification(lead);
  const contentScore = Number(lead.contentMatchScore || 0);
  const decision = lead.decision || (verified ? "Review" : "Candidate lead");
  const rawSignals = verified && lead.contentSignals ? lead.contentSignals : lead.signals || {};
  const signals = Object.fromEntries(
    Object.entries(rawSignals).map(([name, value]) => [name, Number(value || 0)])
  );

  if (verified) {
    const contentReasons = Array.isArray(lead.contentReasons) && lead.contentReasons.length ? lead.contentReasons : [];
    const discoveryReasons = Array.isArray(lead.reasons) ? lead.reasons : [];
    return {
      id: `disc-${index}`,
      name: lead.title || lead.candidateFileName || `Verified lead ${index + 1}`,
      category: decision === "Match" ? "high" : decision === "Review" ? "review" : "low",
      confidence: contentScore,
      scoreLabel: "Content DNA",
      evidenceLabel: "Verification state",
      transformation: `${decision} - direct public media verified`,
      variants: Math.max(1, Number(lead.mediaReferenceCount || 1)),
      sources: 1,
      risk: decision === "Match" ? "Critical" : decision === "Review" ? "Review" : "Low",
      signals,
      reasons: dedupeReasons([
        ...contentReasons,
        ...discoveryReasons.slice(0, 2),
        lead.evidenceBoundary || contentVerificationBoundary(decision)
      ]),
      summary:
        lead.contentAnalysis?.summary ||
        `CineShield discovered ${lead.host || "a public source"}, extracted a direct public media reference, and compared the candidate media against ${webDiscoveryState.query || "the protected work"}. ` +
          `The Content DNA score is ${contentScore.toFixed(1)}%, producing a ${decision.toUpperCase()} decision.`,
      recommendedPriority:
        lead.contentAnalysis?.recommendedPriority ||
        (decision === "Match"
          ? "Critical human-review priority"
          : decision === "Review"
            ? "Human-review queue"
            : "Reject as same-content evidence"),
      failureBoundary:
        lead.contentAnalysis?.failureBoundary ||
        lead.evidenceBoundary ||
        contentVerificationBoundary(decision),
      sourceUrl: lead.url,
      verifiedMediaUrl: lead.verifiedMediaUrl || "",
      host: lead.host,
      accessType: lead.accessType || "Authorized direct public media URL",
      evidenceLevel: 4,
      evidenceLevelLabel: "Multimodal match",
      decision
    };
  }

  return {
    id: `disc-${index}`,
    name: lead.title || `Discovery lead ${index + 1}`,
    category: riskScore >= 70 ? "high" : riskScore >= 35 ? "review" : "low",
    confidence: riskScore,
    scoreLabel: "Risk score",
    evidenceLabel: "Discovery state",
    transformation: `${lead.finalDecisionStage || "DISCOVERED"} - metadata ${metadataScore}, DNA pending`,
    variants: 1,
    sources: 1,
    risk: lead.riskLevel || "Review",
    signals,
    reasons: [
      ...(Array.isArray(lead.reasons) ? lead.reasons : []),
      lead.evidenceBoundary || "Metadata-only lead. Verify with Content DNA before action."
    ],
    summary:
      `${lead.title || "This page"} was discovered from public source metadata for ${webDiscoveryState.query || "the protected work"}. ` +
      `Metadata relevance is ${metadataScore}/100 and investigation risk is ${riskScore}/100. ` +
      "This is not a piracy conclusion; media fingerprint verification is still required.",
    recommendedPriority: riskScore >= 70 ? "High investigation priority" : riskScore >= 35 ? "Review investigation priority" : "Low-risk relevance lead",
    failureBoundary: lead.evidenceBoundary || "No legal or takedown action should happen from metadata alone.",
    sourceUrl: lead.url,
    verifiedMediaUrl: "",
    host: lead.host,
    accessType: lead.accessType || "Public page metadata",
    evidenceLevel: Number(lead.evidenceLevel || 1),
    evidenceLevelLabel: lead.evidenceLevelLabel || "Page evidence",
    decision
  };
}

function getWorkingCandidates() {
  if (webDiscoveryState.candidates.length && localScanState.resultSource === "discovery-url" && countContentVerifiedDiscoveryCandidates()) {
    return webDiscoveryState.candidates.map((lead, index) => normalizeDiscoveryLead(lead, index));
  }

  if (localScanState.results.length) {
    return localScanState.results.map((result, index) => normalizeLiveScanResult(result, index));
  }

  if (webDiscoveryState.candidates.length) {
    return webDiscoveryState.candidates.map((lead, index) => normalizeDiscoveryLead(lead, index));
  }

  return candidates;
}

function renderSummaryMetrics() {
  const summaryCandidates = getWorkingCandidates();
  if (localScanState.results.length && localScanState.resultSource !== "discovery-url") {
    const matches = localScanState.results.filter((item) => item.decision === "Match").length;
    const review = localScanState.results.filter((item) => item.decision === "Review").length;
    const rejects = localScanState.results.filter((item) => item.decision === "No match").length;

    $("#metric-candidates").textContent = String(localScanState.results.length);
    $("#metric-high").textContent = String(matches);
    $("#metric-clusters").textContent = String(Math.max(1, Math.min(12, localScanState.results.length)));
    $("#metric-review").textContent = String(review + rejects);
  } else if (webDiscoveryState.candidates.length) {
    const hosts = new Set(webDiscoveryState.candidates.map((lead) => lead.host).filter(Boolean));
    const verifiedMatches = webDiscoveryState.candidates.filter((lead) => hasContentVerification(lead) && lead.decision === "Match").length;
    const verifiedReview = webDiscoveryState.candidates.filter((lead) => hasContentVerification(lead) && lead.decision === "Review").length;
    const verifiedReject = webDiscoveryState.candidates.filter((lead) => hasContentVerification(lead) && lead.decision === "No match").length;
    const highRiskMetadata = webDiscoveryState.candidates.filter((lead) => !hasContentVerification(lead) && Number(lead.riskScore ?? lead.score ?? 0) >= 70).length;
    $("#metric-candidates").textContent = String(webDiscoveryState.candidates.length);
    $("#metric-high").textContent = String(verifiedMatches + highRiskMetadata);
    $("#metric-clusters").textContent = String(Math.max(1, hosts.size));
    $("#metric-review").textContent = String(
      verifiedReview + verifiedReject + webDiscoveryState.candidates.filter((lead) => !hasContentVerification(lead)).length
    );
  } else {
    $("#metric-candidates").textContent = summaryCandidates.length > 0 ? String(summaryCandidates.length) : "143";
    $("#metric-high").textContent = summaryCandidates.filter((candidate) => candidate.confidence >= 85).length || "31";
    $("#metric-clusters").textContent = "12";
    $("#metric-review").textContent = summaryCandidates.filter((candidate) => candidate.risk === "Review").length || "8";
  }
}

function renderCandidates() {
  const visible = getWorkingCandidates().filter((candidate) => {
    if (state.filter === "all") return true;
    return candidate.category === state.filter;
  });

  $("#candidate-list").innerHTML = visible
    .map(
      (candidate) => {
        const badge = candidate.scoreLabel === "Risk score"
          ? `${candidate.confidence.toFixed(0)} risk`
          : formatCandidateMetric(candidate);
        return `
        <button class="candidate-card ${candidate.id === state.selectedCandidateId ? "active" : ""}" type="button" data-candidate="${candidate.id}">
          <span>
            <h4>${escapeHtml(candidate.name)}</h4>
            <p>${escapeHtml(candidate.transformation)} / ${candidate.variants} variants / ${candidate.sources} sources</p>
          </span>
          <span class="confidence-badge">${badge}</span>
        </button>
      `;
      }
    )
    .join("");

  $$("[data-candidate]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedCandidateId = button.dataset.candidate;
      const liveCandidates = getWorkingCandidates();
      const relatedNode = liveCandidates.find((candidate) => candidate.id === state.selectedCandidateId);
      state.selectedNodeId = relatedNode ? state.selectedCandidateId : state.selectedNodeId;
      state.selectedEdgeId = null;
      state.stage = "investigate";
      renderAll();
      document.querySelector("#casework").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function buildGraphSnapshot() {
  const useDiscoveryGraph =
    webDiscoveryState.candidates.length &&
    (!localScanState.results.length || localScanState.resultSource === "discovery-url");
  if (useDiscoveryGraph) {
    const nodes = [{ id: "work", label: "Protected Work", x: 380, y: 76, type: "work", candidate: "work" }];
    const leads = webDiscoveryState.candidates.slice(0, 7).map((lead, index) => ({
      id: `disc-${index}`,
      label: lead.host ? lead.host.slice(0, 9) : `D${index + 1}`,
      x: 170 + (index % 4) * 142,
      y: 190 + Math.floor(index / 4) * 116,
      type: "source",
      candidate: `disc-${index}`
    }));

    const edges = leads.map((node, index) => {
      const lead = webDiscoveryState.candidates[index];
      const verified = hasContentVerification(lead);
      const decision = lead.decision || "Candidate lead";
      return {
        id: `disc-edge-${index}`,
        from: "work",
        to: node.id,
        type: verified ? "dna" : "pattern",
        relation: verified ? `Content DNA ${decision}` : "Discovery metadata lead",
        confidence: verified ? Number(lead.contentMatchScore || 0) : Number(lead.riskScore ?? lead.score ?? 0),
        evidence: verified
          ? dedupeReasons([...(lead.contentReasons || []), lead.evidenceBoundary || contentVerificationBoundary(decision)])
          : lead.reasons || ["Public metadata lead"],
        why: verified
          ? "This edge was promoted only after public discovery found a direct media reference and the backend compared that candidate with the protected work using Content DNA."
          : "This edge comes from public page metadata and link context. It is not a Content DNA match until media verification runs."
      };
    });

    return { nodes: [...nodes, ...leads], edges };
  }

  if (!localScanState.results.length) {
    return { nodes: graphNodes, edges: graphEdges };
  }

  const nodes = [{ id: "work", label: "Protected Work", x: 380, y: 76, type: "work", candidate: "work" }];
  const results = localScanState.results.map((result, index) => ({
    id: `live-${index}`,
    label: result.fileName ? result.fileName.split(".")[0].slice(0, 8) : `LC${index + 1}`,
    x: 220 + (index % 3) * 160,
    y: 190 + Math.floor(index / 3) * 100,
    type: "source",
    candidate: `live-${index}`
  }));

  const edges = results.map((node, index) => ({
    id: `live-edge-${index}`,
    from: "work",
    to: node.id,
    type: "dna",
    relation: localScanState.results[index].decision === "Match" ? "Live content DNA match" : localScanState.results[index].decision === "Review" ? "Review gate" : "No-link threshold",
    confidence: Number(localScanState.results[index].confidence || 0),
    evidence: Array.isArray(localScanState.results[index].reasons) ? localScanState.results[index].reasons : ["Live backend result"],
    why: `This edge is generated from the live scan response for ${localScanState.results[index].fileName || "candidate"}.`
  }));

  return { nodes: [...nodes, ...results], edges };
}

function renderGraph() {
  const edgesLayer = $("#graph-edges");
  const nodesLayer = $("#graph-nodes");
  const snapshot = buildGraphSnapshot();
  const nodeById = Object.fromEntries(snapshot.nodes.map((node) => [node.id, node]));

  edgesLayer.innerHTML = snapshot.edges
    .map((edge) => {
      const from = nodeById[edge.from];
      const to = nodeById[edge.to];
      const active = edge.id === state.selectedEdgeId ? "active" : "";
      const type = edge.type === "pattern" ? "pattern" : "";
      return `
        <g data-edge="${edge.id}" tabindex="0" role="button" aria-label="${edge.relation}">
          <line class="graph-edge-hit" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" />
          <line class="graph-edge ${type} ${active}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" />
        </g>
      `;
    })
    .join("");

  nodesLayer.innerHTML = snapshot.nodes
    .map(
      (node) => `
        <g class="graph-node ${node.type === "work" ? "work" : ""} ${node.id === state.selectedNodeId ? "active" : ""}" data-node="${node.id}" tabindex="0" role="button" aria-label="${node.label}">
          <circle cx="${node.x}" cy="${node.y}" r="${node.type === "work" ? 38 : 30}"></circle>
          <text x="${node.x}" y="${node.y + 5}">${node.label}</text>
        </g>
      `
    )
    .join("");

  $$("[data-node]").forEach((nodeEl) => {
    const activate = () => {
      const node = nodeById[nodeEl.dataset.node];
      state.selectedNodeId = node.id;
      state.selectedEdgeId = null;
      state.selectedCandidateId = node.candidate;
      state.stage = node.type === "work" ? "graph" : "investigate";
      renderAll();
    };
    nodeEl.addEventListener("click", activate);
    nodeEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") activate();
    });
  });

  $$("[data-edge]").forEach((edgeEl) => {
    const activate = () => {
      const edge = snapshot.edges.find((item) => item.id === edgeEl.dataset.edge);
      const toNode = edge ? nodeById[edge.to] : null;
      state.selectedEdgeId = edgeEl.dataset.edge;
      if (toNode) {
        state.selectedNodeId = toNode.id;
        state.selectedCandidateId = toNode.candidate;
      }
      state.stage = "graph";
      renderAll();
    };
    edgeEl.addEventListener("click", activate);
    edgeEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") activate();
    });
  });
}

function renderNodeDetail() {
  const snapshot = buildGraphSnapshot();
  const selectedEdge = snapshot.edges.find((item) => item.id === state.selectedEdgeId);
  if (selectedEdge) {
    const from = snapshot.nodes.find((item) => item.id === selectedEdge.from);
    const to = snapshot.nodes.find((item) => item.id === selectedEdge.to);
    $("#node-title").textContent = selectedEdge.relation;
    $("#node-risk").textContent = formatEdgeMetric(selectedEdge);
    $("#node-risk").className = "status-pill ready";
    $("#node-detail").innerHTML = `
      <div class="detail-row"><span>From</span><strong>${escapeHtml(from.label)}</strong></div>
      <div class="detail-row"><span>To</span><strong>${escapeHtml(to.label)}</strong></div>
      <div class="detail-row"><span>Edge type</span><strong>${selectedEdge.type === "dna" ? "Content DNA" : "Pattern"}</strong></div>
      <div class="detail-row"><span>${selectedEdge.type === "dna" ? "Confidence" : "Risk score"}</span><strong>${formatEdgeMetric(selectedEdge)}</strong></div>
      <ul class="reason-list">
        ${selectedEdge.evidence.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
      </ul>
      <div class="investigator-block">
        <h4>Why linked</h4>
        <p>${escapeHtml(selectedEdge.why)}</p>
      </div>
    `;
    return;
  }

  const node = snapshot.nodes.find((item) => item.id === state.selectedNodeId) || snapshot.nodes[1] || snapshot.nodes[0];
  const candidate = getCandidate(node.candidate === "work" ? state.selectedCandidateId : node.candidate);
  $("#node-title").textContent = node.type === "work" ? "Protected Work" : candidate.name;
  $("#node-risk").textContent = candidate.risk;
  $("#node-risk").className = `status-pill ${candidate.risk === "Critical" ? "danger" : candidate.risk === "Review" ? "warning" : "ready"}`;

  $("#node-detail").innerHTML = `
    <div class="detail-row"><span>${candidate.scoreLabel || "Adaptive match"}</span><strong>${formatCandidateMetric(candidate)}</strong></div>
    <div class="detail-row"><span>${candidate.evidenceLabel || "Transformation"}</span><strong>${escapeHtml(candidate.transformation)}</strong></div>
    <div class="detail-row"><span>Related sources</span><strong>${candidate.sources}</strong></div>
    <div class="detail-row"><span>Variants</span><strong>${candidate.variants}</strong></div>
    ${candidate.sourceUrl ? `<span class="path-chip">${escapeHtml(candidate.sourceUrl)}</span>` : ""}
    ${candidate.verifiedMediaUrl ? `<span class="path-chip">Media: ${escapeHtml(candidate.verifiedMediaUrl)}</span>` : ""}
    <ul class="reason-list">
      ${candidate.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
    </ul>
  `;
}

function renderInvestigator() {
  const candidate = getCandidate();
  const signalRows = Object.entries(candidate.signals)
    .map(
      ([name, value]) => `
        <div class="signal-row">
          <span>${name}</span>
          <span class="bar"><i style="--value: ${value}%"></i></span>
          <strong>${value}%</strong>
        </div>
      `
    )
    .join("");

  $("#investigator").innerHTML = `
    <div class="investigator-block">
      <h4>Investigation Summary</h4>
      <p>${escapeHtml(candidate.summary)}</p>
    </div>
    <div class="investigator-block">
      <h4>Recommended Priority</h4>
      <p>${escapeHtml(candidate.recommendedPriority ? `${candidate.recommendedPriority}: ` : "")}${candidate.risk === "Review" ? "Escalate to reviewer before any response package leaves the system." : "Prioritize this cluster because confidence, variant count, and source spread are all elevated."}</p>
    </div>
    <div class="investigator-block">
      <h4>Match Analysis</h4>
      <div class="dna-signals">${signalRows}</div>
    </div>
    <div class="investigator-block">
      <h4>Failure Boundary</h4>
      <p>${escapeHtml(candidate.failureBoundary || (candidate.confidence < 85 ? "Below automatic-response threshold. The system keeps the case in review instead of making a stronger claim." : "Above high-confidence threshold, but still requires authorized human review before action."))}</p>
    </div>
  `;
}

function getActiveProtectedWorkLabel() {
  const title =
    webDiscoveryState.query ||
    $("#protected-title-input")?.value.trim() ||
    $("#web-title-input")?.value.trim() ||
    inferTitleFromFilename(localScanState.protectedFile?.name || "") ||
    "Project Monsoon";
  const dnaState = localScanState.protectedDna ? "registered content DNA verified" : "content DNA pending";
  return `${title} / ${dnaState}`;
}

function renderCase() {
  const candidate = getCandidate();
  $("#case-title").textContent = `CASE ${candidate.id.startsWith("live-") ? "CS-LIVE" : `CS-${candidate.id.replace(/\D/g, "").padEnd(5, "8")}`}`;
  $("#case-status").textContent = state.caseStatus;
  $("#case-status").className = `status-pill ${state.caseStatus === "Authorized" ? "ready" : "warning"}`;

  $("#case-card").innerHTML = `
    <div>
      <h4>Protected Work</h4>
      <p>${escapeHtml(getActiveProtectedWorkLabel())}</p>
    </div>
    <ul class="case-facts">
      <li><span>Candidate</span><strong>${escapeHtml(candidate.name)}</strong></li>
      <li><span>${candidate.scoreLabel || "Adaptive match"}</span><strong>${formatCandidateMetric(candidate)}</strong></li>
      <li><span>${candidate.evidenceLabel || "Detected transform"}</span><strong>${escapeHtml(candidate.transformation)}</strong></li>
      <li><span>Related sources</span><strong>${candidate.sources}</strong></li>
      <li><span>Recommended priority</span><strong>${candidate.risk}</strong></li>
    </ul>
    ${candidate.sourceUrl ? `<span class="path-chip">${escapeHtml(candidate.sourceUrl)}</span>` : ""}
    ${candidate.verifiedMediaUrl ? `<span class="path-chip">Media: ${escapeHtml(candidate.verifiedMediaUrl)}</span>` : ""}
    <ul class="reason-list">
      ${candidate.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
    </ul>
  `;
}

function renderBenchmark() {
  const generatedBenchmark = window.CINESHIELD_BENCHMARK;
  const rows = generatedBenchmark?.rows || benchmarks;
  const overall = generatedBenchmark?.overall;
  const coverage = generatedBenchmark?.coverage;

  if (generatedBenchmark) {
    const split = generatedBenchmark.split;
    const splitCopy = split
      ? `${split.testExamples} held-out test examples from ${split.testWorks} test works; ${split.calibrationWorks} calibration works kept separate.`
      : `${generatedBenchmark.sampleCount} synthetic Content DNA examples.`;
    $("#benchmark-meta").textContent =
      `Generated with a ${split?.type || "synthetic"} split: ${splitCopy} Seed ${generatedBenchmark.seed}. ` +
      `Overall F1: baseline ${overall.baseline.f1}%, adaptive ${overall.adaptive.f1}%. ` +
      `${generatedBenchmark.negativeDesign || ""}`;
  }

  if (coverage) {
    $("#benchmark-coverage").innerHTML = renderCoverageCards(coverage);
  }

  $("#benchmark-table").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Transformation</th>
          <th>Baseline F1</th>
          <th>CineShield F1</th>
          <th>Gain</th>
          <th>Degradation</th>
          <th>Evidence profile</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map((row) => {
            const gain = row.gain ?? row.cineshield - row.baseline;
            const degradation = row.degradation ?? Math.max(0, 100 - row.cineshield);
            return `
              <tr>
                <td><strong>${row.transformation}</strong></td>
                <td>${row.baseline}%</td>
                <td><strong>${row.cineshield}%</strong></td>
                <td class="gain">${gain >= 0 ? "+" : ""}${gain}%</td>
                <td>${degradation}%</td>
                <td>${row.note}</td>
              </tr>
            `;
          })
          .join("")}
      </tbody>
    </table>
  `;
}

function renderCoverageCards(coverage) {
  return `
    <article>
      <span class="metric-label">Match</span>
      <strong>${coverage.matchRate}%</strong>
      <small>${coverage.match} high-confidence cases</small>
    </article>
    <article>
      <span class="metric-label">Reject</span>
      <strong>${coverage.negativeRate}%</strong>
      <small>${coverage.negative} negatives</small>
    </article>
    <article>
      <span class="metric-label">Review</span>
      <strong>${coverage.reviewRate}%</strong>
      <small>${coverage.review} human-gated cases</small>
    </article>
    <article>
      <span class="metric-label">Coverage</span>
      <strong>${coverage.automationCoverage}%</strong>
      <small>automated match/reject</small>
    </article>
    <article>
      <span class="metric-label">Auto Accuracy</span>
      <strong>${coverage.automatedDecisionAccuracy}%</strong>
      <small>on automated decisions</small>
    </article>
  `;
}

function renderRealMediaBenchmark() {
  const data = window.CINESHIELD_REAL_MEDIA;
  if (!data) {
    $("#real-media-meta").textContent = "Run python engine\\real_media_benchmark.py to generate real-media benchmark results.";
    $("#real-media-metrics").innerHTML = "";
    $("#real-media-coverage").innerHTML = "";
    $("#real-media-table").innerHTML = "";
    $("#real-case").innerHTML = "";
    return;
  }

  $("#real-media-meta").textContent =
    `Generated ${data.works} permitted synthetic media works and evaluated ${data.sampleCount} media pairs. ` +
    `This is a pipeline smoke test using extracted frame, audio, scene, temporal, and metadata fingerprints. ` +
    `${data.negativeDesign || ""}.`;

  $("#real-media-metrics").innerHTML = `
    <article>
      <span class="metric-label">Works</span>
      <strong>${data.works}</strong>
      <small>generated locally</small>
    </article>
    <article>
      <span class="metric-label">Pairs</span>
      <strong>${data.sampleCount}</strong>
      <small>positive and negative</small>
    </article>
    <article>
      <span class="metric-label">Baseline F1</span>
      <strong>${data.overall.baseline.f1}%</strong>
      <small>${data.overall.baseline.fn} misses</small>
    </article>
    <article>
      <span class="metric-label">Adaptive F1</span>
      <strong>${data.overall.adaptive.f1}%</strong>
      <small>threshold ${Math.round(data.threshold * 100)}%</small>
    </article>
  `;

  if (data.coverage) {
    $("#real-media-coverage").innerHTML = renderCoverageCards(data.coverage);
  }

  $("#real-media-table").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Condition</th>
          <th>Baseline F1</th>
          <th>Adaptive F1</th>
          <th>Gain</th>
          <th>Pairs</th>
        </tr>
      </thead>
      <tbody>
        ${data.rows
          .map(
            (row) => `
              <tr>
                <td><strong>${row.transformation}</strong></td>
                <td>${row.baseline}%</td>
                <td><strong>${row.cineshield}%</strong></td>
                <td class="gain">${row.gain >= 0 ? "+" : ""}${row.gain}%</td>
                <td>${row.examples}</td>
              </tr>
            `
          )
          .join("")}
      </tbody>
    </table>
  `;

  const sample = data.sampleCase;
  const signalRows = Object.entries(sample.signals)
    .map(
      ([signal, value]) => `
        <div class="signal-row">
          <span>${signal}</span>
          <span class="bar"><i style="--value: ${value}%"></i></span>
          <strong>${value}%</strong>
        </div>
      `
    )
    .join("");
  const weightRows = Object.entries(sample.weights)
    .map(
      ([signal, value]) => `
        <div class="signal-row">
          <span>${signal}</span>
          <span class="bar"><i style="--value: ${value * 2.4}%"></i></span>
          <strong>${value}%</strong>
        </div>
      `
    )
    .join("");

  $("#real-case-title").textContent = `${sample.transformation.replace("_", " ")} case`;
  $("#real-case").innerHTML = `
    <div class="real-case-card">
      <div class="detail-row"><span>Baseline</span><strong>${sample.baseline}%</strong></div>
      <div class="detail-row"><span>Adaptive</span><strong>${sample.adaptive}%</strong></div>
      <span class="path-chip">${sample.video}</span>
    </div>
    <div class="real-case-card">
      <h4>Measured signals</h4>
      <div class="dna-signals">${signalRows}</div>
    </div>
    <div class="real-case-card">
      <h4>Adaptive weights</h4>
      <div class="dna-signals">${weightRows}</div>
    </div>
  `;
}

function setScanProgress(value, label, copy) {
  $("#scan-progress").style.width = `${value}%`;
  $("#scan-headline").textContent = label;
  $("#scan-copy").textContent = copy;
}

function runScan() {
  if (localScanState.protectedFile && localScanState.candidateFiles.length) {
    runLocalScan();
    return;
  }

  if (localScanState.protectedFile && parseListInput($("#candidate-url-input")?.value || "").length) {
    runUrlCandidateScan();
    return;
  }

  const discoveryForm = readDiscoveryForm();
  if (discoveryForm.seedUrls.length) {
    runWebDiscovery();
    return;
  }

  if (discoveryForm.title) {
    runWebSearch();
    return;
  }

  state.stage = "discover";
  renderTimeline();
  $("#scan-status").textContent = "Scanning";
  $("#scan-status").className = "status-pill warning";
  setScanProgress(18, "Sampling fingerprints", "Visual, audio, scene, temporal, OCR, and metadata signals are being compared.");

  const steps = [
    [42, "Detecting transformations", "Compression, crop, watermark, subtitle edits, and partial clips are being profiled."],
    [68, "Fusing evidence", "Adaptive weights are assigned based on the detected transformation profile."],
    [88, "Building source graph", "Related candidates are grouped by content DNA, variant similarity, and distribution pattern."],
    [100, "Search complete", "31 high-confidence matches found across 12 source clusters."]
  ];

  steps.forEach(([value, label, copy], index) => {
    window.setTimeout(() => {
      setScanProgress(value, label, copy);
      state.stage = value < 68 ? "discover" : value < 88 ? "verify" : "graph";
      renderTimeline();
      if (value === 100) {
        $("#scan-status").textContent = "Complete";
        $("#scan-status").className = "status-pill ready";
        state.stage = "graph";
        renderTimeline();
      }
    }, 550 * (index + 1));
  });
}

function generateDna() {
  state.stage = "dna";
  $("#dna-status").textContent = "Generated";
  $("#dna-status").className = "status-pill ready";
  renderDnaSignals();
  renderTimeline();
  document.querySelector("#dna").scrollIntoView({ behavior: "smooth", block: "start" });
}

function selectHighest() {
  state.selectedCandidateId = candidates[0].id;
  state.selectedNodeId = "a";
  state.selectedEdgeId = null;
  state.stage = "investigate";
  renderAll();
  document.querySelector("#casework").scrollIntoView({ behavior: "smooth", block: "start" });
}

function generateCase() {
  state.caseStatus = "Package ready";
  state.stage = "evidence";
  renderCase();
  renderTimeline();
}

function approveCase() {
  state.caseStatus = "Authorized";
  state.stage = "monitor";
  renderCase();
  renderTimeline();
}

function bindControls() {
  $$("[data-action='run-scan']").forEach((button) => button.addEventListener("click", runScan));
  $$("[data-action='run-web-search']").forEach((button) => button.addEventListener("click", runWebSearch));
  $$("[data-action='run-web-discovery']").forEach((button) => button.addEventListener("click", runWebDiscovery));
  $$("[data-action='toggle-web-monitor']").forEach((button) => button.addEventListener("click", toggleWebMonitor));
  $$("[data-action='run-url-candidate-scan']").forEach((button) => button.addEventListener("click", runUrlCandidateScan));
  $$("[data-action='search-internet-for-work']").forEach((button) => button.addEventListener("click", searchInternetForProtectedWork));
  $$("[data-action='generate-dna']").forEach((button) => button.addEventListener("click", generateDna));
  $$("[data-action='select-highest']").forEach((button) => button.addEventListener("click", selectHighest));
  $$("[data-action='generate-case']").forEach((button) => button.addEventListener("click", generateCase));
  $$("[data-action='approve-case']").forEach((button) => button.addEventListener("click", approveCase));
  bindLocalScanner();

  $$("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      state.filter = button.dataset.filter;
      $$("[data-filter]").forEach((item) => item.classList.toggle("active", item === button));
      renderCandidates();
    });
  });

  const sections = $$(".workspace section[id]");
  const navLinks = $$(".nav-link");
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((link) => {
          link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`);
        });
      });
    },
    { rootMargin: "-35% 0px -55% 0px" }
  );
  sections.forEach((section) => observer.observe(section));
}

function renderAll() {
  renderSummaryMetrics();
  renderDnaSignals();
  renderFusionStack();
  renderTimeline();
  renderLocalScanner();
  renderWebDiscovery();
  renderLab();
  renderCandidates();
  renderGraph();
  renderNodeDetail();
  renderInvestigator();
  renderCase();
  renderBenchmark();
  renderRealMediaBenchmark();
}

renderAll();
bindControls();
