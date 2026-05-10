const form = document.querySelector("#downloadForm");
const urlInput = document.querySelector("#url");
const previewButton = document.querySelector("#previewButton");
const previewPanel = document.querySelector("#previewPanel");
const previewImage = document.querySelector("#previewImage");
const previewPlatform = document.querySelector("#previewPlatform");
const previewTitle = document.querySelector("#previewTitle");
const previewMeta = document.querySelector("#previewMeta");
const batchUrlsInput = document.querySelector("#batchUrls");
const profileUsernameInput = document.querySelector("#profileUsername");
const sessionFileInput = document.querySelector("#sessionFile");
const rightsInput = document.querySelector("#rightsConfirmed");
const zipInput = document.querySelector("#makeZip");
const formMessage = document.querySelector("#formMessage");
const serviceStatus = document.querySelector("#serviceStatus");
const jobsList = document.querySelector("#jobsList");
const refreshButton = document.querySelector("#refreshButton");
const template = document.querySelector("#jobTemplate");
const modeTabs = document.querySelectorAll(".mode-tab");
const modePanels = document.querySelectorAll(".mode-panel");

let pollTimer = null;
let activeMode = "single";

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

async function checkHealth() {
  try {
    await requestJson("/api/health");
    serviceStatus.textContent = "Ready";
    serviceStatus.dataset.state = "ready";
  } catch {
    serviceStatus.textContent = "Offline";
    serviceStatus.dataset.state = "failed";
  }
}

