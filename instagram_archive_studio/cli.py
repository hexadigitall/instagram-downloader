from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .downloader import DownloadManager, JobStore, export_jobs_csv, export_jobs_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download permitted social media into a local archive.")
    parser.add_argument("url", nargs="?", help="Supported social media URL")
    parser.add_argument("--batch-file", help="Text file with one supported social media URL per line")
    parser.add_argument("--profile", help="Archive an Instagram profile you own or manage")
    parser.add_argument("--session-file", help="Local Instaloader session file for owner archives")
    parser.add_argument("--downloads", default="downloads", help="Download directory")
    parser.add_argument("--no-zip", action="store_true", help="Skip ZIP archive creation")
    parser.add_argument("--export-json", help="Export job history to a JSON file and exit")
    parser.add_argument("--export-csv", help="Export job history to a CSV file and exit")
    parser.add_argument("--yes-i-have-rights", action="store_true", help="Confirm you have rights or permission")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    store = JobStore(Path(args.downloads))
    manager = DownloadManager(store)

    if args.export_json:
        path = export_jobs_json(store.list(), Path(args.export_json))
        print(f"Exported JSON to {path}")
        return 0
    if args.export_csv:
        path = export_jobs_csv(store.list(), Path(args.export_csv))
        print(f"Exported CSV to {path}")
        return 0

    if not args.yes_i_have_rights:
        print("Refusing to start until rights are confirmed. Re-run with --yes-i-have-rights.")
        return 2

    if args.profile:
        job = manager.start_profile_archive(args.profile, session_file=args.session_file, make_zip=not args.no_zip)
        print(f"Started profile archive job {job.id}")
        return wait_for_jobs(store, [job.id])

    if args.batch_file:
        urls = [line.strip() for line in Path(args.batch_file).read_text(encoding="utf-8").splitlines() if line.strip()]
        jobs = manager.start_many(urls, make_zip=not args.no_zip)
        print(f"Started {len(jobs)} jobs")
        return wait_for_jobs(store, [job.id for job in jobs])

    if not args.url:
        parser.error("provide a URL, --batch-file, --profile, --export-json, or --export-csv")

    job = manager.start(args.url, make_zip=not args.no_zip)
    if job.status == "duplicate":
        print(f"Duplicate of completed job {job.duplicate_of}")
        return 0
    print(f"Started job {job.id}")
    return wait_for_jobs(store, [job.id])


def wait_for_jobs(store: JobStore, job_ids: list[str]) -> int:
    complete: set[str] = set()
    failed = False

    while True:
        for job_id in job_ids:
            if job_id in complete:
                continue
            current = store.get(job_id)
            if current is None:
                print(f"{job_id}: job disappeared.")
                failed = True
                complete.add(job_id)
                continue
            print(f"{current.id} {current.status}: {current.message}")
            if current.status not in {"complete", "failed", "duplicate"}:
                continue
            complete.add(job_id)
            if current.status == "complete":
                print(f"Saved to: {current.output_dir}")
                if current.archive:
                    print(f"Archive: {current.archive}")
            elif current.status == "duplicate":
                print(f"Duplicate of completed job {current.duplicate_of}")
            else:
                print("\n".join(current.log[-4:]))
                failed = True
        if len(complete) == len(job_ids):
            return 1 if failed else 0
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
