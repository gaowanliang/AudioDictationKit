import os
import sys
import keyboard
import json
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFileDialog,
    QProgressBar,
    QShortcut,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
import pygame
import re


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

        # 状态保存相关
        self.progress_data = {}
        self.progress_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "dictation_progress.json"
        )
        self.load_progress()

        # 设置UI
        self.init_ui()

        # 设置全局热键
        keyboard.add_hotkey("shift+space", self.replay_current)
        keyboard.add_hotkey("enter", self.play_next)
        keyboard.add_hotkey("ctrl+left", self.play_previous)

    def init_ui(self):
        self.setWindowTitle("Dictation Helper")
        self.setGeometry(100, 100, 600, 400)

        # 创建主布局
        main_layout = QVBoxLayout()

        # 文件选择区域
        file_layout = QHBoxLayout()

        self.audio_btn = QPushButton("Select Audio File", self)
        self.audio_btn.clicked.connect(self.open_audio_file)
        file_layout.addWidget(self.audio_btn)

        self.srt_btn = QPushButton("Select Subtitle File", self)
        self.srt_btn.clicked.connect(self.open_srt_file)
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

        self.prev_btn = QPushButton("Previous (Ctrl+←)", self)
        self.prev_btn.clicked.connect(self.play_previous)
        control_layout.addWidget(self.prev_btn)

        self.replay_btn = QPushButton("Replay (Shift+Space)", self)
        self.replay_btn.clicked.connect(self.replay_current)
        control_layout.addWidget(self.replay_btn)

        self.next_btn = QPushButton("Next (Enter)", self)
        self.next_btn.clicked.connect(self.play_next)
        control_layout.addWidget(self.next_btn)

        main_layout.addLayout(control_layout)

        # 热键提示
        hotkey_hint = QLabel(
            "Hotkeys: Shift+Space (Replay), Enter (Next), Ctrl+← (Previous)", self
        )
        hotkey_hint.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(hotkey_hint)

        # 设置主窗口部件
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 设置窗口快捷键
        QShortcut(
            QKeySequence(Qt.Key_Space | Qt.ShiftModifier), self, self.replay_current
        )
        QShortcut(QKeySequence(Qt.Key_Return), self, self.play_next)
        QShortcut(
            QKeySequence(Qt.Key_Left | Qt.ControlModifier), self, self.play_previous
        )

    def load_progress(self):
        """从JSON文件加载进度数据"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    self.progress_data = json.load(f)
        except Exception as e:
            print(f"Error loading progress data: {e}")
            self.progress_data = {}

    def save_progress(self):
        """将当前进度保存到JSON文件"""
        try:
            if self.audio_file:
                file_key = self.get_file_key()
                if file_key:
                    self.progress_data[file_key] = {
                        "audio_file": self.audio_file,
                        "srt_file": self.srt_file,
                        "current_segment": self.current_segment,
                    }

                    with open(self.progress_file, "w", encoding="utf-8") as f:
                        json.dump(self.progress_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving progress data: {e}")

    def get_file_key(self):
        """根据音频文件名生成唯一键"""
        if self.audio_file:
            return os.path.basename(self.audio_file)
        return None

    def restore_progress(self):
        """恢复之前保存的进度"""
        file_key = self.get_file_key()
        if file_key and file_key in self.progress_data:
            saved_data = self.progress_data[file_key]

            # 检查SRT文件是否匹配或需要加载
            if self.srt_file != saved_data["srt_file"] and os.path.exists(
                saved_data["srt_file"]
            ):
                self.srt_file = saved_data["srt_file"]
                self.parse_srt()

            # 恢复到之前的段落位置
            saved_segment = saved_data["current_segment"]
            if 0 <= saved_segment < len(self.segments):
                # 稍后播放，先更新UI
                self.current_segment = (
                    saved_segment - 1
                )  # 设为前一个，这样play_next会播放正确的段落
                self.status_label.setText(
                    f"Progress restored - segment {saved_segment + 1}/{len(self.segments)}"
                )
                QTimer.singleShot(500, self.play_next)  # 延迟500ms后播放下一段

    def open_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio Files (*.mp3 *.wav *.ogg)"
        )
        if file_path:
            self.audio_file = file_path
            self.status_label.setText(
                f"Audio file selected: {os.path.basename(file_path)}"
            )
            pygame.mixer.music.load(self.audio_file)  # 直接加载完整音频文件

            if self.srt_file:
                self.status_label.setText(
                    "Ready to start dictation, click 'Next' to begin"
                )

            # 尝试恢复之前的进度
            self.restore_progress()

    def open_srt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Subtitle File", "", "Subtitle Files (*.srt)"
        )
        if file_path:
            self.srt_file = file_path
            self.status_label.setText(
                f"Subtitle file selected: {os.path.basename(file_path)}"
            )
            self.parse_srt()

            # 如果音频文件已加载，尝试恢复进度
            if self.audio_file:
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

    def play_next(self):
        if not self.segments or not self.audio_file:
            self.status_label.setText("Please select audio and subtitle files")
            return

        next_segment = 0 if self.current_segment == -1 else self.current_segment + 1

        if next_segment < len(self.segments):
            self.play_audio_segment(next_segment)
        else:
            self.status_label.setText("All segments have been played")

    def play_previous(self):
        if not self.segments or not self.audio_file:
            self.status_label.setText("Please select audio and subtitle files")
            return

        if self.current_segment > 0:
            self.play_audio_segment(self.current_segment - 1)
        else:
            self.status_label.setText("This is the first segment")

    def replay_current(self):
        if self.current_segment >= 0 and self.segments and self.audio_file:
            self.play_audio_segment(self.current_segment)
        else:
            self.status_label.setText("No segment is currently playing")

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
    sys.exit(app.exec_())
