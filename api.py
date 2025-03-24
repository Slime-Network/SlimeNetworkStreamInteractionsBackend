import copy
import json
import sqlite3
import sys
import time
import numpy as np
import requests
import sounddevice as sd
import os
from flask import Flask, request
from melo.api import TTS
import ollama
import ffmpeg

import logging

import yt_dlp
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

flask_app = Flask(__name__)
flask_app.secret_key = 'super secret key'

ollama_client = ollama.Client("http://localhost:11434")

from utils import replace_all
import json

for i in range(1, 100):
    try:
        print(f"{i}: {sd.query_devices(i)}")
    except:
        pass

out_id = 9

class Sound:
    def __init__(self, sound):
        print("Init Sound", sound, file=sys.stderr)
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
            print("Init Song", song, file=sys.stderr)
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

def start_api(**kwargs):
    global characters
    global activePeople
    global config
    global tts_model
    global conversation
    global hold
    global last_save
    global streams
    global music_stream
    global pitch
    global speed
    global voice_volume
    global music_volume
    global recalibrate
    global db
    global paused
    global midi
    global songQueue

    config = kwargs
    conversation = []
    activePeople = {}
    songQueue = []
    hold = False
    pitch = 1.0
    speed = 1.0
    voice_volume = 1.0
    music_volume = 1.0
    recalibrate = False
    last_save = time.time()
    streams = []
    music_stream = None
    paused = False
    midi = {"key": None, "control": None}

    db_stream = sqlite3.connect("db/stream.db", check_same_thread=False)
    c_stream = db_stream.cursor()
    c_stream.execute('''CREATE TABLE IF NOT EXISTS songs
             (id text PRIMARY KEY, title text, author text, link text, duration text, path text, thumbnail_url text, thumbnail_path text, dmca_risk integer, approved integer)''')
    c_stream.execute('''CREATE TABLE IF NOT EXISTS sounds
             (name text PRIMARY KEY, source_url text, duration text, path text, approved integer)''')
    c_stream.execute('''CREATE TABLE IF NOT EXISTS midi_control_mappings
            (control integer PRIMARY KEY, name text)''')
    c_stream.execute('''CREATE TABLE IF NOT EXISTS midi_key_mappings
        (note integer PRIMARY KEY, name text, type text, action text, sources json, selection text)''')
    db_stream.commit()
    db_stream.close()


    db = sqlite3.connect("db/riots-memory.db", check_same_thread=False)

    c = db.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS people
             (username text PRIMARY KEY, nicknames json, tts_id integer, type text, knowledge json, is_ai integer, init_messages json)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS messages
             (username text, message text, timestamp integer)''')
    
    cs = c.execute("SELECT * FROM people WHERE type = 'character'").fetchall()

    if len(cs) == 0:
        try:
            cs = json.load(open("characters.json"))
            for character in cs:
                c.execute("INSERT INTO people VALUES (?, ?, ?, ?, ?, ?, ?)", (character, json.dumps(cs[character]["nicknames"]), cs[character]["tts_id"], "streamer", "[]", cs[character]["is_ai"], json.dumps(cs[character]["init_messages"])))
            db.commit()
            time.sleep(4)
            cs = c.execute("SELECT * FROM people WHERE type = 'character'").fetchall()
        except:
            pass

    characters = {str(character): Character(cs[character]) for character in cs}

    conversation = c.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 300").fetchall()

    checkpointPath = "VoiceTraining/logs/voices/"
    highest = 0
    for file in os.listdir(checkpointPath):
        if file.startswith("G_") and file.endswith(".pth"):
            number = int(file.split("_")[1].split(".")[0])
            if number > highest:
                highest = number
    
    tts_model = TTS(language='EN', device='auto', config_path="VoiceTraining/data/voices/config.json", ckpt_path=f"VoiceTraining/logs/voices/G_{highest}.pth")
    print(f"Loaded TTS model G_{highest}.pth", file=sys.stderr)
    print(f"TTS Voices: {tts_model.hps.data.spk2id}", file=sys.stderr)
    
    print("Starting API...", file=sys.stderr)
    flask_app.run(port=5275)

def push_messages():
    global characters
    global conversation
    global hold
    if not "riot" in characters:
        print("No Riot", file=sys.stderr)
        return
    if hold or config.get('runAI', True) is False or characters["riot"].processing or characters["riot"].doneTalking > time.time():
        return

    characters["riot"].processing = True
    messages = copy.deepcopy(characters["riot"].init_messages)

    if len(conversation) > config.get('conversation_length', 300):
        conversation = conversation[-config.get('conversation_length', 300):]
    
    for line in conversation:
        if len(line[1]) > 1:
            if not line[0] or not line[1]:
                continue
            if line[0] == "Riot":
                messages.append({"role": "assistant", "content": f'{line[1].strip()}'})
            else:
                if line[0] in characters:
                    messages.append({"role": "user", "content": f'{characters[line[0]].nicknames[0]}: {line[1].strip()}'})
                else:
                    person = check_person(line[0])
                    messages.append({"role": "user", "content": f'{person.username}: {line[1].strip()}'})

    response = ollama_client.chat(model='Riot', messages=messages)
    if response['message']['content'] != "":
        speak(response['message']['content'], "Riot", "Riot")
    characters["riot"].processing = False

def check_person(username: str):
    global characters
    if username in characters:
        return characters[username]
    elif username in activePeople:
            return activePeople[username]
    else:
        c = db.cursor()
        person = c.execute("SELECT * FROM people WHERE username = ?", (username,)).fetchone()
        if person:
            activePeople[username] = Character(person)
            return Character(person)
        else:
            n = Character({
                "username": username,
                "nicknames": [],
                "tts_id": 0,
                "type": "chatter",
                "knowledge": [
                    f"{username} is a new chatter",
                ],
                "is_ai": False,
                "init_messages": []
            })
            c.execute("INSERT INTO people VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(username) DO UPDATE nicknames=excluded.nicknames, tts_id=excluded.tts_id, type=excluded.type, knowledge=excluded.knowledge, is_ai=excluded.is_ai, init_messages=excluded.init_messages", (n.username, json.dumps(n.nicknames), n.tts_id, n.type, json.dumps(n.knowledge), n.is_ai, json.dumps(n.init_messages)))
            return n

def speak(message: str, character: str, source: str):
    global last_save
    index = character.lower()
    if character and message:
        if index in characters:

            characters[index].textBuffer.append(message)

            if characters[index].doneTalking > time.time():
                print(f"Waiting for {characters[index].doneTalking - time.time()}s", file=sys.stderr)
                time.sleep(characters[index].doneTalking - time.time())

            if len(characters[index].textBuffer) == 0:
                return 'Messages already spoken'

            messages = ""
            for m in characters[index].textBuffer:
                messages += f"{m}\n"

            characters[index].textBuffer.clear()

            messages_commands = messages.split("::")

            i = 0
            while i < len(messages_commands):
                print(f"Processing: {messages_commands[i]}", file=sys.stderr)
                if i % 2 == 0:
                    audio = tts_model.tts_to_file(replace_all(messages_commands[i]), characters[index].tts_id, speed=speed)
                    
                    conversation.append((source, messages_commands[i]))
                    c = db.cursor()
                    c.execute("INSERT INTO messages VALUES (?, ?, ?)", (source, messages_commands[i], int(time.time())))

                    with sd.OutputStream(channels=1, samplerate=44100 + pitch) as output_stream:
                        characters[index].doneTalking = time.time() + len(audio) / (44100)
                        streams.append(output_stream)
                        output_stream.start()
                        output_stream.write(audio)
                    i += 1
                else:
                    command = messages_commands[i].split(" ")
                    i += 1
                    if command[0] == "pause":
                        time.sleep(float(command[1]))
                    elif command[0] == "stop":
                        break
                    

            if last_save + 60 < time.time():
                db.commit()
                last_save = time.time()
                
        return 'Message posted successfully'
    else:
        return 'Invalid message'
    

@flask_app.route('/speak', methods=['POST'])
def post_message():
    print(f"Received message: {request.json}", file=sys.stderr)
    message = request.json.get('message')
    character = request.json.get('character')
    source = request.json.get('source')
    resp = speak(message, character, source)
    push_messages()
    return resp

@flask_app.route('/hold', methods=['POST'])
def hold_ai():
    global hold
    if request.json.get('hold') == "toggle":
        print("Toggling AI", file=sys.stderr)
    elif request.json.get('hold') == "true":
        print("Holding AI", file=sys.stderr)
    hold = not hold
    return {'success': True, 'hold': hold}

@flask_app.route('/shush', methods=['POST'])
def shush():
    num = len(streams)
    for stream in streams:
        stream.stop()
    streams.clear()
    for character in characters:
        characters[character].doneTalking = 0
    return {'success': True, 'stopped': num}

@flask_app.route('/pitch', methods=['POST'])
def change_pitch():
    global pitch
    print("Changing pitch", request.json, file=sys.stderr)
    pitch = request.json.get('pitch')
    return {'success': True, 'pitch': pitch}

@flask_app.route('/speed', methods=['POST'])
def change_speed():
    global speed
    print("Changing speed", request.json, file=sys.stderr)
    speed = request.json.get('speed')
    return {'success': True, 'speed': speed}

@flask_app.route('/voiceVolume', methods=['POST'])
def change_voice_volume():
    global voice_volume
    print("Changing voice_volume", request.json, file=sys.stderr)
    voice_volume = request.json.get('voice_volume')
    return {'success': True, 'voice_volume': voice_volume}

@flask_app.route('/musicVolume', methods=['POST'])
def change_music_volume():
    global music_volume
    print("Changing music_volume", request.json, file=sys.stderr)
    music_volume = request.json.get('music_volume')
    return {'success': True, 'music_volume': music_volume}

@flask_app.route('/updateTick', methods=['POST'])
def update_tick():
    push_messages()
    return 'Tick updated'

@flask_app.route('/recalibrate', methods=['POST'])
def recalibrate_cam():
    global recalibrate
    recalibrate = True
    return {'success': True}


@flask_app.route('/characters', methods=['GET'])
def get_character_animation():
    global characters
    cs = []
    for character in characters:
        cs.append(characters[character].to_dict())
    return cs


@flask_app.route('/character', methods=['POST'])
def post_character_animation():
    global characters
    character = Character(request.json.get('characters'))

    characters[character.username] = character

    print("update", characters, file=sys.stderr)

    db.cursor().execute("INSERT INTO people VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(username) DO UPDATE SET nicknames=excluded.nicknames, type=excluded.type, tts_id=excluded.tts_id, knowledge=excluded.knowledge, is_ai=excluded.is_ai, init_messages=excluded.init_messages;", (character.username, json.dumps(character.nicknames), character.tts_id, character.type, json.dumps(character.knowledge), character.is_ai, json.dumps(character.init_messages)))
    db.commit()
    print(characters, file=sys.stderr)
    return {'success': True}


@flask_app.route('/animData', methods=['GET'])
def get_anim_data():
    global characters
    global recalibrate
    anim_data = {}
    for character in characters:
        anim_data[character] = {}
        anim_data[character]["isTalking"] = characters[character].doneTalking > time.time()
    
    if recalibrate:
        anim_data["recalibrate"] = True
        recalibrate = False

    return anim_data

@flask_app.route('/clearConversation', methods=['get'])
def clear_conversation():
    global conversation
    conversation = []
    return {'success': True}

@flask_app.route('/twitchEvent', methods=['POST'])
def post_twitch_event():
    global conversation
    print("Received twitch event", request.json, file=sys.stderr)
    conversation.append((request.json['source'], request.json['message']))
    return {'success': True}

@flask_app.route('/midi', methods=['POST'])
def midi_event():
    global midi
    midi = request.json
    print(f"Received MIDI event: {midi}", file=sys.stderr)
    return {'success': True}

@flask_app.route('/midi', methods=['GET'])
def get_midi():
    global midi
    print(f"Sending MIDI event: {midi}", file=sys.stderr)
    return midi

@flask_app.route('/midiMapping', methods=['GET'])
def get_midi_mapping():
    midi_db = sqlite3.connect("db/stream.db", check_same_thread=False)
    c = midi_db.cursor()
    ks = c.execute('''SELECT * FROM midi_key_mappings''').fetchall()
    cs = c.execute('''SELECT * FROM midi_control_mappings''').fetchall()
    keys = []
    controls = []
    for key in ks:
        keys.append({
            'note': key[0],
            'name': key[1],
            'type': key[2],
            'action': key[3],
            'sources': json.loads(key[4]),
            'selection': key[5]
        })
    for control in cs:
        controls.append({
            'control': control[0],
            'name': control[1]
        })
    midi_db.close()
    return {'keys': keys, 'controls': controls}

@flask_app.route('/midiKey', methods=['POST'])
def post_midi_key():
    print(f"Received new MIDI Key: {request.json}", file=sys.stderr)
    midi_db = sqlite3.connect("db/stream.db", check_same_thread=False)
    c = midi_db.cursor()
    print("oooo", json.dumps(request.json['sources']), file=sys.stderr)
    c.execute('''INSERT INTO midi_key_mappings VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(note) DO UPDATE SET name=excluded.name, type=excluded.type, action=excluded.action, sources=excluded.sources, selection=excluded.selection''', (request.json['note'], request.json['name'], request.json['type'], request.json['action'], json.dumps(request.json['sources']), request.json['selection']))
    midi_db.commit()
    midi_db.close()
    return {'success': True}

@flask_app.route('/midiControl', methods=['POST'])
def post_midi_control():
    print(f"Received new MIDI Control: {request.json}", file=sys.stderr)
    midi_db = sqlite3.connect("db/stream.db", check_same_thread=False)
    c = midi_db.cursor()
    c.execute('''INSERT INTO midi_control_mappings VALUES (?, ?) ON CONFLICT(control) DO UPDATE SET name=excluded.name''', (request.json['control'], request.json['name']))
    midi_db.commit()
    midi_db.close()
    return {'success': True}

@flask_app.route('/midiKeyDelete', methods=['POST'])
def delete_midi_key():
    midi_db = sqlite3.connect("db/stream.db", check_same_thread=False)
    c = midi_db.cursor()
    c.execute('''DELETE FROM midi_key_mappings WHERE note = ?''', (request.json['note'],))
    midi_db.commit()
    midi_db.close()
    return {'success': True}

@flask_app.route('/midiControlDelete', methods=['POST'])
def delete_midi_control():
    midi_db = sqlite3.connect("db/stream.db", check_same_thread=False)
    c = midi_db.cursor()
    c.execute('''DELETE FROM midi_control_mappings WHERE control = ?''', (request.json['control'],))
    midi_db.commit()
    midi_db.close()
    return {'success': True}

@flask_app.route('/addYoutubeSong', methods=['POST'])
def add_youtube_song():
    print(f"adding YouTube song: {request.json}", file=sys.stderr)
    url = request.json.get('url')
    dmca_risk = request.json.get('dmca_risk', 0)
    db = sqlite3.connect("db/stream.db")
    c = db.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS songs
             (id text PRIMARY KEY, title text, author text, link text, duration text, path text, thumbnail_url text, thumbnail_path text, dmca_risk integer, approved integer)''')
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'merge_output_format': 'mp3',
            'outtmpl': 'music/%(display_id)s.%(ext)s'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            print(f"Title: {info_dict.get('title', 'Unknown Title')}")
            print(f"Download completed! File saved as {info_dict.get('display_id', 'Unknown')}.{info_dict.get('ext', 'mp3')}")
            thumbnail_url = info_dict.get('thumbnail', 'Unknown Thumbnail URL')
            thumbnail_path = f"./music/{info_dict.get('display_id', 'Unknown')}.webp"
            with requests.get(thumbnail_url) as thumbnail_file:
                with open(thumbnail_path, 'xb') as file:
                    file.write(thumbnail_file.content)

            print(f"Thumbnail downloaded! File saved as {thumbnail_path}")
            c.execute("INSERT INTO songs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET title=excluded.title, author=excluded.author, link=excluded.link, duration=excluded.duration, path=excluded.path, thumbnail_url=excluded.thumbnail_url, thumbnail_path=excluded.thumbnail_path, dmca_risk=excluded.dmca_risk, approved=excluded.approved", (info_dict.get('display_id', 'Unknown Title'), info_dict.get('title', 'Unknown Title'), info_dict.get('uploader', 'Unknown Author'), url, info_dict.get('duration', 'Unknown Duration'), os.path.abspath(f"music/{info_dict.get('display_id', 'Unknown')}.{info_dict.get('ext', 'mp3')}"), info_dict.get('thumbnail', 'Unknown Thumbnail URL'), os.path.abspath(f"music/{info_dict.get('display_id', 'Unknown Title')}.webp"), dmca_risk, 0))
            db.commit()
            db.close()
            return {'success': True}
    except Exception as e:
        print(f"An error occurred: {e}")

