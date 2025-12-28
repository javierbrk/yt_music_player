import sys
import re
import os
import json
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QListWidget, QLabel, QShortcut,
                             QProgressBar, QPlainTextEdit)
from datetime import datetime
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QProcess
from PyQt5.QtGui import QKeySequence

# Path to cookies file (NOT tracked by git - stored in user's home)
COOKIES_FILE = os.path.expanduser('~/.config/ytplayer/cookies.txt')


# --- Hilo de Búsqueda (Worker) ---
class SearchThread(QThread):
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        # Limpiar query
        query = self.query.strip()
        if not query:
            self.results_ready.emit([])
            return

        # Usar yt-dlp para búsqueda (más confiable que youtube-search-python)
        try:
            cmd = ['yt-dlp', '--flat-playlist', '--dump-json', f'ytsearch12:{query}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout:
                valid_results = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            item = json.loads(line)
                            title = item.get('title')
                            video_id = item.get('id') or item.get('url', '').split('=')[-1]
                            if title and video_id:
                                valid_results.append({
                                    'title': title,
                                    'link': f'https://www.youtube.com/watch?v={video_id}',
                                    'duration': item.get('duration_string') or 'N/A'
                                })
                        except json.JSONDecodeError:
                            continue
                self.results_ready.emit(valid_results)
                return

            self.error_occurred.emit("Sin resultados")
            self.results_ready.emit([])
        except subprocess.TimeoutExpired:
            self.error_occurred.emit("Timeout en búsqueda")
            self.results_ready.emit([])
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.results_ready.emit([])


# --- Aplicación Principal ---
class BBBPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(800, 480)
        self.setWindowTitle('🎵 Música de Emilia y Frida 🎵')

        self.current_process = None
        self.video_data_list = []
        self.queue = []
        self.current_title = ""
        self.is_loading = False
        self.playback_started = False
        self.log_lines = []
        self.max_log_lines = 5

        self.init_ui()
        self.setup_shortcuts()

        # Initial log
        self.log("🎉 ¡Hola Emilia y Frida!")
        if os.path.exists(COOKIES_FILE):
            self.log("✅ Todo listo")
        else:
            self.log("⚠️ Falta configurar", "WARN")

    def init_ui(self):
        # Anthroposophic/Waldorf color scheme - warm, natural, organic
        self.setStyleSheet("""
            QWidget {
                background-color: #fdf6e3;
                color: #5c4a3d;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
            }
            QLineEdit {
                background-color: #fff8dc;
                border: 4px solid #e8a87c;
                border-radius: 25px;
                padding: 12px 20px;
                font-size: 22px;
                color: #5c4a3d;
            }
            QLineEdit:focus {
                border-color: #c38d6b;
                background-color: #fffef5;
            }
            QListWidget {
                background-color: #fff8dc;
                border: 4px solid #d4a574;
                border-radius: 25px;
                padding: 12px;
                font-size: 18px;
            }
            QListWidget::item {
                padding: 14px;
                border-radius: 18px;
                margin: 4px;
                background-color: #fef9e7;
            }
            QListWidget::item:selected {
                background-color: #e8a87c;
                color: #3d2914;
            }
            QListWidget::item:hover {
                background-color: #f5deb3;
            }
            QPushButton {
                border-radius: 25px;
                padding: 15px 30px;
                font-size: 20px;
                font-weight: bold;
                border: none;
            }
            QProgressBar {
                border: 4px solid #d4a574;
                border-radius: 15px;
                text-align: center;
                height: 28px;
                background-color: #fff8dc;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e8a87c, stop:0.5 #c9a66b, stop:1 #85c88a);
                border-radius: 11px;
            }
        """)

        main_layout = QHBoxLayout()

        # === LEFT PANEL (Search & Results) ===
        left_panel = QVBoxLayout()

        # Welcome header with kids names
        welcome_label = QLabel("🌸 Música para Emilia y Frida 🌻")
        welcome_label.setStyleSheet("""
            font-size: 26px;
            font-weight: bold;
            color: #5c4a3d;
            padding: 15px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f5deb3, stop:0.3 #e8a87c, stop:0.7 #85c88a, stop:1 #a7c5eb);
            border-radius: 30px;
            margin-bottom: 10px;
        """)
        welcome_label.setAlignment(Qt.AlignCenter)
        left_panel.addWidget(welcome_label)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 ¿Qué quieres escuchar?")
        self.search_input.returnPressed.connect(self.start_search)

        btn_search = QPushButton("🔎 Buscar")
        btn_search.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #85c88a, stop:1 #6ba36e);
            color: #2d4a2e;
            border: none;
        """)
        btn_search.clicked.connect(self.start_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(btn_search)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.play_video)

        self.status_label = QLabel("🎶 Listo para escuchar música!")
        self.status_label.setStyleSheet("font-size: 18px; color: #6ba36e; padding: 8px;")

        progress_layout = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")

        self.time_label = QLabel("--:-- / --:--")
        self.time_label.setStyleSheet("font-size: 16px; color: #c38d6b; min-width: 120px; font-weight: bold;")
        self.time_label.setAlignment(Qt.AlignCenter)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.time_label)

        btn_stop = QPushButton("⏹️ Parar")
        btn_stop.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #e8a87c, stop:1 #c9886a);
            color: #4a3728;
            border: none;
            min-height: 55px;
        """)
        btn_stop.clicked.connect(self.stop_music)

        # === LOG TERMINAL ===
        self.log_terminal = QPlainTextEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setMaximumHeight(65)
        self.log_terminal.setStyleSheet("""
            QPlainTextEdit {
                background-color: #f5f0e1;
                color: #6b5344;
                font-family: monospace;
                font-size: 12px;
                border: 3px solid #d4a574;
                border-radius: 15px;
                padding: 8px;
            }
        """)
        self.log_terminal.setPlaceholderText("...")

        left_panel.addLayout(search_layout)
        left_panel.addWidget(self.list_widget)
        left_panel.addWidget(self.status_label)
        left_panel.addLayout(progress_layout)
        left_panel.addWidget(btn_stop)
        left_panel.addWidget(self.log_terminal)

        # === RIGHT PANEL (Help & Queue) ===
        right_panel = QVBoxLayout()

        # Kid-friendly help panel with Waldorf colors - VISIBLE SHORTCUTS
        help_text = """
<div style='text-align: center;'>
<span style='font-size: 24px; font-weight: bold;'>🌈 ATAJOS 🌈</span><br><br>
<table style='font-size: 18px; margin: auto;'>
<tr><td style='padding: 8px;'><b style='font-size: 24px; color: #6ba36e;'>B</b></td><td>Buscar 🔍</td></tr>
<tr><td style='padding: 8px;'><b style='font-size: 24px; color: #6ba36e;'>R</b></td><td>Reproducir ▶️</td></tr>
<tr><td style='padding: 8px;'><b style='font-size: 24px; color: #6ba36e;'>E</b></td><td>Encolar 📋</td></tr>
<tr><td style='padding: 8px;'><b style='font-size: 24px; color: #e8a87c;'>S</b></td><td>Siguiente ⏭️</td></tr>
<tr><td style='padding: 8px;'><b style='font-size: 24px; color: #c9886a;'>P</b></td><td>Parar ⏹️</td></tr>
<tr><td style='padding: 8px;'><b style='font-size: 24px; color: #a7c5eb;'>L</b></td><td>Limpiar 🗑️</td></tr>
<tr><td style='padding: 8px;'><b style='font-size: 24px; color: #a7c5eb;'>Q</b></td><td>Quitar ❌</td></tr>
<tr><td style='padding: 8px;'><b style='font-size: 24px; color: #c9886a;'>A</b></td><td>Apagar 🚪</td></tr>
</table>
</div>
"""
        help_label = QLabel(help_text)
        help_label.setStyleSheet("""
            font-size: 18px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #fff8dc, stop:1 #f5deb3);
            color: #5c4a3d;
            padding: 15px;
            border-radius: 30px;
            border: 4px solid #d4a574;
        """)
        help_label.setWordWrap(True)
        help_label.setAlignment(Qt.AlignTop)

        queue_title = QLabel("🎶 Siguiente")
        queue_title.setStyleSheet("""
            font-size: 18px;
            color: #6ba36e;
            margin-top: 15px;
            font-weight: bold;
        """)

        self.queue_widget = QListWidget()
        self.queue_widget.setStyleSheet("font-size: 14px;")
        self.queue_widget.setMaximumHeight(200)

        right_panel.addWidget(help_label)
        right_panel.addWidget(queue_title)
        right_panel.addWidget(self.queue_widget)
        right_panel.addStretch()

        left_container = QWidget()
        left_container.setLayout(left_panel)

        right_container = QWidget()
        right_container.setLayout(right_panel)
        right_container.setFixedWidth(280)

        main_layout.addWidget(left_container, stretch=1)
        main_layout.addWidget(right_container)

        self.setLayout(main_layout)
        self.list_widget.setFocus()

    def setup_shortcuts(self):
        # Atajos con primera letra en español
        QShortcut(QKeySequence('B'), self, self.focus_search)      # Buscar
        QShortcut(QKeySequence('R'), self, self.play_selected)     # Reproducir
        QShortcut(QKeySequence('E'), self, self.enqueue_selected)  # Encolar
        QShortcut(QKeySequence('S'), self, self.play_next)         # Siguiente
        QShortcut(QKeySequence('P'), self, self.stop_music)        # Parar
        QShortcut(QKeySequence('L'), self, self.clear_queue)       # Limpiar cola
        QShortcut(QKeySequence('Q'), self, self.remove_from_queue) # Quitar de cola
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.stop_music)
        QShortcut(QKeySequence(Qt.Key_Space), self, self.play_selected)
        QShortcut(QKeySequence('A'), self, self.close)              # Apagar/Salir
        self.list_widget.itemActivated.connect(self.play_video)

    def log(self, message, level="INFO"):
        """Add a message to the log terminal. Levels: INFO, WARN, ERROR"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Console output (stdout)
        level_tag = f"[{level}]" if level != "INFO" else ""
        console_line = f"[{timestamp}] {level_tag} {message}".strip()
        print(console_line, flush=True)

        # GUI output
        color_prefix = ""
        if level == "ERROR":
            color_prefix = "❌ "
        elif level == "WARN":
            color_prefix = "⚠️ "

        line = f"[{timestamp}] {color_prefix}{message}"
        self.log_lines.append(line)

        # Keep only the last N lines
        if len(self.log_lines) > self.max_log_lines:
            self.log_lines = self.log_lines[-self.max_log_lines:]

        self.log_terminal.setPlainText("\n".join(self.log_lines))
        # Scroll to bottom
        self.log_terminal.verticalScrollBar().setValue(
            self.log_terminal.verticalScrollBar().maximum()
        )

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def focus_list(self):
        self.list_widget.setFocus()
        if self.list_widget.count() > 0 and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)

    def play_selected(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            self.play_video(current_item)

    # === Queue Methods ===
    def enqueue_selected(self):
        if self.search_input.hasFocus():
            return
        current_item = self.list_widget.currentItem()
        if current_item:
            index = self.list_widget.row(current_item)
            video_info = self.video_data_list[index]
            self.queue.append(video_info)
            self.update_queue_display()
            self.status_label.setText(f"Encolado: {video_info['title'][:40]}...")

    def update_queue_display(self):
        self.queue_widget.clear()
        for i, vid in enumerate(self.queue):
            title = vid['title'][:35] + "..." if len(vid['title']) > 35 else vid['title']
            self.queue_widget.addItem(f"{i+1}. {title}")

    def play_next(self):
        if self.search_input.hasFocus():
            return
        if self.queue:
            video_info = self.queue.pop(0)
            self.update_queue_display()
            self.play_video_from_info(video_info)
        else:
            self.status_label.setText("Cola vacía")

    def clear_queue(self):
        if self.search_input.hasFocus():
            return
        self.queue.clear()
        self.update_queue_display()
        self.status_label.setText("Cola limpiada")

    def remove_from_queue(self):
        if self.search_input.hasFocus():
            return
        current_row = self.queue_widget.currentRow()
        if current_row >= 0 and current_row < len(self.queue):
            removed = self.queue.pop(current_row)
            self.update_queue_display()
            self.status_label.setText(f"Quitado de cola: {removed['title'][:30]}...")

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key_Escape:
            if self.search_input.hasFocus():
                self.focus_list()
                return

        if key == Qt.Key_Tab:
            if self.search_input.hasFocus():
                self.focus_list()
            else:
                self.focus_search()
            return

        # Navegación: I = Inicio, F = Final
        if key == Qt.Key_I and not self.search_input.hasFocus():
            self.list_widget.setCurrentRow(0)
            return

        if key == Qt.Key_F and not self.search_input.hasFocus():
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            return

        super().keyPressEvent(event)

    def start_search(self):
        query = self.search_input.text()
        if not query: return

        self.status_label.setText("🔍 Buscando...")
        self.list_widget.clear()
        self.log(f"Buscando: {query}")

        self.search_thread = SearchThread(query)
        self.search_thread.results_ready.connect(self.handle_results)
        self.search_thread.error_occurred.connect(lambda e: self.log(f"Error búsqueda: {e}", "ERROR"))
        self.search_thread.start()

    def handle_results(self, results):
        self.video_data_list = results
        self.status_label.setText(f"Encontrados {len(results)} resultados.")

        for vid in results:
            title = vid.get('title') or 'Sin título'
            duration = vid.get('duration') or 'N/A'
            self.list_widget.addItem(f"{title} - [{duration}]")

    def play_video(self, item):
        index = self.list_widget.row(item)
        video_info = self.video_data_list[index]
        self.play_video_from_info(video_info)

    def play_video_from_info(self, video_info):
        """Play a video from its info dict."""
        link = video_info.get('link')
        if not link:
            self.log("Video sin enlace válido", "ERROR")
            return

        self.stop_music()

        # Set loading state
        self.current_title = video_info.get('title') or 'Sin título'
        self.is_loading = True
        self.playback_started = False
        self.status_label.setText(f"⏳ Cargando: {self.current_title[:50]}...")
        self.status_label.setStyleSheet("font-size: 18px; color: #c9886a;")
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.time_label.setText("Cargando...")

        self.log(f"Reproduciendo: {self.current_title[:40]}...")

        # Build mpv arguments
        mpv_args = [
            '--no-video',
            '--term-osd-bar=no',
            '--msg-level=all=status',
        ]

        # Add cookies if file exists (for YouTube authentication)
        if os.path.exists(COOKIES_FILE):
            mpv_args.append(f'--ytdl-raw-options=cookies={COOKIES_FILE}')
            self.log("Usando cookies de autenticación")
        else:
            self.log("Sin cookies (puede fallar)", "WARN")

        mpv_args.append(link)

        # Start mpv
        self.current_process = QProcess(self)
        self.current_process.finished.connect(self.on_playback_finished)
        self.current_process.readyReadStandardError.connect(self.on_mpv_output)
        self.current_process.setProcessChannelMode(QProcess.MergedChannels)
        self.current_process.readyReadStandardOutput.connect(self.on_mpv_output)
        self.current_process.start('mpv', mpv_args)

    def on_mpv_output(self):
        if not self.current_process:
            return

        data = self.current_process.readAllStandardOutput().data().decode('utf-8', errors='ignore')

        # Detect errors from mpv/yt-dlp
        if 'ERROR' in data or 'error' in data.lower():
            # Extract meaningful error message
            for line in data.split('\n'):
                line = line.strip()
                if line and ('error' in line.lower() or 'failed' in line.lower() or 'bot' in line.lower()):
                    self.log(line[:60], "ERROR")

        time_match = re.search(r'A[V]?:\s*(\d+:\d+:\d+|\d+:\d+)\s*/\s*(\d+:\d+:\d+|\d+:\d+)', data)

        if time_match:
            if self.is_loading:
                self.is_loading = False
                self.playback_started = True
                self.status_label.setText(f"▶ {self.current_title[:50]}")
                self.status_label.setStyleSheet("font-size: 18px; color: #6ba36e;")
                self.progress_bar.setRange(0, 100)

            current_time = time_match.group(1)
            total_time = time_match.group(2)

            self.time_label.setText(f"{current_time} / {total_time}")

            current_secs = self.time_to_seconds(current_time)
            total_secs = self.time_to_seconds(total_time)

            if total_secs > 0:
                percent = int((current_secs / total_secs) * 100)
                self.progress_bar.setValue(percent)

    def time_to_seconds(self, time_str):
        parts = time_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0

    def on_playback_finished(self):
        self.current_process = None
        self.is_loading = False
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 100)
        self.time_label.setText("--:-- / --:--")
        self.status_label.setStyleSheet("font-size: 18px; color: #8b7355;")
        if self.queue:
            self.log(f"Siguiente en cola ({len(self.queue)} restantes)")
            self.play_next()
        else:
            self.log("Reproducción finalizada")
            self.status_label.setText("Listo")

    def stop_music(self):
        was_playing = self.current_process is not None
        if self.current_process:
            self.current_process.finished.disconnect()
            self.current_process.terminate()
            self.current_process.waitForFinished(1000)
            self.current_process = None
        self.is_loading = False
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 100)
        self.time_label.setText("--:-- / --:--")
        self.status_label.setText("⏸️ Detenido")
        self.status_label.setStyleSheet("font-size: 18px; color: #8b7355;")
        if was_playing:
            self.log("Detenido por usuario")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = BBBPlayer()
    player.showFullScreen()
    sys.exit(app.exec_())
