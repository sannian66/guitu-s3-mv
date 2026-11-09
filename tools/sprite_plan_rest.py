"""副歌一以外段落（S001–S027、S047–S138）人物精灵计划。生成 crew/sprite_plan_rest.md，并供 tools/gen_rest_sprites.py 使用。
每项：镜号, 段落, 景别, 角色, 处理, 姿势列表[(姿势名, 提示词要点)], 备注。处理：精灵 / 代码剪影保留 / 混合 / 复用(镜号:姿势)。
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GT, TSH = '男主_鬼屠', '最终boss_太上皇'
GT_LOOK = ('The character MUST keep exactly the same face and hairstyle as the reference sheet: young man, sharp straight brows, amber eyes, '
           'pale skin, long black messy hair tied in a HIGH PONYTAIL on top of the head (ponytail always visible and complete), loose strands over the forehead. '
           'Outfit: black layered wuxia robe with dark red inner collar, wide dark brown leather waist wrap with a long dark red sash, leather wrist guards, black boots. '
           'Weapon when present: a long single-edged Chinese dao with black cord-wrapped handle.')
TSH_LOOK = ('The character MUST keep exactly the same face and hairstyle as the reference sheet: tall gaunt older man, hollow cheeks, heavy-lidded tired eyes, '
            'long straight black hair with silver-white streaks falling over the chest, small top bun with a long black hairpin. '
            'Outfit: dark charcoal sheer layered hanfu with very wide sleeves and faint embroidered patterns, dark red cord sash.')
BG = ('Studio sprite plate: plain flat neutral mid-grey seamless background (RGB about 128,128,128), NOTHING else in the background, no props, no ground, no rain, '
      'no particles, no smoke, no text, no watermark, no letterbox bars. ')
LIGHT_COLD = 'Lighting: strong cold moonlight rim light from behind outlining hair and shoulders, dim cold bluish key light, deep shadows, cinematic photorealistic film still. '
LIGHT_WARM = 'Lighting: warm golden candlelight from the side, deep shadows on the other side, cinematic photorealistic film still. '
FRAME = {
    'ECU': 'Framing: extreme close-up, subject fills the frame. ',
    'CU': 'Framing: close-up. ',
    'MCU': 'Framing: medium close-up from chest up, the whole head including the top of the ponytail inside the frame with margin. ',
    'MS': 'Framing: medium-wide shot showing the full body from head to feet with generous margin on all sides, nothing cropped, including the top of the hair and the full sword. ',
    'LS': 'Framing: full body, figure about 70% of frame height, centered, generous margin on all sides, nothing cropped, including hair, sleeves, sword and feet. ',
}
HANDS = 'Hands anatomically correct: exactly five fingers on each visible hand, natural knuckles. '

# (镜号, 段落, 时间, 景别, 角色, 处理, [(姿势, 提示词要点)], 备注)
P = [
 # ---------------- intro / verse1 / pre1 ----------------
 ('S001','intro','ELS',None,'代码',[],'墨晕云海'),
 ('S002','intro','LS',GT,'精灵',[('back_wind','seen from behind, standing still facing away, robe hem and ponytail blown sideways by strong wind, red sash streaming')],'山脊背影；LS 做精灵后合成压暗'),
 ('S003','intro','ECU',GT,'精灵',[('thumb_push','macro extreme close-up of ONLY a hand and sword guard, NO face, NO head in frame: his left hand, thumb pushing the sword guard so three inches of bright steel slide out of the black scabbard, blade angled 12 degrees, sleeve edge visible')],'手+刀镡；刃口 sheen 代码加'),
 ('S004','intro','CU',GT,'精灵',[('profile','pure side profile facing right, eyes half closed, calm, hair strands drifting'),('profile_open','pure side profile facing right, eyes snapped open with a sharp intense stare, leaning slightly forward, shoulder dropping as if about to draw')],'7.6s 卡点切 profile→profile_open；眼中寒光代码加；S127 复用（代码改金边光）'),
 ('S005','intro','LS',None,'代码',[],'片名刀光，无人物'),
 ('S006','intro','MS',None,'代码',[],'横刀刀面，无人持'),
 ('S007','intro','ELS',TSH,'复用 S011:backlit 转剪影',[],'云上 0.35 不透明巨影'),
 ('S008','verse1','ECU',None,'代码',[],'刃口+乌云，无人持'),
 ('S009','verse1','ELS',None,'代码',[],'军阵'),
 ('S010','verse1','MS',GT,'精灵',[('walk','walking toward the right in three-quarter view, sword sheathed at the left hip, right hand on the hilt'),('draw','mid-draw: right hand pulling the dao out of the scabbard across the body, blade half out, knees bent'),('slash_h','follow-through of a horizontal sword sweep, blade extended level to the right at shoulder height, body twisted, robe flaring')],'20.8 draw / 21.2 slash_h 卡点'),
 ('S011','verse1','LS',TSH,'混合（精灵→剪影）',[('backlit','low-angle view, standing tall and still, facing camera, arms down inside wide sleeves, long hair and sleeves moving in wind, imposing')],'合成时压成背光剪影+金边；S007/S017 复用'),
 ('S012','verse1','MS',None,'代码',[],'天平'),
 ('S013','verse1','ECU',None,'代码',[],'秤盘'),
 ('S014','verse1','MS',GT,'精灵',[('slash_diag','diagonal downward sword stroke from upper right to lower left, finished pose, low stance, robe swirling'),('sheath','calm upright stance sliding the dao back into the scabbard at his left hip, head turned aside, looking down with contempt')],'两个反派剪影代码；S086/S118 复用 slash_diag'),
 ('S015','verse1','CU',GT,'精灵',[('hand_draw','close-up of his right hand gripping the black cord-wrapped hilt and slowly drawing the dao, the steel blade gleaming, leather wrist guard and sleeve cuff')],'刻字/火星代码加'),
 ('S016','verse1','ELS',GT,'复用 S120:plant 转剪影',[],'极小剪影'),
 ('S017','verse1','LS',TSH,'复用 S011:backlit 剪影',[],'远处剪影，抬手可代码变形或保留'),
 ('S018','verse1','MCU',GT,'精灵',[('turn','head turning over his shoulder, three-quarter view, gaze lowered, hair blown across face'),('look_up','high ponytail clearly visible on top of the head, face tilted upward looking up at something huge above, determined cold stare, chin raised')],'turn→look_up 卡点；眼中寒光代码'),
 ('S019','verse1','ECU',None,'代码',[],'刀尖+巨印，无手'),
 ('S020','pre1','CU',None,'代码',[],'生死簿'),
 ('S021','pre1','MS',TSH,'混合（精灵→剪影）',[('finger','huge hand reaching down from top of frame, index finger pointing downward, long thin aged fingers, wide sleeve cuff at top edge')],'只出手，合成压剪影'),
 ('S022','pre1','LS',None,'代码',[],'墙+匾'),
 ('S023','pre1','MS',GT,'精灵',[('look_up_low','low-angle shot from below, standing, head tilted up looking at the sky, sword hanging in right hand pointing down')],'仰拍'),
 ('S024','pre1','MCU',GT,'精灵',[('fist','raising a clenched right fist in front of his chest, knuckles tight, intense stare at camera'),('pommel_thrust','camera pulled back enough that the whole head and the high ponytail have clear space above them; thrusting the sword pommel backward over his shoulder with force, body twisted, hair flying')],'52.84 卡点'),
 ('S025','pre1','ECU',None,'代码',[],'字阵'),('S026','pre1','MS',None,'代码',[],'刀身'),('S027','pre1','CU',None,'代码',[],'刃口'),
 # ---------------- interlude / verse2 / pre2 ----------------
 ('S047','interlude','ELS',None,'代码',[],'斜插的刀'),('S048','interlude','ECU',TSH,'代码',[],'雨滴倒影巨影，复用 S011 剪影'),
 ('S049','verse2','LS',None,'代码',[],'纸人群像'),
 ('S050','verse2','MS',TSH,'混合（精灵→剪影投影）',[('scepter','standing in three-quarter view holding a tall dark scepter of authority upright in his right hand, sleeves hanging')],'烛光暖金侧光；屏风投影代码'),
 ('S051','verse2','CU',TSH,'精灵',[('grip_scepter','close-up of his aged long-fingered hand tightening its grip on a dark carved scepter shaft, embroidered sleeve edge')],'烛光暖金侧光'),
 ('S052','verse2','MS',None,'代码',[],''),('S053','verse2','ECU',None,'代码',[],''),
 ('S054','verse2','MS',GT,'精灵',[('rise','rising from a crouch on one knee, one hand pushing off the ground, head up')],'纸人→鬼屠匹配剪辑'),
 ('S055','verse2','LS',GT,'精灵',[('walk_look_up','walking forward toward camera-left, head tilted up looking at the sky, sword sheathed at hip')],''),
 ('S056','verse2','CU',GT,'精灵',[('palm_open','close-up of his open right palm facing up, fingers slightly spread, cupped as if catching water'),('palm_fist','close-up of the same right hand clenched into a tight fist, tendons visible')],'107.6 卡点；水/命字代码'),
 ('S057','verse2','MCU',GT,'精灵',[('grab_turn','gripping the sword hilt at his hip while whipping his head and body around, ponytail swinging in an arc')],'水珠代码'),
 ('S058','verse2','LS',GT,'复用 S010:slash_h 负片倒影',[],''),
 ('S059','verse2','MS',GT,'复用 S010:slash_h',[],''),
 ('S060','verse2','ELS',None,'代码',[],''),('S061','pre2','CU',None,'代码',[],''),
 ('S062','pre2','MS',TSH,'混合（精灵→剪影）',[('puppeteer','his hand at top of frame, palm down, long fingers spread like a puppeteer holding strings')],'红线代码'),
 ('S063','pre2','CU',None,'代码',[],''),('S064','pre2','ECU',None,'代码',[],''),
 ('S065','pre2','MCU',GT,'精灵',[('chin_up','side three-quarter profile, slowly raising his chin, eyes defiant, wet hair')],'雨代码'),
 ('S066','pre2','LS',GT,'复用 S079:leap_slash_up',[],''),
 ('S067','pre2','CU',None,'代码',[],''),('S068','pre2','ECU',None,'代码',[],''),
 ('S069','pre2','ELS',GT,'复用 S079:leap_slash_up 转剪影',[],''),
 # ---------------- chorus2 ----------------
 ('S070','chorus2','ECU',None,'代码',[],''),
 ('S071','chorus2','MS',GT,'精灵',[('land_kneel','landing in a low kneel on one knee, sword planted to the side, robe and ponytail still flaring upward from the fall')],''),
 ('S072','chorus2','LS',GT,'精灵',[('rise_draw','rising from the kneel while drawing the dao from the hip, blade half out')],''),
 ('S073','chorus2','MS',GT,'精灵',[('spin1','mid-spin, back partly to camera, sword arm extended horizontally, robe flaring in a circle'),('spin2','completing a spinning sword sweep, facing camera, blade extended far to the left, low stance')],'S109/S130 复用'),
 ('S074','chorus2','CU',TSH,'精灵',[('head_turn','close-up of his head turning sideways in profile, long hair with silver-white streaks lifting')],'电光代码，可压剪影'),
 ('S075','chorus2','MS',GT+'+'+TSH,'复用 S010:draw + S011:backlit',[],'对角分屏'),
 ('S076','chorus2','ELS',None,'代码',[],''),('S077','chorus2','CU',None,'代码',[],''),
 ('S078','chorus2','MS',GT,'精灵',[('run','running fast to the left in side view, sword held low in right hand trailing behind, blade tip down, body leaning forward')],'S085 复用'),
 ('S079','chorus2','LS',GT,'精灵',[('leap_slash_up','leaping in the air, sword sweeping upward from low to high, both hands on hilt, robe streaming')],'S066/S069 复用'),
 ('S080','chorus2','MS',None,'代码',[],''),('S081','chorus2','ELS',GT,'代码',[],'极小剪影'),
 ('S082','chorus2','MS',GT,'精灵',[('walk_front','walking straight toward camera, sword in right hand pointing down, steady')],'S095/S122 复用'),
 ('S083','chorus2','CU',GT,'精灵',[('sash','close-up of his waist: the long dark red sash whipping in strong wind against the black robe, leather waist wrap')],''),
 ('S084','chorus2','MS',GT,'精灵',[('knock_back','staggering backward, one foot sliding, arm raised to brace, robe pressed by wind')],''),
 ('S085','chorus2','LS',GT,'复用 S078:run',[],''),('S086','chorus2','MS',GT,'复用 S014:slash_diag',[],''),
 ('S087','chorus2','LS',GT,'精灵',[('brace_overhead','holding the dao horizontally above his head with both hands, bracing a crushing weight, knees bent deep')],''),
 ('S088','chorus2','ELS',None,'代码',[],''),('S089','chorus2','CU',None,'代码',[],''),
 ('S090','chorus2','MCU',GT,'精灵',[('wind_up','drawing the sword back behind his body for a big strike, shoulders twisted, eyes forward')],'S129 复用'),
 ('S091','chorus2','LS',None,'代码',[],''),('S092','chorus2','MCU',None,'代码',[],''),
 # ---------------- bridge ----------------
 ('S093','bridge','ECU',None,'代码',[],''),('S094','bridge','ELS',GT,'代码',[],'中心小墨点'),
 ('S095','bridge','MS',GT,'复用 S082:walk_front',[],''),('S096','bridge','LS',None,'代码',[],''),('S097','bridge','CU',None,'代码',[],''),
 ('S098','bridge','LS',TSH,'混合（精灵→剪影）',[('point_down','towering figure bending forward and pointing down with his index finger, sleeve hanging')],'白底黑剪影'),
 ('S099','bridge','MCU',GT,'精灵',[('point_up','low angle, arm raised pointing the sword straight up toward the sky, defiant')],''),
 ('S100','bridge','LS','师兄/师姐/殷若/徒弟','代码剪影保留',[],'剪纸剪影，不做精灵（可后续用四位角色参考做剪纸轮廓）'),
 ('S101','bridge','CU',None,'代码',[],''),
 ('S102','bridge','ECU',GT,'精灵',[('eye_open','extreme close-up of one amber eye opening, brow and loose hair strands, side lit')],'火光代码'),
 ('S103','bridge','MS',GT,'精灵',[('slow_draw','slowly drawing the dao from the scabbard at chest height, blade fully across the body')],''),
 ('S104','bridge','LS',None,'代码',[],''),
 ('S105','bridge','MS',GT,'精灵',[('charge_front','charging straight toward camera, sword held low to the side, robe flying behind, intense')],''),
 ('S106','bridge','ELS',None,'代码',[],''),('S107','bridge','LS',GT,'复用 S010:slash_h',[],''),('S108','bridge','CU',None,'代码',[],''),
 ('S109','bridge','MS',GT,'复用 S073:spin1/spin2',[],''),('S110','bridge','LS',GT,'复用 S112:sword_sky',[],''),
 # ---------------- chorus3 ----------------
 ('S111','chorus3','ECU',None,'代码',[],''),
 ('S112','chorus3','LS',GT,'精灵',[('sword_sky','standing tall raising the dao straight up to the sky with right arm fully extended, seen from slightly behind')],'S110 复用'),
 ('S113','chorus3','ELS',None,'代码',[],''),('S114','chorus3','CU',None,'代码',[],''),('S115','chorus3','MS',None,'代码',[],''),
 ('S116','chorus3','LS',TSH,'复用 S011:backlit 纸化',[],''),('S117','chorus3','CU',None,'代码',[],''),
 ('S118','chorus3','MS',GT,'复用 S014:slash_diag',[],''),('S119','chorus3','CU',GT,'代码',[],'剪影'),
 ('S120','chorus3','LS',GT,'精灵',[('plant','driving the dao point-down into the ground with both hands on the hilt, standing over it, head bowed')],'S016 复用'),
 ('S121','chorus3','MCU',GT,'精灵',[('wind_sash','three-quarter back view, ponytail and red sash whipping together in wind, looking into the distance')],'金色光代码改色'),
 ('S122','chorus3','LS',GT,'复用 S082:walk_front',[],''),
 ('S123','chorus3','MCU',GT,'精灵',[('front','facing camera straight on, calm, steady gaze, sword hilt visible over shoulder')],'S124 镜像翻转复用'),
 ('S124','chorus3','MCU',GT,'复用 S123:front 镜像',[],''),
 ('S125','chorus3','CU',GT,'精灵',[('stare','head turned to look directly into camera, piercing gaze, hair strands across face')],''),
 ('S126','chorus3','ELS',None,'代码',[],''),('S127','chorus3','CU',GT,'复用 S004:profile',[],'金边光代码'),
 ('S128','chorus3','LS',GT,'精灵',[('blade_level','holding the dao horizontally in front of his chest with both hands, blade level like a scale beam')],''),
 ('S129','chorus3','MCU',GT,'复用 S090:wind_up',[],''),('S130','chorus3','LS',GT,'复用 S073:spin2',[],''),('S131','chorus3','ELS',GT,'代码',[],'小剪影'),
 # ---------------- outro ----------------
 ('S132','outro','LS',GT,'精灵',[('back_walk','seen from behind walking away, sword sheathed at hip, ponytail and robe drifting')],''),
 ('S133','outro','MS',None,'代码',[],''),('S134','outro','ELS',None,'代码',[],''),
 ('S135','outro','CU',GT,'精灵',[('sheath_hand','close-up of his hand sliding the dao back into the black scabbard, the last inch of steel catching light')],'S137 复用'),
 ('S136','outro','ELS',None,'代码',[],''),('S137','outro','CU',GT,'复用 S135:sheath_hand',[],''),('S138','outro','ELS',None,'代码',[],''),
]

ORDER = ['intro', 'verse1', 'pre1', 'chorus2', 'chorus3', 'outro', 'interlude', 'verse2', 'pre2', 'bridge']
WARM = {'S050', 'S051'}


def prompt(sid, size, char, pose_txt):
    look = TSH_LOOK if char == TSH else GT_LOOK
    light = LIGHT_WARM if sid in WARM else LIGHT_COLD
    return pose_txt[0].upper() + pose_txt[1:] + '. ' + FRAME.get(size, '') + HANDS + look + ' ' + BG + light


def jobs():
    out = []
    for sec in ORDER:
        for sid, s, size, char, how, poses, note in P:
            if s != sec: continue
            for pn, pt in poses:
                out.append(dict(sid=sid, pose=pn, section=s, size=size, char=char, prompt=prompt(sid, size, char, pt)))
    return out


def write_md():
    shots = {x['id']: x for x in json.load(open(os.path.join(ROOT, 'crew/shots.json')))}
    L = ['# 副歌一以外段落 人物精灵计划（S001–S027、S047–S138）', '',
         '生成：`tools/sprite_plan_rest.py`（提示词全文在脚本里；通用后缀=参考图五官发型锁定 + 纯中性灰背景无背景物无雨 + 冷月逆光轮廓/暗冷主光，S050/S051 暖金烛光侧光 + 五指正确）。',
         '处理：精灵 = 生图+抠图；复用 = 用别镜的精灵（翻转/改色/压剪影）；代码 = 无人物或极小剪影，继续代码。生图顺序：主歌一/Pre → 副歌二/高潮/终章 → 其余。', '']
    for sec in ['intro', 'verse1', 'pre1', 'interlude', 'verse2', 'pre2', 'chorus2', 'bridge', 'chorus3', 'outro']:
        L += ['## ' + sec, '', '| 镜号 | 时间 | 景别 | 角色 | 处理 | 姿势数 | 姿势：提示词要点 | 备注 |', '|---|---|---|---|---|---|---|---|']
        for sid, s, size, char, how, poses, note in P:
            if s != sec: continue
            sh = shots[sid]
            L.append('| %s | %.2f–%.2f | %s | %s | %s | %d | %s | %s |' % (
                sid, sh['t0'], sh['t1'], size, (char or '—').replace('男主_', '').replace('最终boss_', ''), how, len(poses),
                '<br>'.join('**%s**：%s' % p for p in poses) or '—', note))
        L.append('')
    open(os.path.join(ROOT, 'crew/sprite_plan_rest.md'), 'w').write('\n'.join(L))


if __name__ == '__main__':
    write_md(); j = jobs(); print(len(j), 'poses;', len(j) * 3, 'pts')
    for x in j: print(x['section'], x['sid'], x['pose'])
