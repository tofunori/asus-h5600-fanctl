#!/usr/bin/env python3
"""
ASUS ProArt H5600QM Fan Control GUI - With Auto Profiles
"""
import sys
import subprocess
import threading
import time
import os

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QSlider, QCheckBox,
                             QGroupBox, QRadioButton, QSystemTrayIcon, QMenu, QAction,
                             QComboBox, QTabWidget, QSpinBox, QGridLayout, QDialog)
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

LIGHT_STYLE = ""  # Use system default

# Fan curve profiles: (temp_threshold, fan_percent)
# Optimized with 85°C threshold for smoother transitions
# Hysteresis of 5°C applied in control loop to prevent oscillations
PROFILES = {
    "Silent": [
        (0, 0), (55, 0), (60, 15), (70, 30), (80, 50), (85, 75), (90, 100)
    ],
    "Quiet": [
        (0, 0), (55, 0), (60, 20), (70, 40), (80, 60), (85, 80), (90, 100)
    ],
    "Balanced": [
        (0, 0), (50, 0), (60, 25), (70, 50), (80, 70), (85, 85), (90, 100)
    ],
    "Performance": [
        (0, 20), (50, 20), (60, 35), (70, 55), (80, 75), (85, 90), (90, 100)
    ],
    "Turbo": [
        (0, 25), (50, 25), (60, 45), (70, 70), (80, 90), (85, 100), (90, 100)
    ],
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


class CurveWidget(QWidget):
    """Widget to draw fan curve visualization"""
    def __init__(self, profile_name, curve_data, parent=None):
        super().__init__(parent)
        self.profile_name = profile_name
        self.curve_data = curve_data
        self.setFixedSize(350, 250)

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
        title_font = QFont("Segoe UI", 11, QFont.Bold)
        painter.setFont(title_font)
        painter.drawText(left_margin, 20, f"Profil: {self.profile_name}")

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
        label_font = QFont("Segoe UI", 8)
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

        for temp, fan_pct in self.curve_data:
            x = left_margin + (temp / 100.0) * width
            y = top_margin + height - (fan_pct / 100.0) * height
            points.append(QPointF(x, y))

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


class CurveDialog(QDialog):
    """Dialog to show fan curve visualization"""
    def __init__(self, profile_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Courbe - {profile_name}")
        self.setFixedSize(370, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Get curve data
        curve_data = PROFILES.get(profile_name, [])

        # Add curve widget
        curve_widget = CurveWidget(profile_name, curve_data)
        layout.addWidget(curve_widget)

        # Add close button
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)


class FanController(QObject):
    """Handles fan control in background thread"""
    status_changed = pyqtSignal(str)
    temps_changed = pyqtSignal(int, int)  # cpu_temp, gpu_temp

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
        # Hysteresis tracking
        self.last_fan_speed = 0
        self.last_max_temp = 0

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

    def control_loop(self):
        """Main control loop - handles both manual and profile modes"""
        while self.running:
            self.read_temps()

            if self.mode == "manual":
                self.enable_manual()
                self.set_fans(self.cpu_percent, self.gpu_percent)
                time.sleep(0.1)

            elif self.mode == "profile":
                curve = PROFILES.get(self.profile_name, PROFILES["Balanced"])
                # Use max temp for both fans (conservative approach)
                max_temp = max(self.cpu_temp, self.gpu_temp)
                target_speed = self.get_fan_speed_for_temp(max_temp, curve)

                # Apply hysteresis to prevent oscillations
                if target_speed > self.last_fan_speed:
                    # Temperature rising - apply immediately
                    fan_speed = target_speed
                    self.last_max_temp = max_temp
                elif max_temp <= self.last_max_temp - HYSTERESIS:
                    # Temperature dropped enough - allow fan to slow down
                    fan_speed = target_speed
                    self.last_max_temp = max_temp
                else:
                    # Keep current speed (hysteresis zone)
                    fan_speed = self.last_fan_speed

                self.last_fan_speed = fan_speed
                self.enable_manual()
                self.set_fans(fan_speed, fan_speed)

                self.status_changed.emit(f"{self.profile_name} - {fan_speed}% ({max_temp}°C)")
                time.sleep(0.5)  # Profile mode can be slower

            else:  # auto mode
                time.sleep(1)

    def start_control(self):
        if self.control_thread is None or not self.control_thread.is_alive():
            self.control_thread = threading.Thread(target=self.control_loop, daemon=True)
            self.control_thread.start()

    def set_manual(self, cpu, gpu):
        self.mode = "manual"
        self.cpu_percent = cpu
        self.gpu_percent = gpu
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
        self.start_control()
        self.status_changed.emit(f"{profile_name} - En attente...")

    def set_auto(self):
        self.mode = "auto"
        self.disable_manual()
        self.run_cmd("echo 1 | sudo tee /sys/devices/platform/h5600_fan/thermal_policy > /dev/null 2>&1")
        self.status_changed.emit("Automatique (EC)")

    def stop(self):
        self.running = False


class FanControlGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = FanController()
        self.controller.status_changed.connect(self.update_status)
        self.controller.temps_changed.connect(self.update_temps)
        self.linked = True

        self.init_ui()
        self.init_tray()
        self.controller.start_control()

    def init_ui(self):
        self.setWindowTitle("ASUS Fan Control")
        self.setMinimumSize(420, 650)
        self.resize(450, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)

        # Header
        header = QLabel("ASUS Fan Control")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
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
        self.cpu_temp_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        cpu_temp_layout.addWidget(self.cpu_temp_label)
        temp_layout.addLayout(cpu_temp_layout)

        gpu_temp_layout = QVBoxLayout()
        gpu_temp_layout.addWidget(QLabel("GPU"))
        self.gpu_temp_label = QLabel("--°C")
        self.gpu_temp_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        gpu_temp_layout.addWidget(self.gpu_temp_label)
        temp_layout.addLayout(gpu_temp_layout)

        layout.addWidget(temp_group)

        # Status
        self.status_label = QLabel("Mode: Automatique")
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.status_label.setStyleSheet("color: #0066cc;")
        layout.addWidget(self.status_label)

        # Tabs for different modes
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Tab 1: Profiles (Auto based on temp)
        profile_tab = QWidget()
        profile_layout = QVBoxLayout(profile_tab)

        profile_desc = QLabel("Ajustement automatique selon la temperature:")
        profile_layout.addWidget(profile_desc)

        # Profile buttons
        profile_grid = QGridLayout()
        profiles = [
            ("Silent", "0% <60°C\nTres silencieux"),
            ("Quiet", "0% <60°C\nSilencieux"),
            ("Balanced", "0% <60°C\nEquilibre"),
            ("Performance", "15% min\nPerformant"),
            ("Turbo", "15% min\nMaximum"),
        ]
        for i, (name, desc) in enumerate(profiles):
            btn = QPushButton(f"{name}\n{desc}")
            btn.setMinimumHeight(60)
            btn.clicked.connect(lambda checked, n=name: self.set_profile(n))
            # Add right-click context menu to show curve
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, n=name, b=btn: self.show_curve_menu(pos, n, b)
            )
            profile_grid.addWidget(btn, i // 3, i % 3)

        profile_layout.addLayout(profile_grid)

        # Show current curve
        self.curve_label = QLabel("")
        self.curve_label.setStyleSheet("color: gray; font-size: 10px;")
        profile_layout.addWidget(self.curve_label)

        profile_layout.addStretch()
        tabs.addTab(profile_tab, "Profils Auto")

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
        tabs.addTab(manual_tab, "Manuel")

        # Tab 3: EC Auto
        auto_tab = QWidget()
        auto_layout = QVBoxLayout(auto_tab)
        auto_desc = QLabel("Laisser le controleur embarque (EC) gerer les ventilateurs.\n\n"
                          "C'est le mode par defaut du BIOS.")
        auto_layout.addWidget(auto_desc)
        auto_btn = QPushButton("Activer Mode Auto EC")
        auto_btn.clicked.connect(self.on_auto_mode)
        auto_layout.addWidget(auto_btn)
        auto_layout.addStretch()
        tabs.addTab(auto_tab, "Auto EC")

        # CPU Boost
        boost_group = QGroupBox("CPU Boost")
        boost_layout = QHBoxLayout(boost_group)
        self.boost_check = QCheckBox("Turbo Boost")
        self.boost_check.stateChanged.connect(self.toggle_boost)
        boost_layout.addWidget(self.boost_check)
        self.boost_status = QLabel("ON")
        self.boost_status.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.boost_status.setStyleSheet("color: green;")
        boost_layout.addWidget(self.boost_status)
        layout.addWidget(boost_group)

        self.check_boost()

        # Theme selector
        theme_group = QGroupBox("Apparence")
        theme_layout = QHBoxLayout(theme_group)
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Systeme", "Sombre", "Clair"])
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_combo)
        layout.addWidget(theme_group)

        # Load saved theme
        self.settings = QSettings("ASUS", "FanControl")
        saved_theme = self.settings.value("theme", 0, type=int)
        self.theme_combo.setCurrentIndex(saved_theme)
        self.apply_theme(saved_theme)

        # Warning
        warning = QLabel("Mode SILENT = surveillez les temperatures!")
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
        profiles_menu = QMenu("Profils Auto", self)
        for name in PROFILES.keys():
            action = QAction(name, self)
            action.triggered.connect(lambda checked, n=name: self.set_profile(n))
            profiles_menu.addAction(action)
        tray_menu.addMenu(profiles_menu)

        tray_menu.addSeparator()

        # Manual presets
        for name, percent in [("Manuel 100%", 100), ("Manuel 50%", 50), ("Manuel 30%", 30)]:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, p=percent: self.set_preset(p))
            tray_menu.addAction(action)

        tray_menu.addSeparator()

        auto_action = QAction("Auto EC", self)
        auto_action.triggered.connect(self.on_auto_mode)
        tray_menu.addAction(auto_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quitter", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_window()

    def show_window(self):
        # Position window near tray icon (like g-helper)
        tray_geo = self.tray_icon.geometry()
        if tray_geo.isValid():
            # Get screen geometry
            screen = QApplication.primaryScreen().geometry()

            # Calculate position: above tray icon, aligned to right
            x = tray_geo.x() - self.width() + tray_geo.width()
            y = tray_geo.y() - self.height() - 10  # 10px margin above tray

            # Keep window on screen
            if x < 0:
                x = 10
            if x + self.width() > screen.width():
                x = screen.width() - self.width() - 10
            if y < 0:
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
        curve = PROFILES.get(name, [])
        curve_str = " | ".join([f"{t}°C:{f}%" for t, f in curve])
        self.curve_label.setText(f"Courbe: {curve_str}")
        threading.Thread(target=self.controller.set_profile, args=(name,), daemon=True).start()

    def show_curve_menu(self, pos, profile_name, button):
        """Show context menu with option to view curve"""
        menu = QMenu(self)
        show_curve_action = menu.addAction("Voir la courbe")
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
        self.curve_label.setText("")
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
        if index == 1:  # Sombre
            app.setStyleSheet(DARK_STYLE)
        elif index == 2:  # Clair
            app.setStyleSheet(LIGHT_STYLE)
        else:  # Systeme
            app.setStyleSheet("")


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = FanControlGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
