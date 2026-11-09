"""units/sections.py — 第四轮「剧组」分段注册表（2026-11-09 第四任）。
每个摄制组只写自己的 units/sec_<key>.py，接口：
    READY = True/False            # True 才会被整片渲染接入（False 时走旧版 scenes + rest_sprites）
    def frame(f: int, cache: dict) -> np.uint8 (1080,1920,3) RGB   # 已收尾（含黑边、颗粒、暗角）的成品帧
帧区间左闭右开，30fps；区间边界 = shots.json 段落边界，不许改（改了会和相邻组接不上）。
环境变量 V4_OFF=1 全部关闭；V4_ONLY=a,b 只接入指定组；V4_FORCE=a 无视 READY 强制接入（组内自测用）。"""
import os, importlib
SECTIONS = [  # key, 帧起, 帧止, 段落（shots.json）, 组
    ('a_intro_verse1', 0,    1321, 'intro S001–S007 + verse1 S008–S019', 'A 组'),
    ('b_pre1',         1321, 1784, 'pre1 S020–S027', 'B 组'),
    # 1784–2586 = 副歌一 units/chorus1.py（标杆，不动）
    ('b_verse2',       2586, 3534, 'interlude S047–S048 + verse2 S049–S060', 'B 组'),
    ('c_pre2_chorus2', 3534, 4839, 'pre2 S061–S069 + chorus2 S070–S092', 'C 组'),
    ('d_bridge',       4839, 5797, 'bridge S093–S110', 'D 组'),
    ('e_final_outro',  5797, 7241, 'chorus3 S111–S131 + outro S132–S138（含片尾署名）', 'E 组'),
]
_MODS = {}

def _enabled(key):
    if os.environ.get('V4_OFF'): return False
    force = [x for x in os.environ.get('V4_FORCE', '').split(',') if x]
    only = [x for x in os.environ.get('V4_ONLY', '').split(',') if x]
    if only and key not in only and key not in force: return False
    if key not in _MODS:
        try: _MODS[key] = importlib.import_module('sec_' + key)
        except ModuleNotFoundError as e:
            if e.name != 'sec_' + key: raise
            _MODS[key] = None
    m = _MODS[key]
    return m is not None and (getattr(m, 'READY', False) or key in force)

def lookup(f):
    """返回接管该帧的段落模块，或 None（走旧版）。"""
    for key, f0, f1, *_ in SECTIONS:
        if f0 <= f < f1:
            return _MODS[key] if _enabled(key) else None
    return None
