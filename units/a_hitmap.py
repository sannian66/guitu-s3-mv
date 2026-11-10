"""units/a_hitmap.py — A 组（前奏 + 主歌一 0–44.05s）卡点图。方法同 units/hitmap.py（HPSS 打击乐 → 频段谱通量 → 峰值分类），
没有 demucs 分离轨，用全曲 HPSS。输出 crew/round4/A_hitmap.json：hits（kick/snare/hat/crash + strength）、beats（含小节内拍位）、words（行 0–11 字头）。
  python3 units/a_hitmap.py"""
import json, sys
import numpy as np
ROOT = __import__('os').environ.get('MV_ROOT', '/workspace/work/mv')
sys.path[:0] = [ROOT + '/lib', ROOT]
A0, A1, W0, W1, FPS = 0.0, 46.0, 0.0, 44.1, 30


def main():
    import librosa
    y, sr = librosa.load(ROOT + '/audio/谁定正邪.mp3', sr=44100, mono=True, offset=A0, duration=A1 - A0)
    D = librosa.stft(y, n_fft=2048, hop_length=256)
    S = np.abs(librosa.decompose.hpss(D, margin=(1.0, 2.0))[1])
    f = librosa.fft_frequencies(sr=sr, n_fft=2048); hop = 256 / sr
    tt = A0 + np.arange(S.shape[1]) * hop

    def flux(lo, hi):
        m = (f >= lo) & (f < hi); X = np.log1p(S[m] * 20)
        fl = np.maximum(0, np.diff(X, axis=1, prepend=X[:, :1])).sum(0)
        return fl / (np.percentile(fl, 99.7) + 1e-9)
    kick, snare, hat = flux(30, 150), flux(150, 4000) * 0.4 + flux(1200, 4000) * 0.6, flux(6000, 16000)
    m = (f >= 5000); ehi = np.log1p((S[m] ** 2).sum(0)); ehi /= np.percentile(ehi, 99.5) + 1e-9
    full = librosa.onset.onset_strength(y=y, sr=sr, hop_length=256)[:len(tt)]; full /= np.percentile(full, 99.5) + 1e-9
    on = librosa.util.peak_pick(full, pre_max=3, post_max=3, pre_avg=10, post_avg=5, delta=0.05, wait=int(0.055 / hop))
    an = np.load(ROOT + '/analysis.npz'); beats = an['beats']
    hits = []
    for i in on:
        t = float(tt[i])
        if not (W0 <= t <= W1): continue
        w = slice(max(0, i - 2), i + 3); kn, sn, hn = kick[w].max(), snare[w].max(), hat[w].max()
        typ = []
        if kn > 0.33: typ.append('kick')
        if (sn >= 0.30 and hn >= 0.45) or sn > 0.5: typ.append('snare')
        if hn > 0.30 and 'snare' not in typ: typ.append('hat')
        if not typ: continue
        if ehi[min(len(ehi) - 1, i + int(0.3 / hop))] > 0.80 and hn > 0.55: typ.append('crash')
        hits.append(dict(t=round(t, 3), type='+'.join(typ), raw=float(max(kn * 1.2 if 'kick' in typ else 0, sn if 'snare' in typ else 0, hn * 0.7))))
    v = np.array([h['raw'] for h in hits]); lo, hi = np.percentile(v, 5), np.percentile(v, 98)
    for h in hits:
        h['strength'] = round(float(np.clip((h['raw'] - lo) / (hi - lo + 1e-9), 0, 1)) * 0.85 + 0.15, 3)
        bi = int(np.argmin(np.abs(beats - h['t']))); h['on_beat'] = bool(abs(h['t'] - beats[bi]) < 0.06)
        h['frame'] = int(round(h['t'] * FPS)); h['beat'] = bi; del h['raw']
    # 小节相位：4 拍相位上累加底鼓
    bsel = [b for b in beats if W0 - 1 <= b <= W1 + 1]; b0 = int(np.searchsorted(beats, W0 - 1)); sc = np.zeros(4)
    for k, b in enumerate(bsel):
        i = np.searchsorted(tt, b); sc[(b0 + k) % 4] += kick[max(0, i - 3):i + 4].max()
    ph = int(np.argmax(sc))
    for h in hits: h['beat_pos'] = int((h['beat'] - ph) % 4) + 1
    bl = [dict(i=int(i), t=round(float(beats[i]), 3), frame=int(round(beats[i] * FPS)), pos=int((i - ph) % 4) + 1)
          for i in range(len(beats)) if W0 - 0.5 <= beats[i] <= W1 + 0.5]
    import typo as T
    L = T.load_lines(); words = []
    for li in range(0, 12):
        for k, (c, t) in enumerate(zip([c for c in L[li]['text'] if c.strip()], [x for x in L[li]['times'] if x is not None])):
            bi = int(np.argmin(np.abs(beats - t)))
            words.append(dict(line=li, k=k, ch=c, t=round(float(t), 3), frame=int(round(t * FPS)),
                              accent=bool(c in '刀甲寒光罪状命量杀放拔正义权锋芒' or abs(t - beats[bi]) < 0.07)))
    out = dict(window=[W0, W1], method='HPSS percussive (full mix) → band flux; whisper word times', downbeat_phase=ph,
               bpm=round(60 / float(np.median(np.diff(beats))), 2), hits=hits, beats=bl, words=words)
    json.dump(out, open(ROOT + '/crew/round4/A_hitmap.json', 'w'), ensure_ascii=False, indent=1)
    cnt = {}
    for h in hits:
        for ty in h['type'].split('+'): cnt[ty] = cnt.get(ty, 0) + 1
    print(len(hits), cnt, 'phase', ph)


if __name__ == '__main__':
    main()
