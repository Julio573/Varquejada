from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtGui import QColor
import os
from . import constants

class HeaderCard(QFrame):
    def __init__(self, title, value, subtext, icon_key, value_color=None):
        super().__init__()
        self.setObjectName("HeaderCard")
        self.setFixedSize(constants.CARD_WIDTH, constants.CARD_HEIGHT)
        
        # Layout principal do card
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(16)
        
        # Container do Ícone
        self.icon_container = QFrame()
        self.icon_container.setObjectName("IconContainer")
        self.icon_container.setFixedSize(constants.ICON_SIZE, constants.ICON_SIZE)
        
        self.icon_layout = QVBoxLayout(self.icon_container)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.svg_widget = QSvgWidget()
        icon_path = constants.ICON_MAP.get(icon_key, "")
        if os.path.exists(icon_path):
            self.svg_widget.load(icon_path)
        else:
            # Placeholder se não encontrar
            pass
        self.svg_widget.setFixedSize(24, 24)
        self.icon_layout.addWidget(self.svg_widget)
        
        # Container de Texto
        self.text_container = QFrame()
        self.text_layout = QVBoxLayout(self.text_container)
        self.text_layout.setContentsMargins(0, 0, 0, 0)
        self.text_layout.setSpacing(2)
        self.text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")
        
        self.value_label = QLabel(value)
        self.value_label.setObjectName("CardValue")
        if value_color:
            self.value_label.setStyleSheet(f"color: {value_color};")
            
        self.subtext_label = QLabel(subtext)
        self.subtext_label.setObjectName("CardSubtext")
        
        self.text_layout.addWidget(self.title_label)
        self.text_layout.addWidget(self.value_label)
        self.text_layout.addWidget(self.subtext_label)
        
        # Adiciona ao layout principal
        self.main_layout.addWidget(self.icon_container)
        self.main_layout.addWidget(self.text_container)
        
        # Efeito de Sombra
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

    def update_value(self, value, subtext=None):
        self.value_label.setText(value)
        if subtext:
            self.subtext_label.setText(subtext)
