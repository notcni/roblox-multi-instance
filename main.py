import base64
import codecs
import ctypes
import io
import json
import math
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import urllib.error
import urllib.request
import webbrowser

import customtkinter as ctk
import psutil
import win32api
import win32crypt
import win32event
import win32gui
import win32process
from PIL import Image, ImageDraw

ctk.set_appearance_mode("dark")

FA_VERSION = "6.5.1"
FA_CDN = f"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/{FA_VERSION}/webfonts"
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FA_FILES = ("fa-solid-900.ttf", "fa-brands-400.ttf")

FONT_SOLID = "Font Awesome 6 Free"
FONT_BRANDS = "Font Awesome 6 Brands"
FONT_UI = "Segoe UI Variable Display"
FONT_MONO = "Consolas"

ICON_LOGO = "\uf5fd"
ICON_GITHUB = "\uf09b"
ICON_DESKTOP = "\uf108"
ICON_MINIMIZE = "\uf068"
ICON_CLOSE = "\uf00d"
ICON_USER = "\uf007"
ICON_GAMEPAD = "\uf11b"
ICON_POWER = "\uf011"
ICON_KILL = "\uf057"
ICON_DOT = "\uf111"
ICON_USERS = "\uf0c0"
ICON_PLUS = "\uf067"
ICON_PLAY = "\uf04b"
ICON_TRASH = "\uf1f8"
ICON_GRID = "\uf009"
ICON_LIST = "\uf03a"
ICON_LOGS = "\uf15c"

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ACCS_DIR = os.path.join(DATA_DIR, "accs")
ACCS_FILE = os.path.join(ACCS_DIR, "accounts.json")
ICON_FILE = os.path.join(DATA_DIR, "app.ico")
NOTES_URL = "https://raw.githubusercontent.com/notcni/roblox-multi-instance/refs/heads/main/notes.txt"
GITHUB_URL = "https://github.com/notcni"

APP_NAME = "ROBLOX MULTI INSTANCE"

BG = "#060B26"
SIDEBAR_BG = "#0A1034"
CARD_BG = "#111B47"
CARD_BORDER = "#23337A"
CARD_BORDER_HOVER = "#4D6CD0"
ACCENT = "#4A74E8"
ACCENT_HOVER = "#6A8FF5"
ACCENT_SOFT = "#16246B"
ACCENT_LIGHT = "#A8BEFF"
AVATAR_BG = "#1A2A68"
HOVER_BG = "#16225A"

DANGER = "#F26B6B"
DANGER_SOFT = "#351A2B"
SUCCESS = "#3DDC97"
SUCCESS_DIM = "#1D6B4B"

TEXT = "#F4F6FF"
TEXT_SOFT = "#D5DCF5"
TEXT_MUTED = "#A4AED6"
TEXT_DIM = "#6F7AAA"

ROBLOX_PROCESS = "robloxplayerbeta.exe"
ROBLOX_LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Roblox", "logs")
SCAN_INTERVAL = 2.0
AVATAR_SIZE = 56
CARD_HEIGHT = 110
FRAME_MS = 16
GENERIC_TITLES = {"", "roblox", "roblox player", "roblox studio"}

RE_PLACE = re.compile(r"Joining game '[^']*' place (\d+)", re.IGNORECASE)
RE_USERID = re.compile(r"userid[:=\s]+(\d+)", re.IGNORECASE)

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
FR_PRIVATE = 0x10

GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
SW_MINIMIZE = 6

user32 = ctypes.windll.user32
user32.GetParent.argtypes = [ctypes.c_void_p]
user32.GetParent.restype = ctypes.c_void_p
user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.ShowWindow.restype = ctypes.c_bool


def _rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    return "#{:02X}{:02X}{:02X}".format(*(round(x + (y - x) * t) for x, y in zip(_rgb(a), _rgb(b))))


def _ease(t):
    return 1 - (1 - t) ** 3


def tween(widget, key, duration, step, done=None):
    pending = getattr(widget, key, None)
    if pending:
        try:
            widget.after_cancel(pending)
        except tk.TclError:
            pass
    frames = max(1, round(duration / FRAME_MS))

    def run(i):
        try:
            step(_ease(min(i / frames, 1.0)))
            if i < frames:
                setattr(widget, key, widget.after(FRAME_MS, run, i + 1))
                return
            setattr(widget, key, None)
        except tk.TclError:
            return
        if done:
            done()

    run(0)


def fade_color(widget, option, target, duration=160):
    try:
        current = widget.cget(option)
    except Exception:
        current = None
    if current == target:
        return
    begin = current if isinstance(current, str) and current.startswith("#") else target
    tween(widget, f"_fade_{option}", duration, lambda t: widget.configure(**{option: _mix(begin, target, t)}))


def reveal(widget, option, start, target, duration=260):
    widget.configure(**{option: start})
    fade_color(widget, option, target, duration)


def fade_window(window, duration=260, start=0.0, end=1.0):
    window.attributes("-alpha", start)
    tween(window, "_alpha", duration, lambda t: window.attributes("-alpha", start + (end - start) * t))


def _tint(widget, bg, fg, duration=140):
    fade_color(widget, "fg_color", bg, duration)
    fade_color(widget, "text_color", fg, duration)


def _pointer_inside(widget):
    try:
        x, y = widget.winfo_pointerxy()
        node = widget.winfo_containing(x, y)
    except (tk.TclError, KeyError):
        return False
    while node is not None:
        if node is widget:
            return True
        node = getattr(node, "master", None)
    return False


def _tree(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _tree(child)


def bind_hover(widget, enter, leave):
    def on_enter(_event):
        enter()

    def on_leave(_event):
        if not _pointer_inside(widget):
            leave()

    for w in _tree(widget):
        w.bind("<Enter>", on_enter, add="+")
        w.bind("<Leave>", on_leave, add="+")


def build_app_icon(path):
    os.makedirs(DATA_DIR, exist_ok=True)
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=60, fill=ACCENT)
    layers = ((64, "#8FAAF5"), (102, "#C4D4FF"), (140, "#FFFFFF"))
    for top, color in layers:
        draw.polygon([(128, top), (200, top + 36), (128, top + 72), (56, top + 36)], fill=color)
    img.save(path, format="ICO", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])


