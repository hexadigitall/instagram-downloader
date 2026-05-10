from __future__ import annotations

import json
import mimetypes
import tempfile
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .downloader import DownloadManager, JobStore, export_jobs_csv, export_jobs_json


APP_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = APP_ROOT / "static"
DOWNLOAD_ROOT = Path("downloads").resolve()
STORE = JobStore(DOWNLOAD_ROOT)
MANAGER = DownloadManager(STORE)


class AppHandler(BaseHTTPRequestHandler):
    server_version = "InstagramArchiveStudio/0.1"

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_static("index.html", head_only=True)
        elif parsed.path.startswith("/static/"):
            self.send_static(parsed.path.removeprefix("/static/"), head_only=True)
        elif parsed.path == "/api/health":
            self.send_json({"ok": True, "service": "Instagram Archive Studio"}, head_only=True)
        elif parsed.path == "/api/export/jobs.json":
            self.handle_export("json", head_only=True)
        elif parsed.path == "/api/export/jobs.csv":
            self.handle_export("csv", head_only=True)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_static("index.html")
        elif parsed.path.startswith("/static/"):
            self.send_static(parsed.path.removeprefix("/static/"))
        elif parsed.path == "/api/health":
            self.send_json({"ok": True, "service": "Instagram Archive Studio"})
        elif parsed.path == "/api/jobs":
            self.send_json({"jobs": [asdict(job) for job in STORE.list()]})
        elif parsed.path == "/api/export/jobs.json":
            self.handle_export("json")
        elif parsed.path == "/api/export/jobs.csv":
            self.handle_export("csv")
        elif parsed.path.startswith("/api/jobs/"):
            self.handle_job(parsed.path)
        elif parsed.path.startswith("/downloads/"):
            self.handle_download(parsed.path)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/download":
            self.handle_start_download()
        elif parsed.path == "/api/batch":
            self.handle_start_batch()
        elif parsed.path == "/api/profile":
            self.handle_start_profile_archive()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def handle_start_download(self) -> None:
        try:
            body = self.read_json()
            if not body.get("rightsConfirmed"):
                self.send_json({"error": "Confirm that you own the content or have permission to save it."}, 400)
                return
            url = str(body.get("url", ""))
            make_zip = bool(body.get("zip", True))
            job = MANAGER.start(url, make_zip=make_zip)
            status = 200 if job.status == "duplicate" else 202
            self.send_json({"job": asdict(job)}, status)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def handle_start_batch(self) -> None:
        try:
            body = self.read_json()
            if not body.get("rightsConfirmed"):
                self.send_json({"error": "Confirm that you own the content or have permission to save it."}, 400)
                return
            urls = body.get("urls", [])
            if isinstance(urls, str):
                urls = [line.strip() for line in urls.splitlines() if line.strip()]
            if not isinstance(urls, list) or not urls:
                self.send_json({"error": "Add at least one Instagram URL."}, 400)
                return
            make_zip = bool(body.get("zip", True))
            jobs = MANAGER.start_many([str(url) for url in urls], make_zip=make_zip)
            self.send_json({"jobs": [asdict(job) for job in jobs]}, 202)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def handle_start_profile_archive(self) -> None:
        try:
            body = self.read_json()
            if not body.get("rightsConfirmed"):
                self.send_json({"error": "Confirm that you own or manage this profile before archiving it."}, 400)
                return
            username = str(body.get("username", ""))
            session_file = body.get("sessionFile")
            make_zip = bool(body.get("zip", True))
            job = MANAGER.start_profile_archive(username, session_file=str(session_file) if session_file else None, make_zip=make_zip)
            self.send_json({"job": asdict(job)}, 202)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def handle_job(self, path: str) -> None:
        job_id = path.rsplit("/", 1)[-1]
        job = STORE.get(job_id)
        if not job:
            self.send_json({"error": "Job not found"}, 404)
            return
        self.send_json({"job": asdict(job)})

    def handle_export(self, format_name: str, head_only: bool = False) -> None:
        export_dir = Path(tempfile.gettempdir()) / "instagram_archive_studio_exports"
        if format_name == "json":
            path = export_jobs_json(STORE.list(), export_dir / "jobs.json")
            self.send_file(path, "application/json", "jobs.json", head_only=head_only)
            return
        path = export_jobs_csv(STORE.list(), export_dir / "jobs.csv")
        self.send_file(path, "text/csv", "jobs.csv", head_only=head_only)

    def handle_download(self, path: str) -> None:
        parts = unquote(path).split("/", 3)
        if len(parts) < 4:
            self.send_error(HTTPStatus.NOT_FOUND, "Missing file path")
            return

        job = STORE.get(parts[2])
        if not job:
            self.send_error(HTTPStatus.NOT_FOUND, "Job not found")
            return

        requested = Path(job.output_dir, parts[3]).resolve()
        output_dir = Path(job.output_dir).resolve()
        if output_dir not in requested.parents and requested != output_dir:
            self.send_error(HTTPStatus.FORBIDDEN, "Invalid path")
            return
        if not requested.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(requested.stat().st_size))
        self.send_header("Content-Disposition", f'attachment; filename="{requested.name}"')
        self.end_headers()
        with requested.open("rb") as file:
            self.wfile.write(file.read())

    def send_file(self, path: Path, content_type: str, filename: str, head_only: bool = False) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        if head_only:
            return
        with path.open("rb") as file:
            self.wfile.write(file.read())

    def send_static(self, relative_path: str, head_only: bool = False) -> None:
        requested = (STATIC_ROOT / relative_path).resolve()
        if STATIC_ROOT not in requested.parents and requested != STATIC_ROOT:
            self.send_error(HTTPStatus.FORBIDDEN, "Invalid path")
            return
        if not requested.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return

        content_type = mimetypes.guess_type(requested.name)[0] or "text/plain"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(requested.stat().st_size))
        self.end_headers()
        if head_only:
            return
        with requested.open("rb") as file:
            self.wfile.write(file.read())

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        payload = self.rfile.read(length).decode("utf-8")
        return json.loads(payload)

    def send_json(self, payload: dict, status: int = 200, head_only: bool = False) -> None:
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if head_only:
            return
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        print("%s - %s" % (self.address_string(), format % args))


def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Instagram Archive Studio running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
