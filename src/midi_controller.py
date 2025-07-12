import os
import sqlite3
import sys
from threading import Timer
import threading
import time
import mido
import json

import requests

resources = os.path.dirname(__file__) + "/../resources/"
if hasattr(sys, "_MEIPASS"):
    resources = "../resources/"

class MidiDevice():
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.doesTick = kwargs.get("doesTick")
        self.port = kwargs.get("port")

    def __str__(self):
        return f"Name: {self.name}, Port: {self.port}, Does Tick: {self.doesTick}"

    def __repr__(self):
        return f"Name: {self.name}, Port: {self.port}, Does Tick: {self.doesTick}"

class MidiMapping():
    def __init__(self, **kwargs):
        self.note = kwargs.get("note")
        self.control = kwargs.get("control")
        self.name = kwargs.get("name")
        self.type = kwargs.get("type")
        self.action = kwargs.get("action")
        self.sources = kwargs.get("sources")
        self.selection = kwargs.get("selection")
        self.inverted = kwargs.get("inverted", False)

    def __str__(self):
        return f"Note: {self.note}, control: {self.control}, Name: {self.name}, Type: {self.type}, Action: {self.action}, Sources: {self.sources}, Selection: {self.selection}"

    def __repr__(self):
        return f"Note: {self.note}, control: {self.control}, Name: {self.name}, Type: {self.type}, Action: {self.action}, Sources: {self.sources}, Selection: {self.selection}"


