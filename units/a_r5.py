"""units/a_r5.py — A 组第五轮（用户 12 条意见）开关 + 小工具。
所有改动挂在 ON 开关下：环境变量 A_R5_OFF=all 全部回退；A_R5_OFF=walkout,zoom 关指定项。"""
import os

ON = dict(
    credits_off=True,     # 1  开头署名全部去掉（片尾已有）
    walkout=True,         # 2  A08 主角走出城门，城门在身后合上
    slash_keys=True,      # 3  V06 关键帧插帧挥刀（蓄势 → 横斩 → 送出）
    zoom=True,            # 4  V07→V08 撕纸转场 → 推镜穿越
    garble=True,          # 5  罪状右侧文书 → 乱码
    paper_bowl=True,      # 6  V10 秤盘里保留纸人（不换成主角）
    sha_fang=True,        # 7  殺/放 繁体同位 + 同构图 + 字形变换
    draw_cu=True,         # 8  V14 拔刀特写换图
    carve=True,           # 9  V15 全刀入画 + 真刻字
    jade=True,            # 10 V16/V17 玉玺重生成（立体）
    rise=True,            # 11 V20 起势/上挑换图
    fengmang=True,        # 12 V21 锋芒书法字
)
_off = os.environ.get('A_R5_OFF', '')
if _off.strip() == 'all':
    for _k in ON: ON[_k] = False
else:
    for _k in _off.split(','):
        if _k.strip() in ON: ON[_k.strip()] = False


# ------------------------------------------------------------------ 5 乱码文书（天书式拼合假字）
_POOL = '奉旨查办逆犯目无王法擅杀官兵罪证确凿着即拿问律令刑狱囚斩首判词审讯案牍押解赦免诏敕谋叛诛戮讼罚赎黥劓'


def fake_glyph(T, rs, size, fname='kai'):
    """两个真字各取一半拼成一个读不出的假字（左右或上下拼合，偶尔镜像一半），笔画质感与原小楷一致。"""
    import numpy as np
    a = T.glyph(_POOL[rs.randint(len(_POOL))], fname, size)
    b = T.glyph(_POOL[rs.randint(len(_POOL))], fname, size)
    n = a.shape[0]; s = int(n * rs.uniform(0.42, 0.58))
    g = np.zeros_like(a)
    if rs.rand() < 0.6:
        g[:, :s] = a[:, :s]; g[:, s:] = b[:, s:]
    else:
        g[:s] = a[:s]; g[s:] = b[s:]
    if rs.rand() < 0.25: g = g[:, ::-1].copy()
    return g


def garble_doc(T, cols=3, rows=8, x0=1560, dx=92, y0=200, dy=84, size=66, seed=5, color=(0.06, 0.05, 0.05), alpha=0.62, blur=0.9):
    """第五轮 5：右侧诏文 → 乱码（同位置、同字号、同墨色的三列假字）。"""
    import numpy as np, cv2
    rs = np.random.RandomState(seed)
    L = T.Layer()
    for ci in range(cols):
        for ri in range(rows):
            g = fake_glyph(T, rs, size)
            p = int(blur * 3); g = cv2.GaussianBlur(np.pad(g, p), (0, 0), blur)
            L.paste(g, x0 - ci * dx + rs.uniform(-2, 2), y0 + ri * dy + rs.uniform(-3, 3), color, alpha * rs.uniform(0.85, 1.0))
    return L
