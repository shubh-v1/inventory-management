"""
Replace hard-coded colours, spacing, font sizes and radii with design tokens
inside the <style> blocks of Vue SFCs. <template> and <script> are never touched.

Usage (from the repo root):
    python3 .claude/skills/saas-redesign/scripts/tokenize_styles.py client/src [--dry-run]

Run it AFTER the :root tokens exist in App.vue (every token it emits must be
defined there - see the token list in SKILL.md). It skips App.vue and
FilterBar.vue because those are rewritten by hand. Review the diff afterwards:
it is a first pass, not a substitute for manual cleanup.
"""
import glob
import os
import re
import sys

# Existing palette -> semantic tokens. Chart hues map to --chart-* so charts keep
# their exact colours while UI chrome moves to the --color-* scale.
HEX = {
    '#0f172a': 'var(--color-text)', '#1e293b': 'var(--color-text)',
    '#334155': 'var(--color-text-secondary)', '#475569': 'var(--color-text-secondary)',
    '#64748b': 'var(--color-text-muted)', '#94a3b8': 'var(--color-text-subtle)',
    '#e2e8f0': 'var(--color-border)', '#cbd5e1': 'var(--color-border-strong)',
    '#f1f5f9': 'var(--color-surface-muted)', '#f8fafc': 'var(--color-bg)',
    '#2563eb': 'var(--color-accent)', '#1d4ed8': 'var(--color-accent-hover)',
    '#3b82f6': 'var(--chart-blue)', '#10b981': 'var(--chart-green)',
    '#f59e0b': 'var(--chart-amber)', '#ef4444': 'var(--chart-red)',
    '#dc2626': 'var(--color-danger)', '#059669': 'var(--color-success)',
    '#16a34a': 'var(--color-success)', '#d97706': 'var(--color-warning)',
    '#ea580c': 'var(--color-warning)',
    '#eff6ff': 'var(--color-accent-soft)', '#fef2f2': 'var(--color-danger-soft)',
    '#f0fdf4': 'var(--color-success-soft)', '#ecfdf5': 'var(--color-success-soft)',
    '#fffbeb': 'var(--color-warning-soft)',
    '#991b1b': 'var(--color-danger-strong)', '#92400e': 'var(--color-warning-strong)',
    '#065f46': 'var(--color-success-strong)', '#166534': 'var(--color-success-strong)',
    '#1e40af': 'var(--color-accent-strong)',
}
# (px, token step). Off-scale values snap to the nearest step; ties go to the larger.
SPACE = [(4, 1), (8, 2), (12, 3), (16, 4), (20, 5), (24, 6), (32, 8), (40, 10)]
FONT = {12: 'xs', 13: 'sm', 14: 'base', 15: 'base', 16: 'md', 18: 'lg', 22: 'xl', 28: '2xl'}
RADIUS = {6: 'sm', 8: 'md', 10: 'lg', 12: 'lg', 999: 'full', 9999: 'full'}
SKIP = {'App.vue', 'FilterBar.vue'}

SPACING_PROPS = re.compile(r'(padding|margin)(-(top|right|bottom|left|inline|block))?|gap|row-gap|column-gap')


def to_px(value):
    m = re.fullmatch(r'(-?)([\d.]+)(rem|px)', value)
    if not m:
        return None
    n = float(m.group(2))
    return m.group(1), n * 16 if m.group(3) == 'rem' else n


def space_token(px):
    # Leave hairlines and large layout values alone; they aren't rhythm spacing
    if px < 3 or px > 44:
        return None
    step = min(SPACE, key=lambda s: (abs(s[0] - px), -s[0]))[1]
    return f'var(--space-{step})'


def fix_declaration(prop, value):
    if SPACING_PROPS.fullmatch(prop):
        out = []
        for part in value.split():
            conv = to_px(part)
            if conv and conv[1] != 0:
                tok = space_token(conv[1])
                if tok:
                    part = f'calc(-1 * {tok})' if conv[0] else tok
            out.append(part)
        return ' '.join(out)
    if prop == 'font-size':
        conv = to_px(value)
        if conv and round(conv[1]) in FONT:
            return f'var(--text-{FONT[round(conv[1])]})'
    if prop == 'border-radius':
        conv = to_px(value)
        if conv and round(conv[1]) in RADIUS:
            return f'var(--radius-{RADIUS[round(conv[1])]})'
    if prop in ('background', 'background-color') and value in ('white', '#fff', '#ffffff'):
        return 'var(--color-surface)'
    return value


def fix_css(css):
    css = re.sub(r'#[0-9a-fA-F]{6}\b', lambda m: HEX.get(m.group(0).lower(), m.group(0)), css)
    return re.sub(
        r'(?m)^(\s*)([a-z-]+)\s*:\s*([^;{}\n]+?)(\s*;)',
        lambda m: f'{m.group(1)}{m.group(2)}: {fix_declaration(m.group(2), m.group(3).strip())}{m.group(4)}',
        css,
    )


def process(path, dry_run):
    src = open(path).read()
    # Only rewrite the contents of <style ...>...</style>, wherever they sit in the file
    new = re.sub(r'(<style[^>]*>)(.*?)(</style>)',
                 lambda m: m.group(1) + fix_css(m.group(2)) + m.group(3), src, flags=re.S)
    if new != src:
        if not dry_run:
            open(path, 'w').write(new)
        leftover = len(re.findall(r'#[0-9a-fA-F]{6}\b',
                                  ''.join(re.findall(r'<style[^>]*>(.*?)</style>', new, flags=re.S))))
        print(f"{'would update' if dry_run else 'updated'} {path} ({leftover} unmapped hex left in styles)")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    files = glob.glob(os.path.join(root, 'views', '*.vue')) + glob.glob(os.path.join(root, 'components', '*.vue'))
    for path in sorted(files):
        if os.path.basename(path) not in SKIP:
            process(path, dry_run)


if __name__ == '__main__':
    main()
