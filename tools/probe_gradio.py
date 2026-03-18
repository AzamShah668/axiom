from gradio_client import Client

try:
    client = Client("http://127.0.0.1:8000/")
    info = client.view_api(return_format="dict")
    import json
    with open(r"d:\notebook lm\tools\gradio_api_info.json", "w") as f:
        json.dump(info, f, indent=2)
    print("Successfully wrote API info to d:\\notebook lm\\tools\\gradio_api_info.json")
except Exception as e:
    print(f"Error: {e}")
