#!/usr/bin/env python3
"""Test del sistema de doble-buffer para pre-carga de videos."""

import sys
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from yt_mp_player_qt5 import BBBPlayer

# Video que funciona para testing (repetido para probar el sistema de slots)
TEST_VIDEOS = [
    {'title': 'Rick Astley 1', 'link': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'duration': '3:33'},
    {'title': 'Rick Astley 2', 'link': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'duration': '3:33'},
    {'title': 'Rick Astley 3', 'link': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'duration': '3:33'},
    {'title': 'Rick Astley 4', 'link': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'duration': '3:33'},
]

start_time = None


def test_prefetch_system():
    global start_time
    app = QApplication(sys.argv)
    player = BBBPlayer()

    # Agregar videos a la cola
    for video in TEST_VIDEOS:
        player.queue.append(video)
    player.update_queue_display()

    print("\n" + "="*60)
    print("=== TEST: Sistema de Doble-Buffer ===")
    print("="*60)
    print(f"Cola inicial: {len(player.queue)} videos")

    # Verificar estado inicial de slots
    print("\nEstado inicial de slots:")
    for slot in player.slots:
        print(f"  Slot {slot.slot_id}: state={slot.state}")

    start_time = time.time()

    # Timer para verificar estado cada 5 segundos
    def check_state():
        elapsed = time.time() - start_time
        print(f"\n--- Estado (T+{elapsed:.1f}s) ---")
        print(f"Cola: {len(player.queue)} videos restantes")
        print(f"Reproduciendo: {player.current_title[:40] if player.current_title else 'Nada'}")
        print(f"Current slot: {player.current_slot.slot_id if player.current_slot else 'None'}")

        for slot in player.slots:
            video = slot.video_info.get('title', 'None')[:25] if slot.video_info else 'None'
            print(f"  Slot {slot.slot_id}: {slot.state:12} | {video}")

        # Verificar invariantes
        playing_count = sum(1 for s in player.slots if s.state == 'playing')
        if playing_count > 1:
            print("  [ERROR] Más de un slot en estado 'playing'!")

    timer = QTimer()
    timer.timeout.connect(check_state)
    timer.start(5000)

    # Iniciar reproducción del primer video
    print("\n--- Iniciando reproducción ---")
    player.play_next()

    # Cerrar después de 3 minutos
    def finish_test():
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"=== TEST COMPLETADO (T+{elapsed:.1f}s) ===")
        print(f"{'='*60}")
        print(f"Videos en cola restantes: {len(player.queue)}")
        app.quit()

    QTimer.singleShot(300000, finish_test)  # 5 minutos

    player.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test_prefetch_system()