def encrypt_data(data):
    encrypted = win32crypt.CryptProtectData(data.encode("utf-8"), None, None, None, None, 0)
    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_data(b64_data):
    try:
        decrypted = win32crypt.CryptUnprotectData(base64.b64decode(b64_data), None, None, None, 0)[1]
        return decrypted.decode("utf-8")
    except Exception:
        return ""


def find_roblox_exe():
    paths_to_check = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Roblox", "Versions"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Roblox", "Versions"),
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Roblox", "Versions"),
    ]
    for base in paths_to_check:
        if not os.path.exists(base):
            continue
        for root, _, files in os.walk(base):
            if ROBLOX_PROCESS.lower() in (f.lower() for f in files):
                return os.path.join(root, "RobloxPlayerBeta.exe")
    return None


def fetch_auth_ticket(cookie):
    csrf = ""
    req_out = urllib.request.Request("https://auth.roblox.com/v2/logout", method="POST")
    req_out.add_header("Cookie", f".ROBLOSECURITY={cookie}")
    req_out.add_header("User-Agent", BROWSER_UA)
    try:
        urllib.request.urlopen(req_out)
    except urllib.error.HTTPError as e:
        csrf = e.headers.get("x-csrf-token", "")

    req_tick = urllib.request.Request("https://auth.roblox.com/v1/authentication-ticket", method="POST")
    req_tick.add_header("Cookie", f".ROBLOSECURITY={cookie}")
    req_tick.add_header("X-CSRF-TOKEN", csrf)
    req_tick.add_header("Referer", "https://www.roblox.com/")
    req_tick.add_header("Origin", "https://www.roblox.com")
    req_tick.add_header("Content-Type", "application/json")
    req_tick.add_header("User-Agent", BROWSER_UA)
    try:
        with urllib.request.urlopen(req_tick) as resp:
            return resp.headers.get("rbx-authentication-ticket")
    except Exception as e:
        print(f"[Auth] Error obteniendo ticket: {e}")
        return None


def get_auth_user(cookie):
    req = urllib.request.Request("https://users.roblox.com/v1/users/authenticated")
    req.add_header("Cookie", f".ROBLOSECURITY={cookie}")
    req.add_header("User-Agent", BROWSER_UA)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def download_font(filename):
    os.makedirs(FONT_DIR, exist_ok=True)
    path = os.path.join(FONT_DIR, filename)
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return path
    url = f"{FA_CDN}/{filename}"
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except Exception:
        return None
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    return path


def register_font(path):
    gdi32 = ctypes.WinDLL("gdi32")
    gdi32.AddFontResourceExW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
    gdi32.AddFontResourceExW.restype = ctypes.c_int
    return gdi32.AddFontResourceExW(path, FR_PRIVATE, None) > 0


def load_fonts():
    global FONT_SOLID, FONT_BRANDS, FONT_UI
    for filename in FA_FILES:
        path = download_font(filename)
        if path:
            register_font(path)

    root = tk.Tk()
    root.withdraw()
    families = list(tkfont.families(root))
    root.destroy()

    awesome = [f for f in families if "awesome" in f.lower()]
    brands = [f for f in awesome if "brand" in f.lower()]
    solid = [f for f in awesome if "brand" not in f.lower()]
    if brands:
        FONT_BRANDS = brands[0]
    if solid:
        FONT_SOLID = solid[0]
    if "Segoe UI Variable Display" not in families:
        FONT_UI = "Segoe UI"


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def http_json(url):
    return json.loads(http_get(url).decode("utf-8"))


def fetch_user(user_id):
    data = http_json(f"https://users.roblox.com/v1/users/{user_id}")
    return {"name": data.get("name", str(user_id)), "display": data.get("displayName", "")}


def fetch_avatar_url(user_id):
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false"
    items = http_json(url).get("data") or []
    if items and items[0].get("state") == "Completed":
        return items[0].get("imageUrl")
    return None


def fetch_game_name(place_id):
    uni = http_json(f"https://apis.roblox.com/universes/v1/places/{place_id}/universe")
    games = http_json(f"https://games.roblox.com/v1/games?universeIds={uni['universeId']}")
    items = games.get("data") or []
    return items[0]["name"] if items else None


def make_round_avatar(raw, size):
    img = Image.open(io.BytesIO(raw)).convert("RGBA").resize((size, size), Image.LANCZOS)
    scale = 4
    big = size * scale
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=big // 5, fill=255)
    img.putalpha(mask.resize((size, size), Image.LANCZOS))
    return img


def window_titles_by_pid():
    titles = {}

    def _cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                titles.setdefault(pid, title)
        return True

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        pass
    return titles


def find_log_for_process(proc):
    base = ROBLOX_LOG_DIR.lower()
    try:
        for f in proc.open_files():
            if f.path.lower().endswith(".log") and f.path.lower().startswith(base):
                return f.path
    except (psutil.Error, OSError):
        pass
    return None


class LogWatcher:
    def __init__(self, path):
        self.path = path
        self.offset = 0
        self.user_id = None
        self.place_id = None
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._buffer = ""

    def poll(self):
        try:
            with open(self.path, "rb") as f:
                f.seek(self.offset)
                data = f.read()
        except OSError:
            return
        self.offset += len(data)
        text = self._buffer + self._decoder.decode(data)
        lines = text.split("\n")
        self._buffer = lines.pop()
        for line in lines:
            if self.user_id is None:
                m = RE_USERID.search(line)
                if m:
                    self.user_id = int(m.group(1))
            m = RE_PLACE.search(line)
            if m:
                self.place_id = int(m.group(1))


