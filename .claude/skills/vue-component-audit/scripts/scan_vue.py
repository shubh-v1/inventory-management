#!/usr/bin/env python3
"""Mechanical pre-scan of Vue 3 single-file components.

Collects facts that are tedious to gather by eye so the audit can spend its
effort on judgment. Every hit is a *candidate*, not a verdict: read the code
before reporting it.

Usage:
    python3 scan_vue.py [ROOT ...]        # default: client/src
    python3 scan_vue.py client/src --json # machine-readable output

Handles both <script setup> and Options API components. Standard library only.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

LARGE_FILE_LINES = 400
LARGE_TEMPLATE_LINES = 200

BLOCK_RE = re.compile(r"<(template|script|style)\b([^>]*)>(.*?)</\1>", re.S)
VFOR_RE = re.compile(r"v-for=\"\s*\(?\s*([\w$]+)\s*(?:,\s*([\w$]+))?[^\"]*\"([^>]*)", re.S)
KEY_RE = re.compile(r":key=\"([^\"]+)\"")
CONSOLE_RE = re.compile(r"\bconsole\.(log|debug|info|warn|trace)\s*\(")
DEEP_WATCH_RE = re.compile(r"deep\s*:\s*true")
FUNC_RE = re.compile(
    r"(?:^|\n)\s*(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"
    r"|(?:^|\n)\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\("
    r"|(?:^|\n)\s{2,}(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{"
)
TEMPLATE_CALL_RE = re.compile(r"\{\{[^}]*?\b([A-Za-z_$][\w$]*)\(")
BOUND_CALL_RE = re.compile(r"(?<![@\w-])(?:v-bind)?:[\w.-]+=\"[^\"]*?\b([A-Za-z_$][\w$]*)\(")
TEMPLATE_HEAVY_RE = re.compile(r"\.(filter|map|reduce|sort|find)\(")
TAG_RE = re.compile(r"<([A-Z][A-Za-z0-9]+)[\s/>]")
IMPORT_RE = re.compile(r"import\s+([A-Z][\w$]*)\s+from\s+['\"][^'\"]+\.vue['\"]")
JS_KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "function", "t", "$t"}
# Lifecycle/framework names that naturally repeat across components.
FRAMEWORK_NAMES = {"setup", "data", "mounted", "created", "beforeUnmount", "unmounted",
                   "onMounted", "watch", "computed", "methods", "props", "emits"}
# Cheap built-ins: calling these during render is fine, so they are not reported.
CHEAP_BUILTINS = {"toFixed", "toLocaleString", "toString", "trim", "abs", "min", "max",
                  "round", "floor", "ceil", "toUpperCase", "toLowerCase", "slice",
                  "includes", "String", "Number", "Boolean", "parseInt", "parseFloat"}
# A helper is "heavy" when it iterates over component data (this.x / x.value / a
# collection prop), not when it merely loops over the characters of one value.
HEAVY_BODY_RE = re.compile(
    r"(?:this\.[\w$.]+|[\w$]+\.value(?:\.[\w$]+)*|props\.[\w$.]+)\s*\.(filter|map|reduce|sort|find|findIndex|forEach|some|every)\("
    r"|for\s*\([^)]*(?:this\.|\.value|props\.)[^)]*\)"
)
BUILTIN_TAGS = {"RouterView", "RouterLink", "Transition", "TransitionGroup",
                "KeepAlive", "Teleport", "Suspense", "Component"}


def line_of(text, index, offset=0):
    return text.count("\n", 0, index) + 1 + offset


def scan_file(path, root):
    src = path.read_text(encoding="utf-8")
    try:
        rel = str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        rel = str(path)
    info = {"file": rel, "lines": src.count("\n") + 1, "findings": [], "functions": []}

    blocks = {}
    for m in BLOCK_RE.finditer(src):
        tag, attrs, body = m.group(1), m.group(2), m.group(3)
        start_line = line_of(src, m.start(3))
        blocks.setdefault(tag, []).append((body, start_line - 1, attrs))

    def add(kind, line, detail):
        info["findings"].append({"kind": kind, "line": line, "detail": detail})

    if info["lines"] > LARGE_FILE_LINES:
        add("large-file", 1, f"{info['lines']} lines (threshold {LARGE_FILE_LINES})")

    # Template checks
    for body, off, _ in blocks.get("template", [])[:1]:
        tlines = body.count("\n") + 1
        info["template_lines"] = tlines
        if tlines > LARGE_TEMPLATE_LINES:
            add("large-template", off + 1, f"template is {tlines} lines")
        for m in VFOR_RE.finditer(body):
            item, idx, rest = m.group(1), m.group(2), m.group(3)
            ln = line_of(body, m.start(), off)
            key = KEY_RE.search(m.group(0) + rest.split(">")[0])
            if not key:
                add("vfor-no-key", ln, f"v-for over '{item}' has no :key")
            elif idx and key.group(1).strip() == idx:
                add("vfor-index-key", ln, f":key=\"{idx}\" uses the loop index")
            loop_src = m.group(0)
            if TEMPLATE_HEAVY_RE.search(loop_src):
                add("template-heavy-expr", ln, "v-for source does filter/map/sort inline")
        calls = defaultdict(list)
        for rx in (TEMPLATE_CALL_RE, BOUND_CALL_RE):
            for m in rx.finditer(body):
                name = m.group(1)
                if name in JS_KEYWORDS or name in CHEAP_BUILTINS or name.startswith("$"):
                    continue
                calls[name].append(line_of(body, m.start(), off))
        info["_template_calls"] = calls
        used = set(TAG_RE.findall(body))
        info["_used_components"] = used

    # Script checks
    script_text = ""
    for body, off, attrs in blocks.get("script", []):
        script_text += body
        for m in CONSOLE_RE.finditer(body):
            add("console", line_of(body, m.start(), off), f"console.{m.group(1)}")
        for m in DEEP_WATCH_RE.finditer(body):
            add("deep-watch", line_of(body, m.start(), off), "deep watcher")
        for m in FUNC_RE.finditer(body):
            name = next(g for g in m.groups() if g)
            if name in JS_KEYWORDS:
                continue
            info["functions"].append({"name": name, "line": line_of(body, m.start(), off)})

    # Classify render-time calls: helpers whose body loops over data are the
    # expensive ones (they rerun on every render); pure formatters are cheap.
    defs = sorted(info["functions"], key=lambda f: f["line"])
    script_lines = src.split("\n")
    def body_of(name):
        for i, f in enumerate(defs):
            if f["name"] == name:
                end = defs[i + 1]["line"] - 1 if i + 1 < len(defs) else f["line"] + 25
                return "\n".join(script_lines[f["line"] - 1:min(end, f["line"] + 40)])
        return ""
    light = []
    for name, lines in sorted(info.pop("_template_calls", {}).items()):
        heavy = HEAVY_BODY_RE.search(body_of(name))
        where = ",".join(str(l) for l in sorted(set(lines)))
        if heavy:
            add("render-call-iterates", min(lines),
                f"{name}() runs during render {len(lines)}x (lines {where}); body uses "
                f"'{heavy.group(0)[:40]}' -> candidate for computed")
        else:
            light.append(f"{name} x{len(lines)}")
    if light:
        info["light_render_calls"] = light

    # Components used in the template but never imported/registered
    used = info.pop("_used_components", set())
    imported = set(IMPORT_RE.findall(script_text))
    for comp in sorted(used - imported - BUILTIN_TAGS):
        # Allow kebab/registered names that appear literally in a components: {} block
        if re.search(rf"\b{comp}\b", script_text):
            continue
        add("unresolved-component", 1, f"<{comp}> used but not imported")

    return info


def main(argv):
    as_json = "--json" in argv
    roots = [Path(a) for a in argv if not a.startswith("--")] or [Path("client/src")]
    results = []
    for root in roots:
        files = [root] if root.is_file() else sorted(root.rglob("*.vue"))
        for f in files:
            if "node_modules" in f.parts:
                continue
            results.append(scan_file(f, root if root.is_dir() else root.parent))

    # Cross-file: same helper name defined in several components
    by_name = defaultdict(list)
    for r in results:
        for fn in r["functions"]:
            if fn["name"] in FRAMEWORK_NAMES:
                continue
            by_name[fn["name"]].append(f"{r['file']}:{fn['line']}")
    duplicates = {n: locs for n, locs in by_name.items() if len(locs) > 1}

    if as_json:
        print(json.dumps({"files": results, "duplicate_functions": duplicates}, indent=2))
        return

    print("# Vue pre-scan (candidates only; verify each in the source)\n")
    print("## Files by size")
    for r in sorted(results, key=lambda r: -r["lines"]):
        t = r.get("template_lines", "-")
        print(f"- {r['file']}: {r['lines']} lines (template {t})")
    print("\n## Findings")
    for r in results:
        for f in r["findings"]:
            print(f"- [{f['kind']}] {r['file']}:{f['line']} {f['detail']}")
    print("\n## Cheap render-time calls (usually fine; listed for context)")
    for r in results:
        if r.get("light_render_calls"):
            print(f"- {r['file']}: " + ", ".join(r["light_render_calls"]))
    print("\n## Helper names defined in more than one component")
    for name, locs in sorted(duplicates.items(), key=lambda kv: -len(kv[1])):
        print(f"- {name} ({len(locs)}x): " + ", ".join(locs))


if __name__ == "__main__":
    main(sys.argv[1:])
