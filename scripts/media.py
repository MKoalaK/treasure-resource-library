"""Download a verified direct media URL; reject non-media and reuse content."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


def extension(head):
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if head.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if head.startswith((b'GIF87a', b'GIF89a')):
        return '.gif'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return '.webp'
    if head[4:8] == b'ftyp' and head[8:12] in (b'isom', b'iso2', b'mp41', b'mp42', b'avc1', b'M4V ', b'dash'):
        return '.mp4'
    if head.startswith(b'\x1a\x45\xdf\xa3') and b'webm' in head:
        return '.webm'
    raise ValueError('响应不是支持的媒体格式；请改用已核验的来源页链接')


def download(url, directory, max_mb=512):
    if urlsplit(url).scheme not in ('http', 'https') or max_mb <= 0:
        raise ValueError('需要 HTTP(S) 直接媒体地址和正的大小上限')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        request = Request(url, headers={'User-Agent': 'TreasureResourceLibrary/1.0'})
        with urlopen(request, timeout=30) as response:
            if urlsplit(response.url).scheme not in ('http', 'https'):
                raise ValueError('非 HTTP(S) 重定向')
            limit = int(max_mb * 1024 * 1024)
            if int(response.headers.get('Content-Length', 0)) > limit:
                raise ValueError('媒体超过大小上限，请改存来源页链接')
            head = response.read(4096)
            suffix = extension(head)
            fd, temporary = tempfile.mkstemp(prefix='.media-', dir=directory)
            digest = hashlib.sha256()
            size = 0
            with os.fdopen(fd, 'wb') as stream:
                chunk = head
                while chunk:
                    size += len(chunk)
                    if size > limit:
                        raise ValueError('媒体超过大小上限')
                    digest.update(chunk)
                    stream.write(chunk)
                    chunk = response.read(1024 * 1024)
            expected = response.headers.get('Content-Length')
            if expected is not None and size != int(expected):
                raise ValueError('媒体下载不完整')
        fingerprint = digest.hexdigest()
        destination = directory / (fingerprint + suffix)
        reused = destination.exists()
        if reused:
            if hashlib.sha256(destination.read_bytes()).hexdigest() != fingerprint:
                raise ValueError('本地同名素材内容异常，不覆盖')
        else:
            # Exclusive creation prevents overwriting an existing user file.
            with destination.open('xb') as output, open(temporary, 'rb') as source:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
        return {'path': str(destination.absolute()), 'sha256': fingerprint, 'reused': reused, 'bytes': size, 'source_url': url}
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--max-mb', type=float, default=512)
    args = parser.parse_args()
    try:
        print(json.dumps(download(args.url, args.directory, args.max_mb), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(1, f'媒体未保存，请使用已核验的来源页链接：{exc}\n')


if __name__ == '__main__':
    main()
