const form = document.querySelector("#downloadForm");
const urlInput = document.querySelector("#url");
const previewButton = document.querySelector("#previewButton");
const previewPanel = document.querySelector("#previewPanel");
const previewImage = document.querySelector("#previewImage");
const previewPlatform = document.querySelector("#previewPlatform");
const previewTitle = document.querySelector("#previewTitle");
const previewMeta = document.querySelector("#previewMeta");
const qualityLabel = document.getElementById("qualityLabel");
const qualitySelect = document.getElementById("qualitySelect");
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

let jobsHidden = false;

async function loadJobs() {
  if (jobsHidden) return; // Don't render jobs if hidden
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

document.getElementById("clearJobsViewButton")?.addEventListener("click", () => {
  fetch("/api/archive_jobs", { method: "POST" })
    .then((res) => res.json())
    .then((result) => {
      if (result.archived) {
        formMessage.textContent = "Jobs archived. You can start a new session.";
      } else {
        formMessage.textContent = result.message || result.error || "No jobs to archive.";
      }
      loadJobs();
    })
    .catch(() => {
      formMessage.textContent = "Failed to archive jobs.";
    });
});

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

    // Progress bar logic
    const progressBarContainer = node.querySelector('.progress-bar-container');
    const progressBar = node.querySelector('.progress-bar');
    let percent = null;
    // Try to extract percent from job.message (yt-dlp style)
    if (job.status === 'running' && job.message) {
      const match = job.message.match(/\b(\d{1,3}\.\d)%/);
      if (match) {
        percent = parseFloat(match[1]);
      }
    }
    if (job.status === 'running') {
      progressBarContainer.style.display = 'block';
      if (percent !== null && percent >= 0 && percent <= 100) {
        progressBar.style.width = percent + '%';
      } else {
        progressBar.style.width = '5%';
      }
    } else {
      progressBarContainer.style.display = 'none';
      progressBar.style.width = '0%';
    }

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

  // Restart job with different format (for YouTube)
  if (job.platform === "youtube" && Array.isArray(job.metadata?.formats) && job.metadata.formats.length > 0) {
    const restartDiv = document.createElement("div");
    restartDiv.style.marginTop = "8px";
    const restartLabel = document.createElement("label");
    restartLabel.textContent = "Restart with different quality:";
    restartLabel.style.marginRight = "6px";
    const restartSelect = document.createElement("select");
    for (const f of job.metadata.formats) {
      const label = `${f.height || ''}p${f.format_note ? ' ' + f.format_note : ''}${f.filesize ? ` (${(f.filesize/1048576).toFixed(1)}MB)` : ''} — ${f.audio_label || ''}`;
      const opt = document.createElement("option");
      opt.value = f.format_id;
      opt.textContent = label;
      restartSelect.appendChild(opt);
    }
    const restartBtn = document.createElement("button");
    restartBtn.textContent = "Restart";
    restartBtn.type = "button";
    restartBtn.className = "ghost-button";
    restartBtn.onclick = async () => {
      restartBtn.disabled = true;
      restartBtn.textContent = "Restarting...";
      try {
        const res = await fetch("/api/download", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: job.url,
            rightsConfirmed: true,
            zip: true,
            format_id: restartSelect.value,
          }),
        });
        const payload = await res.json();
        if (payload.job && payload.job.id) {
          formMessage.textContent = `Restarted as job ${payload.job.id}.`;
          await loadJobs();
        } else {
          formMessage.textContent = payload.error || "Failed to restart job.";
        }
      } catch (e) {
        formMessage.textContent = "Failed to restart job.";
      } finally {
        restartBtn.disabled = false;
        restartBtn.textContent = "Restart";
      }
    };
    restartDiv.appendChild(restartLabel);
    restartDiv.appendChild(restartSelect);
    restartDiv.appendChild(restartBtn);
    container.append(restartDiv);
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
    // Add note about video-only formats
    const noteId = "videoAudioNote";
    let note = document.getElementById(noteId);
    if (!note) {
      note = document.createElement("div");
      note.id = noteId;
      note.style.fontSize = "0.95em";
      note.style.color = "#666";
      note.style.margin = "6px 0 0 0";
      qualityLabel.parentNode.insertBefore(note, qualityLabel.nextSibling);
    }
    if (preview.platform === "youtube") {
      note.textContent = "Note: If you select a 'Video only' format, the app will automatically merge it with the best available audio.";
      note.style.display = "block";
    } else {
      note.textContent = "";
      note.style.display = "none";
    }
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
  // Quality selector for YouTube
  if (preview.platform === "youtube" && Array.isArray(preview.formats) && preview.formats.length > 0) {
      qualityLabel.style.display = "inline-block";
      qualitySelect.innerHTML = "";
      // Sort by height descending
      const sorted = [...preview.formats].sort((a, b) => (b.height || 0) - (a.height || 0));
      for (const f of sorted) {
        let res = f.height ? `${f.height}p` : '';
        let note = f.format_note || '';
        // Avoid duplicated resolution (e.g., '2160p 2160p')
        let showRes = res && (!note || !note.includes(res));
        let label = `${showRes ? res : ''}${note ? ' ' + note : ''}${f.filesize ? ` (${(f.filesize/1048576).toFixed(1)}MB)` : ''} — ${f.audio_label || ''}`.trim();
        const opt = document.createElement("option");
        opt.value = f.format_id;
        opt.textContent = label;
        qualitySelect.appendChild(opt);
      }
  } else {
    qualityLabel.style.display = "none";
    qualitySelect.innerHTML = "";
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

  // Add format_id for YouTube if selected
  let format_id = null;
  if (qualityLabel.style.display !== "none" && qualitySelect.value) {
    format_id = qualitySelect.value;
  }

  return requestJson("/api/download", {
    method: "POST",
    body: JSON.stringify({
      ...basePayload,
      url: urlInput.value,
      ...(format_id ? { format_id } : {}),
    }),
  });
}

function setMode(mode) {
  activeMode = mode;
  for (const tab of modeTabs) {
    tab.classList.toggle("is-active", tab.dataset.mode === mode);
  }
      for (const f of job.metadata.formats) {
        let res = f.height ? `${f.height}p` : '';
        let note = f.format_note || '';
        let showRes = res && (!note || !note.includes(res));
        let label = `${showRes ? res : ''}${note ? ' ' + note : ''}${f.filesize ? ` (${(f.filesize/1048576).toFixed(1)}MB)` : ''} — ${f.audio_label || ''}`.trim();
        const opt = document.createElement("option");
        opt.value = f.format_id;
        opt.textContent = label;
        restartSelect.appendChild(opt);
      }
}

refreshButton.addEventListener("click", loadJobs);

checkHealth();
loadJobs();
