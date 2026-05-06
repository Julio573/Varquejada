import sys
import cv2
import time
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QListWidget, 
                             QFrame, QStatusBar, QGroupBox, QSlider, QCheckBox,
                             QGraphicsOpacityEffect, QSpacerItem, QSizePolicy,
                             QGraphicsDropShadowEffect, QStackedLayout, QGridLayout)
from PyQt6.QtCore import QTimer, Qt, QUrl, QPropertyAnimation, QEasingCurve, QPoint, QRect, QSize
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QPen, QBrush, QCursor, QShortcut, QKeySequence, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtSvg import QSvgRenderer

class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            self.setValue(int(val))
            self.sliderMoved.emit(int(val))
        super().mousePressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("VARQUEJADA PRO")
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
        
        # Auto-hide Timer
        self.controls_timeout = QTimer()
        self.controls_timeout.setSingleShot(True)
        self.controls_timeout.setInterval(2000)
        self.controls_timeout.timeout.connect(self.hide_controls)
        
        self.setup_shortcuts()
        self.load_stylesheet()
        
        # Proof Timer
        self.proof_timer_val = 0
        self.proof_timer = QTimer()
        self.proof_timer.timeout.connect(self.update_proof_timer)

    def setup_header(self):
        self.header_frame = QFrame()
        self.header_frame.setObjectName("header_frame")
        self.header_frame.setFixedHeight(80)
        header_l = QHBoxLayout(self.header_frame)
        header_l.setContentsMargins(32, 0, 32, 0)
        
        # Logo + Brand
        logo_l = QHBoxLayout()
        self.header_logo = QLabel()
        self.header_logo.setFixedSize(36, 36)
        logo_path = os.path.join(self.assets_dir, "Imagem-colada-_2_.svg")
        self.header_logo.setPixmap(self.get_svg_icon(logo_path, size=QSize(36,36), color="#f0913a"))
        
        title_v = QVBoxLayout()
        title_v.setSpacing(0)
        lbl_v = QLabel("VARQUEJADA")
        lbl_v.setObjectName("header_title")
        lbl_s = QLabel("ARBITRAGEM ASSISTIDA")
        lbl_s.setObjectName("header_tagline")
        title_v.addWidget(lbl_v)
        title_v.addWidget(lbl_s)
        
        logo_l.addWidget(self.header_logo)
        logo_l.addLayout(title_v)
        header_l.addLayout(logo_l)
        
        header_l.addStretch()
        
        cam_s = QLabel("● Câmera  Offline")
        cam_s.setObjectName("status_cam")
        header_l.addWidget(cam_s)
        header_l.addSpacing(40)
        
        self.lbl_proof_timer = QLabel("00:00.000")
        self.lbl_proof_timer.setObjectName("proof_timer")
        header_l.addWidget(self.lbl_proof_timer)
        
        self.btn_proof = QPushButton("Iniciar")
        self.btn_proof.setFixedSize(80, 32)
        self.btn_proof.setStyleSheet("background: #1a1c26; border: 1px solid #3a3d47; border-radius: 6px;")
        self.btn_proof.clicked.connect(self.toggle_proof_timer)
        header_l.addWidget(self.btn_proof)
        
        self.root_layout.addWidget(self.header_frame)

    def setup_video_player(self):
        self.video_container = QWidget()
        self.video_container.setObjectName("video_container")
        self.video_container.setMinimumSize(800, 500)
        self.video_container.installEventFilter(self)
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
        
        # Player
        self.video_label = QLabel()
        self.video_label.setObjectName("video_label")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_stack.addWidget(self.video_label)
        
        self.video_area_layout.addWidget(self.video_container, stretch=1)

    def setup_transport_bar(self):
        self.transport_container = QFrame()
        self.transport_container.setObjectName("transport_container")
        self.transport_container.setFixedHeight(160)
        t_l = QVBoxLayout(self.transport_container)
        t_l.setContentsMargins(24, 16, 24, 16)
        
        # Opacity for Fullscreen Fade
        self.transp_opacity = QGraphicsOpacityEffect(self.transport_container)
        self.transport_container.setGraphicsEffect(self.transp_opacity)
        self.transp_anim = QPropertyAnimation(self.transp_opacity, b"opacity")
        self.transp_anim.setDuration(400)
        
        # Row 1: Timeline
        self.video_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.video_slider.setObjectName("video_slider")
        t_l.addWidget(self.video_slider)
        
        # Row 2: Controls
        ctrl_l = QHBoxLayout()
        
        self.btn_prev_f = QPushButton("‹")
        self.btn_prev_f.setStyleSheet("font-size: 24px; color: #71767b; background: transparent; border: none;")
        ctrl_l.addWidget(self.btn_prev_f)
        
        self.btn_pause_float = QPushButton("▶")
        self.btn_pause_float.setObjectName("btn_pause_float")
        ctrl_l.addWidget(self.btn_pause_float)
        
        self.btn_next_f = QPushButton("›")
        self.btn_next_f.setStyleSheet("font-size: 24px; color: #71767b; background: transparent; border: none;")
        ctrl_l.addWidget(self.btn_next_f)
        
        self.lbl_time = QLabel("00:00.000")
        self.lbl_time.setObjectName("lbl_timecode")
        ctrl_l.addWidget(self.lbl_time)
        
        self.lbl_time_total = QLabel("/ 00:00.000")
        self.lbl_time_total.setStyleSheet("color: #71767b; font-family: 'JetBrains Mono'; font-size: 16px;")
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
        
        # Speeds
        self.speed_btns = {}
        for s in [0.1, 0.25, 0.5, 1.0, 2.0]:
            btn = QPushButton(f"{s}x")
            btn.setFixedSize(60, 32)
            self.speed_btns[s] = btn
            btn.clicked.connect(lambda ch, val=s: self.set_granular_speed(val))
            ctrl_l.addWidget(btn)
        
        t_l.addLayout(ctrl_l)
        
        # Row 3: Quick Verdicts
        v_l = QHBoxLayout()
        self.btn_quick_valid = QPushButton("✓  Válido")
        self.btn_quick_valid.setObjectName("btn_quick_valid")
        self.btn_quick_null = QPushButton("✕  Nulo")
        self.btn_quick_null.setObjectName("btn_quick_null")
        self.btn_quick_review = QPushButton("⚑  Revisar")
        self.btn_quick_review.setObjectName("btn_quick_review")
        v_l.addWidget(self.btn_quick_valid, stretch=1)
        v_l.addWidget(self.btn_quick_null, stretch=1)
        v_l.addWidget(self.btn_quick_review, stretch=1)
        t_l.addLayout(v_l)
        
        self.video_area_layout.addWidget(self.transport_container)
        self.change_volume(50)
        self.update_speed_ui(1.0)

    def setup_sidebar(self):
        self.sidebar = QWidget()
        s_l = QVBoxLayout(self.sidebar)
        s_l.setContentsMargins(0, 0, 0, 0)
        v_g = QGroupBox("RESULTADO DA ARBITRAGEM")
        v_gl = QVBoxLayout(v_g)
        self.lbl_verdict_card = QLabel("AGUARDANDO")
        self.lbl_verdict_card.setObjectName("verdict_display")
        self.lbl_verdict_card.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_verdict_card.setMinimumHeight(140)
        v_gl.addWidget(self.lbl_verdict_card)
        s_l.addWidget(v_g)
        
        t_g = QGroupBox("FERRAMENTAS DE PRECISÃO")
        t_gl = QGridLayout(t_g)
        tools = [("Carregar", "📤", self.open_video), ("Câmera", "((•))", self.start_cam),
                 ("Calibrar", "📏", self.toggle_lane), ("Zoom", "🔍", self.toggle_zoom),
                 ("Loop", "🔁", None), ("Tela cheia", "⛶", self.toggle_fullscreen)]
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
        f_l.addWidget(QLabel("Pronto para análise. Pressione F11 para Tela Cheia."), alignment=Qt.AlignmentFlag.AlignLeft)
        self.root_layout.addWidget(self.footer)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Space"), self, self.toggle_pause)
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.header_frame.show()
            self.sidebar.show()
            self.footer.show()
            self.content_layout.setContentsMargins(24, 24, 24, 24)
            self.video_area_layout.addWidget(self.transport_container)
            self.transport_container.setProperty("class", "")
            self.transport_container.style().unpolish(self.transport_container)
            self.transport_container.style().polish(self.transport_container)
            self.transp_opacity.setOpacity(1.0)
        else:
            self.showFullScreen()
            self.header_frame.hide()
            self.sidebar.hide()
            self.footer.hide()
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.transport_container.setParent(self.video_container)
            self.transport_container.setProperty("class", "floating-transport")
            self.transport_container.style().unpolish(self.transport_container)
            self.transport_container.style().polish(self.transport_container)
            self.transport_container.show()
            self.reposition_fs_controls()
            self.controls_timeout.start()

    def reposition_fs_controls(self):
        if self.isFullScreen():
            margin = 40
            w = self.video_container.width() - (2 * margin)
            h = self.transport_container.height()
            self.transport_container.setGeometry(margin, self.video_container.height() - h - margin, w, h)

    def eventFilter(self, obj, event):
        if self.isFullScreen() and event.type() in [event.Type.MouseMove, event.Type.Enter]:
            self.show_fs_controls()
            self.controls_timeout.start()
        if obj == self.video_container and event.type() == event.Type.Resize:
            self.reposition_fs_controls()
        return super().eventFilter(obj, event)

    def show_fs_controls(self):
        self.transport_container.raise_()
        if self.transp_opacity.opacity() < 1.0:
            self.transp_anim.stop()
            self.transp_anim.setEndValue(1.0)
            self.transp_anim.start()

    def hide_controls(self):
        if not self.isFullScreen() or self.transport_container.underMouse():
            if self.isFullScreen(): self.controls_timeout.start()
            return
        self.transp_anim.stop()
        self.transp_anim.setEndValue(0.0)
        self.transp_anim.start()

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

    def update_verdict(self, verdict):
        self.lbl_verdict_card.setText(verdict.upper())
        colors = {"Válido": "#4cd964", "Inválido": "#e23b2a", "Inconclusivo": "#f0913a"}
        self.lbl_verdict_card.setStyleSheet(f"color: {colors.get(verdict, '#71767b')}; background: #161922; border: 1px solid #1a1c26;")

    def display_frame(self, frame):
        if self.video_stack.currentIndex() == 0: self.video_stack.setCurrentIndex(1)
        if frame is None: return
        if self.controller and hasattr(self.controller, 'bull_tracker'):
            frame = self.controller.bull_tracker.draw_tracking(frame, None, None)
        if hasattr(self, 'btn_zoom') and self.btn_zoom.isChecked():
            h, w = frame.shape[:2]; nw, nh = int(w/1.5), int(h/1.5); x, y = (w-nw)//2, (h-nh)//2; frame = frame[y:y+nh, x:x+nw]
        h, w, ch = frame.shape; q_img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_BGR888); pixmap = QPixmap.fromImage(q_img)
        self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))

    def update_proof_timer(self):
        self.proof_timer_val += 33; ms = self.proof_timer_val; s = (ms // 1000) % 60; m = (ms // (1000 * 60)) % 60; mil = ms % 1000
        self.lbl_proof_timer.setText(f"{m:02d}:{s:02d}.{mil:03d}")

    def toggle_proof_timer(self):
        if self.proof_timer.isActive(): self.proof_timer.stop(); self.btn_proof.setText("Iniciar")
        else: self.proof_timer.start(33); self.btn_proof.setText("Pausar")

    def load_stylesheet(self):
        try:
            with open("/home/juliodev/Downloads/Varquejada_System/ui/style.qss", "r") as f: self.setStyleSheet(f.read())
        except: pass

    def open_video(self): self.controller.open_video_file()
    def start_cam(self): self.controller.start_camera()
    def toggle_pause(self): self.controller.toggle_pause()
    def toggle_lane(self, checked): self.controller.toggle_lane_lock(checked)
    def toggle_zoom(self, checked): pass

if __name__ == "__main__":
    app = QApplication(sys.argv); window = MainWindow(); window.show(); sys.exit(app.exec())
