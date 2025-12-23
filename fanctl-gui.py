#!/usr/bin/env python3
"""
ASUS ProArt H5600QM Fan Control GUI
"""
import tkinter as tk
from tkinter import ttk
import subprocess
import os

class FanControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ASUS H5600 Fan Control")
        self.root.geometry("380x550")
        self.root.resizable(False, False)

        self.manual_mode = False
        self.cpu_boost_enabled = True

        # Style
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 10), padding=8)
        style.configure('TLabel', font=('Arial', 10))
        style.configure('Header.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 9))

        # Header
        header = ttk.Label(root, text="🌀 Fan Control", style='Header.TLabel')
        header.pack(pady=10)

        # Status
        self.status_var = tk.StringVar(value="Mode: Auto")
        status_label = ttk.Label(root, textvariable=self.status_var, style='Status.TLabel')
        status_label.pack(pady=5)

        # Mode frame (Auto/Manuel)
        mode_frame = ttk.LabelFrame(root, text="Mode", padding=10)
        mode_frame.pack(fill='x', padx=20, pady=5)

        self.mode_var = tk.StringVar(value="auto")
        btn_auto = ttk.Radiobutton(mode_frame, text="🔄 Auto (EC contrôle)",
                                   variable=self.mode_var, value="auto",
                                   command=self.set_auto_mode)
        btn_auto.pack(anchor='w', pady=2)

        btn_manual = ttk.Radiobutton(mode_frame, text="🎛️ Manuel (vous contrôlez)",
                                     variable=self.mode_var, value="manual",
                                     command=self.set_manual_mode)
        btn_manual.pack(anchor='w', pady=2)

        # Preset buttons frame
        self.presets_frame = ttk.LabelFrame(root, text="Presets (Mode Manuel)", padding=10)
        self.presets_frame.pack(fill='x', padx=20, pady=5)

        btn_turbo = ttk.Button(self.presets_frame, text="🔥 TURBO (100%)",
                               command=lambda: self.set_fans_percent(100))
        btn_turbo.pack(fill='x', pady=2)

        btn_perf = ttk.Button(self.presets_frame, text="⚡ Performance (80%)",
                              command=lambda: self.set_fans_percent(80))
        btn_perf.pack(fill='x', pady=2)

        btn_balanced = ttk.Button(self.presets_frame, text="⚖️ Balanced (50%)",
                                  command=lambda: self.set_fans_percent(50))
        btn_balanced.pack(fill='x', pady=2)

        btn_quiet = ttk.Button(self.presets_frame, text="🔇 Quiet (30%)",
                               command=lambda: self.set_fans_percent(30))
        btn_quiet.pack(fill='x', pady=2)

        btn_silent = ttk.Button(self.presets_frame, text="🤫 SILENT (Minimum)",
                                command=lambda: self.set_fans_percent(12))
        btn_silent.pack(fill='x', pady=2)

        # Custom slider frame
        slider_frame = ttk.LabelFrame(root, text="Custom Speed", padding=10)
        slider_frame.pack(fill='x', padx=20, pady=5)

        self.slider_value = tk.IntVar(value=50)
        self.slider_label = ttk.Label(slider_frame, text="50%")
        self.slider_label.pack()

        self.slider = ttk.Scale(slider_frame, from_=10, to=100,
                                variable=self.slider_value,
                                command=self.update_slider_label)
        self.slider.pack(fill='x', pady=5)

        btn_apply = ttk.Button(slider_frame, text="Appliquer",
                               command=self.apply_custom)
        btn_apply.pack(pady=3)

        # CPU Boost frame
        boost_frame = ttk.LabelFrame(root, text="CPU Options", padding=10)
        boost_frame.pack(fill='x', padx=20, pady=5)

        self.boost_var = tk.BooleanVar(value=True)
        self.boost_check = ttk.Checkbutton(boost_frame, text="🚀 CPU Boost activé",
                                           variable=self.boost_var,
                                           command=self.toggle_cpu_boost)
        self.boost_check.pack(anchor='w')

        self.boost_status = ttk.Label(boost_frame, text="", style='Status.TLabel')
        self.boost_status.pack(anchor='w')

        # Check current boost status
        self.check_boost_status()

        # Info label
        info = ttk.Label(root, text="⚠️ Mode Silent = fans très lentes, surveillez les températures!",
                        font=('Arial', 8), foreground='gray')
        info.pack(pady=10)

    def update_slider_label(self, value):
        self.slider_label.config(text=f"{int(float(value))}%")

    def run_cmd(self, cmd):
        try:
            result = subprocess.run(cmd, shell=True, check=True,
                          capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def enable_manual_mode(self):
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 1' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 1' | sudo tee /proc/acpi/call > /dev/null")
        self.manual_mode = True

    def disable_manual_mode(self):
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 0' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 0' | sudo tee /proc/acpi/call > /dev/null")
        self.manual_mode = False

    def set_fans(self, hex_value):
        self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 0 {hex_value}' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 1 {hex_value}' | sudo tee /proc/acpi/call > /dev/null")

    def set_fans_percent(self, percent):
        if self.mode_var.get() == "auto":
            self.mode_var.set("manual")
            self.set_manual_mode()

        hex_value = hex(int(percent * 255 / 100))
        self.enable_manual_mode()
        self.set_fans(hex_value)
        self.status_var.set(f"Mode: Manuel - Fans {percent}%")

    def set_auto_mode(self):
        self.disable_manual_mode()
        self.run_cmd("echo 1 | sudo tee /sys/devices/platform/h5600_fan/thermal_policy > /dev/null 2>&1")
        self.status_var.set("Mode: Auto (EC contrôle)")

    def set_manual_mode(self):
        self.enable_manual_mode()
        self.status_var.set("Mode: Manuel - Choisissez une vitesse")

    def apply_custom(self):
        percent = self.slider_value.get()
        self.set_fans_percent(percent)

    def check_boost_status(self):
        try:
            with open('/sys/devices/system/cpu/cpufreq/boost', 'r') as f:
                status = f.read().strip()
                self.cpu_boost_enabled = (status == '1')
                self.boost_var.set(self.cpu_boost_enabled)
                self.boost_status.config(text=f"(Boost: {'ON' if self.cpu_boost_enabled else 'OFF'})")
        except:
            self.boost_status.config(text="(Status inconnu)")

    def toggle_cpu_boost(self):
        new_state = self.boost_var.get()
        value = "1" if new_state else "0"
        success = self.run_cmd(f"echo {value} | sudo tee /sys/devices/system/cpu/cpufreq/boost > /dev/null")

        if success:
            self.cpu_boost_enabled = new_state
            self.boost_status.config(text=f"(Boost: {'ON' if new_state else 'OFF'})")
        else:
            self.boost_var.set(not new_state)  # Revert
            self.boost_status.config(text="(Erreur!)")

def main():
    root = tk.Tk()
    app = FanControlGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
