#!/usr/bin/env python3
"""
zetas8.6 - 增强版Zetas Shell工具箱
传统文本输入界面，完整功能列表
修复版本：包含命令补全、历史记录、安全确认、别名管理等修复
更新：添加创建文件、增强Python环境、多命令支持等功能
"""

import sys
import os
import subprocess
import shutil
import json
import time
import platform
import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
import importlib

# ==================== 工具函数 ====================
# 检测是否作为 EXE 运行
def is_running_as_exe():
    """检测当前是否作为打包的 EXE 文件运行"""
    return hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS')

# 在导入其他模块之前先检查并安装依赖（仅当不是 EXE 运行时）
def install_dependencies():
    """安装必要的依赖包"""
    # 如果是 EXE 运行，跳过依赖安装
    if is_running_as_exe():
        return True
        
    required_packages = [
        'pywin32',
        'psutil', 
        'requests',
        'colorama',
        'tqdm',
        'pycryptodome'
    ]
    
    print("正在检查依赖库...")
    
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            print(f"  {package} 已安装")
        except ImportError:
            print(f"  正在安装 {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
                print(f"  {package} 安装成功")
            except Exception as e:
                print(f"  {package} 安装失败: {e}")
                return False
    return True

# 安装依赖（如果不是 EXE 运行）
if not install_dependencies():
    print("\n依赖安装失败，请手动运行以下命令：")
    print("pip install pywin32 psutil requests colorama tqdm pycryptodome")
    sys.exit(1)

# 现在可以安全导入其他模块
import requests
import psutil
import webbrowser
import re
import base64
import io
import textwrap
from colorama import Fore, Style, init, Back
from tqdm import tqdm

# 尝试导入readline用于命令补全
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

# 初始化colorama
init(autoreset=True)

# ==================== PowerShell蓝色主题颜色 ====================
class Colors:
    """PowerShell 蓝色主题颜色"""
    PROMPT = Fore.BLUE + Style.BRIGHT
    COMMAND = Fore.CYAN + Style.BRIGHT
    SUCCESS = Fore.GREEN + Style.BRIGHT
    WARNING = Fore.YELLOW + Style.BRIGHT
    ERROR = Fore.RED + Style.BRIGHT
    INFO = Fore.BLUE
    HIGHLIGHT = Fore.MAGENTA + Style.BRIGHT
    RESET = Style.RESET_ALL
    BANNER = Fore.BLUE + Style.BRIGHT
    HEADER = Fore.CYAN + Style.BRIGHT
    SYSTEM = Fore.WHITE + Style.BRIGHT
    
    # 颜色映射
    COLOR_MAP = {
        'black': Fore.BLACK,
        'red': Fore.RED,
        'green': Fore.GREEN,
        'yellow': Fore.YELLOW,
        'blue': Fore.BLUE,
        'magenta': Fore.MAGENTA,
        'cyan': Fore.CYAN,
        'white': Fore.WHITE,
        'lightblack': Fore.LIGHTBLACK_EX,
        'lightred': Fore.LIGHTRED_EX,
        'lightgreen': Fore.LIGHTGREEN_EX,
        'lightyellow': Fore.LIGHTYELLOW_EX,
        'lightblue': Fore.LIGHTBLUE_EX,
        'lightmagenta': Fore.LIGHTMAGENTA_EX,
        'lightcyan': Fore.LIGHTCYAN_EX,
        'lightwhite': Fore.LIGHTWHITE_EX,
        'bg_black': Back.BLACK,
        'bg_red': Back.RED,
        'bg_green': Back.GREEN,
        'bg_yellow': Back.YELLOW,
        'bg_blue': Back.BLUE,
        'bg_magenta': Back.MAGENTA,
        'bg_cyan': Back.CYAN,
        'bg_white': Back.WHITE,
    }

# ==================== 颜色管理器 ====================
class ColorManager:
    """颜色管理器"""
    
    def __init__(self):
        self.current_foreground = 'white'
        self.current_background = 'black'
        self.update_global_color()
    
    def set_color(self, color_code: str):
        """设置全局颜色（类似于cmd的color命令）"""
        # 支持两种格式：color 0A 或 color 0A
        if len(color_code) == 2:
            try:
                # 解析Windows颜色代码
                bg_code = color_code[0].upper()
                fg_code = color_code[1].upper()
                
                color_map = {
                    '0': 'black', '1': 'blue', '2': 'green', '3': 'cyan',
                    '4': 'red', '5': 'magenta', '6': 'yellow', '7': 'white',
                    '8': 'lightblack', '9': 'lightblue', 'A': 'lightgreen',
                    'B': 'lightcyan', 'C': 'lightred', 'D': 'lightmagenta',
                    'E': 'lightyellow', 'F': 'lightwhite'
                }
                
                if bg_code in color_map and fg_code in color_map:
                    self.current_background = color_map[bg_code]
                    self.current_foreground = color_map[fg_code]
                    self.update_global_color()
                    print(f"{Colors.SUCCESS}颜色已设置为: 背景={self.current_background}, 前景={self.current_foreground}{Colors.RESET}")
                    return True
            except Exception as e:
                print(f"{Colors.ERROR}颜色代码无效: {e}{Colors.RESET}")
                return False
        else:
            print(f"{Colors.ERROR}用法: color <背景><前景> (例如: color 0A){Colors.RESET}")
            return False
    
    def update_global_color(self):
        """更新全局颜色显示"""
        bg_color = Colors.COLOR_MAP.get(f'bg_{self.current_background}', Back.BLACK)
        fg_color = Colors.COLOR_MAP.get(self.current_foreground, Fore.WHITE)
        sys.stdout.write(bg_color + fg_color)
        sys.stdout.flush()
    
    def reset_color(self):
        """重置颜色"""
        self.current_foreground = 'white'
        self.current_background = 'black'
        sys.stdout.write(Colors.RESET)
        sys.stdout.flush()
        print(f"{Colors.SUCCESS}颜色已重置{Colors.RESET}")

# ==================== 增强的伪Python环境 ====================
class EnhancedPythonEnvironment:
    """增强的伪Python环境"""
    
    def __init__(self):
        self.local_vars = {}
        self.available_modules = {
            'math', 'random', 'datetime', 'time', 'os', 'sys',
            'json', 're', 'collections', 'itertools', 'functools',
            'string', 'hashlib', 'base64', 'urllib', 'pathlib'
        }
        self.imported_modules = {}
    
    def execute_code(self, code: str) -> Tuple[bool, Any]:
        """执行Python代码"""
        try:
            # 创建一个安全的执行环境
            exec_globals = {
                '__builtins__': __builtins__,
                '__name__': '__main__',
                '__doc__': None,
                '__package__': None,
                'print': self._custom_print
            }
            
            # 更新全局变量
            exec_globals.update(self.imported_modules)
            exec_globals.update(self.local_vars)
            
            # 执行代码
            exec(code, exec_globals, self.local_vars)
            
            # 更新局部变量
            self.local_vars.update({k: v for k, v in exec_globals.items() 
                                   if not k.startswith('__')})
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def execute_interactive(self):
        """交互式Python环境"""
        print(f"{Colors.HEADER}增强Python交互式环境 (输入 'exit' 退出, 'help' 查看帮助){Colors.RESET}")
        
        while True:
            try:
                code = input(f"{Colors.PROMPT}py>{Colors.RESET} ").strip()
                
                if code.lower() == 'exit':
                    break
                elif code.lower() == 'help':
                    self._show_help()
                    continue
                elif code.lower() == 'clear':
                    self.local_vars.clear()
                    self.imported_modules.clear()
                    print(f"{Colors.SUCCESS}环境已清空{Colors.RESET}")
                    continue
                elif code.lower().startswith('import '):
                    self._import_module(code)
                    continue
                
                success, result = self.execute_code(code)
                if not success:
                    print(f"{Colors.ERROR}错误: {result}{Colors.RESET}")
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}使用 'exit' 退出{Colors.RESET}")
            except EOFError:
                break
    
    def _custom_print(self, *args, **kwargs):
        """自定义print函数，支持颜色"""
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        
        # 检查是否有颜色标记
        text = sep.join(str(arg) for arg in args)
        if text.startswith('$'):
            # 解析颜色标记: $color:text$ 或 $color:bg:color:text$
            parts = text[1:].split('$', 1)
            if len(parts) == 2:
                color_spec, content = parts
                color_parts = color_spec.split(':')
                
                if len(color_parts) == 1:
                    # 只有前景色
                    color_code = color_parts[0]
                    color = Colors.COLOR_MAP.get(color_code, Colors.RESET)
                    text = color + content + Colors.RESET
                elif len(color_parts) == 2:
                    # 背景色和前景色
                    bg_code, fg_code = color_parts
                    bg_color = Colors.COLOR_MAP.get(f'bg_{bg_code}', Colors.RESET)
                    fg_color = Colors.COLOR_MAP.get(fg_code, Colors.RESET)
                    text = bg_color + fg_color + content + Colors.RESET
        
        sys.stdout.write(text + end)
        sys.stdout.flush()
    
    def _show_help(self):
        """显示帮助"""
        help_text = f"""
{Colors.HEADER}增强Python环境帮助:{Colors.RESET}

{Colors.INFO}基本命令:{Colors.RESET}
  exit          - 退出Python环境
  help          - 显示此帮助
  clear         - 清空环境变量和模块
  import <模块> - 导入模块（支持: {', '.join(sorted(self.available_modules))}）

{Colors.INFO}特殊功能:{Colors.RESET}
  1. 彩色输出: print("$red:红色文本$") 或 print("$bg_red:white:红底白字$")
  2. 自动导入: 常用模块已预置
  3. 变量持久化: 变量在会话间保持
  4. 错误处理: 友好的错误信息

{Colors.INFO}示例:{Colors.RESET}
  print("$green:Hello, World!$")
  import math
  result = math.sqrt(16)
  print(f"结果: {{result}}")
"""
        print(help_text)
    
    def _import_module(self, code: str):
        """导入模块"""
        module_name = code[7:].strip().split()[0]
        
        if module_name in self.available_modules:
            try:
                module = __import__(module_name)
                self.imported_modules[module_name] = module
                print(f"{Colors.SUCCESS}模块 '{module_name}' 导入成功{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.ERROR}导入模块失败: {e}{Colors.RESET}")
        else:
            print(f"{Colors.WARNING}模块 '{module_name}' 不在可用列表中{Colors.RESET}")

