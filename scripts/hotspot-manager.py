#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hotspot Manager — Qt6 application for managing RTL8192CE WiFi Hotspot
Designed to visually integrate with KDE Plasma.
"""

import sys
import subprocess
import io
import os
import glob

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QGraphicsDropShadowEffect,
    QSpinBox, QComboBox, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPixmap, QImage, QFont, QColor, QPalette, QIcon, QPainter
)

try:
    import qrcode
    import qrcode.image.pil
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


# ── Auto-detect RTL8192CE interface ──

def get_wifi_iface() -> str:
    """Detect the RTL8192CE WiFi interface."""
    for iface in glob.glob("/sys/class/net/*"):
        driver_path = os.path.join(iface, "device", "driver")
        if os.path.islink(driver_path):
            driver = os.readlink(driver_path)
            if "rtl8192ce" in driver.lower():
                return os.path.basename(iface)
    return "wlo1"


IFACE = get_wifi_iface()


# ── NetworkManager utilities ──

def nm_run(args: list[str]) -> str:
    """Run an nmcli command and return stdout."""
    try:
        r = subprocess.run(
            ["nmcli"] + args,
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()
    except Exception:
        return ""


def nm_get(prop: str) -> str:
    """Get a property from the Hotspot connection."""
    out = nm_run(["-t", "-f", prop, "connection", "show", "Hotspot"])
    return out.split(":")[-1] if ":" in out else out


def nm_get_secret(prop: str) -> str:
    """Get a secret property from the Hotspot connection."""
    out = nm_run(["-s", "-g", prop, "connection", "show", "Hotspot"])
    return out.strip()


def is_hotspot_active() -> bool:
    """Check if the hotspot is active."""
    active = nm_run(["-t", "-f", "NAME", "connection", "show", "--active"])
    return "Hotspot" in active.split("\n")


def get_hotspot_ssid() -> str:
    """Get the current SSID of the connection."""
    return nm_get("802-11-wireless.ssid")


def get_hotspot_password() -> str:
    """Get the hotspot password."""
    return nm_get_secret("802-11-wireless-security.psk")


def get_hotspot_channel() -> str:
    """Get the channel."""
    return nm_get("802-11-wireless.channel")


def get_connected_clients() -> list[str]:
    """Get the list of connected clients."""
    try:
        r = subprocess.run(
            ["iw", "dev", IFACE, "station", "dump"],
            capture_output=True, text=True, timeout=5
        )
        clients = []
        for line in r.stdout.split("\n"):
            if line.strip().startswith("Station"):
                mac = line.split()[1]
                clients.append(mac)
        return clients
    except Exception:
        return []


def get_real_ssid_from_iw() -> str:
    """Get the actual SSID being broadcast by the antenna."""
    try:
        r = subprocess.run(
            ["iw", "dev", IFACE, "info"],
            capture_output=True, text=True, timeout=5
        )
        for line in r.stdout.split("\n"):
            if "ssid" in line:
                return line.split("ssid")[1].strip()
    except Exception:
        pass
    return ""


def is_hotspot_visible() -> bool:
    """Check if the network is visible (not hidden)."""
    real_ssid = get_real_ssid_from_iw()
    return real_ssid != ".__off__" and real_ssid != ""


# ── QR generator ──

def generate_qr_pixmap(ssid: str, password: str, size: int = 280) -> QPixmap | None:
    """Generate a WiFi QR code as QPixmap."""
    if not HAS_QRCODE:
        return None

    wifi_str = f"WIFI:T:WPA;S:{ssid};P:{password};;"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(wifi_str)
    qr.make(fit=True)

    # Generate image in memory
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    pixmap = QPixmap()
    pixmap.loadFromData(buf.read())
    return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)


# ── Stylesheet ──

STYLE = """
QMainWindow {
    background: palette(window);
}

#card {
    background: palette(base);
    border-radius: 16px;
    border: 1px solid palette(mid);
}

#statusDot {
    border-radius: 6px;
    min-width: 12px;
    max-width: 12px;
    min-height: 12px;
    max-height: 12px;
}

#statusDotOn {
    background: #2ecc71;
    border: 2px solid #27ae60;
    border-radius: 6px;
    min-width: 12px; max-width: 12px;
    min-height: 12px; max-height: 12px;
}