class MidiSoundBoard():

    def __init__(self, device):
        self.input_device = device
        self.load_mappings()
        print(f"Starting Midi Controller...")

        self.tick_delay = 10
        if self.input_device.doesTick:
            self.tick_timer = Timer(self.tick_delay, self.tick)
            self.minimum_tick_delay = 1

        self.holding = False

    def load_mappings(self):
        db = sqlite3.connect(resources + "stream.db", check_same_thread=False)
        c = db.cursor()
        mappings = c.execute("SELECT * FROM midi_mappings").fetchall()
        self.mappings = {}
        for mapping in mappings:
            if (mapping[1] == -1):
                self.mappings[f"note: {mapping[0]}"] = MidiMapping(note=mapping[0], control=mapping[1], name=mapping[2], type=mapping[3], action=mapping[4], sources=json.loads(mapping[5]), selection=mapping[6], inverted=bool(mapping[7]))
            else:
                self.mappings[f"control: {mapping[1]}"] = MidiMapping(note=mapping[0], control=mapping[1], name=mapping[2], type=mapping[3], action=mapping[4], sources=json.loads(mapping[5]), selection=mapping[6], inverted=bool(mapping[7]))

    def tick(self):
        self.tick_timer = Timer(self.tick_delay, self.tick)
        if not self.holding:
            response = requests.post("http://127.0.0.1:5275/updateTick", json={}, headers={"Content-Type": "application/json"})
        self.tick_timer.start()

    def ai_enabled(self, mapping: MidiMapping, message):
        try:
            if mapping.note == -1:
                url = "http://127.0.0.1:5275/AI"
                payload = {
                    "action": "control",
                    "value":  message.value,
                    "inverted": True
                }
                headers = {
                    "Content-Type": "application/json"
                }
                response = requests.post(url, json=payload, headers=headers)
                print(f"Control AI: {response.status_code}")

            if mapping.action == "toggle":
                if message.type == "note_on":
                    url = "http://127.0.0.1:5275/AI"
                    payload = {
                        "action": "toggle",
                        "value": True
                    }
                    headers = {
                        "Content-Type": "application/json"
                    }
                    response = requests.post(url, json=payload, headers=headers)
                    print(f"Toggle AI: {response.status_code}")
            elif mapping.action == "hold":
                if message.type == "note_on":
                    url = "http://127.0.0.1:5275/AI"
                    payload = {
                        "action": "hold",
                        "value": not mapping.inverted
                    }
                    headers = {
                        "Content-Type": "application/json"
                    }
                    response = requests.post(url, json=payload, headers=headers)
                elif message.type == "note_off":
                    url = "http://127.0.0.1:5275/AI"
                    payload = {
                        "action": "release",
                        "value": False
                    }
                    headers = {
                        "Content-Type": "application/json"
                    }
                    response = requests.post(url, json=payload, headers=headers)
                    response = requests.post("http://127.0.0.1:5275/updateTick", json={}, headers={"Content-Type": "application/json"})
        except Exception as e:
            print(f"Error: {e}")

    def ai_hearing_enabled(self, mapping: MidiMapping, message):
        try:
            if mapping.note == -1:
                url = "http://127.0.0.1:5275/AIHearing"
                payload = {
                    "action": "control",
                    "value":  message.value,
                    "inverted": True
                }
                headers = {
                    "Content-Type": "application/json"
                }
                response = requests.post(url, json=payload, headers=headers)
                print(f"Control AI Hearing: {response.status_code}")
            if mapping.action == "toggle":
                if message.type == "note_on":
                    url = "http://127.0.0.1:5275/AIHearing"
                    payload = {
                        "action": "toggle",
                        "value": True
                    }
                    headers = {
                        "Content-Type": "application/json"
                    }
                    response = requests.post(url, json=payload, headers=headers)
                    print(f"Toggle AI: {response.status_code}")
            elif mapping.action == "hold":
                if message.type == "note_on":
                    url = "http://127.0.0.1:5275/AIHearing"
                    payload = {
                        "action": "hold",
                        "value": True
                    }
                    headers = {
                        "Content-Type": "application/json"
                    }
                    response = requests.post(url, json=payload, headers=headers)
                elif message.type == "note_off":
                    url = "http://127.0.0.1:5275/AIHearing"
                    payload = {
                        "action": "release",
                        "value": False
                    }
                    headers = {
                        "Content-Type": "application/json"
                    }
                    response = requests.post(url, json=payload, headers=headers)
                    response = requests.post("http://127.0.0.1:5275/updateTick", json={}, headers={"Content-Type": "application/json"})
        except Exception as e:
            print(f"Error: {e}")

    def shush(self, mapping: MidiMapping, message):
        try:
            if message.type == "note_on":
                url = "http://127.0.0.1:5275/shush"
                payload = {}
                headers = {
                    "Content-Type": "application/json"
                }
                response = requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Error: {e}")

    def change_pitch(self, pitch):
        try:
            url = "http://127.0.0.1:5275/pitch"
            payload = {"pitch": pitch}
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Error: {e}")

    def change_speed(self, speed):
        try:
            url = "http://127.0.0.1:5275/speed"
            payload = {"speed": speed}
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Error: {e}")

    def change_volume(self, volume):
        try:
            url = "http://127.0.0.1:5275/voiceVolume"
            payload = {"volume": volume}
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Error: {e}")

    def change_music_volume(self, volume):
        try:
            url = "http://127.0.0.1:5275/musicVolume"
            payload = {"volume": volume}
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Error: {e}")

    def change_sound_volume(self, volume):
        try:
            url = "http://127.0.0.1:5275/soundVolume"
            payload = {"volume": volume}
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Error: {e}")

    def recalibrate(self):
        try:
            url = "http://127.0.0.1:5275/recalibrate"
            payload = {}
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Error: {e}")

    def send_midi(self, message):
        try:
            print(f"Sending midi: {message}")
            url = "http://127.0.0.1:5275/midi"
            payload = {"key": None if message.type != "note_on" else message.note, "control": None if message.type != "control_change" else message.control}
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Error: {e}")
    
    def play(self, mapping: MidiMapping, message):
        try:
            if mapping.action == "Press":
                if message.type == "note_on":
                    url = "http://127.0.0.1:5275/playSound"
                    payload = {
                        "sounds": mapping.sources,
                        "selection": mapping.selection
                    }
                    headers = {
                        "Content-Type": "application/json"
                    }

                    print(f"Playing: {mapping}")
                    response = requests.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Error: {e}")

    def start(self):
        if self.input_device.doesTick:
            self.tick_timer.start()
        while True:
            with mido.open_input(self.input_device.name) as port:
                print(f"Opened port: {port}\n******************************************************************************")
                for message in port:
                    self.send_midi(message)
                    if message.type == "note_on" or message.type == "note_off":
                        mapping = self.mappings.get(f"note: {message.note}", None)
                        if mapping is None:
                            continue

                        print(f"Key Map: {mapping}")
                        if mapping.type == "Play":
                            self.play(mapping, message)

                        elif mapping.type == "AI Enabled":
                            print("Holding AI")
                            self.hold_ai(mapping, message)

                        elif mapping.type == "Shush":
                            print("Shushing")
                            self.shush(mapping, message)
                        
                        elif mapping.type == "Recalibrate":
                            print("Recalibrating")
                            self.recalibrate()

                    elif message.type == "control_change":
                        control_map = self.mappings.get(f"control: {message.control}", None)
                        if control_map is None:
                            continue
                        if control_map.type == "Voice Speed":
                            self.change_speed(message.value / 127 * 2)
                        elif control_map.type == "Voice Pitch":
                            self.change_pitch(message.value / 127)
                        elif control_map.type == "Voice Volume":
                            self.change_volume(message.value / 127)
                        elif control_map.type == "Music Volume":
                            self.change_music_volume(message.value / 127)
                        elif control_map.type == "Sound Volume":
                            self.change_sound_volume(message.value / 127)
                        elif control_map.type == "Enable AI":
                                self.ai_enabled(control_map, message)
                        elif control_map.type == "Enable AI Hearing":
                                self.ai_hearing_enabled(control_map, message)
                        elif control_map.type == "Tick Frequency":
                            if self.input_device.doesTick:
                                self.tick_delay = max(message.value/2, self.minimum_tick_delay)
                                print(f"New delay: {self.tick_delay}")
                                self.tick_timer.cancel()
                                self.tick_timer = Timer(self.tick_delay, self.tick)
                                self.tick_timer.start()

                    elif message.type == "program_change":
                        print(f"Program Change")

                    elif message.type == "pitchwheel":
                        print(f"Pitch Wheel: {message.pitch}")
                        self.change_pitch(message.pitch )

                    elif message.type == "sysex":
                        print("System Exclusive")

                    elif message.type == "timing_clock":
                        print("Timing Clock")

                    elif message.type == "start":
                        print("Start")

                    elif message.type == "continue":
                        print("Continue")

                    elif message.type == "stop":
                        print("Stop")

                    elif message.type == "active_sensing":
                        print("Active Sensing")

                    elif message.type == "reset":
                        print("System Reset")
                    elif message.type == "aftertouch":
                        pass
                    elif message.type == "sustain":
                        print("Sustain")
                    else:
                        print(f"Unknown message type: {message}")


def start_midi_controller(**kwargs):
    print(f"Input devices: {mido.get_input_names()}")
    devices = mido.get_input_names()
    for i, device in enumerate(devices):
        print(f"{i}: {device}")
        if i == 0:
            continue
        midi_sound_board = MidiSoundBoard(device=MidiDevice(name=device, doesTick=True))
        threading.Thread(target=midi_sound_board.start, daemon=True).start()
        print(f"Started Midi Sound Board for {device}")
    
    while True:
        time.sleep(100)

# if __name__ == "__main__":
#     try:
#         config = {}
#         with open("config.json") as file:
#             config = json.load(file)
#         print("Starting Midi Sound Board")
#         print(json.dumps(config, indent=4))
#         midi_sound_board = MidiSoundBoard(config=config)
#         print("Starting Sound Board")
#         midi_sound_board.start()

#         while True:
#             time.sleep(100)

#     except KeyboardInterrupt:
#         print("Stopping Voice Input")
#     finally:
#         exit()


