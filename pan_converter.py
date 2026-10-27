# -*- coding: utf-8 -*-

import ctypes
import ctypes.wintypes as wintypes
import html
import re
import threading
import time
import tkinter as tk
from tkinter import ttk
from urllib.parse import unquote


# ============================================================
# 配置
# ============================================================

APP_NAME = "网盘链接自动转换器"

UNZIP_PWD = "laoquzhang.com"

CHECK_INTERVAL = 0.35

AUTO_COPY_RESULT = True

IGNORE_SECONDS = 5

# 是否在转换结果末尾追加 |jy=xxx 后缀（默认开启）
APPEND_SUFFIX = True


# ============================================================
# Windows API
# ============================================================

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

CF_UNICODETEXT = 13

WM_CLOSE = 0x0010
WM_USER = 0x0400

WM_TRAY = WM_USER + 1
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205

NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002

NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

IDI_APPLICATION = 32512

# Python 3.14 兼容：
# Windows:
#   LPARAM  = LONG_PTR
#   WPARAM  = UINT_PTR
#   LRESULT = LONG_PTR
LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t


# ============================================================
# 基本 API 类型
# ============================================================

user32.OpenClipboard.argtypes = [
    wintypes.HWND
]
user32.OpenClipboard.restype = wintypes.BOOL

user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL

user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL

user32.GetClipboardData.argtypes = [
    wintypes.UINT
]
user32.GetClipboardData.restype = wintypes.HANDLE

user32.RegisterClipboardFormatW.argtypes = [
    wintypes.LPCWSTR
]
user32.RegisterClipboardFormatW.restype = wintypes.UINT

user32.SetClipboardData.argtypes = [
    wintypes.UINT,
    wintypes.HANDLE
]
user32.SetClipboardData.restype = wintypes.HANDLE

kernel32.GlobalLock.argtypes = [
    wintypes.HGLOBAL
]
kernel32.GlobalLock.restype = wintypes.LPVOID

kernel32.GlobalUnlock.argtypes = [
    wintypes.HGLOBAL
]
kernel32.GlobalUnlock.restype = wintypes.BOOL

kernel32.GlobalAlloc.argtypes = [
    wintypes.UINT,
    ctypes.c_size_t
]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL

kernel32.GlobalFree.argtypes = [
    wintypes.HGLOBAL
]
kernel32.GlobalFree.restype = wintypes.HGLOBAL

kernel32.GetModuleHandleW.argtypes = [
    wintypes.LPCWSTR
]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

user32.RegisterClassW.argtypes = [
    ctypes.c_void_p
]
user32.RegisterClassW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.DestroyWindow.argtypes = [
    wintypes.HWND
]
user32.DestroyWindow.restype = wintypes.BOOL

user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM
]
user32.DefWindowProcW.restype = LRESULT

user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT
]

# GetMessageW:
# > 0  有消息
# = 0  WM_QUIT
# < 0  错误
user32.GetMessageW.restype = ctypes.c_int

user32.TranslateMessage.argtypes = [
    ctypes.POINTER(wintypes.MSG)
]

user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG)
]
user32.DispatchMessageW.restype = LRESULT

user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM
]
user32.PostMessageW.restype = wintypes.BOOL

user32.PostQuitMessage.argtypes = [
    ctypes.c_int
]
user32.PostQuitMessage.restype = None

user32.LoadIconW.argtypes = [
    wintypes.HINSTANCE,
    wintypes.LPCWSTR
]
user32.LoadIconW.restype = wintypes.HICON

shell32.Shell_NotifyIconW.argtypes = [
    wintypes.DWORD,
    ctypes.c_void_p
]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL


# ============================================================
# 剪贴板读取
# ============================================================

def get_clipboard_text():
    opened = False

    try:
        if not user32.OpenClipboard(None):
            return ""

        opened = True

        handle = user32.GetClipboardData(
            CF_UNICODETEXT
        )

        if not handle:
            return ""

        ptr = kernel32.GlobalLock(handle)

        if not ptr:
            return ""

        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)

    except Exception:
        return ""

    finally:
        if opened:
            try:
                user32.CloseClipboard()
            except Exception:
                pass