#statusDotOff {
    background: #e74c3c;
    border: 2px solid #c0392b;
    border-radius: 6px;
    min-width: 12px; max-width: 12px;
    min-height: 12px; max-height: 12px;
}

#statusDotHidden {
    background: #f39c12;
    border: 2px solid #e67e22;
    border-radius: 6px;
    min-width: 12px; max-width: 12px;
    min-height: 12px; max-height: 12px;
}

#titleLabel {
    font-size: 20px;
    font-weight: bold;
}

#subtitleLabel {
    font-size: 13px;
    color: palette(dark);
}

#sectionTitle {
    font-size: 14px;
    font-weight: bold;
    padding-top: 8px;
}

#infoLabel {
    font-size: 13px;
    color: palette(text);
}

#infoValue {
    font-size: 13px;
    font-weight: bold;
    color: palette(text);
}

#toggleBtn {
    font-size: 14px;
    font-weight: bold;
    padding: 10px 24px;
    border-radius: 10px;
    border: none;
    color: white;
    min-height: 40px;
}

#toggleBtnOn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #e74c3c, stop:1 #c0392b);
    font-size: 14px;
    font-weight: bold;
    padding: 10px 24px;
    border-radius: 10px;
    border: none;
    color: white;
    min-height: 40px;
}
#toggleBtnOn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #c0392b, stop:1 #a93226);
}

#toggleBtnOff {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2ecc71, stop:1 #27ae60);
    font-size: 14px;
    font-weight: bold;
    padding: 10px 24px;
    border-radius: 10px;
    border: none;
    color: white;
    min-height: 40px;
}
#toggleBtnOff:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #27ae60, stop:1 #1e8449);
}

#applyBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3498db, stop:1 #2980b9);
    font-size: 13px;
    font-weight: bold;
    padding: 8px 20px;
    border-radius: 8px;
    border: none;
    color: white;
    min-height: 36px;
}
#applyBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2980b9, stop:1 #2471a3);
}

#settingsInput {
    padding: 6px 10px;
    border-radius: 6px;
    border: 1px solid palette(mid);
    background: palette(base);
    font-size: 13px;
    min-height: 28px;
}

QFrame#separator {
    background: palette(mid);
    max-height: 1px;
    min-height: 1px;
}

#qrFrame {
    background: white;
    border-radius: 12px;
    padding: 12px;
    border: 1px solid palette(mid);
}

