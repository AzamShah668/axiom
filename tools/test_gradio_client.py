import sys, os, traceback
from gradio_client import Client, file

try:
    print("Initializing Gradio client connected to local Qwen TTS UI...")
    client = Client("http://127.0.0.1:8000/")
    
    ref_audio = r"d:\notebook lm\voice\reference_voice.wav"
    ref_txt = "Hello my name is Azam Rizwan"
    text = "Hello world, this is a test from the Gradio client bypassing the terminal crash!"
    
    print("Calling /run_voice_clone endpoint...")
    result = client.predict(
        ref_aud=file(ref_audio), # filepath
        ref_txt=ref_txt,         # str
        use_xvec=False,          # bool
        text=text,               # str
        lang_disp="Auto",        # str
        api_name="/run_voice_clone"
    )
    
    print("\n=== SUCCESS ===")
    print(val for val in result)
    print(f"Result tuple: {result}")
    
except Exception as e:
    print("\n=== FAILURE ===")
    traceback.print_exc()
