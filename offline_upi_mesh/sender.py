import json
import sys
from crypto_utils import load_keys, encrypt_payment


def main():
    if len(sys.argv) != 4:
        print("Usage: python sender.py <sender_vpa> <receiver_vpa> <amount>")
        sys.exit(1)

    sender, receiver, amount = sys.argv[1], sys.argv[2], float(sys.argv[3])
    _, public_key = load_keys()
    packet = encrypt_payment(public_key, sender, receiver, amount)

    with open("payment_packet.json", "w") as f:
        json.dump({"packet": packet}, f, indent=2)

    print("Encrypted packet created: payment_packet.json")
    print("Send this file to the bridge device (Bluetooth / Nearby Share / USB / WhatsApp).")
    print("\n" + packet)


if __name__ == "__main__":
    main()