# ==================== 资源监控器 ====================
class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self, warning_thresholds=None):
        self.warning_thresholds = warning_thresholds or {
            'cpu': 80.0,
            'memory': 85.0,
            'disk': 90.0,
            'temp': 75.0
        }
        self.warnings_enabled = True
    
    def check_resources(self):
        """检查系统资源"""
        warnings = []
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.5)
            if cpu_percent > self.warning_thresholds['cpu']:
                warnings.append(f"CPU使用率过高: {cpu_percent:.1f}%")
            
            # 内存使用率
            mem = psutil.virtual_memory()
            if mem.percent > self.warning_thresholds['memory']:
                warnings.append(f"内存使用率过高: {mem.percent:.1f}%")
            
            # 磁盘使用率
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    if usage.percent > self.warning_thresholds['disk']:
                        warnings.append(f"磁盘 {partition.mountpoint} 空间不足: {usage.percent:.1f}%")
                except Exception:
                    pass
            
        except Exception as e:
            warnings.append(f"监控检查失败: {e}")
        
        return warnings

# ==================== 进度管理器 ====================
class ProgressManager:
    """进度管理器"""
    
    @staticmethod
    def copy_with_progress(src: str, dst: str):
        """带进度显示的文件复制"""
        try:
            total_size = os.path.getsize(src)
            
            with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst, \
                 tqdm(total=total_size, unit='B', unit_scale=True, desc=f"复制 {os.path.basename(src)}") as pbar:
                
                while True:
                    buf = fsrc.read(1024 * 1024)
                    if not buf:
                        break
                    fdst.write(buf)
                    pbar.update(len(buf))
            
            return True
        except Exception as e:
            print(f"{Colors.ERROR}复制失败: {e}{Colors.RESET}")
            return False

# ==================== 别名管理器 ====================
class AliasManager:
    """命令别名管理器"""
    
    def __init__(self):
        self.aliases_file = Path.home() / ".zetas_aliases"
        self.aliases = {}
        self._load_aliases()
    
    def _load_aliases(self):
        """加载别名配置"""
        if self.aliases_file.exists():
            try:
                with open(self.aliases_file, 'r', encoding='utf-8') as f:
                    self.aliases = json.load(f)
            except Exception:
                self.aliases = {}
    
    def _save_aliases(self):
        """保存别名配置"""
        try:
            with open(self.aliases_file, 'w', encoding='utf-8') as f:
                json.dump(self.aliases, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"{Colors.WARNING}保存别名失败: {e}{Colors.RESET}")
    
    def add_alias(self, name: str, command: str):
        """添加别名"""
        if name in ['alias', 'unalias']:
            print(f"{Colors.ERROR}不能为 '{name}' 创建别名{Colors.RESET}")
            return False
        
        self.aliases[name] = command
        self._save_aliases()
        print(f"{Colors.SUCCESS}别名已添加: {name} -> {command}{Colors.RESET}")
        return True
    
    def remove_alias(self, name: str):
        """移除别名"""
        if name in self.aliases:
            del self.aliases[name]
            self._save_aliases()
            print(f"{Colors.SUCCESS}别名已移除: {name}{Colors.RESET}")
            return True
        else:
            print(f"{Colors.WARNING}别名不存在: {name}{Colors.RESET}")
            return False
    
    def list_aliases(self):
        """列出所有别名"""
        if not self.aliases:
            print(f"{Colors.INFO}没有定义任何别名{Colors.RESET}")
            return
        
        print(f"{Colors.HEADER}已定义的别名:{Colors.RESET}")
        for name, command in self.aliases.items():
            print(f"  {Colors.COMMAND}{name:<15}{Colors.RESET} -> {command}")
    
    def expand_alias(self, command: str):
        """展开别名"""
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return command
        
        cmd_name = parts[0]
        if cmd_name in self.aliases:
            alias_command = self.aliases[cmd_name]
            if len(parts) > 1:
                return f"{alias_command} {parts[1]}"
            else:
                return alias_command
        
        return command

# ==================== 配置类 ====================
class Config:
    """配置管理类"""
    def __init__(self):
        self.config_path = Path.home() / ".zetas_config.json"
        self.data = {
            "template_dir": str(Path.home() / "Documents"),
            "default_browser": "",
            "enable_confirmation": True,
            "process_list_page_size": 20,
            "enable_color": True,
            "show_progress_bars": False,
            "language": "zh",
            "theme": "powershell",
            "interface_mode": "console",
            "enable_bash_syntax": True,
            "parameter_priority": True,
            "global_color": "07"
        }
        self.load()
    
    def load(self):
        """加载配置并验证"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                validated_data = self._validate_config(loaded_data)
                self.data.update(validated_data)
                
            except json.JSONDecodeError:
                print(f"{Colors.WARNING}配置文件已损坏，使用默认配置{Colors.RESET}")
                self._create_default_config()
            except Exception as e:
                print(f"{Colors.WARNING}加载配置失败: {e}，使用默认配置{Colors.RESET}")
                self._create_default_config()
    
    def _validate_config(self, config_data):
        """验证配置数据"""
        default_keys = set(self.data.keys())
        input_keys = set(config_data.keys())
        
        validated = {}
        for key in default_keys.intersection(input_keys):
            validated[key] = config_data[key]
        
        for key in default_keys - input_keys:
            validated[key] = self.data[key]
        
        if 'process_list_page_size' in validated:
            validated['process_list_page_size'] = max(10, min(100, validated['process_list_page_size']))
        
        if 'language' in validated and validated['language'] not in ['zh', 'en']:
            validated['language'] = 'zh'
        
        return validated
    
    def _create_default_config(self):
        """创建默认配置文件"""
        try:
            self.save()
            print(f"{Colors.SUCCESS}已创建默认配置文件: {self.config_path}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}创建默认配置文件失败: {e}{Colors.RESET}")
    
    def save(self):
        """保存配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"{Colors.ERROR}保存配置失败: {e}{Style.RESET_ALL}")
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.data.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.data[key] = value
        self.save()

