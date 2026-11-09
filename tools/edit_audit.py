#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/edit_audit.py —《谁定正邪》MV「转场去重 + 镜长规范」审计工具（只读，不渲染、不改任何 sec_*.py）

做什么
  1) 把 7 个段落模块（A / B导歌一 / 副歌一 / B主歌二 / C / D / E）里的 SHOTS + CUTS 摊平成一张 202 镜总表：
     组 ｜ 镜号 ｜ 帧区间 ｜ 时长 ｜ 入转场 ｜ 转场族 ｜ 是否硬切 ｜ 闪白/闪色 ｜ 震屏 ｜ 金大字(静态命中)
  2) 重复手法统计：同段 15 镜滑窗内的入转场重复、跨段「同一招」重复、硬切连用、闪白连用/密度
  3) 镜长规范检查：0.9–1.4s 正文、每 8–10s 至少 1 镜 0.6–0.8s 加速镜、同段最长 ≤1.8s
     并给出「改这一刀会动到哪些字/锚点」的定位（切点是否压在字头、镜内相对锚点数、绝对秒常量数）
  4) 输出 JSON + Markdown 表（供 crew/round4/edit_plan.md 引用）

为什么要建镜像
  各 units 模块硬编码 ROOT='/workspace/work/mv'。本工具把 units/lib + 少量顶层模块复制到临时目录，
  把该常量 sed 成镜像路径，再 import，从而在不改仓库源码的前提下读到真实的 SHOTS/CUTS。

用法
  python3 tools/edit_audit.py                 # 自动用仓库内置 venv 重跑（需要 numpy/cv2）
  python3 tools/edit_audit.py --json out.json --md out.md
  python3 tools/edit_audit.py --keep-mirror   # 不删临时镜像目录，便于手查

