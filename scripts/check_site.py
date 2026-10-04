"""Static preflight using Python's standard library. Does not replace visual/data review."""
import argparse
import json
import os
import re
import subprocess
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'site'
TOKEN = re.compile(r'\{\{[^{}]+\}\}')
MEDIA = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.ico', '.mp4', '.webm', '.woff2', '.pdf'}
ALLOWED = MEDIA | {'.html', '.css', '.js', '.json', '.txt'}
PRIVATE = ('materials/', 'notes/', '.local-preview/', '.codex/', '.env', 'PROJECT_BRIEF.md')

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.refs, self.meta, self.canonical = [], [], {}, []
        self.h1, self.title, self.in_title, self.placeholders, self.errors = 0, '', False, False, []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        if tag == 'h1': self.h1 += 1
        if tag == 'title': self.in_title = True
        if 'data-placeholder' in a: self.placeholders = True
        if tag == 'meta': self.meta[a.get('name', a.get('property', ''))] = a.get('content', '')
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical.append(a.get('href', ''))
        for key in ('src', 'href', 'poster'):
            if key in a: self.refs.append(a[key])
        if 'srcset' in a:
            self.refs.extend(part.strip().split()[0] for part in a['srcset'].split(',') if part.strip())
        if tag == 'img' and 'src' in a and not a.get('alt', '').strip() and a.get('role') != 'presentation': self.errors.append('Image is missing meaningful alt text')
        if tag in ('img', 'video') and 'src' in a and not a['src']: self.errors.append('Empty media source')
        if a.get('target') == '_blank' and 'noopener' not in a.get('rel', '').split(): self.errors.append('New-window link needs rel="noopener"')
    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
    def handle_data(self, data):
        if self.in_title: self.title += data