# 全局配置实例
config = Config()

# ==================== 脚本状态类 ====================
class ScriptState:
    def __init__(self):
        self.variables = {}
        self.functions = {}
        self.aliases = {}
        self.current_directory = Path.cwd()
        self.return_code = 0
        self.script_stack = []
        self.encoding = 'utf-8'

script_state = ScriptState()

# ==================== 多命令处理器 ====================
class MultiCommandProcessor:
    """多命令处理器（支持+分隔）"""
    
    def __init__(self, console_interface):
        self.console = console_interface
    
    def parse_commands(self, command_string: str) -> List[str]:
        """解析使用+分隔的命令"""
        commands = []
        current_command = []
        in_quotes = False
        quote_char = None
        skip_next = False
        
        for i, char in enumerate(command_string):
            if skip_next:
                skip_next = False
                current_command.append(char)
                continue
            
            if char == '\\' and i + 1 < len(command_string):
                # 转义字符
                current_command.append(command_string[i + 1])
                skip_next = True
                continue
            
            if char in ('"', "'"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif quote_char == char:
                    in_quotes = False
                    quote_char = None
                current_command.append(char)
            elif char == '+' and not in_quotes:
                # 分隔命令
                if current_command:
                    commands.append(''.join(current_command).strip())
                    current_command = []
            else:
                current_command.append(char)
        
        # 添加最后一个命令
        if current_command:
            commands.append(''.join(current_command).strip())
        
        return commands
    
    def execute_commands(self, command_string: str):
        """执行多个命令"""
        commands = self.parse_commands(command_string)
        
        if len(commands) > 1:
            print(f"{Colors.INFO}检测到 {len(commands)} 个命令，将依次执行:{Colors.RESET}")
        
        results = []
        for i, cmd in enumerate(commands, 1):
            if cmd:  # 跳过空命令
                if len(commands) > 1:
                    print(f"{Colors.HEADER}[{i}/{len(commands)}] 执行: {cmd}{Colors.RESET}")
                
                start_time = time.time()
                try:
                    # 直接调用console的处理方法
                    self.console._process_single_command(cmd)
                    results.append((cmd, True, time.time() - start_time))
                except Exception as e:
                    print(f"{Colors.ERROR}执行失败: {e}{Colors.RESET}")
                    results.append((cmd, False, time.time() - start_time))
        
        # 显示汇总结果
        if len(results) > 1:
            print(f"{Colors.HEADER}执行汇总:{Colors.RESET}")
            success_count = sum(1 for _, success, _ in results if success)
            print(f"  成功: {success_count}/{len(results)} 个命令")
            for cmd, success, exec_time in results:
                status = f"{Colors.SUCCESS}✓" if success else f"{Colors.ERROR}✗"
                print(f"  {status} {cmd} ({exec_time:.2f}s){Colors.RESET}")

# ==================== 文件打开器 ====================
class FileOpener:
    """文件打开器"""
    
    @staticmethod
    def open_file(file_path: str, program_path: str = None) -> bool:
        """打开文件"""
        try:
            file_path = os.path.abspath(file_path)
            
            if not os.path.exists(file_path):
                print(f"{Colors.ERROR}文件不存在: {file_path}{Colors.RESET}")
                return False
            
            # 如果指定了程序，使用指定程序打开
            if program_path:
                if not os.path.exists(program_path):
                    print(f"{Colors.ERROR}程序不存在: {program_path}{Colors.RESET}")
                    return False
                
                print(f"{Colors.INFO}使用 {program_path} 打开 {file_path}{Colors.RESET}")
                try:
                    subprocess.run([program_path, file_path], check=False)
                    return True
                except Exception as e:
                    print(f"{Colors.ERROR}打开失败: {e}{Colors.RESET}")
                    return False
            
            # 如果没有指定程序，使用默认方式打开
            print(f"{Colors.INFO}使用默认程序打开: {file_path}{Colors.RESET}")
            
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # Linux/Mac
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', file_path], check=False)
                else:  # Linux
                    subprocess.run(['xdg-open', file_path], check=False)
            else:
                print(f"{Colors.WARNING}不支持的操作系统: {os.name}{Colors.RESET}")
                return False
            
            return True
            
        except Exception as e:
            print(f"{Colors.ERROR}打开文件失败: {e}{Colors.RESET}")
            return False

# ==================== 参数优先级执行系统 ====================
class ParameterSystem:
    """参数优先级执行系统"""
    
    def __init__(self):
        self.execution_order = []
        self.enhanced_python = EnhancedPythonEnvironment()
        self.color_manager = ColorManager()
        
    def parse_args(self, args: List[str]) -> Dict[str, Any]:
        """解析参数并排序"""
        result: Dict[str, Any] = {
            'commands': [],
            'files': [],
            'directories': [],
            'executables': [],
            'options': {},
            'scripts': []
        }
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg.startswith('/'):
                cmd = arg[1:]
                if i + 1 < len(args) and not args[i + 1].startswith(('-', '/')):
                    result['commands'].append((cmd, args[i + 1]))
                    i += 1
                else:
                    result['commands'].append((cmd, None))
                    
            elif arg.startswith('-'):
                if i + 1 < len(args) and not args[i + 1].startswith(('-', '/')):
                    result['options'][arg] = args[i + 1]
                    i += 1
                else:
                    result['options'][arg] = True
                    
            elif arg.endswith('.zetas'):
                result['scripts'].append(arg)
                
            elif os.path.isdir(arg):
                result['directories'].append(arg)
                
            elif os.path.isfile(arg):
                if self._is_executable(arg):
                    result['executables'].append(arg)
                else:
                    result['files'].append(arg)
                    
            else:
                # 尝试判断是否为可执行文件
                if self._is_executable(arg):
                    result['executables'].append(arg)
                else:
                    result['files'].append(arg)
            
            i += 1
        
        return result
    
    def _is_executable(self, file_path: str) -> bool:
        """判断是否为可执行文件"""
        if not os.path.exists(file_path):
            return False
        
        ext = os.path.splitext(file_path)[1].lower()
        executable_exts = {'.exe', '.bat', '.cmd', '.sh', '.py', '.app'}
        
        if ext in executable_exts:
            return True
        
        # 在Unix-like系统上检查执行权限
        if os.name == 'posix':
            return os.access(file_path, os.X_OK)
        
        return False
    
    def execute_in_order(self, parsed_args: Dict[str, Any], script_state: ScriptState) -> List[Tuple[str, bool]]:
        """按照优先级执行参数"""
        results: List[Tuple[str, bool]] = []
        
        execution_sequence = [
            ('commands', self._execute_command),
            ('scripts', self._execute_script),
            ('files', self._process_file),
            ('directories', self._process_directory),
            ('executables', self._execute_program),
        ]
        
        for category, handler in execution_sequence:
            items = parsed_args.get(category, [])
            for item in items:
                try:
                    if category == 'commands':
                        cmd, arg = item
                        success = handler(cmd, arg, script_state)
                        results.append((f"命令: /{cmd} {arg if arg else ''}", success))
                    else:
                        success = handler(item, parsed_args['options'], script_state)
                        results.append((f"{category[:-1]}: {item}", success))
                except Exception as e:
                    results.append((f"{category[:-1]}: {item} - 错误: {e}", False))
        
        for option, value in parsed_args['options'].items():
            if option == '-console':
                config.set('interface_mode', 'console')
                results.append((f"选项: 切换到控制台界面", True))
            elif option == '-bash':
                config.set('enable_bash_syntax', True)
                results.append((f"选项: 启用Bash语法", True))
        
        return results
    
    def _execute_command(self, command: str, arg: Optional[str], script_state: ScriptState) -> bool:
        """执行内置命令"""
        command_handlers = {
            'p': self._pseudo_python,
            'monitor': self._zy_monitor,
            'bash': self._bash_mode,
            'help': self._show_help,
            'config': self._config_command,
            'sysinfo': self._sysinfo_command,
            'fileops': self._file_operations,
            'process': self._process_management,
            'network': self._network_tools,
            'encode': self._encoding_tools,
            'time': self._time_tools,
            'color': self._color_command
        }
        
        if command in command_handlers:
            return command_handlers[command](arg, script_state)
        else:
            print(f"{Colors.WARNING}未知命令: {command}{Colors.RESET}")
            return False
    
    def _pseudo_python(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """增强的伪Python环境"""
        if arg:
            # 执行单行代码
            success, error = self.enhanced_python.execute_code(arg)
            if not success:
                print(f"{Colors.ERROR}执行错误: {error}{Colors.RESET}")
            return success
        else:
            # 进入交互式环境
            self.enhanced_python.execute_interactive()
            return True
    
    def _color_command(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """颜色命令"""
        if arg:
            return self.color_manager.set_color(arg)
        else:
            print(f"{Colors.INFO}当前颜色: 背景={self.color_manager.current_background}, "
                  f"前景={self.color_manager.current_foreground}{Colors.RESET}")
            print(f"{Colors.INFO}可用颜色代码: 0-9, A-F (例如: color 0A){Colors.RESET}")
            return True
    
    def _zy_monitor(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """启动ZY监控器"""
        print(f"{Colors.HEADER}启动 ZY 监控器...{Colors.RESET}")
        
        if arg:
            print(f"{Colors.INFO}监控目标: {arg}{Colors.RESET}")
        
        try:
            print(f"{Colors.SUCCESS}系统监控已激活{Colors.RESET}")
            print(f"CPU使用率: {psutil.cpu_percent()}%")
            print(f"内存使用率: {psutil.virtual_memory().percent}%")
            return True
        except Exception as e:
            print(f"{Colors.WARNING}监控功能受限: {e}{Colors.RESET}")
            return False
    
    def _bash_mode(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """进入Bash模式"""
        config.set('enable_bash_syntax', True)
        print(f"{Colors.HEADER}Bash 模式已启用{Colors.RESET}")
        
        if arg:
            try:
                result = subprocess.run(arg, shell=True, capture_output=True, text=True)
                print(result.stdout)
                if result.stderr:
                    print(f"{Colors.ERROR}{result.stderr}{Colors.RESET}")
                return result.returncode == 0
            except Exception as e:
                print(f"{Colors.ERROR}执行错误: {e}{Colors.RESET}")
                return False
        
        return True
    
    def _show_help(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """显示帮助"""
        self.print_help()
        return True
    
    def _config_command(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """配置命令"""
        if arg:
            if '=' in arg:
                key, value = arg.split('=', 1)
                config.set(key.strip(), value.strip())
                print(f"{Colors.SUCCESS}配置已更新: {key} = {value}{Colors.RESET}")
            else:
                value = config.get(arg)
                if value is not None:
                    print(f"{Colors.INFO}{arg}: {value}{Colors.RESET}")
                else:
                    print(f"{Colors.WARNING}未知配置项: {arg}{Colors.RESET}")
        else:
            print(f"{Colors.HEADER}当前配置:{Colors.RESET}")
            for key, value in config.data.items():
                print(f"  {Colors.INFO}{key}: {Colors.SYSTEM}{value}{Colors.RESET}")
        
        return True
    
    def _sysinfo_command(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """系统信息命令"""
        self.print_system_info()
        return True
    
    def _file_operations(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """文件操作命令"""
        print(f"{Colors.HEADER}文件操作功能:{Colors.RESET}")
        print(f"{Colors.INFO}可用命令: cp, mv, rm, mkdir, find, ls, dir, cat, touch, open{Colors.RESET}")
        return True
    
    def _process_management(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """进程管理命令"""
        print(f"{Colors.HEADER}进程管理功能:{Colors.RESET}")
        print(f"{Colors.INFO}可用命令: ps, kill, list{Colors.RESET}")
        return True
    
    def _network_tools(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """网络工具命令"""
        print(f"{Colors.HEADER}网络工具功能:{Colors.RESET}")
        print(f"{Colors.INFO}可用命令: ping, netstat, download, open{Colors.RESET}")
        return True
    
    def _encoding_tools(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """编码工具命令"""
        print(f"{Colors.HEADER}编码解码功能:{Colors.RESET}")
        print(f"{Colors.INFO}可用命令: encode, decode, base64, hex{Colors.RESET}")
        return True
    
    def _time_tools(self, arg: Optional[str], script_state: ScriptState) -> bool:
        """时间工具命令"""
        print(f"{Colors.HEADER}时间工具功能:{Colors.RESET}")
        print(f"{Colors.INFO}可用命令: time, date, timestamp{Colors.RESET}")
        return True
    
    def _execute_script(self, script_path: str, options: Dict[str, Any], script_state: ScriptState) -> bool:
        """执行Zetas脚本"""
        print(f"{Colors.INFO}执行脚本: {script_path}{Colors.RESET}")
        if os.path.exists(script_path):
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"{Colors.SUCCESS}脚本内容:{Colors.RESET}")
                print(content[:1000] + "..." if len(content) > 1000 else content)
                return True
            except Exception as e:
                print(f"{Colors.ERROR}读取脚本失败: {e}{Colors.RESET}")
                return False
        else:
            print(f"{Colors.ERROR}脚本文件不存在: {script_path}{Colors.RESET}")
            return False
    
    def _process_file(self, file_path: str, options: Dict[str, Any], script_state: ScriptState) -> bool:
        """处理文件"""
        print(f"{Colors.INFO}处理文件: {file_path}{Colors.RESET}")
        if os.path.exists(file_path):
            print(f"{Colors.SUCCESS}文件存在，大小: {os.path.getsize(file_path)} 字节{Colors.RESET}")
            return True
        else:
            print(f"{Colors.WARNING}文件不存在{Colors.RESET}")
            return False
    
    def _process_directory(self, dir_path: str, options: Dict[str, Any], script_state: ScriptState) -> bool:
        """处理目录"""
        print(f"{Colors.INFO}处理目录: {dir_path}{Colors.RESET}")
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"{Colors.SUCCESS}目录存在{Colors.RESET}")
            return True
        else:
            print(f"{Colors.WARNING}目录不存在{Colors.RESET}")
            return False
    
    def _execute_program(self, program: str, options: Dict[str, Any], script_state: ScriptState) -> bool:
        """执行程序"""
        print(f"{Colors.INFO}执行程序: {program}{Colors.RESET}")
        try:
            # 如果是绝对路径，直接执行
            if os.path.isabs(program):
                subprocess.run(program, shell=True, check=False)
            else:
                # 尝试在当前目录和PATH中查找
                subprocess.run(program, shell=True, check=False)
            return True
        except Exception as e:
            print(f"{Colors.ERROR}执行失败: {e}{Colors.RESET}")
            return False
    
    def print_system_info(self):
        """显示系统信息"""
        print(f"{Colors.HEADER}系统信息:{Colors.RESET}")
        print(f"  系统: {platform.system()} {platform.release()}")
        print(f"  平台: {platform.platform()}")
        print(f"  处理器: {platform.processor()}")
        print(f"  Python版本: {platform.python_version()}")
        print(f"  当前目录: {Path.cwd()}")
        
        try:
            print(f"  CPU使用率: {psutil.cpu_percent()}%")
            mem = psutil.virtual_memory()
            print(f"  内存使用率: {mem.percent}% ({mem.used//(1024**3)}GB/{mem.total//(1024**3)}GB)")
        except ImportError:
            print(f"  {Colors.WARNING}psutil未安装，系统信息受限{Colors.RESET}")
    
    def print_help(self):
        """打印简洁帮助信息"""
        help_text = f"""
{Colors.BANNER}{'='*60}{Colors.RESET}
{Colors.BANNER}              zetas8.6 Shell 工具箱               {Colors.RESET}
{Colors.BANNER}{'='*60}{Colors.RESET}

{Colors.HEADER}基本命令:{Colors.RESET}
  {Colors.COMMAND}help{Colors.RESET}         - 显示帮助信息
  {Colors.COMMAND}exit{Colors.RESET}         - 退出程序
  {Colors.COMMAND}clear{Colors.RESET}        - 清屏
  {Colors.COMMAND}sysinfo{Colors.RESET}      - 显示系统信息
  {Colors.COMMAND}alias{Colors.RESET}        - 显示/设置命令别名
  {Colors.COMMAND}history{Colors.RESET}      - 显示命令历史
  {Colors.COMMAND}echo{Colors.RESET}         - 输出文字
  {Colors.COMMAND}color_echo{Colors.RESET}   - 带颜色输出文字
  {Colors.COMMAND}color{Colors.RESET}        - 设置全局颜色

{Colors.HEADER}文件操作:{Colors.RESET}
  {Colors.COMMAND}ls [目录]{Colors.RESET}     - 列出目录内容
  {Colors.COMMAND}cd <目录>{Colors.RESET}     - 切换目录
  {Colors.COMMAND}pwd{Colors.RESET}          - 显示当前目录
  {Colors.COMMAND}mkdir <目录>{Colors.RESET}  - 创建目录
  {Colors.COMMAND}touch <文件>{Colors.RESET}  - 创建文件
  {Colors.COMMAND}rm <文件>{Colors.RESET}     - 删除文件
  {Colors.COMMAND}cp <源> <目标>{Colors.RESET} - 复制文件
  {Colors.COMMAND}mv <源> <目标>{Colors.RESET} - 移动文件
  {Colors.COMMAND}find <模式>{Colors.RESET}   - 查找文件
  {Colors.COMMAND}cat <文件>{Colors.RESET}    - 显示文件内容
  {Colors.COMMAND}open <文件>{Colors.RESET}   - 打开文件

{Colors.HEADER}系统命令:{Colors.RESET}
  {Colors.COMMAND}ps{Colors.RESET}           - 显示进程列表
  {Colors.COMMAND}kill <PID>{Colors.RESET}    - 结束进程
  {Colors.COMMAND}whoami{Colors.RESET}        - 显示当前用户
  {Colors.COMMAND}date{Colors.RESET}          - 显示日期
  {Colors.COMMAND}time{Colors.RESET}          - 显示时间

{Colors.HEADER}网络命令:{Colors.RESET}
  {Colors.COMMAND}ping <主机>{Colors.RESET}   - Ping测试
  {Colors.COMMAND}ipconfig{Colors.RESET}      - 显示IP配置
  {Colors.COMMAND}netstat{Colors.RESET}       - 显示网络连接

{Colors.HEADER}特殊命令:{Colors.RESET}
  {Colors.COMMAND}/p <代码>{Colors.RESET}      - 增强Python环境
  {Colors.COMMAND}/monitor <目标>{Colors.RESET} - ZY监控器
  {Colors.COMMAND}/bash <命令>{Colors.RESET}    - Bash语法支持
  {Colors.COMMAND}/config [选项]{Colors.RESET}  - 配置管理
  {Colors.COMMAND}/color <代码>{Colors.RESET}   - 设置颜色

{Colors.HEADER}多命令支持:{Colors.RESET}
  使用 + 分隔多个命令，例如:
    {Colors.INFO}open 1.txt + open 2.txt{Colors.RESET}
    {Colors.INFO}cd C:\\ + find *.txt{Colors.RESET}
    {Colors.INFO}echo Hello + color_echo red:World{Colors.RESET}

{Colors.HEADER}官网:{Colors.RESET}
  {Colors.INFO}https://hycz8.netlify.app/{Colors.RESET}

{Colors.BANNER}{'='*60}{Colors.RESET}
"""
        print(help_text)

# ==================== 控制台界面 ====================
class ConsoleInterface:
    """控制台界面"""
    
    def __init__(self):
        self.param_system = ParameterSystem()
        self.running = True
        self.command_history = []
        self.history_index = -1
        
        self.history_file = Path.home() / ".zetas_history"
        self.alias_manager = AliasManager()
        self.resource_monitor = ResourceMonitor()
        self.multi_processor = MultiCommandProcessor(self)
        self.file_opener = FileOpener()
        self.last_resource_check = 0
        self.resource_check_interval = 60
        
        self._load_history()
        
        if READLINE_AVAILABLE:
            self._setup_tab_completion()
    
    def _setup_tab_completion(self):
        """设置Tab自动补全"""
        try:
            def completer(text, state):
                line = readline.get_line_buffer().lstrip()
                
                if not line or line.startswith(' '):
                    commands = [
                        'help', 'exit', 'clear', 'ls', 'cd', 'pwd',
                        'mkdir', 'touch', 'rm', 'cp', 'mv', 'find', 'cat', 'open',
                        'ps', 'kill', 'whoami', 'date', 'time',
                        'ping', 'ipconfig', 'netstat',
                        'alias', 'unalias', 'history',
                        'echo', 'color_echo', 'color'
                    ]
                    matches = [c for c in commands if c.startswith(text)]
                    return matches[state] if state < len(matches) else None
                else:
                    matches = glob.glob(text + '*')
                    matches = [m + '/' if os.path.isdir(m) else m for m in matches]
                    return matches[state] if state < len(matches) else None
            
            readline.set_completer(completer)
            
            if 'libedit' in readline.__doc__:
                readline.parse_and_bind("bind ^I rl_complete")
            else:
                readline.parse_and_bind("tab: complete")
                
        except Exception:
            pass
    
    def _load_history(self):
        """加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.command_history = [line.strip() for line in f.readlines()[-100:]]
            except Exception:
                self.command_history = []
    
    def _save_history(self):
        """保存历史记录到文件"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                for cmd in self.command_history[-100:]:
                    f.write(cmd + '\n')
        except Exception:
            pass
    
    def print_banner(self):
        """打印横幅"""
        banner = f"""
{Colors.BANNER}{'='*60}{Colors.RESET}
{Colors.BANNER}        zetas8.6 Shell 工具箱        {Colors.RESET}
{Colors.BANNER}         版本 8.6 (增强版)          {Colors.RESET}
{Colors.BANNER}{'='*60}{Colors.RESET}
{Colors.INFO}官网: https://hycz8.netlify.app/{Colors.RESET}
{Colors.INFO}输入 'help' 查看帮助{Colors.RESET}
{Colors.INFO}支持多命令执行: 使用 + 分隔命令{Colors.RESET}
"""
        print(banner)
    
    def run_interactive(self):
        """运行交互式模式"""
        self.print_banner()
        
        while self.running:
            try:
                cwd = Path.cwd()
                
                if len(str(cwd)) > 40:
                    display_cwd = "..." + str(cwd)[-37:]
                else:
                    display_cwd = str(cwd)
                
                prompt = f"{Colors.PROMPT}zetas:{display_cwd}>{Colors.RESET} "
                
                try:
                    user_input = input(prompt).strip()
                except EOFError:
                    print(f"\n{Colors.INFO}再见！{Colors.RESET}")
                    break
                except KeyboardInterrupt:
                    print(f"\n{Colors.WARNING}使用 'exit' 退出程序{Colors.RESET}")
                    continue
                
                if not user_input:
                    continue
                
                self.command_history.append(user_input)
                if len(self.command_history) > 100:
                    self.command_history.pop(0)
                self.history_index = -1
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    self._save_history()
                    print(f"{Colors.INFO}再见！{Colors.RESET}")
                    break
                
                self.process_command(user_input)
                
            except Exception as e:
                print(f"{Colors.ERROR}错误: {e}{Colors.RESET}")
        
        self._save_history()
    
    def process_command(self, command: str):
        """处理命令（支持多命令）"""
        import time
        start_time = time.time()
        
        # 检查是否包含多个命令
        if '+' in command:
            self.multi_processor.execute_commands(command)
        else:
            self._process_single_command(command)
        
        execution_time = time.time() - start_time
        if execution_time > 0.1:
            time_str = f"{execution_time:.3f}"
            if execution_time > 1.0:
                time_str = f"{execution_time:.1f}"
            print(f"{Colors.INFO}[执行时间: {time_str}s]{Colors.RESET}")
    
    def _process_single_command(self, command: str):
        """处理单个命令"""
        try:
            expanded_command = self.alias_manager.expand_alias(command)
            if expanded_command != command:
                print(f"{Colors.INFO}执行别名: {command} -> {expanded_command}{Colors.RESET}")
                command = expanded_command
            
            cmd_lower = command.lower()
            
            if cmd_lower == 'history':
                self._show_command_history()
            elif cmd_lower == 'help':
                self.param_system.print_help()
            elif cmd_lower == 'sysinfo':
                self.param_system.print_system_info()
            elif cmd_lower == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                self.print_banner()
            elif command.startswith('/'):
                parts = command[1:].split(maxsplit=1)
                cmd = parts[0] if parts else ''
                arg = parts[1] if len(parts) > 1 else None
                self.param_system._execute_command(cmd, arg, script_state)
            elif cmd_lower.startswith('cd '):
                self._change_directory(command)
            elif cmd_lower.startswith('alias '):
                self._handle_alias_command(command)
            elif cmd_lower == 'alias':
                self.alias_manager.list_aliases()
            elif cmd_lower.startswith('unalias '):
                self._handle_unalias_command(command)
            elif cmd_lower.startswith('ls') or cmd_lower.startswith('dir'):
                self._list_files(command)
            elif cmd_lower.startswith('mkdir '):
                self._make_directory(command)
            elif cmd_lower.startswith('touch '):
                self._touch_file(command)
            elif cmd_lower.startswith('rm '):
                self._remove_file(command)
            elif cmd_lower.startswith('cp '):
                self._copy_file(command)
            elif cmd_lower.startswith('mv '):
                self._move_file(command)
            elif cmd_lower.startswith('find '):
                self._find_file(command)
            elif cmd_lower.startswith('cat ') or cmd_lower.startswith('type '):
                self._show_file_content(command)
            elif cmd_lower.startswith('echo '):
                self._echo_text(command)
            elif cmd_lower.startswith('color_echo '):
                self._color_echo_text(command)
            elif cmd_lower.startswith('color '):
                self._set_global_color(command)
            elif cmd_lower.startswith('open '):
                self._open_file_command(command)
            elif cmd_lower == 'pwd':
                print(f"{Colors.INFO}当前目录: {Path.cwd()}{Colors.RESET}")
            elif cmd_lower == 'ps' or cmd_lower == 'tasklist':
                self._show_process_list()
            elif cmd_lower.startswith('kill ') or cmd_lower.startswith('taskkill '):
                self._kill_process(command)
            elif cmd_lower == 'whoami':
                self._show_current_user()
            elif cmd_lower == 'hostname':
                self._show_hostname()
            elif cmd_lower == 'date':
                self._show_date()
            elif cmd_lower == 'time':
                self._show_time()
            elif cmd_lower.startswith('ping '):
                self._ping_host(command)
            elif cmd_lower == 'ipconfig' or cmd_lower == 'ifconfig':
                self._show_network_config()
            elif cmd_lower == 'netstat':
                self._show_network_connections()
            elif cmd_lower.startswith('base64 '):
                self._base64_encode_decode(command)
            elif cmd_lower.startswith('hex '):
                self._hex_encode_decode(command)
            else:
                # 尝试作为可执行文件执行
                if os.path.exists(command) or self._is_executable_in_path(command):
                    self._run_executable(command)
                else:
                    return_code = self._execute_system_command(command)
                    if return_code == 0:
                        print(f"{Colors.SUCCESS}命令执行完成{Colors.RESET}")
                    elif return_code != -1:
                        print(f"{Colors.WARNING}命令返回非零状态码: {return_code}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}执行错误: {e}{Colors.RESET}")
    
    def _is_executable_in_path(self, command: str) -> bool:
        """检查命令是否在PATH中"""
        if os.path.exists(command):
            return True
        
        # 检查系统PATH
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        for dir_path in path_dirs:
            full_path = os.path.join(dir_path, command)
            if os.path.exists(full_path):
                return True
        
        return False
    
    def _run_executable(self, command: str):
        """运行可执行文件"""
        try:
            print(f"{Colors.INFO}执行程序: {command}{Colors.RESET}")
            
            # 如果是Python脚本，用Python解释器执行
            if command.endswith('.py'):
                subprocess.run([sys.executable, command], check=False)
            else:
                # 其他可执行文件
                subprocess.run(command, shell=True, check=False)
            
            print(f"{Colors.SUCCESS}程序执行完成{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}执行失败: {e}{Colors.RESET}")
    
    def _execute_system_command(self, command: str, timeout: int = 30):
        """执行系统命令"""
        try:
            if os.name == 'nt':
                # Windows 使用 GBK 编码
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='gbk',  # Windows 中文系统使用 GBK
                    errors='replace',  # 用问号替换无法解码的字符
                    timeout=timeout
                )
            else:
                import shlex
                args = shlex.split(command)
                # Linux/macOS 使用 UTF-8
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=timeout
                )
            
            if result.stdout:
                print(result.stdout)
            
            if result.stderr:
                print(f"{Colors.ERROR}{result.stderr}{Colors.RESET}")
            
            return result.returncode
            
        except subprocess.TimeoutExpired:
            print(f"{Colors.ERROR}命令执行超时{Colors.RESET}")
            return -1
        except FileNotFoundError:
            print(f"{Colors.ERROR}命令未找到: {command}{Colors.RESET}")
            return -1
        except Exception as e:
            print(f"{Colors.ERROR}命令执行错误: {e}{Colors.RESET}")
            return -1
    
    def _change_directory(self, command: str):
        """切换目录"""
        try:
            target = command[3:].strip()
            if not target:
                target = str(Path.home())
            
            os.chdir(target)
            print(f"{Colors.SUCCESS}切换到: {Path.cwd()}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}切换目录失败: {e}{Colors.RESET}")
    
    def _handle_alias_command(self, command: str):
        """处理alias命令"""
        parts = command[6:].strip().split('=', 1)
        if len(parts) != 2:
            print(f"{Colors.ERROR}用法: alias 名称=命令{Colors.RESET}")
            return
        
        name = parts[0].strip()
        cmd = parts[1].strip().strip('"\'')
        
        if not name:
            print(f"{Colors.ERROR}别名不能为空{Colors.RESET}")
            return
        
        self.alias_manager.add_alias(name, cmd)
    
    def _handle_unalias_command(self, command: str):
        """处理unalias命令"""
        name = command[8:].strip()
        if not name:
            print(f"{Colors.ERROR}用法: unalias 别名名称{Colors.RESET}")
            return
        
        if name == '-a' or name == '--all':
            confirm = input(f"{Colors.WARNING}确定要删除所有别名吗? (y/N): {Colors.RESET}")
            if confirm.lower() == 'y':
                self.alias_manager.aliases.clear()
                self.alias_manager._save_aliases()
                print(f"{Colors.SUCCESS}所有别名已删除{Colors.RESET}")
        else:
            self.alias_manager.remove_alias(name)
    
    def _show_command_history(self):
        """显示命令历史"""
        if not self.command_history:
            print(f"{Colors.INFO}没有命令历史{Colors.RESET}")
            return
        
        print(f"{Colors.HEADER}命令历史:{Colors.RESET}")
        for i, cmd in enumerate(self.command_history[-20:], 1):
            print(f"  {i:3d}: {cmd}")
    
    def _list_files(self, command: str):
        """列出文件"""
        parts = command.split()
        target = '.'
        
        if len(parts) > 1:
            if parts[1].startswith('-'):
                if len(parts) > 2:
                    target = parts[2]
            else:
                target = parts[1]
        
        try:
            if not os.path.exists(target):
                print(f"{Colors.ERROR}路径不存在: {target}{Colors.RESET}")
                return
            
            if os.path.isdir(target):
                items = os.listdir(target)
                for item in items:
                    full_path = os.path.join(target, item)
                    if os.path.isdir(full_path):
                        print(f"{Colors.INFO}{item}/{Colors.RESET}")
                    elif os.access(full_path, os.X_OK):
                        print(f"{Colors.SUCCESS}{item}*{Colors.RESET}")
                    else:
                        print(item)
            else:
                print(f"{Colors.INFO}{target}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}列出文件失败: {e}{Colors.RESET}")
    
    def _make_directory(self, command: str):
        """创建目录"""
        try:
            dir_name = command[6:].strip()
            if not dir_name:
                print(f"{Colors.ERROR}用法: mkdir <目录名>{Colors.RESET}")
                return
            
            os.makedirs(dir_name, exist_ok=True)
            print(f"{Colors.SUCCESS}目录已创建: {dir_name}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}创建目录失败: {e}{Colors.RESET}")
    
    def _touch_file(self, command: str):
        """创建文件"""
        try:
            files = command[6:].strip().split()
            if not files:
                print(f"{Colors.ERROR}用法: touch <文件1> [文件2] ...{Colors.RESET}")
                return
            
            for file_name in files:
                try:
                    if os.path.exists(file_name):
                        # 更新修改时间
                        os.utime(file_name, None)
                        print(f"{Colors.INFO}已更新修改时间: {file_name}{Colors.RESET}")
                    else:
                        # 创建空文件
                        with open(file_name, 'w', encoding='utf-8') as f:
                            pass
                        print(f"{Colors.SUCCESS}文件已创建: {file_name}{Colors.RESET}")
                except Exception as e:
                    print(f"{Colors.ERROR}创建文件失败 {file_name}: {e}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}操作失败: {e}{Colors.RESET}")
    
    def _remove_file(self, command: str):
        """删除文件"""
        try:
            parts = command[3:].strip().split()
            if not parts:
                print(f"{Colors.ERROR}用法: rm <文件名>{Colors.RESET}")
                return
            
            file_name = parts[0]
            force = '-f' in parts
            
            if not os.path.exists(file_name):
                print(f"{Colors.ERROR}文件不存在: {file_name}{Colors.RESET}")
                return
            
            if not force:
                confirm = input(f"{Colors.WARNING}确定要删除 '{file_name}' 吗? (y/N): {Colors.RESET}")
                if confirm.lower() != 'y':
                    print(f"{Colors.INFO}已取消删除{Colors.RESET}")
                    return
            
            if os.path.isfile(file_name):
                os.remove(file_name)
                print(f"{Colors.SUCCESS}文件已删除: {file_name}{Colors.RESET}")
            else:
                print(f"{Colors.ERROR}{file_name} 不是文件{Colors.RESET}")
                
        except Exception as e:
            print(f"{Colors.ERROR}删除文件失败: {e}{Colors.RESET}")
    
    def _copy_file(self, command: str):
        """复制文件"""
        try:
            parts = command[3:].strip().split()
            if len(parts) < 2:
                print(f"{Colors.ERROR}用法: cp <源文件> <目标文件>{Colors.RESET}")
                return
            
            src = parts[0]
            dst = parts[1]
            show_progress = '-p' in parts
            
            if not os.path.exists(src):
                print(f"{Colors.ERROR}源文件不存在: {src}{Colors.RESET}")
                return
            
            file_size = os.path.getsize(src)
            
            if show_progress and file_size > 10 * 1024 * 1024:
                success = ProgressManager.copy_with_progress(src, dst)
                if success:
                    print(f"{Colors.SUCCESS}文件复制完成: {src} -> {dst}{Colors.RESET}")
            else:
                shutil.copy2(src, dst)
                success = True
                print(f"{Colors.SUCCESS}文件已复制: {src} -> {dst} ({file_size:,} 字节){Colors.RESET}")
            
            return success
            
        except Exception as e:
            print(f"{Colors.ERROR}复制文件失败: {e}{Colors.RESET}")
            return False
    
    def _move_file(self, command: str):
        """移动文件"""
        try:
            parts = command[3:].strip().split()
            if len(parts) < 2:
                print(f"{Colors.ERROR}用法: mv <源文件> <目标文件>{Colors.RESET}")
                return
            
            src = parts[0]
            dst = parts[1]
            
            if os.path.exists(src):
                shutil.move(src, dst)
                print(f"{Colors.SUCCESS}文件已移动: {src} -> {dst}{Colors.RESET}")
            else:
                print(f"{Colors.ERROR}源文件不存在: {src}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}移动文件失败: {e}{Colors.RESET}")
    
    def _find_file(self, command: str):
        """查找文件"""
        try:
            pattern = command[5:].strip()
            if not pattern:
                print(f"{Colors.ERROR}用法: find <模式>{Colors.RESET}")
                return
            
            matches = []
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if pattern in file:
                        matches.append(os.path.join(root, file))
            
            if matches:
                print(f"{Colors.SUCCESS}找到 {len(matches)} 个文件:{Colors.RESET}")
                for match in matches[:20]:
                    print(f"  {match}")
                if len(matches) > 20:
                    print(f"{Colors.INFO}... 还有 {len(matches)-20} 个结果未显示{Colors.RESET}")
            else:
                print(f"{Colors.WARNING}未找到匹配的文件{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}查找文件失败: {e}{Colors.RESET}")
    
    def _show_file_content(self, command: str):
        """显示文件内容"""
        try:
            if command.lower().startswith('cat '):
                file_name = command[4:].strip()
            else:
                file_name = command[5:].strip()
            
            if not file_name:
                print(f"{Colors.ERROR}用法: cat <文件名>{Colors.RESET}")
                return
            
            if os.path.exists(file_name):
                with open(file_name, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(content)
            else:
                print(f"{Colors.ERROR}文件不存在: {file_name}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}读取文件失败: {e}{Colors.RESET}")
    
    def _echo_text(self, command: str):
        """输出文字"""
        text = command[5:].strip()
        print(text)
    
    def _color_echo_text(self, command: str):
        """带颜色的文字输出"""
        try:
            text = command[11:].strip()
            
            # 解析颜色格式: color:文本 或 bg:color:文本
            if ':' in text:
                parts = text.split(':', 1)
                if len(parts) == 2:
                    color_spec, content = parts
                    
                    if ':' in color_spec:
                        # 背景色和前景色: bg:color:文本
                        bg_color, fg_color = color_spec.split(':', 1)
                        bg_code = Colors.COLOR_MAP.get(f'bg_{bg_color}', Colors.RESET)
                        fg_code = Colors.COLOR_MAP.get(fg_color, Colors.RESET)
                        print(bg_code + fg_code + content + Colors.RESET)
                    else:
                        # 只有前景色: color:文本
                        color_code = Colors.COLOR_MAP.get(color_spec, Colors.RESET)
                        print(color_code + content + Colors.RESET)
                else:
                    print(text)
            else:
                print(text)
        except Exception as e:
            print(f"{Colors.ERROR}颜色输出失败: {e}{Colors.RESET}")
    
    def _set_global_color(self, command: str):
        """设置全局颜色"""
        color_code = command[6:].strip()
        if color_code:
            self.param_system.color_manager.set_color(color_code)
        else:
            print(f"{Colors.INFO}用法: color <颜色代码>{Colors.RESET}")
            print(f"{Colors.INFO}示例: color 0A (黑色背景，绿色文字){Colors.RESET}")
    
    def _open_file_command(self, command: str):
        """打开文件命令"""
        try:
            # 解析命令: open 文件路径 {程序路径}
            parts = command[5:].strip().split('{', 1)
            file_part = parts[0].strip()
            
            program_path = None
            if len(parts) > 1:
                program_part = parts[1].rstrip('}')
                program_path = program_part.strip()
            
            # 支持多个文件，用空格分隔
            files = file_part.split()
            
            for file_path in files:
                if file_path:  # 跳过空字符串
                    print(f"{Colors.INFO}打开文件: {file_path}{Colors.RESET}")
                    success = self.file_opener.open_file(file_path, program_path)
                    if not success:
                        print(f"{Colors.WARNING}文件打开失败: {file_path}{Colors.RESET}")
        
        except Exception as e:
            print(f"{Colors.ERROR}打开文件失败: {e}{Colors.RESET}")
    
    def _show_process_list(self):
        """显示进程列表"""
        try:
            if os.name == 'nt':
                result = subprocess.run(['tasklist'], capture_output=True, text=True, encoding='gbk', shell=True)
            else:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, encoding='utf-8')
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"{Colors.ERROR}{result.stderr}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}获取进程列表失败: {e}{Colors.RESET}")
    
    def _kill_process(self, command: str):
        """结束进程"""
        try:
            parts = command.split()
            if len(parts) < 2:
                print(f"{Colors.ERROR}用法: kill <PID>{Colors.RESET}")
                return
            
            pid = parts[1]
            
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True, text=True, encoding='gbk', shell=True)
            else:
                subprocess.run(['kill', '-9', pid], capture_output=True, text=True, encoding='utf-8')
            
            print(f"{Colors.SUCCESS}已尝试结束进程: {pid}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}结束进程失败: {e}{Colors.RESET}")
    
    def _show_current_user(self):
        """显示当前用户"""
        try:
            if os.name == 'nt':
                result = subprocess.run(['whoami'], capture_output=True, text=True, encoding='gbk', shell=True)
            else:
                result = subprocess.run(['whoami'], capture_output=True, text=True, encoding='utf-8')
            
            if result.stdout:
                print(result.stdout.strip())
        except Exception as e:
            print(f"{Colors.ERROR}获取用户信息失败: {e}{Colors.RESET}")
    
    def _show_hostname(self):
        """显示主机名"""
        try:
            if os.name == 'nt':
                result = subprocess.run(['hostname'], capture_output=True, text=True, encoding='gbk', shell=True)
            else:
                result = subprocess.run(['hostname'], capture_output=True, text=True, encoding='utf-8')
            
            if result.stdout:
                print(result.stdout.strip())
        except Exception as e:
            print(f"{Colors.ERROR}获取主机名失败: {e}{Colors.RESET}")
    
    def _show_date(self):
        """显示日期"""
        try:
            now = datetime.now()
            print(now.strftime("%Y年%m月%d日 %A"))
        except Exception as e:
            print(f"{Colors.ERROR}获取日期失败: {e}{Colors.RESET}")
    
    def _show_time(self):
        """显示时间"""
        try:
            now = datetime.now()
            print(now.strftime("%H:%M:%S"))
        except Exception as e:
            print(f"{Colors.ERROR}获取时间失败: {e}{Colors.RESET}")
    
    def _ping_host(self, command: str):
        """Ping测试"""
        try:
            host = command[5:].strip()
            if not host:
                # 没有参数时显示友好提示
                print(f"{Colors.INFO}用法: ping <主机名或IP地址>{Colors.RESET}")
                print(f"{Colors.INFO}示例:{Colors.RESET}")
                print(f"  ping google.com")
                print(f"  ping 8.8.8.8")
                print(f"  ping localhost")
                return
            
            print(f"{Colors.INFO}Ping测试: {host}{Colors.RESET}")
            
            if os.name == 'nt':
                # Windows ping 命令
                result = subprocess.run(['ping', host], 
                                      capture_output=True, 
                                      text=True,
                                      encoding='gbk',
                                      shell=True)
            else:
                # Linux/macOS ping 命令
                result = subprocess.run(['ping', '-c', '4', host], 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8')
            
            if result.stdout:
                # 解析并显示友好的结果
                output = result.stdout
                
                # 提取关键信息
                if "找不到主机" in output or "Unknown host" in output:
                    print(f"{Colors.ERROR}错误: 无法解析主机名 '{host}'{Colors.RESET}")
                elif "请求超时" in output or "Request timed out" in output:
                    print(f"{Colors.WARNING}警告: 请求超时，主机可能不可达{Colors.RESET}")
                elif "字节=32" in output or "bytes=32" in output:
                    # 提取统计信息
                    lines = output.split('\n')
                    for line in lines:
                        if "平均" in line or "Average" in line:
                            print(f"{Colors.SUCCESS}统计: {line.strip()}{Colors.RESET}")
                            break
                    print(f"{Colors.SUCCESS}Ping 测试成功{Colors.RESET}")
                
                # 显示原始输出（去除过长部分）
                max_lines = 15
                lines = output.split('\n')[:max_lines]
                if len(output.split('\n')) > max_lines:
                    lines.append("... (输出已截断)")
                
                for line in lines:
                    if line.strip():
                        print(f"  {line}")
            
            if result.stderr:
                error_msg = result.stderr.strip()
                if error_msg:
                    print(f"{Colors.ERROR}{error_msg}{Colors.RESET}")
                    
        except Exception as e:
            print(f"{Colors.ERROR}Ping测试失败: {e}{Colors.RESET}")
    
    def _show_network_config(self):
        """显示网络配置"""
        try:
            if os.name == 'nt':
                result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='gbk', shell=True)
            else:
                result = subprocess.run(['ifconfig'], capture_output=True, text=True, encoding='utf-8')
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"{Colors.ERROR}{result.stderr}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}获取网络配置失败: {e}{Colors.RESET}")
    
    def _show_network_connections(self):
        """显示网络连接"""
        try:
            if os.name == 'nt':
                result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, encoding='gbk', shell=True)
            else:
                result = subprocess.run(['netstat', '-tulpn'], capture_output=True, text=True, encoding='utf-8')
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"{Colors.ERROR}{result.stderr}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}获取网络连接失败: {e}{Colors.RESET}")
    
    def _base64_encode_decode(self, command: str):
        """Base64编码/解码"""
        try:
            text = command[7:].strip()
            if not text:
                print(f"{Colors.ERROR}用法: base64 <文本>{Colors.RESET}")
                return
            
            try:
                decoded = base64.b64decode(text).decode('utf-8')
                print(f"{Colors.SUCCESS}解码结果:{Colors.RESET} {decoded}")
            except:
                encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
                print(f"{Colors.SUCCESS}编码结果:{Colors.RESET} {encoded}")
        except Exception as e:
            print(f"{Colors.ERROR}Base64操作失败: {e}{Colors.RESET}")
    
    def _hex_encode_decode(self, command: str):
        """十六进制编码/解码"""
        try:
            text = command[4:].strip()
            if not text:
                print(f"{Colors.ERROR}用法: hex <文本>{Colors.RESET}")
                return
            
            hex_pattern = re.compile(r'^[0-9a-fA-F]+$')
            if hex_pattern.match(text.replace(' ', '')):
                try:
                    decoded = bytes.fromhex(text.replace(' ', '')).decode('utf-8')
                    print(f"{Colors.SUCCESS}解码结果:{Colors.RESET} {decoded}")
                except:
                    print(f"{Colors.ERROR}无法解码为UTF-8文本{Colors.RESET}")
            else:
                encoded = text.encode('utf-8').hex()
                print(f"{Colors.SUCCESS}编码结果:{Colors.RESET} {encoded}")
        except Exception as e:
            print(f"{Colors.ERROR}十六进制操作失败: {e}{Colors.RESET}")

# ==================== 主函数 ====================
def main():
    """主函数 - zetas8.6 Shell"""
    print(f"{Colors.BANNER}zetas8.6 Shell 工具箱{Colors.RESET}")
    print(f"{Colors.INFO}版本 8.6 (增强版) | 官网: https://hycz8.netlify.app/{Colors.RESET}")
    
    if is_running_as_exe():
        print(f"{Colors.SUCCESS}检测到程序作为 EXE 运行{Colors.RESET}")
    else:
        print(f"{Colors.INFO}运行模式: Python脚本模式{Colors.RESET}")
    
    print(f"{Colors.INFO}新增功能: 多命令支持(+), 增强Python环境, 文件操作等{Colors.RESET}")
    print()
    
    if len(sys.argv) > 1:
        param_system = ParameterSystem()
        parsed_args = param_system.parse_args(sys.argv[1:])
        
        results = param_system.execute_in_order(parsed_args, script_state)
        
        print(f"{Colors.HEADER}执行结果:{Colors.RESET}")
        for action, success in results:
            status = f"{Colors.SUCCESS}成功" if success else f"{Colors.ERROR}失败"
            print(f"  {status} {action}{Colors.RESET}")
    
    else:
        console = ConsoleInterface()
        console.run_interactive()

if __name__ == "__main__":
    main()