import json
import sys
from crypto_utils import load_keys, encrypt_payment

def main():
    if len(sys.argv) != 4:
        print("Usage: python sender.py <sender_vpa> <receiver_vpa> <amount>")
        print("Example: python sender.py alice@upi bob@upi 250")
        sys.exit(1)

    sender = sys.argv[1]
    receiver = sys.argv[2]
    amount = float(sys.argv[3])

    _, public_key = load_keys()
    packet = encrypt_payment(public_key, sender, receiver, amount)

    filename = "payment_packet.json"
    with open(filename, "w") as f:
        json.dump(packet, f, indent=2)

    print("✅ Encrypted packet created successfully!")
    print(f"📁 Saved as: {filename}")
    print("\nNow send this file to the Bridge device using:")
    print("  • Windows Bluetooth file transfer")
    print("  • Nearby Share")
    print("  • WhatsApp / Telegram / USB / etc.")
    print("\nPacket preview:")
    print(json.dumps(packet, indent=2)[:400] + "...")

if __name__ == "__main__":
    main()