class Monitor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.lock = threading.Lock()
        self.snapshot = {}
        self.running = True

    def run(self):
        watchers = {}
        while self.running:
            titles = window_titles_by_pid()
            snapshot = {}
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if (proc.info["name"] or "").lower() != ROBLOX_PROCESS:
                        continue
                    pid = proc.info["pid"]
                    if pid not in watchers:
                        log_path = find_log_for_process(proc)
                        if log_path:
                            watchers[pid] = LogWatcher(log_path)
                    watcher = watchers.get(pid)
                    if watcher:
                        watcher.poll()
                    snapshot[pid] = {
                        "title": titles.get(pid),
                        "user_id": watcher.user_id if watcher else None,
                        "place_id": watcher.place_id if watcher else None,
                    }
                except (psutil.Error, OSError):
                    pass
            for pid in list(watchers):
                if pid not in snapshot:
                    del watchers[pid]
            with self.lock:
                self.snapshot = snapshot
            time.sleep(SCAN_INTERVAL)


class Resolver(threading.Thread):
    RETRY_AFTER = 30

    def __init__(self):
        super().__init__(daemon=True)
        self._jobs = queue.Queue()
        self._lock = threading.Lock()
        self._cache = {}
        self._pending = set()
        self._failed = {}
        self.running = True

    def request(self, kind, key):
        job = (kind, key)
        with self._lock:
            if job in self._cache or job in self._pending:
                return
            if time.time() - self._failed.get(job, 0) < self.RETRY_AFTER:
                return
            self._pending.add(job)
        self._jobs.put(job)

    def state(self, kind, key):
        job = (kind, key)
        with self._lock:
            if job in self._cache:
                return "done"
            if job in self._pending:
                return "pending"
            return "failed"

    def value(self, kind, key):
        with self._lock:
            return self._cache.get((kind, key))

    def run(self):
        while self.running:
            job = self._jobs.get()
            try:
                result = self._resolve(job[0], job[1])
            except Exception:
                with self._lock:
                    self._pending.discard(job)
                    self._failed[job] = time.time()
                continue
            with self._lock:
                self._pending.discard(job)
                self._cache[job] = result

    @staticmethod
    def _resolve(kind, key):
        if kind == "user":
            return fetch_user(key)
        if kind == "avatar":
            url = fetch_avatar_url(key)
            return make_round_avatar(http_get(url), AVATAR_SIZE) if url else None
        if kind == "game":
            return fetch_game_name(key)
        return None


class NavButton(ctk.CTkFrame):
    BAR_HEIGHT = 0.5

    def __init__(self, master, icon, text, command, accent, text_color, hover, active=False):
        idle = ACCENT_SOFT if active else SIDEBAR_BG
        super().__init__(master, height=44, corner_radius=8, fg_color=idle, border_width=0)
        self.pack_propagate(False)
        self._command = command
        self._accent = accent
        self._hover = hover
        self._idle = idle
        self._active = active
        self._bar = self.BAR_HEIGHT if active else 0.0

        self.indicator = ctk.CTkFrame(self, width=3, corner_radius=2, fg_color=accent if active else idle)
        self.indicator.place(x=4, rely=0.5, anchor="w", relheight=self._bar)

        self._icon = ctk.CTkLabel(self, text=icon, font=(FONT_SOLID, 15), text_color=text_color, width=24)
        self._icon.pack(side="left", padx=(12, 8))
        self._text = ctk.CTkLabel(self, text=text, font=(FONT_UI, 14, "bold"), text_color=text_color, anchor="w")
        self._text.pack(side="left", fill="x", expand=True)

        bind_hover(self, self._enter, self._leave)
        for w in _tree(self):
            w.bind("<Button-1>", lambda _e: self._command(), add="+")

    def _enter(self):
        fade_color(self, "fg_color", self._hover, 140)

    def _leave(self):
        fade_color(self, "fg_color", self._idle, 180)

    def _grow_bar(self, target):
        start = self._bar

        def step(t):
            self._bar = start + (target - start) * t
            self.indicator.place_configure(relheight=self._bar)

        tween(self.indicator, "_grow", 240, step)

    def set_active(self, active):
        self._active = active
        self._idle = ACCENT_SOFT if active else SIDEBAR_BG
        fade_color(self, "fg_color", self._idle, 220)
        fade_color(self.indicator, "fg_color", self._accent if active else self._idle, 220)
        fade_color(self._text, "text_color", TEXT if active else TEXT_MUTED, 220)
        fade_color(self._icon, "text_color", ACCENT_LIGHT if active else TEXT_MUTED, 220)
        self._grow_bar(self.BAR_HEIGHT if active else 0.0)


def _outline(widget, active):
    fade_color(widget, "border_color", CARD_BORDER_HOVER if active else CARD_BORDER, 200)


