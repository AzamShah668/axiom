import json
with open(r"d:\notebook lm\tools\gradio_api_info.json", "r") as f:
    data = json.load(f)

endpoints = data.get("named_endpoints", {})
for name, details in endpoints.items():
    print(f"\nENDPOINT: {name}")
    print("PARAMETERS:")
    for p in details.get("parameters", []):
        try:
            print(f"  - {p.get('parameter_name', 'UNKNOWN')}: {p.get('python_type', {}).get('type', 'UNKNOWN')}")
        except:
            pass
