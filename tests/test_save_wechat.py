# -*- coding: utf-8 -*-
"""Tests for save_wechat.py.

Run from the repository root:
    python -m unittest discover -s tests -v

A local HTTP server stands in for mp.weixin.qq.com and the WeChat image CDN,
so no network access is needed.
"""

import io
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "skills" / "wechat-to-obsidian" / "scripts"))

import save_wechat  # noqa: E402

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-data" * 20
GIF_BYTES = b"GIF89a" + b"fake-gif-data" * 20

ARTICLE_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>page</title></head><body>
<script>
var msg_title = '测试文章&#8217;标题';
var nickname = "测试公众号";
create_time: '2026-05-25 10:00:00'
var dummy = '%s';
</script>
<!-- WeChat pages are large; padding below keeps the fixture above the
     1000-byte minimum download size enforced by download_article(). -->
<div class="rich_media_content
  js_underline_content"
  id="js_content">
  <h2>第一章</h2>
  <p>你好&amp;世界&#8217;测试。</p>
  <img data-src="http://127.0.0.1:{port}/img/a.png?wx_fmt=png" src="">
  <section><span>嵌套内容</span><strong>加粗文字</strong></section>
  <img data-src="http://127.0.0.1:{port}/img/b.gif?wx_fmt=gif">
  <img data-src="http://127.0.0.1:{port}/img/missing.png?wx_fmt=png">
  <div><div><p>深层段落</p></div></div>
  <p>正文填充内容，用于模拟真实微信文章的篇幅长度，保证整页下载体积超过脚本的反爬阈值检查。</p>
</div>
<div id="js_sponsor_ad"><p>广告内容</p></div>
</body></html>
""" % ("x" * 800)


class FakeWeChatHandler(BaseHTTPRequestHandler):
    """Serves a WeChat-shaped article page and a few fake images."""

    def do_GET(self):
        if "mp.weixin.qq.com" in self.path:
            body = ARTICLE_HTML_TEMPLATE.format(port=self.server.server_port)
            self._serve(body.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path.startswith("/img/a.png"):
            self._serve(PNG_BYTES, "image/png")
        elif self.path.startswith("/img/b.gif"):
            self._serve(GIF_BYTES, "image/gif")
        else:
            self.send_response(404)
            self.end_headers()

    def _serve(self, data, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class WithServer(unittest.TestCase):
    """Starts the fake WeChat server once for the whole class."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeWeChatHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def article_url(self):
        return f"http://127.0.0.1:{self.port}/mp.weixin.qq.com/s/test123"


class TestExtraction(WithServer):
    def setUp(self):
        self.html_path = Path(tempfile.mkdtemp()) / "page.html"
        self.html_path.write_text(
            ARTICLE_HTML_TEMPLATE.format(port=self.port), encoding="utf-8"
        )

    def test_metadata_extraction(self):
        title, account, date, body = save_wechat.extract_wechat_metadata(self.html_path)
        self.assertEqual(title, "测试文章’标题")
        self.assertEqual(account, "测试公众号")
        self.assertEqual(date, "2026-05-25")

    def test_body_extraction_with_multiline_attributes(self):
        _, _, _, body = save_wechat.extract_wechat_metadata(self.html_path)
        self.assertIn("深层段落", body)
        self.assertIn("嵌套内容", body)
        # Content outside id="js_content" must not leak into the body
        self.assertNotIn("广告内容", body)

    def test_markdown_conversion(self):
        _, _, _, body = save_wechat.extract_wechat_metadata(self.html_path)
        md = save_wechat.wechat_html_to_markdown(body)
        self.assertIn("## 第一章", md)
        self.assertIn("**加粗文字**", md)
        self.assertIn("你好&世界’测试。", md)
        self.assertNotIn("<span", md)
        self.assertIn(f"![](http://127.0.0.1:{self.port}/img/a.png?wx_fmt=png)", md)


