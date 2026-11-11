"""CA 单元（C01–C21）提示词 → jobs/r8_D_CA.json（PLAN_r8 第五节模板：头段 + Scene + 尾段 + Reminder，只写 Scene）。
画进生图的字：尾段禁字句改成「除指定汉字外不出现任何文字」。"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HEAD = ("ART STYLE: high-contrast Japanese manga ink illustration, sharp pen lines, solid blacks, screentone textures, brushed speed of a modern "
        "shonen cover. COLOR SCHEME: strictly black, white and one blood-red. Red used boldly on large graphic shapes (sky, sun, background block "
        "or light) and on key details, everything else black and white.\n\nScene: ")
TAIL = ("\n\nThis is a multi-color palette distributed across different objects and lights, NOT a single-color filter or monochrome tint over the "
        "whole image. Anime illustration only, not photorealistic, no real people. Bold but controlled color design, refined and high-end, one clear "
        "focal point; not a cheap mobile-game ad, no particle spam. {NOTEXT} 16:9 widescreen.\n\nReminder — art style: high-contrast Japanese manga "
        "ink illustration; color scheme: strictly black, white and one blood-red.")
NOTEXT = "No text, captions, logos or watermark."
GREEN = (" Isolated on a perfectly flat pure chroma-key green (#00FF00) background with no shadows; the green is only a keying backdrop, "
         "not part of the palette.")
SHEET = ("https://filescos.nananobanana.cn/skills/default-tenant-001/279297c7-dd4b-401e-9d7b-4cfc5b57d004/2026/11/10/"
         "1b8d32ac-b857-4535-b22e-55d00d333754.jpg")
GT = ("Gui Tu (keep exactly the face, hair and costume of the reference model sheet), a strikingly handsome young Chinese swordsman, sharp cold "
      "eyes, he does not smile; long jet-black hair in a high ponytail (pure black, no colored highlights), black robe with a red sash")
EMP_SHEET = ("https://filescos.nananobanana.cn/skills/default-tenant-001/279297c7-dd4b-401e-9d7b-4cfc5b57d004/2026/11/11/"
             "68023565-40d4-4a36-acc1-7a6404184505.jpg")
EMP = ("the Retired Emperor (keep exactly the face, hair and costume of the reference model sheet): a tall gaunt old man, long narrow face with "
       "deep wrinkles and heavy eye bags, half-lidded cold eyes, thin down-turned lips, clean-shaven with no beard and no moustache, no crown; "
       "black hair streaked with long silver-white hair, a small topknot pierced by one black hairpin, the rest hanging loose past the waist; "
       "wide-sleeved floor-length robe of black semi-transparent gauze, dark blood-red sash with long tassels; pale bony fingers")
J = {}


def job(name, scene, green=False, ref=False, text=None, emp=False):
    nt = NOTEXT if not text else (f"Apart from the specified Chinese characters {text}, no other text, letters, numbers, captions, seals, "
                                  "logos or watermark.")
    p = HEAD + scene + (GREEN if green else "") + TAIL.replace('{NOTEXT}', nt)
    d = dict(model='RH_image2', prompt=p, ratio='16:9', size='2K')
    if ref: d['input'] = [SHEET]
    if emp: d['input'] = [EMP_SHEET]
    J[name] = d


# ---------- 共用背景 / 元素（同一场景的连续镜头共用）
job('CA_room', "Background plate only, no characters, no people, no objects in the foreground. A dark ancient Chinese chamber at night lit by "
    "candles: heavy wooden pillars and lattice screens dissolving into deep black shadow, a soft pool of white candlelight in the upper right, "
    "one large blood-red lantern glow on the left, screentone gradients, fine ink hatching. Keep the center calm and empty. No windows, no moon, "
    "no sun, no writing, no symbols.")
job('CA_sky', "Background plate only, no characters, no buildings, no ground. A violent thunderstorm night sky filling the whole frame: towering "
    "black storm clouds drawn in bold ink with bright white cloud edges and screentone, slanted rain sheets, a blood-red glow breaking through the "
    "clouds at the upper right. No moon, no sun, no lightning bolts.")
job('CA_water', "Background plate only, no characters, no people. A vast flat plain of shallow black water reflecting a thunderstorm sky, the "
    "horizon line at about 60 percent of the frame height, dark storm clouds with white edges and screentone above, a thin blood-red band of light "
    "along the horizon, rain ripples on the water drawn as fine ink rings, mirror reflections of the clouds. No moon, no sun, no buildings, no "
    "trees, no rocks, no lightning bolts.")
job('CA_rain', "Foreground element only: dense slanted rain very close to the camera, long thin white rain streaks and some thin black ink rain "
    "streaks of varying length and thickness, all slanted the same way, a few large water droplets, evenly spread over the whole frame.", green=True)
job('CA_slash', "Element only: one sweeping crescent-shaped dry-brush sword-trail stroke, white ink with ragged black ink edges, a powerful arc "
    "from left to right, thick in the middle and tapering to razor-sharp points at both ends, frayed bristle streaks and flying ink splatter along "
    "the path, a thin blood-red accent line along its inner edge.", green=True)
# ---------- 预副歌二：剧本 / 提线 / 皮影 / 天平 / 暗箱
job('C01_paper', "Element only: a single sheet of aged rice paper lying flat, seen straight from above, rectangular with slightly torn edges, filling "
    "most of the frame. Exactly five large Chinese characters 谁定好规则 are brush-written in one horizontal line across the upper half of the page, "
    "bold black ink calligraphy, read left to right in this order: 谁 定 好 规 则. The last two characters 规则 are encircled by one loose hand-drawn "
    "blood-red brush ellipse. The rest of the page is blank paper with subtle fibers and screentone shading, no other writing, no seals, no stamps.",
    green=True, text='谁定好规则')
job('C02_hand', f"Element only: the right hand of {EMP}, reaching down from the top of the frame, seen from below, palm down, long pale bony "
    "fingers spread like a puppeteer controlling marionettes, the wide sleeve of black semi-transparent gauze hanging from the wrist, drawn in "
    "sharp black pen lines with screentone. Only the hand and the gauze sleeve, no face, no strings, no puppets.", green=True, emp=True)
job('C02_tags', "Element only: seven small rectangular pale wooden hanging tags in one evenly spaced horizontal row with clear wide gaps between "
    "them, every tag the same size, each with a small hole at the top and exactly one bold black brush-calligraphy Chinese character in its center; "
    "read left to right the seven characters are: 谁 写 好 剧 本 提 纲. Wood drawn with black ink lines and screentone shading. No strings, no "
    "other marks.", green=True, text='谁写好剧本提纲')
job('C03_screen', "Background plate only, no characters, no puppets. A traditional Chinese shadow-puppet theatre screen seen straight on, filling the "
    "frame: a large stretched white paper screen glowing with strong backlight from behind, dark wooden frame posts at the left and right edges, a "
    "black wooden stage rail along the bottom, screentone gradient falling off to black corners, faint paper fibers, a soft blood-red glow low in "
    "the center behind the paper. The screen is empty. No writing, no symbols.")
job('C03_puppets', "Element only: a row of seven traditional Chinese shadow puppets (piying) of officials and commoners, each standing upright as a "
    "full figure, all separate from each other with wide gaps, cut-leather silhouettes in solid black with intricate punched lace patterns, jointed "
    "limbs, some robes in translucent blood-red leather. No strings, no rods, no text.", green=True)
job('C04_balance', "Element only: a large ancient bronze balance scale seen straight from the front, perfectly level and symmetric: one vertical "
    "central post on a heavy base, a long straight horizontal beam on top, two round shallow empty pans hanging from three chains at each end of the "
    "beam; drawn in sharp black pen lines with white highlights and screentone shading, engraved cloud patterns. The whole object visible with space "
    "around it. No writing.", green=True)
job('C04_seal', "Element only: a heavy square imperial jade seal stone with a coiled dragon knob on top, seen from a three-quarter angle, the bottom "
    "face blank with no characters, black ink lines and white highlights with screentone, one small blood-red silk tassel on the knob.", green=True)
job('C05_box', "Element only: an ornate black lacquer treasure chest seen from a high three-quarter angle, its lid completely removed, the open mouth "
    "a pure black void inside, intricate engraved patterns on the sides drawn in sharp black and white pen lines, screentone shading, metal corner "
    "fittings. No writing, no symbols.", green=True)
job('C06_lid', "Element only: the underside of a heavy rectangular wooden chest lid seen from directly below, filling most of the frame, old dark "
    "wooden planks with grain drawn in black ink lines and screentone, iron straps and two hinges along the top edge, black lacquer rim. No writing, "
    "no symbols.", green=True)
# ---------- 我不低头
job('C07_face', f"Medium close-up of {GT}; head and shoulders in heavy rain, his chin lifting defiantly toward the sky, glaring up past the camera, "
    "wet strands of hair stuck to his face, raindrops on his skin, strong white rim light from lightning behind him.", green=True, ref=True)
job('C08_eyes', f"Extreme close-up of the eyes of {GT}, filling the whole frame horizontally from the brows to the bridge of the nose, cold eyes "
    "glaring straight into the camera, wet black hair strands falling across, raindrops running down the lashes, a tiny white lightning reflection "
    "in each pupil, sharp manga ink lines with screentone. Full-frame image.", ref=True)
job('C09_ready', f"Full-body low-angle shot of {GT}, standing in shallow water in the rain in a crouched ready stance, gripping the long straight "
    "sword low behind his right hip about to slash upward, looking up, ponytail and red sash blowing. Whole body visible from head to feet.",
    green=True, ref=True)
job('C09_slash', f"Full-body low-angle shot of {GT}, at the end of a powerful upward slash: right arm fully extended high overhead with the long "
    "straight sword pointing to the upper right, body twisted, left arm back, ponytail and red sash whipping, robe flaring. Whole body visible from "
    "head to feet.", green=True, ref=True)
job('C10_eave', "Background plate only, no characters. A rainy night under the dark carved wooden eaves of an ancient Chinese palace hall, seen from "
    "slightly below: a massive carved roof beam crossing the top part of the frame horizontally, rain pouring from the eaves in streams, dark storm "
    "sky beyond, ink linework and screentone, a blood-red lantern glow far in the background. Empty space under the beam. No writing, no plaques, "
    "no signs, no symbols, no hanging objects.")
job('C10_tablets', "Element only: four tall narrow black lacquered wooden plaques hanging vertically in one row with wide gaps between them, all the "
    "same size, each with exactly one large Chinese character carved deep into the wood and filled with blood-red, bold brush calligraphy; read left "
    "to right the four characters are: 大 局 为 上. The first character is 大 (big): exactly three strokes, one horizontal stroke crossed by a "
    "left-falling and a right-falling sweep, with no dot and no extra stroke. Black ink lines, white highlights, screentone. No strings, no other "
    "marks.", green=True, text='大局为上')
job('C11_blade', "Element only: a long straight Chinese sword lying perfectly horizontal across the full width of the frame, tip pointing right, the "
    "black steel blade drawn in sharp black pen lines with white highlights and screentone, its whole cutting edge glowing red-hot in blood-red and "
    "white, wisps of white steam curling off the hot edge where raindrops hit it, a black hilt with a short blood-red tassel at the far left edge.",
    green=True)
job('C13_vortex', "Background plate only, no characters. Looking straight up into the eye of a colossal thunderstorm: storm clouds spiraling inward "
    "in a giant vortex filling the whole frame, bold black ink cloud bands with white edges and screentone, the calm eye in the center a deep black "
    "hole rimmed with blood-red glowing embers, rain lines streaking toward the center. No moon, no sun, no buildings, no lightning bolts.")
job('C14_ots', f"Over-the-shoulder view from low behind {GT}: the back of his head and shoulders filling the lower part of the frame, high ponytail "
    "and black robe seen from behind, head tilted back looking up at the sky, rain soaking his hair. Only the head, hair and shoulders.",
    green=True, ref=True)
# ---------- 间奏 C15（用户：跳斩太丑，换形式 → 不跳：立定 → 血振）
job('C15_stand', f"Full-body front view of {GT}, standing alone tall and still, the long straight sword held point-down at his right side, head "
    "raised toward the stormy sky, ponytail and red sash blowing in the wind. Whole body visible from head to feet.", green=True, ref=True)
job('C15_flick', f"Full-body front view of {GT}, performing a sharp blood-flick (chiburi): his right arm swept down and out to the side, the long "
    "straight sword pointing diagonally down to the lower right, a fan of blood-red droplets flung off the blade in an arc, body still and upright, "
    "cold expression, ponytail and red sash swinging. Whole body visible from head to feet.", green=True, ref=True)
# ---------- 副歌二前半
job('C16_blood', "Element only: the single Chinese character 血 formed by blood-red ink diffusing in water, seen from directly above, bold "
    "brush-calligraphy strokes with wet bleeding edges, fine ink tendrils curling off the strokes, a few black ink flecks; one character in the "
    "center of the frame.", green=True, text='血')
job('C17_kneel', f"Full-body front view of {GT}, dropping onto one knee in shallow water, driving the long straight sword point-down into the water "
    "in front of him with both hands on the hilt, head bowed, ponytail and red sash swinging down, a splash of water around his knee. Whole body "
    "visible.", green=True, ref=True)
job('C18_soldiers', "Element only: three heavy-armored ancient Chinese spearmen charging toward the camera, each a separate full-body figure with wide "
    "gaps between them, lamellar armor and helmets with blood-red plumes, long spears leveled forward, faces shadowed under the helmets, drawn in "
    "sharp black ink lines with screentone.", green=True)
job('C18_draw', f"Full-body front view of {GT}, rising from a crouch while drawing the long straight sword from the scabbard at his hip, the blade "
    "half out and flashing, glaring forward, ponytail and red sash blowing. Whole body visible from head to feet.", green=True, ref=True)
job('C19_spin', f"Full-body view of {GT}, in the middle of a spinning horizontal slash: body twisted in a full turn, the long straight sword sweeping "
    "horizontally around him at waist height, robe hem, red sash and ponytail flaring outward in a circle. Whole body visible from head to feet.",
    green=True, ref=True)
job('C19_spear', "Element only: one single long ancient Chinese spear lying perfectly horizontal across the frame, a steel leaf-shaped spearhead "
    "pointing right with a bushy blood-red horsehair tassel just behind the head, a black wooden shaft, black ink line art with screentone.",
    green=True)
job('C20_emp', f"Close-up portrait of {EMP}; head and shoulders, his head slowly turning toward the camera over his shoulder with a cold "
    "cunning look, one pale bony hand raised with clawed fingers near his chest, loose silver-streaked hair blowing, strong white lightning backlight "
    "behind him, rain.", green=True, emp=True)
job('C21_split', "Background plate only, no people. A stormy sky split into two halves: the left half is black storm clouds lit blood-red, with one "
    "huge Chinese character 邪 painted in blood-red brush calligraphy in its upper left; the right half is pale white storm clouds with screentone, "
    "with one huge Chinese character 正 painted in black brush calligraphy in its upper right. The middle of the frame is plain clouds without "
    "characters. No moon, no sun, no buildings.", text='邪 and 正')

if __name__ == '__main__':
    json.dump(J, open(ROOT + '/jobs/r8_D_CA.json', 'w'), ensure_ascii=False, indent=1)
    print(len(J), 'jobs', 3 * len(J), '积分')
