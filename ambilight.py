#!/usr/bin/env python3
import subprocess
import json
import socket
import time
import numpy as np
from PIL import Image
from io import BytesIO
import cv2

# ============ CONFIGURATION ============
BULB_IP = "192.168.1.50"  # CHANGE THIS to your bulb's IP
BULB_PORT = 38899
FPS = 20  # Frames per second to sample
# =======================================

def get_vlc_geometry():
    """Get VLC window geometry from Hyprland"""
    try:
        result = subprocess.run(
            ['hyprctl', 'clients', '-j'],
            capture_output=True,
            text=True,
            timeout=1
        )
        clients = json.loads(result.stdout)

        for client in clients:
            cls = client.get('class', '').lower()
            if 'vlc' in cls:
                at = client['at']
                size = client['size']
                return f"{at[0]},{at[1]} {size[0]}x{size[1]}"
        return None
    except Exception:
        return None

def capture_window(geometry):
    """Capture screenshot using grim"""
    try:
        result = subprocess.run(
            ['grim', '-g', geometry, '-t', 'png', '-'],
            capture_output=True,
            timeout=1
        )
        if result.returncode == 0:
            return Image.open(BytesIO(result.stdout))
        return None
    except Exception:
        return None

def extract_edge_average(img):
    """Extract average color from a thin outer edge."""
    # Smaller size for performance and better edge emphasis
    img = img.resize((80, 45))
    img_array = np.array(img)

    h, w = img_array.shape[:2]
    edge_thickness = 5  # thinner edge

    top = img_array[:edge_thickness, :]
    bottom = img_array[-edge_thickness:, :]
    left = img_array[:, :edge_thickness]
    right = img_array[:, -edge_thickness:]

    edges = np.vstack([
        top.reshape(-1, 3),
        bottom.reshape(-1, 3),
        left.reshape(-1, 3),
        right.reshape(-1, 3)
    ])

    avg_color = edges.mean(axis=0).astype(int)
    return tuple(avg_color)

def enhance_color(r, g, b, sat_boost=1.4, val_boost=1.1):
    """Boost saturation and brightness for more vivid ambilight."""
    rgb = np.array([r, g, b], dtype=np.float32) / 255.0
    maxc = rgb.max()
    minc = rgb.min()
    v = maxc
    delta = maxc - minc

    if delta == 0:
        h = 0.0
        s = 0.0
    else:
        s = delta / maxc
        if maxc == rgb[0]:
            h = (rgb[1] - rgb[2]) / delta % 6
        elif maxc == rgb[1]:
            h = (rgb[2] - rgb[0]) / delta + 2
        else:
            h = (rgb[0] - rgb[1]) / delta + 4
        h /= 6.0

    # Boost S and V
    s = max(0.0, min(1.0, s * sat_boost))
    v = max(0.0, min(1.0, v * val_boost))

    # HSV -> RGB
    if s == 0.0:
        r2 = g2 = b2 = v
    else:
        i = int(h * 6.0)
        f = h * 6.0 - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6
        if i == 0:
            r2, g2, b2 = v, t, p
        elif i == 1:
            r2, g2, b2 = q, v, p
        elif i == 2:
            r2, g2, b2 = p, v, t
        elif i == 3:
            r2, g2, b2 = p, q, v
        elif i == 4:
            r2, g2, b2 = t, p, v
        else:
            r2, g2, b2 = v, p, q

    return int(r2 * 255), int(g2 * 255), int(b2 * 255)

def send_color_to_wiz(r, g, b):
    """Send RGB color to WiZ bulb via UDP"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        command = {
            "method": "setPilot",
            "params": {"r": int(r), "g": int(g), "b": int(b)}
        }
        message = json.dumps(command).encode()
        sock.sendto(message, (BULB_IP, BULB_PORT))
        sock.close()
        return True
    except Exception as e:
        print(f"Failed to send color: {e}")
        return False

def smooth_color(new_color, old_color, alpha=0.75):
    """Apply temporal smoothing to prevent flickering."""
    return tuple(int(alpha * n + (1 - alpha) * o)
                 for n, o in zip(new_color, old_color))

def main():
    print("=" * 50)
    print("WiZ Ambilight for VLC on Hyprland")
    print("=" * 50)
    print(f"Target bulb: {BULB_IP}:{BULB_PORT}")
    print(f"Sampling rate: {FPS} FPS")
    print(f"\nPress Ctrl+C to stop\n")
    print("=" * 50)

    last_color = (0, 0, 0)
    frame_delay = 1.0 / FPS
    no_vlc_count = 0

    while True:
        start_time = time.time()

        geometry = get_vlc_geometry()
        if not geometry:
            no_vlc_count += 1
            if no_vlc_count % 10 == 1:
                print("⏳ Waiting for VLC window...")
            time.sleep(1)
            continue

        if no_vlc_count > 0:
            print("✓ VLC window detected!\n")
            no_vlc_count = 0

        img = capture_window(geometry)
        if not img:
            time.sleep(frame_delay)
            continue

        # Edge average
        r, g, b = extract_edge_average(img)

        # Smooth
        r, g, b = smooth_color((r, g, b), last_color, alpha=0.75)

        # Enhance saturation/brightness
        r, g, b = enhance_color(r, g, b, sat_boost=1.4, val_boost=1.1)

        if send_color_to_wiz(r, g, b):
            print(f"✓ R={r:3d} G={g:3d} B={b:3d}")

        last_color = (r, g, b)

        elapsed = time.time() - start_time
        sleep_time = max(0, frame_delay - elapsed)
        time.sleep(sleep_time)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n" + "=" * 50)
        print("Stopping ambilight service...")
        print("=" * 50)

