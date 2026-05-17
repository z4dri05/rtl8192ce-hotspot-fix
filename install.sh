#!/bin/bash
# ============================================================================
# install.sh — RTL8192CE WiFi Hotspot Fix Installer
#
# Usage:    sudo bash install.sh
# Or:       bash install.sh  (will ask for password via pkexec)
#
# What it does:
#   1. Configures RTL8192CE kernel driver parameters (power save OFF, SW encryption)
#   2. Disables MAC randomization which breaks the chip
#   3. Creates "Hotspot" connection with pure WPA2-PSK + CCMP
#   4. Configures the hotspot to auto-start on boot
#   5. Installs the toggle and GUI manager scripts
#   6. Installs the desktop entries
#   7. Installs the guard against KDE's broken hotspot button
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SSID="${1:-fedora}"
PASS="${2:-6btDoJ005W97}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── Check for RTL8192CE ──
if ! lspci | grep -qi "RTL8192CE"; then
    error "No RTL8192CE adapter detected on this system."
fi
info "RTL8192CE adapter detected"

# ── Auto-detect RTL8192CE interface ──
IFACE="wlo1"
for iface in /sys/class/net/*; do
    driver_path="$iface/device/driver"
    if [ -L "$driver_path" ] && readlink "$driver_path" | grep -qi "rtl8192ce"; then
        IFACE=$(basename "$iface")
        break
    fi
done
info "WiFi interface detected: $IFACE"

# ── Function to run commands as root ──
run_root() {
    if [ "$(id -u)" -eq 0 ]; then
        bash -c "$1"
    else
        pkexec bash -c "$1"
    fi
}

# ── 1. Kernel driver ──
run_root "cp '$SCRIPT_DIR/configs/rtl8192ce.conf' /etc/modprobe.d/rtl8192ce.conf"
info "Driver configured: ips=0 fwlps=0 aspm=0 swenc=1"

# ── 2. Disable MAC randomization ──
run_root "cp '$SCRIPT_DIR/configs/99-mac-randomization.conf' /etc/NetworkManager/conf.d/99-mac-randomization.conf"
info "MAC randomization disabled"

# ── 3. Install dispatcher (KDE guard) ──
run_root "cp '$SCRIPT_DIR/configs/99-hotspot-guard.sh' /etc/NetworkManager/dispatcher.d/99-hotspot-guard.sh && chmod 755 /etc/NetworkManager/dispatcher.d/99-hotspot-guard.sh && chown root:root /etc/NetworkManager/dispatcher.d/99-hotspot-guard.sh"
info "Protection dispatcher installed"

# ── 4. Restart NetworkManager to apply config ──
run_root "systemctl restart NetworkManager"
sleep 3
info "NetworkManager restarted"

# ── 5. Remove previous hotspot connections ──
nmcli connection delete "Hotspot" 2>/dev/null && warn "Previous 'Hotspot' connection deleted" || true
nmcli connection delete "fedora" 2>/dev/null || true

# ── 6. Create the hotspot connection ──
nmcli connection add \
  type wifi \
  ifname "$IFACE" \
  con-name "Hotspot" \
  autoconnect yes \
  connection.autoconnect-priority 100 \
  wifi.ssid "$SSID" \
  wifi.mode ap \
  wifi.band bg \
  wifi.channel 6 \
  wifi.cloned-mac-address preserve \
  ipv4.method shared \
  ipv6.method disabled \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "$PASS" \
  wifi-sec.proto rsn \
  wifi-sec.group ccmp \
  wifi-sec.pairwise ccmp \
  wifi-sec.pmf 1

info "Hotspot connection created (SSID: $SSID, autoconnect: yes)"

# ── 7. Install toggle script ──
mkdir -p "$HOME/bin"
cp "$SCRIPT_DIR/scripts/hotspot-toggle.sh" "$HOME/bin/hotspot-toggle.sh"
chmod +x "$HOME/bin/hotspot-toggle.sh"
# Update SSID in the script
sed -i "s/SSID_REAL=\"fedora\"/SSID_REAL=\"$SSID\"/" "$HOME/bin/hotspot-toggle.sh"
info "Toggle script installed at ~/bin/hotspot-toggle.sh"

# ── 8. Install GUI manager script ──
cp "$SCRIPT_DIR/scripts/hotspot-manager.py" "$HOME/bin/hotspot-manager.py"
chmod +x "$HOME/bin/hotspot-manager.py"
info "GUI manager script installed at ~/bin/hotspot-manager.py"

# ── 9. Install desktop entries ──
mkdir -p "$HOME/.local/share/applications"
cp "$SCRIPT_DIR/desktop/hotspot-toggle.desktop" "$HOME/.local/share/applications/hotspot-toggle.desktop"
sed -i "s|Exec=hotspot-toggle.sh|Exec=$HOME/bin/hotspot-toggle.sh|" "$HOME/.local/share/applications/hotspot-toggle.desktop"
cp "$SCRIPT_DIR/desktop/hotspot-manager.desktop" "$HOME/.local/share/applications/hotspot-manager.desktop"
sed -i "s|Exec=hotspot-manager.py|Exec=$HOME/bin/hotspot-manager.py|" "$HOME/.local/share/applications/hotspot-manager.desktop"
info "'Hotspot Toggle' and 'Hotspot Manager' desktop entries installed in KDE menu"

# ── 10. Show summary ──
echo ""
warn "A reboot is required for the driver changes to take effect."
echo ""
echo -e "  ${GREEN}SSID:${NC}        $SSID"
echo -e "  ${GREEN}Password:${NC}    $PASS"
echo -e "  ${GREEN}Security:${NC}    WPA2-PSK / CCMP (AES)"
echo -e "  ${GREEN}Autostart:${NC}   Yes (turns on automatically at boot)"
echo ""
echo -e "  ${YELLOW}KDE menu usage:${NC}"
echo -e "    'Hotspot Toggle' — switch hotspot on/off"
echo -e "    'Hotspot Manager' — GUI with QR code and settings"
echo -e "    (The RTL8192CE chip cannot actually power down the antenna,"
echo -e "     so the button hides/shows the network without touching the hardware.)"
echo ""
echo -e "  ${YELLOW}To change SSID or password manually:${NC}"
echo -e "    nmcli connection modify Hotspot wifi.ssid \"NewSSID\""
echo -e "    nmcli connection modify Hotspot wifi-sec.psk \"NewPassword\""
echo ""
read -p "Reboot now? [y/N] " REBOOT
if [[ "$REBOOT" =~ ^[yY]$ ]]; then
    systemctl reboot
fi
