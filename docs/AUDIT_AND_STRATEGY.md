# Audit And Strategy

## Current State

Before implementation, the project contained only `requirements.txt`. There was no application code, no interface, no CLI, no tests, no README, no product flow, no compliance positioning, and no business strategy.

Based on the dependencies, the intended project was a Python Instagram downloader using `instaloader`, requests, Selenium, browser-user-agent tools, and CLI helpers. That dependency set suggested a tool that could download Instagram media, potentially with browser automation, progress display, and metadata handling.

## What The Product Is Meant To Be

The strongest product interpretation is:

Social Archive Studio is a local-first tool for saving permitted Instagram, Twitter/X, TikTok, Snapchat, Pinterest, Facebook, and YouTube media into organized folders with metadata, history, and exports.

The responsible market position is not "download anything from anyone." The better product is "archive content you own, manage, licensed, or have permission to save." That framing improves trust, reduces platform-policy risk, and gives the product a clearer customer.

## User-Side Feature Requirements

### Interface

- Paste-first input for supported social media URLs.
- Clear content-rights confirmation before downloading.
- Status area showing queued, running, complete, and failed jobs.
- Result cards with file counts, metadata, log, and ZIP/download links.
- Local history so users can return to previous jobs.
- No credential collection in the browser UI.

### Experience

- The first screen must be the tool, not a marketing landing page.
- Copy should be direct and confidence-building.
- Errors must explain what the user can do next.
- The app should support both casual users and power users.

### Site Flow

1. User lands on the app.
2. User pastes a supported social media URL.
3. User confirms rights.
4. App starts a background job.
5. User sees progress and final files.
6. User can open the folder, download a ZIP, or start another job.

### Efficiency And Speed

- Use background jobs so the UI remains responsive.
- Store only per-job state in memory and JSON files.
- Avoid browser automation for the default path.
- Prefer `instaloader` for Instagram owner archive workflows.
- Prefer `yt-dlp` for non-Instagram media URLs.
- Add rate limits, account session support, and queue controls before scaling beyond local use.

### Relevance

Demand exists because short-form video is now central to creator research, offline reference libraries, UGC approval workflows, and brand asset collection. The most relevant audience is not people trying to bypass platform controls; it is people managing content libraries.

## Business Sense

### Audience

- Independent creators archiving their own Reels and posts.
- Social media managers collecting approved brand assets.
- Agencies organizing client-approved UGC.
- Researchers and educators saving permitted public examples.
- Small businesses preserving their own Instagram catalog.

### Potential

The category has durable demand, but a generic downloader is easy to copy and can attract policy risk. A more defensible product adds workflow: rights tracking, approvals, metadata, exports, client folders, content calendars, captions, thumbnails, and backup scheduling.

### USP

"The compliant Instagram archive workflow for creators and agencies."

Differentiators:

- Local-first privacy.
- Rights confirmation and audit trail.
- Creator/client library organization.
- Exportable metadata.
- Batch workflows for approved content.
- No shady credential capture.

### Sales And Pricing Strategy

- Free: Local single-link downloader, manual jobs, ZIP export.
- Pro at $9-15/month: Batch queues, saved collections, duplicate detection, captions export, scheduled owner backups.
- Studio at $29-49/month: Client workspaces, approval notes, team seats, CSV exports, brand folders.
- Agency at $99+/month: Multi-client libraries, audit logs, API/export hooks, white-label reports.

The project should validate willingness to pay with agencies and creators before investing in cloud infrastructure.

### Growth Potential

Best growth loops:

- Creator backup checklist content across major social platforms.
- Agency asset-management templates.
- Browser extension for "save to approved library."
- Integrations with Google Drive, Dropbox, Notion, Airtable, and content calendars.
- Caption and thumbnail extraction for repurposing workflows.

### Additional Services

- Content library setup for creators.
- Agency migration from scattered folders to structured asset libraries.
- UGC rights-management consulting.
- Backup automation for brand-owned profiles.

### Risks

- Meta/Instagram policy enforcement against automated collection.
- Fragile downloader behavior when Instagram changes markup or endpoints.
- User misuse.
- Copyright and privacy complaints.
- Dependency churn in `instaloader`.

Mitigations:

- Keep use narrow and user-directed.
- Avoid stealth or anti-detection features.
- Require rights confirmation.
- Add clear terms before public launch.
- Build official-API or user-export flows where possible.

## Implementation Roadmap

### Built In This Version

- Local web app.
- CLI downloader.
- Job lifecycle with status files.
- URL validation.
- Metadata and logs.
- ZIP creation.
- Batch queue interface for supported social URLs.
- Duplicate detection by Instagram shortcode.
- Owner profile archive workflow using local Instaloader session files.
- Twitter/X, TikTok, Snapchat, Pinterest, Facebook, and YouTube URL support through `yt-dlp`.
- CSV and JSON exports.
- Mocked downloader tests.
- Python package metadata and WSL installer script.
- Placeholder Terms, Privacy, and Acceptable Use pages.
- Product README and strategy document.

### Next Needed To Make It Production-Grade

- Real progress callbacks from download hooks.
- Duplicate detection by media hash, not only shortcode/canonical URL.
- Session setup assistant that helps users create Instaloader sessions locally without collecting passwords in the web app.
- Searchable local library view.
- Rate-limit controls and retry backoff.
- Counsel-reviewed legal terms, privacy policy, and abuse-report channel.
- Installer packaging for Windows/macOS.
- Optional cloud product with account billing and storage integrations.

## Technical Notes

The first version uses Python's standard-library HTTP server to avoid introducing a framework before the product shape is proven. If this grows, move the backend to FastAPI and the frontend to a typed framework only when the local product needs richer state management, auth, or multiple users.
