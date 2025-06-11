import re
import json
import sqlite3

import cv2
import mss
import numpy as np

replace_voice = {
    "tweedy": "3D",
    "\.": "",
    ",": "",
    "mm-hmm": "uh huh",
}

replace = {
    "hina": "heena",
    "vtuber": "v tuber",
    "vtubing": "v tubing",
    "anime": "Annie-May",
    "hololive": "hollow live",
    "nijisanji": "niji sanji",
    "playthrough": "play through",
    "(^ai| ai)[ |,|.|!|]": " Aey eye ",
    "(^ais| ais)[ |,|.|!|]": " Aey eyes ",
    "(^ai,| ai,)": " Aey eye ",
    "(^vr| vr)[ |,|.|!|]": " v r ",
    "3d": "three dee",
    "(^loli| loli)[ |,|.|!|]": "lawly",
    "blockchain": "block chain",
    "cryptocurrenc": "crypto currenc",
    "dayo": "dyeo",
    "vshojo": "v sho joe",
    "(^cpu| cpu)[ |,|.|!|]": " c p u ",
    "(^gpu| gpu)[ |,|.|!|]": " g p u ",
    "(^irl| irl)[ |,|.|!|]": " eye are ell ",
    "(^url| url)[ |,|.|!|]": " u are ell ",
    "(^tts| tts)[ |,|.|!|]": " t t s ",
    "(^asmr| asmr)[ |,|.|!|]": " a s m r ",
    "(^vrchat| vrchat)[ |,|.|!|]": " v r chat ",
    "(^cgi| cgi)[ |,|.|!|]": " cee gee eye ",
    "zentreya": "zen treya",
    "slimenetwork": "slime network",
    "berch": "burch",
    "catgirl": "cat girl",
    "-": " ",
    r"\([^()]*\)": "",
    r"[^\w\s]": "", 
    r"[^\w\s\.,]": ""
}

replace_response = {
    "\n": " ",
    "start_of_turn": "",
    "end_of_turn": "",
    "start_of_start": "",
    "<.*>": "",
    "end_of_start": "",
    "end_of_end": "",
    "<": " ",
    ">": " ",
}

def replace_all_voice(text: str):
    text = text.lower()
    for k, v in replace_voice.items():
        text = re.sub(k, v, text)
    return text

def replace_all(text: str):
    text = text.lower()
    for k, v in replace.items():
        text = re.sub(k, v, text)
    return text

def replace_all_response(text: str):
    text = text.lower()
    rep = dict((re.escape(k), v) for k, v in replace_response.items()) 
    pattern = re.compile("|".join(rep.keys()))
    if "berch:" in text.lower():
        return text[:text.index("Berch:")]
    return pattern.sub(lambda m: rep[re.escape(m.group(0))], text)

def grab_screen():
    print("Capturing screen...")
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        height = monitor['height']
        cut = int((monitor['width'] - monitor['height']) / 2)
        monitor = {'top': monitor['top'], 'left': monitor['left'] + cut, 'width': height, 'height': height}
        print(f"Monitor: {monitor}")
        sct_img = sct.grab(monitor)
        sct_img = np.array(sct_img)
        sct_img = cv2.cvtColor(sct_img, cv2.COLOR_BGRA2BGR)
        sct_img = cv2.resize(sct_img, (896, 896), interpolation=cv2.INTER_AREA)
        cv2.imwrite('screenshot.png', sct_img)
        _, buffer = cv2.imencode('.png', sct_img)
        return buffer.tobytes()


class Sound:
    def __init__(self, sound):
        if isinstance(sound, dict):
            self.name = sound.get('name', '')
            self.source_url = sound.get('source_url', '')
            self.duration = sound.get('duration', '')
            self.path = sound.get('path', '')
            self.approved = sound.get('approved', 0)
        else:
            self.name = sound[0]
            self.source_url = sound[1]
            self.duration = sound[2]
            self.path = sound[3]
            self.approved = sound[4]

    def to_dict(self):
        return {
            'name': self.name,
            'source_url': self.source_url,
            'duration': self.duration,
            'path': self.path,
            'approved': self.approved
        }

    def __str__(self):
        return f"{self.name} ({self.duration})"

