"""Тесты на локальном HTTP-сервере, интернет для них не нужен."""

import contextlib
import http.server
import io
import threading
import unittest

import speed_meter

PAYLOAD = bytes(range(256)) * 4096  # 1 МиБ «картинки»


class Handler(http.server.BaseHTTPRequestHandler):
    hits = 0

    def do_GET(self):
        type(self).hits += 1
        if self.path == "/image.jpg":
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(PAYLOAD)))
            self.end_headers()
            self.wfile.write(PAYLOAD)
        elif self.path == "/broken.jpg":
            self.send_response(200)
            self.send_header("Content-Length", str(len(PAYLOAD)))
            self.end_headers()
            self.wfile.write(PAYLOAD[:1000])  # обрываем ответ посередине
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass  # не засорять вывод тестов


class SpeedMeterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Handler.hits = 0

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = speed_meter.main(list(argv))
        return code, out.getvalue()

    def test_download_counts_every_byte(self):
        size, seconds = speed_meter.download(self.base + "/image.jpg", timeout=5)
        self.assertEqual(size, len(PAYLOAD))
        self.assertGreater(seconds, 0)

    def test_ten_requests_by_default(self):
        code, out = self.run_main(self.base + "/image.jpg")
        self.assertEqual(code, 0)
        self.assertEqual(Handler.hits, 10)
        self.assertIn("Успешных запросов:     10 из 10", out)
        self.assertIn(f"Скачано всего:         {10 * len(PAYLOAD) / speed_meter.MB:.2f} МБ", out)
        self.assertIn("МБ/с", out)

    def test_count_option(self):
        code, _ = self.run_main(self.base + "/image.jpg", "-n", "3")
        self.assertEqual(code, 0)
        self.assertEqual(Handler.hits, 3)

    def test_http_error_is_reported(self):
        code, out = self.run_main(self.base + "/missing.jpg", "-n", "2")
        self.assertEqual(code, 1)
        self.assertEqual(out.count("ошибка: HTTP 404"), 2)

    def test_truncated_response_is_an_error(self):
        with self.assertRaises(ConnectionError):
            speed_meter.download(self.base + "/broken.jpg", timeout=5)

    def test_url_without_scheme_gets_https(self):
        self.assertEqual(speed_meter.http_url("example.com/a.jpg"), "https://example.com/a.jpg")

    def test_bad_count_is_rejected(self):
        for bad in ("0", "-1", "abc"):
            with self.subTest(count=bad), self.assertRaises(SystemExit), \
                    contextlib.redirect_stderr(io.StringIO()):
                speed_meter.parse_args(["https://example.com/a.jpg", "-n", bad])


if __name__ == "__main__":
    unittest.main()
