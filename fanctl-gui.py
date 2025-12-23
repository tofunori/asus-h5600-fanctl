#!/usr/bin/env python3
"""
ASUS ProArt H5600QM Fan Control GUI - Modern Design with Temps
"""
import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import time

class FanControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🌀 ASUS Fan Control")
        self.root.geometry("1200x1400")
        self.root.resizable(True, True)
        self.root.minsize(450, 800)

        # Light mode colors for better visibility
        self.colors = {
            'bg': '#f5f5f5',
            'card': '#ffffff',
            'card_border': '#d0d0d0',
            'accent': '#0066cc',
            'text': '#1a1a1a',
            'text_dim': '#555555',
            'danger': '#cc0000',
            'warning': '#cc7700',
            'success': '#008800',
            'purple': '#7733aa',
        }

        self.root.configure(bg=self.colors['bg'])

        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=self.colors['bg'])
        style.configure('Card.TFrame', background=self.colors['card'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['text'], font=('Segoe UI', 11))
        style.configure('Header.TLabel', font=('Segoe UI', 24, 'bold'), foreground=self.colors['text'])
        style.configure('Sub.TLabel', foreground=self.colors['text_dim'], font=('Segoe UI', 10))
        style.configure('Status.TLabel', foreground=self.colors['accent'], font=('Segoe UI', 11, 'bold'))
        style.configure('Temp.TLabel', font=('Segoe UI', 18, 'bold'))
        style.configure('TempLabel.TLabel', font=('Segoe UI', 10), foreground=self.colors['text_dim'])

        style.configure('TButton', font=('Segoe UI', 11), padding=12, background=self.colors['card'])
        style.map('TButton', background=[('active', self.colors['accent'])])

        style.configure('TLabelframe', background=self.colors['card'], bordercolor=self.colors['card_border'])
        style.configure('TLabelframe.Label', background=self.colors['card'], foreground=self.colors['accent'], font=('Segoe UI', 11, 'bold'))

        style.configure('TRadiobutton', background=self.colors['card'], foreground=self.colors['text'], font=('Segoe UI', 11))
        style.configure('TCheckbutton', background=self.colors['card'], foreground=self.colors['text'], font=('Segoe UI', 11))
        style.configure('Horizontal.TScale', background=self.colors['card'], troughcolor=self.colors['card_border'])

        # Main container with padding
        main = ttk.Frame(root, padding=25)
        main.pack(fill='both', expand=True)

        # Header
        header_frame = ttk.Frame(main)
        header_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(header_frame, text="🌀 Fan Control", style='Header.TLabel').pack(side='left')

        # Subtitle
        ttk.Label(main, text="ASUS ProArt StudioBook H5600QM", style='Sub.TLabel').pack(anchor='w')

        # Temperature display
        temp_frame = ttk.LabelFrame(main, text="🌡️ Températures", padding=20)
        temp_frame.pack(fill='x', pady=15)

        temp_inner = ttk.Frame(temp_frame)
        temp_inner.pack(fill='x')

        # CPU Temp
        cpu_temp_frame = ttk.Frame(temp_inner)
        cpu_temp_frame.pack(side='left', expand=True, fill='x')
        ttk.Label(cpu_temp_frame, text="CPU", style='TempLabel.TLabel').pack()
        self.cpu_temp_var = tk.StringVar(value="--°C")
        self.cpu_temp_label = ttk.Label(cpu_temp_frame, textvariable=self.cpu_temp_var, style='Temp.TLabel')
        self.cpu_temp_label.pack()

        # Separator
        ttk.Frame(temp_inner, width=2, height=50).pack(side='left', padx=20)

        # GPU Temp
        gpu_temp_frame = ttk.Frame(temp_inner)
        gpu_temp_frame.pack(side='left', expand=True, fill='x')
        ttk.Label(gpu_temp_frame, text="GPU", style='TempLabel.TLabel').pack()
        self.gpu_temp_var = tk.StringVar(value="--°C")
        self.gpu_temp_label = ttk.Label(gpu_temp_frame, textvariable=self.gpu_temp_var, style='Temp.TLabel')
        self.gpu_temp_label.pack()

        # Status
        self.status_var = tk.StringVar(value="● Mode: Auto")
        ttk.Label(main, textvariable=self.status_var, style='Status.TLabel').pack(pady=10)

        # Mode frame
        mode_frame = ttk.LabelFrame(main, text="⚙️ Mode de contrôle", padding=15)
        mode_frame.pack(fill='x', pady=8)

        self.mode_var = tk.StringVar(value="auto")
        mode_btns = ttk.Frame(mode_frame)
        mode_btns.pack(fill='x')

        ttk.Radiobutton(mode_btns, text="🔄 Automatique", variable=self.mode_var,
                       value="auto", command=self.set_auto_mode).pack(side='left', expand=True, padx=5)
        ttk.Radiobutton(mode_btns, text="🎛️ Manuel", variable=self.mode_var,
                       value="manual", command=self.set_manual_mode).pack(side='left', expand=True, padx=5)

        # Presets frame
        presets_frame = ttk.LabelFrame(main, text="🎚️ Vitesse des ventilateurs", padding=15)
        presets_frame.pack(fill='x', pady=8)

        presets = [
            ("🔥 TURBO", 100, self.colors['danger']),
            ("⚡ Performance", 80, self.colors['warning']),
            ("⚖️ Balanced", 50, self.colors['accent']),
            ("🔇 Quiet", 30, self.colors['purple']),
            ("🤫 SILENT", 12, self.colors['text_dim']),
        ]

        for text, percent, color in presets:
            btn_frame = ttk.Frame(presets_frame)
            btn_frame.pack(fill='x', pady=3)
            btn = ttk.Button(btn_frame, text=f"{text} ({percent}%)",
                           command=lambda p=percent: self.set_fans_percent(p))
            btn.pack(fill='x')

        # Slider frame
        slider_frame = ttk.LabelFrame(main, text="📊 Vitesse personnalisée", padding=15)
        slider_frame.pack(fill='x', pady=8)

        self.slider_value = tk.IntVar(value=50)
        self.slider_label = ttk.Label(slider_frame, text="50%", font=('Segoe UI', 20, 'bold'))
        self.slider_label.pack(pady=5)

        self.slider = ttk.Scale(slider_frame, from_=10, to=100, variable=self.slider_value,
                               command=self.update_slider_label, orient='horizontal', length=350)
        self.slider.pack(pady=10)

        ttk.Button(slider_frame, text="✓ Appliquer", command=self.apply_custom).pack(pady=5)

        # CPU Options frame
        cpu_frame = ttk.LabelFrame(main, text="🖥️ Options CPU", padding=15)
        cpu_frame.pack(fill='x', pady=8)

        boost_row = ttk.Frame(cpu_frame)
        boost_row.pack(fill='x')

        self.boost_var = tk.BooleanVar(value=True)
        self.boost_check = ttk.Checkbutton(boost_row, text="🚀 CPU Boost (Turbo)",
                                          variable=self.boost_var,
                                          command=self.toggle_cpu_boost)
        self.boost_check.pack(side='left')

        self.boost_status = ttk.Label(boost_row, text="ON", foreground=self.colors['success'],
                                     font=('Segoe UI', 11, 'bold'))
        self.boost_status.pack(side='right')

        self.check_boost_status()

        # Warning
        warn_frame = ttk.Frame(main)
        warn_frame.pack(pady=15)
        ttk.Label(warn_frame, text="⚠️ Mode SILENT = surveillez les températures!",
                 foreground=self.colors['warning'], font=('Segoe UI', 9)).pack()

        # Start temperature monitoring
        self.running = True
        self.temp_thread = threading.Thread(target=self.update_temps, daemon=True)
        self.temp_thread.start()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.running = False
        self.root.destroy()

    def update_temps(self):
        while self.running:
            try:
                # CPU temp (k10temp)
                with open('/sys/class/hwmon/hwmon6/temp1_input', 'r') as f:
                    cpu_temp = int(f.read().strip()) // 1000
                    color = self.colors['success'] if cpu_temp < 60 else self.colors['warning'] if cpu_temp < 80 else self.colors['danger']
                    self.cpu_temp_var.set(f"{cpu_temp}°C")
                    self.cpu_temp_label.configure(foreground=color)
            except:
                self.cpu_temp_var.set("--°C")

            try:
                # GPU temp (amdgpu)
                with open('/sys/class/hwmon/hwmon5/temp1_input', 'r') as f:
                    gpu_temp = int(f.read().strip()) // 1000
                    color = self.colors['success'] if gpu_temp < 60 else self.colors['warning'] if gpu_temp < 80 else self.colors['danger']
                    self.gpu_temp_var.set(f"{gpu_temp}°C")
                    self.gpu_temp_label.configure(foreground=color)
            except:
                self.gpu_temp_var.set("--°C")

            time.sleep(2)

    def update_slider_label(self, value):
        self.slider_label.config(text=f"{int(float(value))}%")

    def run_cmd(self, cmd):
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            return True
        except:
            return False

    def enable_manual_mode(self):
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 1' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 1' | sudo tee /proc/acpi/call > /dev/null")

    def disable_manual_mode(self):
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 0' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 0' | sudo tee /proc/acpi/call > /dev/null")

    def set_fans(self, hex_value):
        self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 0 {hex_value}' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 1 {hex_value}' | sudo tee /proc/acpi/call > /dev/null")

    def set_fans_percent(self, percent):
        self.mode_var.set("manual")
        hex_value = hex(int(percent * 255 / 100))
        self.enable_manual_mode()
        self.set_fans(hex_value)
        self.status_var.set(f"● Mode: Manuel - {percent}%")

    def set_auto_mode(self):
        self.disable_manual_mode()
        self.run_cmd("echo 1 | sudo tee /sys/devices/platform/h5600_fan/thermal_policy > /dev/null 2>&1")
        self.status_var.set("● Mode: Automatique")

    def set_manual_mode(self):
        self.enable_manual_mode()
        self.status_var.set("● Mode: Manuel")

    def apply_custom(self):
        self.set_fans_percent(self.slider_value.get())

    def check_boost_status(self):
        try:
            with open('/sys/devices/system/cpu/cpufreq/boost', 'r') as f:
                enabled = f.read().strip() == '1'
                self.boost_var.set(enabled)
                self.boost_status.config(text="ON" if enabled else "OFF",
                                        foreground=self.colors['success'] if enabled else self.colors['danger'])
        except:
            self.boost_status.config(text="N/A", foreground=self.colors['text_dim'])

    def toggle_cpu_boost(self):
        new_state = self.boost_var.get()
        value = "1" if new_state else "0"
        if self.run_cmd(f"echo {value} | sudo tee /sys/devices/system/cpu/cpufreq/boost > /dev/null"):
            self.boost_status.config(text="ON" if new_state else "OFF",
                                    foreground=self.colors['success'] if new_state else self.colors['danger'])
        else:
            self.boost_var.set(not new_state)

def main():
    root = tk.Tk()
    app = FanControlGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
