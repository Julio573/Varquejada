import cv2
import numpy as np
import logging
from ultralytics import YOLO
import os

class BullTracker:
    """
    Módulo de Processamento: Rastreamento Multi-Objeto (Boi e Cavalos)
    usando YOLOv11 Treinado com persistência de detecção.
    """
    def __init__(self):
        # Base do projeto para caminhos relativos
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Ordem de preferência dos modelos:
        # 1. Modelo da rodada FINAL (se já existir algo bom)
        # 2. Modelo da rodada PRO-2 (já copiado para a pasta models/)
        # 3. Modelo base YOLO11n
        
        model_final = os.path.join(project_root, 'runs/detect/varquejada_yolo11_final/weights/best.pt')
        model_pro = os.path.join(project_root, 'models/best.pt')
        model_base = os.path.join(project_root, 'yolo11n.pt')

        if os.path.exists(model_final):
            self.model = YOLO(model_final)
            logging.info("YOLOv11: Carregado modelo da rodada FINAL.")
        elif os.path.exists(model_pro):
            self.model = YOLO(model_pro)
            logging.info("YOLOv11: Carregado modelo PRO de alta precisão (pasta models/).")
        else:
            self.model = YOLO(model_base)
            logging.warning("YOLOv11: Modelos treinados não encontrados, usando modelo base.")
        
        # Otimização para CPU: Limita threads para não travar o sistema
        import torch
        torch.set_num_threads(4) # Reserva núcleos para o vídeo rodar liso
        self.model.to('cpu')
        
        self.fall_detected = False
        self.fall_coords = None
        self.prev_bull_center = None
        self.prev_bull_dim = None
        
        # Parâmetros de Performance
        self.conf_threshold = 0.20
        self.yolo_interval = 10 # Roda IA a cada 10 frames (3x por segundo) para fluidez total
        self.frame_count = 0
        self.imgsz = 320 # Reduzido de 640 para 320 (Ganho de 4x na velocidade da CPU)
        
        self.current_detections = []

    def track(self, frame):
        if frame is None: return None, None, False
        self.frame_count += 1
        
        # 1. Inferência YOLO (Apenas em intervalos ou se a lista estiver vazia)
        if self.frame_count % self.yolo_interval == 0 or not self.current_detections:
            # Rodar inferência com tamanho reduzido para velocidade
            results = self.model(frame, conf=self.conf_threshold, imgsz=self.imgsz, verbose=False)
            new_detections = []
            if results and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = "BOI" if cls == 0 else "CAVALO"
                    bbox = [int(x1), int(y1), int(x2-x1), int(y2-y1)]
                    
                    new_detections.append({
                        "bbox": bbox,
                        "cls": cls,
                        "conf": conf,
                        "label": label,
                        "velocity": [0, 0] # Para predição futura
                    })
            self.current_detections = new_detections
        else:
            # 2. Predição de Movimento (Mantém os boxes se movendo enquanto a IA "descansa")
            # Isso evita que os boxes fiquem "presos" ou piscando
            for det in self.current_detections:
                x, y, w, h = det['bbox']
                # Mantemos o box na posição, a IA vai corrigir no próximo ciclo
                # (Otimização: em CPU, predição linear simples é melhor que trackers OpenCV)
                pass

        # 3. Lógica de Queda (Focada no Boi)
        bull_bbox = None
        bull_center = None
        is_falling = False
        
        bulls = [d for d in self.current_detections if d['cls'] == 0]
        if bulls:
            best_bull = max(bulls, key=lambda x: x['conf'])
            bull_bbox = best_bull['bbox']
            x, y, w, h = bull_bbox
            bull_center = (int(x + w/2), int(y + h/2))
            
            is_falling = self._check_fall_logic(bull_center, (w, h))
            if is_falling and not self.fall_detected:
                self.fall_detected = True
                self.fall_coords = bull_center
            
            self.prev_bull_center = bull_center
            self.prev_bull_dim = (w, h)

        return bull_bbox, bull_center, is_falling

    def _check_fall_logic(self, center, dim):
        if self.prev_bull_center is None or self.prev_bull_dim is None: return False
        dx, dy = center[0] - self.prev_bull_center[0], center[1] - self.prev_bull_center[1]
        velocity = np.sqrt(dx**2 + dy**2)
        expansion = (dim[0]*dim[1]) / (self.prev_bull_dim[0]*self.prev_bull_dim[1])
        return expansion > 1.35 and velocity < 8

    def reset(self):
        self.fall_detected = False
        self.fall_coords = None
        self.prev_bull_center = None
        self.prev_bull_dim = None
        self.current_detections = []

    def draw_tracking(self, frame, bull_bbox, center):
        # Desenha TODAS as detecções atuais (Boi e Cavalos)
        for det in self.current_detections:
            x, y, w, h = det['bbox']
            cls = det['cls']
            color = (255, 191, 0) # Âmbar padrão
            
            if cls == 0: # Boi
                if self.fall_detected:
                    color = (0, 0, 255) # Vermelho se caiu
                    label = "QUEDA!"
                else:
                    color = (0, 255, 0) # Verde para boi ativo
                    label = "BOI"
            else:
                color = (255, 255, 255) # Branco para cavalos
                label = "CAVALO"

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, f"{label} {det['conf']:.2f}", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame

if __name__ == "__main__":
    tracker = BullTracker()
    print("Módulo BullTracker com YOLOv11 Treinado inicializado.")
