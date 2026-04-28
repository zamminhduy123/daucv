import asyncio
import edge_tts
import tempfile
import os

async def test_tts():
    text = "Xin chào, đây là giọng nói thử nghiệm từ Bé Đậu. Bạn có nghe rõ không?"
    voice = "vi-VN-HoaiMyNeural"
    
    print(f"🎙 Generating audio using edge-tts...")
    print(f"📝 Text: '{text}'")
    print(f"🗣 Voice: {voice}")
    
    communicate = edge_tts.Communicate(text, voice)
    
    # Create a temporary file just like in the FastAPI snippet
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
        
    await communicate.save(tmp_path)
    
    print(f"✅ Success! Audio file saved temporarily to: {tmp_path}")
    print(f"You can play this file to verify the audio quality.")

if __name__ == "__main__":
    asyncio.run(test_tts())