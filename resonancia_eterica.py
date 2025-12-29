#!/usr/bin/env python3
"""
Resonancia Etérica - Prototipo Visual v3
Interfaz antroposófica inspirada en el Goetheanum
Basado en diseño de referencia - Versión mejorada
"""

import sys
import math
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene,
                             QGraphicsObject, QGraphicsTextItem, QLineEdit,
                             QGraphicsProxyWidget)
from PyQt5.QtCore import (Qt, QRectF, QPointF, QPropertyAnimation,
                          pyqtProperty, QEasingCurve, QTimer, QSequentialAnimationGroup)
from PyQt5.QtGui import (QPainter, QBrush, QColor, QRadialGradient,
                         QLinearGradient, QPen, QPainterPath, QFont,
                         QFontDatabase, QPolygonF, QPixmap)
import os


class FlorCentral(QGraphicsObject):
    """Flor/Lotus central - representa la canción actual."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scale_factor = 1.0
        self._glow = 0.5
        self._rotation = 0
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return QRectF(-120, -80, 240, 160)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)

        # Aura externa amplia (resplandor suave rosado/durazno)
        aura = QRadialGradient(0, 0, 110)
        aura.setColorAt(0, QColor(255, 180, 150, int(80 * self._glow)))
        aura.setColorAt(0.4, QColor(255, 150, 120, int(50 * self._glow)))
        aura.setColorAt(0.7, QColor(230, 120, 100, int(30 * self._glow)))
        aura.setColorAt(1, QColor(200, 100, 80, 0))
        painter.setBrush(QBrush(aura))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(-110, -70, 220, 140))

        # Pétalos externos (capa 1) - más horizontales y grandes
        for i in range(8):
            painter.save()
            angle = i * 45 + self._rotation * 0.3
            painter.rotate(angle)

            # Pétalo externo ancho y horizontal
            petal = QPainterPath()
            petal.moveTo(0, 0)
            petal.cubicTo(30, -15, 70, -20, 90, -10)
            petal.cubicTo(95, -5, 95, 5, 90, 10)
            petal.cubicTo(70, 20, 30, 15, 0, 0)

            # Gradiente del pétalo - salmón/durazno
            grad = QRadialGradient(50, 0, 60)
            grad.setColorAt(0, QColor(255, 200, 170, int(180 + 50 * self._glow)))
            grad.setColorAt(0.5, QColor(245, 170, 140, int(160 + 40 * self._glow)))
            grad.setColorAt(1, QColor(230, 140, 110, int(100 + 30 * self._glow)))

            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor(220, 150, 120, 60), 0.5))
            painter.drawPath(petal)
            painter.restore()

        # Pétalos internos (capa 2) - más pequeños
        for i in range(6):
            painter.save()
            angle = i * 60 + 30 + self._rotation * 0.5
            painter.rotate(angle)

            petal = QPainterPath()
            petal.moveTo(0, 0)
            petal.cubicTo(15, -10, 40, -12, 55, -6)
            petal.cubicTo(60, 0, 55, 6, 55, 6)
            petal.cubicTo(40, 12, 15, 10, 0, 0)

            grad = QRadialGradient(30, 0, 40)
            grad.setColorAt(0, QColor(255, 220, 195, int(200 + 55 * self._glow)))
            grad.setColorAt(0.6, QColor(250, 190, 160, int(180 + 50 * self._glow)))
            grad.setColorAt(1, QColor(240, 160, 130, int(120 + 40 * self._glow)))

            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor(230, 170, 140, 50), 0.5))
            painter.drawPath(petal)
            painter.restore()

        # Centro brillante intenso
        centro = QRadialGradient(0, 0, 35)
        centro.setColorAt(0, QColor(255, 255, 250, int(255 * self._glow)))
        centro.setColorAt(0.3, QColor(255, 250, 235, int(230 * self._glow)))
        centro.setColorAt(0.6, QColor(255, 230, 200, int(180 * self._glow)))
        centro.setColorAt(1, QColor(255, 200, 160, int(100 * self._glow)))
        painter.setBrush(QBrush(centro))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(-30, -25, 60, 50))

        # Punto central ultra brillante
        punto = QRadialGradient(0, 0, 12)
        punto.setColorAt(0, QColor(255, 255, 255, 255))
        punto.setColorAt(0.5, QColor(255, 250, 240, 200))
        punto.setColorAt(1, QColor(255, 240, 220, 0))
        painter.setBrush(QBrush(punto))
        painter.drawEllipse(QRectF(-10, -8, 20, 16))

    @pyqtProperty(float)
    def escala(self):
        return self._scale_factor

    @escala.setter
    def escala(self, value):
        self._scale_factor = value
        self.setScale(value)

    @pyqtProperty(float)
    def brillo(self):
        return self._glow

    @brillo.setter
    def brillo(self, value):
        self._glow = value
        self.update()

    @pyqtProperty(float)
    def rotacion(self):
        return self._rotation

    @rotacion.setter
    def rotacion(self, value):
        self._rotation = value
        self.update()


class HojaCola(QGraphicsObject):
    """Hoja flotante para elementos de la cola - más grande y translúcida."""

    def __init__(self, texto, subtexto="", posicion=QPointF(0, 0), escala=1.0, parent=None):
        super().__init__(parent)
        self.texto = texto[:30] if len(texto) > 30 else texto
        self.subtexto = subtexto
        self._opacity = 0.85
        self._hover_glow = 0
        self._glow = 0.4
        self.setPos(posicion)
        self.setScale(escala)
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return QRectF(-90, -40, 180, 80)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)

        # Glow externo suave
        glow = QRadialGradient(0, 0, 85)
        glow.setColorAt(0, QColor(100, 160, 180, int(60 * self._glow)))
        glow.setColorAt(0.5, QColor(80, 140, 160, int(30 * self._glow)))
        glow.setColorAt(1, QColor(60, 120, 140, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(-85, -50, 170, 100))

        # Forma de hoja más orgánica y ondulante
        path = QPainterPath()
        path.moveTo(-75, 0)
        path.cubicTo(-60, -25, -30, -32, 0, -28)
        path.cubicTo(30, -25, 60, -20, 75, -8)
        path.cubicTo(80, 0, 75, 8, 75, 8)
        path.cubicTo(60, 20, 30, 25, 0, 28)
        path.cubicTo(-30, 32, -60, 25, -75, 0)

        # Gradiente azul-verde etéreo más vibrante
        grad = QLinearGradient(-75, 0, 75, 0)
        alpha = int(140 * self._opacity + 80 * self._hover_glow)
        grad.setColorAt(0, QColor(70, 130, 160, alpha))
        grad.setColorAt(0.3, QColor(90, 155, 180, alpha + 20))
        grad.setColorAt(0.5, QColor(100, 165, 190, alpha + 30))
        grad.setColorAt(0.7, QColor(90, 155, 180, alpha + 20))
        grad.setColorAt(1, QColor(70, 130, 160, alpha))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(130, 190, 210, int(120 * self._opacity)), 1.5))
        painter.drawPath(path)

        # Nervadura central curva
        nervadura = QPainterPath()
        nervadura.moveTo(-60, 0)
        nervadura.cubicTo(-30, -3, 30, 3, 60, 0)
        painter.setPen(QPen(QColor(160, 210, 230, int(100 * self._opacity)), 1))
        painter.drawPath(nervadura)

        # Nervaduras secundarias
        for offset in [-15, 15]:
            nerv = QPainterPath()
            nerv.moveTo(-40, offset * 0.3)
            nerv.cubicTo(-20, offset * 0.8, 20, offset * 0.8, 40, offset * 0.3)
            painter.setPen(QPen(QColor(150, 200, 220, int(60 * self._opacity)), 0.5))
            painter.drawPath(nerv)

        # Texto principal
        painter.setPen(QColor(240, 240, 235, int(255 * self._opacity)))
        painter.setFont(QFont("Sans Serif", 10))
        painter.drawText(QRectF(-70, -15, 140, 20), Qt.AlignCenter, self.texto)

        # Subtexto
        if self.subtexto:
            painter.setPen(QColor(200, 210, 220, int(180 * self._opacity)))
            painter.setFont(QFont("Sans Serif", 8))
            painter.drawText(QRectF(-70, 5, 140, 16), Qt.AlignCenter, self.subtexto)

    @pyqtProperty(float)
    def glow(self):
        return self._glow

    @glow.setter
    def glow(self, value):
        self._glow = value
        self.update()

    def hoverEnterEvent(self, event):
        self._hover_glow = 1.0
        self.setScale(self.scale() * 1.08)
        self.update()

    def hoverLeaveEvent(self, event):
        self._hover_glow = 0
        self.setScale(self.scale() / 1.08)
        self.update()


class RamaVertical(QGraphicsObject):
    """Rama que crece verticalmente con hojas azul-verde translúcidas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._growth = 1.0
        self._sway = 0

    def boundingRect(self):
        return QRectF(-100, -180, 200, 200)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)

        # Tallo principal curvo que crece hacia arriba
        tallo = QPainterPath()
        tallo.moveTo(0, 20)
        tallo.cubicTo(5 + self._sway, -20, -5 + self._sway, -60,
                      10 + self._sway, -100)
        tallo.cubicTo(15 + self._sway, -130, 5 + self._sway, -150,
                      0 + self._sway, -160)

        # Gradiente del tallo
        grad_tallo = QLinearGradient(0, 20, 0, -160)
        grad_tallo.setColorAt(0, QColor(80, 120, 100, 200))
        grad_tallo.setColorAt(0.5, QColor(90, 140, 120, 180))
        grad_tallo.setColorAt(1, QColor(100, 150, 130, 150))

        painter.setPen(QPen(QBrush(grad_tallo), 4))
        painter.drawPath(tallo)

        # Hojas grandes translúcidas
        hojas = [
            (-35, -30, -50, 1.0, True),    # izquierda abajo
            (40, -50, 40, 0.95, False),    # derecha
            (-50, -80, -60, 1.1, True),    # izquierda arriba
            (35, -110, 50, 0.9, False),    # derecha arriba
            (-20, -140, -30, 0.85, True),  # izquierda top
        ]

        for x, y, rot, scale, flip in hojas:
            painter.save()
            painter.translate(x * self._growth + self._sway * 0.5, y * self._growth)
            painter.rotate(rot + self._sway * 2)
            if flip:
                painter.scale(-scale * self._growth, scale * self._growth)
            else:
                painter.scale(scale * self._growth, scale * self._growth)

            # Hoja grande y translúcida
            hoja = QPainterPath()
            hoja.moveTo(0, 0)
            hoja.cubicTo(15, -20, 45, -30, 60, -20)
            hoja.cubicTo(70, -10, 70, 10, 60, 20)
            hoja.cubicTo(45, 30, 15, 20, 0, 0)

            # Gradiente azul-verde translúcido
            grad = QRadialGradient(35, 0, 50)
            grad.setColorAt(0, QColor(100, 170, 160, 180))
            grad.setColorAt(0.4, QColor(80, 150, 145, 150))
            grad.setColorAt(0.8, QColor(70, 140, 135, 100))
            grad.setColorAt(1, QColor(60, 130, 125, 50))

            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor(120, 180, 170, 120), 1))
            painter.drawPath(hoja)

            # Nervadura principal
            nerv = QPainterPath()
            nerv.moveTo(5, 0)
            nerv.cubicTo(20, -2, 40, 0, 55, 0)
            painter.setPen(QPen(QColor(140, 190, 180, 150), 1.5))
            painter.drawPath(nerv)

            # Nervaduras secundarias
            for i, (nx, ny1, ny2) in enumerate([(20, -8, 8), (35, -12, 12), (48, -8, 8)]):
                painter.setPen(QPen(QColor(130, 180, 170, 80), 0.5))
                painter.drawLine(QPointF(nx, 0), QPointF(nx + 8, ny1))
                painter.drawLine(QPointF(nx, 0), QPointF(nx + 8, ny2))

            painter.restore()

    @pyqtProperty(float)
    def growth(self):
        return self._growth

    @growth.setter
    def growth(self, value):
        self._growth = value
        self.update()

    @pyqtProperty(float)
    def sway(self):
        return self._sway

    @sway.setter
    def sway(self, value):
        self._sway = value
        self.update()