async function loadJobs() {
  const payload = await requestJson("/api/jobs");
  renderJobs(payload.jobs || []);
  const active = payload.jobs?.some((job) => ["queued", "running"].includes(job.status));
  if (active && !pollTimer) {
    pollTimer = window.setInterval(loadJobs, 1500);
  }
  if (!active && pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

function renderJobs(jobs) {
  jobsList.replaceChildren();
  if (!jobs.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No jobs yet. Paste a link to create the first archive.";
    jobsList.append(empty);
    return;
  }

  for (const job of jobs) {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector("h3").textContent = job.shortcode || job.id;
    node.querySelector("h3").textContent = job.target || job.shortcode || job.id;
    node.querySelector(".job-url").textContent = job.url || `@${job.owner_username || job.target}`;
    const status = node.querySelector(".job-status");
    status.textContent = job.status;
    status.dataset.state = job.status;
    node.querySelector(".job-message").textContent = job.message || "";
    node.querySelector(".job-meta").textContent = buildMetaLine(job);
    node.querySelector("pre").textContent = (job.log || []).join("\n");

    renderActions(node.querySelector(".job-actions"), job);
    const files = node.querySelector(".job-files");
    renderFiles(files, job);
    jobsList.append(node);
  }
}

function buildMetaLine(job) {
  const parts = [];
  if (job.created_at) parts.push(`Created ${new Date(job.created_at).toLocaleString()}`);
  if (job.platform) parts.push(platformLabel(job.platform));
  if (job.kind) parts.push(job.kind === "profile" ? "Owner archive" : "Post");
  if (job.duplicate_of) parts.push(`Duplicate of ${job.duplicate_of}`);
  if (job.files?.length) parts.push(`${job.files.length} files`);
  const owner = job.metadata?.summary?.owner_username || job.metadata?.owner_username;
  if (owner) parts.push(`@${owner}`);
  return parts.join(" | ");
}

function platformLabel(platform) {
  const labels = {
    instagram: "Instagram",
    twitter: "Twitter/X",
    tiktok: "TikTok",
    snapchat: "Snapchat",
    pinterest: "Pinterest",
    facebook: "Facebook",
    youtube: "YouTube",
  };
  return labels[platform] || platform;
}

function renderFiles(container, job) {
  container.replaceChildren();
  const files = job.files || [];
  if (!files.length) return;

  for (const file of files) {
    const link = document.createElement("a");
    link.href = `/downloads/${job.id}/${encodeURIComponent(file)}`;
    link.textContent = file;
    link.className = file.endsWith(".zip") ? "file-link archive-link" : "file-link";
    link.download = file.split("/").pop();
    container.append(link);
  }
}

function renderActions(container, job) {
  container.replaceChildren();
  if (!job.files?.length) return;

  if (job.archive) {
    const archive = document.createElement("a");
    archive.href = `/downloads/${job.id}/${encodeURIComponent(job.archive)}`;
    archive.textContent = "Save ZIP to browser";
    archive.className = "action-link primary-action";
    archive.download = job.archive;
    container.append(archive);
  }

  const folderNote = document.createElement("span");
  folderNote.className = "save-note";
  folderNote.textContent = "Uses your browser download folder";
  container.append(folderNote);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formMessage.textContent = "";

  try {
    const payload = await submitActiveMode();
    if (payload.jobs) {
      formMessage.textContent = `Started ${payload.jobs.length} jobs.`;
    } else if (payload.job.status === "duplicate") {
      formMessage.textContent = `Already archived as job ${payload.job.duplicate_of}.`;
    } else {
      formMessage.textContent = `Started job ${payload.job.id}.`;
    }
    form.reset();
    zipInput.checked = true;
    setMode(activeMode);
    await loadJobs();
  } catch (error) {
    formMessage.textContent = error.message;
  }
});

previewButton.addEventListener("click", async () => {
  formMessage.textContent = "";
  previewPanel.hidden = true;
  previewButton.disabled = true;
  previewButton.textContent = "Checking";

  try {
    const payload = await requestJson("/api/preview", {
      method: "POST",
      body: JSON.stringify({ url: urlInput.value }),
    });
    renderPreview(payload.preview);
  } catch (error) {
    formMessage.textContent = error.message;
  } finally {
    previewButton.disabled = false;
    previewButton.textContent = "Preview";
  }
});

function renderPreview(preview) {
  previewPanel.hidden = false;
  previewPlatform.textContent = platformLabel(preview.platform);
  previewTitle.textContent = preview.title || "Preview found";
  previewMeta.textContent = [preview.uploader, formatDuration(preview.duration)].filter(Boolean).join(" | ");
  if (preview.thumbnail) {
    previewImage.hidden = false;
    previewImage.src = preview.thumbnail;
    previewImage.alt = preview.title || "Media preview thumbnail";
  } else {
    previewImage.hidden = true;
    previewImage.removeAttribute("src");
  }
}

function formatDuration(duration) {
  if (!duration) return "";
  const total = Number(duration);
  if (!Number.isFinite(total)) return "";
  const minutes = Math.floor(total / 60);
  const seconds = Math.floor(total % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

async function submitActiveMode() {
  const basePayload = {
    rightsConfirmed: rightsInput.checked,
    zip: zipInput.checked,
  };

  if (activeMode === "batch") {
    return requestJson("/api/batch", {
      method: "POST",
      body: JSON.stringify({
        ...basePayload,
        urls: batchUrlsInput.value,
      }),
    });
  }

  if (activeMode === "profile") {
    return requestJson("/api/profile", {
      method: "POST",
      body: JSON.stringify({
        ...basePayload,
        username: profileUsernameInput.value,
        sessionFile: sessionFileInput.value,
      }),
    });
  }

  return requestJson("/api/download", {
    method: "POST",
    body: JSON.stringify({
      ...basePayload,
      url: urlInput.value,
    }),
  });
}

function setMode(mode) {
  activeMode = mode;
  for (const tab of modeTabs) {
    tab.classList.toggle("is-active", tab.dataset.mode === mode);
  }
  for (const panel of modePanels) {
    panel.classList.toggle("is-active", panel.dataset.panel === mode);
  }
}

for (const tab of modeTabs) {
  tab.addEventListener("click", () => setMode(tab.dataset.mode));
}

refreshButton.addEventListener("click", loadJobs);

checkHealth();
loadJobs();
