from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from instagram_archive_studio.downloader import (
    DownloadManager,
    JobStore,
    collect_downloaded_files,
    create_archive,
    detect_platform,
    export_jobs_csv,
    export_jobs_json,
    extract_shortcode,
    validate_supported_url,
    validate_instagram_url,
    validate_username,
)


class UrlValidationTests(unittest.TestCase):
    def test_accepts_supported_instagram_urls(self) -> None:
        url = "https://www.instagram.com/reel/ABC_def-12/"

        self.assertEqual(validate_instagram_url(url), url)
        self.assertEqual(extract_shortcode(url), "ABC_def-12")

    def test_rejects_non_instagram_hosts(self) -> None:
        with self.assertRaises(ValueError):
            validate_instagram_url("https://example.com/reel/ABC/")

    def test_rejects_unsupported_paths(self) -> None:
        with self.assertRaises(ValueError):
            validate_instagram_url("https://www.instagram.com/explore/tags/design/")

    def test_detects_requested_social_platforms(self) -> None:
        examples = {
            "https://x.com/user/status/123": "twitter",
            "https://www.twitter.com/user/status/123": "twitter",
            "https://www.tiktok.com/@user/video/123": "tiktok",
            "https://www.snapchat.com/spotlight/abc": "snapchat",
            "https://www.pinterest.com/pin/123/": "pinterest",
            "https://pin.it/abc": "pinterest",
            "https://www.facebook.com/watch/?v=123": "facebook",
            "https://fb.watch/abc/": "facebook",
            "https://www.youtube.com/watch?v=123": "youtube",
            "https://youtu.be/123": "youtube",
        }

        for url, platform in examples.items():
            with self.subTest(url=url):
                self.assertEqual(detect_platform(url), platform)
                self.assertEqual(validate_supported_url(url)[1], platform)


class JobStoreTests(unittest.TestCase):
    def test_creates_job_folder_and_status_file(self) -> None:
        with TemporaryDirectory() as directory:
            store = JobStore(directory)
            job = store.create("https://www.instagram.com/p/ABC123/")

            self.assertEqual(job.shortcode, "ABC123")
            self.assertTrue(Path(job.output_dir).exists())
            self.assertTrue((Path(job.output_dir) / "job.json").exists())

    def test_creates_non_instagram_job(self) -> None:
        with TemporaryDirectory() as directory:
            store = JobStore(directory)
            job = store.create("https://www.youtube.com/watch?v=VIDEO123")

            self.assertEqual(job.platform, "youtube")
            self.assertEqual(job.kind, "post")
            self.assertIn("youtube.com/watch", job.target)

    def test_collects_files_and_archive(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "media.jpg").write_text("image", encoding="utf-8")
            (root / "job.json").write_text("{}", encoding="utf-8")

            archive_name = create_archive(root)
            files = collect_downloaded_files(root)

            self.assertEqual(archive_name, "archive.zip")
            self.assertIn("media.jpg", files)
            self.assertIn("archive.zip", files)
            self.assertNotIn("job.json", files)


class DownloadManagerTests(unittest.TestCase):
    def test_runs_with_mocked_post_downloader(self) -> None:
        with TemporaryDirectory() as directory:
            store = JobStore(directory)

            def fake_downloader(job) -> None:
                Path(job.output_dir, "media.jpg").write_text("image", encoding="utf-8")
                job.metadata = {"owner_username": "creator", "shortcode": job.shortcode}

            manager = DownloadManager(store, post_downloader=fake_downloader)
            job = store.create("https://www.instagram.com/p/MOCK123/")
            result = manager.run_sync(job, make_zip=True)

            self.assertEqual(result.status, "complete")
            self.assertIn("media.jpg", result.files)
            self.assertIn("archive.zip", result.files)
            self.assertEqual(result.metadata["summary"]["owner_username"], "creator")

    def test_marks_duplicate_completed_post(self) -> None:
        with TemporaryDirectory() as directory:
            store = JobStore(directory)

            def fake_downloader(job) -> None:
                Path(job.output_dir, "media.jpg").write_text("image", encoding="utf-8")

            manager = DownloadManager(store, post_downloader=fake_downloader)
            first = store.create("https://www.instagram.com/p/DUP123/")
            manager.run_sync(first, make_zip=False)
            duplicate = manager.start("https://www.instagram.com/p/DUP123/", make_zip=False)

            self.assertEqual(duplicate.status, "duplicate")
            self.assertEqual(duplicate.duplicate_of, first.id)

    def test_runs_with_mocked_profile_downloader(self) -> None:
        with TemporaryDirectory() as directory:
            store = JobStore(directory)

            def fake_profile_downloader(job) -> None:
                Path(job.output_dir, "profile.json").write_text("{}", encoding="utf-8")
                job.metadata = {"owner_username": job.owner_username, "mediacount": 1}

            manager = DownloadManager(store, profile_downloader=fake_profile_downloader)
            job = store.create_profile_archive("brand.account")
            result = manager.run_sync(job, make_zip=False)

            self.assertEqual(result.status, "complete")
            self.assertEqual(result.kind, "profile")
            self.assertIn("profile.json", result.files)

    def test_runs_with_mocked_generic_downloader(self) -> None:
        with TemporaryDirectory() as directory:
            store = JobStore(directory)

            def fake_generic_downloader(job) -> None:
                Path(job.output_dir, "video.mp4").write_text("video", encoding="utf-8")
                job.metadata = {"platform": job.platform, "title": "Example video"}

            manager = DownloadManager(store, generic_downloader=fake_generic_downloader)
            job = store.create("https://www.youtube.com/watch?v=MOCK123")
            result = manager.run_sync(job, make_zip=False)

            self.assertEqual(result.status, "complete")
            self.assertEqual(result.platform, "youtube")
            self.assertIn("video.mp4", result.files)
            self.assertEqual(result.metadata["summary"]["title"], "Example video")

    def test_marks_duplicate_non_instagram_url(self) -> None:
        with TemporaryDirectory() as directory:
            store = JobStore(directory)

            def fake_generic_downloader(job) -> None:
                Path(job.output_dir, "video.mp4").write_text("video", encoding="utf-8")

            manager = DownloadManager(store, generic_downloader=fake_generic_downloader)
            first = store.create("https://www.youtube.com/watch?v=DUP123")
            manager.run_sync(first, make_zip=False)
            duplicate = manager.start("https://www.youtube.com/watch?v=DUP123", make_zip=False)

            self.assertEqual(duplicate.status, "duplicate")
            self.assertEqual(duplicate.duplicate_of, first.id)


class ExportTests(unittest.TestCase):
    def test_exports_jobs_to_json_and_csv(self) -> None:
        with TemporaryDirectory() as directory:
            store = JobStore(Path(directory) / "downloads")
            job = store.create("https://www.instagram.com/p/EXP123/")
            job.status = "complete"
            store.save(job)

            json_path = export_jobs_json(store.list(), Path(directory) / "jobs.json")
            csv_path = export_jobs_csv(store.list(), Path(directory) / "jobs.csv")

            self.assertIn('"EXP123"', json_path.read_text(encoding="utf-8"))
            self.assertIn("file_count", csv_path.read_text(encoding="utf-8"))


class ProfileValidationTests(unittest.TestCase):
    def test_validates_username(self) -> None:
        self.assertEqual(validate_username("@brand.account"), "brand.account")
        with self.assertRaises(ValueError):
            validate_username("bad/user")


if __name__ == "__main__":
    unittest.main()
