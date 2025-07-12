
import time
from melo.api import TTS

import sounddevice as sd


tts_model = TTS(language='EN', device='auto', config_path="VoiceTraining/config.json", ckpt_path=f"logs/voices/G_88000.pth")

print(f"TTS Voices: {tts_model.hps.data.spk2id}")


def sample_tts(text, speaker_id=0,  pitch=0.5, voice_volume=1.0):
    
    audio = tts_model.tts_to_file(speed=1.0, text=text, speaker_id=speaker_id)
                    

    with sd.OutputStream(channels=1, samplerate=44100 + (pitch-0.5) * 10000) as output_stream:
        output_stream.start()
        output_stream.write(audio * voice_volume * 1.5)

if __name__ == "__main__":
    i = 0
    while True:
        text = input("Enter text to synthesize (or 'exit' to quit): ")
        if text.lower() == 'exit':
            break
        print(f"Generating audio for: {text}")
        sample_tts(text, speaker_id=0, pitch=0.5, voice_volume=1.3)
        print(f"Audio generated and played for: {text}")