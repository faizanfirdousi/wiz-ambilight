#!/usr/bin/env python3
import socket
import json

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.settimeout(2)

# Send discovery command
message = json.dumps({"method": "getPilot", "params": {}}).encode()
sock.sendto(message, ('255.255.255.255', 38899))

print("Searching for WiZ bulbs on your network...\n")

# Listen for responses
try:
    while True:
        data, addr = sock.recvfrom(1024)
        print(f"✓ Found WiZ bulb at: {addr[0]}")
        print(f"  Response: {data.decode()}\n")
except socket.timeout:
    print("Search complete.")
finally:
    sock.close()