class TestHelpers(unittest.TestCase):
    def test_image_extension(self):
        cases = {
            "https://mmbiz.qpic.cn/mmbiz_png/abc/640?wx_fmt=png": "png",
            "https://mmbiz.qpic.cn/mmbiz_jpg/abc/640?wx_fmt=jpeg": "jpg",
            "https://mmbiz.qpic.cn/mmbiz_gif/abc?wx_fmt=gif": "gif",
            "https://mmbiz.qpic.cn/mmbiz_webp/abc?wx_fmt=webp": "webp",
            "https://example.com/pic.webp": "webp",
            "https://example.com/pic.jpeg": "jpg",
            "https://example.com/pic": "jpg",
        }
        for url, ext in cases.items():
            self.assertEqual(save_wechat.image_extension(url), ext, url)

    def test_is_wechat_image(self):
        self.assertTrue(save_wechat.is_wechat_image("https://mmbiz.qpic.cn/x?wx_fmt=png"))
        self.assertFalse(save_wechat.is_wechat_image("https://example.com/x.png"))

    def test_safe_name(self):
        self.assertEqual(save_wechat.safe_name('a/b:c*d?"e<f>g|h\\i*j'), "a_b_c_d__e_f_g_h_i_j")

    def test_find_vault_root(self):
        tmp = Path(tempfile.mkdtemp())
        vault = tmp / "vault"
        (vault / ".obsidian").mkdir(parents=True)
        deep_inbox = vault / "a" / "b" / "Inbox"
        deep_inbox.mkdir(parents=True)
        self.assertEqual(save_wechat.find_vault_root(deep_inbox), vault.resolve())
        self.assertIsNone(save_wechat.find_vault_root(tmp / "no-vault" / "inbox"))


class TestLocalization(WithServer):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.vault = self.tmp / "vault"
        self.inbox = self.vault / "Inbox"
        (self.vault / ".obsidian").mkdir(parents=True)
        self.inbox.mkdir(parents=True)
        self._old_hosts = save_wechat.WECHAT_IMAGE_HOSTS
        save_wechat.WECHAT_IMAGE_HOSTS = ("127.0.0.1",)

    def tearDown(self):
        save_wechat.WECHAT_IMAGE_HOSTS = self._old_hosts

    def sample_markdown(self):
        return (
            "## 第一章\n\n"
            f"![](http://127.0.0.1:{self.port}/img/a.png?wx_fmt=png)\n\n"
            f"![](http://127.0.0.1:{self.port}/img/b.gif?wx_fmt=gif)\n\n"
            f"![](http://127.0.0.1:{self.port}/img/missing.png?wx_fmt=png)\n\n"
            f"![](http://127.0.0.1:{self.port}/img/a.png?wx_fmt=png)\n"
        )

    def test_downloads_and_rewrites(self):
        md = self.sample_markdown()
        new_md, stats = save_wechat.localize_images(md, self.inbox, "测试文章", "2026-05-25")

        self.assertEqual(stats, (2, 0, 1))  # downloaded, cached, failed

        attach = self.vault / "attachments"
        files = sorted(p.name for p in attach.iterdir())
        self.assertEqual([f.rsplit(".", 1)[1] for f in files], ["png", "gif"])
        self.assertTrue(files[1].startswith("2026-05-25-测试文章-img"))

        # Duplicate URL maps to the same local file; failed download stays remote
        self.assertEqual(new_md.count("../attachments/"), 3)
        self.assertIn(f"http://127.0.0.1:{self.port}/img/missing.png", new_md)
        self.assertNotIn("/img/a.png?wx_fmt=png)", new_md)

    def test_second_run_uses_cache(self):
        save_wechat.localize_images(self.sample_markdown(), self.inbox, "测试文章", "2026-05-25")
        _, stats = save_wechat.localize_images(
            self.sample_markdown(), self.inbox, "测试文章", "2026-05-25"
        )
        self.assertEqual(stats, (0, 2, 1))

    def test_no_wechat_images_is_noop(self):
        md = "text without images\n\n![](https://example.com/pic.png)\n"
        new_md, stats = save_wechat.localize_images(md, self.inbox, "t", "2026-05-25")
        self.assertEqual(stats, (0, 0, 0))
        self.assertEqual(new_md, md)
        self.assertFalse((self.vault / "attachments").exists())

    def test_falls_back_to_inbox_without_vault_root(self):
        plain = self.tmp / "just" / "inbox"
        plain.mkdir(parents=True)
        md = f"![](http://127.0.0.1:{self.port}/img/a.png?wx_fmt=png)\n"
        new_md, stats = save_wechat.localize_images(md, plain, "t", "2026-05-25")
        self.assertEqual(stats, (1, 0, 0))
        self.assertEqual(new_md.count("attachments/"), 1)
        self.assertTrue((plain / "attachments").is_dir())