class PanelAtajos(QGraphicsObject):
    """Panel de atajos como constelación de estrellas brillantes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._glow = 0.7
        self._twinkle = 0
        self.atajos = [
            ("↵", "Play"),
            ("Q", "Queue"),
            ("␣", "Pause"),
            ("N", "Next"),
            ("S", "Stop"),
            ("/", "Search"),
        ]

    def boundingRect(self):
        return QRectF(0, 0, 130, 220)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)

        # Título
        painter.setPen(QColor(200, 215, 230, 220))
        painter.setFont(QFont("Sans Serif", 11, QFont.Light))
        painter.drawText(QRectF(0, 0, 130, 28), Qt.AlignCenter, "ATAJOS")

        # Posiciones en patrón de constelación
        posiciones = [
            (35, 55), (95, 50), (55, 90),
            (25, 125), (100, 115), (65, 160),
        ]

        # Líneas de constelación - más brillantes
        conexiones = [(0, 1), (0, 2), (1, 2), (2, 3), (2, 4), (3, 5), (4, 5)]

        # Dibujar líneas con gradiente
        for i, j in conexiones:
            p1 = QPointF(*posiciones[i])
            p2 = QPointF(*posiciones[j])

            grad = QLinearGradient(p1, p2)
            grad.setColorAt(0, QColor(180, 200, 220, int(80 * self._glow)))
            grad.setColorAt(0.5, QColor(200, 220, 240, int(100 * self._glow)))
            grad.setColorAt(1, QColor(180, 200, 220, int(80 * self._glow)))

            painter.setPen(QPen(QBrush(grad), 1.5))
            painter.drawLine(p1, p2)

        # Estrellas brillantes
        for idx, (pos, (tecla, desc)) in enumerate(zip(posiciones, self.atajos)):
            x, y = pos

            # Variación de twinkle por estrella
            twinkle_offset = (idx * 0.3 + self._twinkle) % 1.0
            twinkle_factor = 0.7 + 0.3 * math.sin(twinkle_offset * math.pi * 2)

            # Glow externo amplio
            outer_glow = QRadialGradient(x, y, 25)
            outer_glow.setColorAt(0, QColor(255, 240, 180, int(120 * self._glow * twinkle_factor)))
            outer_glow.setColorAt(0.4, QColor(255, 220, 150, int(60 * self._glow * twinkle_factor)))
            outer_glow.setColorAt(1, QColor(255, 200, 100, 0))
            painter.setBrush(QBrush(outer_glow))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(x, y), 20, 20)

            # Brillo interno
            inner_glow = QRadialGradient(x, y, 10)
            inner_glow.setColorAt(0, QColor(255, 255, 250, int(255 * twinkle_factor)))
            inner_glow.setColorAt(0.5, QColor(255, 245, 220, int(200 * twinkle_factor)))
            inner_glow.setColorAt(1, QColor(255, 230, 180, 0))
            painter.setBrush(QBrush(inner_glow))
            painter.drawEllipse(QPointF(x, y), 8, 8)

            # Punto central brillante
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(QPointF(x, y), 2.5, 2.5)

            # Tecla - dorada
            painter.setPen(QColor(255, 240, 200))
            painter.setFont(QFont("Sans Serif", 9, QFont.Bold))
            painter.drawText(QRectF(x - 15, y - 8, 30, 16), Qt.AlignCenter, tecla)

    @pyqtProperty(float)
    def glow(self):
        return self._glow

    @glow.setter
    def glow(self, value):
        self._glow = value
        self.update()

    @pyqtProperty(float)
    def twinkle(self):
        return self._twinkle

    @twinkle.setter
    def twinkle(self, value):
        self._twinkle = value
        self.update()


class EstrellaDecorativa(QGraphicsObject):
    """Estrella decorativa de 4 puntas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._glow = 0.8
        self._rotation = 0

    def boundingRect(self):
        return QRectF(-30, -30, 60, 60)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.save()
        painter.rotate(self._rotation)

        # Glow externo
        glow = QRadialGradient(0, 0, 28)
        glow.setColorAt(0, QColor(200, 220, 255, int(100 * self._glow)))
        glow.setColorAt(0.5, QColor(180, 200, 240, int(50 * self._glow)))
        glow.setColorAt(1, QColor(160, 180, 220, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(-28, -28, 56, 56))

        # Estrella de 4 puntas
        star = QPainterPath()
        star.moveTo(0, -20)
        star.cubicTo(3, -5, 5, -3, 20, 0)
        star.cubicTo(5, 3, 3, 5, 0, 20)
        star.cubicTo(-3, 5, -5, 3, -20, 0)
        star.cubicTo(-5, -3, -3, -5, 0, -20)

        grad = QRadialGradient(0, 0, 18)
        grad.setColorAt(0, QColor(220, 235, 255, int(255 * self._glow)))
        grad.setColorAt(0.5, QColor(180, 200, 240, int(200 * self._glow)))
        grad.setColorAt(1, QColor(150, 170, 220, int(150 * self._glow)))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(200, 220, 255, 100), 0.5))
        painter.drawPath(star)

        # Centro brillante
        centro = QRadialGradient(0, 0, 5)
        centro.setColorAt(0, QColor(255, 255, 255, 255))
        centro.setColorAt(1, QColor(220, 235, 255, 0))
        painter.setBrush(QBrush(centro))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(-4, -4, 8, 8))

        painter.restore()

    @pyqtProperty(float)
    def glow(self):
        return self._glow

    @glow.setter
    def glow(self, value):
        self._glow = value
        self.update()

    @pyqtProperty(float)
    def rotacion(self):
        return self._rotation

    @rotacion.setter
    def rotacion(self, value):
        self._rotation = value
        self.update()


