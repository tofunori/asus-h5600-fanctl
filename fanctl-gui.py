#!/usr/bin/env python3
"""
ASUS ProArt H5600QM Fan Control GUI - PyQt5 System Tray for KDE
"""
import sys
import subprocess
import threading
import time

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QSlider, QCheckBox,
                             QGroupBox, QRadioButton, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

class FanController(QObject):
    """Handles fan control in background thread"""
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.manual_mode = False
        self.cpu_percent = 50
        self.gpu_percent = 50
        self.maintain_thread = None

    def run_cmd(self, cmd):
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            return True
        except:
            return False

    def enable_manual(self):
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 1' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 1' | sudo tee /proc/acpi/call > /dev/null")

    def disable_manual(self):
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 0' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 0' | sudo tee /proc/acpi/call > /dev/null")

    def set_fans(self):
        cpu_hex = hex(int(self.cpu_percent * 255 / 100))
        gpu_hex = hex(int(self.gpu_percent * 255 / 100))
        self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 0 {cpu_hex}' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 1 {gpu_hex}' | sudo tee /proc/acpi/call > /dev/null")

    def maintain_loop(self):
        while self.running and self.manual_mode:
            self.enable_manual()
            self.set_fans()
            time.sleep(0.1)

    def start_manual(self, cpu, gpu):
        self.cpu_percent = cpu
        self.gpu_percent = gpu
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 0' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 0' | sudo tee /proc/acpi/call > /dev/null")
        time.sleep(0.3)
        self.enable_manual()
        self.set_fans()

        if not self.manual_mode:
            self.manual_mode = True
            self.maintain_thread = threading.Thread(target=self.maintain_loop, daemon=True)
            self.maintain_thread.start()

        if cpu == gpu:
            self.status_changed.emit(f"Manuel - {cpu}%")
        else:
            self.status_changed.emit(f"CPU:{cpu}% GPU:{gpu}%")

    def set_auto(self):
        self.manual_mode = False
        self.disable_manual()
        self.run_cmd("echo 1 | sudo tee /sys/devices/platform/h5600_fan/thermal_policy > /dev/null 2>&1")
        self.status_changed.emit("Automatique")

    def stop(self):
        self.running = False
        self.manual_mode = False


class FanControlGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = FanController()
        self.controller.status_changed.connect(self.update_status)
        self.linked = True

        self.init_ui()
        self.init_tray()
        self.start_temp_monitor()

    def init_ui(self):
        self.setWindowTitle("ASUS Fan Control")
        self.setMinimumSize(400, 600)
        self.resize(450, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)

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

        # Mode
        mode_group = QGroupBox("Mode")
        mode_layout = QHBoxLayout(mode_group)
        self.auto_radio = QRadioButton("Automatique")
        self.auto_radio.setChecked(True)
        self.auto_radio.clicked.connect(self.on_auto_mode)
        self.manual_radio = QRadioButton("Manuel")
        self.manual_radio.clicked.connect(self.on_manual_mode)
        mode_layout.addWidget(self.auto_radio)
        mode_layout.addWidget(self.manual_radio)
        layout.addWidget(mode_group)

        # Presets
        presets_group = QGroupBox("Presets")
        presets_layout = QHBoxLayout(presets_group)
        for name, percent in [("TURBO", 100), ("Perf", 80), ("Balance", 50), ("Quiet", 30), ("Silent", 12)]:
            btn = QPushButton(f"{name}\n{percent}%")
            btn.clicked.connect(lambda checked, p=percent: self.set_preset(p))
            presets_layout.addWidget(btn)
        layout.addWidget(presets_group)

        # Individual control
        individual_group = QGroupBox("Controle individuel")
        individual_layout = QVBoxLayout(individual_group)

        self.link_check = QCheckBox("Lier les ventilateurs")
        self.link_check.setChecked(True)
        self.link_check.stateChanged.connect(self.on_link_changed)
        individual_layout.addWidget(self.link_check)

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
        individual_layout.addLayout(cpu_layout)

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
        individual_layout.addLayout(gpu_layout)

        apply_btn = QPushButton("Appliquer")
        apply_btn.clicked.connect(self.apply_individual)
        individual_layout.addWidget(apply_btn)

        layout.addWidget(individual_group)

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

        # Warning
        warning = QLabel("Mode SILENT = surveillez les temperatures!")
        warning.setStyleSheet("color: orange;")
        layout.addWidget(warning)

        layout.addStretch()

    def create_tray_icon(self):
        """Create a simple colored icon for tray"""
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

        # Tray menu
        tray_menu = QMenu()

        show_action = QAction("Afficher", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        for name, percent in [("TURBO 100%", 100), ("Performance 80%", 80),
                               ("Balanced 50%", 50), ("Quiet 30%", 30), ("Silent 12%", 12)]:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, p=percent: self.set_preset(p))
            tray_menu.addAction(action)

        tray_menu.addSeparator()

        auto_action = QAction("Auto", self)
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
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """Minimize to tray instead of closing"""
        event.ignore()
        self.hide()

    def quit_app(self):
        self.controller.stop()
        self.tray_icon.hide()
        QApplication.quit()

    def start_temp_monitor(self):
        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self.update_temps)
        self.temp_timer.start(2000)
        self.update_temps()

    def update_temps(self):
        try:
            with open('/sys/class/hwmon/hwmon6/temp1_input', 'r') as f:
                temp = int(f.read().strip()) // 1000
                color = "green" if temp < 60 else "orange" if temp < 80 else "red"
                self.cpu_temp_label.setText(f"{temp}°C")
                self.cpu_temp_label.setStyleSheet(f"color: {color};")
        except:
            self.cpu_temp_label.setText("--°C")

        try:
            with open('/sys/class/hwmon/hwmon5/temp1_input', 'r') as f:
                temp = int(f.read().strip()) // 1000
                color = "green" if temp < 60 else "orange" if temp < 80 else "red"
                self.gpu_temp_label.setText(f"{temp}°C")
                self.gpu_temp_label.setStyleSheet(f"color: {color};")
        except:
            self.gpu_temp_label.setText("--°C")

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

    def set_preset(self, percent):
        self.cpu_slider.setValue(percent)
        self.gpu_slider.setValue(percent)
        self.manual_radio.setChecked(True)
        threading.Thread(target=self.controller.start_manual, args=(percent, percent), daemon=True).start()

    def apply_individual(self):
        cpu = self.cpu_slider.value()
        gpu = self.gpu_slider.value()
        self.manual_radio.setChecked(True)
        threading.Thread(target=self.controller.start_manual, args=(cpu, gpu), daemon=True).start()

    def on_auto_mode(self):
        self.auto_radio.setChecked(True)
        threading.Thread(target=self.controller.set_auto, daemon=True).start()

    def on_manual_mode(self):
        self.apply_individual()

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


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = FanControlGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
