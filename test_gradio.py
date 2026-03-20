import sys
import traceback
from gradio_client import Client, handle_file

GRADIO_URL = "https://801def6d128636849f.gradio.live"
REF_AUDIO = "d:/notebook lm/voice/Recording (14).m4a"
REF_TEXT = "Hey everyone, welcome back! Have you ever wondered how artificial intelligence is changing the way we learn? Today, we are going to explore some incredible new concepts together. It's truly fascinating, and I know you're going to love it."

def test_short():
    try:
        client = Client(GRADIO_URL)
        print("Testing short text generation...")
        result = client.predict(
            text="This is a very short test.",
            ref_audio_path=handle_file(REF_AUDIO),
            ref_text=REF_TEXT,
            language="English",
            api_name="/predict"
        )
        print("SUCCESS:", result)
    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()

if __name__ == "__main__":
    test_short()