class CometaProgreso(QGraphicsObject):
    """Barra de progreso como cometa con estela luminosa."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0  # 0.0 a 1.0
        self._glow = 0.8
        self._trail_phase = 0  # Para animación de la estela
        self.path_width = 700  # Ancho del recorrido
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return QRectF(-380, -25, 760, 50)

    def get_comet_pos(self, progress):
        """Calcula posición del cometa en trayectoria curva."""
        x = -350 + progress * self.path_width
        # Curva suave ondulante
        y = math.sin(progress * math.pi * 2) * 8
        return QPointF(x, y)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)

        # Línea de trayectoria sutil (órbita)
        orbit = QPainterPath()
        orbit.moveTo(-350, 0)
        for i in range(100):
            t = i / 99.0
            pos = self.get_comet_pos(t)
            if i == 0:
                orbit.moveTo(pos)
            else:
                orbit.lineTo(pos)

        # Trayectoria base muy sutil
        painter.setPen(QPen(QColor(80, 100, 140, 40), 2))
        painter.drawPath(orbit)

        # Trayectoria recorrida (más brillante)
        if self._progress > 0.01:
            traveled = QPainterPath()
            steps = int(self._progress * 100)
            for i in range(steps + 1):
                t = i / 100.0
                pos = self.get_comet_pos(t)
                if i == 0:
                    traveled.moveTo(pos)
                else:
                    traveled.lineTo(pos)

            grad_traveled = QLinearGradient(-350, 0, self.get_comet_pos(self._progress).x(), 0)
            grad_traveled.setColorAt(0, QColor(100, 150, 200, 30))
            grad_traveled.setColorAt(0.7, QColor(150, 180, 220, 60))
            grad_traveled.setColorAt(1, QColor(200, 220, 255, 100))
            painter.setPen(QPen(QBrush(grad_traveled), 3))
            painter.drawPath(traveled)

        # Posición actual del cometa
        comet_pos = self.get_comet_pos(self._progress)
        cx, cy = comet_pos.x(), comet_pos.y()

        # === ESTELA DEL COMETA ===
        trail_length = 120  # Longitud de la estela
        num_particles = 25

        for i in range(num_particles):
            # Posición hacia atrás en el tiempo
            trail_progress = self._progress - (i / num_particles) * 0.15
            if trail_progress < 0:
                continue

            trail_pos = self.get_comet_pos(trail_progress)
            tx, ty = trail_pos.x(), trail_pos.y()

            # Factor de desvanecimiento
            fade = 1.0 - (i / num_particles)
            fade = fade ** 1.5  # Curva de desvanecimiento

            # Variación con fase de animación
            wave = math.sin(self._trail_phase * 2 + i * 0.5) * 0.2 + 0.8

            # Tamaño decreciente
            size = (12 - i * 0.4) * fade * wave

            if size > 0.5:
                # Partículas de la estela
                particle_glow = QRadialGradient(tx, ty, size * 2)
                alpha = int(180 * fade * wave * self._glow)
                particle_glow.setColorAt(0, QColor(255, 240, 200, alpha))
                particle_glow.setColorAt(0.3, QColor(255, 200, 150, int(alpha * 0.7)))
                particle_glow.setColorAt(0.6, QColor(200, 150, 100, int(alpha * 0.3)))
                particle_glow.setColorAt(1, QColor(150, 100, 80, 0))

                painter.setBrush(QBrush(particle_glow))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(tx, ty), size, size * 0.6)

        # Partículas dispersas en la estela
        for i in range(15):
            spark_progress = self._progress - (i / 15) * 0.12
            if spark_progress < 0:
                continue

            spark_pos = self.get_comet_pos(spark_progress)
            # Offset aleatorio basado en índice y fase
            offset_x = math.sin(i * 1.7 + self._trail_phase * 3) * 8
            offset_y = math.cos(i * 2.3 + self._trail_phase * 2) * 6

            fade = 1.0 - (i / 15)
            alpha = int(120 * fade * self._glow)
            size = 2 + fade * 2

            spark_glow = QRadialGradient(spark_pos.x() + offset_x, spark_pos.y() + offset_y, size)
            spark_glow.setColorAt(0, QColor(255, 255, 220, alpha))
            spark_glow.setColorAt(1, QColor(255, 200, 150, 0))

            painter.setBrush(QBrush(spark_glow))
            painter.drawEllipse(QPointF(spark_pos.x() + offset_x, spark_pos.y() + offset_y), size, size)

        # === CABEZA DEL COMETA ===
        # Glow externo amplio
        outer_glow = QRadialGradient(cx, cy, 35)
        outer_glow.setColorAt(0, QColor(255, 250, 220, int(150 * self._glow)))
        outer_glow.setColorAt(0.3, QColor(255, 220, 150, int(100 * self._glow)))
        outer_glow.setColorAt(0.6, QColor(255, 180, 100, int(50 * self._glow)))
        outer_glow.setColorAt(1, QColor(255, 150, 80, 0))
        painter.setBrush(QBrush(outer_glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 30, 20)

        # Núcleo brillante
        core_glow = QRadialGradient(cx, cy, 12)
        core_glow.setColorAt(0, QColor(255, 255, 255, 255))
        core_glow.setColorAt(0.4, QColor(255, 250, 230, 230))
        core_glow.setColorAt(0.8, QColor(255, 230, 180, 150))
        core_glow.setColorAt(1, QColor(255, 200, 150, 0))
        painter.setBrush(QBrush(core_glow))
        painter.drawEllipse(QPointF(cx, cy), 10, 7)

        # Punto central ultra brillante
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(QPointF(cx, cy), 3, 2)

        # === TIEMPO ===
        # Mostrar tiempo si hay progreso
        if self._progress > 0:
            # Tiempo transcurrido (simulado)
            total_secs = 240  # 4 minutos ejemplo
            current_secs = int(self._progress * total_secs)
            mins = current_secs // 60
            secs = current_secs % 60
            time_str = f"{mins}:{secs:02d}"

            painter.setPen(QColor(220, 210, 190, 200))
            painter.setFont(QFont("Sans Serif", 9))
            painter.drawText(QPointF(cx + 20, cy + 5), time_str)

    @pyqtProperty(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = max(0.0, min(1.0, value))
        self.update()

    @pyqtProperty(float)
    def glow(self):
        return self._glow

    @glow.setter
    def glow(self, value):
        self._glow = value
        self.update()

    @pyqtProperty(float)
    def trail_phase(self):
        return self._trail_phase

    @trail_phase.setter
    def trail_phase(self, value):
        self._trail_phase = value
        self.update()

    def mousePressEvent(self, event):
        """Permitir click para cambiar posición."""
        x = event.pos().x()
        progress = (x + 350) / self.path_width
        self.progress = max(0.0, min(1.0, progress))


class PlantaBioluminiscente(QGraphicsObject):
    """Planta pequeña bioluminiscente turquesa."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._glow = 0.8
        self._sway = 0

    def boundingRect(self):
        return QRectF(-40, -60, 80, 70)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)

        # Glow bioluminiscente
        glow = QRadialGradient(0, -25, 45)
        glow.setColorAt(0, QColor(80, 220, 200, int(120 * self._glow)))
        glow.setColorAt(0.5, QColor(60, 200, 180, int(60 * self._glow)))
        glow.setColorAt(1, QColor(40, 180, 160, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(-40, -55, 80, 70))

        # Tallo central
        tallo = QPainterPath()
        tallo.moveTo(0, 0)
        tallo.cubicTo(self._sway * 2, -15, -self._sway * 2, -30, 0, -45)
        painter.setPen(QPen(QColor(70, 180, 160, 200), 2.5))
        painter.drawPath(tallo)

        # Hojas laterales
        for side in [-1, 1]:
            painter.save()
            painter.translate(side * 5 + self._sway, -20)
            painter.rotate(side * (25 + self._sway * 5))

            hoja = QPainterPath()
            hoja.moveTo(0, 0)
            hoja.cubicTo(8 * side, -8, 20 * side, -10, 25 * side, -5)
            hoja.cubicTo(28 * side, 0, 25 * side, 5, 20 * side, 8)
            hoja.cubicTo(10 * side, 10, 5 * side, 5, 0, 0)

            grad = QRadialGradient(15 * side, 0, 20)
            grad.setColorAt(0, QColor(100, 230, 210, int(200 * self._glow)))
            grad.setColorAt(0.6, QColor(80, 210, 190, int(150 * self._glow)))
            grad.setColorAt(1, QColor(60, 190, 170, int(80 * self._glow)))

            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor(120, 240, 220, 150), 0.5))
            painter.drawPath(hoja)
            painter.restore()

        # Brote superior
        brote = QPainterPath()
        brote.moveTo(-8, -45)
        brote.cubicTo(-5, -55, 0, -58, 0, -55)
        brote.cubicTo(0, -58, 5, -55, 8, -45)
        brote.cubicTo(5, -48, -5, -48, -8, -45)

        grad_brote = QRadialGradient(0, -52, 12)
        grad_brote.setColorAt(0, QColor(150, 255, 240, int(255 * self._glow)))
        grad_brote.setColorAt(0.5, QColor(100, 240, 220, int(200 * self._glow)))
        grad_brote.setColorAt(1, QColor(70, 220, 200, int(100 * self._glow)))

        painter.setBrush(QBrush(grad_brote))
        painter.setPen(Qt.NoPen)
        painter.drawPath(brote)

    @pyqtProperty(float)
    def glow(self):
        return self._glow

    @glow.setter
    def glow(self, value):
        self._glow = value
        self.update()

    @pyqtProperty(float)
    def sway(self):
        return self._sway

    @sway.setter
    def sway(self, value):
        self._sway = value
        self.update()


