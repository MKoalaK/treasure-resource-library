import base64
import copy
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import library
import media


def record(identity='official:https://example.com/a'):
    return dict(identity=identity, name='工具 | 示例', url='https://example.com/a',
                intro='提供文档与协作功能，适用于团队知识管理。', review='协作方便，但离线功能有限。',
                type='网站、App', tags=['文档', '办公', '团队', '写作', '协作'],
                download='在线使用，无需下载', media='![图片](%E7%B4%A0%E6%9D%90/a%20b.png)\n[视频](assets/v.mp4)')


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / '中文 空格' / '宝藏资源库.md'

    def update(self, records):
        return library.update(self.path, dict(expected_sha256=library.inspect(self.path)['sha256'], records=records))

    def test_create_multiple_and_inspect(self):
        result = self.update([record(), record('app:store:123')])
        self.assertEqual(result['added'], 2)
        records = library.inspect(self.path)['records']
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]['name'], '工具 | 示例')
        self.assertEqual(records[0]['media'], record()['media'])
        self.assertNotIn('信息来源', self.path.read_text(encoding='utf8'))

    def test_plain_document_preserved_then_updates(self):
        self.path.parent.mkdir()
        original = b'\xef\xbb\xbf# Notes\r\n\r\nMy table | a | b\r\nNo final newline'
        self.path.write_bytes(original)
        self.update([record()])
        self.assertTrue(self.path.read_bytes().startswith(original))
        self.path.write_bytes(self.path.read_bytes() + b'\r\nUser footer\r\n')
        before = self.path.read_bytes()
        self.update([dict(identity=record()['identity'], intro='更新后的功能说明。')])
        after = self.path.read_bytes()
        self.assertTrue(after.startswith(original))
        self.assertTrue(after.endswith(b'\r\nUser footer\r\n'))
        # Exactly the intended row changes.
        self.assertEqual(sum(a != b for a, b in zip(before.splitlines(), after.splitlines())), 1)

    def test_noop_does_not_write_even_reordered_tags(self):
        self.update([record()])
        raw = self.path.read_bytes()
        mtime = self.path.stat().st_mtime_ns
        r = record()
        r['tags'].reverse()
        result = self.update([r])
        self.assertFalse(result['written'])
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertEqual(self.path.stat().st_mtime_ns, mtime)

    def test_partial_update_preserves_unknown_old_fields(self):
        self.update([record()])
        self.update([dict(identity=record()['identity'], intro='新介绍。')])
        self.assertEqual(library.inspect(self.path)['records'][0]['url'], record()['url'])

    def test_validation_rejects_whole_batch(self):
        for key, value in [('intro', '字' * 201), ('review', '字' * 151), ('review', '很好。很贵。'),
                           ('tags', ['a'] * 5), ('tags', ['a']), ('url', 'file:///foo')]:
            with self.subTest(key=key, value=str(value)[:20]):
                bad = record('second')
                bad[key] = value
                with self.assertRaises(ValueError):
                    self.update([record(), bad])
                self.assertFalse(self.path.exists())

    def test_limits_empty_url_insufficient_reviews(self):
        r = record()
        r.update(intro='字' * 200, review='字' * 150, url='', media='')
        self.update([r])
        self.assertEqual(library.inspect(self.path)['records'][0]['url'], '')

    def test_corrupt_region_fails_without_mutation(self):
        self.update([record()])
        raw = self.path.read_bytes().replace(library.HEADER.encode(), b'| Modified header |')
        self.path.write_bytes(raw)
        with self.assertRaises(ValueError):
            library.update(self.path, dict(expected_sha256=library.version(raw), records=[record()]))
        self.assertEqual(raw, self.path.read_bytes())

    def test_duplicate_input_and_stale_version(self):
        with self.assertRaises(ValueError):
            self.update([record(), record()])
        self.update([record()])
        old = library.inspect(self.path)['sha256']
        self.path.write_bytes(self.path.read_bytes() + b'new note')
        raw = self.path.read_bytes()
        with self.assertRaises(ValueError):
            library.update(self.path, dict(expected_sha256=old, records=[record()]))
        self.assertEqual(raw, self.path.read_bytes())

    def test_commit_and_lock_conflict(self):
        self.update([record()])
        raw = self.path.read_bytes()
        self.path.write_bytes(raw + b'concurrent')
        with self.assertRaises(ValueError):
            library.commit(self.path, raw, b'new')
        lock = self.path.with_name(self.path.name + '.trl.lock')
        lock.touch()
        with self.assertRaises(FileExistsError):
            self.update([record()])
        self.assertTrue(lock.exists())

    def test_paths_unknown_markers_and_time(self):
        self.assertEqual(library.target(self.path.parent), self.path)
        with self.assertRaises(ValueError):
            library.parse(b'<!-- treasure-resource-library:v2:start -->')
        self.assertRegex(library.timestamp('+08:00'), r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$')
        with self.assertRaises(ValueError):
            library.timestamp('+14:30')

    def test_table_boundaries_and_contiguous_append(self):
        self.update([record()])
        self.update([record('app:second')])
        lines, block, rows = library.parse(self.path.read_bytes())
        self.assertEqual(lines[block[0] + 1].strip(), '')
        self.assertEqual(lines[block[1] - 1].strip(), '')
        self.assertTrue(all(line.strip() for line in lines[block[0] + 2:block[1] - 1]))
        self.assertEqual(len(rows), 2)

    def test_notes_roundtrip_and_no_generated_title(self):
        r = record()
        r['notes'] = '官网返回 403 | 原因未确定\n视频下载失败，保留来源页'
        self.update([r])
        self.assertFalse(self.path.read_text(encoding='utf8').startswith('#'))
        self.assertEqual(library.inspect(self.path)['records'][0]['notes'], r['notes'])
        self.update([dict(identity=r['identity'], intro='新介绍。')])
        self.assertEqual(library.inspect(self.path)['records'][0]['notes'], r['notes'])
        self.assertFalse(self.update([dict(identity=r['identity'])])['written'])
        self.update([dict(identity=r['identity'], notes='')])
        self.assertEqual(library.inspect(self.path)['records'][0]['notes'], '')

    def test_legacy_migration_preserves_cells_time_and_bom(self):
        self.update([record()])
        lines, block, rows = library.parse(self.path.read_bytes())
        original = list(rows.values())[0][1]
        for i, line in enumerate(lines):
            if line.strip() == library.HEADER:
                lines[i] = library.LEGACY_HEADER + '\n'
            elif line.strip() == library.SEPARATOR:
                lines[i] = library.LEGACY_SEPARATOR + '\n'
            elif '<!-- trl-id:' in line:
                lines[i] = line.rsplit('|', 2)[0].rstrip() + ' |\n'
        raw = ('\ufeff# 宝藏资源库\n\n' + ''.join(lines)).encode('utf8')
        self.path.write_bytes(raw)
        result = self.update([])
        self.assertTrue(result['schema_migrated'])
        self.assertTrue(result['title_removed'])
        self.assertEqual(library.inspect(self.path)['records'][0], original)
        self.assertTrue(self.path.read_bytes().startswith(b'\xef\xbb\xbf<!--'))
        self.assertFalse(self.update([])['written'])

    def test_explicit_legacy_repair_preserves_rows_and_is_idempotent(self):
        self.update([record()])
        raw = self.path.read_bytes().replace((library.START + '\n\n').encode(), (library.START + '\n').encode()).replace(('\n\n' + library.END).encode(), ('\n' + library.END).encode())
        self.path.write_bytes(raw)
        rows_before = library.inspect(self.path)['records']
        self.assertFalse(self.update([record()])['written'])
        result = library.update(self.path, dict(expected_sha256=library.version(raw), records=[], repair_format=True))
        self.assertTrue(result['written'])
        self.assertEqual(rows_before, library.inspect(self.path)['records'])
        current = self.path.read_bytes()
        self.assertEqual([x for x in raw.splitlines() if x], [x for x in current.splitlines() if x])
        result = library.update(self.path, dict(expected_sha256=library.version(current), records=[], repair_format=True))
        self.assertFalse(result['written'])


class Response(io.BytesIO):
    def __init__(self, body):
        super().__init__(body)
        self.url = 'https://example.com/media'
        self.headers = {'Content-Length': str(len(body))}


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / '中文 素材'
        self.png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a6X8AAAAASUVORK5CYII=')

    def test_image_success_and_reuse(self):
        with patch.object(media, 'urlopen', side_effect=lambda *a, **k: Response(self.png)):
            first = media.download('https://example.com/image.png', self.directory)
            second = media.download('https://example.com/image.png', self.directory)
        self.assertEqual(Path(first['path']).read_bytes(), self.png)
        self.assertTrue(second['reused'])
        self.assertEqual(len(list(self.directory.iterdir())), 1)

    def test_video_format_and_download(self):
        body = b'\x00\x00\x00\x18ftypmp42' + bytes(40)
        with patch.object(media, 'urlopen', return_value=Response(body)):
            result = media.download('https://example.com/video.mp4', self.directory)
        self.assertTrue(result['path'].endswith('.mp4'))
        self.assertEqual(Path(result['path']).read_bytes(), body)

    def test_html_size_failure_and_network_failure(self):
        for body, limit in [(b'<html>Error</html>', 1), (self.png, 0.000001)]:
            with patch.object(media, 'urlopen', return_value=Response(body)):
                with self.assertRaises(ValueError):
                    media.download('https://example.com/bad', self.directory, limit)
        with patch.object(media, 'urlopen', side_effect=OSError('network unavailable')):
            with self.assertRaises(OSError):
                media.download('https://example.com/bad', self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)