def get_clipboard_html():
    format_id = user32.RegisterClipboardFormatW(
        "HTML Format"
    )

    if not format_id:
        return ""

    opened = False

    try:
        if not user32.OpenClipboard(None):
            return ""

        opened = True

        handle = user32.GetClipboardData(
            format_id
        )

        if not handle:
            return ""

        ptr = kernel32.GlobalLock(handle)

        if not ptr:
            return ""

        try:
            raw = ctypes.string_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)

        if not raw:
            return ""

        try:
            data = raw.decode(
                "utf-8",
                errors="ignore"
            )
        except Exception:
            data = raw.decode(
                "latin1",
                errors="ignore"
            )

        start_match = re.search(
            r"StartHTML:(-?\d+)",
            data
        )

        end_match = re.search(
            r"EndHTML:(-?\d+)",
            data
        )

        if start_match and end_match:
            start = int(start_match.group(1))
            end = int(end_match.group(1))

            if (
                start >= 0
                and end > start
                and start < len(raw)
            ):
                end = min(end, len(raw))

                encoded = raw[start:end]

                try:
                    return encoded.decode(
                        "utf-8",
                        errors="ignore"
                    )
                except Exception:
                    return encoded.decode(
                        "latin1",
                        errors="ignore"
                    )

        return data

    except Exception:
        return ""

    finally:
        if opened:
            try:
                user32.CloseClipboard()
            except Exception:
                pass


# ============================================================
# 剪贴板写入
# ============================================================

def set_clipboard_text(text):
    """
    直接使用 Windows API 写入 CF_UNICODETEXT。
    不依赖 Tkinter clipboard_append。
    """

    if not text:
        return False

    encoded = (
        str(text)
        .encode("utf-16-le")
        + b"\x00\x00"
    )

    GMEM_MOVEABLE = 0x0002
    GMEM_ZEROINIT = 0x0040

    h_global = kernel32.GlobalAlloc(
        GMEM_MOVEABLE | GMEM_ZEROINIT,
        len(encoded)
    )

    if not h_global:
        return False

    locked = False

    try:
        ptr = kernel32.GlobalLock(
            h_global
        )

        if not ptr:
            kernel32.GlobalFree(
                h_global
            )
            return False

        locked = True

        ctypes.memmove(
            ptr,
            encoded,
            len(encoded)
        )

        kernel32.GlobalUnlock(
            h_global
        )

        locked = False

        if not user32.OpenClipboard(None):
            kernel32.GlobalFree(
                h_global
            )
            return False

        try:
            if not user32.EmptyClipboard():
                kernel32.GlobalFree(
                    h_global
                )
                return False

            result = user32.SetClipboardData(
                CF_UNICODETEXT,
                h_global
            )

            if not result:
                kernel32.GlobalFree(
                    h_global
                )
                return False

            # 成功后由系统接管内存
            h_global = None

            return True

        finally:
            user32.CloseClipboard()

    except Exception:
        return False

    finally:
        if locked:
            try:
                kernel32.GlobalUnlock(
                    h_global
                )
            except Exception:
                pass

        if h_global:
            try:
                kernel32.GlobalFree(
                    h_global
                )
            except Exception:
                pass


# ============================================================
# 文本处理
# ============================================================

def normalize_text(text):
    if not text:
        return ""

    text = html.unescape(
        str(text)
    )

    text = text.replace(
        "\u200b",
        ""
    )

    text = text.replace(
        "\xa0",
        " "
    )

    return text.strip()


def unique(items):
    result = []
    seen = set()

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def get_host(url):
    match = re.match(
        r"^https?://([^/?#]+)",
        url,
        re.I
    )

    if not match:
        return ""

    host = match.group(1).lower()

    if "@" in host:
        host = host.rsplit("@", 1)[-1]

    return host.split(":", 1)[0]


# ============================================================
# URL 提取
# ============================================================

def extract_urls(text):
    if not text:
        return []

    text = normalize_text(text)

    pattern = re.compile(
        r"https?://[^\s\"'<>`]+",
        re.I
    )

    urls = []

    for match in pattern.finditer(text):
        url = match.group(0)

        url = url.rstrip(
            "，。！？；：、）》】]）\"'<>"
        )

        urls.append(url)

    return urls


def extract_embedded_url(url):
    if not url:
        return url

    if (
        "api.qrserver.com" in url
        or "quickchart.io" in url
    ):
        match = re.search(
            r"[?&]data=([^&]+)",
            url,
            re.I
        )

        if match:
            try:
                return unquote(
                    match.group(1)
                )
            except Exception:
                pass

    return url