class ResonanciaEterica(QGraphicsView):
    """Ventana principal - Resonancia Etérica."""

    def __init__(self):
        super().__init__()

        # Configuración ventana
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Escena 720p (1280x720)
        self.scene = QGraphicsScene(-640, -360, 1280, 720)
        self.setScene(self.scene)
        self.resize(1280, 720)

        # Construir interfaz
        self.crear_fondo()  # Imagen PNG de fondo
        # Elementos estáticos ya en la imagen (comentados):
        # self.crear_titulo()
        # self.crear_marco_organico()
        # self.crear_barra_tierra()  # Solo la tierra estática

        # Elementos interactivos/animados sobre la imagen
        self.crear_busqueda()
        self.crear_rama_vertical()
        self.crear_flor_central()
        self.crear_cola_canciones()
        self.crear_cometa_progreso()
        self.crear_planta_inferior()  # Planta animada separada
        self.crear_panel_atajos()
        self.crear_estrella_decorativa()

        # Animaciones
        self.iniciar_animaciones()

    def crear_fondo(self):
        """Fondo con imagen PNG - 720p."""
        # Cargar la imagen de fondo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        imagen_path = os.path.join(script_dir, "Gemini_Generated_Image_4rngoi4rngoi4rng.png")

        if os.path.exists(imagen_path):
            pixmap = QPixmap(imagen_path)
            # Escalar la imagen a 720p exacto
            pixmap = pixmap.scaled(1280, 720, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            pixmap_item = self.scene.addPixmap(pixmap)
            # Centrar la imagen en la escena (origen en -640, -360)
            pixmap_item.setPos(-640, -360)
            pixmap_item.setZValue(-100)  # Asegurar que esté detrás de todo
        else:
            # Fondo de respaldo si no existe la imagen
            fondo_path = QPainterPath()
            fondo_path.addRect(-640, -360, 1280, 720)
            grad_fondo = QRadialGradient(0, 0, 640)
            grad_fondo.setColorAt(0, QColor(20, 25, 50))
            grad_fondo.setColorAt(0.5, QColor(15, 20, 40))
            grad_fondo.setColorAt(1, QColor(10, 12, 25))
            self.scene.addPath(fondo_path, QPen(Qt.NoPen), QBrush(grad_fondo))

    def crear_titulo(self):
        """Título elegante arriba del marco."""
        titulo = self.scene.addText("RESONANCIA ETÉRICA",
                                     QFont("Sans Serif", 20, QFont.Light))
        titulo.setDefaultTextColor(QColor(220, 215, 200, 240))
        titulo.setPos(-120, -365)

    def crear_marco_organico(self):
        """Marco orgánico con curvas fluidas y brillos dorados."""
        # Marco principal con curvas muy ondulantes
        marco = QPainterPath()

        # Punto inicial izquierda
        marco.moveTo(-420, -200)

        # Curvas superiores izquierda - muy ondulantes
        marco.cubicTo(-430, -260, -400, -290, -350, -300)
        marco.cubicTo(-280, -310, -200, -295, -120, -300)
        marco.cubicTo(-40, -305, 40, -305, 120, -300)
        marco.cubicTo(200, -295, 280, -310, 350, -300)
        marco.cubicTo(400, -290, 430, -260, 420, -200)

        # Lado derecho ondulante
        marco.cubicTo(435, -120, 440, -40, 435, 40)
        marco.cubicTo(430, 120, 440, 180, 420, 240)

        # Curvas inferiores
        marco.cubicTo(390, 280, 300, 290, 200, 285)
        marco.cubicTo(100, 280, 0, 290, -100, 285)
        marco.cubicTo(-200, 280, -300, 290, -380, 270)
        marco.cubicTo(-420, 250, -435, 200, -435, 140)

        # Lado izquierdo ondulante
        marco.cubicTo(-440, 60, -435, -20, -430, -100)
        marco.cubicTo(-425, -150, -430, -180, -420, -200)

        # Gradiente del marco - púrpura/azul
        grad_marco = QLinearGradient(-440, 0, 440, 0)
        grad_marco.setColorAt(0, QColor(100, 60, 140, 120))
        grad_marco.setColorAt(0.15, QColor(80, 50, 130, 100))
        grad_marco.setColorAt(0.3, QColor(50, 40, 100, 60))
        grad_marco.setColorAt(0.5, QColor(40, 35, 80, 40))
        grad_marco.setColorAt(0.7, QColor(50, 40, 100, 60))
        grad_marco.setColorAt(0.85, QColor(80, 50, 130, 100))
        grad_marco.setColorAt(1, QColor(100, 60, 140, 120))

        self.scene.addPath(marco, QPen(QColor(140, 100, 180, 80), 4), QBrush(grad_marco))

        # Capa de borde interno más suave
        marco_interno = QPainterPath()
        marco_interno.moveTo(-400, -190)
        marco_interno.cubicTo(-410, -250, -380, -275, -330, -285)
        marco_interno.cubicTo(-260, -295, -180, -280, -100, -285)
        marco_interno.cubicTo(-20, -290, 20, -290, 100, -285)
        marco_interno.cubicTo(180, -280, 260, -295, 330, -285)
        marco_interno.cubicTo(380, -275, 410, -250, 400, -190)
        marco_interno.cubicTo(415, -110, 420, -30, 415, 50)
        marco_interno.cubicTo(410, 130, 420, 180, 400, 230)
        marco_interno.cubicTo(370, 265, 280, 275, 180, 270)
        marco_interno.cubicTo(80, 265, 0, 275, -100, 270)
        marco_interno.cubicTo(-200, 265, -300, 275, -360, 255)
        marco_interno.cubicTo(-400, 235, -415, 190, -415, 130)
        marco_interno.cubicTo(-420, 50, -415, -30, -410, -100)
        marco_interno.cubicTo(-405, -150, -410, -175, -400, -190)

        self.scene.addPath(marco_interno, QPen(QColor(120, 80, 160, 60), 2), QBrush(Qt.NoBrush))

        # Brillos dorados superiores - múltiples capas
        self._crear_brillos_dorados()

    def _crear_brillos_dorados(self):
        """Crear efectos de brillo dorado que fluyen por el marco."""
        # Brillo principal superior
        brillo1 = QPainterPath()
        brillo1.moveTo(-380, -290)
        brillo1.cubicTo(-250, -310, -100, -300, 0, -295)
        brillo1.cubicTo(100, -300, 250, -310, 380, -290)

        grad1 = QLinearGradient(-380, -300, 380, -290)
        grad1.setColorAt(0, QColor(255, 200, 100, 0))
        grad1.setColorAt(0.2, QColor(255, 210, 130, 100))
        grad1.setColorAt(0.4, QColor(255, 225, 160, 150))
        grad1.setColorAt(0.5, QColor(255, 235, 180, 180))
        grad1.setColorAt(0.6, QColor(255, 225, 160, 150))
        grad1.setColorAt(0.8, QColor(255, 210, 130, 100))
        grad1.setColorAt(1, QColor(255, 200, 100, 0))

        self.scene.addPath(brillo1, QPen(grad1, 12), QBrush(Qt.NoBrush))

        # Brillo secundario - más delgado y brillante
        brillo2 = QPainterPath()
        brillo2.moveTo(-350, -285)
        brillo2.cubicTo(-200, -300, -50, -293, 50, -290)
        brillo2.cubicTo(150, -293, 300, -305, 400, -280)

        grad2 = QLinearGradient(-350, -290, 400, -280)
        grad2.setColorAt(0, QColor(255, 220, 150, 0))
        grad2.setColorAt(0.3, QColor(255, 235, 180, 120))
        grad2.setColorAt(0.5, QColor(255, 245, 200, 200))
        grad2.setColorAt(0.7, QColor(255, 235, 180, 120))
        grad2.setColorAt(1, QColor(255, 220, 150, 0))

        self.scene.addPath(brillo2, QPen(grad2, 5), QBrush(Qt.NoBrush))

        # Brillos laterales que bajan
        for side, start_x, end_x in [(-1, -420, -400), (1, 420, 400)]:
            brillo_lat = QPainterPath()
            brillo_lat.moveTo(start_x * 0.95, -250)
            brillo_lat.cubicTo(start_x, -150, start_x * 1.02, -50, end_x, 50)

            grad_lat = QLinearGradient(start_x, -250, end_x, 50)
            grad_lat.setColorAt(0, QColor(255, 220, 150, 100))
            grad_lat.setColorAt(0.3, QColor(255, 200, 120, 60))
            grad_lat.setColorAt(1, QColor(255, 180, 100, 0))

            self.scene.addPath(brillo_lat, QPen(grad_lat, 6), QBrush(Qt.NoBrush))

    def crear_busqueda(self):
        """Área de búsqueda con forma de semilla en esquina superior izquierda."""
        # Forma de semilla/óvalo
        semilla = QPainterPath()
        semilla.addEllipse(-90, -15, 180, 35)

        grad = QLinearGradient(-90, 0, 90, 0)
        grad.setColorAt(0, QColor(50, 70, 90, 100))
        grad.setColorAt(0.5, QColor(70, 90, 110, 130))
        grad.setColorAt(1, QColor(50, 70, 90, 100))

        semilla_item = self.scene.addPath(semilla,
            QPen(QColor(120, 160, 180, 100), 1.5),
            QBrush(grad))
        semilla_item.setPos(-250, -260)

        # Input real
        self.input_busqueda = QLineEdit()
        self.input_busqueda.setPlaceholderText("🔍 Search text input...")
        self.input_busqueda.setFont(QFont("Sans Serif", 11))
        self.input_busqueda.setFixedSize(160, 28)
        self.input_busqueda.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #c8d4e0;
                padding: 0 10px;
            }
        """)
        proxy = self.scene.addWidget(self.input_busqueda)
        proxy.setPos(-350, -245)

    def crear_rama_vertical(self):
        """Rama que crece verticalmente desde el centro."""
        self.rama = RamaVertical()
        self.rama.setPos(0, -80)  # Centrada arriba
        self.scene.addItem(self.rama)

    def crear_flor_central(self):
        """Flor central - canción actual."""
        self.flor = FlorCentral()
        self.flor.setPos(0, 70)  # Centro, ligeramente abajo
        self.scene.addItem(self.flor)

        # Texto de canción actual (ya está en la imagen, comentado)
        # self.texto_cancion = self.scene.addText("Canción Actual",
        #     QFont("Sans Serif", 12))
        # self.texto_cancion.setDefaultTextColor(QColor(240, 235, 220, 220))
        # self.texto_cancion.setPos(-50, 65)
        # self.texto_subtitulo = self.scene.addText("(Euritmia)",
        #     QFont("Sans Serif", 9))
        # self.texto_subtitulo.setDefaultTextColor(QColor(200, 195, 180, 180))
        # self.texto_subtitulo.setPos(-30, 90)

    def crear_cola_canciones(self):
        """Hojas flotantes representando la cola."""
        # Posiciones ajustadas a la imagen 720p
        canciones = [
            ("Canción Anterior", "(Euritmia)", QPointF(-380, 50), 0.85),   # Izq lejana
            ("Canción Anterior", "(Euritmia)", QPointF(-200, 70), 0.80),   # Izq cercana
            ("Canción Actual", "(Euritmia)", QPointF(200, 70), 0.80),      # Der cercana
            ("Canción Actual", "(Euritmia)", QPointF(380, 50), 0.85),      # Der lejana
        ]

        self.hojas_cola = []
        for texto, sub, pos, escala in canciones:
            hoja = HojaCola(texto, sub, pos, escala)
            hoja.setRotation((pos.x() / 15) % 15 - 7)
            self.scene.addItem(hoja)
            self.hojas_cola.append(hoja)

    def crear_cometa_progreso(self):
        """Barra de progreso como cometa con estela."""
        self.cometa = CometaProgreso()
        self.cometa.setPos(0, 200)  # Zona de controles inferior
        self.cometa.progress = 0.35  # Progreso demo
        self.scene.addItem(self.cometa)

    def crear_planta_inferior(self):
        """Planta bioluminiscente animada en la parte inferior."""
        self.planta = PlantaBioluminiscente()
        self.planta.setPos(0, 300)  # Sobre la tierra, abajo
        self.scene.addItem(self.planta)

    def crear_barra_tierra(self):
        """Barra inferior - conexión con la tierra."""
        # Forma de humus/tierra con borde superior muy ondulante
        tierra = QPainterPath()
        tierra.moveTo(-420, 250)
        tierra.cubicTo(-350, 265, -280, 255, -200, 268)
        tierra.cubicTo(-100, 280, 0, 272, 100, 278)
        tierra.cubicTo(200, 285, 300, 270, 380, 262)
        tierra.cubicTo(410, 258, 420, 255, 420, 250)
        tierra.lineTo(420, 300)
        tierra.lineTo(-420, 300)
        tierra.closeSubpath()

        grad_tierra = QLinearGradient(0, 250, 0, 300)
        grad_tierra.setColorAt(0, QColor(55, 40, 30))
        grad_tierra.setColorAt(0.3, QColor(45, 32, 22))
        grad_tierra.setColorAt(0.7, QColor(35, 25, 18))
        grad_tierra.setColorAt(1, QColor(25, 18, 12))

        self.scene.addPath(tierra, QPen(QColor(70, 50, 40, 100), 1), QBrush(grad_tierra))

        # Texto de estado
        estado = self.scene.addText("ESTADO: VIVO - Conectado a la Tierra",
            QFont("Sans Serif", 10))
        estado.setDefaultTextColor(QColor(130, 190, 150, 220))
        estado.setPos(-140, 270)

        # Planta bioluminiscente centrada
        self.planta = PlantaBioluminiscente()
        self.planta.setPos(0, 275)
        self.scene.addItem(self.planta)

    def crear_panel_atajos(self):
        """Panel lateral de atajos."""
        self.panel_atajos = PanelAtajos()
        self.panel_atajos.setPos(480, -100)  # Derecha, centrado verticalmente
        self.scene.addItem(self.panel_atajos)

    def crear_estrella_decorativa(self):
        """Estrella decorativa arriba a la derecha."""
        self.estrella = EstrellaDecorativa()
        self.estrella.setPos(560, -280)  # Esquina superior derecha
        self.estrella.setScale(0.6)  # Más pequeña
        self.scene.addItem(self.estrella)

    def iniciar_animaciones(self):
        """Inicia todas las animaciones."""
        # Respiración de la flor
        self.anim_flor_escala = QPropertyAnimation(self.flor, b"escala")
        self.anim_flor_escala.setDuration(6000)
        self.anim_flor_escala.setStartValue(1.0)
        self.anim_flor_escala.setKeyValueAt(0.5, 1.06)
        self.anim_flor_escala.setEndValue(1.0)
        self.anim_flor_escala.setEasingCurve(QEasingCurve.InOutSine)
        self.anim_flor_escala.setLoopCount(-1)
        self.anim_flor_escala.start()

        # Brillo pulsante
        self.anim_flor_brillo = QPropertyAnimation(self.flor, b"brillo")
        self.anim_flor_brillo.setDuration(5000)
        self.anim_flor_brillo.setStartValue(0.4)
        self.anim_flor_brillo.setKeyValueAt(0.5, 1.0)
        self.anim_flor_brillo.setEndValue(0.4)
        self.anim_flor_brillo.setEasingCurve(QEasingCurve.InOutSine)
        self.anim_flor_brillo.setLoopCount(-1)
        self.anim_flor_brillo.start()

        # Rotación muy lenta de pétalos
        self.anim_flor_rot = QPropertyAnimation(self.flor, b"rotacion")
        self.anim_flor_rot.setDuration(60000)
        self.anim_flor_rot.setStartValue(0)
        self.anim_flor_rot.setEndValue(360)
        self.anim_flor_rot.setLoopCount(-1)
        self.anim_flor_rot.start()

        # Balanceo suave de la rama
        self.anim_rama = QPropertyAnimation(self.rama, b"sway")
        self.anim_rama.setDuration(8000)
        self.anim_rama.setStartValue(-3)
        self.anim_rama.setKeyValueAt(0.5, 3)
        self.anim_rama.setEndValue(-3)
        self.anim_rama.setEasingCurve(QEasingCurve.InOutSine)
        self.anim_rama.setLoopCount(-1)
        self.anim_rama.start()

        # Twinkle de estrellas en constelación
        self.anim_twinkle = QPropertyAnimation(self.panel_atajos, b"twinkle")
        self.anim_twinkle.setDuration(3000)
        self.anim_twinkle.setStartValue(0)
        self.anim_twinkle.setEndValue(1)
        self.anim_twinkle.setLoopCount(-1)
        self.anim_twinkle.start()

        # Rotación lenta de estrella decorativa
        self.anim_estrella = QPropertyAnimation(self.estrella, b"rotacion")
        self.anim_estrella.setDuration(20000)
        self.anim_estrella.setStartValue(0)
        self.anim_estrella.setEndValue(360)
        self.anim_estrella.setLoopCount(-1)
        self.anim_estrella.start()

        # Balanceo de planta bioluminiscente
        self.anim_planta = QPropertyAnimation(self.planta, b"sway")
        self.anim_planta.setDuration(5000)
        self.anim_planta.setStartValue(-2)
        self.anim_planta.setKeyValueAt(0.5, 2)
        self.anim_planta.setEndValue(-2)
        self.anim_planta.setEasingCurve(QEasingCurve.InOutSine)
        self.anim_planta.setLoopCount(-1)
        self.anim_planta.start()

        # Pulsación de glow en planta
        self.anim_planta_glow = QPropertyAnimation(self.planta, b"glow")
        self.anim_planta_glow.setDuration(4000)
        self.anim_planta_glow.setStartValue(0.6)
        self.anim_planta_glow.setKeyValueAt(0.5, 1.0)
        self.anim_planta_glow.setEndValue(0.6)
        self.anim_planta_glow.setEasingCurve(QEasingCurve.InOutSine)
        self.anim_planta_glow.setLoopCount(-1)
        self.anim_planta_glow.start()

        # Animación de la estela del cometa (ondulación continua)
        self.anim_cometa_trail = QPropertyAnimation(self.cometa, b"trail_phase")
        self.anim_cometa_trail.setDuration(2000)
        self.anim_cometa_trail.setStartValue(0)
        self.anim_cometa_trail.setEndValue(math.pi * 2)
        self.anim_cometa_trail.setLoopCount(-1)
        self.anim_cometa_trail.start()

        # Animación demo del progreso del cometa
        self.anim_cometa_progress = QPropertyAnimation(self.cometa, b"progress")
        self.anim_cometa_progress.setDuration(20000)  # 20 segundos para recorrer
        self.anim_cometa_progress.setStartValue(0.0)
        self.anim_cometa_progress.setEndValue(1.0)
        self.anim_cometa_progress.setEasingCurve(QEasingCurve.Linear)
        self.anim_cometa_progress.setLoopCount(-1)
        self.anim_cometa_progress.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_pos'):
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = ResonanciaEterica()
    ventana.show()
    sys.exit(app.exec_())
