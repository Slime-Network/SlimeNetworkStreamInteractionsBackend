import multiprocessing
import json
import time
from live_asr import LiveWav2Vec2

import requests

from midi_controller import start_midi_controller
from api import start_api
from twitch_events import twitch_events

import warnings
import sys
import threading
warnings.filterwarnings("ignore", category=DeprecationWarning) 

def post_text(text):
    print(f"Posting text: {text}")
    url = "http://127.0.0.1:5275/speak"
    payload = {
        "character": "slimenetwork",
        "message": text,
        "source": "slimenetwork"
    }
    headers = {
        "Content-Type": "application/json"
    }
    requests.post(url, json=payload, headers=headers)


def microphone_thread():
    voice_recognition_process = LiveWav2Vec2("facebook/wav2vec2-large-960h-lv60-self", device_name="SteelSeries Arctis")
    voice_recognition_process.start()
    print("Voice Recognition Running...")
    
    while True:
        text, sample_length, inference_time, confidence = voice_recognition_process.get_last_text()
        print(f"Mic: {text}%\t{(confidence*100):.1f}")

        if text and confidence > 0.7:
            thread = threading.Thread(target=post_text, args=(text,))
            thread.start()

def desktop_audio_thread():
    desktop_voice_recognition_process = LiveWav2Vec2("facebook/wav2vec2-large-960h-lv60-self")
    desktop_voice_recognition_process.start()
    print("Desktop Audio Voice Recognition Running...")

    while True:
        text, sample_length, inference_time, confidence = desktop_voice_recognition_process.get_last_text()
        print(f"Audio: {text}%\t{(confidence*100):.1f}")

        if text and confidence > 0.7:
            thread = threading.Thread(target=post_text, args=(text,))
            thread.start()

def main():
    config = {}
    with open("config.json") as file:
        config = json.load(file)
        if len(sys.argv) > 1 and sys.argv[1] == "--no-ai":
            config["runAI"] = False
        print("""
******************************************************************************
   #####                                          #                           
  #     # ##### #####  ######   ##   #    #      # #   #    # #####  #  ####  
  #         #   #    # #       #  #  ##  ##     #   #  #    # #    # # #    # 
   #####    #   #    # #####  #    # # ## #    #     # #    # #    # # #    # 
        #   #   #####  #      ###### #    #    ####### #    # #    # # #    # 
  #     #   #   #   #  #      #    # #    #    #     # #    # #    # # #    # 
   #####    #   #    # ###### #    # #    #    #     #  ####  #####  #  ####  
******************************************************************************""")
        configCopy = config.copy()
        configCopy["app_secret"] = "**********"
        configCopy["twitch_token"] = "**********"
        print(json.dumps(configCopy, indent=4))
        print("""******************************************************************************""")
        try:
            multiprocessing.set_start_method('spawn')
            api_process = multiprocessing.Process(target=start_api, kwargs=(config))
            api_process.start()
            print("API Running...")
            
            twitch_events_process = multiprocessing.Process(target=twitch_events, kwargs=(config))
            twitch_events_process.start()
            print("Twitch Events Running...")

            midi_process = multiprocessing.Process(target=start_midi_controller, kwargs=(config))
            midi_process.start()
            print("Midi Controller Running...")


            threading.Thread(target=microphone_thread).start()
            # threading.Thread(target=desktop_audio_thread).start()

            while True:
                time.sleep(1)

        except Exception as e:
            print(f"Error: {e}")
        finally:
            twitch_events_process.terminate()
            api_process.terminate()
            api_process.join()
            exit()


if __name__ == "__main__":
    main()