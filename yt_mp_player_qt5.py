import sys
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QListWidget, QLabel)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from youtubesearchpython import VideosSearch

# --- Hilo de Búsqueda (Worker) ---
# Separamos la búsqueda de la UI para no bloquear el framebuffer
class SearchThread(QThread):
    results_ready = pyqtSignal(list)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            search = VideosSearch(self.query, limit=12)
            results = search.result()['result']
            self.results_ready.emit(results)
        except Exception as e:
            print(f"Error en búsqueda: {e}")
            self.results_ready.emit([])

# --- Aplicación Principal ---
class BBBPlayer(QWidget):
    def __init__(self):
        super().__init__()
        # En modo framebuffer, la ventana suele tomar toda la pantalla por defecto,
        # pero definimos un tamaño base por si acaso.
        self.resize(800, 480) 
        self.setWindowTitle('BBB Tuber')
        
        self.current_process = None
        self.video_data_list = []

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # 1. Barra de Búsqueda
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
        
        # 2. Lista de Resultados
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("font-size: 18px;")
        self.list_widget.itemDoubleClicked.connect(self.play_video)
        
        # 3. Controles / Estado
        self.status_label = QLabel("Listo")
        self.status_label.setStyleSheet("font-size: 16px; color: gray;")
        
        btn_stop = QPushButton("Detener")
        btn_stop.setStyleSheet("background-color: #d9534f; color: white; font-size: 20px; font-weight: bold;")
        btn_stop.clicked.connect(self.stop_music)

        # Añadir al layout principal
        layout.addLayout(search_layout)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.status_label)
        layout.addWidget(btn_stop)

        self.setLayout(layout)

    def start_search(self):
        query = self.search_input.text()
        if not query: return
        
        self.status_label.setText("Buscando...")
        self.list_widget.clear()
        
        self.search_thread = SearchThread(query)
        self.search_thread.results_ready.connect(self.handle_results)
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
        link = video_info['link']
        
        self.stop_music()
        
        self.status_label.setText(f"Reproduciendo: {video_info['title']}")
        
        # Ejecutar mpv sin video (audio only)
        # --no-video reduce carga de CPU drásticamente
        cmd = ['mpv', '--no-video', link]
        self.current_process = subprocess.Popen(cmd)

    def stop_music(self):
        if self.current_process:
            self.current_process.terminate()
            self.current_process = None
            self.status_label.setText("Detenido")

if __name__ == '__main__':
    # Pasar argumentos al QApplication es importante para recibir flags como -platform
    app = QApplication(sys.argv)
    player = BBBPlayer()
    
    # En modo embedded sin gestor de ventanas, showFullScreen es lo ideal
    player.showFullScreen() 
    
    sys.exit(app.exec_())


