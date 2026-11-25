import json
import sys
import httpx

BACKEND_URL = "http://127.0.0.1:8000/upload"


def main():
    if len(sys.argv) != 2:
        print("Usage: python bridge.py <packet_file.json>")
        sys.exit(1)
    try:
        with open(sys.argv[1], "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read file: {e}")
        sys.exit(1)

    try:
        response = httpx.post(BACKEND_URL, json={"packet": data.get("packet", data)}, timeout=10)
        result = response.json()
        print(f"Result -> {result['status']}: {result.get('message', '')}")
    except Exception as e:
        print(f"Upload failed: {e}\nMake sure the backend is running (python main.py)")


if __name__ == "__main__":
    main()
