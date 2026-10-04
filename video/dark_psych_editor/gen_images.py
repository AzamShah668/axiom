"""Generate noir-style stills for beats with no usable web image (Pollinations, free tier).

Writes assets/gen/<key>.jpg (watermark strip cropped off). Skips keys that already exist.
"""
import os
import subprocess
import sys
import time
import urllib.parse

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'assets', 'gen')
os.makedirs(OUT, exist_ok=True)

PHOTO = ', cinematic black and white film photograph, film noir lighting, high contrast, deep shadows, 1960s, film grain, no text'
ART = ', dark surreal editorial illustration, black and deep red palette, high contrast, cinematic lighting, film grain, no text'

PROMPTS = {
    'stairs_levels': 'a dark stone staircase rising toward a single bright doorway of light' + PHOTO,
    'stairs_climb': 'a small lone man in a suit climbing an endless staircase into darkness' + PHOTO,
    'dissolve_smoke': 'a faceless man in a suit dissolving into smoke, dark background' + ART,
    'finger_lips': 'close up of a man pressing a finger to his lips, silence, dark background' + PHOTO,
    'disintegrate': 'a man in a suit disintegrating into dust particles drifting away, black background' + ART,
    'surgical_tools': 'vintage surgical instruments lying on a metal hospital tray' + PHOTO,
    'ward_1960s': 'a 1960s hospital ward at night, rows of iron beds, a single lamp' + PHOTO,
    'nurse_station': 'a 1960s nurse in white uniform and cap at a hospital nurses station at night, a desk telephone' + PHOTO,
    'nurse_phone': 'a 1960s nurse holding a telephone receiver to her ear, worried face, hospital at night' + PHOTO,
    'ward_beds': 'a long 1960s hospital ward with rows of empty beds, night' + PHOTO,
    'med_cabinet': 'a vintage glass hospital medicine cabinet full of small bottles, dim light' + PHOTO,
    'syringe': 'close up of hands filling a glass syringe from a small medicine vial' + PHOTO,
    'nurses_group': 'a group of 1960s nurses in white uniforms and caps standing in a hospital corridor' + PHOTO,
    'nursing_class': '1960s nursing students sitting in a classroom listening' + PHOTO,
    'questionnaire': 'a vintage paper questionnaire form with a pencil on a wooden desk' + PHOTO,
    'rule_book': 'an old hospital rule book lying open on a desk under a desk lamp' + PHOTO,
    'accuse': 'a hand pointing an accusing finger at the viewer, dramatic shadow' + PHOTO,
    'monster_shadow': 'an ordinary man standing in front of a wall, his shadow on the wall is a monster' + ART,
    'crystal_ball': 'a glowing crystal ball on a dark table, hands hovering over it' + PHOTO,
    'sinister': 'a sinister smiling man half in shadow' + PHOTO,
    'broken_portrait': 'a shattered framed portrait photograph of a man, broken glass' + PHOTO,
    'cracked_mirror': 'a man looking into a cracked mirror, his reflection broken' + PHOTO,
    'notes': 'old handwritten research notes on yellowed paper, a fountain pen' + PHOTO,
    'bite_lip': 'extreme close up of a sweating man biting his lip nervously' + PHOTO,
    'pressure_gauge': 'an old pressure gauge with the needle in the red zone, steam escaping' + PHOTO,
    'open_eye': 'extreme close up of a wide open human eye, terrified' + PHOTO,
    'blindfold': 'a man in a suit wearing a blindfold, dark background' + PHOTO,
    'screen_alone': 'a person sitting alone in a dark room lit only by a phone screen' + PHOTO,
    'heart': 'an anatomical human heart, glowing, black background' + ART,
    'shield': 'a cracked old metal shield on a black background' + PHOTO,
    'light_switch': 'an old light switch on a dark wall, a finger about to press it' + PHOTO,
    'angel_devil': 'a man with a small angel on one shoulder and a small devil on the other, whispering' + ART,
    'microphone': 'a vintage radio microphone in a dark studio' + PHOTO,
    'megaphone': 'a man shouting into a megaphone' + PHOTO,
    'shadow_wall': 'the shadow of a man on a brick wall growing into a monster' + ART,
    'stop_hand': 'a raised open hand gesturing stop, dramatic side light, black background' + PHOTO,
    'pocket_notebook': 'a small notebook in the breast pocket of a suit jacket, close up' + PHOTO,
    'empty_chair': 'a single empty wooden chair under a spotlight in a dark empty room' + PHOTO,
    'date_stamp': 'a vintage rubber date stamp pressing onto an office document' + PHOTO,
    'laptop_email': 'a laptop screen glowing in a dark room, a man staring at it anxiously, modern' + PHOTO,
    'domino_hand': 'a hand stopping a row of falling dominoes' + PHOTO,
    'stand_meeting': 'a man standing up to speak at a 1960s office meeting table, others looking at him' + PHOTO,
    'walk_away': 'a man walking away from a staircase toward a bright light, silhouette' + PHOTO,
    'chains': 'broken iron chains on a black background' + PHOTO,
    'red_rebel': 'one person in red standing still in a crowd of identical grey people walking past' + ART,
    'shabby_office': 'a shabby run down 1960s office with an old desk and peeling walls' + PHOTO,
    'labcoat': 'a white lab coat hanging on a hanger in a dark room' + PHOTO,
    'height_chart': 'a vintage height measuring chart on a wall with pencil marks' + PHOTO,
    'corridor_doors': 'a long dark corridor with many closed doors' + PHOTO,
    'red_crowd': 'a single figure in red stepping out of a grey crowd' + ART,
    'empty_head': 'an empty silhouette of a human head with a dark void inside' + ART,
    'falling_man': 'a man in a suit falling backwards into darkness' + PHOTO,
    'mirror_man': 'a young man in a suit staring at his own reflection in an ornate mirror, dark room' + PHOTO,
    'old_clock': 'an antique wooden wall clock with roman numerals in a dark room' + PHOTO,
    'brain_wires': 'a human brain tangled in electrical wires with glowing red sparks, black background' + ART,
    'hospital_corridor': 'an empty 1960s hospital corridor at night, a single flickering ceiling light' + PHOTO,
    'fading_person': 'a faceless person fading away into darkness, dissolving at the edges, black background' + ART,
    'gloved_hands': 'close up of hands pulling on surgical gloves, dark background, single hard light' + PHOTO,
    'yale': 'the gothic stone buildings of Yale University old campus, 1960s' + PHOTO,
}


def gen(key, prompt, seed):
    dst = os.path.join(OUT, key + '.jpg')
    if os.path.exists(dst):
        return True
    url = 'https://image.pollinations.ai/prompt/%s?width=1920&height=1080&nologo=true&seed=%d&model=flux' % (
        urllib.parse.quote(prompt), seed)
    for attempt in range(4):
        tmp = dst + '.part'
        r = subprocess.run(['curl', '-sL', '--max-time', '240', '-o', tmp, '-w', '%{http_code}', url], capture_output=True, text=True)
        try:
            im = Image.open(tmp).convert('RGB')
            w, h = im.size
            im = im.crop((0, 0, w, int(h * 0.93)))  # drop the bottom strip with the watermark
            im.save(dst, quality=94)
            os.remove(tmp)
            return True
        except Exception:
            time.sleep(8 + 8 * attempt)
    return False


if __name__ == '__main__':
    keys = sys.argv[1:] or list(PROMPTS)
    for n, k in enumerate(keys):
        ok = gen(k, PROMPTS[k], 100 + n)
        print('%2d/%d %s %s' % (n + 1, len(keys), 'ok ' if ok else 'FAIL', k), flush=True)
        time.sleep(2)
