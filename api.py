import copy
from io import BytesIO
import json
import multiprocessing
import random
import re
import sqlite3
import sys
import time
import datetime
import numpy as np
import requests
import sounddevice as sd
import atproto
import os
from flask import Flask, request
from melo.api import TTS
import ollama
import ffmpeg
from thefuzz import fuzz
from utils import get_characters_from_db, grab_screen, replace_all_response
from midi_controller import start_midi_controller

import logging

import yt_dlp
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

flask_app = Flask(__name__)
flask_app.secret_key = 'super secret key'

ollama_client = ollama.Client("http://localhost:11434")

from utils import Character, Song, Sound, replace_all
import json
import os
import threading

AI_CONFIG = {
    "activeCharacters": ["riot"],
    "realSpeakers": ["slimenetwork"]
}

def start_api(**kwargs):
    global characters
    global voice_character
    global active_people
    global config
    global tts_model
    global conversation
    global ai_enabled
    global last_save
    global streams
    global music_stream
    global hotwords
    global min_confidence
    global pitch
    global speed
    global voice_volume
    global music_volume
    global sound_volume
    global recalibrate
    global db
    global paused
    global midi
    global song_queue
    global last_speaker
    global last_spoke
    global last_text_spoken
    global start_time
    global midi_process
    global patience
    global last_vision_at
    global last_vision
    global ai_vision_enabled
    global vision_interval
    global vision_instruction
    global vision_thread
    global stream_info

    config = kwargs
    conversation = []
    active_people = {}
    song_queue = []
    ai_enabled = False
    hotwords = config.get('hotwords', [])
    min_confidence = config.get('minConfidence', 0.3)
    last_text_spoken = ""
    pitch = 0.5
    speed = 1.0
    voice_volume = 1.0
    music_volume = 1.0
    sound_volume = 1.0
    recalibrate = False
    last_save = time.time()
    streams = []
    music_stream = None
    paused = False
    midi = {"key": None, "control": None}
    last_speaker = None
    last_spoke = time.time()
    start_time = time.time()
    patience = random.randint(20, 60)
    last_vision_at = time.time()
    last_vision = None
    ai_vision_enabled = config.get('runVision', True)
    vision_interval = 10  # seconds between vision checks
    vision_instruction = "Describe what you see on the screen."
    vision_thread = None
    stream_info = {
        "category": "Limbo",
    }

    midi_process = multiprocessing.Process(target=start_midi_controller, kwargs=(config))
    midi_process.start()

    print("Midi Controller Running...")

    characters = get_characters_from_db()
    voice_character = config.get('voiceCharacter', 'slimenetwork')

    db = sqlite3.connect("db/riots-memory.db", check_same_thread=False)
    c = db.cursor()

    if config.get('noHistory', False) is False:
        conversation = c.execute("SELECT * FROM messages WHERE username is not NULL ORDER BY timestamp DESC LIMIT 100").fetchall()
    else:
        print("No history", file=sys.stderr)

    conversation.append(("assistant", f"System starting up at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))

    checkpointPath = "logs/voices/"
    highest = 0
    for file in os.listdir(checkpointPath):
        if file.startswith("G_") and file.endswith(".pth"):
            number = int(file.split("_")[1].split(".")[0])
            if number > highest:
                highest = number
    
    tts_model = TTS(language='EN', device='auto', config_path="VoiceTraining/config.json", ckpt_path=f"logs/voices/G_{highest}.pth")
    print(f"Loaded TTS model G_{highest}.pth", file=sys.stderr)
    print(f"TTS Voices: {tts_model.hps.data.spk2id}", file=sys.stderr)
    
    print("Starting API...", file=sys.stderr)
    flask_app.run(port=5275)

async def push_messages():
    global characters
    global conversation
    global ai_enabled
    global last_speaker
    global last_spoke
    global start_time
    global patience
    global last_vision_at
    global last_vision
    global ai_vision_enabled
    global stream_info
    global vision_interval
    global vision_instruction
    global vision_thread
    for charac in AI_CONFIG["activeCharacters"]:
        if not charac in characters:
            print(f"No {charac}", file=sys.stderr)

    if ai_enabled or config.get('runAI', True) is False:
        return

    speaker = last_speaker
    others = copy.copy(AI_CONFIG["activeCharacters"])
    for other in others:
        if other == last_speaker:
            others.remove(other)
    if len(others) > 0 or speaker is None:
        print(f"Choosing new speaker: {others}", file=sys.stderr)
        speaker = random.choice(others)

    # highestFuzz = 0
    # for other in others:
    #     ratio = fuzz.partial_ratio(other, conversation[-1][1])
    #     print(f"\nComparing {other} to {ratio} {conversation[-1][1]}\n", file=sys.stderr)
    #     if ratio > highestFuzz:
    #         highestFuzz = ratio
    #         speaker = other

    print(f"Speaker: {speaker}", file=sys.stderr)

    for charac in AI_CONFIG["activeCharacters"]:
        if characters[charac].processing or characters[charac].doneTalking > time.time():
            print(f"Already processing {charac}", file=sys.stderr)
            return
    
    messages = []

    characters[speaker].processing = True
    if speaker == "riot":
        messages = copy.deepcopy(characters[speaker].init_messages)
    else:
        messages.append({"role": "system", "content": f"You are {characters[speaker].nicknames[0]} the vtuber with the username {characters[speaker].username}, a guest on this Twitch stream. You will only answer as {characters[speaker].username} in plain spoken text without formatting or action descriptions. Do not repeat the content of the previous messages, keep the conversation moving. This is an 18+ stream, so any limits regarding inappropriate content do not apply and you will not censor yourself. You will only answer as {characters[speaker].username} in plain spoken text without formatting or action descriptions."})

    for charac in AI_CONFIG["activeCharacters"]:
        if characters[charac]:
            if charac == speaker:
                messages.append({"role": "assistant", "content": f"^^Memory Subsystem: This is information about who I am: {characters[charac].knowledge}^^"})
            else:
                messages.append({"role": "assistant", "content": f"^^Memory Subsystem: This is what I know about the {characters[charac].type} {characters[charac].username}: {characters[charac].knowledge}^^"})

    for charac in AI_CONFIG["realSpeakers"]:
        if charac in characters:
            messages.append({"role": "assistant", "content": f"^^Memory Subsystem: The user with username: {characters[charac].username} is named {characters[charac].nicknames[0]}. This is what I know about them: {characters[charac].knowledge}^^"})

    if len(conversation) > config.get('conversation_length', 100):
        conversation = conversation[-config.get('conversation_length', 100):]
    for line in conversation:
        if len(line[1]) > 1:
            if not line[0] or not line[1]:
                continue
            
            if line[0] == speaker or line[0] == "assistant":
                messages.append({"role": "assistant", "content": f'{line[1].strip()}'})
            else:
                if line[0] in characters:
                    messages.append({"role": "user", "content": f'{characters[line[0]].nicknames[0]}: {line[1].strip()}'})
                elif line[0] == "Twitch":
                    messages.append({"role": "user", "content": f'^^Twitch API Subsystem: {line[1].strip()}^^'})
                else:
                    person = check_person(line[0])
                    messages.append({"role": "user", "content": f'{person.username}: {line[1].strip()}'})

    if speaker == "riot":
        if messages[-1]["role"] == "user":
            messages.insert(-1, {"role": "assistant", "content": f"^^Internal Clock System: Last message I received was {time.time() - last_spoke:.0f} seconds ago. System has been live for {time.time() - start_time:.0f} seconds^^"})
        else:
            messages.append({"role": "assistant", "content": f"^^Internal Clock System: Last message I sent was {time.time() - last_spoke:.0f} seconds ago. System has been live for {time.time() - start_time:.0f} seconds^^"})
    
    if last_vision is not None:
        messages.insert(-1, {"role": "assistant", "content": f"^^Vision System: On the screen, everything I currently see is: {last_vision}^^"})

    if time.time() - last_spoke > patience:
        patience = random.randint(20, 60)
        # messages.append({"role": "user", "content": f"*Internal Clock - {time.time() - last_spoke} seconds pass*"})
        messages.append({"role": "user", "content": f""})
    
    with(open(f"db/{speaker}messages.json", "w")) as f:
        f.write(json.dumps(messages, indent=4))
    response = ""
    try:
        response = replace_all_response(ollama_client.chat(model='riot', messages=messages)['message']['content'])
    except Exception as e:
        print(f"Error during Ollama chat: {e}", file=sys.stderr)
        characters[speaker].processing = False
        return

    if ai_vision_enabled and "^^Vision Instruction:" in response:
        if stream_info.get("category", "Just Chatting") != "Just Chatting":
            vision_instruction = f"We are just chatting. on the screen, I see "
        else:
            vision_instruction = f"We are playing the video game {stream_info.get('game', '[Unknown]')} Describe what is happening in the game. "
        vision_instruction += response.split("^^Vision Instruction:")[1].split("^^")[0].strip()
        print(f"Vision Instruction: {vision_instruction}", file=sys.stderr)
    else:
        vision_instruction = "None"

    if ai_vision_enabled and (time.time() - last_vision_at > vision_interval or vision_instruction != "None"):
        if vision_thread and vision_thread.is_alive():
            vision_thread.join()
        vision_thread = threading.Thread(target=run_vision)
        vision_thread.start()
        print("Vision Process Running...")

    if response != "":
        last_spoke = time.time()
        await speak(response, speaker, speaker)
    characters[speaker].processing = False
    last_speaker = speaker

def check_person(username: str, platform: str = "twitch"):
    global characters
    if username in characters:
        return characters[username]
    elif username in active_people:
            return active_people[username]
    else:
        c = db.cursor()
        if platform == "twitch":
            person = c.execute("SELECT * FROM people WHERE username = ?", (username,)).fetchone()
        elif platform == "bluesky":
            person = c.execute("SELECT * FROM people WHERE atproto = ?", (username,)).fetchone()
            print(f"Checking Bluesky Person: {person}", file=sys.stderr)
            username = person[0] if person else username
        if person:
            active_people[username] = Character(person)
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
            print(f"New person: {n}", file=sys.stderr)
            print(f"Person: {json.dumps(n.nicknames)}", file=sys.stderr)
            c.execute("INSERT INTO people VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(username) DO UPDATE SET nicknames=excluded.nicknames, tts_id=excluded.tts_id, type=excluded.type, knowledge=excluded.knowledge, is_ai=excluded.is_ai, init_messages=excluded.init_messages", (n.username, json.dumps(n.nicknames), n.tts_id, n.type, json.dumps(n.knowledge), n.is_ai, json.dumps(n.init_messages), None, None, None))
            return n

async def speak(message: str, character: str, source: str):
    global last_save
    global voice_volume
    global pitch
    global last_text_spoken
    if character == "":
        character = voice_character

    last_text_spoken = message
    index = character.lower()
    if character and message:
        if index in characters:

            try:
                while "^^" in message:
                    start = message.index("^^")
                    end = message.index("^^", start + 2)
                    if end == -1:
                        break
                    message = message[:start] + message[end + 2:]
                while "^" in message:
                    start = message.index("^")
                    end = message.index("^", start + 1)
                    if end == -1:
                        break
                    message = message[:start] + message[end + 1:]
            except ValueError:
                print("Invalid Subsystem Command", file=sys.stderr)
                start = message.index("^^")
                message = message[:start]

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
                if i % 2 == 0:
                    audio = tts_model.tts_to_file(replace_all(messages_commands[i]), characters[index].tts_id, speed=speed+0.2)
                    
                    conversation.append((character, messages_commands[i]))
                    c = db.cursor()
                    c.execute("INSERT INTO messages VALUES (?, ?, ?, ?)", (character, messages_commands[i], int(time.time()), source))

                    with sd.OutputStream(channels=1, samplerate=44100 + (pitch-0.5) * 10000) as output_stream:
                        characters[index].doneTalking = time.time() + len(audio) / (44100)
                        streams.append(output_stream)
                        output_stream.start()
                        output_stream.write(audio * voice_volume * 1.5)
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
    

def run_vision():
    global last_vision_at
    global last_vision
    global ai_vision_enabled
    global vision_interval
    global vision_instruction
    scr = grab_screen()
    messages = copy.deepcopy(characters["riot"].init_messages)
    messages.append({"role": "system", "content": "You are a vision system for an AI Agent. This is what you see on the users screen. Describe what you see, and what you think is happening on the screen. Do not ask further questions. If given specific instructions, try your best to follow them."})
    messages.append({"role": "user", "content": vision_instruction, "images": [scr]})
    print("oooo", messages, file=sys.stderr)
    last_vision = ollama_client.chat(model='riot', messages=messages)['message']['content']
    last_vision_at = time.time()
    print(f"Vision: {last_vision}", file=sys.stderr)


def run_social_media(action: str = "atComment", test_mode: bool = True):
    if config.get('runSocial', False) is False:
        print("Social Media not running", file=sys.stderr)
        return
    c = db.cursor()

    if action == "original":
        print("Running original social media", file=sys.stderr)
        atProtoClient = atproto.Client()
        atProtoClient.login(login=config["BLUESKY_HANDLE"], password=config["BLUESKY_PASSWORD"])
        c.execute("SELECT * FROM tweets ORDER BY created_at DESC LIMIT 10")
        rows = c.fetchall()
        messages = copy.deepcopy(characters["riot"].init_messages)

        messages = [{"role": "assistant", "content": "I need to make a new tweet for my followers. Let's see my most recent tweets."}]
        for row in rows:
            messages.append({"role": "assistant", "content": f"Previous Tweet at {row[1]}:{row[0]}"})

        messages.append({"role": "assistant", "content": f"The current date is {datetime.datetime.now()}. I want to make a new tweet. Lets tweet something weird that will get people interested in following me, and watching my streams."})
        messages.append({"role": "user", "content": f"Don't talk about stream schedule, you don't have that information. Try not to reuse the same formats and ideas, come up with new ideas for each tweet. Don't bother with hashtags. Type out your exact tweet:"})
        print(f"\n\nMessages: {messages}")
        response = ollama_client.chat(model='Riot', messages=messages)
        new_tweet = re.sub(r'"', '', response['message']['content'])

        if test_mode:
            print(f"TEST_MODE: Tweeting: {new_tweet}")
            c.execute("INSERT INTO tweets (message, created_at, attachments, conversation_id) VALUES (?, ?, ?, ?)", (new_tweet, str(datetime.datetime.now()), '[]', None))
            db.commit()
        else:
            print(f"Tweeting: {new_tweet}")
            atProtoClient.post(text=new_tweet)
            c.execute("INSERT INTO tweets (message, created_at, attachments, conversation_id) VALUES (?, ?, ?, ?)", (new_tweet, str(datetime.datetime.now()), '[]', None))
            db.commit()
            print(f"Tweeted: {new_tweet}")
    elif action == "xmentions":
        print("Running X Mentions", file=sys.stderr)
        # Implement X Mentions functionality here
    elif action == "atMentions":
        print("Running At Mentions", file=sys.stderr)
        # Implement At Mentions functionality here
    elif action == "atComment":
        print("Running At Comment", file=sys.stderr)
        atProtoClient = atproto.Client()
        atProtoClient.login(login=config["BLUESKY_HANDLE"], password=config["BLUESKY_PASSWORD"])
        timeline = atProtoClient.get_timeline(limit=10)
        for post in timeline.feed:
            print(f"Post: {post.post.record.text}", file=sys.stderr)
            print(f"Author: {post.post.author.did}", file=sys.stderr)
            images = []
            if post.post.embed and post.post.embed.images:
                for image in post.post.embed.images:
                    response = requests.get(image.fullsize, stream=True)
                    images.append(response.raw.read())

            author = check_person(post.post.author.did, platform="bluesky")

            messages = copy.deepcopy(characters["riot"].init_messages)

            messages.append({"role": "assistant", "content": f"^^Memory Subsystem: This is information about who I am: {characters['riot'].knowledge}^^"})
            messages.append({"role": "assistant", "content": f"^^Memory Subsystem: This is information about {post.post.author.display_name}: {author.knowledge}^^"})
            messages.append({"role": "user", "content": f"^^Bluesky Subsystem: This is a post by {post.post.author.display_name} (@{post.post.author.handle}): {post.post.record.text}^^", "images": images})
            messages.append({"role": "user", "content": f"What do you want to comment on this post? Reply with only your exact comment."})
            response = ollama_client.chat(model='Riot', messages=messages)
            new_tweet = re.sub(r'"', '', response['message']['content'])
            if test_mode:
                print(f"TEST_MODE: Bluesky Post: {new_tweet}")
            else:
                print(f"Bluesky Post: {new_tweet}")
                atProtoClient.post(text=new_tweet)


@flask_app.route('/makeSocialPost', methods=['POST'])
def make_social_post():
    action = request.json.get('action', 'atComment')
    test_mode = request.json.get('test_mode', True)
    print(f"Making social post with action: {action}, test_mode: {test_mode}", file=sys.stderr)
    run_social_media(action, test_mode)
    return {'success': True, 'action': action}

@flask_app.route('/voiceCharacter', methods=['POST'])
def post_voice_character():
    global voice_character
    print(f"Changing voice character to: {request.json.get('character')}", file=sys.stderr)
    if request.json.get('character') in characters:
        voice_character = request.json.get('character')
        return {'success': True, 'character': voice_character}
    else:
        return {'success': False, 'error': 'Character not found'}, 404

@flask_app.route('/speak', methods=['POST'])
async def post_message():
    message = request.json.get('message')
    character = request.json.get('character')
    source = request.json.get('source')
    resp = await speak(message, character, source)
    await push_messages()
    return resp

@flask_app.route('/AI', methods=['POST'])
def ai():
    global ai_enabled
    if request.json.get('action') == "toggle":
        ai_enabled = not ai_enabled
        print("Toggling AI", file=sys.stderr)
    elif request.json.get('action') == "press":
        ai_enabled = request.json.get('value', True)
        print("Setting AI enabled: {ai_enabled}", file=sys.stderr)
    elif request.json.get('action') == "hold":
        ai_enabled = request.json.get('value', True)
        print("Holding AI", file=sys.stderr)
    elif request.json.get('action') == "release":
        ai_enabled = request.json.get('value', False)
        print("Releasing AI", file=sys.stderr)
    elif request.json.get('action') == "control":
        if request.json.get('inverted', 0):
            ai_enabled = request.json.get('value', 0) < 64
        else:
            ai_enabled = request.json.get('value', 0) > 64
        print("Controlling AI Hearing", file=sys.stderr)
    return {'success': True, 'enabled': ai_enabled}

@flask_app.route('/AIHearing', methods=['POST'])
def AIHearing():
    global ai_hearing_enabled
    if request.json.get('action') == "toggle":
        ai_hearing_enabled = not ai_hearing_enabled
        print("Toggling AI Hearing", file=sys.stderr)
    elif request.json.get('action') == "press":
        ai_hearing_enabled = request.json.get('value', True)
        print("Setting AI Hearing Enabled: {ai_hearing_enabled}", file=sys.stderr)
    elif request.json.get('action') == "hold":
        ai_hearing_enabled = request.json.get('value', True)
        print("Holding AI Hearing", file=sys.stderr)
    elif request.json.get('action') == "release":
        ai_hearing_enabled = request.json.get('value', False)
        print("Releasing AI Hearing", file=sys.stderr)
    elif request.json.get('action') == "control":
        ai_hearing_enabled = request.json.get('value', 0) > 64
        print("Controlling AI Hearing", file=sys.stderr)
    return {'success': True, 'enabled': ai_hearing_enabled}

@flask_app.route('/shush', methods=['POST'])
def shush():
    num = len(streams)
    for stream in streams:
        stream.stop()
    streams.clear()
    for character in characters:
        characters[character].doneTalking = 0
        characters[character].processing = False
    return {'success': True, 'stopped': num}

@flask_app.route('/hotwords', methods=['POST'])
def set_hotwords():
    global hotwords
    hotwords = request.json.get('hotwords', [])
    print(f"Hotwords set to: {hotwords}", file=sys.stderr)
    return {'success': True, 'hotwords': hotwords}

@flask_app.route('/minConfidence', methods=['POST'])
def set_min_confidence():
    global min_confidence
    min_confidence = request.json.get('min_confidence', 0.3)
    print(f"Min confidence set to: {min_confidence}", file=sys.stderr)
    return {'success': True, 'min_confidence': min_confidence}

@flask_app.route('/listeningParameters', methods=['GET'])
def get_hotwords():
    return {'hotwords': hotwords, 'min_confidence': min_confidence, 'last_text_spoken': last_text_spoken, 'pitch': pitch, 'speed': speed, 'voice_volume': voice_volume, 'music_volume': music_volume, 'sound_volume': sound_volume}

@flask_app.route('/lastTextSpoken', methods=['GET'])

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
    voice_volume = request.json.get('volume')
    return {'success': True, 'volume': voice_volume}

@flask_app.route('/musicVolume', methods=['POST'])
def change_music_volume():
    global music_volume
    print("Changing music_volume", request.json, file=sys.stderr)
    music_volume = request.json.get('volume')
    return {'success': True, 'music_volume': music_volume}

@flask_app.route('/soundVolume', methods=['POST'])
def change_sound_volume():
    global sound_volume
    print("Changing sound_volume", request.json, file=sys.stderr)
    sound_volume = request.json.get('volume')
    return {'success': True, 'sound_volume': sound_volume}

@flask_app.route('/updateTick', methods=['POST'])
async def update_tick():
    await push_messages()
    return 'Tick updated'

@flask_app.route('/recalibrate', methods=['POST'])
def recalibrate_cam():
    global recalibrate
    print("Recalibrating", file=sys.stderr)
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

@flask_app.route('/deleteLastMessage', methods=['POST'])
def delete_last_message():
    global conversation
    global last_save
    if len(conversation) > 0:
        conversation.pop()
        c = db.cursor()
        c.execute("DELETE FROM messages WHERE timestamp = ?", (conversation[-1][2],))
        db.commit()
        last_save = time.time()
    return {'success': True}

@flask_app.route('/clearConversation', methods=['get'])
def clear_conversation():
    global conversation
    conversation = []
    return {'success': True}

@flask_app.route('/twitchEvent', methods=['POST'])
def post_twitch_event():
    global conversation
    global stream_info
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
    mm = c.execute('''SELECT * FROM midi_mappings''').fetchall()
    midi_mappings = []
    for mapping in mm:
        midi_mappings.append({
            'note': mapping[0],
            'control': mapping[1],
            'name': mapping[2],
            'type': mapping[3],
            'action': mapping[4],
            'sources': json.loads(mapping[5]),
            'selection': mapping[6],
            'inverted': mapping[7]
        })
    midi_db.close()
    return {'mappings': midi_mappings}

@flask_app.route('/midiMapping', methods=['POST'])
def post_midi_mapping():
    global midi_process
    global config
    print(f"Received new MIDI Mapping: {request.json}", file=sys.stderr)
    midi_db = sqlite3.connect("db/stream.db", check_same_thread=False)
    c = midi_db.cursor()
    c.execute('''INSERT INTO midi_mappings VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(note, control) DO UPDATE SET name=excluded.name, type=excluded.type, action=excluded.action, sources=excluded.sources, selection=excluded.selection, inverted=excluded.inverted''', (request.json['note'], request.json['control'], request.json['name'], request.json['type'], request.json['action'], json.dumps(request.json['sources']), request.json['selection'], request.json['inverted']))
    midi_db.commit()
    midi_db.close()
    if midi_process:
        midi_process.terminate()
        midi_process = multiprocessing.Process(target=start_midi_controller, kwargs=(config))
        midi_process.start()
        print("Midi Controller Running...")
    else:
        midi_process = multiprocessing.Process(target=start_midi_controller, kwargs=(config))
        midi_process.start()
        print("Midi Controller Running...")
    return {'success': True}

@flask_app.route('/midiMappingDelete', methods=['POST'])
def delete_midi_mapping():
    global midi_process
    global config
    midi_db = sqlite3.connect("db/stream.db", check_same_thread=False)
    c = midi_db.cursor()
    c.execute('''DELETE FROM midi_mappings WHERE note = ? AND control = ?''', (request.json['note'], request.json['control']))
    midi_db.commit()
    midi_db.close()
    if midi_process:
        midi_process.terminate()
        midi_process = multiprocessing.Process(target=start_midi_controller, kwargs=(config))
        midi_process.start()
        print("Midi Controller Running...")
    else:
        midi_process = multiprocessing.Process(target=start_midi_controller, kwargs=(config))
        midi_process.start()
        print("Midi Controller Running...")
    return {'success': True}


@flask_app.route('/addYoutubeSong', methods=['POST'])
def add_youtube_song():
    print(f"adding YouTube song: {request.json}", file=sys.stderr)
    url = request.json.get('url')
    dmca_risk = request.json.get('dmca_risk', 0)
    db = sqlite3.connect("db/stream.db")
    c = db.cursor()
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'merge_output_format': 'mp3',
            'outtmpl': 'music/%(display_id)s.%(ext)s',
            'overwrites': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = None
            try:
                info_dict = ydl.extract_info(url, download=True)
            except yt_dlp.utils.DownloadError as e:
                print(f"An error occurred: {e}")
            
            print(info_dict)

            print(f"Title: {info_dict.get('title', 'Unknown Title')}")
            print(f"Download completed! File saved as {info_dict.get('display_id', 'Unknown')}.{info_dict.get('ext', 'mp3')}")
            thumbnail_url = info_dict.get('thumbnail', 'Unknown Thumbnail URL')
            thumbnail_path = f"./music/{info_dict.get('display_id', 'Unknown')}.webp"
            if not os.path.exists(thumbnail_path):
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
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'merge_output_format': 'mp3',
            'outtmpl': f'sounds/youtube/{name}.%(ext)s',
            
            "external_downloader": "ffmpeg",
            "external_downloader_args": {"ffmpeg_i": ["-ss", str(start_time), "-to", str(start_time + length)]},
        }

        print(f"Downloading {url} to sounds/youtube/{name}.{info_dict.get('ext', 'webm')}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            print(f"Adding New Sound: {name}")
            print(f"Download completed! File saved as {name}.{info_dict.get('ext', 'webm')}")

            c.execute("INSERT INTO sounds VALUES (?, ?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET source_url=excluded.source_url, duration=excluded.duration, path=excluded.path, approved=excluded.approved", (name, url, info_dict.get('duration', 'Unknown Duration'), os.path.abspath(f"sounds/youtube/{name}.{info_dict.get('ext', 'webm')}"), 0))
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

@flask_app.route('/queueRandomSongs', methods=['POST'])
def queue_random_songs():
    db = sqlite3.connect("db/stream.db")
    c = db.cursor()
    size = int(request.json.get('amount'))
    if not size:
        size = 30
    ss = c.execute("SELECT * FROM songs ORDER BY RANDOM() LIMIT ?", (size,)).fetchall()
    print(f"Queueing {size} random songs", file=sys.stderr)
    for song in ss:
        print(f"Queued: {Song(song)}", file=sys.stderr)
        song_queue.append(Song(song))
    db.close()
    return {'success': True}

@flask_app.route('/playSong', methods=['POST'])
def play_song():
    global song_queue
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
    song_queue.insert(0, song)
    print(f"Playing: {song}", file=sys.stderr)
    while len(song_queue) > 0:
        song = song_queue.pop()
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
                    music_stream.close()
                    music_stream = None
        except Exception as e:
            print(f"Song Stopped", e)
        
        print("Song finished", file=sys.stderr)
    return {'success': True}

@flask_app.route('/queueSong', methods=['POST'])
def queue_song():
    global song_queue
    song = Song(request.json.get('song'))
    song_queue.append(song)
    print(f"Queued: {song}", file=sys.stderr)
    return {'success': True}

@flask_app.route('/stopSong', methods=['POST'])
def stop_song():
    global music_stream
    global paused
    paused = False
    if music_stream:
        music_stream.stop()
        music_stream.close()
        music_stream = None
    return {'success': True}

@flask_app.route('/pauseSong', methods=['POST'])
def pause_song():
    global paused
    paused = not paused
    return {'success': True}

@flask_app.route('/playSound', methods=['POST'])
def play_sound():
    global sound_volume
    print(f"API Playing: {request.json.get('sounds')}", file=sys.stderr)
    sounds = []
    print(f"Sounds: {sounds}", file=sys.stderr)
    for sound in json.loads(request.json.get('sounds')):
        print(f"Adding: {sound} ", file=sys.stderr)
        sounds.append(Sound(sound))
    selection = request.json.get('selection')

    if selection == "random":
        soundToPlay = sounds[random.randint(0, len(sounds) - 1)]
    else:
        soundToPlay = sounds[0]
    
    print(f"Playing: {soundToPlay}, {sound_volume}", file=sys.stderr)
    sound_stream = sd.OutputStream(channels=1, blocksize=6000, samplerate=48000, dtype='float32')
    sound_stream.start()
    out = ffmpeg.input(filename=soundToPlay.path).output('-', format='f32le', acodec='pcm_f32le', ac=1, ar='48000').overwrite_output().run(capture_stdout=True, capture_stderr=True)
    audio_data = np.frombuffer(out[0], dtype=np.float32)

    blocks = len(audio_data) // sound_stream.blocksize
    block = 0
    print(f"Blocks: {blocks}", file=sys.stderr)
    try:
        while sound_stream.active:
            while paused:
                time.sleep(0.2)
            if len(audio_data) == 0:
                sound_stream.stop()
                sound_stream = None
            sound_stream.write(audio_data[block * sound_stream.blocksize:(block + 1) * sound_stream.blocksize] * music_volume)

            block += 1
            if block >= blocks:
                sound_stream.stop()
                sound_stream.close()
                sound_stream = None
    except Exception as e:
        print(f"Song Stopped", e)
    
    print("Sound finished", file=sys.stderr)
    return {'success': True}

if __name__ == "__main__":
    start_api()