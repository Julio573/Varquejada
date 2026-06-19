import cv2
import numpy as np

class AutoCalibrator:
    """
    Detecta automaticamente as linhas da pista de vaquejada para calibrar o PPM.
    Assume que a largura da pista (distância entre as linhas de cal) é de 1.5m.
    """
    def __init__(self):
        # Limites HSV para a cal branca (ajustáveis)
        self.lower_white = np.array([0, 0, 180])
        self.upper_white = np.array([180, 50, 255])
        self.min_area = 500

    def calibrate(self, frame):
        """
        Analisa o frame para encontrar a largura da pista e a geometria das linhas.
        Retorna dicionário com PPM e Pontos de Referência para Homografia.
        """
        if frame is None: return None
        
        h_f, w_f = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_white, self.upper_white)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 15)) # Kernel vertical para faixas
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        lane_lines = []
        for cnt in contours:
            if cv2.contourArea(cnt) < 400: continue
            # Aproxima por uma linha reta
            [vx, vy, x, y] = cv2.fitLine(cnt, cv2.DIST_L2, 0, 0.01, 0.01)
            # Verifica se é predominantemente vertical
            if abs(vy) > abs(vx) * 1.5:
                lane_lines.append({'x': int(x), 'v': (vx, vy), 'cnt': cnt})
        
        if len(lane_lines) >= 2:
            lane_lines.sort(key=lambda l: l['x'])
            # Pegamos as duas linhas mais distantes que representam a pista
            l1, l2 = lane_lines[0], lane_lines[-1]
            
            # Calcula distância média na altura central
            dist_px = abs(l1['x'] - l2['x'])
            if dist_px > 100:
                ppm = dist_px / 1.5
                return {
                    'ppm': ppm,
                    'l1_x': l1['x'],
                    'l2_x': l2['x'],
                    'w': w_f, 'h': h_f
                }
                
        return None