注意：本脚本只读源码、只写 /tmp 与 tools/ 下的产出；不要在这里拍板改切点，方案见 crew/round4/edit_plan.md。
"""
import argparse
import ast
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, OrderedDict, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
VENV_PY = os.path.join(REPO, 'out/full_sprite/chunks/local60_149c727_20261109/venv/bin/python')
ROOT_CONST = '/workspace/work/mv'

# key, 模块名, 组帧起, 组帧止, 标签
GROUPS = [
    ('A',  'sec_a_intro_verse1',  0,    1321, 'A 组 · intro+verse1'),
    ('B1', 'sec_b_pre1',          1321, 1784, 'B 组 · 导歌一'),
    ('C1', 'chorus1',             1784, 2586, '副歌一（标杆，用户点名不动）'),
    ('B2', 'sec_b_verse2',        2586, 3534, 'B 组 · 主歌二'),
    ('C',  'sec_c_pre2_chorus2',  3534, 4839, 'C 组 · pre2+chorus2'),
    ('D',  'sec_d_bridge',        4839, 5797, 'D 组 · bridge'),
    ('E',  'sec_e_final_outro',   5797, 7241, 'E 组 · chorus3+outro'),
]

# ---------------------------------------------------------------- 转场分类
# 转场名 → (族, 中文标签)；未登记的名字落到 'other' 并在报告里点名
TRANS = {
    # 硬切家族
    'hard': ('hard', '硬切'), 'cut': ('hard', '硬切(2帧闪)'), 'none': ('hard', '无冲击硬切'),
    'hard_cut_x': ('hard', '硬切+墨压+色散+顿挫'), 'hard_cut_on_beat': ('hard', '硬切+2帧闪'),
    # 闪
    'flash_white': ('flash', '闪白'), 'flash': ('flash', '闪白'), 'entry_flash': ('flash', '金白闪(段落入口)'),
    'flash_red': ('flash', '闪红'), 'flashr': ('flash', '闪红'), 'gold': ('flash', '闪金'),
    'impact': ('flash', '色闪+位移抖'),
    # 运动（甩/推/穿/滑）
    'whip': ('motion', '甩镜糊'), 'whip_pan_blur': ('motion', '甩镜糊'), 'push': ('motion', '推镜'), 'push_h': ('motion', '横推'),
    'zoom_through': ('motion', '穿镜'), 'a_zoom': ('motion', '穿镜'), 'a_zoom2': ('motion', '穿镜2'),
    'split_slide': ('motion', '分屏滑移'),
    # 图形匹配 / 形状
    'match_cut': ('graphic', '图形匹配'), 'match_line': ('graphic', '光缝匹配'), 'a_seam': ('graphic', '门缝合缝'),
    'iris_moon': ('graphic', '光圈(月)'), 'seal_iris': ('graphic', '印框收放'), 'seal_cover': ('graphic', '印章盖屏'),
    'door_open': ('graphic', '门缝开'), 'light_sweep': ('graphic', '光扫'), 'glitch_cut': ('graphic', '故障切'),
    'freeze_glitch': ('graphic', '故障冻结'), 'freeze_glitch_keep': ('graphic', '故障冻结(保字)'),
    # 遮挡
    'occlusion': ('occl', '前景遮挡'), 'plaque_sweep': ('occl', '木牌横扫'),
    # 撕裂 / 刀
    'paper_tear': ('tear', '撕纸'), 'shatter': ('tear', '碎裂'), 'slash_wipe': ('tear', '刀切擦除'),
    'bolt_cut': ('tear', '闪电切'), 'blade_black': ('tear', '刀光黑切'),
    # 墨 / 烟 / 烧
    'ink_bleed': ('ink', '墨洇'), 'ink_bleed_hd': ('ink', '墨洇HD'), 'ink_swallow': ('ink', '墨吞屏'),
    'ink_press': ('ink', '墨压'), 'smoke_through': ('ink', '烟过'), 'a_cloud': ('ink', '云墙过'),
    'a_brush': ('ink', '飞白大笔'), 'burn_wipe': ('ink', '火线烧过'), 'a_glint': ('ink', '冷光掠'),
    'a_glyph': ('ink', '字转'), 'a_cleave': ('ink', '劈开'), 'a_split': ('ink', '分屏'),
    # 金
    'gold_leaf': ('gold', '金箔'), 'gold_beam': ('gold', '金光束'), 'gold_tip': ('gold', '金尖'),
    'fade_black': ('fade', '黑场'),
    # —— 各组模块内自带的 CUSTOM / BTRANS / c_trans 转场（在 sec_*.py 里注册，不在 lib/trans.py）
    'punch': ('hard', '硬切+推近色散(无白闪)'),          # b_kit：无白闪冲击
    'cloud_wipe': ('ink', '云幕下压'), 'rain_curtain': ('ink', '雨帘落幕'),
    'warm_veil': ('ink', '暖雾封顶'), 'fog_wall': ('ink', '雾墙'),
    'zoom_dark': ('graphic', '推镜圆开门'), 'zoom_iris': ('graphic', '圆开门(无叠化)'),
    'ring_wipe': ('graphic', '声波环开门'), 'lattice_open': ('graphic', '窗格亮开'),
    'luma': ('graphic', '亮度擦除'), 'seam': ('graphic', '缝隙光'),
    'over': ('flash', '闪电过曝切(保留明暗)'),
    'tip': ('motion', '穿刀尖光点'),
    'ink_crack': ('ink', '墨裂'), 'bolt_split': ('tear', '雷劈裂开'), 'blade_sweep': ('tear', '刀身掠镜'),
}
FAMILY_CN = OrderedDict([
    ('hard', '硬切'), ('flash', '闪白/闪色'), ('motion', '甩/推/穿'), ('graphic', '图形匹配'),
    ('occl', '前景遮挡'), ('tear', '撕裂/刀切'), ('ink', '墨/烟/烧'), ('gold', '金'), ('fade', '黑场'),
    ('other', '未登记'),
])

# 各族「硬切」判定：这些族是「一刀下去」的瞬间切（无过渡帧）
INSTANT_FAM = {'hard', 'flash'}
# 各段 'hard' 的实际冲击实现（见 units/*.py 的 Section.raw / HARD_FX）；用于标「闪白」「震屏」
HARD_IMPL = {
    'A':  dict(flash='轻闪白', shake=False, note='提亮22% + 推近3% + 加亮0.05，2帧（sec_a Section.raw）'),
    'B1': dict(flash='轻闪白', shake=False, note='提亮15% + 推近3% + 加亮0.04，2帧（b_kit.Section.raw）'),
    'C1': dict(flash='轻闪白', shake=False, note='提亮15% + 推近2.5% + 加亮0.04，2帧（chorus1.raw）'),
    'B2': dict(flash='轻闪白', shake=False, note='提亮15% + 推近3% + 加亮0.04，2帧（b_kit.Section.raw）'),
    'C':  dict(flash='强闪白', shake=True,  note='3帧电白闪 + 8px 抖 + 色偏（HARD_FX: flash/slam/zoom/strike/quake）'),
    'D':  dict(flash='无', shake=False, note='D 的 hard 不触发任何冲击 = 纯硬切（Bridge.raw 直接 continue）'),
    'E':  dict(flash='轻闪白', shake=False, note='提亮15% + 推近2.5% + 加亮0.04，2帧（_Sec.frame_f）'),
}


# ---------------------------------------------------------------- 镜像 & import
def build_mirror():
    """复制 units/lib + 顶层依赖到临时目录，把 ROOT 硬编码 sed 成镜像路径。返回镜像路径。"""
    mir = tempfile.mkdtemp(prefix='mv_audit_')
    for d in ('units', 'lib'):
        shutil.copytree(os.path.join(REPO, d), os.path.join(mir, d),
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for f in ('proc.py', 'fx.py', 'scenes.py', 'align.json', 'analysis.npz', 'lyrics.json'):
        p = os.path.join(REPO, f)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(mir, f))
    for link in ('fonts', 'assets', 'crew'):
        p = os.path.join(REPO, link)
        if os.path.exists(p):
            os.symlink(p, os.path.join(mir, link))
    # ROOT 常量替换
    for root, _dirs, files in os.walk(mir):
        for fn in files:
            if not fn.endswith('.py'):
                continue
            p = os.path.join(root, fn)
            try:
                s = open(p, encoding='utf-8').read()
            except UnicodeDecodeError:
                continue
            if ROOT_CONST in s:
                open(p, 'w', encoding='utf-8').write(s.replace(ROOT_CONST, mir))
    return mir


def load_modules(mir):
    sys.path[:0] = [os.path.join(mir, 'units'), os.path.join(mir, 'lib'), mir]
    os.environ.setdefault('SPRITE_MODE', '1')
    out = OrderedDict()
    for key, mod, f0, f1, label in GROUPS:
        m = __import__(mod)
        out[key] = m
    return out


# ---------------------------------------------------------------- 静态特征
def class_spans(path):
    """{类名: 源码片段}——用于静态判定「金大字」「镜内相对锚点数」。"""
    src = open(path, encoding='utf-8').read()
    tree = ast.parse(src)
    lines = src.splitlines()
    spans = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            seg = '\n'.join(lines[node.lineno - 1:node.end_lineno])
            spans[node.name] = seg
    return spans


GOLD_RE = re.compile(r'GOLD|gold|\b1\.0,\s*0\.(7|8|9)|\[\s*1\.0,\s*0\.(7|8|9)')
SIZE_RE = re.compile(r'\b([1-9]\d{2,3})\b')


def static_feats(seg):
    """返回 dict(gold=bool, big=bool, rel=相对锚点数, abs=绝对秒常量数)"""
    if seg is None:
        return dict(gold=False, big=False, rel=0, abs=0)
    gold = bool(GOLD_RE.search(seg))
    sizes = [int(x) for x in SIZE_RE.findall(seg)]
    big = any(200 <= s <= 760 for s in sizes)          # 200–760px 视为「大字」（画面有效高 840）
    rel = len(re.findall(r'self\.t0', seg)) + len(re.findall(r'\bu\(t\)', seg))
    abs_ = len(re.findall(r'\b\d{1,3}\.\d{2,3}\b', seg))   # 手写秒常量
    return dict(gold=gold, big=big, rel=rel, abs=abs_)


# ---------------------------------------------------------------- 数据抽取
def frames_of(key, m):
    """返回 [(镜id, f0, f1)]，帧区间左闭右开。"""
    ids = list(getattr(m, 'IDS', [])) or [s.__name__ for s in m.SHOTS]
    if hasattr(m, 'BOUNDS'):                       # E（SHOTS 是 (类, 起帧, 原镜号, 景别) 元组）
        cuts = list(m.BOUNDS) + [m.F1]
    elif hasattr(m, 'CUT_F') and len(getattr(m, 'CUT_F')) == len(ids) + 1:
        cuts = list(m.CUT_F)                   # A / 副歌一
    else:
        cuts = [int(round(s.t0 * FPS)) for s in m.SHOTS] + [int(round(m.SHOTS[-1].t1 * FPS))]
    return [(ids[i], cuts[i], cuts[i + 1]) for i in range(len(ids))]


def cut_entry(key, m, sid, is_first):
    """取该镜入转场 (name, pre, post, kw)；第一镜无入转场。"""
    if is_first:
        return None
    cuts = getattr(m, 'CUTS', {})
    v = cuts.get(sid)
    if v is None:
        return ('hard', 0, 0, {})
    name = v[0]
    pre = v[1] if len(v) > 1 else 0
    post = v[2] if len(v) > 2 else 0
    kw = v[3] if len(v) > 3 else {}
    return (name, pre, post, kw)


def entry_flags(key, m, name, kw, sid):
    """(族, 是否硬切, 闪白/闪色, 震屏)"""
    fam, _ = TRANS.get(name, ('other', name))
    hard = fam == 'hard' and name not in ('hard_cut_x',)
    flash, shake = '', False
    if name in ('hard', 'cut'):
        impl = HARD_IMPL[key]
        flash = impl['flash']
        shake = impl['shake']
        if name == 'cut':
            flash, shake = '闪白(2帧)', False
        elif key == 'C':                        # C 的 hard 按 HARD_FX 分档
            fx = getattr(m, 'HARD_FX', {}).get(sid, 'flash')
            if fx == 'flash':
                flash, shake = '强闪白', True
            elif fx == 'slam':
                flash, shake = '暖闪+下顿', True
            elif fx == 'strike':
                flash, shake = '强闪白(1帧)', True
            elif fx == 'quake':
                flash, shake = '朱偏压暗', True
            elif fx == 'zoom':
                flash, shake = '提亮+径向糊', False
    elif name == 'hard_cut_x':
        flash = '墨压暗(无白闪)'
        shake = bool(any(kw.get('jolt', (0, 0))))
    elif name == 'hard_cut_on_beat':
        flash = '闪%d帧' % int(round(kw.get('flash', 0) * 10)) if kw.get('flash') else ''
        hard = True
    elif name in ('flash_white', 'flash', 'entry_flash'):
        flash = '金白闪' if name == 'entry_flash' else '闪白'
    elif name in ('flash_red', 'flashr'):
        flash = '闪红'
    elif name == 'gold':
        flash = '闪金'
    elif name == 'impact':
        flash = '色闪+抖'
        shake = True
    elif name in ('whip', 'whip_pan_blur'):
        shake = False
    elif name == 'punch':
        flash, hard = '无白闪(推近+色散)', True
    elif name in ('flashr', 'flash', 'gold'):          # b_kit 冲击族里的闪
        flash = {'flashr': '闪红', 'flash': '闪白', 'gold': '闪金'}[name]
        hard = True
    elif name == 'none':
        hard = True
    return fam, hard, flash, shake


def module_funcs(path):
    tree = ast.parse(open(path, encoding='utf-8').read())
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def collect(mir):
    mods = load_modules(mir)
    for key, mod, _f0, _f1, _l in GROUPS:
        setattr(mods[key], '_FUNCS', module_funcs(os.path.join(mir, 'units', mod + '.py')) |
                {n for n in dir(mods[key]) if n.startswith('a_')})
    rows = []
    for key, mod, f0, f1, label in GROUPS:
        m = mods[key]
        spans = class_spans(os.path.join(mir, 'units', mod + '.py'))
        recs = frames_of(key, m)
        for i, (sid, a, b) in enumerate(recs):
            # 段首镜若在 CUTS 里有自施的入口冲击（如 E01 entry_flash），也算一次入转场
            first_self = (i == 0 and sid in getattr(m, 'CUTS', {}))
            e = cut_entry(key, m, sid, i == 0 and not first_self)
            if e is None:
                name, pre, post, kw = '(段首)', 0.0, 0.0, {}
                fam, hard, flash, shake = 'other', False, '', False
            else:
                name, pre, post, kw = e
                fam, hard, flash, shake = entry_flags(key, m, name, kw, sid)
            st = static_feats(spans.get(sid))
            rows.append(dict(
                group=key, glabel=label, id=sid, f0=a, f1=b,
                t0=a / FPS, t1=b / FPS, dur=(b - a) / FPS,
                entry=name, pre=pre, post=post, fam=fam, hard=hard,
                flash=flash, shake=shake, gold=st['gold'], big=st['big'],
                rel=st['rel'], absc=st['abs'],
                vis0=max(a, f0), vis1=min(b, f1),
                clipped=not (a >= f0 and b <= f1),
            ))
    return rows, mods


# ---------------------------------------------------------------- 外部时间轴
def load_lyric_heads():
    segs = json.load(open(os.path.join(REPO, 'align.json'), encoding='utf-8'))['segments']
    heads = []
    for s in segs:
        txt = s['text']
        for w in s.get('words', []):
            ch = w['word'].strip()
            if ch and w.get('start') is not None:
                heads.append((float(w['start']), ch, txt.strip()))
    heads.sort()
    return heads


def load_beats():
    import numpy as np
    return np.load(os.path.join(REPO, 'analysis.npz'))['beats'].astype(float)


# ---------------------------------------------------------------- 统计
def hist(rows, step=0.2, top=2.6):
    nb = int(round(top / step))
    out = Counter()
    for r in rows:
        k = min(nb - 1, int(r['dur'] / step))
        out[k] += 1
    return [(k * step, (k + 1) * step, out.get(k, 0)) for k in range(nb)]


def group_stats(rows):
    st = OrderedDict()
    for key, _mod, f0, f1, label in GROUPS:
        sub = [r for r in rows if r['group'] == key]
        ds = sorted(r['dur'] for r in sub)
        n = len(ds)
        st[key] = dict(
            label=label, n=n, span=(f1 - f0) / FPS, mean=sum(ds) / n,
            med=ds[n // 2], mn=ds[0], mx=ds[-1],
            fast=sum(1 for d in ds if 0.6 - 1e-9 <= d <= 0.8 + 1e-9),
            short=sum(1 for d in ds if d < 0.9), long=sum(1 for d in ds if d > 1.4),
            over=sum(1 for d in ds if d > 1.8),
            hard=sum(1 for r in sub if r['hard']),
            flash=sum(1 for r in sub if r['flash']),
            shake=sum(1 for r in sub if r['shake']),
            distinct=len({r['entry'] for r in sub if r['entry'] != '(段首)'}),
            min_shots=int(-(-round((f1 - f0) / FPS / 1.4 * 1e6) // 1e6)),   # ceil(段长/1.4)
            over_time=round(sum(max(0.0, r['dur'] - 1.4) for r in sub if r['id'] not in EXEMPT), 2),
        )
        st[key]['need_cuts'] = max(0, st[key]['min_shots'] - st[key]['n'])
    return st


def window_repeats(rows, win=15):
    """同段 15 镜滑窗内重复的入转场（按族 & 按具体转场名）。"""
    res = []
    for key, _m, _a, _b, label in GROUPS:
        sub = [r for r in rows if r['group'] == key]
        if len(sub) < win:
            continue
        for i in range(len(sub) - win + 1):
            w = sub[i:i + win]
            fc = Counter(r['fam'] for r in w if r['entry'] != '(段首)')
            nc = Counter(r['entry'] for r in w if r['entry'] != '(段首)')
            res.append(dict(group=key, start=w[0]['id'], end=w[-1]['id'],
                            t0=w[0]['t0'], fam=fc.most_common(3), name=nc.most_common(3),
                            distinct=len(nc)))
    return res


def same_trick(rows):
    """跨段「同一招」：按族统计总数、出现的段、最长连用。"""
    agg = defaultdict(lambda: dict(n=0, groups=Counter(), ids=[]))
    for r in rows:
        if r['entry'] == '(段首)':
            continue
        a = agg[r['fam']]
        a['n'] += 1
        a['groups'][r['group']] += 1
        a['ids'].append((r['group'], r['id'], r['t0']))
    # 硬切连用 / 闪连用
    runs = defaultdict(list)
    for key, _m, _a, _b, _l in GROUPS:
        sub = [r for r in rows if r['group'] == key]
        cur = []
        for r in sub:
            hit = {'hard': r['hard'], 'flash': bool(r['flash'])}.get('hard')
            if r['hard']:
                cur.append(r)
            else:
                if len(cur) >= 2:
                    runs['hard'].append((key, [c['id'] for c in cur]))
                cur = []
        if len(cur) >= 2:
            runs['hard'].append((key, [c['id'] for c in cur]))
        cur = []
        for r in sub:
            if r['flash']:
                cur.append(r)
            else:
                if len(cur) >= 2:
                    runs['flash'].append((key, [c['id'] for c in cur]))
                cur = []
        if len(cur) >= 2:
            runs['flash'].append((key, [c['id'] for c in cur]))
    return agg, runs


def name_counts(rows):
    c = Counter()
    where = defaultdict(list)
    for r in rows:
        if r['entry'] == '(段首)':
            continue
        c[r['entry']] += 1
        where[r['entry']].append((r['group'], r['id'], round(r['t0'], 2)))
    return c, where


def fast_gaps(rows):
    """每段内两枚「加速镜(0.6–0.8s)」之间的最大间隔，>10s 视为缺口。"""
    out = []
    for key, _m, f0, f1, label in GROUPS:
        sub = [r for r in rows if r['group'] == key]
        marks = [r['t0'] for r in sub if 0.599 <= r['dur'] <= 0.801]
        edges = [f0 / FPS] + marks + [f1 / FPS]
        gaps = [(edges[i + 1] - edges[i], edges[i], edges[i + 1]) for i in range(len(edges) - 1)]
        mx = max(gaps)
        out.append(dict(group=key, nfast=len(marks), max_gap=mx[0], at=(mx[1], mx[2]),
                        marks=[round(x, 2) for x in marks], bad=mx[0] > 10.0))
    return out


def lyric_in(heads, a, b):
    return [(t, ch) for (t, ch, _s) in heads if a - 1e-6 <= t <= b + 1e-6]


def near_head(heads, t, tol=0.10):
    for (h, ch, _s) in heads:
        if abs(h - t) <= tol:
            return (h, ch)
    return None


def snap_beat(beats, t, span=0.22):
    best = None
    for b in beats:
        if abs(b - t) <= span and (best is None or abs(b - t) < abs(best - t)):
            best = float(b)
    return best


# ---------------------------------------------------------------- 建议（P2 才动切点）
# 长镜豁免白名单：开场/片名/落版/署名等「慢」是设计，不按规范硬压（理由见报告）
EXEMPT = {
    'A01':  '开场：墨滴入画→云海→残月，2.17s 是唯一一次「黑场呼吸」',
    'A06':  '片名「谁定正邪」刀光在镜内完成，属屏幕层停留',
    'A07a': '片名仍在屏上（屏幕层不动），同属片名停留',
    'E30':  '片尾落版：金匾/署名段，慢是刻意的',
    'E31':  '片尾落版', 'E32': '片尾落版', 'E33': '片尾落版', 'E34': '片尾落版：收墨前最后一口气',
    'E35':  '片尾落版（朱印「谁定正邪」）', 'E36': '收墨落版 2.23s，全片最后一镜',
    'S30_Da': '「答」字定格收束（bridge 收尾，长镜=停顿）',
}
# 只读段落（用户点名：副歌一是标杆，不动）
READONLY = {'C1'}


def dur_cost(d, fast_bonus=True):
    """镜长规范代价：正文 0.9–1.4s 零代价；0.6–0.8s 加速镜低代价；越界递增；>1.8s / <0.45s 重罚。"""
    if 0.9 - 1e-9 <= d <= 1.4 + 1e-9:
        return 0.0
    if 0.6 - 1e-9 <= d <= 0.8 + 1e-9:
        return 0.10 if fast_bonus else 0.5
    if 0.8 < d < 0.9:
        return 0.10 + 0.8 * (0.9 - d)
    if 1.4 < d <= 1.8:
        return 1.1 * (d - 1.4)
    if d > 1.8:
        return 0.44 + 5.0 * (d - 1.8)
    if 0.45 <= d < 0.6:
        return 1.4
    return 8.0


def retime_group(sub, beats, heads, lam=0.75, prot=3.0, pin=(), dmin=0.55, dmax=1.85):
    """对一段做「卡拍网格上的 DP 重定时」：镜数不变（不加不减镜），每个切点吸附到最近拍点。
    目标 = 镜长规范代价 + 位移代价（字头切点位移代价 ×4）。
    pin 里的镜「钉住」（豁免镜 / 标杆段）：它的两个边界都不许动。
    返回 [(原秒, 新秒, 是否压字头, 左镜新时长, 右镜新时长)]，只含内部边界。"""
    n = len(sub)
    if n < 2:
        return []
    B = [r['t0'] for r in sub] + [sub[-1]['t1']]
    prot_flag = [bool(near_head(heads, B[j], 0.075)) for j in range(n + 1)]
    pinned = [False] * (n + 1)                     # 边界 j 是否被钉住
    for i in pin:
        if 0 <= i < n:
            pinned[i] = pinned[i + 1] = True
    cand = [None] * (n + 1)
    cand[0] = [B[0]]
    cand[n] = [B[n]]
    for j in range(1, n):
        if pinned[j]:
            cand[j] = [B[j]]
        else:
            c = [b for b in beats if abs(float(b) - B[j]) <= 0.9]
            c.append(B[j])
            cand[j] = sorted({round(x * FPS) / FPS for x in c})

    def shift_pen(j, pos):
        return abs(pos - B[j]) * (prot if prot_flag[j] else lam)

    INF = float('inf')
    layers = [cand[j] for j in range(1, n)]
    dp, back = {}, []
    dp = {pos: dur_cost(pos - B[0]) + 0.5 * shift_pen(1, pos) for pos in layers[0]}
    for j in range(1, n - 1):
        nd, nb = {}, {}
        for pos in layers[j]:
            best, arg = INF, None
            for ppos, cost in dp.items():
                d = pos - ppos
                if d < dmin or d > dmax:
                    continue
                c = cost + dur_cost(d) + 0.5 * shift_pen(j, ppos) + 0.5 * shift_pen(j + 1, pos)
                if c < best:
                    best, arg = c, ppos
            nd[pos], nb[pos] = best, arg
        back.append(nb)
        dp = nd
    best, arg = INF, None
    for ppos, cost in dp.items():
        d = B[n] - ppos
        if d < dmin or d > dmax:
            continue
        c = cost + dur_cost(d) + 0.5 * shift_pen(n - 1, ppos)
        if c < best:
            best, arg = c, ppos
    if arg is None:
        return []
    path = [arg]
    for j in range(len(back) - 1, -1, -1):
        path.append(back[j][path[-1]])
    path.reverse()
    newB = [B[0]] + path + [B[n]]
    return [(B[j], newB[j], prot_flag[j], newB[j] - newB[j - 1], newB[j + 1] - newB[j])
            for j in range(1, n)]


def propose(rows, heads, beats):
    """生成 P2 施工清单：每段边界的位移 + 这一刀动到的字头/镜内锚点。"""
    out = []
    for key, _m, f0, f1, label in GROUPS:
        sub = [r for r in rows if r['group'] == key]
        pin = [i for i, r in enumerate(sub) if r['id'] in EXEMPT]
        if key in READONLY:
            pin = list(range(len(sub)))
        moves = retime_group(sub, beats, heads, pin=pin)
        for j, (old, new, ishead, ndl, ndr) in enumerate(moves, start=1):
            if abs(new - old) < 1e-6:
                continue
            a, b = sub[j - 1], sub[j]
            out.append(dict(
                group=key, cut_id='%s|%s' % (a['id'], b['id']),
                left=a['id'], right=b['id'],
                old_f=int(round(old * FPS)), new_f=int(round(new * FPS)),
                delta=round(new - old, 3), dF=int(round((new - old) * FPS)),
                on_head=ishead, at_head=(near_head(heads, old) or (None,))[0],
                new_at_head=(near_head(heads, new) or (None,))[0],
                left_dur=(round(a['dur'], 2), round(ndl, 2)), right_dur=(round(b['dur'], 2), round(ndr, 2)),
                left_entry=a['entry'], right_entry=b['entry'],
                left_flash=a['flash'], right_flash=b['flash'],
                left_rel=a['rel'], right_rel=b['rel'],
                left_abs=a['absc'], right_abs=b['absc'],
                lyric=[(round(t, 2), ch) for t, ch in
                       lyric_in(heads, min(old, new) - 0.1, max(old, new) + 0.1)],
                readonly=key in READONLY,
            ))
    return out


# ---------------------------------------------------------------- 同质化 / 去重候选
CAND_POOL = [   # 「无白闪」替代招（P0 只换名时的候选池；按「不留白帧」优先排序）
    'punch', 'hard_cut_x', 'luma', 'ink_crack', 'bolt_split',
    'ink_press', 'ink_swallow', 'ink_bleed', 'ink_bleed_hd', 'glitch_cut', 'freeze_glitch',
    'match_cut', 'match_line', 'occlusion', 'plaque_sweep', 'paper_tear', 'slash_wipe',
    'shatter', 'burn_wipe', 'blade_black', 'seal_iris', 'door_open', 'light_sweep',
    'smoke_through', 'cloud_wipe', 'rain_curtain', 'warm_veil', 'lattice_open', 'ring_wipe',
    'zoom_iris', 'zoom_through', 'push', 'push_h', 'tip', 'seam', 'a_glint', 'a_brush',
    'a_cleave', 'a_cloud', 'a_seam', 'a_split', 'gold_leaf', 'gold_beam', 'gold_tip',
]


EXTRA_AVAIL = {   # 各段 Section.raw 里特判的「冲击型」名字（不是普通 trans 函数）
    'A':  {'a_cleave', 'a_zoom', 'a_zoom2', 'a_glyph', 'a_split', 'a_seam', 'a_cloud', 'a_brush', 'a_glint'},
    'B1': {'punch', 'flash', 'flashr', 'gold', 'none'}, 'C1': set(),
    'B2': {'punch', 'flash', 'flashr', 'gold', 'none'}, 'C': {'hard', 'match_line'},
    'D':  {'hard', 'hard_cut_x'}, 'E': {'hard'},
}


def avail_set(key, m):
    """该段 CUTS 里能安全写进去的转场名集合（lib 注册表 + 段落命名空间 + 段落 BTRANS/CUSTOM/CX.NAMES）。"""
    import trans as TR
    names = set(TR.TRANSITIONS)
    for attr in ('CUSTOM',):
        names |= set((getattr(m, attr, None) or {}))
    bk = getattr(m, 'BK', None)
    if bk is not None:
        names |= set((getattr(bk, 'BTRANS', None) or {}))
    for attr in ('K', 'CX', 'D', 'BTRANS'):
        x = getattr(m, attr, None)
        if hasattr(x, 'NAMES'):
            names |= set(x.NAMES)
    # 模块里自定义的转场函数（a_* / d_* / gold_beam / hard_cut_x …）
    names |= {n for n in getattr(m, '_FUNCS', ())}
    names |= EXTRA_AVAIL.get(key, set())
    names |= {v[0] for v in (getattr(m, 'CUTS', None) or {}).values()}     # 本段已经在用的，必然能 dispatch
    names -= {'hard', 'none', 'cut'} if key in ('B1', 'B2') else set()
    return names


def neighbours(rows, key, i, span=7):
    sub = [r for r in rows if r['group'] == key]
    return sub[max(0, i - span):i + span + 1]


def homogeneity(rows, win=15, thr_flash=4, thr_hard=5):
    """同段滑窗同质化：闪≥thr 或 硬切≥thr 的窗口。"""
    bad = []
    for key, _m, _a, _b, _l in GROUPS:
        sub = [r for r in rows if r['group'] == key]
        if len(sub) < win:
            continue
        for i in range(len(sub) - win + 1):
            w = sub[i:i + win]
            nf = sum(1 for r in w if r['flash'])
            nh = sum(1 for r in w if r['hard'])
            if nf >= thr_flash or nh >= thr_hard:
                bad.append(dict(group=key, ids=w[0]['id'] + '…' + w[-1]['id'],
                                t0=round(w[0]['t0'], 1), t1=round(w[-1]['t1'], 1),
                                flash=nf, hard=nh,
                                names=[r['entry'] for r in w if r['entry'] != '(段首)']))
    return bad


def p0_candidates(rows, mods=None):
    """P0（只换转场名，不动一帧）：把压在闪白/硬切连用里的刀，换成同段没出现过的「无白闪」招。"""
    out = []
    mods = mods or {}
    for key, _m, _a, _b, _l in GROUPS:
        if key in READONLY:
            continue
        sub = [r for r in rows if r['group'] == key]
        ok_names = avail_set(key, mods[key]) if key in mods else set(CAND_POOL)
        for i, r in enumerate(sub):
            if r['entry'] in ('(段首)',) or r['id'] in EXEMPT:
                continue
            if not r['flash'] or '闪' not in r['flash'] or '无白闪' in r['flash']:
                continue
            nb = neighbours(rows, key, i)
            nf = sum(1 for x in nb if x['flash'])
            nh = sum(1 for x in nb if x['hard'])
            if nf < 4 and nh < 4:
                continue
            used = Counter(x['entry'] for x in nb)
            cands = [n for n in CAND_POOL if used[n] == 0 and n in ok_names]
            if not cands:
                continue
            # 优先：与本节现有视觉语言相近、且「不是闪」的招
            out.append(dict(group=key, id=r['id'], dur=round(r['dur'], 2),
                            cur=r['entry'], flash=r['flash'], hard=r['hard'],
                            win_flash=nf, win_hard=nh,
                            alt=cands[:6], lyric=[(round(t, 2), ch) for t, ch in
                                                  lyric_in(load_lyric_heads(), r['t0'] - 0.1, r['t1'] + 0.1)]))
    return out


def p1_candidates(rows):
    """P1（只改 pre/post，一帧切点都不动）：过渡窗口长度问题。
    规则：
      ① 图形匹配族 pre==0 → 转场只跑「切后半程」（p 从 0.5 起），中间帧没有两镜同框，匹配感丢失
      ② 有形转场（撕/墨/刀）pre+post < 0.12s → 视觉上几乎等于硬切，等于白写了一个转场
      ③ post > 0.28s → 切后拖太久，压住新镜的字头
      ④ pre+post > 0.6×本镜时长 → 过渡吃掉半个镜头
    """
    out = []
    for r in rows:
        if r['entry'] == '(段首)':
            continue
        pre, post = r['pre'], r['post']
        why = None
        if r['fam'] == 'graphic' and pre < 1e-9:
            why = '匹配/形状类 pre=0，只有切后半程（无两镜同框的匹配帧）→ 建议 pre 0.06–0.12'
        elif r['fam'] in ('tear', 'ink', 'occl') and (pre + post) < 0.12:
            why = '有形转场只有 %.2fs，几乎等于硬切 → 建议 0.10/0.16' % (pre + post)
        elif post > 0.28:
            why = '切后 %.2fs 太长，压新镜字头 → 收到 0.20' % post
        elif (pre + post) > 0.6 * r['dur']:
            why = '过渡占本镜 %.0f%%（%.2f / %.2fs）→ 收到 %.2f' % (100 * (pre + post) / r['dur'], pre + post, r['dur'],
                                                            0.5 * r['dur'])
        if why:
            out.append(dict(group=r['group'], id=r['id'], entry=r['entry'], pre=pre, post=post,
                            dur=r['dur'], why=why, fam=r['fam']))
    return out


def p2b_splits(rows, heads, beats):
    """P2b（最高风险）：光移刀满足不了规范（均值已超 1.4s），必须「长镜内加一刀」。
    对每个非豁免的 >1.4s 镜，给出建议劈点（卡拍）与两半时长。"""
    out = []
    for key, _m, _a, _b, _l in GROUPS:
        if key in READONLY:
            continue
        sub = [r for r in rows if r['group'] == key]
        for r in sub:
            if r['dur'] <= 1.401 or r['id'] in EXEMPT:
                continue
            mid = r['t0'] + r['dur'] / 2
            cand = [float(b) for b in beats if r['t0'] + 0.55 <= b <= r['t1'] - 0.55]
            if not cand:
                continue
            sp = min(cand, key=lambda t: abs(t - mid))
            sp = round(sp * FPS) / FPS
            L, R = sp - r['t0'], r['t1'] - sp
            out.append(dict(group=key, id=r['id'], dur=round(r['dur'], 2),
                            split_f=int(round(sp * FPS)), L=round(L, 2), R=round(R, 2),
                            rel=r['rel'], absc=r['absc'],
                            lyric=[(round(t, 2), ch) for t, ch in lyric_in(heads, sp - 0.4, sp + 0.4)],
                            entry=r['entry']))
    return out


def compliance(rows, moved=None):
    moved = moved or set()
    """逐镜标注：要不要改（不改 / 加速镜保留 / 改切点 / 豁免）。"""
    tags = {}
    for r in rows:
        d = r['dur']
        key = (r['group'], r['id'])          # 注意：V01/S02 这类镜号在 A/B2/D 里会重名，必须带组
        if r['id'] in EXEMPT:
            tags[key] = ('豁免', EXEMPT[r['id']])
        elif 0.9 - 1e-9 <= d <= 1.4 + 1e-9:
            tags[key] = ('不改', '正文达标 %.2fs' % d)
        elif 0.6 - 1e-9 <= d <= 0.8 + 1e-9:
            tags[key] = ('保留', '加速镜 %.2fs（0.6–0.8 配额）' % d)
        elif d > 1.4:
            way = 'P2 移刀' if key in moved else 'P2b 加刀（移刀救不了）'
            tags[key] = ('改', ('超 1.8s 硬顶' if d > 1.8 else '偏长') + ' %.2fs → %s' % (d, way))
        else:
            way = 'P2 移刀' if key in moved else 'P2b 加刀'
            tags[key] = ('改', ('短于 0.6s 底限' if d < 0.6 else '偏短') + ' %.2fs → %s' % (d, way))
    return tags



# ---------------------------------------------------------------- 用户点名的三段
FAVS = [
    ('1:30–1:40', 90.0, 100.0),
    ('1:58–2:04', 118.0, 124.0),
    ('2:41–2:57', 161.0, 177.0),
]


def fav_stats(rows):
    out = []
    for name, a, b in FAVS:
        sub = [r for r in rows if r['f1'] / FPS > a + 1e-6 and r['t0'] < b - 1e-6]
        names = [r['entry'] for r in sub if r['entry'] != '(段首)']
        out.append(dict(name=name, a=a, b=b, n=len(sub),
                        avg=sum(r for r in (min(r['t1'], b) - max(r['t0'], a) for r in sub)) / max(1, len(sub)),
                        distinct=len(set(names)), names=names, ids=[r['id'] for r in sub]))
    return out


# ---------------------------------------------------------------- Markdown 输出
def verify_names(mods, pairs):
    """候选转场名落地可行性验证：在 1080p 零图上跑一次 p=0.5，确认该段能 dispatch 且形状正确。
    （不是渲染整片；单个转场函数 <0.5s，属于「单帧核查」范围）"""
    import numpy as np
    res = {}
    A = np.zeros((1080, 1920, 3), np.float32)
    B = np.ones((1080, 1920, 3), np.float32) * 0.5
    for item in pairs:
        key, name = item[0], item[1]
        kw = dict(item[2]) if len(item) > 2 else {}
        m = mods[key]
        try:
            fn = None
            bk = getattr(m, 'BK', None)
            cx = getattr(m, 'CX', None)
            if bk is not None and name in (getattr(bk, 'BTRANS', None) or {}):
                fn = bk.BTRANS[name]
            elif cx is not None and name in (getattr(cx, 'NAMES', None) or {}):
                fn = cx.NAMES[name]
            elif name in (getattr(m, 'CUSTOM', None) or {}):
                fn = m.CUSTOM[name]
            elif name == 'a_cleave' and hasattr(m, 'R8'):
                fn = m.R8.a_cleave8
            elif name == 'match_line':                  # C 段 Section.raw 内联特判（无独立函数）
                res['%s|%s' % (key, name)] = 'ok(inline)'
                continue
            elif hasattr(m, name) and callable(getattr(m, name)):
                fn = getattr(m, name)
            else:
                import trans as TR
                fn = TR.TRANSITIONS.get(name)
            if fn is None:
                res['%s|%s' % (key, name)] = 'no-dispatch'
                continue
            out = fn(A.copy(), B.copy(), 0.5, **kw)
            res['%s|%s' % (key, name)] = 'ok' if getattr(out, 'shape', None) == A.shape else 'bad-shape'
        except Exception as e:
            res['%s|%s' % (key, name)] = 'ERR %s' % type(e).__name__
    return res


# ---------------------------------------------------------------- 人工策展的 P0 换名清单
# (组, 镜号, 原转场, 新转场, pre, post, kw, 策展理由)
# 规则：① 只换名字，一帧切点都不动；② 只换 dur≥0.8s 的刀（更短的刀换 0.2s 转场会吃掉半镜）；
#      ③ 换成该段自己用过/已注册的「无白闪」招，保持视觉母题；④ 真正的冲击点保留（E05/E23/E27a/E27b/E28、C1 段）。
SWAPS = [
    # ——— E 段（闪密度最高：20/38）———
    ('E', 'E02', 'hard', 'ink_swallow', 0.14, 0.20, dict(center=(900, 380), seed=202), '「刀不放」：墨晕吞屏与 E03/E29 同族，但不与邻刀重名'),
    ('E', 'E04', 'hard', 'seal_cover', 0.10, 0.18, dict(center=(820, 470), rot=-5), '匾特写「什么天理昭」→ 朱印盖屏，接「昭彰」印章母题'),
    ('E', 'E07', 'hard', 'blade_black', 0.10, 0.16, dict(angle=-28, width=210, seed=7), '「是谎言」→ 刀光黑切（E10 同族，隔 3 刀），暗底不留白'),
    ('E', 'E08', 'hard', 'paper_tear', 0.08, 0.16, dict(seed=8, angle=5), '「伪装」→ 撕纸，纸感对位「伪装」的假面'),
    ('E', 'E11', 'hard', 'occlusion', 0.10, 0.14, dict(kind='pillar', direction=-1, color=(0.03, 0.02, 0.015)), '「定规章」→ 前景暗剪影横扫（E06 同族，隔 5 刀）'),
    ('E', 'E13', 'hard', 'ink_swallow', 0.16, 0.18, dict(center=(1000, 520), seed=13), '「血未冷骨」→ 墨吞屏；与 E02 隔 11 刀'),
    ('E', 'E21', 'flash_red', 'door_open', 0.00, 0.20, dict(cx=960), '「判我」→ 门缝开（E16 同族），朱红闪挪到 E23 保留'),
    # ——— C 段（13/43，C17/C22/C30/C36 四处连闪）———
    ('C', 'C17', 'hard', 'ink_crack', 0.08, 0.16, dict(center=(960, 540), seed=217), '「刀不」→ 墨裂（C 段已有 ink_crack 语言），替换第 2 刀连闪'),
    ('C', 'C22', 'hard', 'luma', 0.06, 0.16, dict(), '「若规则」→ 亮度擦除（C 段自己的无白闪招）'),
    ('C', 'C30', 'flash_red', 'bolt_split', 0.00, 0.18, dict(x0=1100, seed=330), '「血未冷骨」→ 雷劈裂开，只雷路发光不提亮整幅'),
    ('C', 'C36', 'flash_red', 'match_line', 0.00, 0.14, dict(), '「天不」→ 光缝匹配（与 C02 同一招但隔 34 刀）'),
    # ——— A 段（11/29，硬切全段无变化）———
    ('A', 'V02', 'hard', 'zoom_through', 0.08, 0.16, dict(center=(960, 540)), 'A 段 0 处甩/推，补一个穿镜（慢段里唯一运动转场）'),
    ('A', 'V06', 'hard', 'ink_bleed', 0.12, 0.18, dict(seed=206, center=(1250, 420)), '水墨洇开（A 段母题），断开 V05-V06 的硬切连用'),
    ('A', 'V14', 'hard', 'a_cleave', 0.10, 0.16, dict(angle=32, center=(960, 540)), '「每一次拔刀」→ 劈开（A 段自有 a_cleave，V12/V21 用过）'),
    ('A', 'V17', 'hard', 'paper_tear', 0.08, 0.16, dict(seed=217, angle=6), '「由权势执掌」→ 撕纸，断开 V17 与前后的闪'),
    # ——— B1 段（6/15）———
    ('B1', 'P07', 'flash_white', 'shatter', 0.06, 0.18, dict(seed=7, center=(1060, 880), n=60), '「我不信」→ 碎裂，去掉唯一一处纯白闪'),
    ('B1', 'P11', 'gold', 'occlusion', 0.10, 0.14, dict(kind='spear', direction=-1, seed=11), '「当」→ 枪林横扫（B1 与战争语境同族）'),
    ('B1', 'P13', 'flash_red', 'rain_curtain', 0.06, 0.14, dict(seed=13), '「刀还」→ 雨帘落幕（b_kit 自有，B2 用过三次）'),
]


def tighten_swaps(rows, heads, swaps):
    """P0 的第二道闸：转场窗口不许压住本镜第一个字头。
    规则：post 收到「切点→下一个字头」-0.02s，且不低于 0.06/0.08（按族）；pre 不动。
    返回 (新 swaps, 调整说明)。"""
    idx = {(r['group'], r['id']): r for r in rows}
    out, notes = [], []
    for g, sid, old, new, pre, post, kw, note in swaps:
        r = idx.get((g, sid))
        if r is None:
            out.append((g, sid, old, new, pre, post, kw, note))
            continue
        c = r['t0']
        floor = 0.08 if TRANS.get(new, ('other',))[0] in ('ink', 'tear', 'graphic', 'occl') else 0.06
        nxt = next((h[0] for h in heads if h[0] > c + 1e-6), None)
        newpost = post
        if nxt is not None:
            room = (nxt - c) - 0.02
            if room < post:
                newpost = max(floor, round(room / 0.02) * 0.02)
                notes.append('%s %s：下一个字头在切后 %.2fs，post %.2f→%.2f 避免压字'
                             % (g, sid, nxt - c, post, newpost))
        out.append((g, sid, old, new, pre, newpost, kw, note))
    return out, notes


def simulate_swaps(rows, swaps):
    """把 P0 换名「试算」一遍（不改代码，只改内存里的表），返回前后对比：闪计数 / 最差 15 镜窗口 / 硬切连用。"""
    import copy
    before = copy.deepcopy(rows)
    after = copy.deepcopy(rows)
    idx = {(r['group'], r['id']): r for r in after}
    for g, sid, old, new, pre, post, kw, _note in swaps:
        r = idx.get((g, sid))
        if r is None:
            continue
        fam, _cn = TRANS.get(new, ('other', new))
        r['entry'] = new
        r['pre'], r['post'] = pre, post
        r['fam'] = fam
        r['hard'] = fam == 'hard'
        fl = ''
        if fam == 'flash':
            fl = {'flash_white': '闪白', 'flash_red': '闪红', 'entry_flash': '金白闪', 'impact': '色闪+抖',
                  'over': '过曝切'}.get(new, '闪')
        elif fam == 'hard':
            fl = HARD_IMPL[g]['flash']
        r['flash'] = fl
        r['shake'] = bool(fam == 'flash' and new == 'impact')

    def cnt(rs):
        d = {}
        for k, *_ in GROUPS:
            sub = [r for r in rs if r['group'] == k]
            d[k] = dict(flash=sum(1 for r in sub if r['flash']), hard=sum(1 for r in sub if r['hard']),
                        distinct=len({r['entry'] for r in sub if r['entry'] != '(段首)'}))
        return d

    def worst(rs, win=15):
        o = {}
        for k, *_ in GROUPS:
            sub = [r for r in rs if r['group'] == k]
            best = (0, 0, None)
            for i in range(max(0, len(sub) - win + 1)):
                w = sub[i:i + win]
                f = sum(1 for r in w if r['flash'])
                h = sum(1 for r in w if r['hard'])
                if f > best[0]:
                    best = (f, h, w[0]['id'] + '…' + w[-1]['id'])
            o[k] = best
        return o
    return cnt(before), cnt(after), worst(before), worst(after)


def md_t1(rows, tags):
    L = ['| 组 | 镜号 | 帧区间 | 时长s | 入转场 | 转场族 | 硬切 | 闪白/闪色 | 震屏 | 镜内锚点 | 评定 |',
         '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        tg = tags.get((r['group'], r['id']), ('', ''))[0]
        L.append('| %s | %s | %d–%d | %.2f | `%s` | %s | %s | %s | %s | %d | %s |' % (
            r['group'], r['id'], r['f0'], r['f1'], r['dur'], r['entry'],
            '—' if r['entry'] == '(段首)' else FAMILY_CN.get(r['fam'], r['fam']),
            '是' if r['hard'] else '',
            r['flash'] or '',
            '是' if r['shake'] else '',
            r['rel'], tg))
    return '\n'.join(L)


def md_t3(rows, st, h, props, fg_, tags):
    L = []
    L.append('### T3-a 镜长分布（全片直方图，0.2s 一格）\n')
    L.append('| 区间 s | 镜数 | 占比 | |')
    L.append('|---|---|---|---|')
    tot = len(rows)
    for lo, hi, c in h:
        L.append('| %.1f–%.1f | %d | %.1f%% | %s |' % (lo, hi, c, 100.0 * c / tot, '█' * c))
    L.append('')
    edges = [(0.0, 0.6), (0.6, 0.8), (0.8, 1.0), (1.0, 1.2), (1.2, 1.4), (1.4, 1.8), (1.8, 9.9)]
    L.append('### T3-a2 分段镜长分布（镜数）\n')
    L.append('| 区间 s | ' + ' | '.join(k for k, *_ in GROUPS) + ' | 全片 |')
    L.append('|---|' + '---|' * (len(GROUPS) + 1))
    for lo, hi in edges:
        cells, tot = [], 0
        for k, *_r in GROUPS:
            c = sum(1 for r in rows if r['group'] == k and lo - 1e-9 <= r['dur'] < hi)
            cells.append(str(c)); tot += c
        L.append('| %s%.1f–%.1f | %s | %d |' % ('>' if hi > 9 else '', lo, min(hi, 2.8), ' | '.join(cells), tot))
    L.append('')
    L.append('### T3-b 分段镜长统计\n')
    L.append('| 组 | 镜数 | 均值 | 中位 | 最短 | 最长 | 加速镜0.6–0.8 | <0.9s | >1.4s | >1.8s | 均值×段长 |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|')
    for k, v in st.items():
        L.append('| %s | %d | %.2f | %.2f | %.2f | %.2f | %d | %d | %d | %d | %d 镜/%d 镜 |' % (
            k, v['n'], v['mean'], v['med'], v['mn'], v['mx'], v['fast'], v['short'], v['long'], v['over'],
            v['fast'], v['n']))
    L.append('')
    L.append('### T3-c 加速镜（0.6–0.8s）覆盖缺口\n')
    L.append('| 组 | 加速镜数 | 最大空档 s | 空档区间 s | 判定 |')
    L.append('|---|---|---|---|---|')
    for x in fg_:
        L.append('| %s | %d | %.2f | %.1f–%.1f | %s |' % (x['group'], x['nfast'], x['max_gap'], x['at'][0], x['at'][1],
                                                       '**缺口**' if x['bad'] else 'ok'))
    L.append('')
    L.append('### T3-d P2 切点施工清单（DP 卡拍重定时，只列真要动的刀）\n')
    L.append('| 组 | 切点(左|右) | 帧 | Δ帧 | 左镜 时长 | 右镜 时长 | 压字头 | 区间内字头 | 左锚点 | 右锚点 | 备注 |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|')
    for p in props:
        L.append('| %s | %s | %d→%d | %+d | %.2f→%.2f | %.2f→%.2f | %s | %s | %d | %d | %s |' % (
            p['group'], p['cut_id'], p['old_f'], p['new_f'], p['dF'],
            p['left_dur'][0], p['left_dur'][1], p['right_dur'][0], p['right_dur'][1],
            '是' if p['on_head'] else '',
            '、'.join('%s@%.2f' % (ch, t) for t, ch in p['lyric'][:6]) or '—',
            p['left_rel'], p['right_rel'],
            '**标杆只读**' if p['readonly'] else ''))
    L.append('')
    L.append('### T3-e 逐镜评定（202 行，压缩：只列非「不改」）\n')
    L.append('| 组 | 镜号 | 时长s | 评定 | 说明 |')
    L.append('|---|---|---|---|---|')
    for r in rows:
        tg, why = tags.get((r['group'], r['id']), ('', ''))
        if tg in ('', '不改'):
            continue
        L.append('| %s | %s | %.2f | %s | %s |' % (r['group'], r['id'], r['dur'], tg, why))
    return '\n'.join(L)


def md_t2(rows, st, nc, where, agg, runs, homo, wr, fav):
    L = []
    L.append('### T2-a 入转场族分布（按段）\n')
    fams = ['hard', 'flash', 'motion', 'graphic', 'occl', 'tear', 'ink', 'gold', 'fade']
    L.append('| 族 | ' + ' | '.join(k for k, *_ in GROUPS) + ' | 合计 |')
    L.append('|---|' + '---|' * (len(GROUPS) + 1))
    for f in fams:
        row = [str(agg[f]['groups'].get(k, 0)) for k, *_ in GROUPS]
        L.append('| %s | %s | %d |' % (FAMILY_CN[f], ' | '.join(row), agg[f]['n']))
    L.append('| **镜数** | ' + ' | '.join(str(v['n']) for v in st.values()) + ' | %d |' % len(rows))
    L.append('| **入转场种数** | ' + ' | '.join(str(v['distinct']) for v in st.values()) + ' | — |')
    L.append('| **硬切数** | ' + ' | '.join(str(v['hard']) for v in st.values()) + ' | %d |' % sum(v['hard'] for v in st.values()))
    L.append('| **闪（合计）** | ' + ' | '.join(str(v['flash']) for v in st.values()) + ' | %d |' % sum(v['flash'] for v in st.values()))
    fn = {k: sum(1 for r in rows if r['group'] == k and r['flash'] and r['fam'] == 'flash') for k, *_ in GROUPS}
    fh = {k: sum(1 for r in rows if r['group'] == k and r['flash'] and r['fam'] == 'hard') for k, *_ in GROUPS}
    L.append('| 其中：具名闪转场 | ' + ' | '.join(str(fn[k]) for k, *_ in GROUPS) + ' | %d |' % sum(fn.values()))
    L.append('| 其中：硬切自身提亮闪 | ' + ' | '.join(str(fh[k]) for k, *_ in GROUPS) + ' | %d |' % sum(fh.values()))
    L.append('')
    L.append('### T2-b 跨段重复的「同一招」（全片逐名计数）\n')
    L.append('| 转场名 | 出现次数 | 分布 | 镜号 |')
    L.append('|---|---|---|---|')
    for nm, c in nc.most_common():
        if c < 2:
            continue
        L.append('| `%s` | %d | %s | %s |' % (
            nm, c, ', '.join('%s×%d' % (g, n) for g, n in Counter(x[0] for x in where[nm]).most_common()),
            ' '.join('%s:%s' % (g, i) for g, i, _t in where[nm])))
    L.append('')
    L.append('### T2-c 连用（同段相邻 ≥2 刀同一招）\n')
    L.append('| 类型 | 段 | 镜号 | 连用刀数 |')
    L.append('|---|---|---|---|')
    for kind, lst in runs.items():
        for g, ids in lst:
            L.append('| %s | %s | %s | %d |' % ('硬切' if kind == 'hard' else '闪白/闪色', g, ' '.join(ids), len(ids)))
    L.append('')
    L.append('### T2-d 15 镜滑窗同质化（闪≥4 或 硬切≥5）：每段最差窗口\n')
    L.append('| 组 | 违规窗口数 | 最差窗口 | 时间 s | 闪 | 硬切 | 窗口内入转场序列 |')
    L.append('|---|---|---|---|---|---|---|')
    for k, *_r in GROUPS:
        sub = [x for x in homo if x['group'] == k]
        if not sub:
            L.append('| %s | 0 | — | — | — | — | — |' % k)
            continue
        w = max(sub, key=lambda x: (x['flash'], x['hard']))
        L.append('| %s | %d | %s | %.1f–%.1f | %d | %d | %s |' % (k, len(sub), w['ids'], w['t0'], w['t1'], w['flash'], w['hard'],
                                                              ' '.join(w['names'])))
    L.append('')
    L.append('### T2-e 用户点名三段的「不重样」证据（全部用帧精确重叠口径）\n')
    L.append('| 段 | 时间 | 镜数 | 刀数 | 不同转场数 | 重样 | 不重样率 | 平均镜长 | 序列 |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    for f in fav:
        cuts = len(f['names'])          # 窗口首镜若非段首，也带一刀
        dup = cuts - f['distinct']
        L.append('| %s | %.0f–%.0fs | %d | %d | **%d** | %d | %.0f%% | %.2fs | %s |' % (
            f['name'], f['a'], f['b'], f['n'], cuts, f['distinct'], dup,
            100.0 * (cuts - dup) / max(1, cuts), f['avg'], ' '.join(f['names'])))
    return '\n'.join(L)


def md_t2b(p2b):
    L = ['| 组 | 镜号 | 现时长 | 建议劈点(帧) | 左/右半 s | 镜内相对锚点 | 劈点±0.4s 内的字头 | 入转场 |',
         '|---|---|---|---|---|---|---|---|']
    for x in p2b:
        L.append('| %s | %s | %.2f | %d | %.2f / %.2f | %d | %s | `%s` |' % (
            x['group'], x['id'], x['dur'], x['split_f'], x['L'], x['R'], x['rel'],
            '、'.join('%s@%.2f' % (ch, t) for t, ch in x['lyric'][:5]) or '—', x['entry']))
    return '\n'.join(L)


def md_p01(p0, p1):
    L = ['| 组 | 镜号 | 转场 | pre | post | 本镜时长 | 问题 |',
         '|---|---|---|---|---|---|---|']
    for x in p1:
        L.append('| %s | %s | `%s` | %.2f | %.2f | %.2f | %s |' % (x['group'], x['id'], x['entry'], x['pre'], x['post'],
                                                                x['dur'], x['why']))
    return '\n'.join(L)


def md_p0_alts(p0):
    L = ['| 组 | 镜号 | 时长 | 现用 | 邻域闪/硬 | 可换（同段未用过的无白闪招，自动生成） |',
         '|---|---|---|---|---|---|']
    for x in p0:
        L.append('| %s | %s | %.2f | `%s` | %d/%d | %s |' % (x['group'], x['id'], x['dur'], x['cur'],
                                                            x['win_flash'], x['win_hard'],
                                                            '、'.join('`%s`' % a for a in x['alt'][:6])))
    L.append('')
    L.append('#### P1 · 只调 pre/post（不动切点）\n')
    L.append('| 组 | 镜号 | 转场 | pre | post | 本镜时长 | 问题 |')
    L.append('|---|---|---|---|---|---|---|')
    for x in p1:
        L.append('| %s | %s | `%s` | %.2f | %.2f | %.2f | %s |' % (x['group'], x['id'], x['entry'], x['pre'], x['post'],
                                                                x['dur'], x['why']))
    return '\n'.join(L)


def md_p0(swaps, rows, heads, cb, ca, wb, wa, ver, tnotes):
    """P0 施工清单（只换名字）+ 试算前后对比。"""
    idx = {(r['group'], r['id']): r for r in rows}
    L = ['#### P0 · 只换转场名（切点一帧不动）—— 按风险从低到高\n',
         '> 状态：**已于 2026-11-09 实施**（逐条 diff 与自检见 `edit_plan.md` §7）。下表是施工记录；',
         '> 因为代码里已经是新值，所以下面「试算前后」两列必然相同——那不是没生效，是已经生效。\n',
         '| # | 组 | 镜号 | 时长 | 现用 → 建议 | pre/post | 切点帧 | 转场窗口内的字头 | 理由 |',
         '|---|---|---|---|---|---|---|---|---|']
    for i, (g, sid, old, new, pre, post, kw, note) in enumerate(swaps, 1):
        r = idx[(g, sid)]
        c = r['t0']
        ly = [(t, ch) for t, ch, *_ in heads if c - pre - 0.02 <= t <= c + post + 0.02]
        L.append('| %d | %s | %s | %.2f | `%s` → `%s` | %.2f/%.2f | %d | %s | %s |' % (
            i, g, sid, r['dur'], old, new, pre, post, int(round(c * FPS)),
            '、'.join('%s@%.2f' % (ch, t) for t, ch in ly) or '—', note))
    L.append('')
    if tnotes:
        L.append('**窗口收窄（post 收到「下一个字头」前 0.02s，避免转场纹理压字）：**\n')
        for n in tnotes:
            L.append('- ' + n)
        L.append('')
    L.append('**试算前后（不渲染，只改内存里的表）：**\n')
    L.append('| 组 | 闪（含硬切提亮） | 硬切 | 入转场种数 | 最差 15 镜窗口 |')
    L.append('|---|---|---|---|---|')
    for k, *_r in GROUPS:
        L.append('| %s | %d → **%d** | %d → **%d** | %d → %d | 闪%d@%s → 闪%d@%s |' % (
            k, cb[k]['flash'], ca[k]['flash'], cb[k]['hard'], ca[k]['hard'],
            cb[k]['distinct'], ca[k]['distinct'], wb[k][0], wb[k][2], wa[k][0], wa[k][2]))
    L.append('')
    if ver:
        bad = {k: v for k, v in ver.items() if not v.startswith('ok')}
        L.append('**落地可行性验证**：%d 条候选在 1080p 零图上各跑一次 p=0.5，%d 条返回正确形状；%s\n' % (
            len(ver), len(ver) - len(bad), ('失败 ' + str(bad)) if bad else '无失败'))
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default='/tmp/edit_audit.json')
    ap.add_argument('--md', default=os.path.join(REPO, 'crew/round4/edit_audit_tables.md'))
    ap.add_argument('--keep-mirror', action='store_true')
    ap.add_argument('--verify', action='store_true', help='在 1080p 零图上真跑候选转场，验证可 dispatch')
    a = ap.parse_args()

    mir = build_mirror()
    try:
        rows, mods = collect(mir)
        heads = load_lyric_heads()
        beats = load_beats()
    finally:
        if not a.keep_mirror:
            shutil.rmtree(mir, ignore_errors=True)

    st = group_stats(rows)
    h = hist(rows)
    wr = window_repeats(rows, 15)
    agg, runs = same_trick(rows)
    nc, where = name_counts(rows)
    fg_ = fast_gaps(rows)
    props = propose(rows, heads, beats)
    moved = set()
    for _p in props:
        moved.add((_p['group'], _p['left']))
        moved.add((_p['group'], _p['right']))
    tags = compliance(rows, moved)
    fav = fav_stats(rows)
    homo = homogeneity(rows)
    p0 = p0_candidates(rows, mods)
    p1 = p1_candidates(rows)
    p2b = p2b_splits(rows, heads, beats)

    print('镜数 = %d（各段：%s）' % (len(rows), ', '.join('%s %d' % (k, v['n']) for k, v in st.items())))
    print('\n段统计')
    for k, v in st.items():
        print('  %-3s n=%2d 均%.2fs 中位%.2fs 最短%.2fs 最长%.2fs 加速镜%d <0.9s %d >1.4s %d >1.8s %d | 硬切%d 闪%d 抖%d 转场种数%d'
              % (k, v['n'], v['mean'], v['med'], v['mn'], v['mx'], v['fast'], v['short'], v['long'], v['over'],
                 v['hard'], v['flash'], v['shake'], v['distinct']))
    print('\n用户点名三段')
    for f in fav:
        print('  %s  %.0f–%.0fs  %d 镜  均%.2fs  入转场 %d 种 %s' % (f['name'], f['a'], f['b'], f['n'], f['avg'],
                                                             f['distinct'], f['names']))
    print('\n直方图（全片，0.2s 一格）')
    for lo, hi, c in h:
        if c:
            print('  %.1f–%.1f %4d %s' % (lo, hi, c, '#' * c))
    print('\n转场名重复次数（全片，≥2）')
    for nm, c in nc.most_common():
        if c < 2:
            continue
        gs = ', '.join('%s×%d' % (g, n) for g, n in Counter(x[0] for x in where[nm]).most_common())
        print('  %-22s %2d  %s' % (nm, c, gs))
    print('\n族统计')
    for fam, v in sorted(agg.items(), key=lambda kv: -kv[1]['n']):
        print('  %-8s %3d  %s' % (FAMILY_CN.get(fam, fam), v['n'],
                                  ', '.join('%s×%d' % (g, n) for g, n in v['groups'].most_common())))
    print('\n连用（≥2）')
    for k, lst in runs.items():
        for g, ids in lst:
            print('  [%s] %s: %s' % (k, g, ' '.join(ids)))
    print('\n加速镜缺口')
    for x in fg_:
        print('  %-3s 加速镜%d 最大间隔%.2fs @%.1f–%.1f %s' % (x['group'], x['nfast'], x['max_gap'], x['at'][0], x['at'][1],
                                                          '⚠' if x['bad'] else ''))
    print('\nP2 候选（DP 重定时真的要动的刀）%d 条' % len(props))
    for p in props:
        print('  %-3s %-20s %d→%d (%+d 帧) 左 %.2f→%.2f 右 %.2f→%.2f 压字头=%s 字头=%s'
              % (p['group'], p['cut_id'], p['old_f'], p['new_f'], p['dF'],
                 p['left_dur'][0], p['left_dur'][1], p['right_dur'][0], p['right_dur'][1],
                 'Y' if p['on_head'] else 'N', '、'.join(ch for _t, ch in p['lyric'][:5]) or '-'))
    print('\n同质化窗口（15镜内 闪≥4 或 硬切≥5）：%d 个' % len(homo))
    for x in homo:
        print('  %-3s %s  %.1f–%.1fs 闪%d 硬%d' % (x['group'], x['ids'], x['t0'], x['t1'], x['flash'], x['hard']))
    print('\nP0 换名候选 %d 条（示例 15）' % len(p0))
    for x in p0[:15]:
        print('  %-3s %-9s %.2fs 现 %s(%s) 邻域闪%d/硬%d → 可换 %s'
              % (x['group'], x['id'], x['dur'], x['cur'], x['flash'], x['win_flash'], x['win_hard'], '/'.join(x['alt'][:3])))
    print('\nP1 pre/post 候选 %d 条' % len(p1))
    for x in p1:
        print('  %-3s %-9s %s pre%.2f post%.2f (%.2fs) %s' % (x['group'], x['id'], x['entry'], x['pre'], x['post'], x['dur'], x['why']))
    print('\nP2b 新增切点候选 %d 条' % len(p2b))
    for x in p2b:
        print('  %-3s %-9s %.2fs → 劈在 %d 帧，%.2f+%.2fs，锚点 %d，近字头 %s'
              % (x['group'], x['id'], x['dur'], x['split_f'], x['L'], x['R'], x['rel'],
                 '、'.join(ch for _t, ch in x['lyric'][:4]) or '-'))
    swaps, tnotes = tighten_swaps(rows, heads, SWAPS)
    if tnotes:
        print('\nP0 窗口收窄（避免压字头）：')
        for n_ in tnotes:
            print('  · ' + n_)
    cb, ca, wb, wa = simulate_swaps(rows, swaps)
    print('\nP0 策展清单 %d 条 · 试算前后' % len(swaps))
    for k, *_r in GROUPS:
        print('  %-3s 闪 %2d→%2d  硬切 %2d→%2d  种数 %2d→%2d  最差15镜窗口 闪%d@%s → 闪%d@%s'
              % (k, cb[k]['flash'], ca[k]['flash'], cb[k]['hard'], ca[k]['hard'],
                 cb[k]['distinct'], ca[k]['distinct'], wb[k][0], wb[k][2], wa[k][0], wa[k][2]))
    ver = {}
    if a.verify:
        pairs = sorted({(g, new, tuple(kw.items())) for g, _s, _o, new, _a, _b, kw, _n in swaps})
        ver = verify_names(mods, pairs)
        print('\n候选转场名验证 %d 条：%s' % (len(ver), Counter(ver.values()).most_common()))
        for k_, v_ in sorted(ver.items()):
            if v_ != 'ok':
                print('  ✗ %s → %s' % (k_, v_))
    print('\n评定汇总: %s' % Counter(v[0] for v in tags.values()).most_common())
    print('\n段长/最小镜数/需新增刀数')
    for k, v in st.items():
        print('  %-3s 段长%.1fs 现%d镜 均值%.2fs → 规范下界需≥%d镜 缺口%d刀 超额时长%.2fs'
              % (k, v['span'], v['n'], v['mean'], v['min_shots'], v['need_cuts'], v['over_time']))

    data = dict(rows=rows, stats=st, hist=h, tags={'%s|%s' % k: v for k, v in tags.items()}, fav=fav,
                windows=wr, families={k: dict(n=v['n'], groups=dict(v['groups'])) for k, v in agg.items()},
                runs=runs, names={k: dict(n=v, where=where[k]) for k, v in nc.items()},
                fast_gaps=fg_, props=props, homo=homo, p0=p0, p1=p1, p2b=p2b, verify=ver,
                swaps=[dict(group=g_, id=s_, old=o_, new=n_, pre=pr_, post=po_, kw=kw_, note=no_)
                       for g_, s_, o_, n_, pr_, po_, kw_, no_ in swaps], tnotes=tnotes)
    json.dump(data, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    os.makedirs(os.path.dirname(a.md), exist_ok=True)
    open(a.md, 'w', encoding='utf-8').write(
        '## T1 · 202 镜摊平表\n\n' + md_t1(rows, tags)
        + '\n\n## T2 · 重复手法\n\n' + md_t2(rows, st, nc, where, agg, runs, homo, wr, fav)
        + '\n\n## T3 · 镜长规范\n\n' + md_t3(rows, st, h, props, fg_, tags)
        + '\n\n### T3-f P2b 新增切点候选（最高风险，需加镜/镜内二次构图）\n\n' + md_t2b(p2b)
        + '\n\n## T4 · 施工清单\n\n'
        + md_p0(swaps, rows, heads, cb, ca, wb, wa, ver, tnotes)
        + '\n\n### P1 · 只调 pre/post（不动切点）\n\n' + md_p01(p0, p1) + '\n')
    print('\nJSON → %s\n表格 → %s' % (a.json, a.md))


if __name__ == '__main__':
    try:
        import numpy  # noqa: F401
        import cv2    # noqa: F401
    except ImportError:
        if os.path.exists(VENV_PY):
            os.execv(VENV_PY, [VENV_PY, os.path.abspath(__file__)] + sys.argv[1:])
        raise
    main()