class TestNonInteractive(unittest.TestCase):
    def setUp(self):
        self._old_conf = save_wechat.CONFIG_FILE
        save_wechat.CONFIG_FILE = (
            Path(tempfile.gettempdir()) / "nonexistent-wechat-conf-for-tests"
        )
        self._old_env = os.environ.pop("OBSIDIAN_VAULT_INBOX", None)

    def tearDown(self):
        save_wechat.CONFIG_FILE = self._old_conf
        if self._old_env is not None:
            os.environ["OBSIDIAN_VAULT_INBOX"] = self._old_env

    def test_flag_fails_cleanly_without_config(self):
        argv = ["save_wechat.py", "--non-interactive", "https://example.com/article"]
        with mock.patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as ctx:
                save_wechat.main()
        self.assertEqual(ctx.exception.code, 1)

    def test_non_tty_stdin_fails_cleanly(self):
        # No --non-interactive flag, but stdin/stdout are not a TTY (agent shell)
        argv = ["save_wechat.py", "https://example.com/article"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(sys, "stdin", io.StringIO()), \
             mock.patch.object(sys, "stdout", io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                save_wechat.main()
        self.assertEqual(ctx.exception.code, 1)

    def test_is_interactive_detects_piped_streams(self):
        with mock.patch.object(sys, "stdin", io.StringIO()), \
             mock.patch.object(sys, "stdout", io.StringIO()):
            self.assertFalse(save_wechat.is_interactive())
        self.assertTrue(save_wechat.is_interactive() in (True, False))  # smoke: no crash


class TestEndToEnd(WithServer):
    """Full pipeline through main(): download → extract → localize → save."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.vault = self.tmp / "vault"
        self.inbox = self.vault / "Inbox"
        (self.vault / ".obsidian").mkdir(parents=True)
        self.inbox.mkdir(parents=True)
        self._old_hosts = save_wechat.WECHAT_IMAGE_HOSTS
        save_wechat.WECHAT_IMAGE_HOSTS = ("127.0.0.1",)
        self._old_env = os.environ.get("OBSIDIAN_VAULT_INBOX")
        os.environ["OBSIDIAN_VAULT_INBOX"] = str(self.inbox)

    def tearDown(self):
        save_wechat.WECHAT_IMAGE_HOSTS = self._old_hosts
        if self._old_env is None:
            os.environ.pop("OBSIDIAN_VAULT_INBOX", None)
        else:
            os.environ["OBSIDIAN_VAULT_INBOX"] = self._old_env

    def run_main(self, *extra_args):
        argv = ["save_wechat.py", "--non-interactive", *extra_args, self.article_url()]
        with mock.patch.object(sys, "argv", argv):
            save_wechat.main()

    def test_full_pipeline_with_localization(self):
        self.run_main()
        notes = list(self.inbox.glob("*.md"))
        self.assertEqual(len(notes), 1)
        text = notes[0].read_text(encoding="utf-8")

        self.assertIn('title: "测试文章’标题"', text)
        self.assertIn('author: "测试公众号"', text)
        self.assertIn("date: 2026-05-25", text)
        self.assertIn("## 第一章", text)
        self.assertNotIn("广告内容", text)
        # Images were localized; the intentionally-broken one kept its remote URL
        self.assertIn("../attachments/", text)
        self.assertNotIn("/img/a.png", text)
        self.assertNotIn("/img/b.gif", text)
        self.assertIn("/img/missing.png", text)
        # Images exist on disk next to the vault attachments folder
        attach = self.vault / "attachments"
        self.assertEqual(len(list(attach.glob("*.png"))), 1)
        self.assertEqual(len(list(attach.glob("*.gif"))), 1)

    def test_no_local_images_keeps_remote_urls(self):
        self.run_main("--no-local-images")
        notes = list(self.inbox.glob("*.md"))
        self.assertEqual(len(notes), 1)
        text = notes[0].read_text(encoding="utf-8")
        self.assertIn(f"![](http://127.0.0.1:{self.port}/img/a.png?wx_fmt=png)", text)
        self.assertFalse((self.vault / "attachments").exists())

    def test_temp_files_are_cleaned_up(self):
        self.run_main()
        leftovers = list(Path(tempfile.gettempdir()).glob("wechat_article_*.html"))
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
