import math
import soundfile as sf
import whisper

class WhisperInference:
    def __init__(self, model_name="large-v3-turbo"):
        self.model = whisper.load_model(model_name)


    def buffer_to_text(self, audio_buffer, hotwords, min_confidence=0.3):
        if len(audio_buffer) < 3000:
            return ""
        results = self.model.transcribe(audio_buffer, language='en', condition_on_previous_text=False, no_speech_threshold=0.1, logprob_threshold=-1.0, without_timestamps=True, fp16=True)
        text = ""
        score = 0.0
        for segment in results["segments"]:
            s_score = math.exp(segment["avg_logprob"])
            print(f"{segment['start']:.2f} --> {segment['end']:.2f} : {segment['text']} : {s_score:.2f}: {math.exp(segment['no_speech_prob']):.2f} : {len(audio_buffer)}")
            if score == 0.0:
                score = s_score
            if s_score > min_confidence:
                text = text + " " + segment['text'].strip()
                score = (score + s_score) / 2

        if score < min_confidence:
            print("Confidence too low, returning empty string.")
            return ""

        if len(text) > 20 and text.count(text[10:15]) > 7:
            return ""
        if len(audio_buffer) < 80000 and len(text) > 400:
            return ""
        
        if text == " Thank you." or text == " you":
            return ""

        return text
