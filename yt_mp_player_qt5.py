import sys
import re
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QListWidget, QLabel, QShortcut,
                             QProgressBar, QPlainTextEdit)
from datetime import datetime
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QProcess
from PyQt5.QtGui import QKeySequence
from youtubesearchpython import VideosSearch

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
        try:
            search = VideosSearch(self.query, limit=12)
            results = search.result()['result']
            self.results_ready.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.results_ready.emit([])


# --- Aplicación Principal ---
class BBBPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(800, 480)
        self.setWindowTitle('BBB Tuber')

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
        self.log("BBB Tuber iniciado")
        if os.path.exists(COOKIES_FILE):
            self.log("Cookies encontradas")
        else:
            self.log("Cookies no encontradas - ejecuta export_cookies.sh", "WARN")

    def init_ui(self):
        main_layout = QHBoxLayout()

        # === LEFT PANEL (Search & Results) ===
        left_panel = QVBoxLayout()

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar en YouTube...")
        self.search_input.setStyleSheet("font-size: 20px; padding: 5px;")
        self.search_input.returnPressed.connect(self.start_search)

        btn_search = QPushButton("Buscar")
        btn_search.setStyleSheet("font-size: 20px; padding: 10px;")
        btn_search.clicked.connect(self.start_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(btn_search)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("font-size: 18px;")
        self.list_widget.itemDoubleClicked.connect(self.play_video)

        self.status_label = QLabel("Listo")
        self.status_label.setStyleSheet("font-size: 16px; color: gray;")

        progress_layout = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #5cb85c;
            }
        """)
        self.progress_bar.setFormat("")

        self.time_label = QLabel("--:-- / --:--")
        self.time_label.setStyleSheet("font-size: 14px; color: #888; min-width: 100px;")
        self.time_label.setAlignment(Qt.AlignCenter)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.time_label)

        btn_stop = QPushButton("Detener")
        btn_stop.setStyleSheet("background-color: #d9534f; color: white; font-size: 20px; font-weight: bold;")
        btn_stop.clicked.connect(self.stop_music)

        # === LOG TERMINAL ===
        self.log_terminal = QPlainTextEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setMaximumHeight(90)
        self.log_terminal.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1a1a1a;
                color: #00ff00;
                font-family: monospace;
                font-size: 11px;
                border: 1px solid #333;
                border-radius: 3px;
            }
        """)
        self.log_terminal.setPlaceholderText("Terminal de errores...")

        left_panel.addLayout(search_layout)
        left_panel.addWidget(self.list_widget)
        left_panel.addWidget(self.status_label)
        left_panel.addLayout(progress_layout)
        left_panel.addWidget(btn_stop)
        left_panel.addWidget(self.log_terminal)

        # === RIGHT PANEL (Shortcuts & Queue) ===
        right_panel = QVBoxLayout()

        shortcuts_text = """
<b>ATAJOS DE TECLADO</b><br><br>
<b>Navegación:</b><br>
↑/↓, j/k - Navegar lista<br>
g - Ir al inicio<br>
G - Ir al final<br><br>
<b>Reproducción:</b><br>
Enter/Space - Reproducir<br>
e - Encolar selección<br>
s/Esc - Detener<br>
n - Siguiente en cola<br><br>
<b>Cola:</b><br>
c - Limpiar cola<br>
x - Quitar de cola<br><br>
<b>Otros:</b><br>
/ o Ctrl+F - Buscar<br>
Tab - Cambiar foco<br>
Ctrl+Q - Salir
"""
        shortcuts_label = QLabel(shortcuts_text)
        shortcuts_label.setStyleSheet("""
            font-size: 14px;
            background-color: #2d2d2d;
            color: #cccccc;
            padding: 15px;
            border-radius: 5px;
        """)
        shortcuts_label.setWordWrap(True)
        shortcuts_label.setAlignment(Qt.AlignTop)

        queue_title = QLabel("<b>COLA DE REPRODUCCIÓN</b>")
        queue_title.setStyleSheet("font-size: 16px; color: #5cb85c; margin-top: 10px;")

        self.queue_widget = QListWidget()
        self.queue_widget.setStyleSheet("font-size: 14px;")
        self.queue_widget.setMaximumHeight(200)

        right_panel.addWidget(shortcuts_label)
        right_panel.addWidget(queue_title)
        right_panel.addWidget(self.queue_widget)
        right_panel.addStretch()

        left_container = QWidget()
        left_container.setLayout(left_panel)

        right_container = QWidget()
        right_container.setLayout(right_panel)
        right_container.setFixedWidth(250)

        main_layout.addWidget(left_container, stretch=1)
        main_layout.addWidget(right_container)

        self.setLayout(main_layout)
        self.list_widget.setFocus()

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.stop_music)
        QShortcut(QKeySequence('/'), self, self.focus_search)
        QShortcut(QKeySequence('Ctrl+F'), self, self.focus_search)
        QShortcut(QKeySequence('Ctrl+Q'), self, self.close)
        QShortcut(QKeySequence(Qt.Key_Space), self, self.play_selected)
        self.list_widget.itemActivated.connect(self.play_video)
        QShortcut(QKeySequence('E'), self, self.enqueue_selected)
        QShortcut(QKeySequence('N'), self, self.play_next)
        QShortcut(QKeySequence('C'), self, self.clear_queue)
        QShortcut(QKeySequence('X'), self, self.remove_from_queue)

    def log(self, message, level="INFO"):
        """Add a message to the log terminal. Levels: INFO, WARN, ERROR"""
        timestamp = datetime.now().strftime("%H:%M:%S")
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

        if key == Qt.Key_J and not self.search_input.hasFocus():
            current_row = self.list_widget.currentRow()
            if current_row < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(current_row + 1)
            return
        elif key == Qt.Key_K and not self.search_input.hasFocus():
            current_row = self.list_widget.currentRow()
            if current_row > 0:
                self.list_widget.setCurrentRow(current_row - 1)
            return

        if key == Qt.Key_G and not self.search_input.hasFocus():
            if event.modifiers() & Qt.ShiftModifier:
                self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            else:
                self.list_widget.setCurrentRow(0)
            return

        if key == Qt.Key_S and not self.search_input.hasFocus():
            self.stop_music()
            return

        super().keyPressEvent(event)

    def start_search(self):
        query = self.search_input.text()
        if not query: return

        self.status_label.setText("Buscando...")
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
            title = vid['title']
            duration = vid.get('duration', 'N/A')
            self.list_widget.addItem(f"{title} - [{duration}]")

    def play_video(self, item):
        index = self.list_widget.row(item)
        video_info = self.video_data_list[index]
        self.play_video_from_info(video_info)

    def play_video_from_info(self, video_info):
        """Play a video from its info dict."""
        link = video_info['link']

        self.stop_music()

        # Set loading state
        self.current_title = video_info['title']
        self.is_loading = True
        self.playback_started = False
        self.status_label.setText(f"⏳ Cargando: {self.current_title[:50]}...")
        self.status_label.setStyleSheet("font-size: 16px; color: orange;")
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
                self.status_label.setStyleSheet("font-size: 16px; color: #5cb85c;")
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
        self.status_label.setStyleSheet("font-size: 16px; color: gray;")
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
        self.status_label.setText("Detenido")
        self.status_label.setStyleSheet("font-size: 16px; color: gray;")
        if was_playing:
            self.log("Detenido por usuario")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = BBBPlayer()
    player.showFullScreen()
    sys.exit(app.exec_())