# ============================================================
# 网盘识别
# ============================================================

def classify(url):
    host = get_host(url)

    if "pan.baidu.com" in host:
        return "百度网盘"

    if "pan.quark.cn" in host:
        return "夸克网盘"

    if "pan.xunlei.com" in host:
        return "迅雷云盘"

    if (
        "alipan.com" in host
        or "aliyundrive.com" in host
    ):
        return "阿里云盘"

    if (
        "123pan.com" in host
        or "123pan.cn" in host
    ):
        return "123云盘"

    if "cloud.189.cn" in host:
        return "天翼云盘"

    if any(
        item in host
        for item in (
            "lanzou",
            "lanzoux",
            "lanzoui",
            "lanzn"
        )
    ):
        return "蓝奏云"

    if "drive.uc.cn" in host:
        return "UC网盘"

    if (
        "1drv.ms" in host
        or "onedrive.live.com" in host
    ):
        return "OneDrive"

    if "drive.google.com" in host:
        return "GoogleDrive"

    if "mega.nz" in host:
        return "MEGA"

    return ""


# ============================================================
# 百度提取码
# ============================================================

def extract_baidu_pwd(text):
    if not text:
        return ""

    text = normalize_text(text)

    patterns = (
        r"提取码\s*[:：]\s*([a-zA-Z0-9]{4,8})\b",
        r"提取码\s+([a-zA-Z0-9]{4,8})\b",
        r"pwd\s*[:=]\s*([a-zA-Z0-9]{4,8})\b",
        r"密码\s*[:：]\s*([a-zA-Z0-9]{4,8})\b",
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:
            return match.group(1).strip()

    return ""


def add_baidu_pwd(url, pwd):
    if not pwd:
        return url

    if re.search(
        r"[?&]pwd=",
        url,
        re.I
    ):
        return url

    separator = (
        "&"
        if "?" in url
        else "?"
    )

    return (
        url
        + separator
        + "pwd="
        + pwd
    )


# ============================================================
# HTML 属性解析
# ============================================================

def extract_urls_from_html(raw):
    if not raw:
        return []

    urls = []

    pattern = re.compile(
        r'''(?:href|src|data-src|data-url|data-original|value)
        \s*=\s*["']([^"']+)["']''',
        re.I | re.X
    )

    for match in pattern.finditer(raw):
        value = normalize_text(
            match.group(1)
        )

        if (
            value.startswith("http://")
            or value.startswith("https://")
        ):
            urls.append(
                extract_embedded_url(
                    value
                )
            )

    urls.extend(
        extract_urls(raw)
    )

    return unique(urls)


# ============================================================
# 判断是不是本程序目标格式
# ============================================================

NETWORK_NAMES = (
    "百度网盘",
    "夸克网盘",
    "迅雷云盘",
    "阿里云盘",
    "123云盘",
    "天翼云盘",
    "蓝奏云",
    "UC网盘",
    "OneDrive",
    "GoogleDrive",
    "MEGA",
)


def is_converted_result(text):
    """
    兼容两种格式：
      带后缀：网盘名|链接|jy=xxx
      不带后缀：网盘名|链接
    只要前两段合法，就视为已转换结果，避免重复转换。
    """
    if not text:
        return False

    text = normalize_text(text)

    if not text:
        return False

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return False

    expected_suffix = "jy=" + UNZIP_PWD

    for line in lines:
        parts = line.split("|")

        if len(parts) < 2 or len(parts) > 3:
            return False

        network_name = parts[0]
        url = parts[1]

        if network_name not in NETWORK_NAMES:
            return False

        if not (
            url.startswith("http://")
            or url.startswith("https://")
        ):
            return False

        if len(parts) == 3 and parts[2] != expected_suffix:
            return False

    return True


# ============================================================
# 核心转换
# ============================================================

def convert_content(
    raw_html,
    raw_text,
    append_suffix=True
):
    if not raw_html and not raw_text:
        return "", 0

    # 如果剪贴板本来就是最终结果，直接跳过
    if is_converted_result(raw_text):
        return "", 0

    combined = (
        (raw_html or "")
        + "\n"
        + (raw_text or "")
    )

    baidu_pwd = extract_baidu_pwd(combined)

    urls = []

    if raw_html:
        urls.extend(
            extract_urls_from_html(raw_html)
        )
        urls.extend(
            extract_urls(raw_html)
        )

    if raw_text:
        urls.extend(
            extract_urls(raw_text)
        )

    urls = unique(urls)

    lines = []
    seen = set()

    for url in urls:
        url = normalize_text(url)

        if not url:
            continue

        url = extract_embedded_url(url)

        network_type = classify(url)

        if not network_type:
            continue

        if network_type == "百度网盘":
            url = add_baidu_pwd(url, baidu_pwd)

        if append_suffix:
            line = (
                f"{network_type}|"
                f"{url}|"
                f"jy={UNZIP_PWD}"
            )
        else:
            line = f"{network_type}|{url}"

        if line not in seen:
            seen.add(line)
            lines.append(line)

    return (
        "\n".join(lines),
        len(lines)
    )


# ============================================================
# Tk 主程序
# ============================================================

class PanConverter:

    def __init__(self):
        self.running = True
        self.monitor_enabled = True

        self.last_clipboard_signature = ""

        # 程序自己生成的内容
        self.own_clipboard_text = ""

        # 程序写入结果的时间
        self.ignore_until = 0.0

        self.total_count = 0

        # 后缀开关变量
        self.append_suffix_var = tk.BooleanVar(value=APPEND_SUFFIX)

        self.build_ui()

        self.thread = threading.Thread(
            target=self.monitor_clipboard,
            name="ClipboardMonitor",
            daemon=True
        )

        self.thread.start()


    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):
        root.title(APP_NAME)

        root.geometry("900x650")

        root.minsize(760, 550)

        root.protocol(
            "WM_DELETE_WINDOW",
            self.hide_window
        )

        style = ttk.Style()

        try:
            style.theme_use("vista")
        except Exception:
            pass

        main = ttk.Frame(
            root,
            padding=18
        )

        main.pack(
            fill="both",
            expand=True
        )

        title = ttk.Label(
            main,
            text="网盘链接自动提取 / 转换器",
            font=("Microsoft YaHei", 18, "bold")
        )

        title.pack(pady=(0, 8))

        subtitle = ttk.Label(
            main,
            text=(
                "复制网页 / WordPress 内容，"
                "程序会自动检测并转换。"
            ),
            foreground="#666666"
        )

        subtitle.pack(pady=(0, 12))

        self.status_var = tk.StringVar(
            value="正在监控系统剪贴板……"
        )

        ttk.Label(
            main,
            textvariable=self.status_var
        ).pack(
            anchor="w",
            pady=(0, 10)
        )

        ttk.Label(
            main,
            text="最近检测到的内容："
        ).pack(anchor="w")

        self.source = tk.Text(
            main,
            height=10,
            wrap="word",
            font=("Consolas", 10)
        )

        self.source.pack(
            fill="both",
            expand=True,
            pady=(5, 10)
        )

        ttk.Label(
            main,
            text="转换结果："
        ).pack(anchor="w")

        self.result = tk.Text(
            main,
            height=8,
            wrap="word",
            font=("Consolas", 10)
        )

        self.result.pack(
            fill="both",
            expand=True,
            pady=(5, 10)
        )

        button_frame = ttk.Frame(main)
        button_frame.pack(fill="x")

        ttk.Button(
            button_frame,
            text="立即读取剪贴板",
            command=self.manual_parse
        ).pack(
            side="left",
            padx=(0, 8)
        )

        ttk.Button(
            button_frame,
            text="复制转换结果",
            command=self.copy_result
        ).pack(
            side="left",
            padx=(0, 8)
        )

        ttk.Button(
            button_frame,
            text="清空",
            command=self.clear
        ).pack(side="left")

        # 后缀开关
        ttk.Checkbutton(
            button_frame,
            text="追加后缀 |jy=laoquzhang.com",
            variable=self.append_suffix_var,
            command=self.on_append_suffix_changed
        ).pack(side="left", padx=(16, 0))

        self.auto_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            button_frame,
            text="自动监控 / 自动转换",
            variable=self.auto_var,
            command=self.toggle_monitor
        ).pack(side="right")

        ttk.Label(
            main,
            text=(
                "支持百度、夸克、迅雷、阿里、123、"
                "天翼、蓝奏、UC、OneDrive、"
                "Google Drive、MEGA。"
                " 关闭窗口将进入右下角托盘。"
            ),
            foreground="#666666"
        ).pack(
            anchor="w",
            pady=(12, 0)
        )


    # ========================================================
    # 后缀开关切换
    # ========================================================

    def on_append_suffix_changed(self):
        # 切换后清空签名，避免和上一次结果混淆
        self.last_clipboard_signature = ""
        self.own_clipboard_text = ""

        state = "已开启" if self.append_suffix_var.get() else "已关闭"
        self.status_var.set(f"后缀追加{state}，新转换将生效。")


    # ========================================================
    # 隐藏 / 显示
    # ========================================================

    def hide_window(self):
        root.withdraw()

        self.status_var.set(
            "程序正在后台运行，"
            "双击右下角托盘图标可恢复窗口。"
        )


    def show_window(self):
        root.deiconify()

        try:
            root.state("normal")
        except Exception:
            pass

        root.lift()

        # 临时置顶，保证双击托盘后真的能看到
        try:
            root.attributes("-topmost", True)

            root.after(
                250,
                lambda: root.attributes("-topmost", False)
            )
        except Exception:
            pass

        root.focus_force()

        self.status_var.set("正在监控系统剪贴板……")


    # ========================================================
    # 自动开关
    # ========================================================

    def toggle_monitor(self):
        self.monitor_enabled = self.auto_var.get()

        if self.monitor_enabled:
            self.status_var.set("剪贴板自动监控已开启。")
        else:
            self.status_var.set("剪贴板自动监控已暂停。")


    # ========================================================
    # 剪贴板
    # ========================================================

    def get_clipboard(self):
        return (
            get_clipboard_html(),
            get_clipboard_text()
        )


    def make_signature(
        self,
        html_data,
        text_data
    ):
        return (
            html_data
            + "\n---TEXT---\n"
            + text_data
        )


    # ========================================================
    # 自动监控
    # ========================================================

    def monitor_clipboard(self):

        while self.running:

            try:

                if not self.monitor_enabled:
                    time.sleep(CHECK_INTERVAL)
                    continue

                html_data, text_data = self.get_clipboard()

                if not html_data and not text_data:
                    time.sleep(CHECK_INTERVAL)
                    continue

                signature = self.make_signature(
                    html_data,
                    text_data
                )

                # 保险 1：程序自己刚生成的结果
                if (
                    self.own_clipboard_text
                    and text_data.strip()
                    == self.own_clipboard_text.strip()
                ):
                    self.last_clipboard_signature = signature
                    time.sleep(CHECK_INTERVAL)
                    continue

                # 保险 2：已经是目标格式
                if is_converted_result(text_data):
                    self.last_clipboard_signature = signature

                    self.after_ui(
                        lambda:
                        self.status_var.set(
                            "检测到已经转换过的内容，已跳过。"
                        )
                    )

                    time.sleep(CHECK_INTERVAL)
                    continue

                # 保险 3：剪贴板内容完全没有变化
                if signature == self.last_clipboard_signature:
                    time.sleep(CHECK_INTERVAL)
                    continue

                self.last_clipboard_signature = signature

                append_suffix = self.append_suffix_var.get()

                result, count = convert_content(
                    html_data,
                    text_data,
                    append_suffix=append_suffix
                )

                if count <= 0:
                    self.after_ui(
                        lambda:
                        self.status_var.set(
                            "已检测剪贴板，"
                            "未发现可转换的网盘链接。"
                        )
                    )
                else:
                    self.total_count += count

                    self.after_ui(
                        lambda
                        r=result,
                        c=count:
                        self.process_result(r, c)
                    )

            except Exception as exc:
                error_text = str(exc)

                self.after_ui(
                    lambda
                    err=error_text:
                    self.status_var.set(
                        "监控异常：" + err
                    )
                )

            time.sleep(CHECK_INTERVAL)


    # ========================================================
    # UI 跨线程
    # ========================================================

    def after_ui(self, func):
        try:
            root.after(0, func)
        except Exception:
            pass


    # ========================================================
    # 自动转换结果
    # ========================================================

    def process_result(
        self,
        result,
        count
    ):

        self.result.delete("1.0", "end")
        self.result.insert("1.0", result)

        if not AUTO_COPY_RESULT:
            self.status_var.set(f"成功转换 {count} 条链接。")
            return

        ok = set_clipboard_text(result)

        if ok:
            self.own_clipboard_text = result.strip()
            self.ignore_until = time.time() + IGNORE_SECONDS

            self.status_var.set(
                f"成功转换 {count} 条链接，"
                f"结果已自动复制到剪贴板。"
            )

        else:
            self.status_var.set(
                f"成功转换 {count} 条链接，"
                f"自动复制失败。"
            )


    # ========================================================
    # 手动读取
    # ========================================================

    def manual_parse(self):

        html_data, text_data = self.get_clipboard()

        if is_converted_result(text_data):
            self.status_var.set(
                "当前剪贴板已经是转换结果，无需重复转换。"
            )
            return

        append_suffix = self.append_suffix_var.get()

        result, count = convert_content(
            html_data,
            text_data,
            append_suffix=append_suffix
        )

        if count <= 0:
            self.status_var.set("没有发现可转换的网盘链接。")
            return

        self.result.delete("1.0", "end")
        self.result.insert("1.0", result)

        if set_clipboard_text(result):
            self.own_clipboard_text = result.strip()
            self.ignore_until = time.time() + IGNORE_SECONDS
            self.last_clipboard_signature = ""

            self.status_var.set(
                f"手动转换成功：{count} 条，结果已复制。"
            )


    # ========================================================
    # 复制结果
    # ========================================================

    def copy_result(self):

        result = self.result.get("1.0", "end").strip()

        if not result:
            return

        if set_clipboard_text(result):
            self.own_clipboard_text = result
            self.ignore_until = time.time() + IGNORE_SECONDS
            self.last_clipboard_signature = ""

            self.status_var.set("转换结果已复制。")


    # ========================================================
    # 清空
    # ========================================================

    def clear(self):

        self.source.delete("1.0", "end")
        self.result.delete("1.0", "end")

        self.status_var.set("正在监控系统剪贴板……")


    # ========================================================
    # 退出
    # ========================================================

    def quit_program(self):

        if not self.running:
            return

        self.running = False

        try:
            tray.stop()
        except Exception:
            pass

        try:
            root.destroy()
        except Exception:
            pass