class Song:
        def __init__(self, song):
            if isinstance(song, dict):
                self.id = song.get('id', '')
                self.title = song.get('title', '')
                self.author = song.get('author', '')
                self.link = song.get('link', '')
                self.duration = song.get('duration', '')
                self.path = song.get('path', '')
                self.thumbnail_url = song.get('thumbnail_url', '')
                self.thumbnail_path = song.get('thumbnail_path', '')
            else:
                self.id = song[0]
                self.title = song[1]
                self.author = song[2]
                self.link = song[3]
                self.duration = song[4]
                self.path = song[5]
                self.thumbnail_url = song[6]
                self.thumbnail_path = song[7]

        def to_dict(self):
            return {
                'id': self.id,
                'title': self.title,
                'author': self.author,
                'link': self.link,
                'duration': self.duration,
                'path': self.path,
                'thumbnail_url': self.thumbnail_url,
                'thumbnail_path': self.thumbnail_path
            }

        def __str__(self):
            return f"{self.title} by {self.author} ({self.duration})"

class Character:
    def __init__(self, character):
        if isinstance(character, dict):
            self.username = character.get('username', '')
            self.nicknames = character.get('nicknames', [])
            self.tts_id = character.get('tts_id', 0)
            self.type = character.get('type', '')
            self.knowledge = character.get('knowledge', [])
            self.is_ai = character.get('is_ai', False)
            self.init_messages = character.get('init_messages', [])
        elif isinstance(character, str):
            print(f"invalid: {character}")
            exit(1)
        else:
            self.username = character[0]
            self.nicknames = json.loads(character[1])
            self.tts_id = character[2]
            self.type = character[3]
            self.knowledge = json.loads(character[4])
            self.is_ai = character[5]
            self.init_messages = json.loads(character[6])
        self.doneTalking = 0
        self.processing = False
        self.textBuffer = []

    def __dict__(self):
        return {
            'username': self.username,
            'nicknames': self.nicknames,
            'tts_id': self.tts_id,
            'type': self.type,
            'knowledge': self.knowledge,
            'init_messages': self.init_messages,
            'doneTalking': self.doneTalking,
            'processing': self.processing,
            'is_ai': self.is_ai,
            'textBuffer': self.textBuffer
        }
    
    def to_dict(self):
        return {
            'username': self.username,
            'nicknames': self.nicknames,
            'tts_id': self.tts_id,
            'type': self.type,
            'knowledge': self.knowledge,
            'init_messages': self.init_messages,
            'doneTalking': self.doneTalking,
            'processing': self.processing,
            'is_ai': self.is_ai,
            'textBuffer': self.textBuffer
        }

    def __str__(self):
        return json.dumps(self.to_dict())

    def __repr__(self):
        return self.__str__()
    

def init_db():
    db = sqlite3.connect("db/riots-memory.db", check_same_thread=False)
    c = db.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS people
             (username text PRIMARY KEY, twitter_username, nicknames json, tts_id integer, type text, knowledge json, is_ai integer, init_messages json)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
             (username text, message text, timestamp integer, source text)''')
    c.execute('''CREATE TABLE IF NOT EXISTS xmentions
             (id text, message text, x_id text, username text, created_at text, attachments text, conversation_id text)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tweets
             (message text, created_at text, attachments text, conversation_id text)''')
    db.commit()
    db.close()

def init_stream_db():
    db_stream = sqlite3.connect("db/stream.db", check_same_thread=False)
    c_stream = db_stream.cursor()
    c_stream.execute('''CREATE TABLE IF NOT EXISTS songs
        (id text PRIMARY KEY, title text, author text, link text, duration text, path text, thumbnail_url text, thumbnail_path text, dmca_risk integer, approved integer)''')
    c_stream.execute('''CREATE TABLE IF NOT EXISTS sounds
        (name text PRIMARY KEY, source_url text, duration text, path text, approved integer)''')
    c_stream.execute('''CREATE TABLE IF NOT EXISTS midi_mappings
        (note integer, control integer, name text, type text, action text, sources json, selection text, inverted integer, UNIQUE(note, control) ON CONFLICT REPLACE)''')
    c_stream.execute('''CREATE TABLE IF NOT EXISTS midi_devices
        (name text, does_tick integer, port integer)''')
    db_stream.commit()
    db_stream.close()

def get_characters_from_db():
    db = sqlite3.connect("db/riots-memory.db", check_same_thread=False)
    c = db.cursor()
    cs = c.execute("SELECT * FROM people WHERE type = 'streamer' OR type = 'vtuber'").fetchall()
    characters = {}
    for character in cs:
        characters[character[0]] = Character(character)
    db.close()
    return characters