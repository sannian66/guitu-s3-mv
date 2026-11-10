"""units/c_hitmap.py — C 组（预副歌二+副歌二 117–162s）卡点图，由 units/hitmap.py 复制改窗口；原注释：副歌一 58–90s 鼓件分离级卡点图
python3 units/hitmap.py  → crew/hitmap_c1.json + crew/hitmap_c1.png

方法：HPSS 取打击乐分量 → STFT 频段拆分（底鼓 <150Hz、军鼓 150–4kHz 瞬态（以 1.2–4k 为主判据）、镲/hi-hat >6kHz）
→ 各频段谱通量 onset 包络 → 自适应峰值检测 → 同一时刻多频段合并分类 → 强度归一化
→ 结合 analysis.npz beats（拍网格、小节号、强拍）和 align.json 逐字时间（字头）。
所有时间同时给出最近帧号（30fps）与「视觉帧」= 最近帧 - 1（感知同步：画面早 1 帧）。"""
import json, sys, math
import numpy as np
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
sys.path.insert(0, ROOT + '/lib'); sys.path.insert(0, ROOT)
FPS = 30
A0, A1 = 115.0, 163.0      # 分析窗（含前后余量）
W0, W1 = 117.0, 162.0      # 输出窗


def frame_of(t): return int(round(t * FPS))


