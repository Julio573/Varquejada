from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from . import constants
from .cards import HeaderCard

class HeaderWidget(QFrame):
    close_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Header")
        self.setFixedHeight(constants.HEADER_HEIGHT)
        
        # Aplicar estilo externo
        self.load_stylesheet()
        
        # Layout Principal
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(32, 0, 32, 0)
        self.layout.setSpacing(24)
        
        # ─── Área Esquerda (Logo) ──────────────────────────────────────────
        self.logo_container = QFrame()
        self.logo_layout = QVBoxLayout(self.logo_container)
        self.logo_layout.setContentsMargins(0, 0, 0, 0)
        self.logo_layout.setSpacing(0)
        self.logo_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.logo_label = QLabel('<span style="color: #FFFFFF;">VAQ</span><span style="color: #FF8C00;">VISION</span>')
        self.logo_label.setObjectName("LogoLabel")
        
        self.subtitle_label = QLabel("Sistema de Medição de Velocidade")
        self.subtitle_label.setObjectName("LogoSubtitle")
        
        self.logo_layout.addWidget(self.logo_label)
        self.logo_layout.addWidget(self.subtitle_label)
        
        self.layout.addWidget(self.logo_container)
        
        # Espaçador entre Logo e Cards
        self.layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # ─── Área Central (Cards) ──────────────────────────────────────────
        self.card_time = HeaderCard("TEMPO PERCORRIDO", "00:00.0", "hh:mm:ss.sss", "cronometro")
        self.card_dist = HeaderCard("DISTÂNCIA PERCORRIDA", "0.0 m", "metros", "distancia", constants.COLOR_GREEN)
        self.card_date = HeaderCard("DATA ATUAL", "12 de junho de 2026", "sexta-feira", "calendario")
        self.card_hour = HeaderCard("HORA LOCAL", "08:18:11", "GMT-3", "relogio")
        
        self.layout.addWidget(self.card_time)
        self.layout.addWidget(self.card_dist)
        self.layout.addWidget(self.card_date)
        self.layout.addWidget(self.card_hour)
        
        # Espaçador entre Cards e Botão Fechar
        self.layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # ─── Área Direita (Botão Fechar) ───────────────────────────────────
        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("CloseButton")
        self.close_button.setFixedSize(constants.CLOSE_BTN_SIZE, constants.CLOSE_BTN_SIZE)
        self.close_button.clicked.connect(self.close_requested.emit)
        
        self.layout.addWidget(self.close_button)

    def load_stylesheet(self):
        if hasattr(constants, 'QSS_PATH') and constants.QSS_PATH:
            with open(constants.QSS_PATH, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def update_telemetry(self, time_val, dist_val):
        self.card_time.update_value(time_val)
        self.card_dist.update_value(f"{dist_val:.1f} m")

    def update_datetime(self, date_val, weekday_val, hour_val):
        self.card_date.update_value(date_val, weekday_val)
        self.card_hour.update_value(hour_val)
