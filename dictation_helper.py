import os
import sys
import keyboard
import json
import time
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFileDialog,
    QProgressBar,
    QMenu,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QAction
import pygame
import re


# 创建一个热键处理类，用于在线程间安全通信
class KeyboardHandler(QObject):
    # 信号可以传递一个来源标识字符串
    replay_signal = Signal(str)
    next_signal = Signal(str)
    previous_signal = Signal(str)
    hotkey_pause_signal = Signal(str)

    def __init__(self):
        super().__init__()

    def replay_triggered(self):
        self.replay_signal.emit("hotkey")  # 使用字符串区分来源

    def next_triggered(self):
        self.next_signal.emit("hotkey")

    def previous_triggered(self):
        self.previous_signal.emit("hotkey")

    def hotkey_pause_triggered(self):
        self.hotkey_pause_signal.emit("hotkey")


class DictationHelper(QMainWindow):
    def __init__(self):
        super().__init__()

        # 初始化音频播放器
        pygame.mixer.init()

        # 设置程序状态变量
        self.audio_file = None
        self.srt_file = None
        self.current_segment = -1  # 开始为-1，表示还没有播放任何片段
        self.segments = []
        self.playback_timer = QTimer(self)  # 用于控制播放时长
        self.playback_timer.timeout.connect(self.stop_playback)
        self.allow_hotkeys_flag = True

        # 状态保存相关
        self.progress_data = {}

        # 获取基础路径 - 区分打包环境和开发环境
        self.base_path = self.get_base_path()
        print(f"Base path: {self.base_path}")
        self.progress_file = os.path.join(self.base_path, "dictation_progress.json")
        self.load_progress()

        # 设置UI
        self.init_ui()

        # 创建热键处理器
        self.keyboard_handler = KeyboardHandler()
        self.keyboard_handler.replay_signal.connect(self.replay_current)
        self.keyboard_handler.next_signal.connect(self.play_next)
        self.keyboard_handler.previous_signal.connect(self.play_previous)
        self.keyboard_handler.hotkey_pause_signal.connect(self.allow_hotkeys)

        # 设置全局热键 - 修改重播热键为alt+x
        keyboard.add_hotkey("alt+x", self.keyboard_handler.replay_triggered)
        keyboard.add_hotkey("enter", self.keyboard_handler.next_triggered)
        keyboard.add_hotkey("alt+left", self.keyboard_handler.previous_triggered)
        keyboard.add_hotkey("alt+n", self.keyboard_handler.hotkey_pause_triggered)

    def get_base_path(self):
        if getattr(sys, "frozen", False):
            # 打包环境 - PyInstaller, cx_Freeze等
            return os.path.dirname(os.path.realpath(sys.executable))
        elif "__compiled__" in globals():
            # Nuitka编译环境
            return os.path.dirname(os.path.realpath(sys.argv[0]))
        else:
            # 开发环境 - 使用当前脚本的路径
            return os.path.dirname(os.path.realpath(__file__))

    def init_ui(self):
        self.setWindowTitle("Dictation Helper")
        self.setGeometry(100, 100, 600, 400)

        # 创建主布局
        main_layout = QVBoxLayout()

        # 文件选择区域
        file_layout = QHBoxLayout()

        self.audio_btn = QPushButton("Select Audio File", self)
        self.audio_btn.clicked.connect(self.show_audio_menu)
        file_layout.addWidget(self.audio_btn)

        self.srt_btn = QPushButton("Select Subtitle File", self)
        self.srt_btn.clicked.connect(self.show_srt_menu)
        file_layout.addWidget(self.srt_btn)

        main_layout.addLayout(file_layout)

        # 状态显示区域
        self.status_label = QLabel("Please select audio and subtitle files", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        # 进度显示
        progress_layout = QHBoxLayout()

        self.progress_label = QLabel("0/0", self)
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        main_layout.addLayout(progress_layout)

        # 字幕内容显示
        self.content_label = QLabel("", self)
        self.content_label.setAlignment(Qt.AlignCenter)
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet("font-size: 16pt;")
        main_layout.addWidget(self.content_label)

        # 控制按钮区域
        control_layout = QHBoxLayout()

        self.prev_btn = QPushButton("Previous (Alt+←)", self)
        self.prev_btn.clicked.connect(lambda: self.play_previous("button"))
        control_layout.addWidget(self.prev_btn)

        self.replay_btn = QPushButton("Replay (Alt+X)", self)  # 更新按钮文本
        self.replay_btn.clicked.connect(lambda: self.replay_current("button"))
        control_layout.addWidget(self.replay_btn)

        self.next_btn = QPushButton("Next (Enter)", self)
        self.next_btn.clicked.connect(lambda: self.play_next("button"))
        control_layout.addWidget(self.next_btn)

        main_layout.addLayout(control_layout)

        # 热键暂停按钮
        another_control_layout = QHBoxLayout()
        self.hotkey_pause_btn = QPushButton("Toggle Hotkeys", self)
        self.hotkey_pause_btn.clicked.connect(lambda: self.allow_hotkeys("button"))
        another_control_layout.addWidget(self.hotkey_pause_btn)
        main_layout.addLayout(another_control_layout)

        # 热键提示
        hotkey_hint = QLabel(
            "Hotkeys: Alt+X (Replay), Enter (Next), Alt+← (Previous)",
            self,  # 更新热键提示
        )
        hotkey_hint.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(hotkey_hint)

        # 设置主窗口部件
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def load_progress(self):
        """从JSON文件加载进度数据"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.progress_data = data.get("progress", {})
        except Exception as e:
            print(f"Error loading progress data: {e}")
            self.progress_data = {}

    def save_progress(self):
        """将当前进度保存到JSON文件"""
        try:
            data_to_save = {"progress": self.progress_data}

            if self.audio_file:
                file_key = self.get_file_key()
                if file_key:
                    current_segment = self.progress_data[file_key].get(
                        "current_segment", -1
                    )
                    if current_segment < self.current_segment:
                        current_segment = self.current_segment
                    self.progress_data[file_key] = {
                        "audio_file": self.audio_file,
                        "srt_file": self.srt_file,
                        "current_segment": current_segment,
                        "last_accessed": int(time.time()),  # 添加最后访问时间
                    }

            # 保存数据
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving progress data: {e}")

    def get_file_key(self):
        """根据音频文件名生成唯一键"""
        if self.audio_file:
            return os.path.basename(self.audio_file)
        return None

    def add_recent_file(self, file_path, file_type):
        """添加文件到进度数据中"""
        if not file_path or not os.path.exists(file_path):
            return

        # 更新当前文件的最后访问时间
        file_key = (
            os.path.basename(file_path) if file_type == "audio" else self.get_file_key()
        )

        if file_type == "audio":
            # 如果是添加音频文件
            self.progress_data[file_key] = self.progress_data.get(file_key, {})
            self.progress_data[file_key]["audio_file"] = file_path
            self.progress_data[file_key]["last_accessed"] = int(time.time())
            if "current_segment" not in self.progress_data[file_key]:
                self.progress_data[file_key]["current_segment"] = -1
        elif file_type == "srt" and file_key:
            # 如果是添加字幕文件，并且有对应的音频文件
            if file_key in self.progress_data:
                self.progress_data[file_key]["srt_file"] = file_path
                self.progress_data[file_key]["last_accessed"] = int(time.time())

        # 保存进度
        self.save_progress()

    def get_recent_files(self, file_type, limit=10):
        """获取最近使用的文件列表"""
        result = []
        # 根据last_accessed排序进度数据
        sorted_items = sorted(
            self.progress_data.items(),
            key=lambda x: x[1].get("last_accessed", 0),
            reverse=True,
        )

        # 获取文件路径
        for _, data in sorted_items:
            file_path = data.get(f"{file_type}_file")
            if file_path and os.path.exists(file_path) and file_path not in result:
                result.append(file_path)
                if len(result) >= limit:
                    break

        return result

    def show_audio_menu(self):
        """显示音频文件选择菜单，包含最近文件"""
        menu = QMenu(self)

        # 添加"浏览..."选项
        browse_action = QAction("Browse...", self)
        browse_action.triggered.connect(self.open_audio_file)
        menu.addAction(browse_action)

        # 获取最近的音频文件
        recent_audio_files = self.get_recent_files("audio")

        # 如果有最近文件，添加分隔线和最近文件
        if recent_audio_files:
            menu.addSeparator()
            menu.addAction("Recent Audio Files").setEnabled(False)

            for file_path in recent_audio_files:
                action = QAction(os.path.basename(file_path), self)
                action.setData(file_path)
                action.triggered.connect(
                    lambda checked, path=file_path: self.open_recent_audio(path)
                )
                menu.addAction(action)

        # 显示菜单
        menu.exec(self.audio_btn.mapToGlobal(self.audio_btn.rect().bottomLeft()))

    def show_srt_menu(self):
        """显示字幕文件选择菜单，包含最近文件"""
        menu = QMenu(self)

        # 添加"浏览..."选项
        browse_action = QAction("Browse...", self)
        browse_action.triggered.connect(self.open_srt_file)
        menu.addAction(browse_action)

        # 获取最近的字幕文件
        recent_srt_files = self.get_recent_files("srt")

        # 如果有最近文件，添加分隔线和最近文件
        if recent_srt_files:
            menu.addSeparator()
            menu.addAction("Recent Subtitle Files").setEnabled(False)

            for file_path in recent_srt_files:
                action = QAction(os.path.basename(file_path), self)
                action.setData(file_path)
                action.triggered.connect(
                    lambda checked, path=file_path: self.open_recent_srt(path)
                )
                menu.addAction(action)

        # 显示菜单
        menu.exec(self.srt_btn.mapToGlobal(self.srt_btn.rect().bottomLeft()))

    def open_srt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Subtitle File", "", "Subtitle Files (*.srt)"
        )
        if file_path:
            # 重置播放状态
            self.reset_playback_state()

            self.srt_file = file_path
            self.status_label.setText(
                f"Subtitle file selected: {os.path.basename(file_path)}"
            )
            self.parse_srt()

            # 如果音频文件已加载，尝试恢复进度
            if self.audio_file:
                self.restore_progress()

    def open_recent_audio(self, file_path):
        """打开最近使用的音频文件"""
        # 重置播放状态
        self.reset_playback_state()

        self.audio_file = file_path
        self.status_label.setText(f"Audio file selected: {os.path.basename(file_path)}")
        pygame.mixer.music.load(self.audio_file)

        # 添加到最近文件列表
        self.add_recent_file(file_path, "audio")

        # 自动寻找匹配的字幕文件
        self.find_matching_subtitle()

        # 尝试恢复之前的进度
        self.restore_progress()

    def find_matching_subtitle(self):
        """自动寻找匹配的字幕文件"""
        if not self.audio_file:
            return

        # 先检查是否在进度数据中有记录
        file_key = self.get_file_key()
        print(file_key, self.audio_file, self.srt_file)
        if file_key and file_key in self.progress_data:
            saved_srt = self.progress_data[file_key].get("srt_file")
            if saved_srt and os.path.exists(saved_srt):
                self.srt_file = saved_srt
                self.status_label.setText(
                    f"Found saved subtitle: {os.path.basename(saved_srt)}"
                )
                print("Found saved subtitle:", saved_srt)
                self.parse_srt()
                return

        # 如果进度数据中没有，则寻找同名的SRT文件
        audio_dir = os.path.dirname(self.audio_file)
        audio_name = os.path.splitext(os.path.basename(self.audio_file))[0]

        # 尝试在相同目录下找同名.srt文件
        potential_srt = os.path.join(audio_dir, audio_name + ".srt")
        if os.path.exists(potential_srt):
            self.srt_file = potential_srt
            self.status_label.setText(
                f"Auto-loaded subtitle: {os.path.basename(potential_srt)}"
            )
            print("Auto-loaded subtitle:", potential_srt)
            self.add_recent_file(potential_srt, "srt")
            self.parse_srt()
            return

        # 尝试在相同目录下找包含音频文件名的.srt文件
        for file in os.listdir(audio_dir):
            if file.endswith(".srt") and audio_name.lower() in file.lower():
                potential_srt = os.path.join(audio_dir, file)
                self.srt_file = potential_srt
                self.status_label.setText(f"Found similar subtitle: {file}")

                self.add_recent_file(potential_srt, "srt")
                self.parse_srt()
                print("Found saved subtitle:", potential_srt)
                return

        self.status_label.setText("No matching subtitle found. Please select manually.")

    def restore_progress(self):
        """恢复之前保存的进度"""
        file_key = self.get_file_key()
        if file_key and file_key in self.progress_data:
            saved_data = self.progress_data[file_key]

            # 检查SRT文件是否匹配或需要加载
            if (
                saved_data.get("srt_file")
                and self.srt_file != saved_data["srt_file"]
                and os.path.exists(saved_data["srt_file"])
            ):
                self.srt_file = saved_data["srt_file"]
                self.parse_srt()

            # 恢复到之前的段落位置
            saved_segment = saved_data.get("current_segment", -1)
            if 0 <= saved_segment < len(self.segments):
                # 稍后播放，先更新UI
                self.current_segment = (
                    saved_segment - 1
                )  # 设为前一个，这样play_next会播放正确的段落
                self.status_label.setText(
                    f"Progress restored - segment {saved_segment + 1}/{len(self.segments)}"
                )
                QTimer.singleShot(500, self.play_next)  # 延迟500ms后播放下一段

            # 更新最后访问时间
            saved_data["last_accessed"] = int(time.time())
            self.save_progress()

    def open_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio Files (*.mp3 *.wav *.ogg)"
        )
        if file_path:
            # 重置播放状态
            self.reset_playback_state()

            self.audio_file = file_path
            self.status_label.setText(
                f"Audio file selected: {os.path.basename(file_path)}"
            )
            pygame.mixer.music.load(self.audio_file)  # 直接加载完整音频文件

            # 添加到最近文件列表
            self.add_recent_file(file_path, "audio")

            # 自动寻找匹配的字幕文件
            self.find_matching_subtitle()

            # 尝试恢复之前的进度
            self.restore_progress()

    def open_recent_srt(self, file_path):
        """打开最近使用的字幕文件"""
        # 重置播放状态
        self.reset_playback_state()

        self.srt_file = file_path
        self.status_label.setText(
            f"Subtitle file selected: {os.path.basename(file_path)}"
        )

        # 添加到最近文件列表
        self.add_recent_file(file_path, "srt")

        self.parse_srt()

        if self.audio_file:
            self.status_label.setText("Ready to start dictation, click 'Next' to begin")
            self.restore_progress()

    def parse_srt(self):
        if not self.srt_file:
            return

        try:
            self.segments = []
            with open(self.srt_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 使用正则表达式匹配字幕条目
            pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n([\s\S]*?)(?=\n\n\d+\n|$)"
            matches = re.findall(pattern, content)

            for match in matches:
                index = int(match[0])
                start_time = self.time_to_seconds(match[1])
                end_time = self.time_to_seconds(match[2])
                text = match[3].strip()

                self.segments.append(
                    {"index": index, "start": start_time, "end": end_time, "text": text}
                )

            self.progress_bar.setMaximum(len(self.segments))
            self.progress_label.setText(f"0/{len(self.segments)}")

            if self.audio_file:
                self.status_label.setText(
                    "Ready to start dictation, click 'Next' to begin"
                )

        except Exception as e:
            self.status_label.setText(f"Error parsing subtitle file: {e}")

    def time_to_seconds(self, time_str):
        # 将 "00:00:00,000" 格式的时间转换为秒
        hours, minutes, seconds = time_str.replace(",", ".").split(":")
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)

    def play_audio_segment(self, segment_index):
        if not self.audio_file or not self.segments:
            return

        if 0 <= segment_index < len(self.segments):
            # 停止当前播放和计时器
            pygame.mixer.music.stop()
            self.playback_timer.stop()

            segment = self.segments[segment_index]
            start_time = segment["start"]
            end_time = segment["end"]
            duration = (end_time - start_time) * 1000  # 毫秒

            # 设置播放位置并开始播放
            pygame.mixer.music.play(0, start_time)

            # 设置计时器在片段结束时停止播放
            self.playback_timer.start(int(duration))

            # 更新UI
            self.current_segment = segment_index
            self.progress_bar.setValue(segment_index + 1)
            self.progress_label.setText(f"{segment_index + 1}/{len(self.segments)}")
            self.content_label.setText(self.segments[segment_index]["text"])

            # 保存当前进度
            self.save_progress()

    def stop_playback(self):
        # 计时器触发时停止播放
        pygame.mixer.music.stop()
        self.playback_timer.stop()

    def play_next(self, source=None):
        if source == "hotkey":
            if not self.allow_hotkeys_flag:
                return
        if not self.segments or not self.audio_file:
            self.status_label.setText("Please select audio and subtitle files")
            return

        next_segment = 0 if self.current_segment == -1 else self.current_segment + 1

        if next_segment < len(self.segments):
            self.play_audio_segment(next_segment)
        else:
            self.status_label.setText("All segments have been played")

    def play_previous(self, source=None):
        if source == "hotkey":
            if not self.allow_hotkeys_flag:
                return

        if not self.segments or not self.audio_file:
            self.status_label.setText("Please select audio and subtitle files")
            return

        if self.current_segment > 0:
            self.play_audio_segment(self.current_segment - 1)
        else:
            self.status_label.setText("This is the first segment")

    def replay_current(self, source=None):
        if source == "hotkey":
            if not self.allow_hotkeys_flag:
                return

        if self.current_segment >= 0 and self.segments and self.audio_file:
            self.play_audio_segment(self.current_segment)
        else:
            self.status_label.setText("No segment is currently playing")

    def allow_hotkeys(self, allow):
        self.allow_hotkeys_flag = not self.allow_hotkeys_flag
        print("Hotkeys are now ", "enabled" if self.allow_hotkeys_flag else "disabled")

    def reset_playback_state(self):
        """重置播放状态"""
        # 停止当前播放和计时器
        pygame.mixer.music.stop()
        self.playback_timer.stop()

        # 重置状态变量
        self.current_segment = -1
        self.srt_file = None
        self.segments = []

        # 重置UI
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"0/{len(self.segments)}")
        self.content_label.setText("")

    def closeEvent(self, event):
        # 保存当前进度
        self.save_progress()

        # 停止播放和计时器
        pygame.mixer.music.stop()
        self.playback_timer.stop()
        pygame.mixer.quit()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DictationHelper()
    window.show()
    sys.exit(app.exec())
