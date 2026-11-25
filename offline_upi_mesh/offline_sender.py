#!/usr/bin/env python3
"""
Offline Sender - creates an encrypted payment packet and a QR code.
Works completely offline (no backend needed).
Usage: python offline_sender.py <sender_vpa> <receiver_vpa> <amount>
"""
import json
import sys

import qrcode

from crypto_utils import encrypt_payment, load_keys


def main():
    if len(sys.argv) != 4:
        print("Usage: python offline_sender.py <sender_vpa> <receiver_vpa> <amount>")
        sys.exit(1)

    sender, receiver, amount = sys.argv[1], sys.argv[2], float(sys.argv[3])
    _, public_key = load_keys()
    packet = encrypt_payment(public_key, sender, receiver, amount)

    with open("payment_packet.json", "w") as f:
        json.dump({"packet": packet}, f, indent=2)

    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=12, border=4)
    qr.add_data(packet)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save("payment_qr.png")

    print(f"Payment: {sender} -> {receiver}  Rs.{amount:.2f}")
    print(f"Packet length: {len(packet)} chars (QR version {qr.version})")
    print("Saved: payment_packet.json, payment_qr.png")
    print("\nPacket (you can paste this into the dashboard's Paste tab):\n")
    print(packet)


if __name__ == "__main__":
    main()
