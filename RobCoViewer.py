import os
import sys
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import subprocess

class RobCoViewer:
    def __init__(self, root):
        self.bg_color = "#0A0A0A"
        self.text_color = "#5AEB5A"
        self.root = root
        self.root.title("ROBCO TERMINAL")
        self.root.configure(bg=self.bg_color)
        self.root.geometry("1024x768")
        self.use_exe_icon()
        self.root.overrideredirect(True)
        self.is_fullscreen = True
        self.setup_taskbar_visibility()
        self.image_paths = []
        self.current_index = 0
        self.zoom_level = 1.0
        self.rotation = 0
        self.photo = None
        self.normal_geometry = "1024x768"
        self.setup_ui()
        self.bind_keys()
        self.root.after(100, self.toggle_fullscreen)
        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            self.open_file(sys.argv[1])
        else:
            self.status_label.config(text="NO IMAGE LOADED - PRESS ENTER TO BROWSE")
    
    def use_exe_icon(self):
        try:
            import win32gui
            import win32api
            import win32con
            executable = sys.executable
            if executable.lower().endswith('.exe'):
                large_icon = win32gui.ExtractIcon(0, executable, 0)
                if large_icon:
                    self.root.wm_iconbitmap(default=f"@{large_icon}")
                    win32gui.DestroyIcon(large_icon)
        except Exception:
            pass
    
    def setup_taskbar_visibility(self):
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RobCoViewer")
                self.root.after(200, self.show_in_taskbar)
            except Exception:
                pass
            try:
                self.root.wm_attributes("-alpha", 0.99)
                self.root.after(100, lambda: self.root.wm_attributes("-alpha", 1.0))
            except Exception:
                pass
        self.root.update_idletasks()
        
    def show_in_taskbar(self):
        try:
            import win32gui
            import win32con
            import win32api
            hwnd = win32gui.GetParent(self.root.winfo_id())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            style = style & ~win32con.WS_EX_TOOLWINDOW
            style = style | win32con.WS_EX_APPWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            executable = sys.executable
            if executable.lower().endswith('.exe'):
                hicon_sm = win32gui.ExtractIcon(0, executable, 0)
                hicon_lg = win32gui.ExtractIcon(0, executable, 0)
                if hicon_sm and hicon_lg:
                    win32api.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, hicon_sm)
                    win32api.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, hicon_lg)
        except Exception:
            pass
    
    def setup_ui(self):
        self.title_bar = tk.Frame(self.root, bg=self.bg_color, height=30)
        self.title_bar.pack(side=tk.TOP, fill=tk.X)
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<ButtonRelease-1>", self.stop_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        self.title_label = tk.Label(self.title_bar, text="■ ROBCO INDUSTRIES (TM) TERMINAL", font=("VT323", 14), fg=self.text_color, bg=self.bg_color, anchor=tk.W)
        self.title_label.pack(side=tk.LEFT, padx=5)
        self.close_btn = tk.Label(self.title_bar, text="×", font=("VT323", 14), fg=self.text_color, bg=self.bg_color)
        self.close_btn.pack(side=tk.RIGHT, padx=5)
        self.close_btn.bind("<Button-1>", lambda e: self.exit_app())
        self.minimize_btn = tk.Label(self.title_bar, text="+", font=("VT323", 14), fg=self.text_color, bg=self.bg_color)
        self.minimize_btn.pack(side=tk.RIGHT, padx=5)
        self.minimize_btn.bind("<Button-1>", lambda e: self.toggle_fullscreen())
        self.title_separator = tk.Frame(self.root, height=1, bg=self.text_color)
        self.title_separator.pack(side=tk.TOP, fill=tk.X)
        self.content_frame = tk.Frame(self.root, bg=self.bg_color)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.header_label = tk.Label(self.content_frame, text="ROBCO IMAGE VIEWER v2.0", font=("VT323", 16), fg=self.text_color, bg=self.bg_color)
        self.header_label.pack(side=tk.TOP, anchor=tk.W)
        self.canvas = tk.Canvas(self.content_frame, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=5)
        self.status_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        self.status_label = tk.Label(self.status_frame, text="", font=("VT323", 12), fg=self.text_color, bg=self.bg_color, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X)
        self.details_label = tk.Label(self.status_frame, text="", font=("VT323", 12), fg=self.text_color, bg=self.bg_color, justify=tk.RIGHT)
        self.details_label.pack(side=tk.RIGHT)
        self.help_label = tk.Label(self.content_frame, text="← →: Navigate | ENTER: Browse | R: Rotate | +/-: Zoom | L: Open Location | F: Fullscreen | ESC: Exit", font=("VT323", 12), fg=self.text_color, bg=self.bg_color)
        self.help_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        self.canvas.bind("<Configure>", lambda e: self.display_image())
    
    def start_move(self, event):
        self.x = event.x
        self.y = event.y
    
    def stop_move(self, event):
        self.x = None
        self.y = None
    
    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")
    
    def toggle_fullscreen(self):
        old_width = self.canvas.winfo_width()
        old_height = self.canvas.winfo_height()
        if self.is_fullscreen:
            self.root.geometry(self.normal_geometry)
            self.minimize_btn.config(text="+")
        else:
            self.normal_geometry = self.root.geometry()
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            self.root.geometry(f"{width}x{height}+0+0")
            self.minimize_btn.config(text="-")
        self.is_fullscreen = not self.is_fullscreen
        self.root.update_idletasks()
        new_width = self.canvas.winfo_width()
        new_height = self.canvas.winfo_height()
        if old_width != new_width or old_height != new_height:
            self.display_image()
    
    def bind_keys(self):
        self.root.bind("<Escape>", lambda e: self.exit_app())
        self.root.bind("<Left>", lambda e: self.prev_image())
        self.root.bind("<Right>", lambda e: self.next_image())
        self.root.bind("r", lambda e: self.rotate_image())
        self.root.bind("R", lambda e: self.rotate_image())
        self.root.bind("+", lambda e: self.zoom_in())
        self.root.bind("=", lambda e: self.zoom_in())
        self.root.bind("-", lambda e: self.zoom_out())
        self.root.bind("l", lambda e: self.open_image_location())
        self.root.bind("L", lambda e: self.open_image_location())
        self.root.bind("<Return>", lambda e: self.browse_images())
        self.root.bind("f", lambda e: self.toggle_fullscreen())
        self.root.bind("F", lambda e: self.toggle_fullscreen())
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
    
    def browse_images(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.tiff"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.open_file(file_path)
    
    def open_file(self, file_path):
        if not os.path.isfile(file_path):
            return
        directory = os.path.dirname(file_path)
        target_file = os.path.basename(file_path)
        self.image_paths = []
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
        for file in os.listdir(directory):
            full_path = os.path.join(directory, file)
            if os.path.isfile(full_path) and os.path.splitext(file)[1].lower() in valid_extensions:
                self.image_paths.append(full_path)
        self.image_paths.sort()
        selected_path = os.path.join(directory, target_file)
        if selected_path in self.image_paths:
            self.current_index = self.image_paths.index(selected_path)
        else:
            self.current_index = 0
        self.zoom_level = 1.0
        self.rotation = 0
        self.load_current_image()
    
    def load_current_image(self):
        if not self.image_paths:
            self.status_label.config(text="NO IMAGES FOUND")
            return
        try:
            if hasattr(self, 'photo'):
                del self.photo
            image_path = self.image_paths[self.current_index]
            self.original_image = Image.open(image_path)
            self.display_image()
            filename = os.path.basename(image_path)
            total = len(self.image_paths)
            current = self.current_index + 1
            self.status_label.config(text=f"FILE: {filename} [{current}/{total}]")
            self.update_image_details(image_path)
        except Exception as e:
            self.status_label.config(text=f"ERROR: {str(e)}")
    
    def update_image_details(self, image_path):
        width, height = self.original_image.size
        file_size = os.path.getsize(image_path) / 1024
        if file_size > 1024:
            size_str = f"{file_size/1024:.1f}MB"
        else:
            size_str = f"{file_size:.1f}KB"
        details = f"{width}x{height} | {size_str} | {self.original_image.format}"
        self.details_label.config(text=details)
    
    def display_image(self):
        if not hasattr(self, 'original_image'):
            return
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = self.root.winfo_width() - 20
            canvas_height = self.root.winfo_height() - 100
        img = self.original_image.copy()
        if self.rotation:
            img = img.rotate(self.rotation, expand=True)
        img_width, img_height = img.size
        width_ratio = canvas_width / img_width
        height_ratio = canvas_height / img_height
        scale = min(width_ratio, height_ratio) * self.zoom_level
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        if new_width > 0 and new_height > 0:
            img = img.resize((new_width, new_height), Image.LANCZOS)
            self.photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            self.canvas.create_image(x, y, anchor=tk.NW, image=self.photo)
    
    def next_image(self):
        if not self.image_paths:
            return
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        self.zoom_level = 1.0
        self.rotation = 0
        self.load_current_image()
    
    def prev_image(self):
        if not self.image_paths:
            return
        self.current_index = (self.current_index - 1) % len(self.image_paths)
        self.zoom_level = 1.0
        self.rotation = 0
        self.load_current_image()
    
    def rotate_image(self):
        if not hasattr(self, 'original_image'):
            return
        self.rotation = (self.rotation + 90) % 360
        self.display_image()
    
    def zoom_in(self):
        if not hasattr(self, 'original_image'):
            return
        self.zoom_level *= 1.2
        self.display_image()
    
    def zoom_out(self):
        if not hasattr(self, 'original_image'):
            return
        self.zoom_level /= 1.2
        if self.zoom_level < 0.1:
            self.zoom_level = 0.1
        self.display_image()
    
    def open_image_location(self):
        if not self.image_paths or self.current_index >= len(self.image_paths):
            return
        image_path = self.image_paths[self.current_index]
        try:
            if sys.platform == 'win32':
                    os.system(f'explorer /select,"{os.path.normpath(image_path)}"')
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', '-R', image_path])
            else:
                directory = os.path.dirname(image_path)
                subprocess.Popen(['xdg-open', directory])
            self.status_label.config(text=f"OPENED LOCATION: {os.path.dirname(image_path)}")
        except Exception as e:
            self.status_label.config(text=f"ERROR: Could not open location - {str(e)}")
    
    def exit_app(self):
        self.root.destroy()
        sys.exit()

def main():
    root = tk.Tk()
    app = RobCoViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()