def inspect(release=False):
    errors, warnings = [], []
    def draft_issue(message): (errors if release else warnings).append(message)
    if not (PUBLIC / 'index.html').is_file(): return ['site/index.html is missing'], []
    config = json.loads((ROOT / 'release.json').read_text(encoding='utf-8'))
    manifest = json.loads((PUBLIC / 'assets/manifest.json').read_text(encoding='utf-8'))
    entries = manifest.get('assets', [])
    inventory = {x['path']: x for x in entries}
    if len(inventory) != len(entries): errors.append('Duplicate paths in assets/manifest.json')
    pages = {}
    for file in PUBLIC.rglob('*'):
        if file.is_symlink() or not file.resolve().is_relative_to(PUBLIC.resolve()):
            errors.append('Symlink or path outside site/: ' + str(file)); continue
        if not file.is_file(): continue
        rel = file.relative_to(PUBLIC).as_posix()
        if file.name != '.nojekyll' and file.suffix.lower() not in ALLOWED: errors.append('Unexpected public file type: ' + rel)
        if any(part.startswith('.') for part in file.relative_to(PUBLIC).parts) and file.name != '.nojekyll': errors.append('Hidden public file: ' + rel)
        if file.stat().st_size >= 100 * 1024 * 1024: errors.append('File reaches 100 MiB; reduce or host separately: ' + rel)
        if file.suffix.lower() in MEDIA:
            if rel not in inventory: errors.append('Media is not in public asset manifest: ' + rel)
            elif not inventory[rel].get('public_approved'): draft_issue('Media not marked for public use: ' + rel)
        if rel.startswith('assets/examples/'): draft_issue('Remove template example before release: ' + rel)
        if file.suffix.lower() in {'.html', '.css', '.js', '.json', '.svg', '.txt'}:
            text = file.read_text(encoding='utf-8')
            if TOKEN.search(text): draft_issue('Unresolved template fields: ' + rel)
        if file.suffix == '.html':
            page = Page(); page.feed(text); pages[file.resolve()] = page
            errors.extend(rel + ': ' + e for e in page.errors)
            if page.h1 != 1: errors.append(rel + ': expected exactly one h1')
            if any(n > 1 for n in Counter(page.ids).values()): errors.append(rel + ': duplicate IDs')
            if page.placeholders: draft_issue('Remove data-placeholder after replacing/removing sample modules: ' + rel)
            if re.search(r'updated manuscript|updated benchmark|existing qualitative demos|YOUR NAME|TODO', text, re.I): draft_issue('Editorial or unfinished copy remains: ' + rel)
    def local_ref(value, base):
        if not value or value == '#': errors.append('Empty/placeholder link in ' + base.name); return
        if TOKEN.search(value): return
        parsed = urlsplit(value)
        if parsed.scheme:
            if parsed.scheme not in {'https', 'mailto', 'tel', 'data'}: errors.append('Unsafe or non-HTTPS URL: ' + value)
            return
        if parsed.netloc or value.startswith('/') or '\\' in value: errors.append('Use project-relative paths: ' + value); return
        target = (base.parent / unquote(parsed.path)).resolve() if parsed.path else base.resolve()
        if not target.is_relative_to(PUBLIC.resolve()): errors.append('Reference escapes public directory: ' + value); return
        if target.is_dir(): target /= 'index.html'
        if not target.is_file(): errors.append('Missing file: ' + value); return
        # Check spelling even on case-insensitive Windows filesystems.
        literal = Path(os.path.abspath(base.parent / unquote(parsed.path))) if parsed.path else base
        if literal.is_dir(): literal /= 'index.html'
        current = PUBLIC
        for part in literal.relative_to(PUBLIC).parts:
            if part not in {p.name for p in current.iterdir()}: errors.append('Path case mismatch: ' + value); return
            current /= part
        if parsed.fragment and target in pages and unquote(parsed.fragment) not in pages[target].ids: errors.append('Broken anchor: ' + value)
    for file, page in pages.items():
        for ref in page.refs: local_ref(ref, file)
    for file in PUBLIC.rglob('*.css'):
        for ref in re.findall(r'url\([\s\'"]*([^\)\'"\s]+)', file.read_text(encoding='utf-8')): local_ref(ref, file)
    for name in inventory:
        path = PUBLIC / name
        if not path.resolve().is_relative_to(PUBLIC.resolve()) or not path.is_file(): errors.append('Manifest path is missing or outside site/: ' + name)
    if release:
        if config.get('content_ready') is not True: errors.append('release.json: content_ready must be true after human-readable final review')
        site_url = config.get('site_url', '')
        if not site_url.startswith('https://') or not site_url.endswith('/'): errors.append('release.json: site_url must be an HTTPS URL ending in /')
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', config.get('repository', '')): errors.append('release.json: set owner/repository')
        if not config.get('branch'): errors.append('release.json: branch is missing')
        page = pages[(PUBLIC / 'index.html').resolve()]
        if not config.get('title') or page.title.strip() != config['title']: errors.append('Page title and release.json title differ')
        for key in ['og:title', 'twitter:title']:
            if page.meta.get(key) != config.get('title'): errors.append('Sharing title differs: ' + key)
        if page.canonical != [site_url] or page.meta.get('og:url') != site_url: errors.append('Canonical / og:url differs from release.json site_url')
        if not page.meta.get('description'): errors.append('Page description is missing')
        for key in ['og:image', 'twitter:image']:
            value = page.meta.get(key, '')
            if not value.startswith(site_url): errors.append('Sharing image must use this site’s absolute URL: ' + key)
            else: local_ref(value[len(site_url):], PUBLIC / 'index.html')
        if os.environ.get('GITHUB_REPOSITORY') and os.environ['GITHUB_REPOSITORY'] != config.get('repository'): errors.append('Workflow repository differs from release.json')
        if os.environ.get('GITHUB_REF_NAME') and os.environ['GITHUB_REF_NAME'] != config.get('branch'): errors.append('Workflow branch differs from release.json')
        try:
            result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True, capture_output=True)
            if result.returncode == 0:
                if Path(result.stdout.strip()).resolve() != ROOT.resolve(): errors.append('This folder is inside another Git repository. Copy it outside before publishing.')
                else:
                    tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
                    errors.extend('Private file is tracked: ' + p for p in tracked if p.startswith(PRIVATE))
        except FileNotFoundError: warnings.append('Git unavailable; tracked-file check skipped')
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', action='store_true', help='Reject all placeholders and unapproved public media')
    args = parser.parse_args()
    try: errors, warnings = inspect(args.release)
    except (OSError, ValueError, KeyError) as error: errors, warnings = [str(error)], []
    for line in warnings: print('WARN:', line)
    for line in errors: print('ERROR:', line)
    print('{}: {} error(s), {} warning(s).'.format('Release' if args.release else 'Draft', len(errors), len(warnings)))
    raise SystemExit(1 if errors else 0)
