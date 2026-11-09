"""第三轮生图（2026-11-09 06:0x）：补桥段 5 姿势 + 重抽 7 个弱姿势。预算 60 积分（用户 05:59 同意），每姿势最多 3 抽。
复用 tools/gen_rest_sprites.py 的提交/轮询/判定逻辑，状态文件独立：crew/round3_gen_state.json；日志 crew/genlog.md。
  python3 tools/gen_round3.py submit [并发=6] | poll | ok S0xx pose | bad S0xx pose 原因 | status
采用后：assets/gen/<镜号>/<姿势>_raw.png（重抽姿势覆盖旧 raw；旧图仍在 git 历史）。
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gen_rest_sprites as G, sprite_plan_rest as plan

GT, TSH = plan.GT, plan.TSH
# 优先级顺序 = 用户给定顺序（桥段补图 → 重抽 S045 S037 S062 S120 S084 S073 S018）
R3 = [
 ('S098', 'point_down', 'LS', TSH, 'towering figure bending forward from the waist and pointing straight down with his right index finger, long wide sleeve hanging down, looking down with cold contempt'),
 ('S099', 'point_up', 'MCU', GT, 'low angle from below, his right arm raised high pointing the dao straight up toward the sky, blade fully visible, defiant upward stare'),
 ('S102', 'eye_open', 'ECU', GT, 'macro extreme close-up of ONLY one amber eye and its brow, eye wide open with a sharp cold stare, loose black hair strands crossing the brow, side lit, the eye fills the frame, no mouth, no full face'),
 ('S103', 'slow_draw', 'MS', GT, 'standing upright drawing the dao slowly out of the black scabbard at chest height, both arms spread apart, the steel blade fully across his body, calm focused face'),
 ('S105', 'charge_front', 'MS', GT, 'running straight toward the camera in a powerful charge, body leaning forward, the dao held low to his right side, robe hem and ponytail flying behind him, intense stare'),
 ('S045', 'spin', 'LS', GT, 'seen squarely FROM BEHIND, his back fully to the camera, in the middle of a spinning turn: torso rotated, right arm extended straight out to the side holding the dao perfectly horizontal, the blade a clean sharp line, robe hem and ponytail swinging outward in a wide circle, both feet planted, crisp sharp image with no motion blur'),
 ('S037', 'stand', 'LS', GT, 'seen directly from behind (back view), standing still with feet apart, the dao held low in his right hand pointing to the ground, ponytail and robe hem moving in wind; a BRIGHT strong cold rim light outlines the entire silhouette (head, ponytail, shoulders, arms, sword, legs) so the outline reads clearly; overall exposure a bit brighter than usual'),
 ('S062', 'puppeteer', 'CU', TSH, 'ONLY his right hand and the edge of his wide sleeve cuff reaching in from the top edge of the frame, palm facing down, long thin aged fingers spread wide like a puppeteer holding invisible strings; NO face, NO head, NO body in the frame, just the hand and sleeve cuff'),
 ('S120', 'plant', 'LS', GT, 'he has driven the dao point-down DEEP into the ground: half of the blade is buried in a small mound of dark broken earth, only the upper blade and the hilt rise above it, both his hands resting on the pommel, standing over it, head bowed. The only allowed ground is that small mound of earth where the blade enters'),
 ('S084', 'knock_back', 'MS', GT, 'thrown backward by a powerful impact: upper body bent far back, head tilted back, back arched, one foot lifting off the ground, arms flung forward, the dao still in his right hand, robe and hair whipped forward'),
 ('S073', 'spin1', 'MS', GT, 'seen FROM BEHIND with his back to the camera, mid-spin, sword arm extended horizontally to the side, the blade a clean sharp line, robe flaring in a circle, ponytail swinging, crisp sharp image with no motion blur'),
 ('S018', 'turn', 'MCU', GT, 'his body and shoulders face AWAY from the camera, he turns his head sharply back over his right shoulder toward the camera, three-quarter face clearly visible over the shoulder, gaze lowered, ponytail swinging, hair blown across his face'),
]


def jobs():
    return [dict(sid=s, pose=p, section='round3', size=sz, char=c, prompt=plan.prompt(s, sz, c, txt)) for s, p, sz, c, txt in R3]


G.STATE = os.path.join(G.ROOT, 'crew/round3_gen_state.json')
G.BUDGET = 60
G.plan = type('P', (), {'jobs': staticmethod(jobs), 'ROOT': G.ROOT})

if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'submit': G.submit(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    elif c == 'poll': G.poll()
    elif c == 'ok': G.verdict(sys.argv[2], sys.argv[3], True)
    elif c == 'bad': G.verdict(sys.argv[2], sys.argv[3], False, ' '.join(sys.argv[4:]))
    elif c == 'status': G.status()
    elif c == 'prompts':
        for j in jobs(): print(j['sid'], j['pose'], j['prompt'][:200])
