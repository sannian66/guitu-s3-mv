"""男主「鬼屠」设定图测量值（assets/characters/男主_鬼屠.webp, 2000x1116）。
只做测量/取色/描轮廓参考：渲染时不读任何图片，这里全是手工核对过的数字。
测量方法：PIL 读图 → cv2 灰度阈值(<70=发, <235=前景) + 轮廓 approxPolyDP(2.5px) + 网格人工读点（2026-11-09）。

坐标约定
- REF_* 为设定图原图像素 (x, y)。
- HU_* 为换算到 rig 头部系的“头单位”：x 右（角色右为 +，正面看图像左侧）、y 上，下巴 y=-6.45，头顶(头盖) ≈ +6.45（13 单位）。
"""

# ---------------------------------------------------------------- 全身比例（正面三视图，x 860–1210）
REF_FRONT_TOP_PONYTAIL = 67      # 马尾发髻最高点
REF_FRONT_CROWN = 108            # 头盖顶（发髻下方的头顶弧）
REF_FRONT_EYE = 168
REF_FRONT_CHIN = 213
REF_FRONT_FEET = 1051
REF_FRONT_MIDX = 1035
HEADS_TALL = (REF_FRONT_FEET - REF_FRONT_CROWN) / (REF_FRONT_CHIN - REF_FRONT_CROWN)   # ≈ 9.0 头身
PONYTAIL_ROOT_ABOVE_CROWN = (REF_FRONT_CROWN - REF_FRONT_TOP_PONYTAIL) / (REF_FRONT_CHIN - REF_FRONT_CROWN)  # ≈ 0.39 头高
# 侧视（x 1290–1520）：马尾根在后脑顶，先上扬再垂落，发梢散开，落到背中—腰（侧视梢 ≈ y309，腰封上沿 ≈ y370）
REF_SIDE_PONYTAIL_TIP_Y = 309
REF_SIDE_BELT_TOP_Y = 370
PONYTAIL_LEN_HEADS = (REF_SIDE_PONYTAIL_TIP_Y - 83) / (REF_FRONT_CHIN - REF_FRONT_CROWN)   # 发髻顶→梢 ≈ 2.2 头高（按文案要求做到过腰）

# ---------------------------------------------------------------- 脸部特写（左侧 0–800）
# 读点（原图像素）：中线 x≈418；眼中心 y≈490；眉内端 y≈470、眉尾 y≈450；鼻尖 y≈620；口裂 y≈680；下巴 y≈775
REF_CU = dict(midx=418, eye_y=490, eye_l=(295, 390), eye_r=(445, 545), iris_l=(340, 492), iris_r=(495, 490),
              brow_in_y=470, brow_out_y=450, brow_l=(268, 398), brow_r=(440, 562), brow_thick=17,
              nose_tip_y=620, nostril=(375, 460), mouth_y=680, mouth=(355, 485), chin_y=775,
              cheek_y=520, cheek=(250, 590), jaw_y=700, jaw=(310, 530), ear_y=(400, 560), part_top_y=250)
CU_PX_PER_HU = (775 - 490) / (0.43 * 13.0)      # 眼位于下巴往上 0.43 头高（由正面三视图得出）→ ≈ 51 px/单位

def cu_to_hu(x, y):
    """特写像素 → 头单位"""
    return ((REF_CU['midx'] - x) / CU_PX_PER_HU, -6.45 + (REF_CU['chin_y'] - y) / CU_PX_PER_HU)

# 头单位下的五官（由上面读点换算，rig v3 直接用）
HU_EYE_Y = -0.9            # 眼中心高度
HU_EYE_CX = 1.50           # 眼中心距中线
HU_EYE_HALFW = 0.93        # 半眼宽（眼形细长：宽高比 ≈ 3.8）
HU_EYE_OPEN = 0.49 / 2     # 半眼高
HU_IRIS_R = 0.30
HU_BROW_IN = (0.40, -0.42)     # 眉头 (x, y)
HU_BROW_OUT = (2.80, -0.03)    # 眉尾（上挑）
HU_BROW_THICK = 0.33
HU_NOSE_TIP_Y = -3.43
HU_NOSTRIL_HALFW = 0.83
HU_MOUTH_Y = -4.60
HU_MOUTH_HALFW = 1.26
HU_CHIN_Y = -6.45
HU_CHEEK_HALFW = 3.31      # 颧骨（高颧骨线，眼下 0.6 单位处最宽）
HU_JAW_HALFW = 2.14        # 口裂高度处下颌半宽 → 尖下巴

