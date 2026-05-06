import cv2
import logging

class DecisionModule:
    """
    Módulo de Decisão: Analisa a posição da queda em relação à faixa
    e emite o veredicto final.
    """
    def __init__(self, margin=5):
        self.margin = margin  # Margem de tolerância em pixels
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("DecisionModule")

    def evaluate(self, fall_coords, lane_bbox):
        """
        Avalia se a queda foi dentro da faixa.
        fall_coords: (x, y) do centro do boi na queda
        lane_bbox: (x, y, w, h) da faixa detectada
        
        Retorna: "Válido", "Inválido" ou "Inconclusivo"
        """
        if fall_coords is None or lane_bbox is None:
            return "Inconclusivo"

        fx, fy, fw, fh = lane_bbox
        bx, by = fall_coords

        # Limites da faixa
        lane_left = fx
        lane_right = fx + fw
        lane_top = fy
        lane_bottom = fy + fh

        # Verificação com margem (Casos de borda)
        is_on_border = (
            abs(bx - lane_left) <= self.margin or
            abs(bx - lane_right) <= self.margin or
            abs(by - lane_top) <= self.margin or
            abs(by - lane_bottom) <= self.margin
        )

        if is_on_border:
            return "Inconclusivo"

        # Verificação geométrica (Dentro/Fora)
        is_inside = (
            lane_left < bx < lane_right and
            lane_top < by < lane_bottom
        )

        if is_inside:
            return "Válido"
        else:
            return "Inválido"

    def apply_overlay(self, frame, verdict, fall_coords, lane_bbox):
        """
        Desenha o veredicto e as marcações visuais no frame.
        """
        if frame is None:
            return None

        # Cores (BGR)
        colors = {
            "Válido": (0, 255, 0),      # Verde
            "Inválido": (0, 0, 255),    # Vermelho
            "Inconclusivo": (0, 255, 255) # Amarelo
        }
        
        color = colors.get(verdict, (255, 255, 255))

        # 1. Desenha a faixa (se existir)
        if lane_bbox:
            lx, ly, lw, lh = lane_bbox
            cv2.rectangle(frame, (lx, ly), (lx + lw, ly + lh), color, 2)

        # 2. Desenha o ponto da queda
        if fall_coords:
            cv2.circle(frame, fall_coords, 8, color, -1)
            cv2.drawMarker(frame, fall_coords, color, cv2.MARKER_TILTED_CROSS, 15, 2)

        # 3. Banner de Veredicto
        cv2.rectangle(frame, (0, 0), (300, 60), (0, 0, 0), -1) # Fundo preto
        cv2.putText(frame, f"VAR: {verdict}", (10, 45), 
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, color, 2)

        return frame

if __name__ == "__main__":
    # Teste estrutural
    dm = DecisionModule()
    lane = (400, 500, 400, 100) # Faixa exemplo
    fall = (600, 550)           # Queda dentro
    
    verdict = dm.evaluate(fall, lane)
    print(f"Veredicto teste: {verdict}")
