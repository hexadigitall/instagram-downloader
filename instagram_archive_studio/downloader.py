from __future__ import annotations

import json
import re
import shutil
import threading
import traceback
import csv
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import uuid4


INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
SHORTCODE_RE = re.compile(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)/?")
USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
Downloader = Callable[["Job"], None]


class DownloadError(RuntimeError):
    """Raised when a download job cannot be completed."""


@dataclass
class Job:
    id: str
    url: str = ""
    kind: str = "post"
    target: str = ""
    status: str = "queued"
    created_at: str = field(default_factory=lambda: utc_now())
    updated_at: str = field(default_factory=lambda: utc_now())
    message: str = "Waiting to start"
    output_dir: str = ""
    shortcode: str | None = None
    duplicate_of: str | None = None
    session_file: str | None = None
    owner_username: str | None = None
    files: list[str] = field(default_factory=list)
    archive: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)

    def touch(self, message: str | None = None) -> None:
        self.updated_at = utc_now()
        if message is not None:
            self.message = message

    def add_log(self, message: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.log.append(f"{stamp}Z {message}")
        self.touch(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_instagram_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("Paste an Instagram post, Reel, or video URL.")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must start with http:// or https://.")

    host = parsed.netloc.lower()
    if host not in INSTAGRAM_HOSTS:
        raise ValueError("Only instagram.com URLs are supported.")

    if not SHORTCODE_RE.search(parsed.path):
        raise ValueError("Use a public Instagram post, Reel, or video URL.")

    return url


def extract_shortcode(url: str) -> str:
    match = SHORTCODE_RE.search(urlparse(url).path)
    if not match:
        raise ValueError("Could not find an Instagram shortcode in the URL.")
    return match.group(1)


def validate_username(raw_username: str) -> str:
    username = raw_username.strip().lstrip("@")
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Use a valid Instagram username.")
    return username


class JobStore:
    def __init__(self, root: Path | str = "downloads") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()
        self._load_existing_jobs()

    def create(self, url: str) -> Job:
        clean_url = validate_instagram_url(url)
        shortcode = extract_shortcode(clean_url)
        job_id = uuid4().hex[:12]
        output_dir = self.root / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{shortcode}_{job_id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        job = Job(
            id=job_id,
            url=clean_url,
            kind="post",
            target=shortcode,
            shortcode=shortcode,
            output_dir=str(output_dir),
        )
        duplicate = self.find_completed_post(shortcode)
        if duplicate:
            job.duplicate_of = duplicate.id
            job.add_log(f"Matches completed job {duplicate.id}")
        job.add_log("Job created")
        with self._lock:
            self._jobs[job.id] = job
            self.save(job)
        return job

    def create_profile_archive(self, username: str, session_file: str | None = None) -> Job:
        clean_username = validate_username(username)
        clean_session = str(Path(session_file).expanduser().resolve()) if session_file else None
        if clean_session and not Path(clean_session).is_file():
            raise ValueError("Session file does not exist.")
        job_id = uuid4().hex[:12]
        output_dir = self.root / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{clean_username}_{job_id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        job = Job(
            id=job_id,
            kind="profile",
            target=clean_username,
            owner_username=clean_username,
            session_file=clean_session,
            output_dir=str(output_dir),
        )
        job.add_log("Profile archive job created")
        with self._lock:
            self._jobs[job.id] = job
            self.save(job)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)

    def find_completed_post(self, shortcode: str) -> Job | None:
        with self._lock:
            for job in self._jobs.values():
                if job.kind == "post" and job.shortcode == shortcode and job.status == "complete":
                    return job
        return None

    def save(self, job: Job) -> None:
        job_path = Path(job.output_dir) / "job.json"
        job_path.write_text(json.dumps(asdict(job), indent=2), encoding="utf-8")

    def _load_existing_jobs(self) -> None:
        for job_file in self.root.glob("*/job.json"):
            try:
                data = json.loads(job_file.read_text(encoding="utf-8"))
                job = Job(**data)
                self._jobs[job.id] = job
            except Exception:
                continue


class DownloadManager:
    def __init__(
        self,
        store: JobStore,
        post_downloader: Downloader | None = None,
        profile_downloader: Downloader | None = None,
    ) -> None:
        self.store = store
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        self.post_downloader = post_downloader or download_instagram_post
        self.profile_downloader = profile_downloader or download_instagram_profile

    def start(self, url: str, make_zip: bool = True) -> Job:
        job = self.store.create(url)
        if job.duplicate_of:
            duplicate = self.store.get(job.duplicate_of)
            job.status = "duplicate"
            job.files = duplicate.files if duplicate else []
            job.archive = duplicate.archive if duplicate else None
            job.touch("Already archived")
            self.store.save(job)
            return job
        thread = threading.Thread(target=self._run_job, args=(job.id, make_zip), daemon=True)
        with self._lock:
            self._threads[job.id] = thread
        thread.start()
        return job

    def start_many(self, urls: list[str], make_zip: bool = True) -> list[Job]:
        jobs = []
        seen: set[str] = set()
        for url in urls:
            clean_url = validate_instagram_url(url)
            if clean_url in seen:
                continue
            seen.add(clean_url)
            jobs.append(self.start(clean_url, make_zip=make_zip))
        return jobs

    def start_profile_archive(self, username: str, session_file: str | None = None, make_zip: bool = True) -> Job:
        job = self.store.create_profile_archive(username, session_file=session_file)
        thread = threading.Thread(target=self._run_job, args=(job.id, make_zip), daemon=True)
        with self._lock:
            self._threads[job.id] = thread
        thread.start()
        return job

    def run_sync(self, job: Job, make_zip: bool = True) -> Job:
        self._run_job(job.id, make_zip=make_zip)
        current = self.store.get(job.id)
        if not current:
            raise DownloadError("Job disappeared.")
        return current

    def _run_job(self, job_id: str, make_zip: bool) -> None:
        job = self.store.get(job_id)
        if not job:
            return

        try:
            job.status = "running"
            job.add_log("Starting download")
            self.store.save(job)

            if job.kind == "profile":
                self.profile_downloader(job)
            else:
                self.post_downloader(job)

            summary_metadata = dict(job.metadata)
            job.files = collect_downloaded_files(Path(job.output_dir))
            job.metadata = {
                "summary": summary_metadata,
                "instaloader": load_instaloader_metadata(Path(job.output_dir)),
            }
            if make_zip:
                job.archive = create_archive(Path(job.output_dir))
                job.files = collect_downloaded_files(Path(job.output_dir))
            job.status = "complete"
            job.add_log("Download complete")
        except Exception as exc:
            job.status = "failed"
            job.add_log(str(exc))
            job.log.append(traceback.format_exc())
        finally:
            self.store.save(job)


def download_instagram_post(job: Job) -> None:
    try:
        import instaloader
    except ImportError as exc:
        raise DownloadError("Install dependencies with: python -m pip install -r requirements.txt") from exc

    output_dir = Path(job.output_dir)
    loader = instaloader.Instaloader(
        dirname_pattern=str(output_dir),
        download_comments=False,
        download_geotags=False,
        download_pictures=True,
        download_video_thumbnails=True,
        save_metadata=True,
        compress_json=False,
        quiet=True,
    )
    load_session_if_requested(loader, job)

    shortcode = job.shortcode or extract_shortcode(job.url)
    post = instaloader.Post.from_shortcode(loader.context, shortcode)

    job.metadata = {
        "shortcode": shortcode,
        "owner_username": getattr(post.owner_profile, "username", None),
        "caption": post.caption,
        "date_utc": post.date_utc.isoformat() if post.date_utc else None,
        "is_video": post.is_video,
        "typename": post.typename,
        "url": job.url,
    }
    job.add_log(f"Resolved @{job.metadata.get('owner_username') or 'unknown'}")
    loader.download_post(post, target=shortcode)


def download_instagram_profile(job: Job) -> None:
    try:
        import instaloader
    except ImportError as exc:
        raise DownloadError("Install dependencies with: python -m pip install -r requirements.txt") from exc

    username = validate_username(job.owner_username or job.target)
    output_dir = Path(job.output_dir)
    loader = instaloader.Instaloader(
        dirname_pattern=str(output_dir / "{profile}"),
        download_comments=False,
        download_geotags=False,
        download_pictures=True,
        download_video_thumbnails=True,
        save_metadata=True,
        compress_json=False,
        quiet=True,
    )
    load_session_if_requested(loader, job)
    profile = instaloader.Profile.from_username(loader.context, username)
    if not profile.is_private and profile.username.lower() != username.lower():
        raise DownloadError("Could not resolve the requested profile.")
    job.metadata = {
        "owner_username": profile.username,
        "full_name": profile.full_name,
        "biography": profile.biography,
        "followers": profile.followers,
        "followees": profile.followees,
        "mediacount": profile.mediacount,
        "url": f"https://www.instagram.com/{profile.username}/",
    }
    job.add_log(f"Resolved owner archive @{profile.username}")
    loader.download_profile(profile.username, profile_pic=True, fast_update=True)


def load_session_if_requested(loader: Any, job: Job) -> None:
    if not job.session_file:
        return
    username = job.owner_username or job.target
    loader.load_session_from_file(username, filename=job.session_file)
    job.add_log("Loaded local Instaloader session file")


def collect_downloaded_files(output_dir: Path) -> list[str]:
    files: list[str] = []
    for path in output_dir.rglob("*"):
        if path.is_file() and path.name != "job.json":
            files.append(str(path.relative_to(output_dir)).replace("\\", "/"))
    return sorted(files)


def load_instaloader_metadata(output_dir: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for path in output_dir.rglob("*.json"):
        if path.name == "job.json":
            continue
        try:
            metadata[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return metadata


def create_archive(output_dir: Path) -> str:
    temp_base = output_dir.parent / f"{output_dir.name}_archive"
    archive_path = Path(shutil.make_archive(str(temp_base), "zip", root_dir=output_dir))
    final_path = output_dir / "archive.zip"
    if final_path.exists():
        final_path.unlink()
    archive_path.replace(final_path)
    return final_path.name


def export_jobs_json(jobs: list[Job], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps([asdict(job) for job in jobs], indent=2), encoding="utf-8")
    return destination


def export_jobs_csv(jobs: list[Job], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "kind",
        "status",
        "target",
        "url",
        "shortcode",
        "owner_username",
        "duplicate_of",
        "created_at",
        "updated_at",
        "file_count",
        "archive",
        "message",
    ]
    with destination.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for job in jobs:
            writer.writerow(
                {
                    "id": job.id,
                    "kind": job.kind,
                    "status": job.status,
                    "target": job.target,
                    "url": job.url,
                    "shortcode": job.shortcode,
                    "owner_username": job.owner_username,
                    "duplicate_of": job.duplicate_of,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "file_count": len(job.files),
                    "archive": job.archive,
                    "message": job.message,
                }
            )
    return destination
