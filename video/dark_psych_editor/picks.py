"""Per-beat visual decisions for image beats, made after reviewing review/pick_*.png.

Keys are indexes into review/pick_order.json (the image queries in plan order).
  ('img', k)            candidate k (1-based) of that query: DuckDuckGo cands[:3] then Openverse ov[:4]
  ('imgof', idx, k)     candidate k of another query
  ('gen', key)          generated still assets/gen/<key>.jpg
  ('clip', 'SRC:sec')   archival footage (verified shot time)
  ('gfx', name, opts) / ('word', text, opts) / ('type', text, opts)
  ('remove',)           drop the beat (previous beat extends)
"""
R = {
    0: ('img', 1), 3: ('gen', 'mirror_man'), 4: ('gen', 'old_clock'),
    5: ('gfx', 'counter', {'text': '20–50', 'sub': 'YEARS OLD'}),
    6: ('img', 1), 7: ('clip', 'WAY:338'), 8: ('img', 2), 9: ('clip', 'MDE:767.4'),
    10: ('img', 1), 11: ('img', 1), 13: ('gen', 'brain_wires'), 14: ('gen', 'stairs_levels'), 15: ('clip', 'WAY:477'),
    16: ('img', 3), 17: ('clip', 'MDE:790'), 18: ('clip', 'MDE:140'),
    19: ('type', 'YALE UNIVERSITY', {'sub': 'DEPT. OF PSYCHOLOGY'}),
    20: ('img', 1), 21: ('clip', 'EIC:392'), 22: ('img', 2), 23: ('img', 5), 24: ('clip', 'NUR:600'),
    25: ('word', 'STRIP THE COSTUME', {'color': 'white', 'sfx': 'whoosh'}),
    26: ('gfx', 'puppet', {'mode': 'cut', 'sfx': 'cutsnap'}),
    27: ('gen', 'stairs_climb'), 28: ('img', 4), 29: ('img', 4),
    30: ('gen', 'dissolve_smoke'), 31: ('gen', 'finger_lips'), 32: ('gen', 'disintegrate'),
    33: ('img', 3), 34: ('img', 5),
    35: ('gfx', 'puppet', {'mode': 'control'}), 36: ('remove',),
    37: ('gen', 'surgical_tools'), 38: ('gen', 'ward_1960s'), 39: ('gen', 'hospital_corridor'),
    41: ('gen', 'nurse_station'), 42: ('gen', 'nurse_phone'), 43: ('gen', 'ward_beds'),
    45: ('gen', 'med_cabinet'), 46: ('gen', 'syringe'), 49: ('gen', 'fading_person'), 50: ('gen', 'gloved_hands'),
    51: ('gen', 'nurses_group'), 52: ('gen', 'nursing_class'), 53: ('gen', 'questionnaire'), 54: ('gen', 'rule_book'),
    55: ('img', 4), 56: ('img', 1), 57: ('gen', 'accuse'), 58: ('clip', 'MDE:600'), 59: ('gen', 'monster_shadow'),
    60: ('clip', 'MDE:906'), 61: ('gen', 'crystal_ball'), 62: ('gen', 'sinister'), 63: ('gen', 'broken_portrait'),
    64: ('gen', 'cracked_mirror'), 65: ('gen', 'notes'), 66: ('gen', 'bite_lip'), 67: ('img', 3),
    68: ('gen', 'pressure_gauge'), 69: ('clip', 'NAR:565'), 70: ('gen', 'open_eye'), 71: ('img', 3),
    72: ('gen', 'blindfold'), 73: ('gen', 'screen_alone'), 74: ('gen', 'heart'), 75: ('gen', 'shield'),
    76: ('gen', 'light_switch'), 77: ('gen', 'angel_devil'), 78: ('gen', 'microphone'), 79: ('gen', 'megaphone'),
    80: ('gen', 'shadow_wall'), 81: ('img', 1), 82: ('img', 2), 83: ('gen', 'stop_hand'), 84: ('gen', 'pocket_notebook'),
    85: ('gen', 'empty_chair'), 86: ('img', 5), 87: ('gfx', 'puppet', {'mode': 'control'}), 88: ('clip', 'NUR:1620'),
    89: ('img', 4), 90: ('img', 4), 92: ('gen', 'laptop_email'),
    93: ('type', 'URGENT: MOVE YOUR MONEY NOW.', {'sub': 'FRAUD DEPARTMENT'}),
    94: ('img', 4),
    95: ('gfx', 'staircase', {'marks': [580.8, 581.2, 581.6, 582.3, 582.7], 'sfx': 'stepclicks'}),
    96: ('gen', 'domino_hand'), 97: ('gen', 'stand_meeting'), 98: ('gen', 'walk_away'), 99: ('gen', 'chains'),
    100: ('gen', 'red_rebel'), 101: ('gen', 'shabby_office'), 102: ('gen', 'labcoat'), 103: ('img', 4),
    104: ('gfx', 'puppet', {'mode': 'cut', 'sfx': 'cutsnap'}),
    105: ('img', 3), 106: ('img', 3), 107: ('gen', 'height_chart'), 108: ('gen', 'corridor_doors'), 109: ('img', 5),
    110: ('gen', 'red_crowd'), 111: ('gen', 'empty_head'), 112: ('img', 3), 113: ('img', 4), 114: ('img', 6),
    115: ('clip', 'WAY:480'), 116: ('clip', 'NAR:610'), 117: ('img', 2), 118: ('gen', 'falling_man'),
}

# wiki beats whose files are rate-limited: beat_time -> replacement
WIKI_R = {13.9: ('gen', 'yale'), 14.9: ('clip', 'MDE:816')}

# background overrides for title/typewriter beats: beat_time -> bg spec
BG_R = {293.5: 'MDE:828', 563.2: 'gen:date_stamp'}
