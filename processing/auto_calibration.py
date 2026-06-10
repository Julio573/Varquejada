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
        Analisa o frame para encontrar a largura da pista em pixels.
        Retorna o PPM (Pixels Per Meter) ou None se falhar.
        """
        if frame is None: return None
        
        # 1. Segmentação da cor branca (cal)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_white, self.upper_white)
        
        # Limpeza morfológica
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # 2. Encontrar contornos das faixas
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar contornos verticais/longos que pareçam faixas
        lane_candidates = []
        for cnt in contours:
            if cv2.contourArea(cnt) < self.min_area: continue
            
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = h / float(w)
            
            # Faixas de vaquejada costumam ser mais altas que largas na perspectiva da câmera
            if aspect_ratio > 2.0:
                lane_candidates.append({'bbox': [x, y, w, h], 'center': x + w//2})
        
        # Precisamos de pelo menos duas faixas para medir a distância entre elas
        if len(lane_candidates) >= 2:
            # Ordenar por posição X
            lane_candidates.sort(key=lambda x: x['center'])
            
            # Pegar as duas faixas mais prováveis (ex: as duas maiores ou mais centrais)
            # Aqui pegamos a distância entre os centros das duas faixas detectadas
            dist_px = abs(lane_candidates[0]['center'] - lane_candidates[1]['center'])
            
            if dist_px > 50: # Evitar falsos positivos muito próximos
                ppm = dist_px / 1.5 # 1.5 metros é a largura padrão
                return ppm
                
        return None