# 风格化折中（rig v3 实际采用；完全照搬写实比例会让小尺度全身里五官糊成一团）
STYLE = dict(eye_y=-0.45, eye_cx=1.62, eye_halfw=1.0, eye_open=0.34, iris_r=0.34,
             nose_tip_y=-2.75, mouth_y=-4.25, chin_y=-6.75, cheek_halfw=3.55, jaw_halfw=2.35, cran_rx=4.55)
# 面部特征 y 重映射（rig v2 的 y → v3 的 y），分段线性
FACE_Y_REMAP = ((-6.45, -6.75), (-3.45, -4.25), (-1.35, -2.75), (0.55, -0.45), (2.2, 1.45), (5.0, 4.6), (9.0, 9.0))

# ---------------------------------------------------------------- 取色（sRGB 0–255，中值）
COL_HAIR = (9, 9, 12)            # 发：近黑偏冷
COL_HAIR_SHEEN = (120, 122, 132) # 发丝高光
COL_SKIN = (196, 153, 138)       # 颧部亮面：苍白偏粉
COL_SKIN_SHADOW = (140, 107, 96)
COL_IRIS = (150, 92, 40)         # 琥珀
COL_INNER_COLLAR = (146, 101, 86)  # 暗红内领在受光处（暗部约 (70,20,22)）
COL_INNER_COLLAR_DARK = (70, 20, 22)
# rig 是 tone(灰阶)+朱红+金 的合成管线：皮肤 tone≈190（苍白），瞳孔走金通道出琥珀，内领走朱红通道
RIG_SKIN_TONE = 190
RIG_IRIS_TONE = 70
RIG_IRIS_GOLD = 210

# ---------------------------------------------------------------- 描出的轮廓（cv2 阈值<70 + approxPolyDP 2.5px，已截去衣服部分）
REF_FRONT_HAIR_OUTLINE = [(1026, 74), (1022, 81), (1015, 82), (1007, 96), (1007, 106), (999, 114), (992, 130), (995, 172),
                          (991, 185), (996, 188), (993, 213), (997, 218), (991, 225), (1075, 224), (1075, 218), (1079, 217),
                          (1072, 171), (1076, 170), (1074, 155), (1079, 144), (1068, 99), (1057, 77)]
REF_SIDE_HAIR_OUTLINE = [(1445, 83), (1429, 83), (1421, 87), (1417, 95), (1404, 105), (1377, 102), (1345, 113), (1341, 124),
                         (1334, 126), (1329, 160), (1360, 165), (1379, 177), (1387, 160), (1402, 153), (1405, 183),
                         (1416, 195), (1415, 200), (1393, 211), (1375, 228), (1362, 259), (1467, 259), (1470, 226),
                         (1470, 207), (1475, 195), (1467, 176), (1466, 158), (1475, 154), (1467, 142), (1465, 113)]
# 正面刘海（特写读点，像素）：中分缝 x≈420，两侧发帘从 y≈330 斜垂到颧骨 y≈560，3 缕长发垂过眼前到鼻翼高度
REF_BANG_CURTAIN_L = [(420, 300), (370, 330), (320, 380), (285, 450), (265, 530), (255, 590)]
REF_BANG_CURTAIN_R = [(425, 300), (470, 330), (520, 385), (555, 455), (575, 530), (585, 600)]
REF_BANG_EYE_STRANDS = [[(400, 320), (380, 420), (360, 510), (350, 590)], [(445, 320), (470, 420), (490, 520), (500, 600)],
                        [(430, 310), (436, 420), (446, 500)]]
# 鬓发：耳前两侧长发垂到胸前（特写 y≈850 以下仍可见）
REF_SIDELOCK_L = [(230, 420), (200, 560), (180, 700), (170, 860)]
REF_SIDELOCK_R = [(610, 420), (640, 560), (660, 700), (675, 860)]

def front_px_to_hu(x, y):
    s = 13.0 / (REF_FRONT_CHIN - REF_FRONT_CROWN)
    return ((REF_FRONT_MIDX - x) * s, -6.45 + (REF_FRONT_CHIN - y) * s)

HU_FRONT_HAIR_OUTLINE = [tuple(round(v, 2) for v in front_px_to_hu(*p)) for p in REF_FRONT_HAIR_OUTLINE]
HU_BANG_CURTAIN = [tuple(round(v, 2) for v in cu_to_hu(*p)) for p in REF_BANG_CURTAIN_R]
HU_SIDELOCK = [tuple(round(v, 2) for v in cu_to_hu(*p)) for p in REF_SIDELOCK_R]
