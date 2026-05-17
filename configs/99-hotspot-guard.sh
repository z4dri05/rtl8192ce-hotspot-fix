#!/bin/bash
# 99-hotspot-guard.sh — NetworkManager dispatcher
# If KDE tries to create an ephemeral hotspot (with broken WPA3/SAE),
# intercept it and replace it with our correctly configured "Hotspot" connection.

IFACE="$1"
ACTION="$2"
CORRECT_CON="Hotspot"

# Check if this interface is an RTL8192CE device
RTL8192CE=false
for iface in /sys/class/net/*; do
    driver_path="$iface/device/driver"
    if [ -L "$driver_path" ] && readlink "$driver_path" | grep -qi "rtl8192ce"; then
        [ "$(basename "$iface")" = "$IFACE" ] && RTL8192CE=true
        break
    fi
done
$RTL8192CE || exit 0
[ "$ACTION" = "up" ] || exit 0

ACTIVE_CON=$(nmcli -t -f GENERAL.CONNECTION device show "$IFACE" 2>/dev/null | cut -d: -f2)
[ "$ACTIVE_CON" = "$CORRECT_CON" ] && exit 0

WIFI_MODE=$(nmcli -t -f wifi.mode connection show "$ACTIVE_CON" 2>/dev/null | cut -d: -f2)
[ "$WIFI_MODE" = "ap" ] || exit 0

logger -t hotspot-guard "Unauthorized hotspot '$ACTIVE_CON' detected, replacing with '$CORRECT_CON'"
nmcli connection down "$ACTIVE_CON" 2>/dev/null
nmcli connection delete "$ACTIVE_CON" 2>/dev/null
sleep 1
nmcli connection up "$CORRECT_CON" 2>/dev/null
