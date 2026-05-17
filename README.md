# 📡 RTL8192CE Hotspot Fix for Linux

> Make your old Realtek RTL8192CE WiFi adapter work as a proper Access Point on modern Linux (Fedora 44 / KDE Plasma 6)

## The Problem

The **RTL8192CE** is a PCIe WiFi adapter from ~2012 that technically supports AP mode, but **it's completely broken out of the box on modern Linux** due to 5 separate bugs that stack on top of each other:

| # | Bug | What happens | Root cause |
|---|-----|-------------|------------|
| 1 | **WPA3/SAE injected** | Phone can't see the network | NetworkManager 1.56+ auto-upgrades security to WPA3, which the chip can't handle in AP mode |
| 2 | **MAC randomization** | Radio dies silently | NM randomizes the MAC address for privacy; the RTL8192CE firmware crashes when the MAC changes |
| 3 | **Power saving** | Network disappears after seconds | The chip enters sleep mode (IPS/FWLPS/ASPM) immediately when no client is connected, stopping beacon transmission |
| 4 | **Hardware crypto broken** | "Wrong password" on phone | The chip's hardware WPA2 encryption engine corrupts packets in AP mode, causing authentication failures |
| 5 | **Firmware can't recover** | Hotspot works once, then never again | Once the AP is stopped, the firmware enters an unrecoverable state — only a full reboot restores it |

On KDE Plasma specifically, the built-in hotspot button makes things worse: it creates a new ephemeral connection every time with all of the above bugs enabled, overwriting any manual fixes.

## The Solution

This repository provides a **one-command installer** that applies all 5 fixes and includes a Qt6 GUI manager with QR code support.

### What it does

1. **Kernel driver parameters** — Disables power saving and forces software encryption:
   ```
   options rtl8192ce ips=0 fwlps=0 aspm=0 swenc=1
   ```

2. **NetworkManager configuration** — Disables MAC randomization globally and creates a persistent hotspot connection with:
   - WPA2-PSK only (no WPA3/SAE)
   - CCMP (AES) cipher forced
   - PMF (Protected Management Frames) disabled
   - MAC address preserved (no cloning)
   - Auto-start on boot

3. **Smart toggle script** — Since the firmware dies permanently after stopping the AP, the toggle script **never actually stops it**. Instead, it hides/shows the SSID, keeping the hardware alive internally.

4. **KDE protection** — A NetworkManager dispatcher script intercepts KDE's broken hotspot attempts and redirects them to the correctly configured connection.

5. **Qt6 GUI Manager** — A native KDE application for managing the hotspot.

## Quick Install

```bash
git clone https://github.com/z4dri05/rtl8192ce-hotspot-fix.git
cd rtl8192ce-hotspot-fix
bash install.sh
```

Or with custom SSID and password:

```bash
bash install.sh "MyNetwork" "MyPassword123"
```

Then **reboot** to apply the kernel driver changes.

### Requirements

- Linux with NetworkManager (tested on Fedora 44, should work on any NM-based distro)
- Realtek RTL8192CE WiFi adapter
- Python 3 + PyQt6 + python3-qrcode (for the GUI — installed automatically on Fedora)
- Ethernet connection for internet sharing

#### Installing GUI dependencies (Fedora)

```bash
sudo dnf install python3-pyqt6 python3-qrcode qrencode
```

#### Installing GUI dependencies (Ubuntu/Debian)

```bash
sudo apt install python3-pyqt6 python3-qrcode
```

## Hotspot Manager (GUI)

The included Qt6 application integrates with KDE Plasma and provides:

- **📊 Live status** — Green/yellow/red indicator showing hotspot state
- **📱 QR Code** — Scan from your phone to connect instantly (no typing passwords)
- **👥 Client counter** — See how many devices are connected in real time
- **⚙️ Settings panel** — Change SSID, password, and WiFi channel
- **⏻ Smart toggle** — Turn the hotspot on/off without killing the hardware

### Launch

Search for **"Hotspot Manager"** in the KDE application menu, or run:

```bash
python3 scripts/hotspot-manager.py
```

### Settings behavior

| Setting | When it applies |
|---------|----------------|
| **Password** | Saved immediately, takes effect on next client connection |
| **SSID** | Saved immediately, takes effect after reboot |
| **Channel** | Saved immediately, takes effect after reboot |

> **Why reboot?** The RTL8192CE firmware cannot reconfigure the AP parameters while running. Any attempt to restart the AP will permanently kill beacon transmission until the next power cycle.

## Repository Structure

```
rtl8192ce-hotspot-fix/
├── install.sh                          # One-command installer
├── README.md                           # This file
├── configs/
│   ├── rtl8192ce.conf                  # Kernel driver parameters
│   ├── 99-mac-randomization.conf       # NetworkManager MAC fix
│   └── 99-hotspot-guard.sh             # KDE hotspot interceptor
├── scripts/
│   ├── hotspot-toggle.sh               # Smart on/off toggle (bash)
│   └── hotspot-manager.py              # Qt6 GUI application
└── desktop/
    ├── hotspot-toggle.desktop          # KDE menu entry (toggle)
    └── hotspot-manager.desktop         # KDE menu entry (GUI)
```

## How the Smart Toggle Works

The RTL8192CE has a fatal firmware bug: once you take the adapter out of AP mode, it can never transmit beacons again until the machine is rebooted. This means a traditional on/off cycle (`nmcli connection down/up`) will work **exactly once**.

To work around this, the toggle script uses a "fake off" strategy:

```
"ON"  → SSID = "fedora"     (visible, phones can see it)
"OFF" → SSID = ".__off__"   (hidden, phones ignore it)
```

The AP never actually stops. The hardware stays in AP mode permanently, keeping the firmware happy. When you "turn off" the hotspot, all connected clients are disconnected and the SSID is changed to a hidden dummy name. When you "turn on" again, the real SSID is restored.

## Tested On

- **OS:** Fedora 44 (KDE Plasma Desktop Edition)
- **Kernel:** 7.0.8-200.fc44.x86_64
- **KDE Plasma:** 6.6.5
- **NetworkManager:** 1.56.0
- **wpa_supplicant:** 2.11
- **Adapter:** Realtek RTL8192CE (PCIe, `lspci: 21:00.0`)
- **Driver:** rtl8192ce (in-tree rtlwifi)

## Troubleshooting

### The hotspot doesn't appear on my phone
1. **Reboot the PC** — This is the #1 fix. The RTL8192CE firmware gets stuck easily.
2. Check that the connection exists: `nmcli connection show Hotspot`
3. Check the driver is loaded with correct params: `cat /sys/module/rtl8192ce/parameters/swenc` (should say `Y`)

### "Wrong password" error on phone
- Make sure `swenc=1` is set in `/etc/modprobe.d/rtl8192ce.conf`
- Reboot after changing driver parameters
- Try "Forget network" on your phone and reconnect

### The hotspot worked once but now it's invisible
- This is the firmware bug (Bug #5). **You must reboot.**
- If you're using the toggle script or the GUI app, this shouldn't happen because they never actually stop the AP.

### KDE's hotspot button creates a broken network
- The dispatcher script (`99-hotspot-guard.sh`) should intercept this automatically
- Use the Hotspot Manager app or the toggle script instead of KDE's button

## License

MIT — Do whatever you want with it. If this saved you hours of debugging, consider starring the repo ⭐

## Credits

Diagnosed and fixed through extensive reverse-engineering of the RTL8192CE driver behavior on modern kernels. Special thanks to the `rtlwifi` kernel module maintainers for documenting the `swenc`, `ips`, `fwlps`, and `aspm` parameters.
