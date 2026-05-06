import cv2
import numpy as np
import logging

class LaneDetector:
    """
    Módulo de Processamento: Responsável por detectar a faixa de pontuação
    por meio de segmentação de cor no espaço HSV com persistência de dados.
    """
    def __init__(self):
        # Definição inicial do range HSV para o branco (cal)
        self.lower_white = np.array([0, 0, 180]) # Ajustado para ser levemente mais tolerante
        self.upper_white = np.array([180, 60, 255])
        
        # Parâmetros de filtragem
        self.min_area = 4000  # Reduzido ligeiramente para maior sensibilidade inicial
        
        # Persistência e Estado
        self.last_valid_bbox = None
        self.is_locked = False
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("LaneDetector")

    def lock_lane(self):
        """Trava as coordenadas atuais da faixa."""
        if self.last_valid_bbox:
            self.is_locked = True
            self.logger.info(f"Faixa travada em: {self.last_valid_bbox}")
            return True
        return False

    def unlock_lane(self):
        """Destrava a detecção para permitir nova calibração."""
        self.is_locked = False
        self.logger.info("Faixa destravada. Redetectando...")

    def detect(self, frame):
        """
        Detecta a faixa no frame. Se estiver travada, retorna a anterior.
        Se a detecção atual falhar, retorna a última válida como fallback.
        """
        if self.is_locked and self.last_valid_bbox:
            return self.last_valid_bbox

        if frame is None:
            return self.last_valid_bbox

        # 1. Conversão para espaço HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 2. Aplicação da máscara de cor
        mask = cv2.inRange(hsv, self.lower_white, self.upper_white)

        # 3. Limpeza de ruído (Morfologia)
        kernel = np.ones((7, 7), np.uint8) # Kernel maior para suavizar contornos
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 4. Extração de contornos
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        current_bbox = None
        if contours:
            # 5. Selecionar o maior contorno
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)

            # 6. Validação
            if area >= self.min_area:
                x, y, w, h = cv2.boundingRect(largest_contour)
                current_bbox = (x, y, w, h)
                self.last_valid_bbox = current_bbox
            else:
                self.logger.debug(f"Detecção fraca ignorada (área: {area})")

        # Fallback: Se não detectou nada válido agora, usa a última
        if current_bbox is None and self.last_valid_bbox:
            # self.logger.debug("Usando fallback da última faixa válida")
            return self.last_valid_bbox
            
        return current_bbox

    def draw_lane(self, frame, bbox):
        """Desenha a faixa detectada no frame para visualização."""
        if bbox:
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, "FAIXA DETECTADA", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame

if __name__ == "__main__":
    # Teste rápido com frame vazio (preto)
    detector = LaneDetector()
    test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    # Simular uma faixa branca
    cv2.rectangle(test_frame, (400, 600), (900, 700), (255, 255, 255), -1)
    
    result = detector.detect(test_frame)
    if result:
        print(f"Faixa detectada em: {result}")
        test_frame = detector.draw_lane(test_frame, result)
        # cv2.imshow("Teste", test_frame) # Comentado pois não há display
    else:
        print("Falha na detecção ou status inconclusivo.")
