"""Conservative UTF-8 Markdown library maintenance; standard library only."""
import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

START = '<!-- treasure-resource-library:v1:start -->'
END = '<!-- treasure-resource-library:v1:end -->'
HEADERS = ['名称', '官方网址', '介绍', '评价', '类型', '标签', '下载方式', '多媒体资料', '更新时间', '备注']
KEYS = ['name', 'url', 'intro', 'review', 'type', 'tags', 'download', 'media', 'updated', 'notes']
HEADER = '| ' + ' | '.join(HEADERS) + ' |'
SEPARATOR = '| ' + ' | '.join(['---'] * len(KEYS)) + ' |'
LEGACY_HEADER = '| ' + ' | '.join(HEADERS[:-1]) + ' |'
LEGACY_SEPARATOR = '| ' + ' | '.join(['---'] * 9) + ' |'
ROW_ID = re.compile(r'<!-- trl-id:([A-Za-z0-9_-]+) -->$')


def target(value):
    path = Path(value).expanduser().absolute()
    if path.is_dir() or (not path.exists() and not path.suffix):
        path = path / '宝藏资源库.md'
    if path.suffix.lower() not in ('.md', '.markdown'):
        raise ValueError('目标必须是文件夹或 Markdown 文件')
    if path.is_symlink():
        raise ValueError('不自动替换符号链接，请提供实际文档路径')
    return path


def version(raw):
    return 'missing' if raw is None else hashlib.sha256(raw).hexdigest()


def read(path):
    return path.read_bytes() if path.exists() else None


def encode(value):
    return html.escape(value, quote=False).replace('|', '&#124;').replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')


def decode(value):
    return html.unescape(value.replace('<br>', '\n'))


def parse(raw):
    text = '' if raw is None else raw.decode('utf-8')
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.strip().lstrip('\ufeff') == START]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    if not starts and not ends:
        if 'treasure-resource-library:' in text or '<!-- trl-id:' in text:
            raise ValueError('未知或损坏的资源库标记，停止写入')
        return lines, None, {}
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ValueError('资源库区域不唯一或未闭合')
    start, end = starts[0], ends[0]
    # Refuse malformed or extra library markers even outside the managed block.
    if text.count('treasure-resource-library:') != 2:
        raise ValueError('存在多余或未知版本的标记')
    nonempty = [(i, lines[i].strip()) for i in range(start + 1, end) if lines[i].strip()]
    legacy = bool(nonempty and nonempty[0][1] == LEGACY_HEADER)
    if len(nonempty) < 2 or (nonempty[0][1], nonempty[1][1]) not in ((HEADER, SEPARATOR), (LEGACY_HEADER, LEGACY_SEPARATOR)):
        raise ValueError('表头不匹配，停止写入')
    rows = {}
    for index, line in nonempty[2:]:
        if not line.startswith('|') or not line.endswith('|'):
            raise ValueError('库区存在非标准内容，保留原文并停止')
        cells = [s.strip() for s in line[1:-1].split('|')]
        if len(cells) != (9 if legacy else 10):
            raise ValueError('表格列数异常')
        match = ROW_ID.search(cells[0])
        if not match:
            raise ValueError('资源行身份标记缺失')
        token = match.group(1)
        identity = base64.urlsafe_b64decode(token + '=' * (-len(token) % 4)).decode('utf-8')
        if not identity or identity in rows:
            raise ValueError('重复或空身份标记')
        cells[0] = cells[0][:match.start()].rstrip()
        record = dict(zip(KEYS, map(decode, cells)))
        record.setdefault('notes', '')
        record['tags'] = record['tags'].split('、')
        record['identity'] = identity
        validate(record)
        rows[identity] = (index, record)
    return lines, (start, end), rows


def validate(record):
    if set(record) != set(KEYS) | {'identity'}:
        raise ValueError('记录字段不完整或包含未知字段')
    for key in set(KEYS) - {'tags'} | {'identity'}:
        if not isinstance(record[key], str):
            raise ValueError(f'{key} 必须为字符串')
    for key in ('name', 'intro', 'review', 'type', 'identity'):
        if not record[key].strip():
            raise ValueError(f'{key} 不可为空')
    if len(record['intro']) > 200 or len(record['review']) > 150:
        raise ValueError('介绍限 200 字，评价限 150 字')
    if '\n' in record['intro'] or '\n' in record['review']:
        raise ValueError('介绍和评价应为单段纯文本')
    # Conservative sentence check; decimals and URL periods are not sentence endings.
    if len([x for x in re.split(r'[。！？!?]+|\.(?=\s|$)', record['review']) if x.strip()]) > 1:
        raise ValueError('评价应归纳为一句话')
    tags = record['tags']
    if not isinstance(tags, list) or len(tags) != 5 or any(not isinstance(t, str) or not t.strip() or any(c in t for c in '、\r\n') for t in tags):
        raise ValueError('需要五个非空标签，不可含顿号或换行')
    if len({t.strip().casefold() for t in tags}) != 5:
        raise ValueError('标签必须互不重复')
    if record['url']:
        url = urlsplit(record['url'])
        if url.scheme not in ('http', 'https') or not url.netloc or any(c.isspace() for c in record['url']):
            raise ValueError('官方网址应为 HTTP(S) URL 或空字符串')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', record['updated']):
        raise ValueError('更新时间格式异常')


def render(record, newline):
    token = base64.urlsafe_b64encode(record['identity'].encode()).decode().rstrip('=')
    cells = [encode('、'.join(record[k]) if k == 'tags' else record[k]) for k in KEYS]
    cells[0] += f' <!-- trl-id:{token} -->'
    return '| ' + ' | '.join(cells) + ' |' + newline


