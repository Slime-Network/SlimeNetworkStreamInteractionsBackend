import random
import sqlite3
from threading import Timer
import time
import mido
import json

import requests

db = sqlite3.connect("midi.db", check_same_thread=False)

class KeyMapping():
    def __init__(self, **kwargs):
        self.note = kwargs.get("note")
        self.name = kwargs.get("name")
        self.type = kwargs.get("type")
        self.action = kwargs.get("action")
        self.sources = kwargs.get("sources")
        self.selection = kwargs.get("selection")

    def __str__(self):
        return f"Note: {self.note}, Name: {self.name}, Type: {self.type}, Action: {self.action}, Sources: {self.sources}, Selection: {self.selection}"

    def __repr__(self):
        return f"Note: {self.note}, Name: {self.name}, Type: {self.type}, Action: {self.action}, Sources: {self.sources}, Selection: {self.selection}"

class ControlMapping():
    def __init__(self, **kwargs):
        self.control = kwargs.get("control")
        self.name = kwargs.get("name")

    def __str__(self):
        return f"Control: {self.control}, Name: {self.name}"

    def __repr__(self):
        return f"Control: {self.control}, Name: {self.name}"

class MidiSoundBoard():

    def __init__(self, **kwargs):
        self.config = kwargs

        c = db.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS midi_control_mappings
             (control integer PRIMARY KEY, name text)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS midi_key_mappings
            (note integer PRIMARY KEY, name text, type text, action text, sources json, selection text)''')

        db.commit()

        controls = c.execute("SELECT * FROM midi_control_mappings").fetchall()
        keys = c.execute("SELECT * FROM midi_key_mappings").fetchall()
        self.keys = {}
        self.controls = {}
        for control in controls:
            self.controls[control[0]] = ControlMapping(control=control[0], name=control[1])
        for key in keys:
            self.keys[key[0]] = KeyMapping(note=key[0], name=key[1], type=key[2], action=key[3], sources=key[4], selection=key[5])

        self.in_port = 1

        print(f"Input Port: {self.in_port} {mido.get_input_names()}")

        self.input_device = mido.get_input_names()[self.in_port]
        print(f"Starting Midi Controller...\nInput device: {self.input_device}")

        self.tick_delay = 10
        self.tick_timer = Timer(self.tick_delay, self.tick)
        self.minimum_tick_delay = 5

        self.holding = False

    def tick(self):
        self.tick_timer = Timer(self.tick_delay, self.tick)
        if not self.holding:
            response = requests.post("http://127.0.0.1:5275/updateTick", json={}, headers={"Content-Type": "application/json"})
        self.tick_timer.start()

    def hold_ai(self, key_map, message):
        try:
            print(f"hold ai: {key_map, message}")
            if key_map["action"] == "toggle":
                if message.type == "note_on":
                    url = "http://127.0.0.1:5275/hold"
                    payload = {
                        "hold": "toggle"
                    }
                    headers = {
                        "Content-Type": "application/json"
                    }
                    response = requests.post(url, json=payload, headers=headers)
                    print(f"Holding AI: {response.status_code}")
            elif key_map["action"] == "hold":
                if message.type == "note_on":
                    url = "http://127.0.0.1:5275/hold"
                    payload = {
                        "hold": "true"
                    }
                    headers = {
                        "Content-Type": "application/json"
                    }
                    response = requests.post(url, json=payload, headers=headers)
                elif message.type == "note_off":
                    url = "http://127.0.0.1:5275/hold"
                    payload = {
                        "hold": "false"
                    }
                    headers = {
                        "Content-Type": "application/json"
                    }
                    response = requests.post(url, json=payload, headers=headers)
                    response = requests.post("http://127.0.0.1:5275/updateTick", json={}, headers={"Content-Type": "application/json"})
        except Exception as e:
            print(f"Error: {e}")

    def shush(self, key_map, message):
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
            url = "http://127.0.0.1:5275/volume"
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
            

    def start(self):
        self.tick_timer.start()
        while True:
            with mido.open_input(self.input_device) as port:
                print(f"Opened port: {port}\n******************************************************************************")
                for message in port:
                    self.send_midi(message)
                    print(f"Message: {message}")
                    if message.type == "note_on" or message.type == "note_off":
                        key_map = self.keys.get(str(message.note))
                        if key_map is None:
                            continue

                        print(f"Key Map: {key_map}")
                        if key_map.type == "play":
                            self.play(key_map, message)

                        elif key_map.type == "hold":
                            print("Holding")

                        elif key_map.type == "hold ai":
                            print("Holding AI")
                            self.hold_ai(key_map, message)

                        elif key_map.type == "shush":
                            print("Shushing")
                            self.shush(key_map, message)
                        
                        elif key_map.type == "recalibrate":
                            print("Recalibrating")
                            self.recalibrate()

                        
                    elif message.type == "control_change":
                        control_map = self.controls.get(str(message.control))

                        if control_map is None:
                            continue

                        if control_map.name == "speed":
                            self.change_speed(message.value / 127 * 2)
                            print("Speed")
                        elif control_map.name == "pitch":
                            self.change_pitch(message.value / 127)
                            print("Pitch")
                        elif control_map.name == "volume":
                            self.change_volume(message.value / 127)
                            print("Volume")
                        elif control_map.name == "frequency":
                            print("Frequency: {}".format(message.value))
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

                    else:
                        print(f"Unknown message type: {message}")
                
                

def start_midi_controller(**kwargs):
    midi_sound_board = MidiSoundBoard(**kwargs)
    midi_sound_board.start()

if __name__ == "__main__":
    try:
        config = {}
        with open("config.json") as file:
            config = json.load(file)
        print("Starting Midi Sound Board")
        print(json.dumps(config, indent=4))
        midi_sound_board = MidiSoundBoard(config=config)
        print("Starting Sound Board")
        midi_sound_board.start()

        while True:
            time.sleep(100)

    except KeyboardInterrupt:
        print("Stopping Voice Input")
    finally:
        exit()


