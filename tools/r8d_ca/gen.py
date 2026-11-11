"""CA 单元批量生图：jobs/r8_D_CA.json → ~/Downloads/gen_cands/R8_D/CA/<名>/（并发 ≤3，已有成图跳过），
每张结果（含失败）追加到 crew/round8/genlog_CA.md。
用法：python tools/r8d_ca/gen.py [名1 名2 ...]   （不给名字 = 全部）；TRY=2 标记重抽。"""
import json, os, sys, time, subprocess, glob
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT + '/tools')
import nb
J = json.load(open(ROOT + '/jobs/r8_D_CA.json'))
OUT = os.path.expanduser('~/Downloads/gen_cands/R8_D/CA')
LOG = ROOT + '/crew/round8/genlog_CA.md'
TRY = os.environ.get('TRY', '1')
NOTE = os.environ.get('NOTE', '')
names = sys.argv[1:] or list(J)


def one(n):
    d = f'{OUT}/{n}' + ('' if TRY == '1' else f'_try{TRY}')
    if glob.glob(d + '/*.png') or glob.glob(d + '/*.jpg') or glob.glob(d + '/*.webp'):
        return n, 'skip', None, None
    body = dict(J[n])
    try:
        r = nb.generate(body, d)
    except Exception as e:                       # 网络 / 轮询异常也要记账（任务可能已提交扣分）
        r = {'_error': 'exception: %s' % e}
    ok = not r.get('_error') and r.get('files')
    tid = r.get('task_id', '')
    st = '已出图' if ok else ('失败 ' + str(r.get('_error')))
    ref = ('太上皇定妆照参考' if 'taishang' in str(body.get('input')) or '68023565' in str(body.get('input')) else '定妆照参考') if body.get('input') else '纯文生图'
    with open(LOG, 'a') as f:
        f.write(f"| {time.strftime('%m-%d %H:%M')} | R8_D/CA/{n} | RH_image2 | 2K 16:9 | 3 | {tid} | {st} | "
                f"{(r.get('files') or [''])[0].replace(os.path.expanduser('~'), '~')} | {ref} try{TRY}{NOTE} |\n")
    return n, st, tid, r.get('files')


if __name__ == '__main__':
    if not os.path.exists(LOG):
        open(LOG, 'w').write('# 第八轮 CA 单元（C01–C21）生图记录\n\n提示词：jobs/r8_D_CA.json；每张 3 积分（RH_image2 2K）。候选原图在仓库外 '
                             '~/Downloads/gen_cands/R8_D/CA/，入库只放用到的抠像与背景板（assets/gen/R8_D/CA/）。\n\n'
                             '| 时间 | 名 | 模型 | 规格 | 积分 | task_id | 状态 | 原图 | 备注 |\n|---|---|---|---|---|---|---|---|---|\n')
    with ThreadPoolExecutor(3) as ex:
        for n, st, tid, files in ex.map(one, names):
            print(n, st, tid, files, flush=True)
