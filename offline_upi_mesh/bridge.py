import json
import sys
import httpx

BACKEND_URL = "http://127.0.0.1:8000/upload"

def main():
    if len(sys.argv) != 2:
        print("Usage: python bridge.py <packet_file.json>")
        print("Example: python bridge.py payment_packet.json")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, "r") as f:
            packet = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read file: {e}")
        sys.exit(1)

    print("📦 Packet loaded. Uploading to backend...")

    try:
        response = httpx.post(BACKEND_URL, json={"packet": packet}, timeout=10)
        result = response.json()
        print(f"\nResult → {result['status']}: {result.get('message', '')}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        print("Make sure the backend is running (python main.py)")

if __name__ == "__main__":
    main()