def main():
    import librosa, os
    drums = ROOT + '/out/c_drums_none.wav'          # units/c1_sep.py（htdemucs）分离出的鼓轨，56–92s
    if os.path.exists(drums):
        y, sr = librosa.load(drums, sr=44100, mono=True); base = 56.0
        y = y[int((A0 - base) * sr):int((A1 - base) * sr)]
        S = np.abs(librosa.stft(y, n_fft=2048, hop_length=256)); src = 'htdemucs drums stem'
    else:
        y, sr = librosa.load(ROOT + '/song.mp3', sr=44100, mono=True, offset=A0, duration=A1 - A0)
        D = librosa.stft(y, n_fft=2048, hop_length=256)
        S = np.abs(librosa.decompose.hpss(D, margin=(1.0, 2.0))[1]); src = 'HPSS percussive'
    f = librosa.fft_frequencies(sr=sr, n_fft=2048)
    hop_t = 256 / sr
    tt = A0 + np.arange(S.shape[1]) * hop_t

    def band_flux(lo, hi):
        m = (f >= lo) & (f < hi)
        X = np.log1p(S[m] * 20)
        fl = np.maximum(0, np.diff(X, axis=1, prepend=X[:, :1])).sum(0)
        return fl / (np.percentile(fl, 99.7) + 1e-9)

    def band_energy(lo, hi):
        m = (f >= lo) & (f < hi)
        e = np.log1p((S[m] ** 2).sum(0))
        return e / (np.percentile(e, 99.5) + 1e-9)

    kick = band_flux(30, 150)
    snare = band_flux(150, 4000) * 0.4 + band_flux(1200, 4000) * 0.6
    hat = band_flux(6000, 16000)
    e_kick = band_energy(30, 150); e_hi = band_energy(5000, 16000)
    full = librosa.onset.onset_strength(y=y, sr=sr, hop_length=256)[:len(tt)]
    full = full / (np.percentile(full, 99.5) + 1e-9)
    on = librosa.util.peak_pick(full, pre_max=3, post_max=3, pre_avg=10, post_avg=5, delta=0.05, wait=int(0.055 / hop_t))
    hits = []
    for i in on:
        t = float(tt[i])
        if not (W0 <= t <= W1): continue
        w = slice(max(0, i - 2), i + 3)
        kn, sn, hn = kick[w].max(), snare[w].max(), hat[w].max()
        typ = []
        if kn > 0.33: typ.append('kick')
        # 鼓轨里军鼓 = 中频体 + 宽带响弦（高频也很强）；纯 hi-hat 中频很弱
        if (sn >= 0.30 and hn >= 0.45) or sn > 0.5: typ.append('snare')
        if hn > 0.30 and 'snare' not in typ: typ.append('hat')
        if not typ: continue
        # 吊镲/重音镲：高频能量在 300ms 后仍高
        crash = e_hi[min(len(e_hi) - 1, i + int(0.3 / hop_t))] > 0.80 and hn > 0.55
        if crash: typ.append('crash')
        j = i
        while j > 0 and full[j - 1] > full[i] * 0.5 and i - j < 5: j -= 1
        hits.append(dict(t=round(float(tt[j]), 3), type='+'.join(typ),
                         band=dict(kick=round(float(kn), 3), snare=round(float(sn), 3), hat=round(float(hn), 3)),
                         raw=float(max(kn * 1.2 if 'kick' in typ else 0, sn if 'snare' in typ else 0, hn * 0.7))))
    v = np.array([h['raw'] for h in hits]); lo, hi = np.percentile(v, 5), np.percentile(v, 98)
    for h in hits:
        h['strength'] = round(float(np.clip((h['raw'] - lo) / (hi - lo + 1e-9), 0, 1)) * 0.85 + 0.15, 3)
    pk = {'kick': 1, 'snare': 1, 'hat': 1}
    an = np.load(ROOT + '/analysis.npz')
    beats = an['beats']
    bw = float(np.median(np.diff(beats)))

    # 拍网格信息
    bsel = beats[(beats >= W0 - 1) & (beats <= W1 + 1)]
    # 强拍相位：在每 4 拍相位上累加底鼓强度，取最大者为小节第 1 拍
    bidx = np.searchsorted(beats, W0 - 1)
    score = np.zeros(4)
    for k, b in enumerate(bsel):
        i = np.searchsorted(tt, b)
        score[(bidx + k) % 4] += kick[max(0, i - 3):i + 4].max() + e_kick[max(0, i - 3):i + 4].max()
    ph = int(np.argmax(score))
    for h in hits:
        bi = int(np.argmin(np.abs(beats - h['t'])))
        off = h['t'] - beats[bi]
        h['beat'] = int(bi)
        h['beat_pos'] = int((bi - ph) % 4) + 1           # 小节内第几拍
        h['on_beat'] = bool(abs(off) < 0.06)
        sub = (h['t'] - beats[bi]) / bw
        h['sub'] = float(round(sub * 4) / 4)                  # 16 分位置（-0.5..0.5）
        h['frame'] = frame_of(h['t'])
        h['vis_frame'] = h['frame'] - 1                # 画面早一帧
        del h['raw']
    # 歌词字头：whisper 逐字时间 → 在人声轨（htdemucs vocals）onset 峰上精修（窗口 -0.15/+0.10s）
    vox_env = None
    vp = ROOT + '/out/c_vocals_none.wav'
    if os.path.exists(vp):
        yv, _ = librosa.load(vp, sr=44100, mono=True)
        yv = yv[int((A0 - 56.0) * sr):int((A1 - 56.0) * sr)]
        Sv = np.abs(librosa.stft(yv, n_fft=2048, hop_length=256))
        m = (f >= 150) & (f < 5000)
        Xv = np.log1p(Sv[m] * 20)
        vox_env = np.maximum(0, np.diff(Xv, axis=1, prepend=Xv[:, :1])).sum(0)
        vox_env = np.convolve(vox_env, np.hanning(5) / np.hanning(5).sum(), 'same')
        vox_env /= np.percentile(vox_env, 99.5) + 1e-9
        vox_env = vox_env[:len(tt)]
        vpk = librosa.util.peak_pick(vox_env, pre_max=4, post_max=4, pre_avg=10, post_avg=4, delta=0.04, wait=int(0.08 / hop_t))
        vpk_t = tt[vpk]; vpk_v = vox_env[vpk]

    def refine(t):
        if vox_env is None: return t, 'whisper'
        c = (vpk_t >= t - 0.15) & (vpk_t <= t + 0.10) & (vpk_v > 0.18)
        if not c.any(): return t, 'whisper'
        # 最近且足够强的峰（距离惩罚）
        sc = vpk_v[c] - np.abs(vpk_t[c] - t) * 2.0
        return float(vpk_t[c][np.argmax(sc)]), 'vocal_onset'
    import typo as T
    L = T.load_lines()
    words = []
    for li in range(28, 40):
        txt = [c for c in L[li]['text'] if c.strip()]
        ts = [x for x in L[li]['times'] if x is not None]
        for k, (c, tw) in enumerate(zip(txt, ts)):
            t, src_ = refine(tw)
            # 重音字：落在拍上（±70ms）或句首/句尾，或是关键字
            bi = int(np.argmin(np.abs(beats - t)))
            onb = abs(t - beats[bi]) < 0.07
            key = c in '规剧暗箱不命刀烫血谁正邪墙劈亮骨扛天判量答'
            words.append(dict(line=li, k=k, ch=c, t=round(float(t), 3), t_whisper=round(float(tw), 3), src=src_, frame=frame_of(t), vis_frame=frame_of(t) - 1,
                              on_beat=bool(onb), accent=bool(key or onb), beat_pos=int((bi - ph) % 4) + 1))
    # 单调性：精修后撞车的字（两字吸到同一 onset）回退 whisper，仍撞则顺延 80ms
    for a_, b_ in zip(words, words[1:]):
        if b_['t'] <= a_['t'] + 0.06:
            b_['t'] = round(b_['t_whisper'] if b_['t_whisper'] > a_['t'] + 0.06 else a_['t'] + 0.08, 3); b_['src'] = 'whisper_fallback'
            b_['frame'] = frame_of(b_['t']); b_['vis_frame'] = b_['frame'] - 1
    # 乐句（按歌词句）
    phrases = [dict(line=li, text=L[li]['text'], start=round(float([x for x in L[li]['times'] if x][0]), 3),
                    end=round(float(L[li + 1]['times'][0]) if li < 39 else 161.31, 3)) for li in range(28, 40)]
    beat_list = [dict(i=int(i), t=round(float(beats[i]), 3), frame=frame_of(beats[i]), pos=int((i - ph) % 4) + 1)
                 for i in range(len(beats)) if W0 - 0.5 <= beats[i] <= W1 + 0.5]
    cnt = {}
    for h in hits:
        for ty in h['type'].split('+'): cnt[ty] = cnt.get(ty, 0) + 1
    out = dict(window=[W0, W1], fps=FPS, bpm=round(60 / bw, 2), beat_s=round(bw, 4), downbeat_phase=int(ph),
               counts=dict(total=len(hits), **cnt), method=src + ' → 频段谱通量 + 全频 onset 峰值，按频段分类；strength 为 0.15–1 归一',
               hits=hits, beats=beat_list, words=words, phrases=phrases)
    json.dump(out, open(ROOT + '/crew/round4/C_hitmap.json', 'w'), ensure_ascii=False, indent=1)
    print('hits', len(hits), cnt, 'bpm', 60 / bw, 'downbeat phase', ph)
    plot(y, sr, tt, kick, snare, hat, out, vox_env)


