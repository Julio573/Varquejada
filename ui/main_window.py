import sys
import cv2
import time
import os
import glob
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QListWidget, 
                             QFrame, QStatusBar, QGroupBox, QSlider, QCheckBox,
                             QGraphicsOpacityEffect, QSpacerItem, QSizePolicy,
                             QGraphicsDropShadowEffect, QStackedLayout, QGridLayout)
from PyQt6.QtCore import QTimer, Qt, QUrl, QPropertyAnimation, QEasingCurve, QPoint, QRect, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QPen, QBrush, QCursor, QShortcut, QKeySequence, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QDialog, QComboBox, QListView

class CustomMessageBox(QDialog):
    """QMessageBox customizado com design do sistema."""
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 180)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #12141D;
                border: 2px solid #1F2937;
                border-radius: 16px;
            }
            QLabel { color: #F9FAFB; font-size: 14px; }
            QPushButton {
                background-color: #1A1C26;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 10px;
                min-width: 80px;
            }
            QPushButton#btn_yes { background-color: #F59E0B; color: #000000; font-weight: bold; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        
        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet("color: #71767b; font-weight: 800; font-size: 10px; letter-spacing: 1px;")
        layout.addWidget(title_lbl)
        
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)
        
        layout.addSpacing(20)
        
        btn_layout = QHBoxLayout()
        self.btn_no = QPushButton("NÃO")
        self.btn_no.clicked.connect(self.reject)
        
        self.btn_yes = QPushButton("SIM")
        self.btn_yes.setObjectName("btn_yes")
        self.btn_yes.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_no)
        btn_layout.addWidget(self.btn_yes)
        layout.addLayout(btn_layout)

class CameraSelectionDialog(QDialog):
    """Diálogo customizado para seleção de câmera com o design do sistema."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SELECIONAR CÂMERA")
        self.setFixedSize(450, 220)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        
        # Design
        self.setStyleSheet("""
            QDialog {
                background-color: #12141D;
                border: 2px solid #1F2937;
                border-radius: 16px;
            }
            QLabel { color: #F9FAFB; font-weight: bold; font-size: 14px; }
            QComboBox {
                background-color: #1A1C26;
                border: 1px solid #374151;
                border-radius: 8px;
                padding: 10px;
                color: #FFFFFF;
                font-size: 13px;
                min-width: 250px;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1C26;
                color: #FFFFFF;
                selection-background-color: #F59E0B;
                selection-color: #000000;
                outline: none;
                border: 1px solid #374151;
            }
            QComboBox QAbstractItemView::item {
                min-height: 35px;
                padding-left: 10px;
                color: #FFFFFF;
            }
            QComboBox::drop-down { border: none; }
            QPushButton {
                background-color: #F59E0B;
                color: #000000;
                font-weight: bold;
                border-radius: 10px;
                padding: 12px;
                min-width: 100px;
            }
            QPushButton#btn_cancel {
                background-color: transparent;
                border: 1px solid #374151;
                color: #9CA3AF;
            }
            QPushButton#btn_stop {
                background-color: #EF4444;
                color: #FFFFFF;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("DISPOSITIVOS DISPONÍVEIS")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.combo = QComboBox()
        self.combo.setView(QListView())
        layout.addWidget(self.combo)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15) # Mais espaço entre os botões
        
        # Se houver captura ativa, mostramos o botão de PARAR
        self.result_code = -1 # -1: Cancel, -2: Stop, >=0: Camera Index
        
        self.btn_cancel = QPushButton("CANCELAR")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        if parent and hasattr(parent, 'controller') and parent.controller.capture and not isinstance(parent.controller.capture.source, str):
            self.btn_stop = QPushButton("PARAR")
            self.btn_stop.setObjectName("btn_stop")
            self.btn_stop.clicked.connect(self.handle_stop)
            btn_layout.addWidget(self.btn_stop)
        
        btn_layout.addSpacing(10) # Espaço extra antes do botão principal
        
        self.btn_ok = QPushButton("INICIAR / TROCAR")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)
        
        layout.addLayout(btn_layout)
        
        # Chama a detecção APÓS os botões existirem
        self.detect_cameras()

    def handle_stop(self):
        self.result_code = -2
        self.done(1) # Fecha com sucesso para processar o código -2

    def accept(self):
        self.result_code = self.get_selected_index()
        super().accept()

    def get_action_result(self):
        return self.result_code

    def detect_cameras(self):
        """Detecta câmeras de forma segura no Linux usando o sistema de arquivos."""
        self.combo.clear()
        
        # 1. Mapeia nomes amigáveis via v4l (Linux)
        friendly_names = {}
        try:
            v4l_path = "/dev/v4l/by-id/"
            if os.path.exists(v4l_path):
                for name in os.listdir(v4l_path):
                    target = os.path.realpath(os.path.join(v4l_path, name))
                    if "video" in target:
                        try:
                            idx = int(target.split("video")[-1])
                            # Nome limpo e curto
                            clean_name = name.replace("usb-", "").split("-video-")[0].replace("_", " ")
                            friendly_names[idx] = clean_name
                        except: pass
        except: pass

        # 2. Lista dispositivos reais
        import glob
        video_devices = sorted(glob.glob("/dev/video*"))
        added_indices = set()

        for dev in video_devices:
            try:
                idx = int(dev.replace("/dev/video", ""))
                # Foca em dispositivos principais (pares) para evitar duplicatas de metadata
                if idx % 2 == 0 and idx not in added_indices:
                    name = friendly_names.get(idx, f"Câmera {idx}")
                    self.combo.addItem(f"{name.upper()}", idx)
                    added_indices.add(idx)
            except: pass
        
        # Fallback se nada for detectado
        if self.combo.count() == 0:
            self.combo.addItem("CÂMERA PADRÃO (0)", 0)
        
        self.btn_ok.setEnabled(True)

    def get_selected_index(self):
        return self.combo.currentData()

class ClickableSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.markers = []  # Lista de dicionários: {'pos': ms, 'color': QColor, 'label': str}

    def add_marker(self, pos_ms, color, label=""):
        self.markers.append({'pos': pos_ms, 'color': QColor(color), 'label': label})
        self.update()

    def clear_markers(self):
        self.markers = []
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            self.setValue(int(val))
            self.sliderMoved.emit(int(val))
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.markers or self.maximum() <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Geometria do slider para alinhar os marcadores
        rect = self.rect()
        groove_height = 6 # Aproximado do QSS
        y_center = rect.height() // 2
        
        for marker in self.markers:
            # Calcula a posição X proporcional ao tempo
            ratio = marker['pos'] / self.maximum()
            x = int(ratio * rect.width())
            
            # Desenha um pequeno diamante ou círculo como marcador
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.setBrush(QBrush(marker['color']))
            
            # Marcador em formato de diamante/pino
            points = [
                QPoint(x, y_center - 6),
                QPoint(x + 4, y_center),
                QPoint(x, y_center + 6),
                QPoint(x - 4, y_center)
            ]
            painter.drawPolygon(points)

class Speedometer(QWidget):
    """Widget de Multímetro/Velocímetro customizado baseado no design VeloVaquejo."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0.0
        self._display_value = 0.0
        self.setMinimumSize(220, 220)
        
        # Timer para animação suave
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate)
        self.animation_timer.start(16) # ~60 FPS

    def setValue(self, val):
        self.value = float(val)

    def _animate(self):
        # Interpolação para movimento suave da agulha/barra (Inércia visual)
        diff = self.value - self._display_value
        if abs(diff) < 0.05:
            self._display_value = self.value
        else:
            self._display_value += diff * 0.15 # Velocidade de resposta da animação
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 25
        
        # 1. Desenha o Arco de Fundo (Pista de Telemetria)
        pen_bg = QPen(QColor("#1F2937"), 14)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        # Arco de 240 graus centralizado no topo (-210 até 30 graus)
        painter.drawArc(center.x() - radius, center.y() - radius, radius * 2, radius * 2, -30 * 16, 240 * 16)
        
        # 2. Desenha o Arco de Progresso (Ativo - Laranja Ambar)
        # Mapeia 0-80 km/h para o arco de 240 graus
        span_angle = int((min(self._display_value, 80) / 80) * 240)
        pen_active = QPen(QColor("#F59E0B"), 14) 
        pen_active.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_active)
        painter.drawArc(center.x() - radius, center.y() - radius, radius * 2, radius * 2, 210 * 16, -span_angle * 16)
        
        # 3. Marcas de Escala (Ticks)
        painter.setPen(QColor("#374151"))
        for i in range(9): # 0 a 80 de 10 em 10
            angle = 210 - (i * 30)
            rad = np.deg2rad(angle)
            p1 = center + QPoint(int((radius-20) * np.cos(rad)), int(-(radius-20) * np.sin(rad)))
            p2 = center + QPoint(int((radius-30) * np.cos(rad)), int(-(radius-30) * np.sin(rad)))
            painter.drawLine(p1, p2)

        # 4. Texto Central
        # Valor (Foco principal)
        painter.setPen(QColor("#F9FAFB"))
        font_val = QFont("Inter", 38, QFont.Weight.ExtraBold)
        painter.setFont(font_val)
        val_text = f"{int(self._display_value)}"
        painter.drawText(rect.adjusted(0, 0, 0, -10), Qt.AlignmentFlag.AlignCenter, val_text)
        
        # Unidade (Sub-texto)
        painter.setPen(QColor("#9CA3AF"))
        font_unit = QFont("Inter", 11, QFont.Weight.Bold)
        font_unit.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        painter.setFont(font_unit)
        painter.drawText(rect.adjusted(0, 55, 0, 0), Qt.AlignmentFlag.AlignCenter, "KM/H")

class VideoWidget(QWidget):
    """Widget de vídeo otimizado para pintura direta de frames OpenCV."""
    calibration_clicked = pyqtSignal(QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = QImage()
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(640, 360)
        self.calibration_points = []
        self.is_calibrating = False

    def mousePressEvent(self, event):
        if self.is_calibrating and event.button() == Qt.MouseButton.LeftButton:
            self.calibration_clicked.emit(event.position().toPoint())
        super().mousePressEvent(event)

    def update_frame(self, frame):
        if frame is None: return
        try:
            # Conversão segura para RGB (mais estável que BGR888 direto)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            # Criação do QImage com cópia profunda para segurança de thread
            self.image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
            self.update()
        except Exception as e:
            print(f"[VIDEO_WIDGET] Erro na conversão: {e}")

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        if self.image.isNull():
            # DIAGNÓSTICO: Se a imagem for nula, pinta magenta com um X branco
            painter.fillRect(rect, QColor(255, 0, 255)) 
            painter.setPen(QPen(Qt.GlobalColor.white, 3))
            painter.drawLine(rect.topLeft(), rect.bottomRight())
            painter.drawLine(rect.topRight(), rect.bottomLeft())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "DEBUG: IMAGEM NULA")
            return

        # 1. Fundo Midnight
        painter.fillRect(rect, QColor(10, 13, 20))

        # 2. Desenho centralizado mantendo proporção
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        img_size = self.image.size()
        img_size.scale(rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
        
        x = (rect.width() - img_size.width()) // 2
        y = (rect.height() - img_size.height()) // 2
        
        target_rect = QRect(x, y, img_size.width(), img_size.height())
        painter.drawImage(target_rect, self.image)

        # 3. Desenho de Calibração
        if self.is_calibrating and self.calibration_points:
            painter.setPen(QPen(QColor("#F59E0B"), 3, Qt.PenStyle.DashLine))
            painter.setBrush(QColor("#F59E0B"))
            for pt in self.calibration_points:
                painter.drawEllipse(pt, 5, 5)
            if len(self.calibration_points) == 2:
                painter.drawLine(self.calibration_points[0], self.calibration_points[1])

    def get_frame_point(self, screen_point):
        """Converte um ponto da tela para a coordenada original do frame OpenCV."""
        if self.image.isNull(): return None
        rect = self.rect()
        img_size = self.image.size()
        img_size.scale(rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
        
        x_off = (rect.width() - img_size.width()) // 2
        y_off = (rect.height() - img_size.height()) // 2
        
        # Ponto relativo ao vídeo desenhado
        rx = screen_point.x() - x_off
        ry = screen_point.y() - y_off
        
        # Proporção
        orig_w = self.image.width()
        orig_h = self.image.height()
        
        fx = (rx / img_size.width()) * orig_w
        fy = (ry / img_size.height()) * orig_h
        
        return int(fx), int(fy)

class MainWindow(QMainWindow):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.frame_count = 0
        self.setWindowTitle("VELOVAQUEJO PRO")
        self.setMinimumSize(1400, 900)
        
        # Assets dir
        self.assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons")
        
        # Media
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        
        # 1. HEADER
        self.setup_header()
        
        # 2. CONTENT
        self.content_container = QWidget()
        self.content_layout = QHBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(24)
        
        # Left Area (Video Area)
        self.video_area = QWidget()
        self.video_area_layout = QVBoxLayout(self.video_area)
        self.video_area_layout.setContentsMargins(0, 0, 0, 0)
        self.video_area_layout.setSpacing(24)
        
        self.setup_video_player()
        self.setup_transport_bar()
        
        # Sidebar
        self.setup_sidebar()
        
        self.content_layout.addWidget(self.video_area, stretch=9)
        self.content_layout.addWidget(self.sidebar, stretch=3)
        self.root_layout.addWidget(self.content_container)

        # 3. FOOTER
        self.setup_footer()
        
        # Auto-hide Timer (YouTube style)
        self.controls_timeout = QTimer()
        self.controls_timeout.setSingleShot(True)
        self.controls_timeout.setInterval(2000)
        self.controls_timeout.timeout.connect(self.hide_controls)
        
        self.setup_shortcuts()
        self.load_stylesheet()
        
        self.frame_count = 0

    def setup_header(self):
        self.header_frame = QFrame()
        self.header_frame.setObjectName("header_frame")
        self.header_frame.setFixedHeight(120) # Header bem mais alto
        self.header_frame.setStyleSheet("""
            #header_frame {
                background-color: #0B0F14;
                border-bottom: 2px solid #1F2937;
            }
        """)
        
        header_l = QHBoxLayout(self.header_frame)
        header_l.setContentsMargins(40, 0, 40, 0)
        header_l.setSpacing(0)
        
        # --- LEFT SECTION (Logo Gigante) ---
        self.header_logo = QLabel()
        logo_path = os.path.join(self.assets_dir, "VeloVaquejo.png")
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            # Logo agora com 115px de altura, preenchendo o limite do header
            scaled_pixmap = pixmap.scaledToHeight(115, Qt.TransformationMode.SmoothTransformation)
            self.header_logo.setPixmap(scaled_pixmap)
        
        header_l.addWidget(self.header_logo, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        # Spacer
        header_l.addStretch()
        
        # --- CENTER SECTION (Telemetria de Corrida) ---
        telemetry_container = QWidget()
        telemetry_layout = QHBoxLayout(telemetry_container)
        telemetry_layout.setContentsMargins(0, 0, 0, 0)
        telemetry_layout.setSpacing(12) # Espaço entre os cards
        
        card_style = """
            QFrame {
                background-color: #12141D;
                border: 1px solid #1F2937;
                border-radius: 12px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """

        # Card: Tempo Percorrido
        time_card = QFrame()
        time_card.setStyleSheet(card_style)
        time_v = QVBoxLayout(time_card)
        time_v.setContentsMargins(16, 8, 16, 8)
        time_v.setSpacing(2)
        
        lbl_time_title = QLabel("TEMPO PERCORRIDO")
        lbl_time_title.setStyleSheet("color: #71767b; font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        lbl_time_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_header_elapsed = QLabel("00:00.0")
        self.lbl_header_elapsed.setStyleSheet("color: #F9FAFB; font-family: 'JetBrains Mono'; font-size: 20px; font-weight: 700;")
        self.lbl_header_elapsed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        time_v.addWidget(lbl_time_title)
        time_v.addWidget(self.lbl_header_elapsed)
        
        # Card: Distância Percorrida
        dist_card = QFrame()
        dist_card.setStyleSheet(card_style)
        dist_v = QVBoxLayout(dist_card)
        dist_v.setContentsMargins(16, 8, 16, 8)
        dist_v.setSpacing(2)
        
        lbl_dist_title = QLabel("DISTÂNCIA PERCORRIDA")
        lbl_dist_title.setStyleSheet("color: #71767b; font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        lbl_dist_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_header_dist = QLabel("0.0 m")
        self.lbl_header_dist.setStyleSheet("color: #22C55E; font-family: 'JetBrains Mono'; font-size: 20px; font-weight: 700;")
        self.lbl_header_dist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        dist_v.addWidget(lbl_dist_title)
        dist_v.addWidget(self.lbl_header_dist)
        
        telemetry_layout.addWidget(time_card)
        telemetry_layout.addWidget(dist_card)
        header_l.addWidget(telemetry_container, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        # Spacer to push timer to right
        header_l.addStretch()
        
        # --- RIGHT SECTION (Data e Relógio em Cards Separados) ---
        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Card: Data
        date_card = QFrame()
        date_card.setStyleSheet(card_style)
        date_v = QVBoxLayout(date_card)
        date_v.setContentsMargins(16, 8, 16, 8)
        date_v.setSpacing(2)
        
        lbl_date_title = QLabel("DATA ATUAL")
        lbl_date_title.setStyleSheet("color: #71767b; font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        lbl_date_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_header_date = QLabel()
        self.lbl_header_date.setStyleSheet("color: #9CA3AF; font-size: 14px; font-weight: 600;")
        self.lbl_header_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        date_v.addWidget(lbl_date_title)
        date_v.addWidget(self.lbl_header_date)

        # Card: Relógio
        clock_card = QFrame()
        clock_card.setStyleSheet(card_style)
        clock_v = QVBoxLayout(clock_card)
        clock_v.setContentsMargins(16, 8, 16, 8)
        clock_v.setSpacing(2)
        
        lbl_clock_title = QLabel("HORA LOCAL")
        lbl_clock_title.setStyleSheet("color: #71767b; font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        lbl_clock_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_header_clock = QLabel()
        self.lbl_header_clock.setStyleSheet("color: #F9FAFB; font-family: 'JetBrains Mono'; font-size: 20px; font-weight: 700;")
        self.lbl_header_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        clock_v.addWidget(lbl_clock_title)
        clock_v.addWidget(self.lbl_header_clock)

        right_layout.addWidget(date_card)
        right_layout.addWidget(clock_card)
        header_l.addWidget(right_container, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        self.root_layout.addWidget(self.header_frame)
        
        # Inicia a atualização do relógio
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_header_time)
        self.clock_timer.start(1000)
        self.update_header_time() # Primeira chamada imediata

    def setup_video_player(self):
        self.video_container = QWidget()
        self.video_container.setObjectName("video_container")
        self.video_container.setMinimumSize(800, 500)
        self.video_container.setMouseTracking(True)
        
        self.video_stack = QStackedLayout(self.video_container)
        
        # Empty
        self.empty_widget = QWidget()
        empty_l = QVBoxLayout(self.empty_widget)
        empty_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.empty_circle = QFrame()
        self.empty_circle.setObjectName("empty_state_circle")
        self.empty_circle.setFixedSize(160, 160)
        cl = QVBoxLayout(self.empty_circle)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_up_icon = QLabel()
        up_p = os.path.join(self.assets_dir, "upload.svg")
        self.lbl_up_icon.setPixmap(self.get_svg_icon(up_p, size=QSize(48,48), color="#3a3d47"))
        cl.addWidget(self.lbl_up_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        
        empty_l.addWidget(self.empty_circle, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_l.addSpacing(20)
        lbl_e = QLabel("Aguardando vídeo")
        lbl_e.setObjectName("empty_state_text")
        empty_l.addWidget(lbl_e, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.video_stack.addWidget(self.empty_widget)
        
        # Player (Novo Renderizador de Alta Performance)
        self.video_widget = VideoWidget()
        self.video_widget.setObjectName("video_widget")
        self.video_widget.setMouseTracking(True)
        self.video_widget.installEventFilter(self)
        self.video_widget.calibration_clicked.connect(self.handle_calibration_click)
        self.video_stack.addWidget(self.video_widget)
        
        self.video_area_layout.addWidget(self.video_container, stretch=1)
        
        # Espaçador fixo para manter o tamanho original da área de vídeo
        # compensando o fato de a barra de transporte ser flutuante agora
        self.bottom_spacer = QWidget()
        self.bottom_spacer.setFixedHeight(100)
        self.video_area_layout.addWidget(self.bottom_spacer)
        
        # SÓ INSTALA O FILTRO NO CONTAINER APÓS TUDO CRIADO
        self.video_container.installEventFilter(self)

        # OSD (On-Screen Display) estilo YouTube
        self.osd_label = QLabel(self.video_container)
        self.osd_label.setObjectName("osd_label")
        self.osd_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.osd_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.osd_label.hide()
        
        self.osd_opacity = QGraphicsOpacityEffect(self.osd_label)
        self.osd_label.setGraphicsEffect(self.osd_opacity)
        
        self.osd_anim = QPropertyAnimation(self.osd_opacity, b"opacity")
        self.osd_anim.setDuration(600)
        self.osd_anim.setStartValue(1.0)
        self.osd_anim.setEndValue(0.0)
        self.osd_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self.osd_anim.finished.connect(self.osd_label.hide)

    def show_osd(self, text):
        """Mostra feedback visual no centro do vídeo com prioridade de exibição."""
        self.osd_label.setText(text)
        self.osd_label.show()
        self.osd_label.raise_() # Garante que fique na frente do vídeo
        
        # Centralização precisa baseada no tamanho atual
        w, h = 300, 150
        self.osd_label.setFixedSize(w, h)
        self.osd_label.move(
            (self.video_container.width() - w) // 2,
            (self.video_container.height() - h) // 2
        )
        
        self.osd_opacity.setOpacity(1.0)
        self.osd_anim.stop()
        self.osd_anim.start()
        print(f"OSD exibido: {text}") # Debug log no console

    def setup_transport_bar(self):
        # Agora o container é filho direto do video_container (Layer flutuante estilo YouTube)
        self.transport_container = QFrame(self.video_container)
        self.transport_container.setObjectName("transport_container")
        self.transport_container.setFixedHeight(100)
        
        # Estilo YouTube: Fundo transparente, sem bordas sólidas
        self.transport_container.setStyleSheet("""
            #transport_container {
                background-color: transparent;
                border: none;
            }
        """)
        
        t_l = QVBoxLayout(self.transport_container)
        t_l.setContentsMargins(30, 0, 30, 10)
        
        # Opacity para o efeito de HOVER (Começa invisível)
        self.transp_opacity = QGraphicsOpacityEffect(self.transport_container)
        self.transp_opacity.setOpacity(0.0) 
        self.transport_container.setGraphicsEffect(self.transp_opacity)
        
        self.transp_anim = QPropertyAnimation(self.transp_opacity, b"opacity")
        self.transp_anim.setDuration(300)
        
        # Row 1: Timeline
        self.video_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.video_slider.setObjectName("video_slider")
        t_l.addWidget(self.video_slider)
        
        # Row 2: Controls
        ctrl_l = QHBoxLayout()
        
        self.btn_prev_f = QPushButton("‹")
        self.btn_prev_f.setObjectName("btn_prev_f")
        ctrl_l.addWidget(self.btn_prev_f)
        
        self.btn_pause_float = QPushButton("▶")
        self.btn_pause_float.setObjectName("btn_pause_float")
        ctrl_l.addWidget(self.btn_pause_float)
        
        self.btn_next_f = QPushButton("›")
        self.btn_next_f.setObjectName("btn_next_f")
        ctrl_l.addWidget(self.btn_next_f)
        
        self.lbl_time = QLabel("00:00.000")
        self.lbl_time.setObjectName("lbl_timecode")
        ctrl_l.addWidget(self.lbl_time)
        
        self.lbl_time_total = QLabel("/ 00:00.000")
        self.lbl_time_total.setStyleSheet("color: #FFFFFF; font-family: 'JetBrains Mono'; font-size: 16px; font-weight: bold;")
        ctrl_l.addWidget(self.lbl_time_total)
        
        ctrl_l.addStretch()
        
        # Volume
        self.last_volume = 50
        self.btn_vol_toggle = QPushButton()
        self.btn_vol_toggle.setObjectName("btn_vol_icon")
        self.btn_vol_toggle.setFixedSize(32, 32)
        self.btn_vol_toggle.clicked.connect(self.toggle_mute)
        
        self.sld_volume = QSlider(Qt.Orientation.Horizontal)
        self.sld_volume.setObjectName("vol_slider_prof")
        self.sld_volume.setFixedWidth(80)
        self.sld_volume.valueChanged.connect(self.change_volume)
        
        ctrl_l.addWidget(self.btn_vol_toggle)
        ctrl_l.addWidget(self.sld_volume)
        ctrl_l.addSpacing(20)

        # Fullscreen Button (YouTube Style)
        self.btn_fullscreen_player = QPushButton("⛶")
        self.btn_fullscreen_player.setObjectName("btn_fullscreen_player")
        self.btn_fullscreen_player.setFixedSize(32, 32)
        self.btn_fullscreen_player.clicked.connect(self.toggle_fullscreen)
        ctrl_l.addWidget(self.btn_fullscreen_player)
        ctrl_l.addSpacing(10)
        
        # Speeds
        self.speed_btns = {}
        for s in [0.1, 0.25, 0.5, 1.0, 2.0]:
            btn = QPushButton(f"{s}x")
            btn.setFixedSize(60, 32)
            self.speed_btns[s] = btn
            btn.clicked.connect(lambda ch, val=s: self.set_granular_speed(val))
            ctrl_l.addWidget(btn)
        
        t_l.addLayout(ctrl_l)
        
        # Posicionamento inicial
        self.reposition_controls()
        self.change_volume(50)
        self.update_speed_ui(1.0)

    def setup_sidebar(self):
        self.sidebar = QWidget()
        s_l = QVBoxLayout(self.sidebar)
        s_l.setContentsMargins(0, 0, 0, 0)
        s_l.setSpacing(24)

        # Dashboard de Velocidade
        v_g = QGroupBox("VELOCIDADE ATUAL")
        v_gl = QVBoxLayout(v_g)
        v_gl.setContentsMargins(15, 25, 15, 15)
        v_gl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.speedometer = Speedometer()
        v_gl.addWidget(self.speedometer)
        
        s_l.addWidget(v_g)
        
        t_g = QGroupBox("FERRAMENTAS DE PRECISÃO")
        t_gl = QGridLayout(t_g)
        tools = [("Carregar", "📤", self.open_video), ("Câmera", "((•))", self.start_cam),
                 ("Calibrar", "📏", self.toggle_lane), ("Zoom", "🔍", self.toggle_zoom),
                 ("Início", "🚩", self.mark_start), ("Fim", "🏁", self.mark_end)]
        for i, (name, icon, func) in enumerate(tools):
            btn = QPushButton(f"{icon}\n{name}")
            btn.setProperty("class", "tool-btn")
            if name == "Calibrar": self.btn_lock_lane = btn; btn.setCheckable(True)
            if name == "Zoom": self.btn_zoom = btn; btn.setCheckable(True)
            if func: btn.clicked.connect(func)
            t_gl.addWidget(btn, i // 2, i % 2)
        s_l.addWidget(t_g)
        
        h_g = QGroupBox("HISTÓRICO")
        h_gl = QVBoxLayout(h_g)
        self.log_list = QListWidget()
        h_gl.addWidget(self.log_list)
        s_l.addWidget(h_g, stretch=1)

    def setup_footer(self):
        self.footer = QFrame()
        self.footer.setFixedHeight(30)
        self.footer.setStyleSheet("background: #0b0d14; border-top: 1px solid #1a1c26;")
        f_l = QHBoxLayout(self.footer)
        f_l.addWidget(QLabel("Pronto para análise. Pressione F ou F11 para Tela Cheia."), alignment=Qt.AlignmentFlag.AlignLeft)
        self.root_layout.addWidget(self.footer)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Space"), self, self.toggle_pause)
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("F"), self, self.toggle_fullscreen)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        # Hover inteligente: Mostra controles ao mexer o mouse na área do vídeo
        if hasattr(self, 'video_widget') and obj in [self.video_container, self.video_widget]:
            if event.type() in [event.Type.MouseMove, event.Type.Enter]:
                self.show_controls()
                self.controls_timeout.start()
            elif event.type() == event.Type.Leave:
                # Esconde rapidamente ao tirar o mouse da área total de vídeo
                QTimer.singleShot(100, self.check_mouse_leave)
            if event.type() == event.Type.Resize:
                self.reposition_controls()
        return super().eventFilter(obj, event)

    def check_mouse_leave(self):
        """Verifica se o mouse realmente saiu da área de interação do player."""
        if not self.video_container.underMouse() and not self.transport_container.underMouse():
            self.hide_controls(force=True)

    def show_controls(self):
        if hasattr(self, 'transp_opacity') and self.transp_opacity.opacity() < 1.0:
            self.transp_anim.stop()
            self.transp_anim.setEndValue(1.0)
            self.transp_anim.start()

    def hide_controls(self, force=False):
        # Não esconde se o mouse estiver em cima da barra (a menos que seja uma saída forçada)
        if not force:
            if self.transport_container.underMouse() or self.video_stack.currentIndex() != 1:
                self.controls_timeout.start()
                return
        
        self.transp_anim.stop()
        self.transp_anim.setEndValue(0.0)
        self.transp_anim.start()

    def reposition_controls(self):
        # Posiciona sempre na base do vídeo de forma flutuante
        if hasattr(self, 'transport_container'):
            margin = 15
            w = self.video_container.width() - (2 * margin)
            h = self.transport_container.height()
            self.transport_container.setGeometry(margin, self.video_container.height() - h - margin, w, h)
            self.transport_container.raise_()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.header_frame.show()
            self.sidebar.show()
            self.footer.show()
            self.bottom_spacer.show()
            self.content_layout.setContentsMargins(24, 24, 24, 24)
        else:
            self.showFullScreen()
            self.header_frame.hide()
            self.sidebar.hide()
            self.footer.hide()
            self.bottom_spacer.hide()
            self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # O reposicionamento agora é unificado pelo eventFilter do video_container
        QTimer.singleShot(50, self.reposition_controls)

    def get_svg_icon(self, path, size=QSize(24, 24), color="#FFFFFF"):
        if not os.path.exists(path): return QPixmap()
        renderer = QSvgRenderer(path)
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        renderer.render(p)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect(pixmap.rect(), QColor(color))
        p.end()
        return pixmap

    def change_volume(self, value):
        self.audio_output.setVolume(value / 100.0)
        path = os.path.join(self.assets_dir, "volume-up-interface-symbol.svg" if value > 66 else "medium-volume.svg" if value > 33 else "low-volume.svg")
        self.btn_vol_toggle.setIcon(QIcon(self.get_svg_icon(path, color="#71767b" if value == 0 else "#FFFFFF")))

    def toggle_mute(self):
        if self.sld_volume.value() > 0: self.last_volume = self.sld_volume.value(); self.sld_volume.setValue(0)
        else: self.sld_volume.setValue(self.last_volume if self.last_volume > 0 else 50)

    def set_granular_speed(self, val):
        if self.controller: self.controller.set_speed(val); self.update_speed_ui(val)

    def update_speed_ui(self, active):
        for s, btn in self.speed_btns.items():
            btn.setStyleSheet(f"background: {'#f0913a' if s==active else '#1a1c26'}; color: {'#000' if s==active else '#71767b'}; border-radius: 12px; font-size: 12px; font-weight: bold;")

    def reset_ui(self):
        """Reseta a interface para o estado inicial de espera."""
        self.video_stack.setCurrentIndex(0)
        self.video_slider.setValue(0)
        self.video_slider.clear_markers()
        self.lbl_header_dist.setText("0.0 m")
        self.lbl_header_elapsed.setText("00:00.0")
        self.speedometer.setValue(0)
        self.video_widget.image = QImage() # Limpa o último frame
        self.video_widget.update()
        self.transport_container.show() # Garante que volte ao padrão

    def display_frame(self, frame):
        if frame is None: return
        
        # Só troca para o player se houver uma captura ativa
        if self.controller and not self.controller.capture:
            return

        # Controle de visibilidade da barra de transporte (Player)
        # Se for câmera (int), esconde a barra. Se for vídeo (str), mostra.
        is_live = not isinstance(self.controller.capture.source, str)
        if is_live:
            self.transport_container.hide()
        else:
            # Em modo vídeo, o sistema de hover automático gerencia o show/hide
            pass

        try:
            # 1. Debugging inicial
            if self.frame_count == 0:
                print(f"[DEBUG] Primeiro frame recebido no Widget: {frame.shape}")
            self.frame_count += 1

            # 2. Sincroniza Pilha de Vídeo
            if self.video_stack.currentIndex() != 1: 
                self.video_stack.setCurrentIndex(1)
            
            # 3. Desenho de Telemetria
            if self.controller and hasattr(self.controller, 'horse_tracker'):
                frame = self.controller.horse_tracker.draw_tracking(frame, None, None)
            
            if frame is None: return

            # 4. Zoom (opcional)
            if hasattr(self, 'btn_zoom') and self.btn_zoom.isChecked():
                h, w = frame.shape[:2]
                nw, nh = int(w/1.5), int(h/1.5)
                x, y = (w-nw)//2, (h-nh)//2
                frame = frame[y:y+nh, x:x+nw]

            if frame is None or frame.size == 0: return
            
            # 5. Pintura Direta (Alta Performance)
            self.video_widget.update_frame(frame)
            
        except Exception as e:
            print(f"Erro na renderização: {e}")

    def update_header_time(self):
        """Atualiza data e relógio no header a cada segundo."""
        now = datetime.now()
        # Data formatada: Terça-feira, 12 de Maio de 2026
        # Usaremos formatação manual simples para garantir compatibilidade de locale
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        data_str = f"{now.day} de {meses[now.month-1]} de {now.year}"
        clock_str = now.strftime("%H:%M:%S")
        
        self.lbl_header_date.setText(data_str.upper())
        self.lbl_header_clock.setText(clock_str)

    def load_stylesheet(self):
        try:
            with open("/home/juliodev/Downloads/Varquejada_System/ui/style.qss", "r") as f: self.setStyleSheet(f.read())
        except: pass

    def toggle_lane_lock(self, checked):
        self.video_widget.is_calibrating = checked
        if checked:
            self.video_widget.calibration_points = []
            self.log_list.addItem("MODO CALIBRAÇÃO: Clique em 2 pontos da largura da pista (1.5m)")
        else:
            self.video_widget.calibration_points = []
            self.video_widget.update()

    def handle_calibration_click(self, point):
        self.video_widget.calibration_points.append(point)
        if len(self.video_widget.calibration_points) > 2:
            self.video_widget.calibration_points.pop(0)
        
        self.video_widget.update()
        
        if len(self.video_widget.calibration_points) == 2:
            p1 = self.video_widget.get_frame_point(self.video_widget.calibration_points[0])
            p2 = self.video_widget.get_frame_point(self.video_widget.calibration_points[1])
            if p1 and p2:
                dist_px = np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
                ppm = dist_px / 1.5 # Assume 1.5m de largura da pista
                if self.controller:
                    self.controller.set_ppm(ppm)
                    self.log_list.addItem(f"Calibração concluída: {ppm:.2f} px/m")

    def open_video(self):
        self.video_slider.clear_markers()
        self.controller.open_video_file()

    def mark_start(self):
        if self.controller:
            self.controller.add_manual_marker("Início da Corrida", "#3B82F6") # Azul

    def mark_end(self):
        if self.controller:
            self.controller.add_manual_marker("Fim da Corrida / Queda", "#22C55E") # Verde

    def start_cam(self): self.controller.start_camera()
    def toggle_pause(self): self.controller.toggle_pause()
    def toggle_lane(self, checked): self.controller.toggle_lane_lock(checked)
    def toggle_zoom(self, checked): pass

if __name__ == "__main__":
    app = QApplication(sys.argv); window = MainWindow(); window.show(); sys.exit(app.exec())
