#!/usr/bin/env python3
"""
ASUS ProArt H5600QM Fan Control GUI - With System Tray Support
"""
import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import time

# System tray support
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

class FanControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ASUS Fan Control")
        self.root.geometry("500x900")
        self.root.resizable(True, True)
        self.root.minsize(450, 800)

        # Manual mode state
        self.manual_mode_active = False
        self.cpu_fan_percent = 50
        self.gpu_fan_percent = 50
        self.fans_linked = True
        self.fan_maintain_thread = None

        # System tray
        self.tray_icon = None
        self.window_visible = True

        # Light mode colors
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
        style.configure('Header.TLabel', font=('Segoe UI', 20, 'bold'), foreground=self.colors['text'])
        style.configure('Sub.TLabel', foreground=self.colors['text_dim'], font=('Segoe UI', 10))
        style.configure('Status.TLabel', foreground=self.colors['accent'], font=('Segoe UI', 11, 'bold'))
        style.configure('Temp.TLabel', font=('Segoe UI', 18, 'bold'))
        style.configure('TempLabel.TLabel', font=('Segoe UI', 10), foreground=self.colors['text_dim'])

        style.configure('TButton', font=('Segoe UI', 10), padding=8, background=self.colors['card'])
        style.map('TButton', background=[('active', self.colors['accent'])])

        style.configure('TLabelframe', background=self.colors['card'], bordercolor=self.colors['card_border'])
        style.configure('TLabelframe.Label', background=self.colors['card'], foreground=self.colors['accent'], font=('Segoe UI', 10, 'bold'))

        style.configure('TRadiobutton', background=self.colors['card'], foreground=self.colors['text'], font=('Segoe UI', 10))
        style.configure('TCheckbutton', background=self.colors['card'], foreground=self.colors['text'], font=('Segoe UI', 10))
        style.configure('Horizontal.TScale', background=self.colors['card'], troughcolor=self.colors['card_border'])

        # Main container
        main = ttk.Frame(root, padding=15)
        main.pack(fill='both', expand=True)

        # Header with minimize button
        header_frame = ttk.Frame(main)
        header_frame.pack(fill='x', pady=(0, 5))

        ttk.Label(header_frame, text="ASUS Fan Control", style='Header.TLabel').pack(side='left')

        if TRAY_AVAILABLE:
            ttk.Button(header_frame, text="Minimiser", command=self.minimize_to_tray).pack(side='right')

        # Subtitle
        ttk.Label(main, text="ProArt StudioBook H5600QM", style='Sub.TLabel').pack(anchor='w')

        # Temperature display
        temp_frame = ttk.LabelFrame(main, text="Temperatures", padding=10)
        temp_frame.pack(fill='x', pady=8)

        temp_inner = ttk.Frame(temp_frame)
        temp_inner.pack(fill='x')

        # CPU Temp
        cpu_temp_frame = ttk.Frame(temp_inner)
        cpu_temp_frame.pack(side='left', expand=True, fill='x')
        ttk.Label(cpu_temp_frame, text="CPU", style='TempLabel.TLabel').pack()
        self.cpu_temp_var = tk.StringVar(value="--C")
        self.cpu_temp_label = ttk.Label(cpu_temp_frame, textvariable=self.cpu_temp_var, style='Temp.TLabel')
        self.cpu_temp_label.pack()

        # GPU Temp
        gpu_temp_frame = ttk.Frame(temp_inner)
        gpu_temp_frame.pack(side='left', expand=True, fill='x')
        ttk.Label(gpu_temp_frame, text="GPU", style='TempLabel.TLabel').pack()
        self.gpu_temp_var = tk.StringVar(value="--C")
        self.gpu_temp_label = ttk.Label(gpu_temp_frame, textvariable=self.gpu_temp_var, style='Temp.TLabel')
        self.gpu_temp_label.pack()

        # Status
        self.status_var = tk.StringVar(value="Mode: Auto")
        ttk.Label(main, textvariable=self.status_var, style='Status.TLabel').pack(pady=5)

        # Mode frame
        mode_frame = ttk.LabelFrame(main, text="Mode", padding=10)
        mode_frame.pack(fill='x', pady=5)

        self.mode_var = tk.StringVar(value="auto")
        mode_btns = ttk.Frame(mode_frame)
        mode_btns.pack(fill='x')

        ttk.Radiobutton(mode_btns, text="Automatique", variable=self.mode_var,
                       value="auto", command=self.set_auto_mode).pack(side='left', expand=True)
        ttk.Radiobutton(mode_btns, text="Manuel", variable=self.mode_var,
                       value="manual", command=self.set_manual_mode).pack(side='left', expand=True)

        # Presets frame
        presets_frame = ttk.LabelFrame(main, text="Presets", padding=10)
        presets_frame.pack(fill='x', pady=5)

        presets_row = ttk.Frame(presets_frame)
        presets_row.pack(fill='x')

        presets = [("TURBO", 100), ("Perf", 80), ("Balance", 50), ("Quiet", 30), ("Silent", 12)]
        for text, percent in presets:
            ttk.Button(presets_row, text=f"{text}\n{percent}%",
                      command=lambda p=percent: self.set_fans_percent(p)).pack(side='left', expand=True, padx=2)

        # Individual fan control
        individual_frame = ttk.LabelFrame(main, text="Controle individuel", padding=10)
        individual_frame.pack(fill='x', pady=5)

        # Link checkbox
        self.link_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(individual_frame, text="Lier les ventilateurs",
                       variable=self.link_var, command=self.toggle_link).pack(anchor='w')

        # CPU Fan slider
        cpu_row = ttk.Frame(individual_frame)
        cpu_row.pack(fill='x', pady=5)
        ttk.Label(cpu_row, text="CPU:", width=5).pack(side='left')
        self.cpu_slider_value = tk.IntVar(value=50)
        self.cpu_slider_label = ttk.Label(cpu_row, text="50%", width=5)
        self.cpu_slider_label.pack(side='left')
        self.cpu_slider = ttk.Scale(cpu_row, from_=10, to=100, variable=self.cpu_slider_value,
                                   command=self.update_cpu_slider, orient='horizontal')
        self.cpu_slider.pack(side='left', fill='x', expand=True, padx=5)

        # GPU Fan slider
        gpu_row = ttk.Frame(individual_frame)
        gpu_row.pack(fill='x', pady=5)
        ttk.Label(gpu_row, text="GPU:", width=5).pack(side='left')
        self.gpu_slider_value = tk.IntVar(value=50)
        self.gpu_slider_label = ttk.Label(gpu_row, text="50%", width=5)
        self.gpu_slider_label.pack(side='left')
        self.gpu_slider = ttk.Scale(gpu_row, from_=10, to=100, variable=self.gpu_slider_value,
                                   command=self.update_gpu_slider, orient='horizontal')
        self.gpu_slider.pack(side='left', fill='x', expand=True, padx=5)

        ttk.Button(individual_frame, text="Appliquer", command=self.apply_individual).pack(pady=5)

        # CPU Boost
        boost_frame = ttk.LabelFrame(main, text="CPU Boost", padding=10)
        boost_frame.pack(fill='x', pady=5)

        boost_row = ttk.Frame(boost_frame)
        boost_row.pack(fill='x')

        self.boost_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(boost_row, text="Turbo Boost", variable=self.boost_var,
                       command=self.toggle_cpu_boost).pack(side='left')
        self.boost_status = ttk.Label(boost_row, text="ON", foreground=self.colors['success'], font=('Segoe UI', 10, 'bold'))
        self.boost_status.pack(side='right')

        self.check_boost_status()

        # Warning
        ttk.Label(main, text="Mode SILENT = surveillez les temperatures!",
                 foreground=self.colors['warning'], font=('Segoe UI', 9)).pack(pady=5)

        # Start threads
        self.running = True
        self.temp_thread = threading.Thread(target=self.update_temps, daemon=True)
        self.temp_thread.start()

        # Setup system tray
        if TRAY_AVAILABLE:
            self.setup_tray()

        # Handle window close - minimize to tray instead of closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_button)

    def create_tray_image(self):
        """Create a simple fan icon for the tray"""
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # Draw a simple circular fan icon
        draw.ellipse([4, 4, size-4, size-4], fill='#0066cc', outline='#003366', width=2)
        draw.ellipse([size//2-8, size//2-8, size//2+8, size//2+8], fill='white')
        return image

    def setup_tray(self):
        """Setup system tray icon"""
        image = self.create_tray_image()

        menu = pystray.Menu(
            pystray.MenuItem("Afficher", self.show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("TURBO 100%", lambda: self.tray_set_fans(100)),
            pystray.MenuItem("Performance 80%", lambda: self.tray_set_fans(80)),
            pystray.MenuItem("Balanced 50%", lambda: self.tray_set_fans(50)),
            pystray.MenuItem("Quiet 30%", lambda: self.tray_set_fans(30)),
            pystray.MenuItem("Silent 12%", lambda: self.tray_set_fans(12)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Auto", self.tray_set_auto),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quitter", self.quit_app)
        )

        self.tray_icon = pystray.Icon("fanctl", image, "ASUS Fan Control", menu)

        # Run tray in separate thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def tray_set_fans(self, percent):
        """Set fans from tray menu"""
        self.cpu_fan_percent = percent
        self.gpu_fan_percent = percent
        self.root.after(0, lambda: self.cpu_slider_value.set(percent))
        self.root.after(0, lambda: self.gpu_slider_value.set(percent))
        self.root.after(0, lambda: self.cpu_slider_label.config(text=f"{percent}%"))
        self.root.after(0, lambda: self.gpu_slider_label.config(text=f"{percent}%"))
        self.root.after(0, lambda: self.start_manual_mode())
        self.root.after(0, lambda: self.status_var.set(f"Mode: Manuel - {percent}%"))

    def tray_set_auto(self):
        """Set auto mode from tray"""
        self.root.after(0, self.set_auto_mode)

    def minimize_to_tray(self):
        """Minimize window to system tray"""
        if TRAY_AVAILABLE and self.tray_icon:
            self.root.withdraw()
            self.window_visible = False

    def show_window(self):
        """Show window from tray"""
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.root.lift)
        self.window_visible = True

    def on_close_button(self):
        """Handle window close button - minimize to tray if available"""
        if TRAY_AVAILABLE:
            self.minimize_to_tray()
        else:
            self.quit_app()

    def quit_app(self):
        """Completely quit the application"""
        self.running = False
        self.manual_mode_active = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()

    def maintain_fan_speed(self):
        """Background thread that continuously sends fan speed commands"""
        while self.running and self.manual_mode_active:
            cpu_hex = hex(int(self.cpu_fan_percent * 255 / 100))
            gpu_hex = hex(int(self.gpu_fan_percent * 255 / 100))
            self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 1' | sudo tee /proc/acpi/call > /dev/null")
            self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 1' | sudo tee /proc/acpi/call > /dev/null")
            self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 0 {cpu_hex}' | sudo tee /proc/acpi/call > /dev/null")
            self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 1 {gpu_hex}' | sudo tee /proc/acpi/call > /dev/null")
            time.sleep(0.1)

    def update_temps(self):
        while self.running:
            try:
                with open('/sys/class/hwmon/hwmon6/temp1_input', 'r') as f:
                    cpu_temp = int(f.read().strip()) // 1000
                    color = self.colors['success'] if cpu_temp < 60 else self.colors['warning'] if cpu_temp < 80 else self.colors['danger']
                    self.cpu_temp_var.set(f"{cpu_temp}C")
                    self.cpu_temp_label.configure(foreground=color)
            except:
                self.cpu_temp_var.set("--C")

            try:
                with open('/sys/class/hwmon/hwmon5/temp1_input', 'r') as f:
                    gpu_temp = int(f.read().strip()) // 1000
                    color = self.colors['success'] if gpu_temp < 60 else self.colors['warning'] if gpu_temp < 80 else self.colors['danger']
                    self.gpu_temp_var.set(f"{gpu_temp}C")
                    self.gpu_temp_label.configure(foreground=color)
            except:
                self.gpu_temp_var.set("--C")

            time.sleep(2)

    def update_cpu_slider(self, value):
        self.cpu_slider_label.config(text=f"{int(float(value))}%")
        if self.link_var.get():
            self.gpu_slider_value.set(int(float(value)))
            self.gpu_slider_label.config(text=f"{int(float(value))}%")

    def update_gpu_slider(self, value):
        self.gpu_slider_label.config(text=f"{int(float(value))}%")
        if self.link_var.get():
            self.cpu_slider_value.set(int(float(value)))
            self.cpu_slider_label.config(text=f"{int(float(value))}%")

    def toggle_link(self):
        if self.link_var.get():
            cpu_val = self.cpu_slider_value.get()
            self.gpu_slider_value.set(cpu_val)
            self.gpu_slider_label.config(text=f"{cpu_val}%")

    def apply_individual(self):
        self.cpu_fan_percent = self.cpu_slider_value.get()
        self.gpu_fan_percent = self.gpu_slider_value.get()
        self.start_manual_mode()
        if self.cpu_fan_percent == self.gpu_fan_percent:
            self.status_var.set(f"Mode: Manuel - {self.cpu_fan_percent}%")
        else:
            self.status_var.set(f"Manuel - CPU:{self.cpu_fan_percent}% GPU:{self.gpu_fan_percent}%")

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

    def set_fans(self, cpu_hex, gpu_hex):
        self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 0 {cpu_hex}' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd(f"echo '\\_SB.PCI0.SBRG.EC0.ST84 1 {gpu_hex}' | sudo tee /proc/acpi/call > /dev/null")

    def start_manual_mode(self):
        self.mode_var.set("manual")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110013 0' | sudo tee /proc/acpi/call > /dev/null")
        self.run_cmd("echo '\\_SB.ATKD.CWAP 0x00110014 0' | sudo tee /proc/acpi/call > /dev/null")
        time.sleep(0.5)

        cpu_hex = hex(int(self.cpu_fan_percent * 255 / 100))
        gpu_hex = hex(int(self.gpu_fan_percent * 255 / 100))
        self.enable_manual_mode()
        self.set_fans(cpu_hex, gpu_hex)

        if not self.manual_mode_active:
            self.manual_mode_active = True
            self.fan_maintain_thread = threading.Thread(target=self.maintain_fan_speed, daemon=True)
            self.fan_maintain_thread.start()

    def set_fans_percent(self, percent):
        self.cpu_fan_percent = percent
        self.gpu_fan_percent = percent
        self.cpu_slider_value.set(percent)
        self.gpu_slider_value.set(percent)
        self.cpu_slider_label.config(text=f"{percent}%")
        self.gpu_slider_label.config(text=f"{percent}%")
        self.start_manual_mode()
        self.status_var.set(f"Mode: Manuel - {percent}%")

    def set_auto_mode(self):
        self.manual_mode_active = False
        self.mode_var.set("auto")
        self.disable_manual_mode()
        self.run_cmd("echo 1 | sudo tee /sys/devices/platform/h5600_fan/thermal_policy > /dev/null 2>&1")
        self.status_var.set("Mode: Automatique")

    def set_manual_mode(self):
        self.apply_individual()

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
