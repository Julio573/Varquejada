import cv2
import numpy as np
import logging
from ultralytics import YOLO
import os
import threading

class HorseTracker:
    """
    Módulo de Telemetria de Alta Performance.
    Otimizado para velocidade e precisão constante.
    """
    def __init__(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.lock = threading.Lock()
        
        # Modelo PRO
        model_pro = os.path.join(project_root, 'models/best.pt')
        model_base = os.path.join(project_root, 'yolo11n.pt')
        self.model = YOLO(model_pro if os.path.exists(model_pro) else model_base)
        self.model.to('cpu')
        
        # IA Config - Otimizada para Performance
        self.conf_threshold = 0.30
        self.imgsz = 320 # Reduzido para fluidez total (CPU processing)
        self.yolo_interval = 2 # Alivia a CPU (15 FPS de detecção com 30 FPS de interpolação)
        self.frame_count = 0
        
        # MEMÓRIA TEMPORAL
        self.tracked_horses = {} 
        self.next_id = 0
        self.max_lost_frames = 10 # Mais rigoroso
        
        # TELEMETRIA
        self.fps = 30.0
        self.ppm = None # Pixels Per Meter (Definido pela calibração)
        self.speed_buffer = {} 
        self.prev_centers = {} # {id: (cx, cy)}
        self.fall_coords = None

    def _calculate_iou(self, boxA, boxB):
        xA, yA = max(boxA[0], boxB[0]), max(boxA[1], boxB[1])
        xB, yB = min(boxA[0] + boxA[2], boxB[0] + boxB[2]), min(boxA[1] + boxA[3], boxB[1] + boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        iou = interArea / float(boxA[2]*boxA[3] + boxB[2]*boxB[3] - interArea + 1e-6)
        return iou

    def track(self, frame, fps=None):
        if frame is None: return None, None, False
        if fps: self.fps = fps
        self.frame_count += 1
        
        # 1. DETECÇÃO (IA) - Otimizada para Tempo Real
        new_detections = []
        # half=True para processamento 2x mais rápido em algumas CPUs/GPUs
        results = self.model(frame, conf=self.conf_threshold, imgsz=self.imgsz, verbose=False, half=False)
        if results and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                x, y, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                if int(box.cls[0]) == 0: continue
                new_detections.append({"bbox": [x, y, x2-x, y2-y], "conf": float(box.conf[0])})

        with self.lock:
            # 2. ASSOCIAÇÃO
            if new_detections:
                used_det = set()
                # Priorizar tracks existentes
                for tid, data in self.tracked_horses.items():
                    best_iou, match_idx = 0.2, None
                    for i, det in enumerate(new_detections):
                        if i in used_det: continue
                        iou = self._calculate_iou(data["bbox"], det["bbox"])
                        if iou > best_iou: best_iou, match_idx = iou, i
                    
                    if match_idx is not None:
                        data["bbox"] = new_detections[match_idx]["bbox"]
                        data["conf"], data["frames_lost"] = new_detections[match_idx]["conf"], 0
                        used_det.add(match_idx)
                    else:
                        data["frames_lost"] += 1

                for i, det in enumerate(new_detections):
                    if i not in used_det:
                        if not any(self._calculate_iou(det["bbox"], d["bbox"]) > 0.3 for d in self.tracked_horses.values()):
                            self.tracked_horses[self.next_id] = {"bbox": det["bbox"], "frames_lost": 0, "conf": det["conf"], "speed": 0.0}
                            self.next_id += 1
            else:
                for tid in self.tracked_horses: self.tracked_horses[tid]["frames_lost"] += 1

            # 3. VELOCIDADE E ESTABILIZAÇÃO (Filtros de Histerese e EMA Pesado)
            for tid in list(self.tracked_horses.keys()):
                data = self.tracked_horses[tid]
                if data["frames_lost"] > self.max_lost_frames:
                    self.tracked_horses.pop(tid); self.prev_centers.pop(tid, None); self.speed_buffer.pop(tid, None)
                    continue

                x, y, w, h = data["bbox"]
                
                # 1. ESTABILIZAÇÃO DE DIMENSÕES
                if "smooth_w" not in data:
                    data["smooth_w"] = float(w)
                    data["smooth_h"] = float(h)
                    # Âncora no corpo (Peito/Ombro ~85% da altura) - Evita ruído das patas
                    data["smooth_c"] = np.array([float(x + w/2.0), float(y + h * 0.85)])
                else:
                    alpha_size = 0.08 
                    data["smooth_w"] = alpha_size * w + (1.0 - alpha_size) * data["smooth_w"]
                    data["smooth_h"] = alpha_size * h + (1.0 - alpha_size) * data["smooth_h"]
                
                # 2. ESTABILIZAÇÃO DE POSIÇÃO (EMA + Histerese)
                curr_anchor = np.array([float(x + w/2.0), float(y + h * 0.85)])
                alpha_pos = 0.35 
                data["smooth_c"] = alpha_pos * curr_anchor + (1.0 - alpha_pos) * data["smooth_c"]
                
                # 3. CÁLCULO DE VELOCIDADE (Fórmula Corrigida com Perspectiva)
                if tid in self.prev_centers:
                    # Deslocamento
                    dx = data["smooth_c"][0] - self.prev_centers[tid][0]
                    dy = data["smooth_c"][1] - self.prev_centers[tid][1]
                    
                    # Se tivermos PPM (calibração), usamos ele. 
                    # Geralmente calibramos a largura da pista (X), então usamos esse PPM.
                    if self.ppm:
                        fator_escala = 1.0 / self.ppm
                        # Em vaquejada, o movimento é predominantemente horizontal (X)
                        # O fator 2.0 no dy tenta compensar a compressão da profundidade se não houver homografia
                        dist_px = np.sqrt(dx**2 + (dy * 2.0)**2)
                    else:
                        # Fallback: Estimativa baseada na altura média do cavalo (1.65m)
                        fator_escala = 1.65 / max(1.0, data["smooth_h"])
                        dist_px = np.sqrt(dx**2 + (dy * 2.5)**2)
                    
                    # Deadzone Rigoroso: Elimina tremor de passos lentos (< 1.2px = parado)
                    if dist_px < 1.2: dist_px = 0.0 
                    
                    delta_t = 1.0 / self.fps
                    
                    v_ms = (dist_px * fator_escala) / delta_t
                    v_kmh_raw = v_ms * 3.6
                    
                    # Filtro de Inércia Física: Cavalos não aceleram instantaneamente
                    if tid not in self.speed_buffer: self.speed_buffer[tid] = []
                    self.speed_buffer[tid].append(v_kmh_raw)
                    if len(self.speed_buffer[tid]) > 25: self.speed_buffer[tid].pop(0)
                    
                    # Suavização por Miolo Estável (descarta picos de jitter)
                    if len(self.speed_buffer[tid]) > 10:
                        filtered = sorted(self.speed_buffer[tid])[4:-4]
                        new_speed = np.mean(filtered)
                    else:
                        new_speed = np.mean(self.speed_buffer[tid])
                    
                    # Aplica a velocidade suavizada
                    data["speed"] = new_speed
                        
                    # Registro de Estatísticas
                    data["max_speed"] = max(data.get("max_speed", 0.0), data["speed"])
                    data["speed_sum"] = data.get("speed_sum", 0.0) + data["speed"]
                    data["speed_count"] = data.get("speed_count", 0) + 1
                    data["avg_speed"] = data["speed_sum"] / data["speed_count"]
                    
                    # Acumulador de Distância (metros)
                    # dist_px corrigida * fator_escala = distância real percorrida neste frame
                    dist_real_m = dist_px * fator_escala
                    data["dist_total_m"] = data.get("dist_total_m", 0.0) + dist_real_m
                
                self.prev_centers[tid] = data["smooth_c"].copy()
                
                # Atualiza a BBOX final (Baseada na âncora corrigida)
                sw, sh = int(data["smooth_w"] * 1.25), int(data["smooth_h"] * 1.10)
                scx, scy = int(data["smooth_c"][0]), int(data["smooth_c"][1] + (data["smooth_h"] * 0.15))
                data["final_bbox"] = [scx - sw//2, scy - sh, sw, sh]

            if self.tracked_horses:
                best_tid = max(self.tracked_horses, key=lambda k: self.tracked_horses[k]["conf"])
                b = self.tracked_horses[best_tid]["final_bbox"]
                return b, (int(b[0]+b[2]/2), int(b[1]+b[3])), False
            
        return None, None, False

    def reset(self):
        with self.lock:
            self.tracked_horses = {}; self.speed_buffer = {}; self.prev_centers = {}; self.next_id = 0

    def draw_tracking(self, frame, horse_bbox, center):
        if frame is None: return frame
        with self.lock:
            for tid, data in self.tracked_horses.items():
                # USAR A BBOX SUAVIZADA PARA O DESENHO
                if "final_bbox" not in data: continue
                x, y, w, h = data["final_bbox"]
                
                speed = data.get("speed", 0.0)
                color_accent = (11, 158, 245) 
                
                # Badge de Telemetria (Centralizado e com Marcador)
                font = cv2.FONT_HERSHEY_SIMPLEX
                speed_str = f"{speed:.1f}"
                (tw, th), _ = cv2.getTextSize(speed_str, font, 0.7, 2)
                
                # Dimensões e posição do Badge
                bw, bh = tw + 65, 35
                bx = x + w//2 - bw//2
                by = y - 50 # Posição vertical mais próxima
                
                # Linha de Marcador (Apontando para o cavalo)
                cv2.line(frame, (x + w//2, by + bh), (x + w//2, y - 2), color_accent, 2, cv2.LINE_AA)
                cv2.circle(frame, (x + w//2, y - 2), 3, color_accent, -1, cv2.LINE_AA)
                
                # Desenho do Badge
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (15, 18, 22), -1)
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (60, 65, 70), 1, cv2.LINE_AA)
                cv2.rectangle(frame, (bx, by), (bx + 4, by + bh), color_accent, -1)
                
                # Texto da Velocidade Instantânea
                cv2.putText(frame, speed_str, (bx + 12, by + bh - 10), font, 0.7, (255,255,255), 2, cv2.LINE_AA)
                cv2.putText(frame, "KM/H", (bx + 18 + tw, by + bh - 12), font, 0.4, color_accent, 1, cv2.LINE_AA)
                
                # Velocidade Máxima (Pequeno destaque inferior)
                max_speed = data.get("max_speed", 0.0)
                max_str = f"MAX: {max_speed:.1f}"
                cv2.putText(frame, max_str, (bx + 4, by + bh + 12), font, 0.35, (200, 200, 200), 1, cv2.LINE_AA)
            
        return frame
