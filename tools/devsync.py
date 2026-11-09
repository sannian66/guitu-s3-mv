#!/usr/bin/env python3
"""tools/devsync.py — 把仓库源码同步进渲染快照（**别再手写临时同步脚本**）

为什么需要：`units/` 和 `lib/` 里的模块把 `ROOT` 硬编码成 `/workspace/work/mv`（渲染沙箱路径）。
直接 `cp` 仓库文件进快照，模块会去找 `/workspace/work/mv/crew/...` 然后崩（FileNotFoundError）。
本工具做四件事，缺一不可：
  ① **只同步改过的文件**（sha256 比对，未变的不写盘 → 快照里 mtime 稳定，缓存不失效）
  ② **重写 ROOT 路径**：`/workspace/work/mv` → `<快照>/code`（外加两个历史临时缓存路径）
  ③ `assets` / `audio` / `fonts` / `align.json` / `lyrics.json` / `analysis.npz` **软链**到仓库（不复制大文件）
  ④ `crew/` **复制**（渲染途中别人改 crew 不影响本次快照）

用法：
  python3 tools/devsync.py out/devsnap                  # 增量同步（默认）
  python3 tools/devsync.py out/devsnap --check          # 只报告哪些文件与仓库不一致，不写盘
  python3 tools/devsync.py out/devsnap --dry-run        # 同上（别名）
  python3 tools/devsync.py out/devsnap --clean          # 先删 code/ 再全量同步
  python3 tools/devsync.py out/devsnap --only units/sec_a_intro_verse1.py   # 只同步指定文件（调试用）
  python3 tools/devsync.py out/devsnap --list           # 打印闭包文件清单就退出

注意：只同步**源码**。`out/`、`assets/gen/` 一律不复制（assets 是软链）。
"""
import ast, hashlib, json, pathlib, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINK = ['assets', 'audio', 'fonts', 'align.json', 'lyrics.json', 'analysis.npz']
COPY = ['crew']
SEED = ['render_sprite_full', 'chorus1', 'sec_a_intro_verse1', 'sec_b_pre1', 'sec_b_verse2',
        'sec_c_pre2_chorus2', 'sec_d_bridge', 'sec_e_final_outro', 'sections']
SEARCH = [ROOT, ROOT / 'units', ROOT / 'lib']
ROOT_CONST = '/workspace/work/mv'
REWRITE = [(ROOT_CONST, None),                       # None = 换成 <快照>/code
           ('/tmp/a_spr', 'cache/a_spr'),
           ('/tmp/spr_cache', 'cache/spr_cache')]


def closure():
    """从 SEED 出发沿 import 递归收集源码闭包（只收 .py）。"""
    pending, seen = list(SEED), {}
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        src = next((d / f'{name}.py' for d in SEARCH if (d / f'{name}.py').exists()), None)
        seen[name] = src
        if src is None:
            continue
        for n in ast.walk(ast.parse(src.read_text())):
            if isinstance(n, ast.Import):
                pending.extend(a.name.split('.')[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module:
                pending.append(n.module.split('.')[0])
    return {n: p for n, p in seen.items() if p is not None}


def render_text(src, code):
    text = src.read_text()
    for a, b in REWRITE:
        text = text.replace(a, str(code) if b is None else str(code.parent / b))
    return text


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dest = pathlib.Path(args[0] if args else 'out/devsnap')
    if not dest.is_absolute():
        dest = (ROOT / dest).resolve()
    code = dest / 'code'
    check = '--check' in sys.argv or '--dry-run' in sys.argv
    only = None
    if '--only' in sys.argv:
        only = sys.argv[sys.argv.index('--only') + 1]

    if not check:
        if '--clean' in sys.argv and code.exists():
            shutil.rmtree(code)
        code.mkdir(parents=True, exist_ok=True)

    files = closure()
    if '--list' in sys.argv:
        for n in sorted(files):
            print(f'{n:28s} {files[n].relative_to(ROOT)}')
        print(f'共 {len(files)} 个文件')
        return

    if only:
        files = {p.stem: p for n, p in files.items() if str(p.relative_to(ROOT)) == only} or {}
        p = ROOT / only
        if p.exists():
            files[p.stem] = p
        if not files:
            print(f'[devsync] --only {only}: 不在闭包里，仍按单文件同步')
            files = {p.stem: p}

    changed, same, manifest = [], 0, {}
    for name, src in files.items():
        rel = src.relative_to(ROOT)
        dst = code / rel
        text = render_text(src, code)
        manifest[str(rel)] = hashlib.sha256(text.encode()).hexdigest()
        if dst.exists() and dst.read_text() == text:
            same += 1
            continue
        changed.append(str(rel))
        if not check:
            dst.parent.mkdir(parents=True, exist_ok=True)
            ast.parse(text)                      # 语法自检：坏文件不写进快照
            dst.write_text(text)

    if not check:
        for name in LINK:
            src, dst = ROOT / name, code / name
            if dst.exists() or dst.is_symlink():
                continue
            dst.symlink_to(src, target_is_directory=src.is_dir())
        for name in COPY:
            src, dst = ROOT / name, code / name
            if not src.exists():
                continue
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        for d in ['cache/a_spr', 'cache/spr_cache', 'chunks', 'logs', 'delivery', 'samples']:
            (dest / d).mkdir(parents=True, exist_ok=True)

    verb = 'CHECK' if check else 'SYNC'
    print(f'[devsync] {verb} {dest}')
    print(f'  闭包 {len(files)} 个文件：改 {len(changed)} / 未变 {same}'
          f'{"（未写盘）" if check else ""}')
    for c in changed[:40]:
        print('   ', c)
    if len(changed) > 40:
        print(f'    …还有 {len(changed) - 40} 个')
    if check and changed:
        print('[devsync] 快照落后于仓库 → 跑一次不带 --check 的同步')
        sys.exit(1)


if __name__ == '__main__':
    main()