class InstanceCard(ctk.CTkFrame):
    def __init__(self, master, pid, on_kill):
        super().__init__(master, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER, corner_radius=12, height=CARD_HEIGHT)
        self.pack_propagate(False)
        self.pid = pid
        self._avatar_user = None
        self._photo = None

        self.avatar = ctk.CTkLabel(self, text=ICON_USER, width=AVATAR_SIZE, height=AVATAR_SIZE, fg_color=AVATAR_BG, corner_radius=10, font=(FONT_SOLID, 24), text_color=TEXT_DIM)
        self.avatar.pack(side="left", padx=(16, 14), pady=22)

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=16)

        name_row = ctk.CTkFrame(info, fg_color="transparent")
        name_row.pack(anchor="w")
        self.username = ctk.CTkLabel(name_row, text="Detecting user…", font=(FONT_MONO, 15, "bold"), text_color=TEXT)
        self.username.pack(side="left")
        self.displayname = ctk.CTkLabel(name_row, text="", font=(FONT_UI, 12), text_color=TEXT_MUTED)
        self.displayname.pack(side="left", padx=(8, 0))

        game_row = ctk.CTkFrame(info, fg_color="transparent")
        game_row.pack(anchor="w", pady=(6, 0))
        ctk.CTkLabel(game_row, text=ICON_GAMEPAD, font=(FONT_SOLID, 11), text_color=ACCENT_LIGHT).pack(side="left")
        self.game = ctk.CTkLabel(game_row, text="Waiting in menu", font=(FONT_UI, 13), text_color=TEXT_MUTED)
        self.game.pack(side="left", padx=(6, 0))

        status_row = ctk.CTkFrame(info, fg_color="transparent")
        status_row.pack(anchor="w", pady=(4, 0))
        self.dot = ctk.CTkLabel(status_row, text=ICON_DOT, font=(FONT_SOLID, 7), text_color=SUCCESS)
        self.dot.pack(side="left", pady=(1, 0))
        ctk.CTkLabel(status_row, text=f"Client Active  ·  PID {pid}", font=(FONT_UI, 11), text_color=TEXT_DIM).pack(side="left", padx=(6, 0))

        self.btn_kill = ctk.CTkButton(self, text=ICON_KILL, width=40, height=40, corner_radius=8, fg_color=CARD_BG, hover=False, text_color=DANGER, font=(FONT_SOLID, 16), command=lambda: on_kill(pid))
        self.btn_kill.pack(side="right", padx=16)
        bind_hover(self.btn_kill, lambda: _tint(self.btn_kill, DANGER_SOFT, DANGER), lambda: _tint(self.btn_kill, CARD_BG, DANGER))
        bind_hover(self, lambda: _outline(self, True), lambda: _outline(self, False))

        reveal(self, "fg_color", BG, CARD_BG)
        self._pulse()

    def _pulse(self):
        try:
            wave = (math.sin(time.time() * 3.2) + 1) / 2
            self.dot.configure(text_color=_mix(SUCCESS_DIM, SUCCESS, wave))
            self.after(60, self._pulse)
        except tk.TclError:
            pass

    def set_user(self, user_id, user, avatar, loading):
        if user:
            self.username.configure(text=f"@{user['name']}")
            display = user.get("display") or ""
            self.displayname.configure(text=display if display != user["name"] else "")
        elif user_id:
            self.username.configure(text="Loading…" if loading else f"User {user_id}")
            self.displayname.configure(text="")
        else:
            self.username.configure(text="Detecting user…")
            self.displayname.configure(text="")

        if avatar is not None and self._avatar_user != user_id:
            photo = ctk.CTkImage(light_image=avatar, dark_image=avatar, size=(AVATAR_SIZE, AVATAR_SIZE))
            self.avatar.configure(image=photo, text="")
            self._photo = photo
            self._avatar_user = user_id

    def set_game(self, text, known):
        if self.game.cget("text") != text:
            self.game.configure(text=text)
        fade_color(self.game, "text_color", TEXT_SOFT if known else TEXT_MUTED, 220)


class AccountCard(ctk.CTkFrame):
    def __init__(self, master, acc_id, acc_data, on_launch, on_delete, resolver):
        super().__init__(master, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER, corner_radius=12, height=84)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self.acc_id = acc_id
        self.resolver = resolver
        self.acc_data = acc_data
        self.user_id = acc_data.get("user_id")
        self._photo = None

        self.avatar_label = ctk.CTkLabel(self, text=ICON_USER, width=AVATAR_SIZE, height=AVATAR_SIZE, fg_color=AVATAR_BG, corner_radius=10, font=(FONT_SOLID, 24), text_color=TEXT_DIM)
        self.avatar_label.pack(side="left", padx=(16, 14), pady=14)

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)

        self.name_label = ctk.CTkLabel(info, text=f"@{acc_data.get('name', 'Unknown')}", font=(FONT_MONO, 15, "bold"), text_color=TEXT)
        self.name_label.pack(anchor="w", expand=True)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="right", padx=16)

        self.btn_delete = ctk.CTkButton(btn_frame, text=ICON_TRASH, width=38, height=38, corner_radius=8, fg_color=CARD_BG, hover=False, text_color=DANGER, font=(FONT_SOLID, 14), command=lambda: on_delete(acc_id))
        self.btn_delete.pack(side="left", padx=(0, 8))
        self.btn_launch = ctk.CTkButton(btn_frame, text=ICON_PLAY, width=38, height=38, corner_radius=8, fg_color=ACCENT_SOFT, hover=False, text_color=ACCENT_LIGHT, font=(FONT_SOLID, 14), command=lambda: on_launch(acc_id))
        self.btn_launch.pack(side="left")

        bind_hover(self.btn_delete, lambda: _tint(self.btn_delete, DANGER_SOFT, DANGER), lambda: _tint(self.btn_delete, CARD_BG, DANGER))
        bind_hover(self.btn_launch, lambda: _tint(self.btn_launch, ACCENT, TEXT), lambda: _tint(self.btn_launch, ACCENT_SOFT, ACCENT_LIGHT))
        bind_hover(self, lambda: _outline(self, True), lambda: _outline(self, False))

        reveal(self, "fg_color", BG, CARD_BG)

        if self.user_id:
            self.after(100, self._load_avatar)

    def _load_avatar(self):
        state = self.resolver.state("avatar", self.user_id)
        if state == "done":
            avatar = self.resolver.value("avatar", self.user_id)
            if avatar:
                photo = ctk.CTkImage(light_image=avatar, dark_image=avatar, size=(AVATAR_SIZE, AVATAR_SIZE))
                self.avatar_label.configure(image=photo, text="")
                self._photo = photo
        elif state == "pending":
            self.after(500, self._load_avatar)
        elif state is None:
            self.resolver.request("avatar", self.user_id)
            self.after(500, self._load_avatar)

    def set_status(self, text, color):
        self.name_label.configure(text=text)
        fade_color(self.name_label, "text_color", color, 200)

    def reset_status(self):
        self.name_label.configure(text=f"@{self.acc_data.get('name', 'Unknown')}")
        fade_color(self.name_label, "text_color", TEXT, 200)