def timestamp(offset):
    match = re.fullmatch(r'([+-])(\d{2}):(\d{2})', offset)
    if not match:
        raise ValueError('utc_offset 应为 +08:00 等形式')
    hours, minutes = int(match[2]), int(match[3])
    if hours > 14 or minutes > 59 or (hours == 14 and minutes):
        raise ValueError('时区偏移无效')
    delta = timedelta(hours=hours, minutes=minutes) * (1 if match[1] == '+' else -1)
    return datetime.now(timezone(delta)).strftime('%Y-%m-%d %H:%M')


def inspect(path):
    raw = read(path)
    _, block, rows = parse(raw)
    return {'path': str(path), 'sha256': version(raw), 'managed': block is not None,
            'records': [r for _, r in rows.values()]}


def prepare(raw, payload):
    if payload.get('expected_sha256') != version(raw):
        raise ValueError('文件版本已变化，请重新读取并评估')
    records = payload.get('records')
    if not isinstance(records, list):
        raise ValueError('records 必须为数组')
    lines, block, rows = parse(raw)
    text = ''.join(lines)
    newline = '\r\n' if '\r\n' in text else '\n'
    migrated = bool(block and any(line.strip() == LEGACY_HEADER for line in lines[block[0] + 1:block[1]]))
    if migrated:
        for i in range(block[0] + 1, block[1]):
            ending = '\r\n' if lines[i].endswith('\r\n') else '\n'
            if lines[i].strip() == LEGACY_HEADER:
                lines[i] = HEADER + ending
            elif lines[i].strip() == LEGACY_SEPARATOR:
                lines[i] = SEPARATOR + ending
        for index, _ in rows.values():
            # Append an empty cell without reserializing existing user content.
            ending = '\r\n' if lines[index].endswith('\r\n') else '\n'
            lines[index] = lines[index].rstrip('\r\n') + '  |' + ending
    remove_title = bool(block and ''.join(lines[:block[0]]).lstrip('\ufeff').strip() == '# 宝藏资源库')
    now = timestamp(payload.get('utc_offset', '+08:00'))
    added, changed, unchanged = [], 0, 0
    seen = set()
    for patch in records:
        if not isinstance(patch, dict) or not isinstance(patch.get('identity'), str):
            raise ValueError('每条记录必须提供字符串 identity')
        identity = patch['identity']
        if identity in seen:
            raise ValueError('同批输入有重复 identity')
        seen.add(identity)
        if set(patch) - (set(KEYS) - {'updated'} | {'identity'}):
            raise ValueError('输入包含未知字段或自行指定的更新时间')
        old = rows.get(identity)
        candidate = dict(old[1]) if old else {}
        candidate.update(patch)
        candidate.setdefault('notes', '')
        candidate['updated'] = now
        validate(candidate)
        if old:
            if set(candidate['tags']) == set(old[1]['tags']):
                candidate['tags'] = old[1]['tags']
            if all(candidate[k] == old[1][k] for k in KEYS if k != 'updated'):
                unchanged += 1
                continue
            index = old[0]
            ending = '\r\n' if lines[index].endswith('\r\n') else '\n'
            lines[index] = render(candidate, ending)
            changed += 1
        else:
            added.append(render(candidate, newline))
    stats = {'added': len(added), 'updated': changed, 'unchanged': unchanged, 'schema_migrated': migrated, 'title_removed': remove_title}
    if not added and not changed and not migrated and not remove_title and not payload.get('repair_format', False):
        return raw, stats
    if block:
        # Keep appended rows contiguous with the table, before its closing gap.
        insertion = block[1]
        while insertion > block[0] + 1 and not lines[insertion - 1].strip():
            insertion -= 1
        lines[insertion:insertion] = added
        end = block[1] + len(added)
        # Some Markdown editors require blank lines between HTML and tables.
        if lines[end - 1].strip():
            lines.insert(end, newline)
        if lines[block[0] + 1].strip():
            lines.insert(block[0] + 1, newline)
        result = ''.join(lines)
        if remove_title:
            prefix = ''.join(lines[:block[0]])
            result = ('\ufeff' if prefix.startswith('\ufeff') else '') + result[len(prefix):]
    else:
        if not added:
            return raw, stats
        prefix = text
        if prefix and not prefix.endswith(('\n', '\r')):
            prefix += newline
        if prefix:
            prefix += newline
        result = prefix + START + newline * 2 + HEADER + newline + SEPARATOR + newline + ''.join(added) + newline + END + newline
    return result.encode('utf-8'), stats


def commit(path, expected_raw, output):
    if read(path) != expected_raw:
        raise ValueError('写入前检测到外部修改，已取消')
    fd, temp = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(output)
            stream.flush()
            os.fsync(stream.fileno())
        if read(path) != expected_raw:
            raise ValueError('保存时检测到外部修改，已取消')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def update(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + '.trl.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.close(fd)
        raw = read(path)
        output, stats = prepare(raw, payload)
        if output != raw:
            commit(path, raw, output)
        return {'path': str(path), **stats, 'written': output != raw}
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inspect', 'update'])
    parser.add_argument('--path', required=True)
    parser.add_argument('--input')
    args = parser.parse_args()
    try:
        path = target(args.path)
        if args.command == 'inspect':
            result = inspect(path)
        else:
            if not args.input:
                raise ValueError('update 需要 --input')
            result = update(path, json.loads(Path(args.input).read_text(encoding='utf-8-sig')))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, UnicodeError, KeyError) as exc:
        parser.exit(1, f'未写入或操作失败：{exc}\n')


if __name__ == '__main__':
    main()