def plot(y, sr, tt, kick, snare, hat, out, vox=None):
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    Wd, Hh = 3600, 1200
    rows = 2
    img = Image.new('RGB', (Wd, Hh * rows // 2 * 1), (14, 14, 18))
    d = ImageDraw.Draw(img)
    fnt = ImageFont.truetype(ROOT + '/fonts/NotoSerifSC.otf', 20)
    seg = [(117, 140), (140, 162)]
    rh = Hh // 2
    for r, (a, b) in enumerate(seg):
        y0 = r * rh
        X = lambda t: int(60 + (t - a) / (b - a) * (Wd - 80))
        # 波形
        s0, s1 = int((a - A0) * sr), int((b - A0) * sr)
        w = y[s0:s1]
        n = Wd - 80
        ch = w[:len(w) // n * n].reshape(n, -1)
        mx, mn = ch.max(1), ch.min(1)
        mid = y0 + 170
        for i in range(n):
            d.line([(60 + i, mid - mx[i] * 140), (60 + i, mid - mn[i] * 140)], fill=(90, 95, 110))
        # 包络
        for env, col, base in ((kick, (230, 60, 50), y0 + 420), (snare, (240, 200, 110), y0 + 480), (hat, (120, 180, 255), y0 + 530)) + (((vox, (240, 240, 240), y0 + 585),) if vox is not None else ()):
            m = (tt >= a) & (tt <= b)
            pts = [(X(t), base - min(1.5, v) * 50) for t, v in zip(tt[m], env[m])]
            d.line(pts, fill=col, width=1)
        # 拍网格
        for bt in out['beats']:
            if a <= bt['t'] <= b:
                c = (200, 200, 200) if bt['pos'] == 1 else (70, 70, 80)
                d.line([(X(bt['t']), y0 + 20), (X(bt['t']), y0 + 590)], fill=c, width=2 if bt['pos'] == 1 else 1)
        # 击打
        for h in out['hits']:
            if not (a <= h['t'] <= b): continue
            x = X(h['t']); s = h['strength']
            for ty, col, yy in (('kick', (230, 60, 50), 300), ('snare', (240, 200, 110), 330), ('hat', (120, 180, 255), 355), ('crash', (255, 255, 255), 380)):
                if ty in h['type']:
                    rr = 3 + 8 * s
                    d.ellipse([x - rr, y0 + yy - rr, x + rr, y0 + yy + rr], fill=col)
        # 字头
        for wd in out['words']:
            if a <= wd['t'] <= b:
                x = X(wd['t'])
                d.line([(x, y0 + 30), (x, y0 + 70)], fill=(255, 120, 100) if wd['accent'] else (180, 180, 180), width=2)
                d.text((x - 10, y0 + 2), wd['ch'], font=fnt, fill=(255, 140, 120) if wd['accent'] else (220, 220, 220))
        for k in range(int(a), int(b) + 1):
            d.text((X(k) - 10, y0 + 592 - 22), f'{k}', fill=(150, 150, 150))
        d.text((8, y0 + 290), 'K', fill=(230, 60, 50)); d.text((8, y0 + 320), 'S', fill=(240, 200, 110)); d.text((8, y0 + 345), 'H', fill=(120, 180, 255))
    img.save(ROOT + '/crew/round4/C_hitmap.png')
    print(ROOT + '/crew/round4/C_hitmap.png')


if __name__ == '__main__':
    main()
