from concurrent.futures import thread
import multiprocessing
import json
import time
from live_asr import LiveWhisper

import requests

from api import start_api
from twitch_events import twitch_events

import warnings
import sys
import threading

from utils import replace_all_voice, init_db, init_stream_db
warnings.filterwarnings("ignore", category=DeprecationWarning) 

def post_text(text):
    url = "http://127.0.0.1:5275/speak"
    payload = {
        "character": "",
        "message": text,
        "source": "voice"
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        requests.post(url, json=payload, headers=headers)
    except requests.exceptions.RequestException as e:
        print(f"Error posting text: {e}")

def microphone_thread():
    voice_recognition_process = LiveWhisper("large-v3-turbo", device_name="SteelSeries Arctis")
    voice_recognition_process.start()
    print("Voice Recognition Running...")
    
    while True:
        text, inference_time = voice_recognition_process.get_last_text()
        if isinstance(text, str) and text:
            text = replace_all_voice(text)
            thread = threading.Thread(target=post_text, args=(text,))
            thread.start()

def desktop_audio_thread():
    desktop_voice_recognition_process = LiveWhisper("large-v3-turbo")
    desktop_voice_recognition_process.start()
    print("Desktop Audio Voice Recognition Running...")

    while True:
        text, confidence = desktop_voice_recognition_process.get_last_text()
        print(f"Audio: {text}%\t{(confidence*100):.1f}")

        if text and confidence > 0.7:
            thread = threading.Thread(target=post_text, args=(text,))
            thread.start()

def main():
    config = {}
    init_stream_db()
    init_db()

    with open("config.json") as file:
        config = json.load(file)
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                if arg == "--no-ai":
                    config["runAI"] = False
                elif arg == "--no-history":
                    config["noHistory"] = True
                elif arg == "--no-vision":
                    config["runVision"] = False
                elif arg == "--no-social":
                    config["runSocial"] = False
        print("""
****************************************************************************
   #####                                          #                           
  #     # ##### #####  ######   ##   #    #      # #   #    # #####  #  ####  
  #         #   #    # #       #  #  ##  ##     #   #  #    # #    # # #    # 
   #####    #   #    # #####  #    # # ## #    #     # #    # #    # # #    # 
        #   #   #####  #      ###### #    #    ####### #    # #    # # #    # 
  #     #   #   #   #  #      #    # #    #    #     # #    # #    # # #    # 
   #####    #   #    # ###### #    # #    #    #     #  ####  #####  #  ####  
******************************************************************************""")
        configCopy = config.copy()
        # configCopy["app_secret"] = "**********"
        # configCopy["twitch_token"] = "**********"
        # print(json.dumps(configCopy, indent=4))
        print("""******************************************************************************""")
        try:
            multiprocessing.set_start_method('spawn')
            api_process = multiprocessing.Process(target=start_api, kwargs=(config))
            api_process.start()
            print("API Running...")
            
            twitch_events_process = multiprocessing.Process(target=twitch_events, kwargs=(config))
            twitch_events_process.start()
            print("Twitch Events Running...")

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