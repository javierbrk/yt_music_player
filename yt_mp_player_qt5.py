import sys
import re
import os
import json
import subprocess
import time
import socket
from threading import Lock
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QListWidget, QLabel, QShortcut,
                             QProgressBar, QPlainTextEdit)
from datetime import datetime
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QProcess
from PyQt5.QtGui import QKeySequence

# Path to cookies file (NOT tracked by git - stored in user's home)
COOKIES_FILE = os.path.expanduser('~/.config/ytplayer/cookies.txt')

# Path to yt-dlp (evita timeout de 60s buscando en config directories)
YTDLP_PATH = os.path.expanduser('~/.local/bin/yt-dlp')


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


# --- Slot de Reproducción (Doble-Buffer) ---
class PlayerSlot:
    """Representa un slot de reproducción con su propio socket IPC."""

    def __init__(self, slot_id):
        self.slot_id = slot_id
        self.socket_path = f'/tmp/mpv_ytplayer_{slot_id}'
        self.process = None       # QProcess de mpv
        self.video_info = None    # dict con title, link, etc
        self.video_link = None    # link del video (para comparar)
        self.state = 'free'       # free|prefetching|buffering|ready|playing

    def cleanup(self):
        """Limpia el slot para reutilización."""
        if self.process:
            try:
                self.process.terminate()
                self.process.waitForFinished(500)
            except:
                pass
        self.process = None
        self.video_info = None
        self.video_link = None
        self.state = 'free'

    def __repr__(self):
        video = self.video_info.get('title', '')[:20] if self.video_info else 'None'
        return f"Slot({self.slot_id}, {self.state}, '{video}')"


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

        # Pre-carga paralela (yt-dlp)
        self.url_cache = {}           # {video_link: direct_audio_url}
        self.prefetch_process = None  # QProcess para pre-carga yt-dlp
        self.prefetch_slot = None     # Slot siendo pre-cargado

        # Sistema de doble-buffer para pre-buffering
        self.slots = [PlayerSlot(0), PlayerSlot(1)]
        self.slot_lock = Lock()       # Protege acceso concurrente a slots
        self.current_slot = None      # Slot actualmente reproduciendo
        self.waiting_for_prefetch = None  # Video info esperando prefetch

        # Resolución URL asíncrona para reproducción
        self.resolve_process = None   # QProcess para resolver URL
        self.resolve_video_info = None

        # Debug timing
        self.load_start_time = None

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

        # Kid-friendly help panel with Waldorf colors - COMPACT SHORTCUTS
        help_text = """
<div style='text-align: center;'>
<b>🌈 ATAJOS 🌈</b><br>
<table style='font-size: 14px;'>
<tr><td><b style='color: #6ba36e;'>B</b> 🔍Buscar</td><td><b style='color: #6ba36e;'>R</b> ▶️Play</td></tr>
<tr><td><b style='color: #6ba36e;'>E</b> 📋Encolar</td><td><b style='color: #e8a87c;'>S</b> ⏭️Sig</td></tr>
<tr><td><b style='color: #c9886a;'>P</b> ⏹️Parar</td><td><b style='color: #a7c5eb;'>L</b> 🗑️Limp</td></tr>
<tr><td><b style='color: #a7c5eb;'>Q</b> ❌Quitar</td><td><b style='color: #c9886a;'>A</b> 🚪Salir</td></tr>
</table>
</div>
"""
        help_label = QLabel(help_text)
        help_label.setStyleSheet("""
            font-size: 13px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #fff8dc, stop:1 #f5deb3);
            color: #5c4a3d;
            padding: 8px;
            border-radius: 15px;
            border: 3px solid #d4a574;
        """)
        help_label.setWordWrap(True)
        help_label.setAlignment(Qt.AlignTop)
        help_label.setMaximumHeight(160)

        queue_title = QLabel("🎶 Siguiente")
        queue_title.setStyleSheet("""
            font-size: 18px;
            color: #6ba36e;
            margin-top: 15px;
            font-weight: bold;
        """)

        self.queue_widget = QListWidget()
        self.queue_widget.setStyleSheet("font-size: 14px;")

        right_panel.addWidget(help_label)
        right_panel.addWidget(queue_title)
        right_panel.addWidget(self.queue_widget, stretch=1)

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

    def _flow(self, msg):
        """Debug flow message with timestamp."""
        if self.load_start_time:
            elapsed = time.time() - self.load_start_time
            print(f"[FLOW T+{elapsed:6.2f}s] {msg}", flush=True)
        else:
            print(f"[FLOW T+  -.--s] {msg}", flush=True)

    # === Slot Management (Double-Buffer) ===
    def get_free_slot(self):
        """Retorna un slot libre o None si ambos ocupados."""
        with self.slot_lock:
            for slot in self.slots:
                if slot.state == 'free':
                    return slot
        return None

    def get_ready_slot(self, video_link):
        """Retorna slot ready o buffering que coincida con el video, o None."""
        with self.slot_lock:
            for slot in self.slots:
                if slot.state in ('ready', 'buffering') and slot.video_link == video_link:
                    return slot
        return None

    def get_prefetching_slot(self, video_link):
        """Retorna slot prefetching que coincida con el video, o None."""
        with self.slot_lock:
            for slot in self.slots:
                if slot.state == 'prefetching' and slot.video_link == video_link:
                    return slot
        return None

    def _log_slots(self):
        """Log del estado de los slots."""
        for slot in self.slots:
            self._flow(f"  Slot {slot.slot_id}: {slot.state:12} {slot.video_link if slot.video_link else 'None'}")

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
        # NO limpiar slots aquí - play_video_from_info() usará los que correspondan
        # y stop_music() limpiará los que no sirvan
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
        self.url_cache.clear()  # Limpiar cache de URLs pre-cargadas

        # Terminar proceso de prefetch
        if self.prefetch_process:
            self.prefetch_process.terminate()
            self.prefetch_process = None
        self.prefetch_slot = None

        # Limpiar todos los slots
        with self.slot_lock:
            for slot in self.slots:
                if slot != self.current_slot:  # No tocar el que está reproduciendo
                    slot.cleanup()

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

    # === Pre-carga Paralela (con Doble-Buffer) ===
    def prefetch_next(self):
        """Pre-cargar la URL del siguiente video en la cola usando un slot libre."""
        self._flow(f"prefetch_next() - cola tiene {len(self.queue)} items")
        self._log_slots()

        if not self.queue:
            self._flow("  → Sin cola, saliendo")
            return
        if self.prefetch_process:
            self._flow("  → Prefetch ya en curso, saliendo")
            return

        next_video = self.queue[0]
        link = next_video.get('link')

        if not link:
            self._flow("  → Video sin link, saliendo")
            return

        # Buscar slot libre
        slot = self.get_free_slot()
        if not slot:
            self._flow("  → No hay slot libre, saliendo")
            return

        # Verificar si ya hay un slot ready para este video
        ready_slot = self.get_ready_slot(link)
        if ready_slot:
            self._flow(f"  → Ya hay slot ready para este video (slot {ready_slot.slot_id})")
            return

        # Marcar slot como prefetching
        with self.slot_lock:
            slot.state = 'prefetching'
            slot.video_info = next_video
            slot.video_link = link

        self.prefetch_slot = slot
        self.prefetch_process = QProcess(self)
        self.prefetch_process.finished.connect(self.on_prefetch_finished)

        cmd_args = ['-f', 'bestaudio[protocol!=m3u8_native]/bestaudio/best', '-g', '--no-warnings', '--socket-timeout', '10', '--retries', '1', '--fragment-retries', '1']
        if os.path.exists(COOKIES_FILE):
            cmd_args.extend(['--cookies', COOKIES_FILE])
        cmd_args.append(link)

        self._flow(f"  → Slot {slot.slot_id} prefetching: {next_video.get('title', '')[:30]}...")
        self._flow(f"  → Slot {slot.slot_id} video_link: {link}")
        self.prefetch_process.start(YTDLP_PATH, cmd_args)

    def on_prefetch_finished(self):
        """Callback cuando termina la pre-carga yt-dlp."""
        self._flow("on_prefetch_finished()")

        slot = self.prefetch_slot
        if not slot:
            self._flow("  → No hay prefetch_slot, saliendo")
            self.prefetch_process = None
            return

        waiting_video = self.waiting_for_prefetch
        self.waiting_for_prefetch = None

        if self.prefetch_process:
            output = self.prefetch_process.readAllStandardOutput().data().decode('utf-8').strip()
            if output and output.startswith('http'):
                self.url_cache[slot.video_link] = output
                self._flow(f"  → URL obtenida para slot {slot.slot_id}")

                # Si estábamos esperando este prefetch, reproducir inmediatamente
                if waiting_video and waiting_video.get('link') == slot.video_link:
                    self._flow(f"  → Estábamos esperando este video, reproduciendo ahora")
                    with self.slot_lock:
                        slot.state = 'free'
                        slot.video_info = None
                        slot.video_link = None
                    self.prefetch_process = None
                    self.prefetch_slot = None
                    # Reproducir usando el cache que acabamos de llenar
                    self.play_video_from_info(waiting_video)
                    return

                # Validar que el video sigue siendo el primero en la cola
                if self.queue and self.queue[0].get('link') == slot.video_link:
                    self._flow(f"  → Video sigue en cola, iniciando mpv pausado en slot {slot.slot_id}")
                    self.start_paused_mpv(slot, output)
                else:
                    self._flow("  → Video ya no está en cola, liberando slot")
                    with self.slot_lock:
                        slot.state = 'free'
                        slot.video_info = None
                        slot.video_link = None
            else:
                stderr = self.prefetch_process.readAllStandardError().data().decode('utf-8').strip()
                self._flow(f"  → Prefetch falló: {stderr[:60]}")
                with self.slot_lock:
                    slot.state = 'free'
                    slot.video_info = None
                    slot.video_link = None

                # Si estábamos esperando, intentar con play_next normal
                if waiting_video:
                    self._flow("  → Prefetch falló pero estábamos esperando, usando fallback")
                    self.prefetch_process = None
                    self.prefetch_slot = None
                    self.play_video_from_info(waiting_video)
                    return

        self.prefetch_process = None
        self.prefetch_slot = None

    def start_paused_mpv(self, slot, url):
        """Inicia mpv pausado en un slot específico."""
        self._flow(f"start_paused_mpv() - slot {slot.slot_id}")

        with self.slot_lock:
            slot.state = 'buffering'

        mpv_args = [
            '--pause',
            '--no-video',
            '--term-osd-bar=no',
            '--msg-level=all=status',
            f'--script-opts=ytdl_hook-ytdl_path={YTDLP_PATH}',
            f'--input-ipc-server={slot.socket_path}',
            url
        ]

        slot.process = QProcess(self)
        slot.process.setProcessChannelMode(QProcess.MergedChannels)
        slot.process.started.connect(lambda: self._on_slot_buffering_started(slot))
        slot.process.start('mpv', mpv_args)
        self._flow(f"  → mpv iniciado en slot {slot.slot_id} (socket: {slot.socket_path})")

    def _on_slot_buffering_started(self, slot):
        """Callback cuando mpv empieza a hacer buffering."""
        with self.slot_lock:
            if slot.state == 'buffering':
                slot.state = 'ready'
        self._flow(f"  → Slot {slot.slot_id} ahora READY")
        self.log("⏸️ Siguiente listo")

    def unpause_slot(self, slot):
        """Despausa un slot via IPC socket. Retorna True si exitoso."""
        self._flow(f"unpause_slot() - slot {slot.slot_id}")

        if not slot.process:
            self._flow("  → No hay proceso en el slot, retornando False")
            return False

        try:
            self._flow(f"  → Conectando a socket {slot.socket_path}")
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(slot.socket_path)
            sock.send(b'{"command":["set_property","pause",false]}\n')
            sock.close()
            self._flow("  → Comando de despause enviado OK")
            return True
        except Exception as e:
            self._flow(f"  → Error despausando slot {slot.slot_id}: {e}")
            return False

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
        self._flow(f"play_video_from_info() - {video_info.get('title', '')[:40]}")

        link = video_info.get('link')
        if not link:
            self._flow("  → Sin link válido, saliendo")
            self.log("Video sin enlace válido", "ERROR")
            return

        # Verificar si hay un slot READY para este video (prefetch completado)
        ready_slot = self.get_ready_slot(link)
        if ready_slot:
            self._flow(f"  → Slot {ready_slot.slot_id} está READY, usando directamente")
            self._stop_current_playback_only()

            if self.unpause_slot(ready_slot):
                # Reconectar signals
                ready_slot.process.finished.connect(self.on_playback_finished)
                ready_slot.process.readyReadStandardOutput.connect(self.on_mpv_output)

                with self.slot_lock:
                    ready_slot.state = 'playing'
                self.current_slot = ready_slot
                self.current_process = ready_slot.process

                self.current_title = video_info.get('title') or 'Sin título'
                self.load_start_time = time.time()
                self.playback_started = True
                self.is_loading = False
                self.progress_bar.setRange(0, 100)

                self.status_label.setText(f"⚡ {self.current_title[:50]}")
                self.status_label.setStyleSheet("font-size: 18px; color: #6ba36e;")
                self.log(f"⚡ Instantáneo: {self.current_title[:30]}...")

                # Pre-cargar el siguiente
                self.prefetch_next()
                return
            else:
                self._flow(f"  → Unpause falló, liberando slot y continuando")
                with self.slot_lock:
                    ready_slot.cleanup()

        # Verificar si hay un prefetch en curso para ESTE video
        prefetching_slot = self.get_prefetching_slot(link)
        # También verificar si el prefetch_process actual es para este video
        if not prefetching_slot and self.prefetch_slot and self.prefetch_slot.video_link == link:
            prefetching_slot = self.prefetch_slot

        # Debug: mostrar estado del prefetch y slots
        self._flow(f"  → DEBUG requested link: {link}")
        self._log_slots()
        if self.prefetch_slot:
            self._flow(f"  → DEBUG prefetch_slot: state={self.prefetch_slot.state}, link_match={self.prefetch_slot.video_link == link}")
            self._flow(f"  → DEBUG prefetch_slot.video_link: {self.prefetch_slot.video_link}")
        else:
            self._flow(f"  → DEBUG prefetch_slot es None")

        if prefetching_slot:
            self._flow(f"  → Prefetch en curso para este video (slot {prefetching_slot.slot_id}), esperando...")
            # Detener solo la reproducción actual, NO el prefetch
            self._stop_current_playback_only()
            # Configurar estado de espera
            self.current_title = video_info.get('title') or 'Sin título'
            self.is_loading = True
            self.playback_started = False
            self.progress_bar.setValue(0)
            self.progress_bar.setRange(0, 0)
            self.time_label.setText("Cargando...")
            self.load_start_time = time.time()
            self.status_label.setText(f"⏳ Esperando: {self.current_title[:40]}...")
            self.status_label.setStyleSheet("font-size: 18px; color: #c9886a;")
            self.log(f"⏳ Esperando prefetch: {self.current_title[:30]}...")
            self.waiting_for_prefetch = video_info
            return

        self._flow("  → Llamando stop_music()")
        self.stop_music()

        # Set loading state
        self.current_title = video_info.get('title') or 'Sin título'
        self.is_loading = True
        self.playback_started = False
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.time_label.setText("Cargando...")

        # DEBUG: Start timing
        self.load_start_time = time.time()

        # Obtener URL directa del cache
        direct_url = self.url_cache.pop(link, None)

        if direct_url:
            # URL en cache - reproducir inmediatamente
            self._flow("  → Cache HIT! URL directa disponible")
            self.status_label.setText(f"⚡ {self.current_title[:50]}")
            self.status_label.setStyleSheet("font-size: 18px; color: #6ba36e;")
            self.log(f"⚡ Cache hit: {self.current_title[:30]}...")
            self._start_mpv_with_url(direct_url)
        else:
            # Resolver URL con yt-dlp asíncrono (no bloquea UI)
            self._flow("  → Cache MISS - iniciando yt-dlp asíncrono")
            self.status_label.setText(f"⏳ Cargando: {self.current_title[:50]}...")
            self.status_label.setStyleSheet("font-size: 18px; color: #c9886a;")
            self.log(f"🔄 yt-dlp: {self.current_title[:30]}...")

            self.resolve_video_info = video_info
            self.resolve_process = QProcess(self)
            self.resolve_process.finished.connect(self._on_resolve_finished)

            cmd_args = ['-f', 'bestaudio[protocol!=m3u8_native]/bestaudio/best', '-g', '--no-warnings', '--socket-timeout', '10', '--retries', '1', '--fragment-retries', '1']
            if os.path.exists(COOKIES_FILE):
                cmd_args.extend(['--cookies', COOKIES_FILE])
            cmd_args.append(link)

            self._flow("  → Ejecutando yt-dlp asíncrono")
            self.resolve_process.start(YTDLP_PATH, cmd_args)

    def _on_resolve_finished(self):
        """Callback cuando yt-dlp termina de resolver la URL."""
        self._flow("_on_resolve_finished()")

        if not self.resolve_process:
            self._flow("  → No hay resolve_process, saliendo")
            return

        output = self.resolve_process.readAllStandardOutput().data().decode('utf-8').strip()

        if output and output.startswith('http'):
            self._flow("  → URL resuelta OK, llamando _start_mpv_with_url()")
            self._start_mpv_with_url(output)
        else:
            stderr = self.resolve_process.readAllStandardError().data().decode('utf-8').strip()
            self._flow(f"  → yt-dlp falló: {stderr[:60]}")
            self.log("Error obteniendo URL", "ERROR")
            self.is_loading = False
            self.progress_bar.setRange(0, 100)

        self.resolve_process = None
        self.resolve_video_info = None

    def _start_mpv_with_url(self, direct_url):
        """Inicia mpv con una URL directa."""
        self._flow("_start_mpv_with_url()")

        mpv_args = [
            '--no-video',
            '--term-osd-bar=no',
            '--msg-level=all=status',
            direct_url
        ]

        self._flow("  → Creando QProcess para mpv")
        self.current_process = QProcess(self)
        self.current_process.finished.connect(self.on_playback_finished)
        self.current_process.readyReadStandardError.connect(self.on_mpv_output)
        self.current_process.setProcessChannelMode(QProcess.MergedChannels)
        self.current_process.readyReadStandardOutput.connect(self.on_mpv_output)
        self.current_process.start('mpv', mpv_args)
        self._flow("  → mpv iniciado, llamando prefetch_next()")

        # Pre-cargar el siguiente en la cola
        self.prefetch_next()

    def on_mpv_output(self):
        if not self.current_process:
            return

        data = self.current_process.readAllStandardOutput().data().decode('utf-8', errors='ignore')

        # DEBUG: Log timing for key events
        if self.load_start_time:
            elapsed = time.time() - self.load_start_time
            for line in data.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # Log ytdl-hook events (URL resolution)
                if 'ytdl_hook' in line or 'yt-dlp' in line.lower():
                    print(f"[DEBUG] T+{elapsed:.2f}s: {line[:80]}", flush=True)
                # Log when audio opens
                elif 'Opening' in line or 'AO:' in line:
                    print(f"[DEBUG] T+{elapsed:.2f}s: {line[:80]}", flush=True)

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
                # DEBUG: Log time to first audio
                if self.load_start_time:
                    elapsed = time.time() - self.load_start_time
                    print(f"[DEBUG] T+{elapsed:.2f}s: ✅ AUDIO STARTED", flush=True)
                    self.log(f"⏱️ Cargó en {elapsed:.1f}s")

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
        self._flow("on_playback_finished()")
        self._flow(f"  → Terminó: {self.current_title[:40]}")
        self._flow(f"  → Cola: {len(self.queue)} items")
        self._log_slots()

        # Liberar slot actual
        if self.current_slot:
            self._flow(f"  → Liberando slot {self.current_slot.slot_id}")
            with self.slot_lock:
                self.current_slot.cleanup()
            self.current_slot = None

        self.current_process = None
        self.is_loading = False
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 100)
        self.time_label.setText("--:-- / --:--")
        self.status_label.setStyleSheet("font-size: 18px; color: #8b7355;")

        if not self.queue:
            self._flow("  → Cola vacía, reproducción terminada")
            self.log("Reproducción finalizada")
            self.status_label.setText("Listo")
            return

        # Buscar slot ready para el siguiente video
        next_video = self.queue[0]
        next_link = next_video.get('link')
        ready_slot = self.get_ready_slot(next_link)

        if ready_slot:
            self._flow(f"  → Slot {ready_slot.slot_id} está READY, intentando unpause")
            if self.unpause_slot(ready_slot):
                self._flow(f"  → Unpause exitoso! Usando slot {ready_slot.slot_id}")

                # Reconectar signals
                ready_slot.process.finished.connect(self.on_playback_finished)
                ready_slot.process.readyReadStandardOutput.connect(self.on_mpv_output)

                # Actualizar estado del slot
                with self.slot_lock:
                    ready_slot.state = 'playing'
                self.current_slot = ready_slot
                self.current_process = ready_slot.process

                # Actualizar estado de reproducción
                self.queue.pop(0)
                self.update_queue_display()
                self.current_title = ready_slot.video_info.get('title', 'Sin título')
                self.load_start_time = time.time()
                self.playback_started = True

                self.status_label.setText(f"⚡ {self.current_title[:50]}")
                self.status_label.setStyleSheet("font-size: 18px; color: #6ba36e;")
                self.log(f"⚡ Instantáneo: {self.current_title[:30]}...")

                # Pre-cargar el siguiente
                self._flow("  → Llamando prefetch_next() para pre-cargar siguiente")
                self.prefetch_next()
                return
            else:
                self._flow(f"  → Unpause slot {ready_slot.slot_id} falló, liberando y usando fallback")
                with self.slot_lock:
                    ready_slot.cleanup()
        else:
            self._flow("  → No hay slot READY disponible")

        # Verificar si hay un prefetch en curso para este video
        prefetching_slot = self.get_prefetching_slot(next_link)
        # También verificar si el prefetch_process actual es para este video
        if not prefetching_slot and self.prefetch_slot and self.prefetch_slot.video_link == next_link:
            prefetching_slot = self.prefetch_slot

        if prefetching_slot:
            self._flow(f"  → Slot {prefetching_slot.slot_id} está PREFETCHING, esperando...")
            self.log(f"⏳ Esperando: {next_video.get('title', '')[:30]}...")
            self.status_label.setText(f"⏳ Esperando: {next_video.get('title', '')[:40]}...")
            self.status_label.setStyleSheet("font-size: 18px; color: #c9886a;")
            self.progress_bar.setRange(0, 0)  # Indeterminate mode
            self.waiting_for_prefetch = next_video
            return

        # Fallback: reproducción normal (no hay prefetch en curso)
        self._flow("  → No hay prefetch en curso, usando play_next()")
        self.log(f"Siguiente en cola ({len(self.queue)} restantes)")
        self.play_next()

    def _stop_current_playback_only(self):
        """Detiene solo la reproducción actual, sin tocar el prefetch."""
        if self.current_process:
            try:
                self.current_process.finished.disconnect()
            except:
                pass
            self.current_process.terminate()
            self.current_process.waitForFinished(1000)
            self.current_process = None

        if self.current_slot:
            with self.slot_lock:
                self.current_slot.cleanup()
            self.current_slot = None

        # Terminar proceso de resolución URL (si hay uno en curso)
        if self.resolve_process:
            self.resolve_process.terminate()
            self.resolve_process = None
            self.resolve_video_info = None

    def stop_music(self):
        was_playing = self.current_process is not None

        # Terminar proceso actual
        if self.current_process:
            try:
                self.current_process.finished.disconnect()
            except:
                pass
            self.current_process.terminate()
            self.current_process.waitForFinished(1000)
            self.current_process = None

        # Limpiar slot actual
        if self.current_slot:
            with self.slot_lock:
                self.current_slot.cleanup()
            self.current_slot = None

        # Terminar proceso de resolución URL
        if self.resolve_process:
            self.resolve_process.terminate()
            self.resolve_process = None
            self.resolve_video_info = None

        # Terminar prefetch en curso (desconectar signal primero para evitar callbacks huérfanos)
        if self.prefetch_process:
            try:
                self.prefetch_process.finished.disconnect()
            except:
                pass
            self.prefetch_process.terminate()
            self.prefetch_process = None
        if self.prefetch_slot:
            with self.slot_lock:
                self.prefetch_slot.cleanup()
        self.prefetch_slot = None
        self.waiting_for_prefetch = None

        # Limpiar todos los slots
        with self.slot_lock:
            for slot in self.slots:
                slot.cleanup()

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
