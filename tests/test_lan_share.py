from __future__ import annotations

import http.client
import io
import ipaddress
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import urlsplit

import zxingcpp
from PIL import Image

from areagrab.i18n import CODES, translate
from areagrab.lan_adapters import Adapter, parse_adapters
from areagrab.lan_share import SharedImage, ShareSession, qr_image
from areagrab.share_source import ShareSource, file_identity

LOOPBACK = Adapter(ipaddress.IPv4Interface("127.0.0.1/32"), "test")


def encoded(image, format):
    output = io.BytesIO()
    image.save(output, format=format)
    return output.getvalue()


class LanShareTests(unittest.TestCase):
    def share(self, content, ttl=20, language="en", adapter=LOOPBACK):
        image = SharedImage.load(ShareSource(content, None))
        session = ShareSession(image, adapter, ttl, language)
        self.addCleanup(self.close, session)
        return session

    def close(self, session):
        session.stop()
        self.assertTrue(session.wait_closed(5))

    def request(self, session, suffix="", *, target=None, method="GET", headers=None):
        url = urlsplit(session.url)
        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=4)
        try:
            connection.request(method, target or url.path + suffix, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_qr_decodes_to_exact_url_and_sessions_have_unique_tokens(self):
        data = encoded(Image.new("RGB", (2, 2)), "PNG")
        one, another = self.share(data), self.share(data)
        self.assertNotEqual(one.route, another.route)
        self.assertNotEqual(urlsplit(one.url).port, urlsplit(another.url).port)
        self.assertGreaterEqual(len(one.route.split("/")[-1]), 43)
        self.assertEqual(zxingcpp.read_barcode(qr_image(one.url)).text, one.url)

    def test_png_and_saved_jpg_are_byte_exact(self):
        image = Image.new("RGB", (200, 150), "#6080b0")
        for format in ("PNG", "JPEG"):
            with self.subTest(format=format), tempfile.TemporaryDirectory() as folder:
                content = encoded(image, format)
                path = Path(folder) / "original"
                path.write_bytes(content)
                source = ShareSource(b"", path, file_identity(path.stat()))
                loaded = SharedImage.load(source)
                session = ShareSession(loaded, LOOPBACK, 20, "en")
                with self.subTest(operation="transfer"):
                    self.addCleanup(self.close, session)
                    status, headers, data = self.request(session, "/image")
                    self.assertEqual(status, 200)
                    self.assertEqual(headers["Content-Type"], f"image/{format.lower()}")
                    self.assertEqual(headers["Cache-Control"], "no-store, max-age=0")
                    self.assertEqual(data, content)
                    self.assertTrue(session.delivered.wait(2))
                    status, headers, data = self.request(session, "/download")
                    self.assertEqual(status, 200)
                    self.assertIn(f'AreaGrab.{loaded.extension}', headers["Content-Disposition"])
                    self.assertEqual(data, content)

    def test_4k_transfer_without_compressing_again(self):
        image = Image.frombytes("RGB", (3840, 2160), os.urandom(3840 * 2160 * 3))
        content = encoded(image, "PNG")
        session = self.share(content)
        self.assertGreater(len(content), 20 * 1024 * 1024)
        status, headers, body = self.request(session, "/download")
        self.assertEqual((status, headers["Content-Length"]), (200, str(len(content))))
        self.assertEqual(body, content)

    def test_invalid_paths_hosts_and_methods_do_not_disclose_image(self):
        session = self.share(encoded(Image.new("RGB", (2, 2)), "PNG"))
        for path in ("/", "/share/incorrect/image", session.route + "/../image",
                     session.route + "/%2e%2e/secret", "/" + session.route + "/image",
                     session.route + "/image?file=C:/secret", "/settings.json"):
            with self.subTest(path=path):
                self.assertEqual(self.request(session, target=path)[0], 404)
        self.assertEqual(self.request(session, headers={"Host": "other.local"})[0], 400)
        self.assertEqual(self.request(session, method="POST")[0], 405)
        self.assertEqual(self.request(session, "/image", method="HEAD")[2], b"")
        self.assertFalse(session.delivered.is_set())

    def test_expiration_refresh_and_cleanup_of_idle_connection(self):
        content = encoded(Image.new("RGB", (2, 2)), "PNG")
        existing = {thread.ident for thread in threading.enumerate()}
        session = self.share(content, ttl=0.35)
        url = urlsplit(session.url)
        with socket.create_connection((url.hostname, url.port), timeout=3) as stalled:
            stalled.sendall(b"GET /share/unfinished")
            self.assertTrue(session.wait_closed(5))
            self.assertEqual(stalled.recv(1), b"")
        with self.assertRaises(OSError):
            self.request(session, "/image")
        refreshed = self.share(content)
        self.assertEqual(self.request(refreshed, target=url.path + "/image")[0], 404)
        self.assertEqual(self.request(refreshed, "/image")[2], content)
        self.close(refreshed)
        self.assertEqual({thread.ident for thread in threading.enumerate()} - existing, set())

    def test_stop_interrupts_download_with_a_stalled_receiver(self):
        content = encoded(Image.new("RGB", (1, 1)), "PNG")
        image = SharedImage(content + bytes(8 * 1024 * 1024), 1, 1, "png")
        session = ShareSession(image, LOOPBACK, 20, "en")
        self.addCleanup(self.close, session)
        url = urlsplit(session.url)
        with socket.create_connection((url.hostname, url.port), timeout=3) as client:
            client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
            client.sendall(f"GET {url.path}/image HTTP/1.1\r\nHost: {url.netloc}\r\n\r\n".encode("ascii"))
            self.assertIn(b"200 OK", client.recv(256))
            self.close(session)
        self.assertFalse(session.delivered.is_set())

    def test_page_localized_for_every_supported_language(self):
        import html

        content = encoded(Image.new("RGB", (120, 40)), "PNG")
        for language in CODES:
            with self.subTest(language=language):
                session = self.share(content, language=language)
                status, headers, body = self.request(session)
                self.assertEqual(status, 200)
                self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
                page = body.decode()
                self.assertIn(f'lang="{language}"', page)
                self.assertIn(html.escape(translate("Скачать снимок", language)), page)
                self.assertIn("120 × 40 px", page)
                self.assertIn(session.route + "/download", page)
                self.assertNotIn("<script", page)
                self.close(session)

    def test_changed_or_removed_file_cannot_be_shared(self):
        content = encoded(Image.new("RGB", (2, 2)), "PNG")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "original.png"
            path.write_bytes(content)
            source = ShareSource(content, path, file_identity(path.stat()))
            path.write_bytes(content + b"changed")
            with self.assertRaises(ValueError):
                SharedImage.load(source)
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                SharedImage.load(source)

    def test_physical_adapter_preferred_and_public_profile_preserved(self):
        items = [
            {"address": "10.1.0.1", "prefix": 24, "name": "VPN", "physical": False, "metric": 1},
            {"address": "192.168.1.9", "prefix": 24, "name": "Ethernet", "physical": True,
             "metric": 30, "category": "Public"},
            {"address": "169.254.1.1", "prefix": 16, "name": "Unconnected"},
            {"address": "127.0.0.1", "prefix": 8, "name": "Loopback"},
        ]
        adapters = parse_adapters(json.dumps(items))
        self.assertEqual([adapter.name for adapter in adapters], ["Ethernet", "VPN"])
        self.assertEqual(adapters[0].category, "Public")
        self.assertEqual(str(adapters[0].address.network), "192.168.1.0/24")


@unittest.skipUnless(sys.platform == "win32", "Requires the Windows Tk UI")
class WindowsShareTests(unittest.TestCase):
    def test_close_reopen_and_quit_stop_the_network_server(self):
        import tkinter as tk
        from unittest.mock import patch

        from areagrab.app import AreaGrabApp, build_parser
        from areagrab.config import Settings

        root = tk.Tk()
        root.withdraw()
        settings = Settings.from_dict({"advanced": {"language": "en"}})
        args = build_parser().parse_args(["--preview-pro"])
        with patch("areagrab.app.Settings.load", return_value=settings):
            app = AreaGrabApp(root, args)

        def cleanup():
            app.quit()

        self.addCleanup(cleanup)
        source = ShareSource(encoded(Image.new("RGB", (8, 8)), "PNG"), None)

        def open_window():
            with patch("areagrab.ui.share_window.find_adapters", return_value=[LOOPBACK]):
                app.open_share(source)
                window = app._share_window
                deadline = time.monotonic() + 5
                while window.session is None and time.monotonic() < deadline:
                    root.update()
                    time.sleep(0.01)
            self.assertIsNotNone(window.session)
            return window

        with patch.object(app, "save_settings"):
            first = open_window()
            original = first.session
            self.assertEqual(first.title(), "Send to device")
            first._renew()
            replacement = first.session
            self.assertNotEqual(original.url, replacement.url)
            self.assertTrue(original.wait_closed(5))
            first.destroy()
            self.assertTrue(replacement.wait_closed(5))
            second = open_window()
            active = second.session
            app.quit()
            self.assertTrue(active.wait_closed(5))

    def test_settings_defaults_and_duration_validation(self):
        from areagrab.config import Settings

        defaults = Settings()
        self.assertTrue(defaults.lan_share.enabled)
        self.assertTrue(defaults.lan_share.show_in_toast)
        self.assertEqual(defaults.lan_share.ttl, 60)
        for duration in (60, 120, 300, 7):
            with self.subTest(duration=duration):
                settings = Settings.from_dict({"lan_share": {
                    "enabled": False, "show_in_toast": False, "ttl": duration,
                }})
                self.assertFalse(settings.lan_share.enabled)
                self.assertFalse(settings.lan_share.show_in_toast)
                self.assertEqual(settings.lan_share.ttl, duration if duration != 7 else 60)

    def test_adapter_discovery_on_windows(self):
        from areagrab.lan_adapters import find_adapters

        adapters = find_adapters()
        self.assertTrue(all(isinstance(adapter.address, ipaddress.IPv4Interface) for adapter in adapters))
