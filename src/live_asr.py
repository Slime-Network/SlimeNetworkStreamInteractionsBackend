import pyaudio
import webrtcvad
from whisper_inference import WhisperInference
import numpy as np
import threading
import time
from sys import exit
from queue import  Queue
import requests

def quit_function():
    raise TimeoutError(
        f"Timeout.")

class LiveWhisper:
    exit_event = threading.Event()
    def __init__(self, model_name, device_name="default"):
        self.model_name = model_name
        self.device_name = device_name

    def stop(self):
        """stop the asr process"""
        LiveWhisper.exit_event.set()
        self.asr_input_queue.put("close")
        print("asr stopped")

    def start(self):
        """start the asr process"""
        self.asr_output_queue = Queue()
        self.asr_input_queue = Queue()
        self.asr_process = threading.Thread(target=LiveWhisper.asr_process, args=(
            self.model_name, self.asr_input_queue, self.asr_output_queue,))
        self.asr_process.start()
        time.sleep(5)  # start vad after asr model is loaded
        self.vad_process = threading.Thread(target=LiveWhisper.vad_process, args=(
            self.device_name, self.asr_input_queue,))
        self.vad_process.start()

    @staticmethod
    def vad_process(device_name, asr_input_queue):
        vad = webrtcvad.Vad()
        vad.set_mode(1)

        audio = pyaudio.PyAudio()
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        # A frame must be either 10, 20, or 30 ms in duration for webrtcvad
        FRAME_DURATION = 30
        CHUNK = int(RATE * FRAME_DURATION / 1000)

        microphones = LiveWhisper.list_microphones(audio)
        print("Available microphones:{}".format(microphones))
        selected_input_device_id = LiveWhisper.get_input_device_id(
            device_name, microphones)
        
        print("Selected microphone:{}".format(selected_input_device_id))

        stream = audio.open(input_device_index=selected_input_device_id,
                            format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)

        frames = b''
        last_speech = time.time()
        while True:
            if LiveWhisper.exit_event.is_set():
                break
            frame = stream.read(CHUNK, exception_on_overflow=False)
            is_speech = vad.is_speech(frame, RATE)
            if is_speech:
                frames += frame
                last_speech = time.time()
            else:
                if len(frames) > 3000:
                    asr_input_queue.put(frames)
                frames = b''
        stream.stop_stream()
        stream.close()
        audio.terminate()

    @staticmethod
    def asr_process(model_name, in_queue, output_queue):
        wave2vec_asr = WhisperInference(model_name)
        hotwords = []
        min_confidence = 0.3
        last_fetch = time.time()
        while True:
            audio_frames = in_queue.get()
            if audio_frames == "close":
                break
            
            if time.time() - last_fetch > 3000:
                print("Fetching hotwords...")
                response = requests.get("http://localhost:5275/listeningParameters",)
                if response.status_code == 200:
                    hotwords = response.json().get("hotwords", [])
                    min_confidence = response.json().get("min_confidence", 0.3)
                else:
                    print("Failed to fetch listeningParameters, using default.")

            float32_buffer = (np.frombuffer(
            audio_frames, dtype=np.int16) / (32768.0)).astype(np.float32)  # convert to float64
            start = time.perf_counter()
            text = wave2vec_asr.buffer_to_text(float32_buffer, hotwords, min_confidence)
            inference_time = time.perf_counter()-start
            sample_length = len(float32_buffer) / 16000  # length in sec
            output_queue.put([text,inference_time])

    @staticmethod
    def get_input_device_id(device_name, microphones):
        for device in microphones:
            print(device)
            if device_name in device[1]:
                return device[0]

    @staticmethod
    def list_microphones(pyaudio_instance):
        info = pyaudio_instance.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')

        result = []
        for i in range(0, numdevices):
            if (pyaudio_instance.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                name = pyaudio_instance.get_device_info_by_host_api_device_index(
                    0, i).get('name')
                result += [[i, name]]
        return result

    def get_last_text(self):
        return self.asr_output_queue.get()