# ============================================================
# Windows 托盘
# ============================================================

class TrayIcon:

    def __init__(self):
        self.running = True
        self.hwnd = None

        self.ready = threading.Event()

        self.class_name = "PanConverterTrayWindow"

        self.thread = threading.Thread(
            target=self.tray_thread,
            name="TrayThread",
            daemon=True
        )

        # 非常重要：
        # 保持 WNDCLASS / WNDPROC / NOTIFYICONDATA
        # 这些对象的引用，防止被 Python GC。
        self.WNDCLASS_TYPE = None
        self.NOTIFYICONDATA_TYPE = None
        self.wndproc_callback = None
        self.nid = None

        self.thread.start()

        self.ready.wait(timeout=5)


    # ========================================================
    # 托盘专用线程
    # ========================================================

    def tray_thread(self):

        try:
            self.create_hidden_window()
            self.create_icon()
            self.ready.set()
            self.message_loop()

        except Exception as exc:

            self.ready.set()

            root.after(
                0,
                lambda:
                app.status_var.set(
                    "托盘创建失败：" + str(exc)
                )
            )


    # ========================================================
    # 创建隐藏窗口
    # ========================================================

    def create_hidden_window(self):

        hinstance = kernel32.GetModuleHandleW(None)

        WNDPROCTYPE = ctypes.WINFUNCTYPE(
            LRESULT,
            wintypes.HWND,
            wintypes.UINT,
            WPARAM,
            LPARAM
        )

        self.wndproc_callback = WNDPROCTYPE(self.window_proc)

        class WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", ctypes.c_void_p),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HCURSOR),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        self.WNDCLASS_TYPE = WNDCLASS

        wc = WNDCLASS()

        wc.lpfnWndProc = ctypes.cast(
            self.wndproc_callback,
            ctypes.c_void_p
        )

        wc.hInstance = hinstance
        wc.lpszClassName = self.class_name

        atom = user32.RegisterClassW(ctypes.byref(wc))

        if not atom:
            # 可能是类已经注册，继续尝试创建
            pass

        self.hwnd = user32.CreateWindowExW(
            0,
            self.class_name,
            self.class_name,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            hinstance,
            None
        )

        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())


    # ========================================================
    # 创建托盘图标
    # ========================================================

    def create_icon(self):

        class NOTIFYICONDATA(ctypes.Structure):

            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT),
                ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128),
                ("dwState", wintypes.DWORD),
                ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256),
                ("uVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64),
                ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", ctypes.c_byte * 16),
                ("hBalloonIcon", wintypes.HICON),
            ]

        self.NOTIFYICONDATA_TYPE = NOTIFYICONDATA

        self.nid = NOTIFYICONDATA()

        self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        self.nid.hWnd = self.hwnd
        self.nid.uID = 1
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.nid.uCallbackMessage = WM_TRAY

        self.nid.hIcon = user32.LoadIconW(
            None,
            ctypes.cast(
                ctypes.c_void_p(IDI_APPLICATION),
                wintypes.LPCWSTR
            )
        )

        self.nid.szTip = APP_NAME

        result = shell32.Shell_NotifyIconW(
            NIM_ADD,
            ctypes.byref(self.nid)
        )

        if not result:
            raise ctypes.WinError(ctypes.get_last_error())


    # ========================================================
    # 托盘窗口消息
    # ========================================================

    def window_proc(
        self,
        hwnd,
        msg,
        wparam,
        lparam
    ):

        if msg == WM_TRAY:

            # 双击左键
            if lparam == WM_LBUTTONDBLCLK:

                root.after(0, app.show_window)
                return 0

            # 右键
            if lparam == WM_RBUTTONUP:

                root.after(0, self.show_menu)
                return 0

        if msg == WM_CLOSE:

            self.remove_icon()
            user32.PostQuitMessage(0)
            return 0

        return user32.DefWindowProcW(
            hwnd,
            msg,
            wparam,
            lparam
        )


    # ========================================================
    # 删除托盘图标
    # ========================================================

    def remove_icon(self):

        if self.nid is None:
            return

        try:
            shell32.Shell_NotifyIconW(
                NIM_DELETE,
                ctypes.byref(self.nid)
            )
        except Exception:
            pass


    # ========================================================
    # 右键菜单
    # ========================================================

    def show_menu(self):

        menu = tk.Menu(root, tearoff=0)

        menu.add_command(
            label="显示主窗口",
            command=app.show_window
        )

        menu.add_separator()

        if app.monitor_enabled:
            menu.add_command(
                label="暂停自动转换",
                command=self.pause_monitor
            )
        else:
            menu.add_command(
                label="恢复自动转换",
                command=self.resume_monitor
            )

        menu.add_separator()

        # 后缀追加开关
        if app.append_suffix_var.get():
            menu.add_command(
                label="关闭后缀追加",
                command=self.toggle_append_suffix
            )
        else:
            menu.add_command(
                label="开启后缀追加",
                command=self.toggle_append_suffix
            )

        menu.add_separator()

        menu.add_command(
            label="退出程序",
            command=app.quit_program
        )

        try:
            x = root.winfo_pointerx()
            y = root.winfo_pointery()
            menu.tk_popup(x, y)

        finally:
            try:
                menu.grab_release()
            except Exception:
                pass


    def pause_monitor(self):

        def action():
            app.monitor_enabled = False
            app.auto_var.set(False)
            app.status_var.set("自动监控已暂停。")

        root.after(0, action)


    def resume_monitor(self):

        def action():
            app.monitor_enabled = True
            app.auto_var.set(True)
            app.status_var.set("自动监控已恢复。")

        root.after(0, action)


    def toggle_append_suffix(self):
        """托盘菜单切换后缀追加状态，与主界面复选框同步"""
        def action():
            current = app.append_suffix_var.get()
            app.append_suffix_var.set(not current)
            app.on_append_suffix_changed()

        root.after(0, action)


    # ========================================================
    # Windows 消息循环
    # ========================================================

    def message_loop(self):

        msg = wintypes.MSG()

        while self.running:

            result = user32.GetMessageW(
                ctypes.byref(msg),
                None,
                0,
                0
            )

            if result == -1:
                break

            if result == 0:
                break

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))


    # ========================================================
    # 停止托盘
    # ========================================================

    def stop(self):

        if not self.running:
            return

        self.running = False

        if self.hwnd:

            try:
                self.remove_icon()
            except Exception:
                pass

            try:
                user32.PostMessageW(
                    self.hwnd,
                    WM_CLOSE,
                    0,
                    0
                )
            except Exception:
                pass


# ============================================================
# 程序入口
# ============================================================

root = tk.Tk()

app = PanConverter()

tray = TrayIcon()

root.mainloop()

try:
    tray.stop()
except Exception:
    pass
