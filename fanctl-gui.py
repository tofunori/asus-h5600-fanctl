#!/usr/bin/env python3
"""
ASUS ProArt H5600QM Fan Control GUI - With Auto Profiles
"""
import sys
import subprocess
import threading
import time
import os

# DBus for sleep/wake detection (must be before Qt imports)
import dbus
from dbus.mainloop.pyqt5 import DBusQtMainLoop

# Logging
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path.home() / ".local/share/fanctl"
LOG_FILE = LOG_DIR / "fanctl.log"

# Enable HiDPI scaling for Qt5 (must be before QApplication)
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QSlider, QCheckBox,
                             QGroupBox, QRadioButton, QSystemTrayIcon, QMenu, QAction,
                             QComboBox, QTabWidget, QSpinBox, QGridLayout, QDialog, QToolTip)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QSettings, QPointF
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen, QPainterPath, QBrush

# Dark mode stylesheet
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
}
QGroupBox {
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    background-color: #252525;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    color: #e0e0e0;
}
QPushButton {
    background-color: #3a3a3a;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 8px;
    color: #e0e0e0;
}
QPushButton:hover {
    background-color: #4a4a4a;
}
QPushButton:pressed {
    background-color: #2a2a2a;
}
QSlider::groove:horizontal {
    background: #3a3a3a;
    height: 8px;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #0078d4;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}
QTabWidget::pane {
    border: 1px solid #3a3a3a;
    background-color: #252525;
}
QTabBar::tab {
    background-color: #2a2a2a;
    color: #e0e0e0;
    padding: 8px 16px;
    border: 1px solid #3a3a3a;
}
QTabBar::tab:selected {
    background-color: #3a3a3a;
}
QCheckBox {
    color: #e0e0e0;
}
QComboBox {
    background-color: #3a3a3a;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 4px;
    color: #e0e0e0;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #2a2a2a;
    color: #e0e0e0;
    selection-background-color: #0078d4;
}
"""

LIGHT_STYLE = """
QMainWindow, QWidget {
    background-color: #f5f5f5;
    color: #1e1e1e;
}
QGroupBox {
    border: 1px solid #c0c0c0;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    color: #1e1e1e;
}
QPushButton {
    background-color: #e0e0e0;
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    padding: 8px;
    color: #1e1e1e;
}
QPushButton:hover {
    background-color: #d0d0d0;
}
QPushButton:pressed {
    background-color: #c0c0c0;
}
QSlider::groove:horizontal {
    background: #c0c0c0;
    height: 8px;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #0078d4;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}
QTabWidget::pane {
    border: 1px solid #c0c0c0;
    background-color: #ffffff;
}
QTabBar::tab {
    background-color: #e8e8e8;
    color: #1e1e1e;
    padding: 8px 16px;
    border: 1px solid #c0c0c0;
}
QTabBar::tab:selected {
    background-color: #ffffff;
}
QCheckBox {
    color: #1e1e1e;
}
QComboBox {
    background-color: #ffffff;
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    padding: 4px;
    color: #1e1e1e;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1e1e1e;
    selection-background-color: #0078d4;
}
"""

# System theme: only layout properties, colors from system
SYSTEM_STYLE = """
QGroupBox {
    margin-top: 10px;
    padding-top: 10px;
}
QPushButton {
    padding: 8px;
}
QSlider::groove:horizontal {
    height: 8px;
}
QSlider::handle:horizontal {
    width: 18px;
    margin: -5px 0;
}
QTabBar::tab {
    padding: 8px 16px;
}
QComboBox {
    padding: 4px;
}
"""

# Fan curve profiles: (temp_threshold, fan_percent)
# Separate curves for CPU and GPU - GPU needs slightly more cooling at high temps
# Based on ASUS recommendations: GPU min 34% at 70C vs CPU 31%
# Hysteresis of 5°C applied in control loop to prevent oscillations
PROFILES = {
    "Silent": {
        "cpu": [(0, 0), (50, 0), (55, 5), (58, 8), (60, 10), (62, 12), (65, 18), (70, 30), (75, 45), (80, 60), (85, 80), (90, 100)],
        "gpu": [(0, 0), (50, 0), (55, 7), (58, 10), (60, 12), (62, 15), (65, 22), (70, 34), (75, 50), (80, 65), (85, 85), (90, 100)],
    },
    "Quiet": {
        "cpu": [(0, 0), (50, 0), (55, 8), (58, 10), (60, 14), (62, 18), (65, 25), (70, 38), (75, 50), (80, 65), (85, 85), (90, 100)],
        "gpu": [(0, 0), (50, 0), (55, 10), (58, 12), (60, 16), (62, 22), (65, 30), (70, 42), (75, 55), (80, 70), (85, 90), (90, 100)],
    },
    "Balanced": {
        "cpu": [(0, 0), (48, 0), (52, 5), (55, 10), (58, 14), (60, 18), (62, 22), (65, 30), (70, 42), (75, 55), (80, 70), (85, 88), (90, 100)],
        "gpu": [(0, 0), (48, 0), (52, 7), (55, 12), (58, 16), (60, 22), (62, 26), (65, 35), (70, 48), (75, 60), (80, 75), (85, 92), (90, 100)],
    },
    "Performance": {
        "cpu": [(0, 10), (50, 10), (55, 15), (58, 20), (60, 26), (62, 32), (65, 40), (70, 52), (75, 65), (80, 78), (85, 92), (90, 100)],
        "gpu": [(0, 12), (50, 12), (55, 18), (58, 24), (60, 30), (62, 36), (65, 45), (70, 58), (75, 70), (80, 82), (85, 95), (90, 100)],
    },
    "Turbo": {
        "cpu": [(0, 15), (50, 15), (55, 22), (58, 30), (60, 38), (62, 45), (65, 55), (70, 68), (75, 80), (80, 90), (85, 100), (90, 100)],
        "gpu": [(0, 18), (50, 18), (55, 26), (58, 34), (60, 42), (62, 50), (65, 60), (70, 72), (75, 85), (80, 95), (85, 100), (90, 100)],
    },
}

# Hysteresis in degrees - fan won't slow down until temp drops by this amount
HYSTERESIS = 5

# Profile colors for curve visualization
PROFILE_COLORS = {
    "Silent": "#4CAF50",      # Green
    "Quiet": "#03A9F4",       # Light blue
    "Balanced": "#2196F3",    # Blue
    "Performance": "#FF9800", # Orange
    "Turbo": "#F44336",       # Red
}

# Power profiles: CPU energy preference + GPU power level + CPU boost
POWER_PROFILES = {
    "Performance": {
        "cpu_energy": "performance",
        "gpu_power": "high",
        "cpu_boost": True,
        "color": "#F44336",  # Red
    },
    "Balanced": {
        "cpu_energy": "balance_power",
        "gpu_power": "auto",
        "cpu_boost": False,
        "color": "#2196F3",  # Blue
    },
    "Power Saver": {
        "cpu_energy": "power",
        "gpu_power": "low",
        "cpu_boost": False,
        "color": "#4CAF50",  # Green
    },
}

# Temperature notification settings
TEMP_WARNING_THRESHOLD = 85  # Celsius
NOTIFICATION_COOLDOWN = 60   # Seconds between notifications


class CurveWidget(QWidget):
    """Widget to draw fan curve visualization with hover tooltips"""
    def __init__(self, profile_name, curve_data, parent=None):
        super().__init__(parent)
        self.profile_name = profile_name
        self.curve_data = curve_data
        self.setFixedSize(350, 250)
        self.setMouseTracking(True)
        self.point_data = []  # Store (QPointF, temp, fan_pct) for tooltips

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Margins
        left_margin = 45
        right_margin = 20
        top_margin = 30
        bottom_margin = 35

        # Drawing area
        width = self.width() - left_margin - right_margin
        height = self.height() - top_margin - bottom_margin

        # Background
        is_dark = self.palette().window().color().lightness() < 128
        bg_color = QColor("#2a2a2a") if is_dark else QColor("#ffffff")
        grid_color = QColor("#404040") if is_dark else QColor("#e0e0e0")
        text_color = QColor("#e0e0e0") if is_dark else QColor("#333333")

        painter.fillRect(self.rect(), bg_color)

        # Draw title
        painter.setPen(QPen(text_color))
        title_font = QFont("Cantarell", 11, QFont.Bold)
        painter.setFont(title_font)
        painter.drawText(left_margin, 20, f"Profile: {self.profile_name}")

        # Draw grid
        painter.setPen(QPen(grid_color, 1, Qt.DotLine))

        # Horizontal grid lines (every 25%)
        for i in range(5):
            y = top_margin + height - (i * height / 4)
            painter.drawLine(left_margin, int(y), left_margin + width, int(y))

        # Vertical grid lines (every 20°C)
        for i in range(6):
            x = left_margin + (i * width / 5)
            painter.drawLine(int(x), top_margin, int(x), top_margin + height)

        # Draw axes labels
        painter.setPen(QPen(text_color))
        label_font = QFont("Cantarell", 8)
        painter.setFont(label_font)

        # Y-axis labels (fan %)
        for i in range(5):
            y = top_margin + height - (i * height / 4)
            painter.drawText(5, int(y) + 4, f"{i * 25}%")

        # X-axis labels (temperature)
        temps = [0, 20, 40, 60, 80, 100]
        for i, temp in enumerate(temps):
            x = left_margin + (i * width / 5)
            painter.drawText(int(x) - 10, top_margin + height + 15, f"{temp}°C")

        # Draw curve
        profile_color = QColor(PROFILE_COLORS.get(self.profile_name, "#0078d4"))

        # Create path for the curve
        path = QPainterPath()
        points = []
        self.point_data = []  # Reset for tooltips

        for temp, fan_pct in self.curve_data:
            x = left_margin + (temp / 100.0) * width
            y = top_margin + height - (fan_pct / 100.0) * height
            point = QPointF(x, y)
            points.append(point)
            self.point_data.append((point, temp, fan_pct))

        if points:
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)

        # Draw filled area under curve
        fill_path = QPainterPath(path)
        if points:
            fill_path.lineTo(points[-1].x(), top_margin + height)
            fill_path.lineTo(points[0].x(), top_margin + height)
            fill_path.closeSubpath()

        fill_color = QColor(profile_color)
        fill_color.setAlpha(50)
        painter.fillPath(fill_path, QBrush(fill_color))

        # Draw curve line
        painter.setPen(QPen(profile_color, 3))
        painter.drawPath(path)

        # Draw points
        painter.setBrush(QBrush(profile_color))
        painter.setPen(QPen(Qt.white, 2))
        for point in points:
            painter.drawEllipse(point, 5, 5)

    def mouseMoveEvent(self, event):
        """Show tooltip when hovering over curve points"""
        pos = event.pos()
        for point, temp, fan_pct in self.point_data:
            # Check if mouse is within 10px radius of point
            if (pos.x() - point.x())**2 + (pos.y() - point.y())**2 <= 100:
                QToolTip.showText(event.globalPos(), f"{temp}°C → {fan_pct}%")
                return
        QToolTip.hideText()


class CurveDialog(QDialog):
    """Dialog to show fan curve visualization"""
    def __init__(self, profile_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Courbe - {profile_name}")
        self.setFixedSize(370, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Get curve data - show CPU curve (GPU is similar but slightly higher)
        profile = PROFILES.get(profile_name, {"cpu": [], "gpu": []})
        curve_data = profile["cpu"]

        # Add curve widget
        curve_widget = CurveWidget(profile_name, curve_data)
        layout.addWidget(curve_widget)

        # Add close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)


class AboutDialog(QDialog):
    """About dialog with project info and contact"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setFixedSize(380, 280)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Title
        title = QLabel("ASUS Fan Control")
        title.setFont(QFont("Cantarell", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Version
        version = QLabel("Version 1.3")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(10)

        # Description
        desc = QLabel("Fan control utility for ASUS ProArt StudioBook H5600QM\nwith independent CPU/GPU temperature-based profiles.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(15)

        # Contact
        contact = QLabel("Contact: tofunori@gmail.com")
        contact.setAlignment(Qt.AlignCenter)
        layout.addWidget(contact)

        # GitHub
        github = QLabel("GitHub: github.com/tofunori/asus-h5600-fanctl")
        github.setAlignment(Qt.AlignCenter)
        github.setStyleSheet("color: #0078d4;")
        layout.addWidget(github)

        layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)


class GaugeWidget(QWidget):
    """Modern gauge widget with needle for fan speed display"""
    def __init__(self, title="Fan", accent_color=None, parent=None):
        super().__init__(parent)
        self.title = title
        self.value = 0
        self.accent_color = accent_color  # Custom color for needle/arc
        self.setFixedSize(160, 160)

    def setValue(self, value):
        self.value = max(0, min(100, value))
        self.update()

    def paintEvent(self, event):
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # Colors based on theme
        is_dark = self.palette().window().color().lightness() < 128
        bg_color = QColor("#1e1e1e") if is_dark else QColor("#ffffff")
        arc_bg = QColor("#3a3a3a") if is_dark else QColor("#e0e0e0")
        text_color = QColor("#ffffff") if is_dark else QColor("#333333")
        subtle_text = QColor("#888888") if is_dark else QColor("#666666")

        # Dimensions
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2 + 5
        radius = 60

        # Draw outer glow/shadow ring
        glow_rect = self.rect().adjusted(8, 8, -8, -8)
        pen = QPen(QColor("#252525") if is_dark else QColor("#f0f0f0"), 14, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(glow_rect, 225 * 16, -270 * 16)

        # Draw background arc (270 degrees)
        arc_rect = self.rect().adjusted(15, 15, -15, -15)
        pen = QPen(arc_bg, 10, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(arc_rect, 225 * 16, -270 * 16)

        # Draw colored arc - use accent color or value-based color
        if self.accent_color:
            color = QColor(self.accent_color)
        elif self.value <= 30:
            color = QColor("#00E676")  # Bright green
        elif self.value <= 50:
            color = QColor("#4CAF50")  # Green
        elif self.value <= 70:
            color = QColor("#FFEB3B")  # Yellow
        elif self.value <= 85:
            color = QColor("#FF9800")  # Orange
        else:
            color = QColor("#F44336")  # Red

        pen = QPen(color, 10, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        arc_span = int(-270 * self.value / 100)
        painter.drawArc(arc_rect, 225 * 16, arc_span * 16)

        # Draw tick marks
        painter.setPen(QPen(subtle_text, 1))
        for i in range(0, 101, 25):
            angle = math.radians(225 - (270 * i / 100))
            inner_r = radius - 18
            outer_r = radius - 12
            x1 = cx + inner_r * math.cos(angle)
            y1 = cy - inner_r * math.sin(angle)
            x2 = cx + outer_r * math.cos(angle)
            y2 = cy - outer_r * math.sin(angle)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Draw needle
        angle = math.radians(225 - (270 * self.value / 100))
        needle_len = radius - 22

        # Needle shadow
        painter.setPen(QPen(QColor(0, 0, 0, 50), 4, Qt.SolidLine, Qt.RoundCap))
        nx = cx + needle_len * math.cos(angle) + 1
        ny = cy - needle_len * math.sin(angle) + 1
        painter.drawLine(cx + 1, cy + 1, int(nx), int(ny))

        # Needle
        painter.setPen(QPen(color, 3, Qt.SolidLine, Qt.RoundCap))
        nx = cx + needle_len * math.cos(angle)
        ny = cy - needle_len * math.sin(angle)
        painter.drawLine(cx, cy, int(nx), int(ny))

        # Draw center circle
        painter.setBrush(QBrush(QColor("#2d2d2d") if is_dark else QColor("#ffffff")))
        painter.setPen(QPen(color, 2))
        painter.drawEllipse(cx - 8, cy - 8, 16, 16)

        # Draw inner dot
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - 4, cy - 4, 8, 8)

        # Draw title at top
        painter.setPen(QPen(subtle_text))
        font = QFont("Cantarell", 9)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, 8, 0, 0), Qt.AlignHCenter | Qt.AlignTop, self.title)

        # Draw large value in center-bottom (with margin from edge)
        painter.setPen(QPen(text_color))
        font = QFont("Cantarell", 15, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, 10, 0, -5), Qt.AlignHCenter | Qt.AlignBottom, f"{self.value}%")


class FanController(QObject):
    """Handles fan control in background thread"""
    status_changed = pyqtSignal(str)
    temps_changed = pyqtSignal(int, int)  # cpu_temp, gpu_temp
    fan_duty_changed = pyqtSignal(int, int)  # cpu_duty, gpu_duty
    temp_warning = pyqtSignal(str, int)  # component, temp

    def __init__(self):
        super().__init__()
        self.running = True
        self.mode = "auto"  # auto, manual, profile
        self.profile_name = "Balanced"
        self.cpu_percent = 50
        self.gpu_percent = 50
        self.cpu_temp = 0
        self.gpu_temp = 0
        self.control_thread = None
        # Hysteresis tracking - separate for CPU and GPU
        self.last_cpu_speed = 0
        self.last_gpu_speed = 0
        self.last_cpu_temp = 0
        self.last_gpu_temp = 0
        # Temperature notification
        self.notification_enabled = True
        self.last_notification_time = 0
        # Sleep/wake state tracking
        self.last_mode = "auto"
        self.last_profile = "Balanced"
        self.last_manual_cpu = 50
        self.last_manual_gpu = 50
        # Logging
        self.verbose_until = 0
        self.setup_logging()

    def setup_logging(self):
        """Initialize logging system"""
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("fanctl")
        self.logger.setLevel(logging.INFO)
        # Prevent duplicate handlers on restart
        if not self.logger.handlers:
            handler = RotatingFileHandler(
                LOG_FILE, maxBytes=1_000_000, backupCount=2
            )
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self.logger.addHandler(handler)
        self.log("App started")

    def log(self, message, level="info", verbose_only=False):
        """Log message. verbose_only=True logs only in verbose mode."""
        if verbose_only and time.time() > self.verbose_until:
            return
        getattr(self.logger, level)(message)

    def enable_verbose(self, hours):
        """Enable verbose logging for N hours"""
        self.verbose_until = time.time() + (hours * 3600)
        self.logger.setLevel(logging.DEBUG)
        self.log(f"Verbose logging enabled for {hours}h")

    def disable_verbose(self):
        """Disable verbose logging"""
        self.verbose_until = 0
        self.logger.setLevel(logging.INFO)
        self.log("Verbose logging disabled")

    def is_verbose(self):
        """Check if verbose logging is active"""
        return time.time() < self.verbose_until

    def run_cmd(self, cmd):
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            return True
        except:
            return False

    def enable_manual(self):
        # Use direct EC register write - bypasses CWAP GPU check that fails
        # Read current value, set bit 0x40 for manual mode
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 1' | sudo tee /proc/acpi/call > /dev/null")
        # Force GPU active bit and manual mode via direct EC write
        self.run_cmd("echo '\\_SB.PCI0.SBRG.EC0.WRAM 0xCD 0x10 0x03' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.PCI0.SBRG.EC0.WRAM 0xCD 0x30 0x41' | sudo tee /proc/acpi/call > /dev/null")

    def disable_manual(self):
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 0' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 0' | sudo tee /proc/acpi/call > /dev/null")

    def set_fans(self, cpu_pct, gpu_pct):
        cpu_hex = hex(int(cpu_pct * 255 / 100))
        gpu_hex = hex(int(gpu_pct * 255 / 100))
        self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 0 {cpu_hex}' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 1 {gpu_hex}' | sudo tee /proc/acpi/call > /dev/null")

    def read_temps(self):
        try:
            with open('/sys/class/hwmon/hwmon6/temp1_input', 'r') as f:
                self.cpu_temp = int(f.read().strip()) // 1000
        except:
            self.cpu_temp = 0

        try:
            with open('/sys/class/hwmon/hwmon5/temp1_input', 'r') as f:
                self.gpu_temp = int(f.read().strip()) // 1000
        except:
            self.gpu_temp = 0

        self.temps_changed.emit(self.cpu_temp, self.gpu_temp)
        self.check_temp_warning()

    def check_temp_warning(self):
        """Check if temperature exceeds threshold and emit warning"""
        if not self.notification_enabled:
            return

        current_time = time.time()
        if current_time - self.last_notification_time < NOTIFICATION_COOLDOWN:
            return

        if self.cpu_temp > TEMP_WARNING_THRESHOLD:
            self.last_notification_time = current_time
            self.log(f"Temperature warning: CPU at {self.cpu_temp}°C", level="warning")
            self.temp_warning.emit("CPU", self.cpu_temp)
        elif self.gpu_temp > TEMP_WARNING_THRESHOLD:
            self.last_notification_time = current_time
            self.log(f"Temperature warning: GPU at {self.gpu_temp}°C", level="warning")
            self.temp_warning.emit("GPU", self.gpu_temp)

    def read_fan_duty(self):
        """Read actual fan duty cycle via ST83"""
        try:
            # CPU fan duty
            subprocess.run("echo '\\_SB.PCI0.SBRG.EC0.ST83 0' | sudo tee /proc/acpi/call > /dev/null",
                          shell=True, capture_output=True)
            result = subprocess.run("sudo cat /proc/acpi/call", shell=True, capture_output=True)
            cpu_hex = result.stdout.replace(b'\x00', b'').decode().strip()
            cpu_raw = int(cpu_hex, 16) if cpu_hex.startswith('0x') else 0
            cpu_duty = cpu_raw * 100 // 255

            # GPU fan duty
            subprocess.run("echo '\\_SB.PCI0.SBRG.EC0.ST83 1' | sudo tee /proc/acpi/call > /dev/null",
                          shell=True, capture_output=True)
            result = subprocess.run("sudo cat /proc/acpi/call", shell=True, capture_output=True)
            gpu_hex = result.stdout.replace(b'\x00', b'').decode().strip()
            gpu_raw = int(gpu_hex, 16) if gpu_hex.startswith('0x') else 0
            gpu_duty = gpu_raw * 100 // 255

            self.fan_duty_changed.emit(cpu_duty, gpu_duty)
        except Exception as e:
            pass

    def get_fan_speed_for_temp(self, temp, curve):
        """Calculate fan speed based on temperature and curve"""
        for i in range(len(curve) - 1):
            t1, f1 = curve[i]
            t2, f2 = curve[i + 1]
            if t1 <= temp < t2:
                # Linear interpolation
                ratio = (temp - t1) / (t2 - t1) if t2 != t1 else 0
                return int(f1 + ratio * (f2 - f1))
        return curve[-1][1]  # Return max if above all thresholds

    def get_fan_speed_with_hysteresis(self, temp, last_temp, last_speed, curve):
        """Calculate fan speed with hysteresis for one fan"""
        target = self.get_fan_speed_for_temp(temp, curve)

        if target > last_speed:
            # Temperature rising - apply immediately
            return target, temp
        elif temp <= last_temp - HYSTERESIS:
            # Temperature dropped enough - allow slowdown
            return target, temp
        else:
            # Hysteresis zone - keep current speed
            return last_speed, last_temp

    def control_loop(self):
        """Main control loop - handles both manual and profile modes"""
        log_counter = 0
        while self.running:
            self.read_temps()
            self.read_fan_duty()

            if self.mode == "manual":
                self.enable_manual()
                self.set_fans(self.cpu_percent, self.gpu_percent)
                # Verbose log every ~5 seconds (50 iterations at 0.1s)
                log_counter += 1
                if log_counter >= 50:
                    self.log(f"CPU:{self.cpu_temp}°C GPU:{self.gpu_temp}°C Fan:{self.cpu_percent}%/{self.gpu_percent}%", verbose_only=True)
                    log_counter = 0
                time.sleep(0.1)

            elif self.mode == "profile":
                profile = PROFILES.get(self.profile_name, PROFILES["Balanced"])
                cpu_curve = profile["cpu"]
                gpu_curve = profile["gpu"]

                # CPU fan - based on CPU temperature
                cpu_speed, self.last_cpu_temp = self.get_fan_speed_with_hysteresis(
                    self.cpu_temp, self.last_cpu_temp, self.last_cpu_speed, cpu_curve)
                self.last_cpu_speed = cpu_speed

                # GPU fan - based on GPU temperature
                gpu_speed, self.last_gpu_temp = self.get_fan_speed_with_hysteresis(
                    self.gpu_temp, self.last_gpu_temp, self.last_gpu_speed, gpu_curve)
                self.last_gpu_speed = gpu_speed

                self.enable_manual()
                self.set_fans(cpu_speed, gpu_speed)

                # Verbose log every ~5 seconds (10 iterations at 0.5s)
                log_counter += 1
                if log_counter >= 10:
                    self.log(f"CPU:{self.cpu_temp}°C GPU:{self.gpu_temp}°C Fan:{cpu_speed}%/{gpu_speed}%", verbose_only=True)
                    log_counter = 0

                self.status_changed.emit(f"{self.profile_name} - CPU:{cpu_speed}% GPU:{gpu_speed}%")
                time.sleep(0.5)  # Profile mode can be slower

            else:  # auto mode
                # Verbose log every ~5 seconds
                log_counter += 1
                if log_counter >= 5:
                    self.log(f"Auto mode - CPU:{self.cpu_temp}°C GPU:{self.gpu_temp}°C", verbose_only=True)
                    log_counter = 0
                time.sleep(1)

    def start_control(self):
        if self.control_thread is None or not self.control_thread.is_alive():
            self.control_thread = threading.Thread(target=self.control_loop, daemon=True)
            self.control_thread.start()

    def set_manual(self, cpu, gpu):
        self.mode = "manual"
        self.cpu_percent = cpu
        self.gpu_percent = gpu
        self.log(f"Manual mode: CPU={cpu}% GPU={gpu}%")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 0' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 0' | sudo tee /proc/acpi/call > /dev/null")
        time.sleep(0.3)
        self.start_control()

        if cpu == gpu:
            self.status_changed.emit(f"Manuel - {cpu}%")
        else:
            self.status_changed.emit(f"CPU:{cpu}% GPU:{gpu}%")

    def set_profile(self, profile_name):
        self.mode = "profile"
        self.profile_name = profile_name
        self.log(f"Profile changed to {profile_name}")
        # Reset hysteresis state to apply new profile immediately
        self.last_cpu_speed = 0
        self.last_gpu_speed = 0
        self.last_cpu_temp = 0
        self.last_gpu_temp = 0
        self.start_control()
        self.status_changed.emit(f"{profile_name} - Loading...")

    def set_auto(self):
        self.mode = "auto"
        self.log("Auto mode (EC control)")
        self.disable_manual()
        self.run_cmd("echo 1 | sudo tee /sys/devices/platform/h5600_fan/thermal_policy > /dev/null 2>&1")
        self.status_changed.emit("Automatic (EC)")

    def stop(self):
        self.log("App stopped")
        self.running = False

    def prepare_for_sleep(self):
        """Called before system suspend - save state and return to EC control"""
        self.log("Preparing for sleep")
        # Save current state
        self.last_mode = self.mode
        self.last_profile = self.profile_name
        if self.mode == "manual":
            self.last_manual_cpu = self.cpu_percent
            self.last_manual_gpu = self.gpu_percent

        # Stop control loop and return to EC (safe for suspend)
        self.running = False
        self.disable_manual()
        self.status_changed.emit("Suspending...")

    def resume_from_sleep(self):
        """Called after system resumes - restore previous mode"""
        self.log(f"Resumed from sleep, restoring {self.last_mode}")
        self.running = True
        # Restore previous mode
        if self.last_mode == "profile":
            self.set_profile(self.last_profile)
        elif self.last_mode == "manual":
            self.set_manual(self.last_manual_cpu, self.last_manual_gpu)
        else:
            self.set_auto()


class FanControlGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = FanController()
        self.controller.status_changed.connect(self.update_status)
        self.controller.temps_changed.connect(self.update_temps)
        self.linked = True

        self.init_ui()
        self.init_tray()
        self.setup_sleep_detection()
        self.controller.fan_duty_changed.connect(self.update_fan_gauges)
        self.controller.temp_warning.connect(self.show_temp_warning)
        self.controller.start_control()

        # Default settings: Balanced profile + CPU boost disabled
        self.set_profile("Balanced")
        self.disable_boost_on_start()

    def disable_boost_on_start(self):
        """Disable CPU boost on startup"""
        subprocess.run("echo 0 | sudo tee /sys/devices/system/cpu/cpufreq/boost > /dev/null",
                      shell=True, capture_output=True)
        self.boost_check.setChecked(False)
        self.boost_status.setText("OFF")
        self.boost_status.setStyleSheet("color: red;")

    def init_ui(self):
        self.setWindowTitle("ASUS Fan Control")
        self.setMinimumSize(420, 650)
        self.resize(450, 700)

        # Initialize settings early (before combo boxes trigger signals)
        self.settings = QSettings("ASUS", "FanControl")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)

        # Header
        header = QLabel("ASUS Fan Control")
        header.setFont(QFont("Cantarell", 18, QFont.Bold))
        layout.addWidget(header)

        subtitle = QLabel("ProArt StudioBook H5600QM")
        subtitle.setStyleSheet("color: gray;")
        layout.addWidget(subtitle)

        # Temperatures
        temp_group = QGroupBox("Temperatures")
        temp_layout = QHBoxLayout(temp_group)

        cpu_temp_layout = QVBoxLayout()
        cpu_temp_layout.addWidget(QLabel("CPU"))
        self.cpu_temp_label = QLabel("--°C")
        self.cpu_temp_label.setFont(QFont("Cantarell", 16, QFont.Bold))
        cpu_temp_layout.addWidget(self.cpu_temp_label)
        temp_layout.addLayout(cpu_temp_layout)

        gpu_temp_layout = QVBoxLayout()
        gpu_temp_layout.addWidget(QLabel("GPU"))
        self.gpu_temp_label = QLabel("--°C")
        self.gpu_temp_label.setFont(QFont("Cantarell", 16, QFont.Bold))
        gpu_temp_layout.addWidget(self.gpu_temp_label)
        temp_layout.addLayout(gpu_temp_layout)

        layout.addWidget(temp_group)

        # Status
        self.status_label = QLabel("Mode: Automatique")
        self.status_label.setFont(QFont("Cantarell", 11, QFont.Bold))
        self.status_label.setStyleSheet("color: #0066cc;")
        layout.addWidget(self.status_label)

        # Tabs for different modes
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Tab 1: Profiles (Auto based on temp)
        profile_tab = QWidget()
        profile_layout = QVBoxLayout(profile_tab)

        profile_desc = QLabel("Auto adjustment based on temperature:")
        profile_layout.addWidget(profile_desc)

        # Profile buttons
        profile_grid = QGridLayout()
        profiles = ["Silent", "Quiet", "Balanced", "Performance", "Turbo"]
        for i, name in enumerate(profiles):
            btn = QPushButton(name)
            btn.setMinimumHeight(45)
            btn.clicked.connect(lambda checked, n=name: self.set_profile(n))
            # Add right-click context menu to show curve
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, n=name, b=btn: self.show_curve_menu(pos, n, b)
            )
            profile_grid.addWidget(btn, i // 3, i % 3)

        profile_layout.addLayout(profile_grid)

        # Fan speed gauges - centered with vertical spacing
        profile_layout.addSpacing(20)
        gauge_layout = QHBoxLayout()
        gauge_layout.addStretch()
        self.cpu_gauge = GaugeWidget("CPU Fan", accent_color="#2196F3")  # Blue
        self.gpu_gauge = GaugeWidget("GPU Fan", accent_color="#FF9800")  # Orange
        gauge_layout.addWidget(self.cpu_gauge, 0, Qt.AlignCenter)
        gauge_layout.addSpacing(40)
        gauge_layout.addWidget(self.gpu_gauge, 0, Qt.AlignCenter)
        gauge_layout.addStretch()
        profile_layout.addLayout(gauge_layout)
        profile_layout.addSpacing(15)

        profile_layout.addStretch()
        tabs.addTab(profile_tab, "Auto Profiles")

        # Tab 2: Manual control
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)

        # Presets row
        presets_layout = QHBoxLayout()
        for name, percent in [("TURBO", 100), ("Perf", 80), ("Balance", 50), ("Quiet", 30), ("Silent", 12)]:
            btn = QPushButton(f"{name}\n{percent}%")
            btn.clicked.connect(lambda checked, p=percent: self.set_preset(p))
            presets_layout.addWidget(btn)
        manual_layout.addLayout(presets_layout)

        # Link checkbox
        self.link_check = QCheckBox("Lier les ventilateurs")
        self.link_check.setChecked(True)
        self.link_check.stateChanged.connect(self.on_link_changed)
        manual_layout.addWidget(self.link_check)

        # CPU slider
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(QLabel("CPU:"))
        self.cpu_value_label = QLabel("50%")
        self.cpu_value_label.setMinimumWidth(40)
        cpu_layout.addWidget(self.cpu_value_label)
        self.cpu_slider = QSlider(Qt.Horizontal)
        self.cpu_slider.setRange(10, 100)
        self.cpu_slider.setValue(50)
        self.cpu_slider.valueChanged.connect(self.on_cpu_slider)
        cpu_layout.addWidget(self.cpu_slider)
        manual_layout.addLayout(cpu_layout)

        # GPU slider
        gpu_layout = QHBoxLayout()
        gpu_layout.addWidget(QLabel("GPU:"))
        self.gpu_value_label = QLabel("50%")
        self.gpu_value_label.setMinimumWidth(40)
        gpu_layout.addWidget(self.gpu_value_label)
        self.gpu_slider = QSlider(Qt.Horizontal)
        self.gpu_slider.setRange(10, 100)
        self.gpu_slider.setValue(50)
        self.gpu_slider.valueChanged.connect(self.on_gpu_slider)
        gpu_layout.addWidget(self.gpu_slider)
        manual_layout.addLayout(gpu_layout)

        apply_btn = QPushButton("Appliquer")
        apply_btn.clicked.connect(self.apply_individual)
        manual_layout.addWidget(apply_btn)

        manual_layout.addStretch()
        tabs.addTab(manual_tab, "Manual")

        # Tab 3: Power (new)
        power_tab = QWidget()
        power_layout = QVBoxLayout(power_tab)

        # Power Profile section
        power_profile_group = QGroupBox("Power Profile")
        power_profile_layout = QVBoxLayout(power_profile_group)

        power_desc = QLabel("Controls CPU energy, GPU power, and CPU boost:")
        power_profile_layout.addWidget(power_desc)

        # Power profile buttons
        power_btn_layout = QHBoxLayout()
        self.power_profile_buttons = {}
        for name in ["Performance", "Balanced", "Power Saver"]:
            btn = QPushButton(name)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda checked, n=name: self.set_power_profile(n))
            power_btn_layout.addWidget(btn)
            self.power_profile_buttons[name] = btn
        power_profile_layout.addLayout(power_btn_layout)

        # Current power profile status
        self.power_status_label = QLabel("Current: Balanced")
        self.power_status_label.setStyleSheet("color: #2196F3;")
        power_profile_layout.addWidget(self.power_status_label)

        power_layout.addWidget(power_profile_group)

        # CPU Boost
        boost_group = QGroupBox("CPU Boost")
        boost_layout_inner = QHBoxLayout(boost_group)
        self.boost_check = QCheckBox("Turbo Boost")
        self.boost_check.stateChanged.connect(self.toggle_boost)
        boost_layout_inner.addWidget(self.boost_check)
        self.boost_status = QLabel("ON")
        self.boost_status.setFont(QFont("Cantarell", 10, QFont.Bold))
        self.boost_status.setStyleSheet("color: green;")
        boost_layout_inner.addWidget(self.boost_status)
        power_layout.addWidget(boost_group)

        self.check_boost()

        # Battery section
        battery_group = QGroupBox("Battery")
        battery_layout_inner = QHBoxLayout(battery_group)
        battery_layout_inner.addWidget(QLabel("Charge Limit:"))
        self.battery_combo = QComboBox()
        self.battery_combo.addItems(["60%", "80%", "100%"])
        self.battery_combo.currentIndexChanged.connect(self.set_battery_limit)
        battery_layout_inner.addWidget(self.battery_combo)
        self.battery_status = QLabel("100%")
        self.battery_status.setFont(QFont("Cantarell", 10, QFont.Bold))
        battery_layout_inner.addWidget(self.battery_status)
        power_layout.addWidget(battery_group)

        # Read current battery limit
        self.check_battery_limit()

        # Settings section
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout(settings_group)

        # Autostart
        self.autostart_check = QCheckBox("Start with system")
        self.autostart_check.stateChanged.connect(self.toggle_autostart)
        settings_layout.addWidget(self.autostart_check)
        self.check_autostart()

        # Temperature notifications
        self.notify_check = QCheckBox("Temperature alerts (>85°C)")
        self.notify_check.setChecked(True)
        self.notify_check.stateChanged.connect(self.toggle_notifications)
        settings_layout.addWidget(self.notify_check)

        # Theme selector
        theme_layout_inner = QHBoxLayout()
        theme_layout_inner.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Dark", "Light"])
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        theme_layout_inner.addWidget(self.theme_combo)
        theme_layout_inner.addStretch()
        settings_layout.addLayout(theme_layout_inner)

        power_layout.addWidget(settings_group)

        # Logging section
        log_group = QGroupBox("Logging")
        log_layout = QHBoxLayout(log_group)

        log_layout.addWidget(QLabel("Verbose:"))
        self.verbose_combo = QComboBox()
        self.verbose_combo.addItems(["Off", "1h", "2h", "5h", "12h", "24h"])
        log_layout.addWidget(self.verbose_combo)

        self.verbose_btn = QPushButton("Enable")
        self.verbose_btn.clicked.connect(self.toggle_verbose_logging)
        log_layout.addWidget(self.verbose_btn)

        self.open_log_btn = QPushButton("Open Log")
        self.open_log_btn.clicked.connect(self.open_log_folder)
        log_layout.addWidget(self.open_log_btn)

        log_layout.addStretch()
        power_layout.addWidget(log_group)

        power_layout.addStretch()
        tabs.addTab(power_tab, "Power")

        # Tab 4: EC Auto
        auto_tab = QWidget()
        auto_layout = QVBoxLayout(auto_tab)
        auto_desc = QLabel("Let the embedded controller (EC) manage the fans.\n\n"
                          "This is the BIOS default mode.")
        auto_layout.addWidget(auto_desc)
        auto_btn = QPushButton("Enable Auto EC Mode")
        auto_btn.clicked.connect(self.on_auto_mode)
        auto_layout.addWidget(auto_btn)
        auto_layout.addStretch()
        tabs.addTab(auto_tab, "Auto EC")

        # Load saved settings
        saved_theme = self.settings.value("theme", 0, type=int)
        self.theme_combo.setCurrentIndex(saved_theme)
        self.apply_theme(saved_theme)

        # Warning
        warning = QLabel("SILENT mode = watch temperatures!")
        warning.setStyleSheet("color: orange;")
        layout.addWidget(warning)

    def create_tray_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor("#0066cc"))
        painter.setPen(QColor("#003366"))
        painter.drawEllipse(2, 2, 28, 28)
        painter.setBrush(QColor("white"))
        painter.drawEllipse(12, 12, 8, 8)
        painter.end()
        return QIcon(pixmap)

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.create_tray_icon())
        self.tray_icon.setToolTip("ASUS Fan Control")

        tray_menu = QMenu()

        show_action = QAction("Afficher", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        # Profiles submenu
        profiles_menu = QMenu("Auto Profiles", self)
        for name in PROFILES.keys():
            action = QAction(name, self)
            action.triggered.connect(lambda checked, n=name: self.set_profile(n))
            profiles_menu.addAction(action)
        tray_menu.addMenu(profiles_menu)

        tray_menu.addSeparator()

        # Manual presets
        for name, percent in [("Manual 100%", 100), ("Manual 50%", 50), ("Manual 30%", 30)]:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, p=percent: self.set_preset(p))
            tray_menu.addAction(action)

        tray_menu.addSeparator()

        auto_action = QAction("Auto EC", self)
        auto_action.triggered.connect(self.on_auto_mode)
        tray_menu.addAction(auto_action)

        tray_menu.addSeparator()

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        tray_menu.addAction(about_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def setup_sleep_detection(self):
        """Setup DBus listener for sleep/wake events from systemd-logind"""
        try:
            bus = dbus.SystemBus()
            bus.add_signal_receiver(
                self.on_sleep_wake,
                signal_name='PrepareForSleep',
                dbus_interface='org.freedesktop.login1.Manager',
                bus_name='org.freedesktop.login1',
                path='/org/freedesktop/login1'
            )
        except Exception as e:
            print(f"Sleep detection unavailable: {e}")

    def on_sleep_wake(self, sleeping):
        """Handle sleep/wake events from systemd"""
        if sleeping:
            self.controller.prepare_for_sleep()
        else:
            self.controller.resume_from_sleep()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_window()

    def show_window(self):
        # Position window near tray icon (like g-helper)
        tray_geo = self.tray_icon.geometry()
        if tray_geo.isValid():
            # Get the screen where tray icon is located (multi-monitor support)
            tray_screen = QApplication.screenAt(tray_geo.center())
            if tray_screen:
                screen = tray_screen.geometry()
            else:
                screen = QApplication.primaryScreen().geometry()

            # Calculate position: above tray icon, aligned to right
            x = tray_geo.x() - self.width() + tray_geo.width()
            y = tray_geo.y() - self.height() - 10  # 10px margin above tray

            # Keep window on screen
            if x < screen.x():
                x = screen.x() + 10
            if x + self.width() > screen.x() + screen.width():
                x = screen.x() + screen.width() - self.width() - 10
            if y < screen.y():
                y = tray_geo.y() + tray_geo.height() + 10  # Below tray if no space above

            self.move(x, y)

        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def quit_app(self):
        self.controller.stop()
        self.tray_icon.hide()
        QApplication.quit()

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec_()

    def update_temps(self, cpu, gpu):
        cpu_color = "green" if cpu < 60 else "orange" if cpu < 80 else "red"
        gpu_color = "green" if gpu < 60 else "orange" if gpu < 80 else "red"
        self.cpu_temp_label.setText(f"{cpu}°C")
        self.cpu_temp_label.setStyleSheet(f"color: {cpu_color};")
        self.gpu_temp_label.setText(f"{gpu}°C")
        self.gpu_temp_label.setStyleSheet(f"color: {gpu_color};")

        # Update tray tooltip
        self.tray_icon.setToolTip(f"Fan Control - CPU:{cpu}°C GPU:{gpu}°C")

    def update_status(self, status):
        self.status_label.setText(f"Mode: {status}")

    def update_fan_gauges(self, cpu_duty, gpu_duty):
        self.cpu_gauge.setValue(cpu_duty)
        self.gpu_gauge.setValue(gpu_duty)

    def on_cpu_slider(self, value):
        self.cpu_value_label.setText(f"{value}%")
        if self.linked:
            self.gpu_slider.blockSignals(True)
            self.gpu_slider.setValue(value)
            self.gpu_value_label.setText(f"{value}%")
            self.gpu_slider.blockSignals(False)

    def on_gpu_slider(self, value):
        self.gpu_value_label.setText(f"{value}%")
        if self.linked:
            self.cpu_slider.blockSignals(True)
            self.cpu_slider.setValue(value)
            self.cpu_value_label.setText(f"{value}%")
            self.cpu_slider.blockSignals(False)

    def on_link_changed(self, state):
        self.linked = state == Qt.Checked
        if self.linked:
            self.gpu_slider.setValue(self.cpu_slider.value())

    def set_profile(self, name):
        threading.Thread(target=self.controller.set_profile, args=(name,), daemon=True).start()

    def show_curve_menu(self, pos, profile_name, button):
        """Show context menu with option to view curve"""
        menu = QMenu(self)
        show_curve_action = menu.addAction("Show curve")
        action = menu.exec_(button.mapToGlobal(pos))
        if action == show_curve_action:
            dialog = CurveDialog(profile_name, self)
            dialog.exec_()

    def set_preset(self, percent):
        self.cpu_slider.setValue(percent)
        self.gpu_slider.setValue(percent)
        threading.Thread(target=self.controller.set_manual, args=(percent, percent), daemon=True).start()

    def apply_individual(self):
        cpu = self.cpu_slider.value()
        gpu = self.gpu_slider.value()
        threading.Thread(target=self.controller.set_manual, args=(cpu, gpu), daemon=True).start()

    def on_auto_mode(self):
        threading.Thread(target=self.controller.set_auto, daemon=True).start()

    def check_boost(self):
        try:
            with open('/sys/devices/system/cpu/cpufreq/boost', 'r') as f:
                enabled = f.read().strip() == '1'
                self.boost_check.setChecked(enabled)
                self.boost_status.setText("ON" if enabled else "OFF")
                self.boost_status.setStyleSheet(f"color: {'green' if enabled else 'red'};")
        except:
            self.boost_status.setText("N/A")

    def toggle_boost(self, state):
        value = "1" if state == Qt.Checked else "0"
        result = subprocess.run(f"echo {value} | sudo tee /sys/devices/system/cpu/cpufreq/boost > /dev/null",
                               shell=True, capture_output=True)
        if result.returncode == 0:
            self.boost_status.setText("ON" if state else "OFF")
            self.boost_status.setStyleSheet(f"color: {'green' if state else 'red'};")

    def change_theme(self, index):
        self.apply_theme(index)
        self.settings.setValue("theme", index)

    def apply_theme(self, index):
        app = QApplication.instance()
        if index == 1:  # Dark
            app.setStyleSheet(DARK_STYLE)
        elif index == 2:  # Light
            app.setStyleSheet(LIGHT_STYLE)
        else:  # System
            app.setStyleSheet(SYSTEM_STYLE)

    def set_power_profile(self, name):
        """Apply power profile: CPU energy + GPU power + CPU boost"""
        profile = POWER_PROFILES.get(name)
        if not profile:
            return

        # CPU Energy (all cores)
        for cpu in range(16):
            path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/energy_performance_preference"
            subprocess.run(f"echo {profile['cpu_energy']} | sudo tee {path} > /dev/null",
                          shell=True, capture_output=True)

        # GPU Power
        subprocess.run(f"echo {profile['gpu_power']} | sudo tee /sys/class/drm/card1/device/power_dpm_force_performance_level > /dev/null",
                      shell=True, capture_output=True)

        # CPU Boost
        boost_val = "1" if profile['cpu_boost'] else "0"
        subprocess.run(f"echo {boost_val} | sudo tee /sys/devices/system/cpu/cpufreq/boost > /dev/null",
                      shell=True, capture_output=True)

        # Update UI
        self.boost_check.setChecked(profile['cpu_boost'])
        self.power_status_label.setText(f"Current: {name}")
        self.power_status_label.setStyleSheet(f"color: {profile['color']};")

        # Save setting
        self.settings.setValue("power_profile", name)

    def set_battery_limit(self, index):
        """Set battery charge limit"""
        limits = [60, 80, 100]
        value = limits[index]
        result = subprocess.run(f"echo {value} | sudo tee /sys/class/power_supply/BAT0/charge_control_end_threshold > /dev/null",
                               shell=True, capture_output=True)
        if result.returncode == 0:
            self.battery_status.setText(f"{value}%")
            self.settings.setValue("battery_limit", index)

    def check_battery_limit(self):
        """Read current battery charge limit"""
        try:
            with open('/sys/class/power_supply/BAT0/charge_control_end_threshold', 'r') as f:
                value = int(f.read().strip())
                self.battery_status.setText(f"{value}%")
                # Set combo to matching value
                limits = [60, 80, 100]
                if value in limits:
                    self.battery_combo.setCurrentIndex(limits.index(value))
        except:
            self.battery_status.setText("N/A")

    def toggle_autostart(self, state):
        """Enable or disable autostart"""
        desktop_path = os.path.expanduser("~/.config/autostart/fanctl-gui.desktop")
        if state == Qt.Checked:
            content = """[Desktop Entry]
Type=Application
Name=ASUS Fan Control
Exec=/usr/local/bin/fanctl-gui
Icon=preferences-system
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
            os.makedirs(os.path.dirname(desktop_path), exist_ok=True)
            with open(desktop_path, 'w') as f:
                f.write(content)
        else:
            if os.path.exists(desktop_path):
                os.remove(desktop_path)

    def check_autostart(self):
        """Check if autostart is enabled"""
        desktop_path = os.path.expanduser("~/.config/autostart/fanctl-gui.desktop")
        self.autostart_check.setChecked(os.path.exists(desktop_path))

    def toggle_notifications(self, state):
        """Enable or disable temperature notifications"""
        self.controller.notification_enabled = (state == Qt.Checked)
        self.settings.setValue("notifications", state == Qt.Checked)

    def show_temp_warning(self, component, temp):
        """Show temperature warning notification"""
        self.tray_icon.showMessage(
            "Temperature Warning",
            f"{component} at {temp}°C!",
            QSystemTrayIcon.Warning,
            5000
        )

    def toggle_verbose_logging(self):
        """Enable or disable verbose logging"""
        combo_text = self.verbose_combo.currentText()
        if combo_text == "Off" or self.controller.is_verbose():
            # Disable verbose
            self.controller.disable_verbose()
            self.verbose_btn.setText("Enable")
            self.verbose_combo.setEnabled(True)
        else:
            # Enable verbose for selected duration
            hours = int(combo_text.replace("h", ""))
            self.controller.enable_verbose(hours)
            self.verbose_btn.setText("Disable")
            self.verbose_combo.setEnabled(False)

    def open_log_folder(self):
        """Open log folder in file manager"""
        import subprocess
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["xdg-open", str(LOG_DIR)])


def main():
    # DBus Qt integration MUST be before QApplication
    DBusQtMainLoop(set_as_default=True)

    # Enable high DPI scaling attributes (Qt 5.6+)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = FanControlGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