@flask_app.route('/addYoutubeSound', methods=['POST'])
def add_youtube_sound():
    print(f"adding YouTube sound: {request.json}", file=sys.stderr)
    url = request.json.get('url')
    name = request.json.get('name')
    start_time = int(request.json.get('start_time', 0))
    length = int(request.json.get('length', 6))
    length = min(length, 10)
    db = sqlite3.connect("db/stream.db")
    c = db.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sounds
             (name text PRIMARY KEY, source_url text, duration text, path text, approved integer)''')
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'merge_output_format': 'mp3',
            'outtmpl': f'sounds/youtube/{name}.%(ext)s',
            
            "external_downloader": "ffmpeg",
            "external_downloader_args": {"ffmpeg_i": ["-ss", str(start_time), "-to", str(start_time + length)]},
        }

        print(f"Downloading {url} to sounds/youtube/{name}.mp3")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            print(f"Adding New Sound: {name}")
            print(f"Download completed! File saved as {name}.{info_dict.get('ext', 'mp3')}")

            c.execute("INSERT INTO sounds VALUES (?, ?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET source_url=excluded.source_url, duration=excluded.duration, path=excluded.path, approved=excluded.approved", (name, url, info_dict.get('duration', 'Unknown Duration'), os.path.abspath(f"sounds/youtube/{name}.webm"), 0))
            db.commit()
            db.close()
            return {'success': True}
    except Exception as e:
        print(f"An error occurred: {e}")


@flask_app.route('/songs', methods=['GET'])
def get_songs():
    db = sqlite3.connect("db/stream.db")
    c = db.cursor()
    ss = c.execute("SELECT * FROM songs").fetchall()
    songs = []
    for song in ss:
        songs.append(Song(song).to_dict())
    db.close()
    return songs

@flask_app.route('/sounds', methods=['GET'])
def get_sounds():
    db = sqlite3.connect("db/stream.db")
    c = db.cursor()
    ss = c.execute("SELECT * FROM sounds").fetchall()
    sounds = []
    for sound in ss:
        sounds.append(Sound(sound).to_dict())
    db.close()
    return sounds

@flask_app.route('/randomPlaylist', methods=['GET'])
def get_random_playlist():
    db = sqlite3.connect("db/stream.db")
    c = db.cursor()
    size = request.args.get('size')
    if not size:
        size = 30
    ss = c.execute("SELECT * FROM songs ORDER BY RANDOM() LIMIT ?", (size)).fetchall()
    songs = []
    for song in ss:
        songs.append(Song(song).to_dict())
    return songs

@flask_app.route('/playSong', methods=['POST'])
def play_song():
    global songQueue
    global music_stream
    global paused
    if paused:
        paused = False
        if music_stream:
            music_stream.start()
            return {'success': True}
    if music_stream:
        music_stream.stop()
        music_stream = None
    song = Song(request.json.get('song'))
    songQueue.insert(0, song)
    print(f"Playing: {song}", file=sys.stderr)
    while len(songQueue) > 0:
        song = songQueue.pop()
        print(f"Playing: {song}", file=sys.stderr)
        music_stream = sd.OutputStream(channels=1, blocksize=6000, samplerate=48000, dtype='float32')
        music_stream.start()
        out = ffmpeg.input(filename=song.path).output('-', format='f32le', acodec='pcm_f32le', ac=1, ar='48000').overwrite_output().run(capture_stdout=True, capture_stderr=True)
        audio_data = np.frombuffer(out[0], dtype=np.float32)

        blocks = len(audio_data) // music_stream.blocksize
        block = 0
        print(f"Blocks: {blocks}", file=sys.stderr)
        try:
            while music_stream.active:
                while paused:
                    time.sleep(0.2)
                if len(audio_data) == 0:
                    music_stream.stop()
                    music_stream = None
                music_stream.write(audio_data[block * music_stream.blocksize:(block + 1) * music_stream.blocksize] * music_volume)

                block += 1
                if block >= blocks:
                    music_stream.stop()
                    music_stream = None
        except Exception as e:
            print(f"Song Stopped", e)
            return {'success': True}
        
        print("Song finished", file=sys.stderr)
    return {'success': True}

@flask_app.route('/queueSong', methods=['POST'])
def queue_song():
    global songQueue
    song = Song(request.json.get('song'))
    songQueue.append(song)
    return {'success': True}

@flask_app.route('/stopSong', methods=['POST'])
def stop_song():
    global music_stream
    global paused
    paused = False
    if music_stream:
        music_stream.stop()
        music_stream = None
    return {'success': True}

@flask_app.route('/pauseSong', methods=['POST'])
def pause_song():
    global paused
    paused = not paused
    return {'success': True}

@flask_app.route('/playSound', methods=['POST'])
def play_sound():
    global music_stream
    global paused
    if paused:
        paused = False
        if music_stream:
            music_stream.start()
            return {'success': True}
    if music_stream:
        music_stream.stop()
        music_stream = None
    sound = Sound(request.json.get('sound'))
    print(f"Playing: {sound}", file=sys.stderr)
    music_stream = sd.OutputStream(channels=1, blocksize=6000, samplerate=48000, dtype='float32')
    music_stream.start()
    out = ffmpeg.input(filename=sound.path).output('-', format='f32le', acodec='pcm_f32le', ac=1, ar='48000').overwrite_output().run(capture_stdout=True, capture_stderr=False)
    audio_data = np.frombuffer(out[0], dtype=np.float32)

    blocks = len(audio_data) // music_stream.blocksize
    block = 0
    print(f"Blocks: {blocks}", file=sys.stderr)
    try:
        while music_stream.active:
            while paused:
                print("Paused", file=sys.stderr)
                time.sleep(0.2)
            if len(audio_data) == 0:
                music_stream.stop()
                music_stream = None
            music_stream.write(audio_data[block * music_stream.blocksize:(block + 1) * music_stream.blocksize] * music_volume)
            print(f"Block {block} of {blocks}", file=sys.stderr)
            block += 1
            if block >= blocks:
                music_stream.stop()
                music_stream = None
    except Exception as e:
        print(f"Sound Stopped")
        return {'success': True}
    
    print("Sound finished", file=sys.stderr)
    return {'success': True}

if __name__ == "__main__":
    start_api()