#!/bin/bash
# hotspot-toggle.sh — Toggle WiFi hotspot on/off for RTL8192CE
#
# IMPORTANT: The RTL8192CE has a firmware bug where, once you leave AP mode,
# it CANNOT transmit beacons again without a full reboot. Therefore this script
# NEVER turns off the radio or AP mode. Instead:
#   - "On"  = bring up the hotspot (only needed the first time after boot)
#   - "Off" = change the SSID to a hidden one and kick all clients,
#             but keep the AP alive internally to avoid killing the chip
#   - "On again" = restore the visible SSID

CONNECTION="Hotspot"
SSID_REAL="fedora"
SSID_HIDDEN=".__off__"

# Auto-detect RTL8192CE interface
IFACE="wlo1"
for iface in /sys/class/net/*; do
    driver_path="$iface/device/driver"
    if [ -L "$driver_path" ] && readlink "$driver_path" | grep -qi "rtl8192ce"; then
        IFACE=$(basename "$iface")
        break
    fi
done

# Check if the hotspot is active
if nmcli -t -f NAME connection show --active 2>/dev/null | grep -qx "${CONNECTION}"; then
    # It's active. Check if it's "visible" or "hidden"
    SSID_ACTUAL=$(iw dev "$IFACE" info 2>/dev/null | grep ssid | awk '{print $2}')

    if [ "$SSID_ACTUAL" = "$SSID_HIDDEN" ]; then
        # In "fake off" mode → restore visible SSID
        nmcli connection modify "$CONNECTION" wifi.ssid "$SSID_REAL" wifi.hidden no
        nmcli connection up "$CONNECTION" 2>/dev/null
        notify-send -i network-wireless-hotspot "Hotspot" "Enabled — SSID: $SSID_REAL" 2>/dev/null
        echo "Hotspot enabled. SSID: $SSID_REAL"
    else
        # Visible → "disable" by hiding the SSID and disconnecting clients
        # First disconnect all connected clients
        for STA in $(iw dev "$IFACE" station dump 2>/dev/null | grep Station | awk '{print $2}'); do
            iw dev "$IFACE" station del "$STA" 2>/dev/null
        done
        # Switch to hidden SSID so phones can't see it
        nmcli connection modify "$CONNECTION" wifi.ssid "$SSID_HIDDEN" wifi.hidden yes
        nmcli connection up "$CONNECTION" 2>/dev/null
        notify-send -i network-wireless-disconnected "Hotspot" "Disabled" 2>/dev/null
        echo "Hotspot disabled."
    fi
else
    # Not active at all → start for the first time
    # Kill any ephemeral KDE hotspot that might be active
    ACTIVE_AP=$(nmcli -t -f NAME,TYPE connection show --active | grep ":802-11-wireless$" | cut -d: -f1)
    if [ -n "$ACTIVE_AP" ] && [ "$ACTIVE_AP" != "$CONNECTION" ]; then
        nmcli connection down "$ACTIVE_AP" 2>/dev/null
        nmcli connection delete "$ACTIVE_AP" 2>/dev/null
    fi

    # Make sure SSID is correct
    nmcli connection modify "$CONNECTION" wifi.ssid "$SSID_REAL" wifi.hidden no
    nmcli connection up "$CONNECTION"
    if [ $? -eq 0 ]; then
        PASS=$(nmcli -s -g 802-11-wireless-security.psk connection show "$CONNECTION")
        notify-send -i network-wireless-hotspot "Hotspot" "Enabled — SSID: $SSID_REAL\nPassword: $PASS" 2>/dev/null
        echo "Hotspot enabled. SSID: $SSID_REAL"
    else
        notify-send -i dialog-error "Hotspot" "Failed to enable hotspot" 2>/dev/null
        echo "Failed to enable hotspot." >&2
        exit 1
    fi
fi