class AddAccountDialog(ctk.CTkToplevel):
    def __init__(self, master, on_save):
        super().__init__(master)
        self.title("Add Account")
        self.overrideredirect(True)
        self.configure(fg_color=BG)
        self.transient(master)
        self.attributes("-alpha", 0.0)

        width, height = 460, 350
        x = master.winfo_x() + (master.winfo_width() // 2) - (width // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.on_save = on_save
        self._drag_offset = (0, 0)
        self._shaking = False
        self._anchor = (x, y)

        titlebar = ctk.CTkFrame(self, height=44, fg_color=CARD_BG, corner_radius=0)
        titlebar.pack(fill="x", side="top")
        ctk.CTkLabel(titlebar, text="Add New Account", font=(FONT_UI, 14, "bold"), text_color=TEXT).pack(side="left", padx=20)
        self.btn_close = ctk.CTkButton(titlebar, text=ICON_CLOSE, font=(FONT_SOLID, 14), width=30, height=30, corner_radius=6, fg_color=CARD_BG, hover=False, text_color=TEXT_MUTED, command=self.destroy)
        self.btn_close.pack(side="right", padx=10)
        bind_hover(self.btn_close, lambda: _tint(self.btn_close, DANGER_SOFT, DANGER), lambda: _tint(self.btn_close, CARD_BG, TEXT_MUTED))

        titlebar.bind("<Button-1>", self._start_drag)
        titlebar.bind("<B1-Motion>", self._drag)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=16)

        ctk.CTkLabel(content, text="Paste .ROBLOSECURITY Cookie:", font=(FONT_UI, 13, "bold"), text_color=TEXT_SOFT).pack(anchor="w", pady=(10, 5))
        self.cookie_entry = self._entry(content, "_|WARNING:-DO-NOT-SHARE...")
        self.cookie_entry.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(content, text="Account Name (Auto-fetched if valid):", font=(FONT_UI, 13, "bold"), text_color=TEXT_SOFT).pack(anchor="w", pady=(0, 5))
        self.name_entry = self._entry(content, "Optional manual name...")
        self.name_entry.pack(fill="x", pady=(0, 5))

        self.status_label = ctk.CTkLabel(content, text="", text_color=DANGER, font=(FONT_UI, 12))
        self.status_label.pack(pady=(0, 10))

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", pady=(10, 5))

        self.btn_cancel = ctk.CTkButton(btn_frame, text="Cancel", height=38, fg_color=BG, hover=False, border_width=1, border_color=CARD_BORDER, text_color=TEXT_SOFT, command=self.destroy)
        self.btn_cancel.pack(side="left", expand=True, fill="x", padx=(0, 5))
        bind_hover(self.btn_cancel, lambda: _tint(self.btn_cancel, CARD_BG, TEXT), lambda: _tint(self.btn_cancel, BG, TEXT_SOFT))

        self.btn_save = ctk.CTkButton(btn_frame, text="Verify & Save", height=38, fg_color=ACCENT, hover=False, text_color=TEXT, font=(FONT_UI, 13, "bold"), command=self.verify_and_save)
        self.btn_save.pack(side="left", expand=True, fill="x", padx=(5, 0))
        bind_hover(self.btn_save, lambda: _tint(self.btn_save, ACCENT_HOVER, TEXT), lambda: _tint(self.btn_save, ACCENT, TEXT))

        fade_window(self, 200)
        self.grab_set()

    def _entry(self, parent, placeholder):
        entry = ctk.CTkEntry(parent, height=38, placeholder_text=placeholder, fg_color=CARD_BG, border_color=CARD_BORDER, text_color=TEXT)
        entry.bind("<FocusIn>", lambda _e: fade_color(entry, "border_color", ACCENT, 180), add="+")
        entry.bind("<FocusOut>", lambda _e: fade_color(entry, "border_color", CARD_BORDER, 180), add="+")
        return entry

    def _start_drag(self, event):
        self._drag_offset = (event.x, event.y)

    def _drag(self, event):
        self.geometry(f"+{event.x_root - self._drag_offset[0]}+{event.y_root - self._drag_offset[1]}")

    def _error(self, text):
        self.status_label.configure(text=text, text_color=DANGER)
        self._shake()

    def _shake(self, step=0):
        if step == 0:
            if self._shaking:
                return
            self._shaking = True
            self._anchor = (self.winfo_x(), self.winfo_y())
        offsets = (12, -12, 8, -8, 4, -4, 0)
        if step >= len(offsets):
            self._shaking = False
            return
        x, y = self._anchor
        self.geometry(f"+{x + offsets[step]}+{y}")
        self.after(30, self._shake, step + 1)

    def verify_and_save(self):
        cookie = self.cookie_entry.get().strip()
        if not cookie:
            self._error("Cookie cannot be empty.")
            return

        self.status_label.configure(text="Verifying cookie...", text_color=ACCENT_LIGHT)
        self.update()

        user_info = get_auth_user(cookie)
        user_id = None
        if user_info and "name" in user_info:
            name = user_info["name"]
            user_id = user_info.get("id")
        else:
            name = self.name_entry.get().strip()
            if not name:
                self._error("Invalid Cookie. Enter a manual name to force save.")
                return

        self.on_save(name, user_id, encrypt_data(cookie))
        self.destroy()


