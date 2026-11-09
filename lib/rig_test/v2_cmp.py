"""角色组 v2 前后对比：python v2_cmp.py <scene> [scene...]
scene: sw | act | cu | hand | emp | army | paper
before = rig_test/*_v1_baseline.py（v1 冻结）；after = lib/ 当前版本。输出 lib/rig_test/v2_cmp_<scene>.png（上 before / 下 after）"""
import sys, time, os, importlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import numpy as np, cv2
import rig as RN, rig_v1_baseline as RO

def bg(h=1080, w=1920, a=0.30, b=0.10):
    return (np.linspace(a, b, h)[:, None, None] * np.ones((1, w, 3))).astype(np.float32)

def warm(sw, act, ph, n=40, wind=300, **kw):
    for k in range(n): sw.pose(act, ph, k / 30, wind=wind, **kw)

def sc_sw(R):
    fr = bg(); T = []
    for seed, view, wind, x, act, ph in [(1, 'side', 300, 330, 'stand_wind', 0.3), (1, '3q', -300, 780, 'slash_diag', 0.30),
                                         (1, 'front3q', 250, 1180, 'stand_wind', 0.1), (1, 'back', 300, 1600, 'sword_on_shoulder', 0.2)]:
        sw = R.Swordsman(seed, view=view); warm(sw, act, ph, wind=wind)
        a = time.time(); fr, _ = sw.draw(fr, x, 1010, 820, rim_color=(0.9, 0.92, 1), rim_dir=(-0.8, -0.6)); T.append(time.time() - a)
    return fr, T

def sc_act(R):
    """slash_diag 四段：预备/出刀/随势/收势"""
    fr = bg(a=0.16, b=0.05); T = []
    for i, ph in enumerate((0.30, 0.44, 0.60, 0.90)):
        sw = R.Swordsman(3, view='side')
        hist = []
        for f in range(45):
            p = ph * f / 44; sw.pose('slash_diag', p, f / 60, wind=-150)
            if f >= 38:
                _, info = sw.draw(np.zeros((1080, 1920, 3), np.float32), 260 + i * 470, 1000, 700, rim=0)
                hist.append((info['guard'], info['tip']))
        a = time.time(); fr, info = sw.draw(fr, 260 + i * 470, 1000, 700, rim_color=(0.85, 0.9, 1), rim_dir=(-0.7, -0.6)); T.append(time.time() - a)
        if 0.38 < ph < 0.7: fr = R.blade_trail(fr, hist[-6:], edge_color=(1.0, 0.25, 0.15))
    return fr, T

def sc_cu(R):
    fr = bg(a=0.12, b=0.04); T = []
    for (cx, ph, fl) in ((560, 0.0, False), (1400, 0.75, False)):
        sw = R.Swordsman(43, view='side', hair=1.0)
        for k in range(30): R.profile_cu(np.zeros_like(fr), sw, k / 30, cx, 560, 400, action='turn_head', phase=ph * k / 29)
        a = time.time(); fr, _ = R.profile_cu(fr, sw, 1.0, cx, 560, 400, light='moon', glint=2.5, action='turn_head', phase=ph); T.append(time.time() - a)
    return fr, T

def sc_hand(R):
    T = []
    h = R.HandCU(29); fr = bg(a=0.12, b=0.04)
    a = time.time(); r = h.draw(fr[:, :1920].copy(), 'grip', 0.9, 1.0, 900, 560, 400, angle=-8, rim_color=(0.9, 0.93, 1.0), rim_dir=(-0.2, -1.0), lift=0.35); T.append(time.time() - a)
    f1 = r[0] if isinstance(r, tuple) else r
    h = R.HandCU(44); fr = bg(a=0.06, b=0.02)
    a = time.time(); r = h.draw(fr, 'thumb_push', 0.6, 1.0, 960, 560, 560, rim_color=(0.85, 0.9, 1.0), rim_dir=(-0.3, -1)); T.append(time.time() - a)
    f2 = r[0] if isinstance(r, tuple) else r
    return np.hstack([f1[:, 380:1340], f2[:, 480:1440]]), T

def sc_emp(R):
    fr = bg() * 0.4; T = []
    for x, view, act in ((560, 'front', 'raise_hand_decree'), (1400, 'side', 'grip_scepter')):
        em = R.Emperor(1, view=view)
        for f in range(20): em.pose(act, f / 19, f / 30, wind=120)
        a = time.time(); fr, _ = em.draw(fr, x, 1040, 920, rim_color=(1, 0.8, 0.5), rim_dir=(0, -1)); T.append(time.time() - a)
    return fr, T

def sc_army(C):
    fr = bg(a=0.10, b=0.05); T = []
    ar = C.Army(seed=0, rows=4, cols=7)
    a = time.time(); fr, _ = ar.draw(fr, 1.5, cam=dict(x=1.5, y=1.4, z=4, pitch=-4, f=1400), kneel=1.0, march=0); T.append(time.time() - a)
    return fr, T

def sc_paper(P):
    fr = bg(a=0.10, b=0.04); T = []
    pf = P.PaperFigure(3, view='front'); a = time.time(); fr, _ = pf.draw(fr, 520, 1000, 820, 1.0, light='back', light_color=(1, 0.8, 0.5)); T.append(time.time() - a)
    pf = P.PaperFigure(4, view='side'); a = time.time(); fr, _ = pf.draw(fr, 1350, 1000, 820, 1.0, bow=0.4, light='front'); T.append(time.time() - a)
    return fr, T

to8 = lambda f: np.clip(f * 255, 0, 255).astype(np.uint8)
def lab(img, s):
    cv2.putText(img, s, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3); return img

if __name__ == '__main__':
    for name in sys.argv[1:]:
        if name == 'army':
            import crowd as CN, crowd_v1_baseline as CO; mods = (CO, CN); fn = sc_army
        elif name == 'paper':
            import paper as PN, paper_v1_baseline as PO; mods = (PO, PN); fn = sc_paper
        else:
            mods = (RO, RN); fn = globals()['sc_' + name]
        outs = []
        for tag, M in zip(('v1 before', 'v2 after'), mods):
            fn(M); a, T = fn(M)       # 第二次计时（缓存热）
            outs.append(lab(to8(cv2.resize(a, (1920, int(1920 * a.shape[0] / a.shape[1])))), '%s  %s' % (tag, ' '.join('%.2fs' % x for x in T))))
            print(name, tag, ['%.3f' % x for x in T], flush=True)
        img = np.vstack(outs)
        cv2.imwrite(os.path.join(HERE, 'v2_cmp_%s.png' % name), cv2.resize(img, (img.shape[1] // 2 * 2 // 2 * 1, img.shape[0] // 2 * 1))[:, :, ::-1] if False else img[:, :, ::-1])
