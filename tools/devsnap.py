#!/usr/bin/env python3
"""tools/devsnap.py — 把仓库的源码闭包镜像到任意目录（做渲染/测试快照）

为什么需要：units/lib 里的模块把 ROOT 硬编码成 `/workspace/work/mv`，在本机直接 import 会找不到资源。
本脚本复制所有被 import 到的 .py（沿 AST 递归收集闭包），把该路径改写成快照绝对路径，并把
assets / audio / fonts 软链过去、crew 复制（避免渲染途中被别人改）。

用法：
  python3 tools/devsnap.py out/devsnap            # 增量同步到 out/devsnap
  python3 tools/devsnap.py out/devsnap --clean    # 先清空 code/ 再同步
  python3 tools/devsnap.py out/devsnap --check    # 只报告哪些文件与仓库不一致
"""
import ast, hashlib, json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINK = ['assets', 'audio', 'fonts', 'align.json', 'align.log', 'lyrics.json', 'analysis.npz', 'previews', 'gen_cands', 'skills']
COPY = ['crew']
SEED = ['render_sprite_full', 'chorus1', 'sec_a_intro_verse1', 'sec_b_pre1', 'sec_b_verse2',
        'sec_c_pre2_chorus2', 'sec_d_bridge', 'sec_e_final_outro', 'sections']
SEARCH = [ROOT, ROOT / 'units', ROOT / 'lib']


def read_src(src, ref):
    """ref 为空 → 读工作区；给了 git ref → 读该 ref 里的同名文件（做 A/B 对照快照）。"""
    if not ref:
        return src.read_text()
    rel = str(src.relative_to(ROOT))
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{ref}:{rel}'], text=True)


def exists_at(src, ref):
    if not ref:
        return src.exists()
    try:
        subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '-e', f'{ref}:{src.relative_to(ROOT)}'], stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def closure(ref=''):
    pending, seen = list(SEED), {}
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        src = next((d / f'{name}.py' for d in SEARCH if exists_at(d / f'{name}.py', ref)), None)
        seen[name] = src
        if src is None:
            continue
        for n in ast.walk(ast.parse(read_src(src, ref))):
            if isinstance(n, ast.Import):
                pending.extend(a.name.split('.')[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module:
                pending.append(n.module.split('.')[0])
    return {n: p for n, p in seen.items() if p is not None}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ref = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else ''
    dest = pathlib.Path(args[0] if args else 'out/devsnap').resolve()
    check = '--check' in sys.argv
    code = dest / 'code'
    if '--clean' in sys.argv and code.exists():
        shutil.rmtree(code)
    code.mkdir(parents=True, exist_ok=True)

    files = closure(ref)
    manifest, changed = {}, []
    for name, src in files.items():
        rel = src.relative_to(ROOT)
        dst = code / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = read_src(src, ref)
        text = text.replace('/workspace/work/mv', str(code))
        text = text.replace('/tmp/a_spr', str(dest / 'cache/a_spr')).replace('/tmp/spr_cache', str(dest / 'cache/spr_cache'))
        manifest[str(rel)] = hashlib.sha256(text.encode()).hexdigest()
        if not dst.exists() or dst.read_text() != text:
            changed.append(str(rel))
            if not check:
                ast.parse(text)
                dst.write_text(text)

    for name in LINK:
        src, dst = ROOT / name, code / name
        if dst.exists() or dst.is_symlink():
            continue
        if not check:
            dst.symlink_to(src, target_is_directory=src.is_dir())
    for name in COPY:
        src, dst = ROOT / name, code / name
        if check:
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    for d in ['cache/a_spr', 'cache/spr_cache', 'chunks', 'logs', 'delivery', 'samples']:
        (dest / d).mkdir(parents=True, exist_ok=True)

    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--short', ref or 'HEAD'], text=True).strip()
    dirty = subprocess.run(['git', '-C', str(ROOT), 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
    (dest / 'source_manifest.json').write_text(json.dumps(
        {'head': head, 'ref': ref or 'WORKTREE', 'dirty': len(dirty.splitlines()), 'files': manifest}, ensure_ascii=False, indent=2))
    verb = 'DIFF' if check else 'SYNC'
    print(f'{verb} {dest}  HEAD={head}  {"dirty" if dirty else "clean"}  files={len(files)}  changed={len(changed)}')
    for c in changed[:25]:
        print('   ', c)


if __name__ == '__main__':
    main()
