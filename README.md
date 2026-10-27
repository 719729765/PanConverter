# PanConverter | 网盘链接自动转换器

Automatically monitor the Windows clipboard, extract various netdisk links from copied text/HTML content, and uniformly format the output. Support system tray background operation and Baidu Netdisk extraction code automatic splicing.

自动监控 Windows 系统剪贴板，从复制的文本/网页内容中提取各类网盘链接，统一格式化输出；支持系统托盘后台运行、百度网盘提取码自动拼接、输出后缀灵活开关。

## ✨ Features | 功能特性

- 📋 **Clipboard Auto Monitor**: Real-time polling of system clipboard, automatic conversion when content is copied
- 🔗 **11 Netdisks Supported**: Cover mainstream domestic and foreign cloud storage services
- 🔑 **Extract Code Auto-merge**: Automatically identify Baidu Netdisk extraction code and splice it into the link URL
- ⚙️ **Suffix Toggle**: One-click enable/disable custom decompression password suffix for output
- 🖥️ **System Tray Support**: Minimize to background tray, no taskbar occupation
- 🎛️ **Dual Modes**: Free switch between automatic monitoring and manual parsing
- 🧹 **Auto Deduplication**: Automatically remove duplicate links in the result
- 🌐 **HTML Parsing**: Extract links from HTML content copied by the browser
- 📱 **QR Link Resolve**: Parse real netdisk links from QR code generation URLs
- 📦 **Portable Single File**: Can be packaged as a standalone exe, no installation required
- 🔒 **Local Processing**: All data is processed locally, no clipboard content is uploaded

---

- 📋 **剪贴板自动监控**：实时轮询系统剪贴板，复制内容即自动转换
- 🔗 **支持 11 款网盘**：覆盖国内外主流云存储服务
- 🔑 **提取码自动拼接**：自动识别百度网盘提取码，自动拼接到链接中
- ⚙️ **后缀开关可控**：一键开启/关闭输出的自定义解压密码后缀
- 🖥️ **系统托盘支持**：最小化后台托盘运行，不占用任务栏
- 🎛️ **双运行模式**：自动监控与手动解析自由切换
- 🧹 **自动去重**：自动去除结果中的重复链接
- 🌐 **HTML 解析**：支持从浏览器复制的 HTML 内容中提取链接
- 📱 **二维码链接解析**：从二维码生成链接中解析真实网盘链接
- 📦 **单文件便携**：可打包为独立 exe，无需安装
- 🔒 **全本地处理**：所有数据本地运算，不上传任何剪贴板内容

## 📦 Supported Netdisks | 支持的网盘列表

| Netdisk Name / 网盘名称 | Domain / 域名标识 |
|-------------------------|-------------------|
| 百度网盘 | `pan.baidu.com` |
| 夸克网盘 | `pan.quark.cn` |
| 迅雷云盘 | `pan.xunlei.com` |
| 阿里云盘 | `shturl.cc/` / `aliyundrive.com` |
| 123云盘 | `123pan.com` / `123pan.cn` |
| 天翼云盘 | `cloud.189.cn` |
| 蓝奏云 | `lanzou*` series domains |
| UC网盘 | `drive.uc.cn` |
| OneDrive | `1drv.ms` / `onedrive.live.com` |
| Google Drive | `drive.google.com` |
| MEGA | `mega.nz` |

## 🚀 Quick Start | 快速开始

### Method 1: Run packaged EXE | 方式一：直接运行打包版
1. Go to the [Releases](https://github.com/719729765/PanConverter/releases) page to download the latest `PanConverter.exe`
2. Double-click to run, the program will start monitoring the clipboard by default
3. Copy any content containing netdisk links, and the converted result will be automatically copied to the clipboard

> 前往 Release 页面下载最新 `PanConverter.exe`，双击即可运行，默认自动监控剪贴板，复制含网盘链接的内容后，转换结果会自动复制到剪贴板。

### Method 2: Run from source code | 方式二：源码运行
#### Environment Requirements | 环境要求
- Windows 7 / 8 / 10 / 11
- Python 3.8 ~ 3.14

#### Steps | 操作步骤
1. Clone the repository | 克隆仓库
```bash
git clone https://github.com/719729765/PanConverter.git
cd PanConverter