class AppGUI(ctk.CTk):
    WIDTH, HEIGHT = 920, 600
    UI_REFRESH_MS = 1000

    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.configure(fg_color=BG)
        self.attributes("-alpha", 0.0)
        self.overrideredirect(True)

        self.mutex_handle = None
        self.setup_mutex()

        self.cards = {}
        self.accs_data = {}
        self.accounts_view_mode = "list"
        self._drag_offset = (0, 0)
        self.nav_buttons = {}
        self.views = {}
        self.current_view = None
        self.logs_loaded = False
        self._ui_queue = queue.Queue()

        self.monitor = Monitor()
        self.resolver = Resolver()

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.load_accounts()

        self._build_titlebar()
        self._build_sidebar()
        self._build_content()
        self._build_instances_view()
        self._build_accounts_view()
        self._build_logs_view()

        self.views = {
            "instances": self.instances_frame,
            "accounts": self.accounts_frame,
            "logs": self.logs_frame,
        }
        self.show_view("instances", animate=False)

        self.monitor.start()
        self.resolver.start()
        self.after(self.UI_REFRESH_MS, self._sync_ui)
        self.after(20, self._pump)
        self.after(30, self._apply_taskbar_style)
        self.after(60, lambda: fade_window(self, 320))

    def setup_mutex(self):
        try:
            self.mutex_handle = win32event.CreateMutex(None, True, "ROBLOX_singletonMutex")
        except Exception:
            pass

    def _apply_taskbar_style(self):
        self.update_idletasks()
        hwnd = user32.GetParent(self.winfo_id())
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW)
        try:
            build_app_icon(ICON_FILE)
            self.iconbitmap(ICON_FILE)
        except Exception:
            pass
        self.withdraw()
        self.after(10, self.deiconify)

    def minimize(self):
        user32.ShowWindow(user32.GetParent(self.winfo_id()), SW_MINIMIZE)

    def _post(self, fn, *args):
        self._ui_queue.put((fn, args))

    def _pump(self):
        while True:
            try:
                fn, args = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args)
            except tk.TclError:
                pass
        self.after(20, self._pump)

    def _build_titlebar(self):
        self.title_bar = ctk.CTkFrame(self, height=44, fg_color=BG, corner_radius=0)
        self.title_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.title_bar.grid_columnconfigure(1, weight=1)

        self.logo_label = ctk.CTkLabel(self.title_bar, text=f"{ICON_LOGO} {APP_NAME}", text_color=ACCENT_LIGHT, font=(FONT_SOLID, 15, "bold"))
        self.logo_label.grid(row=0, column=0, padx=22, pady=10, sticky="w")

        for widget in (self.title_bar, self.logo_label):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)

        controls = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        controls.grid(row=0, column=2, padx=10, sticky="e")

        self._icon_btn(controls, ICON_GITHUB, lambda: webbrowser.open(GITHUB_URL), family=FONT_BRANDS, size=16, text_color=TEXT_MUTED).pack(side="left", padx=2)
        self._icon_btn(controls, ICON_MINIMIZE, self.minimize, size=12, text_color=TEXT_MUTED).pack(side="left", padx=2)
        self._icon_btn(controls, ICON_CLOSE, self.close_app, size=14, text_color=TEXT_MUTED, hover=DANGER_SOFT, hover_text=DANGER).pack(side="left", padx=2)

    def _icon_btn(self, parent, icon, command, family=None, size=14, hover=HOVER_BG, text_color=TEXT, hover_text=TEXT):
        btn = ctk.CTkButton(parent, text=icon, command=command, width=32, height=32, corner_radius=8, fg_color=BG, hover=False, text_color=text_color, font=(family or FONT_SOLID, size))
        bind_hover(btn, lambda: _tint(btn, hover, hover_text), lambda: _tint(btn, BG, text_color))
        return btn

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=230, fg_color=SIDEBAR_BG, corner_radius=0)
        self.sidebar.grid(row=1, column=0, sticky="nsew")
        self.sidebar.pack_propagate(False)

        self.nav_buttons["instances"] = NavButton(self.sidebar, ICON_DESKTOP, "Instances", lambda: self.show_view("instances"), accent=ACCENT, text_color=TEXT_MUTED, hover=HOVER_BG)
        self.nav_buttons["instances"].pack(pady=(25, 4), padx=12, fill="x")

        self.nav_buttons["accounts"] = NavButton(self.sidebar, ICON_USERS, "Accounts", lambda: self.show_view("accounts"), accent=ACCENT, text_color=TEXT_MUTED, hover=HOVER_BG)
        self.nav_buttons["accounts"].pack(pady=4, padx=12, fill="x")

        self.nav_buttons["logs"] = NavButton(self.sidebar, ICON_LOGS, "Logs", lambda: self.show_view("logs"), accent=ACCENT, text_color=TEXT_MUTED, hover=HOVER_BG)
        self.nav_buttons["logs"].pack(pady=4, padx=12, fill="x")

        self.btn_close_all = NavButton(self.sidebar, ICON_POWER, "Close all", command=self.kill_all, accent=DANGER, text_color=DANGER, hover=DANGER_SOFT)
        self.btn_close_all.pack(side="bottom", pady=(6, 25), padx=12, fill="x")

        ctk.CTkFrame(self, width=1, fg_color=CARD_BORDER, corner_radius=0).grid(row=1, column=0, sticky="nse")

    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.grid(row=1, column=1, sticky="nsew")

    def _build_instances_view(self):
        self.instances_frame = ctk.CTkFrame(self.content, fg_color=BG, corner_radius=0)
        self.instances_frame.grid_columnconfigure(0, weight=1)
        self.instances_frame.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self.instances_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 4))
        ctk.CTkLabel(header, text="Active Instances", font=(FONT_UI, 26, "bold"), text_color=TEXT).pack(side="left")

        self.clients_count_label = ctk.CTkLabel(self.instances_frame, text="0 clients detected", font=(FONT_UI, 14), text_color=TEXT_MUTED)
        self.clients_count_label.grid(row=1, column=0, sticky="w", padx=32, pady=(0, 24))

        self.scroll_inst = ctk.CTkScrollableFrame(self.instances_frame, fg_color="transparent")
        self.scroll_inst.grid(row=2, column=0, sticky="nsew", padx=20)
        self.scroll_inst.grid_columnconfigure(0, weight=1)

        self.empty_inst = ctk.CTkFrame(self.scroll_inst, fg_color="transparent")
        ctk.CTkLabel(self.empty_inst, text=ICON_GAMEPAD, font=(FONT_SOLID, 48), text_color=TEXT_DIM).pack()
        ctk.CTkLabel(self.empty_inst, text="No active clients", font=(FONT_UI, 18, "bold"), text_color=TEXT_MUTED).pack(pady=(12, 4))
        ctk.CTkLabel(self.empty_inst, text="Launch Roblox and instances will appear here", font=(FONT_UI, 13), text_color=TEXT_DIM).pack()

    def _build_accounts_view(self):
        self.accounts_frame = ctk.CTkFrame(self.content, fg_color=BG, corner_radius=0)
        self.accounts_frame.grid_columnconfigure(0, weight=1)
        self.accounts_frame.grid_rowconfigure(1, weight=1)

        header_acc = ctk.CTkFrame(self.accounts_frame, fg_color="transparent")
        header_acc.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 24))

        title_box = ctk.CTkFrame(header_acc, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="Saved Accounts", font=(FONT_UI, 26, "bold"), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Launch directly from encrypted cookies", font=(FONT_UI, 14), text_color=TEXT_MUTED).pack(anchor="w", pady=(2, 0))

        controls_box = ctk.CTkFrame(header_acc, fg_color="transparent")
        controls_box.pack(side="right")

        self.btn_toggle_view = ctk.CTkButton(controls_box, text=ICON_GRID if self.accounts_view_mode == "list" else ICON_LIST, font=(FONT_SOLID, 16), width=40, height=40, corner_radius=8, fg_color=CARD_BG, hover=False, text_color=TEXT_MUTED, command=self.toggle_view_mode)
        self.btn_toggle_view.pack(side="left", padx=(0, 12))
        bind_hover(self.btn_toggle_view, lambda: _tint(self.btn_toggle_view, HOVER_BG, TEXT), lambda: _tint(self.btn_toggle_view, CARD_BG, TEXT_MUTED))

        self.btn_add = ctk.CTkButton(controls_box, text=f"  {ICON_PLUS} Add Account", font=(FONT_SOLID, 13, "bold"), height=40, corner_radius=8, fg_color=ACCENT, hover=False, text_color=TEXT, command=self.open_add_account)
        self.btn_add.pack(side="left")
        bind_hover(self.btn_add, lambda: _tint(self.btn_add, ACCENT_HOVER, TEXT), lambda: _tint(self.btn_add, ACCENT, TEXT))

        self.scroll_accs = ctk.CTkScrollableFrame(self.accounts_frame, fg_color="transparent")
        self.scroll_accs.grid(row=1, column=0, sticky="nsew", padx=15)

    def _build_logs_view(self):
        self.logs_frame = ctk.CTkFrame(self.content, fg_color=BG, corner_radius=0)
        self.logs_frame.grid_columnconfigure(0, weight=1)
        self.logs_frame.grid_rowconfigure(1, weight=1)

        header_logs = ctk.CTkFrame(self.logs_frame, fg_color="transparent")
        header_logs.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 14))
        ctk.CTkLabel(header_logs, text="Changelog & Updates", font=(FONT_UI, 26, "bold"), text_color=TEXT).pack(side="left")

        self.logs_textbox = ctk.CTkTextbox(self.logs_frame, fg_color=CARD_BG, text_color=TEXT, font=(FONT_MONO, 13), border_width=1, border_color=CARD_BORDER, corner_radius=12)
        self.logs_textbox.grid(row=1, column=0, sticky="nsew", padx=32, pady=(0, 32))
        self.logs_textbox.insert("0.0", "Loading logs from GitHub...")
        self.logs_textbox.configure(state="disabled")

    def show_view(self, name, animate=True):
        if name == self.current_view:
            return
        previous = self.views.get(self.current_view)
        if previous is not None:
            previous.place_forget()

        frame = self.views[name]
        self.current_view = name
        offset = 0.06 if animate else 0.0
        frame.place(relx=offset, rely=0, relwidth=1, relheight=1)
        frame.lift()
        if animate:
            tween(frame, "_slide", 300, lambda t: frame.place_configure(relx=offset * (1 - t)))

        for key, btn in self.nav_buttons.items():
            btn.set_active(key == name)

        if name == "accounts":
            self.refresh_accounts_ui()
        elif name == "logs" and not self.logs_loaded:
            self._fetch_logs()

    def _fetch_logs(self):
        self.logs_loaded = True

        def task():
            try:
                req = urllib.request.Request(NOTES_URL, headers={"User-Agent": BROWSER_UA})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    text = resp.read().decode("utf-8")
            except Exception as e:
                text = f"Error loading notes:\n{e}"
            self._post(self._set_logs_text, text)

        threading.Thread(target=task, daemon=True).start()

    def _set_logs_text(self, text):
        self.logs_textbox.configure(state="normal")
        self.logs_textbox.delete("0.0", "end")
        self.logs_textbox.insert("0.0", text)
        self.logs_textbox.configure(state="disabled")

    def _sync_ui(self):
        with self.monitor.lock:
            snapshot = dict(self.monitor.snapshot)

        for pid in set(self.cards) - set(snapshot):
            card = self.cards.pop(pid, None)
            if card:
                card.destroy()

        for pid in sorted(set(snapshot) - set(self.cards)):
            card = InstanceCard(self.scroll_inst, pid, on_kill=self.kill_process)
            card.pack(fill="x", pady=(0, 10), padx=12)
            self.cards[pid] = card

        for pid, info in snapshot.items():
            card = self.cards[pid]
            uid = info["user_id"]
            user = avatar = None
            loading = False
            if uid:
                self.resolver.request("user", uid)
                self.resolver.request("avatar", uid)
                user = self.resolver.value("user", uid)
                avatar = self.resolver.value("avatar", uid)
                loading = self.resolver.state("user", uid) == "pending"
            card.set_user(uid, user, avatar, loading)
            name, known = self._game_text(info)
            card.set_game(name, known)

        count = len(self.cards)
        self.clients_count_label.configure(text=f"{count} client{'s' if count != 1 else ''} running")

        if count == 0 and not self.empty_inst.winfo_manager():
            self.empty_inst.pack(expand=True, pady=60)
        elif count > 0 and self.empty_inst.winfo_manager():
            self.empty_inst.pack_forget()

        if self.monitor.running:
            self.after(self.UI_REFRESH_MS, self._sync_ui)

    def _game_text(self, info):
        pid = info["place_id"]
        if pid:
            self.resolver.request("game", pid)
            name = self.resolver.value("game", pid)
            if name:
                return name, True
            if self.resolver.state("game", pid) == "pending":
                return "Loading game info…", False
        title = (info["title"] or "").strip()
        if title and title.lower() not in GENERIC_TITLES:
            return title, True
        if pid:
            return f"Place {pid}", False
        return "Waiting in menu", False

    def kill_process(self, pid):
        try:
            psutil.Process(pid).terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def kill_all(self):
        for pid in list(self.cards):
            self.kill_process(pid)

    def load_accounts(self):
        os.makedirs(ACCS_DIR, exist_ok=True)
        if os.path.exists(ACCS_FILE):
            try:
                with open(ACCS_FILE, "r") as f:
                    self.accs_data = json.load(f)
            except Exception:
                self.accs_data = {}

    def save_accounts_file(self):
        with open(ACCS_FILE, "w") as f:
            json.dump(self.accs_data, f)

    def open_add_account(self):
        AddAccountDialog(self, on_save=self.add_account_entry)

    def add_account_entry(self, name, user_id, encrypted_cookie):
        acc_id = str(time.time_ns())
        self.accs_data[acc_id] = {"name": name, "user_id": user_id, "cookie": encrypted_cookie}
        self.save_accounts_file()
        self.refresh_accounts_ui()

    def delete_account(self, acc_id):
        if acc_id in self.accs_data:
            del self.accs_data[acc_id]
            self.save_accounts_file()
            self.refresh_accounts_ui()

    def toggle_view_mode(self):
        if self.accounts_view_mode == "list":
            self.accounts_view_mode = "grid"
            self.btn_toggle_view.configure(text=ICON_LIST)
        else:
            self.accounts_view_mode = "list"
            self.btn_toggle_view.configure(text=ICON_GRID)
        self.refresh_accounts_ui()

    def _account_card(self, acc_id):
        return next(
            (w for w in self.scroll_accs.winfo_children() if isinstance(w, AccountCard) and w.acc_id == acc_id),
            None,
        )

    def _set_status(self, card, text, color, reset_after=None):
        if card is None:
            return
        card.set_status(text, color)
        if reset_after:
            self.after(reset_after, lambda: self._restore_status(card))

    def _restore_status(self, card):
        try:
            card.reset_status()
        except tk.TclError:
            pass

    def launch_account(self, acc_id):
        if acc_id not in self.accs_data:
            return
        cookie = decrypt_data(self.accs_data[acc_id]["cookie"])
        card = self._account_card(acc_id)

        if not cookie:
            self._set_status(card, "Decryption Failed", DANGER, 3000)
            return

        self._set_status(card, "Authenticating...", ACCENT_LIGHT)

        def worker():
            ticket = fetch_auth_ticket(cookie)
            if not ticket:
                self._post(self._set_status, card, "Auth Failed", DANGER, 3000)
                return

            exe_path = find_roblox_exe()
            if not exe_path:
                self._post(self._set_status, card, "Roblox not found", DANGER, 3000)
                return

            try:
                self._post(self._set_status, card, "Launching...", ACCENT_LIGHT)
                subprocess.Popen([exe_path, "--app", "-t", ticket])
                self._post(self._set_status, card, "Launched Successfully!", SUCCESS, 3000)
            except Exception:
                self._post(self._set_status, card, "Launch Error", DANGER, 3000)

        threading.Thread(target=worker, daemon=True).start()

    def refresh_accounts_ui(self):
        for widget in self.scroll_accs.winfo_children():
            widget.destroy()

        if not self.accs_data:
            self.scroll_accs.grid_columnconfigure(0, weight=1)
            self.scroll_accs.grid_columnconfigure(1, weight=0)
            empty = ctk.CTkFrame(self.scroll_accs, fg_color="transparent")
            ctk.CTkLabel(empty, text=ICON_USERS, font=(FONT_SOLID, 48), text_color=TEXT_DIM).pack()
            ctk.CTkLabel(empty, text="No accounts saved", font=(FONT_UI, 18, "bold"), text_color=TEXT_MUTED).pack(pady=(12, 4))
            empty.grid(row=0, column=0, pady=60)
            return

        if self.accounts_view_mode == "list":
            self.scroll_accs.grid_columnconfigure(0, weight=1)
            self.scroll_accs.grid_columnconfigure(1, weight=0)
            for row, (acc_id, data) in enumerate(self.accs_data.items()):
                card = AccountCard(self.scroll_accs, acc_id, data, on_launch=self.launch_account, on_delete=self.delete_account, resolver=self.resolver)
                card.grid(row=row, column=0, sticky="ew", pady=(0, 10), padx=10)
        else:
            self.scroll_accs.grid_columnconfigure(0, weight=1)
            self.scroll_accs.grid_columnconfigure(1, weight=1)
            for index, (acc_id, data) in enumerate(self.accs_data.items()):
                card = AccountCard(self.scroll_accs, acc_id, data, on_launch=self.launch_account, on_delete=self.delete_account, resolver=self.resolver)
                card.grid(row=index // 2, column=index % 2, sticky="ew", pady=(0, 10), padx=8)

    def close_app(self):
        self.monitor.running = False
        self.resolver.running = False
        if self.mutex_handle:
            win32event.ReleaseMutex(self.mutex_handle)
            win32api.CloseHandle(self.mutex_handle)
        self.destroy()
        sys.exit(0)

    def _start_drag(self, event):
        self._drag_offset = (event.x, event.y)

    def _drag(self, event):
        self.geometry(f"+{event.x_root - self._drag_offset[0]}+{event.y_root - self._drag_offset[1]}")


if __name__ == "__main__":
    load_fonts()
    app = AppGUI()
    app.mainloop()