import os

# Paleta de Cores
COLOR_BG_MAIN = "#060B16"
COLOR_SURFACE = "#0E1628"
COLOR_SURFACE_LIGHT = "#121D33"
COLOR_ORANGE = "#FF8C00"
COLOR_ORANGE_HOVER = "#FFA733"
COLOR_GREEN = "#4DFF88"
COLOR_TEXT_PRIMARY = "#FFFFFF"
COLOR_TEXT_SECONDARY = "rgba(255, 255, 255, 0.65)"
COLOR_BORDER = "rgba(255, 255, 255, 0.08)"
COLOR_ICON_CONTAINER = "#131E34"
COLOR_ICON_BORDER = "#1D3358"
COLOR_CARD_BG = "#101A2F"
COLOR_CARD_BORDER = "#1E335A"
COLOR_CLOSE_HOVER = "#E53935"
COLOR_CLOSE_PRESSED = "#C62828"

# Fontes
FONT_FAMILY = "Inter, Segoe UI, Arial"

# Dimensões
HEADER_HEIGHT = 96
CARD_WIDTH = 270
CARD_HEIGHT = 78
ICON_SIZE = 48
CLOSE_BTN_SIZE = 36

# Caminhos de Assets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
QSS_PATH = os.path.join(os.path.dirname(__file__), "header_style.qss")

# Mapeamento de Ícones
ICON_MAP = {
    "cronometro": os.path.join(ICONS_DIR, "Imagem-colada-_2_.svg"),
    "distancia": os.path.join(ICONS_DIR, "Imagem-colada-_2_.svg"),
    "calendario": os.path.join(ICONS_DIR, "Imagem-colada-_2_.svg"),
    "relogio": os.path.join(ICONS_DIR, "Imagem-colada-_2_.svg"),
    "logo": os.path.join(ICONS_DIR, "Imagem-colada-_2_.svg")
}
