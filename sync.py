#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync.py —— 把 posts/ 文件夹里的 Markdown 文章同步进 index.html。

用法（在仓库根目录）：
    python sync.py            # 读取 posts/*.md，重建 index.html 里的 posts 数组
    python sync.py --check    # 只检查有无变化，不写文件（退出码 1 表示有变化）

设计：posts/ 文件夹是唯一真相源，本脚本全量重建。
正文语法与网页后台 parseBody 保持一致：
    #~######  →  标题
    >         →  引用
    ```       →  代码块
    `行内`    →  <code>
不自动 git commit / push，请自行确认后提交。
"""
import sys
import re
import math
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
INDEX = ROOT / "index.html"

CAT_NAME = {"essay": "随笔", "tech": "技术", "life": "生活"}
TRUEISH = {"true", "yes", "1", "on"}

MARK_START = "// ---------- Posts data ----------"
MARK_END = "// ---------- Render ----------"
NL = "\r\n"  # index.html 全程使用 CRLF，写回时必须保持

INLINE_CODE = re.compile(r"`([^`]+)`")


def escape_html(s):
    # 与网页 parseBody 的 escapeHtml 完全一致
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text):
    # 转义 HTML，并把成对反引号转成 <code>；未闭合的反引号按普通字符处理
    out = []
    last = 0
    for m in INLINE_CODE.finditer(text):
        out.append(escape_html(text[last:m.start()]))
        out.append("<code>" + escape_html(m.group(1)) + "</code>")
        last = m.end()
    out.append(escape_html(text[last:]))
    return "".join(out)


def parse_body(text):
    # 复刻网页后台 parseBody：``` 之间为代码块，其余按行解析
    body = []
    segments = text.split("```")
    for i, seg in enumerate(segments):
        if i % 2 == 1:
            code = seg.strip("\n")
            if code.strip() == "":
                continue
            body.append(["pre", "<code>" + escape_html(code) + "</code>"])
        else:
            for line in seg.split("\n"):
                t = line.strip()
                if t == "":
                    continue
                if re.match(r"^#{1,6}", t):
                    body.append(["h2", inline(re.sub(r"^#{1,6}\s*", "", t))])
                elif t.startswith(">"):
                    body.append(["blockquote", inline(re.sub(r"^>\s*", "", t))])
                else:
                    body.append(["p", inline(t)])
    return body


def est_read_time(text):
    # 复刻 estReadTime：中文约 400 字/分钟，向上取整到分钟，最少 1 分钟
    chars = re.sub(r"\s", "", text)
    mins = max(1, math.floor(len(chars) / 400 + 0.5))
    return f"{mins} 分钟"


def parse_frontmatter(raw):
    # 极简 frontmatter 解析：--- 之间的 key: value 行
    meta = {}
    body = raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
    if m:
        fm, body = m.group(1), m.group(2)
        for line in fm.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            meta[k] = v
    return meta, body


def load_posts():
    posts = []
    errors = []
    for md in sorted(POSTS_DIR.glob("*.md")):
        if md.name.lower() == "readme.md":
            continue
        raw = md.read_text(encoding="utf-8")  # 通用换行，统一为 \n
        meta, body_md = parse_frontmatter(raw)
        title = meta.get("title", md.stem)
        cat = meta.get("cat", "essay")
        if cat not in CAT_NAME:
            errors.append(f"{md.name}: 未知分类 '{cat}'（应为 essay/tech/life），已按 essay 处理")
            cat = "essay"
        excerpt = meta.get("excerpt", "")
        date = meta.get("date") or datetime.date.fromtimestamp(md.stat().st_mtime).isoformat()
        body = parse_body(body_md)
        if not body:
            errors.append(f"{md.name}: 正文为空，已跳过")
            continue
        post = {
            "cat": cat,
            "catName": CAT_NAME[cat],
            "date": str(date),
            "read": est_read_time(body_md),
            "title": title,
            "excerpt": excerpt,
            "body": body,
        }
        if str(meta.get("big", "")).lower() in TRUEISH:
            post["big"] = True
        posts.append((post, md.name))
    # 按日期倒序（最新在前）；同日期按文件名倒序，保证结果稳定
    posts.sort(key=lambda x: (x[0]["date"], x[1]), reverse=True)
    return [p for p, _ in posts], errors


def build_block(posts):
    # 与网页 replacePostsInFile 的格式一致，但用 CRLF
    entries = [
        "    " + json.dumps(p, ensure_ascii=False, separators=(",", ":"))
        for p in posts
    ]
    inner = ("," + NL).join(entries)
    return (
        MARK_START + NL
        + "  const posts = [" + NL
        + inner + "," + NL
        + "  ];" + NL + NL
        + "  "
    )


def main():
    check = "--check" in sys.argv
    if not INDEX.exists():
        raise SystemExit(f"找不到 {INDEX}")
    if not POSTS_DIR.exists():
        raise SystemExit(f"找不到文件夹 {POSTS_DIR}，请先创建并放入 .md 文章")

    with open(INDEX, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    s = content.find(MARK_START)
    e = content.find(MARK_END)
    if s == -1 or e == -1:
        raise SystemExit("index.html 格式不正确：找不到 Posts/Render 标记")

    posts, errors = load_posts()
    for msg in errors:
        print("  ⚠ " + msg)

    new_content = content[:s] + build_block(posts) + content[e:]
    changed = new_content != content

    if check:
        print(f"共 {len(posts)} 篇文章；{'有变化' if changed else '无变化'}")
        sys.exit(1 if changed else 0)

    if not changed:
        print(f"✓ 无变化，共 {len(posts)} 篇文章。")
        return

    with open(INDEX, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)
    print(f"✓ 已同步 {len(posts)} 篇文章到 index.html：")
    for p in posts:
        flag = "  [大卡片]" if p.get("big") else ""
        print(f'    · {p["date"]}  {p["catName"]}  {p["title"]}{flag}')
    print('\n下一步：git add -A && git commit -m "更新文章" && git push')


if __name__ == "__main__":
    main()