#clientCount {
    font-size: 12px;
    color: palette(dark);
    padding: 2px 8px;
    border-radius: 4px;
    background: palette(midlight);
}
"""


# ── Main widget ──

class HotspotManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hotspot Manager")
        self.setMinimumSize(460, 780)
        self.setMaximumSize(520, 900)
        self.setStyleSheet(STYLE)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ── Main card ──
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # Header with status
        header = QHBoxLayout()
        header.setSpacing(10)

        header_left = QVBoxLayout()
        self.title_label = QLabel("Hotspot WiFi")
        self.title_label.setObjectName("titleLabel")
        header_left.addWidget(self.title_label)

        self.status_label = QLabel("Comprobando...")
        self.status_label.setObjectName("subtitleLabel")
        header_left.addWidget(self.status_label)

        header.addLayout(header_left)
        header.addStretch()

        self.status_dot = QLabel()
        self.status_dot.setObjectName("statusDotOff")
        self.status_dot.setFixedSize(12, 12)
        header.addWidget(self.status_dot, alignment=Qt.AlignmentFlag.AlignTop)

        card_layout.addLayout(header)

        # Separator
        sep1 = QFrame()
        sep1.setObjectName("separator")
        sep1.setFrameShape(QFrame.Shape.HLine)
        card_layout.addWidget(sep1)

        # Hotspot info
        info_grid = QVBoxLayout()
        info_grid.setSpacing(6)

        self.ssid_row = self._make_info_row("SSID:", "—")
        info_grid.addLayout(self.ssid_row[0])

        self.pass_row = self._make_info_row("Password:", "—")
        info_grid.addLayout(self.pass_row[0])

        self.channel_row = self._make_info_row("Channel:", "—")
        info_grid.addLayout(self.channel_row[0])

        self.clients_row = self._make_info_row("Clients:", "0")
        info_grid.addLayout(self.clients_row[0])

        card_layout.addLayout(info_grid)

        # QR code
        self.qr_frame = QFrame()
        self.qr_frame.setObjectName("qrFrame")
        qr_layout = QVBoxLayout(self.qr_frame)
        qr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.qr_label = QLabel("Scan to connect")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setObjectName("subtitleLabel")
        qr_layout.addWidget(self.qr_label)

        self.qr_image = QLabel()
        self.qr_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_image.setMinimumSize(280, 280)
        self.qr_image.setFixedSize(280, 280)
        qr_layout.addWidget(self.qr_image)

        card_layout.addWidget(self.qr_frame)

        # Toggle button
        self.toggle_btn = QPushButton("Enable Hotspot")
        self.toggle_btn.setObjectName("toggleBtnOff")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_hotspot)
        card_layout.addWidget(self.toggle_btn)

        main_layout.addWidget(card)

        # ── Settings card ──
        settings_card = QFrame()
        settings_card.setObjectName("card")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(20, 16, 20, 16)
        settings_layout.setSpacing(10)

        settings_title = QLabel("⚙  Settings (applied after reboot)")
        settings_title.setObjectName("sectionTitle")
        settings_layout.addWidget(settings_title)

        # SSID input
        ssid_layout = QHBoxLayout()
        ssid_lbl = QLabel("SSID:")
        ssid_lbl.setObjectName("infoLabel")
        ssid_lbl.setFixedWidth(80)
        ssid_layout.addWidget(ssid_lbl)
        self.ssid_input = QLineEdit()
        self.ssid_input.setObjectName("settingsInput")
        self.ssid_input.setPlaceholderText("Network name")
        ssid_layout.addWidget(self.ssid_input)
        settings_layout.addLayout(ssid_layout)

        # Password input
        pass_layout = QHBoxLayout()
        pass_lbl = QLabel("Password:")
        pass_lbl.setObjectName("infoLabel")
        pass_lbl.setFixedWidth(80)
        pass_layout.addWidget(pass_lbl)
        self.pass_input = QLineEdit()
        self.pass_input.setObjectName("settingsInput")
        self.pass_input.setPlaceholderText("Minimum 8 characters")
        pass_layout.addWidget(self.pass_input)
        settings_layout.addLayout(pass_layout)

        # Canal
        chan_layout = QHBoxLayout()
        chan_lbl = QLabel("Channel:")
        chan_lbl.setObjectName("infoLabel")
        chan_lbl.setFixedWidth(80)
        chan_layout.addWidget(chan_lbl)
        self.channel_combo = QComboBox()
        self.channel_combo.setObjectName("settingsInput")
        for ch in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
            self.channel_combo.addItem(f"Channel {ch}", ch)
        chan_layout.addWidget(self.channel_combo)
        settings_layout.addLayout(chan_layout)

        # Apply button
        self.apply_btn = QPushButton("Apply changes")
        self.apply_btn.setObjectName("applyBtn")
        self.apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_btn.clicked.connect(self.apply_settings)
        settings_layout.addWidget(self.apply_btn)

        main_layout.addWidget(settings_card)
        main_layout.addStretch()

        # Timer for status updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(3000)

        # Load initial state
        self.refresh_status()

    def _make_info_row(self, label: str, value: str) -> tuple:
        """Create an info row."""
        layout = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setObjectName("infoLabel")
        lbl.setFixedWidth(90)
        layout.addWidget(lbl)
        val = QLabel(value)
        val.setObjectName("infoValue")
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(val)
        layout.addStretch()
        return (layout, val)

    def refresh_status(self):
        """Update all hotspot information."""
        active = is_hotspot_active()
        visible = is_hotspot_visible() if active else False

        ssid = get_hotspot_ssid()
        password = get_hotspot_password()
        channel = get_hotspot_channel()
        clients = get_connected_clients()

        # Update info
        self.ssid_row[1].setText(ssid if ssid else "—")
        self.pass_row[1].setText(password if password else "—")
        self.channel_row[1].setText(channel if channel else "—")
        self.clients_row[1].setText(str(len(clients)))

        # Fill settings fields if empty
        if not self.ssid_input.text() and ssid:
            self.ssid_input.setText(ssid)
        if not self.pass_input.text() and password:
            self.pass_input.setText(password)
        if channel:
            idx = self.channel_combo.findData(int(channel))
            if idx >= 0:
                self.channel_combo.setCurrentIndex(idx)

        # Update visual state
        if active and visible:
            self.status_label.setText(f"Broadcasting · {len(clients)} client(s)")
            self.status_dot.setObjectName("statusDotOn")
            self.toggle_btn.setText("⏻  Disable Hotspot")
            self.toggle_btn.setObjectName("toggleBtnOn")
            self.qr_frame.setVisible(True)
        elif active and not visible:
            self.status_label.setText("Hidden (standby)")
            self.status_dot.setObjectName("statusDotHidden")
            self.toggle_btn.setText("▶  Enable Hotspot")
            self.toggle_btn.setObjectName("toggleBtnOff")
            self.qr_frame.setVisible(False)
        else:
            self.status_label.setText("Off")
            self.status_dot.setObjectName("statusDotOff")
            self.toggle_btn.setText("▶  Enable Hotspot")
            self.toggle_btn.setObjectName("toggleBtnOff")
            self.qr_frame.setVisible(False)

        # Force style repaint
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)

        # Update QR
        if active and visible and ssid and password:
            pixmap = generate_qr_pixmap(ssid, password)
            if pixmap:
                self.qr_image.setPixmap(pixmap)
                self.qr_label.setText("Scan to connect")
            else:
                self.qr_label.setText("(install python3-qrcode to see QR)")
        else:
            self.qr_image.clear()

    def toggle_hotspot(self):
        """Turn hotspot on/off (hide/show)."""
        self.toggle_btn.setEnabled(False)
        self.toggle_btn.setText("⏳  Applying...")

        try:
            script = os.path.expanduser("~/bin/hotspot-toggle.sh")
            if os.path.exists(script):
                subprocess.run(["bash", script], timeout=15)
            else:
                # Fallback if script doesn't exist
                if is_hotspot_active() and is_hotspot_visible():
                    nm_run(["connection", "modify", "Hotspot",
                            "wifi.ssid", ".__off__", "wifi.hidden", "yes"])
                    nm_run(["connection", "up", "Hotspot"])
                elif is_hotspot_active():
                    ssid = self.ssid_input.text() or "fedora"
                    nm_run(["connection", "modify", "Hotspot",
                            "wifi.ssid", ssid, "wifi.hidden", "no"])
                    nm_run(["connection", "up", "Hotspot"])
                else:
                    nm_run(["connection", "up", "Hotspot"])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not toggle state:\n{e}")

        self.toggle_btn.setEnabled(True)
        QTimer.singleShot(1000, self.refresh_status)

    def apply_settings(self):
        """Apply SSID, password and channel changes."""
        new_ssid = self.ssid_input.text().strip()
        new_pass = self.pass_input.text().strip()
        new_channel = self.channel_combo.currentData()

        if not new_ssid:
            QMessageBox.warning(self, "Error", "SSID cannot be empty.")
            return

        if new_pass and len(new_pass) < 8:
            QMessageBox.warning(self, "Error",
                                "Password must be at least 8 characters.")
            return

        cmds = []
        if new_ssid:
            cmds += ["wifi.ssid", new_ssid]
        if new_pass:
            cmds += ["wifi-sec.psk", new_pass]
        if new_channel:
            cmds += ["wifi.channel", str(new_channel)]

        if cmds:
            nm_run(["connection", "modify", "Hotspot"] + cmds)

            # Update SSID in the toggle script
            script = os.path.expanduser("~/bin/hotspot-toggle.sh")
            if os.path.exists(script) and new_ssid:
                try:
                    with open(script, "r") as f:
                        content = f.read()
                    import re
                    content = re.sub(
                        r'SSID_REAL="[^"]*"',
                        f'SSID_REAL="{new_ssid}"',
                        content
                    )
                    with open(script, "w") as f:
                        f.write(content)
                except Exception:
                    pass

            QMessageBox.information(
                self, "Settings applied",
                "Changes have been saved.\n\n"
                "If the hotspot is active, SSID and channel changes "
                "will take effect after reboot.\n\n"
                "Password changes apply immediately."
            )

        self.refresh_status()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Hotspot Manager")
    app.setDesktopFileName("hotspot-manager")

    # Use system icon theme (KDE Breeze)
    QIcon.setThemeName(QIcon.themeName() or "breeze")

    window = HotspotManager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
