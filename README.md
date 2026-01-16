# Ambilight Effect with Smart Bulb

I tweaked my smart bulb to act like an Ambilight backdrop that changes color to match the scenes of the movie I'm watching, and it looks insanely good.
What I Built

A small Python script that:

    Watches whatever is playing on my screen

    Picks the dominant color from the frame

    Pushes that color in real-time to my WiZ bulb over WiFi

## How the WiZ Protocol Actually Works

I couldn't have made this if the community hadn't reverse-engineered how WiZ bulbs work. Here's what's amazing:

The WiZ bulb exposes a local control port on your LAN – port 38899 to be exact – and it uses plain JSON over simple UDP packets.

This is the JSON you literally send if you want the bulb to be red:

```json
{"method": "setPilot", "params": {"r": 255, "g": 0, "b": 0}}
```

## How My Script Works

I'm on Arch btw, so I've made it work with it:

    The script invokes grim, which is a Wayland-native screenshot utility that outputs PNG bytes

    These PNG bytes are decoded by Pillow (image processing library)

    NumPy converts them into pixel arrays

    The script does some work managing the saturation, brightness, and other parameters to output a single RGB value

    This RGB value is then packaged as JSON and sent to the bulb's IP on port 38899
