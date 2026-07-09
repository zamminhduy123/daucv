from vieneu import Vieneu
import os

tts = Vieneu()
os.makedirs("voice_tests", exist_ok=True)

text = """
Chào bạn. Tôi là người phỏng vấn hôm nay.
Bạn có thể giới thiệu ngắn gọn về project AI gần đây nhất của mình không?
"""

voices = tts.list_preset_voices()

for i, (desc, voice_id) in enumerate(voices):
    print(f"{i}: {desc} ({voice_id})")

    voice_data = tts.get_preset_voice(voice_id)

    audio = tts.infer(
        text=text,
        voice=voice_data,
        max_chars=180,
        temperature=0.7,
        top_k=30,
        silence_p=0.25,
        crossfade_p=0.05,
        apply_watermark=False,
    )

    filename = f"voice_tests/{i:02d}_{voice_id}.wav"
    filename = filename.replace("/", "_").replace(" ", "_")
    tts.save(audio, filename)