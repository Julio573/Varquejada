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
        self.conf_threshold = 0.50
        self.imgsz = 320 # Reduzido para fluidez total (CPU processing)
        self.yolo_interval = 1 # Alivia a CPU (15 FPS de detecção com 30 FPS de interpolação)
        self.frame_count = 0
        
        # MEMÓRIA TEMPORAL
        self.tracked_horses = {} 
        self.next_id = 0
        self.max_lost_frames = 2 # Mais rigoroso
        
        # TELEMETRIA PRO
        self.fps = 30.0
        self.ppm = None 
        self.homography = None # Matriz de Homografia
        self.speed_buffer = {} 
        self.prev_pos_world = {} # Posições no mapa mundial (metros)
        self.prev_frame_gray = None 
        self.camera_motion = np.array([0.0, 0.0])

    def setup_homography(self, calib_data):
        """Constrói a matriz de homografia para projetar a imagem no plano real."""
        # Largura real assumida: 1.5m
        w, h = calib_data['w'], calib_data['h']
        l1x, l2x = calib_data['l1_x'], calib_data['l2_x']
        
        # Pontos de origem na imagem (Trapézio da pista)
        src_pts = np.float32([
            [l1x + (l2x-l1x)*0.2, h*0.3], [l2x - (l2x-l1x)*0.2, h*0.3], # Fundo
            [l1x, h*0.9], [l2x, h*0.9] # Frente
        ])
        
        # Pontos de destino no mundo real (em CM para maior precisão: 1.5m -> 150cm)
        # Comprimento virtual de 20 metros (2000cm)
        dst_pts = np.float32([
            [0, 0], [150, 0],
            [0, 2000], [150, 2000]
        ])
        
        self.homography = cv2.getPerspectiveTransform(src_pts, dst_pts)
        self.ppm = calib_data['ppm']

    def _get_camera_motion(self, frame_gray):
        """Calcula o movimento da câmera usando Optical Flow Robusto."""
        if self.prev_frame_gray is None:
            self.prev_frame_gray = frame_gray
            return np.array([0.0, 0.0])
        
        h, w = frame_gray.shape
        roi = frame_gray[int(h*0.1):int(h*0.4), :]
        p0 = cv2.goodFeaturesToTrack(roi, maxCorners=40, qualityLevel=0.1, minDistance=10)
        
        motion = np.array([0.0, 0.0])
        if p0 is not None:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(roi, frame_gray[int(h*0.1):int(h*0.4), :], p0, None)
            if p1 is not None:
                good_new = p1[st == 1]
                good_old = p0[st == 1]
                if len(good_new) > 5:
                    # Estimador robusto: Mediana das diferenças (ignora outliers)
                    motion = np.median(good_new - good_old, axis=0)
        
        self.prev_frame_gray = frame_gray.copy()
        return motion

    def track(self, frame, fps=None):
        if frame is None: return None, None, False
        if fps: self.fps = fps
        self.frame_count += 1
        
        # 0. ESTABILIZAÇÃO DE CÂMERA
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.camera_motion = self._get_camera_motion(frame_gray)
        
        # 1. RASTREAMENTO (ByteTrack)
        results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", 
                                  conf=self.conf_threshold, imgsz=self.imgsz, verbose=False)
        
        if not results or not results[0].boxes or results[0].boxes.id is None:
            with self.lock:
                for tid in list(self.tracked_horses.keys()):
                    self.tracked_horses[tid]["frames_lost"] += 1
            return None, None, False

        boxes = results[0].boxes
        ids = boxes.id.cpu().numpy().astype(int)
        coords = boxes.xyxy.cpu().numpy().astype(int)

        with self.lock:
            active_ids = set()
            for i, tid in enumerate(ids):
                x, y, x2, y2 = coords[i]
                w, h = x2 - x, y2 - y
                active_ids.add(tid)
                
                if tid not in self.tracked_horses:
                    self.tracked_horses[tid] = {"bbox": [x, y, w, h], "frames_lost": 0, "conf": boxes.conf[i].cpu().item(), "speed": 0.0}
                else:
                    self.tracked_horses[tid]["bbox"] = [x, y, w, h]
                    self.tracked_horses[tid]["frames_lost"] = 0

            for tid in list(self.tracked_horses.keys()):
                data = self.tracked_horses[tid]
                if tid not in active_ids: data["frames_lost"] += 1
                if data["frames_lost"] > self.max_lost_frames:
                    self.tracked_horses.pop(tid); self.prev_pos_world.pop(tid, None); self.speed_buffer.pop(tid, None)
                    continue

                x, y, w, h = data["bbox"]
                
                # 1. SUAVIZAÇÃO DE ANCORAGEM (Pés)
                curr_p = np.array([float(x + w/2.0), float(y + h)])
                if "smooth_c" not in data:
                    data["smooth_c"] = curr_p
                    data["smooth_w"], data["smooth_h"] = float(w), float(h)
                else:
                    data["smooth_c"] = 0.20 * curr_p + 0.80 * data["smooth_c"]
                    data["smooth_w"] = 0.1 * w + 0.9 * data["smooth_w"]
                    data["smooth_h"] = 0.1 * h + 0.9 * data["smooth_h"]
                
                # 2. PROJEÇÃO WORLD (Bird's Eye View)
                # Aplicamos a Homografia para converter (X,Y) da imagem para metros reais
                pos_img = np.array([[[data["smooth_c"][0], data["smooth_c"][1]]]], dtype=np.float32)
                if self.homography is not None:
                    # Converte de coordenadas da imagem para o plano virtual (em cm)
                    pos_world = cv2.perspectiveTransform(pos_img, self.homography)[0][0]
                    curr_pos_m = pos_world / 100.0 # Transforma cm para metros
                else:
                    # Fallback robusto por escala de altura
                    escala = 1.65 / max(1.0, data["smooth_h"])
                    curr_pos_m = data["smooth_c"] * escala

                # 3. CÁLCULO DE VELOCIDADE (Geometria Pura)
                if tid in self.prev_pos_world:
                    # Distância real percorrida no plano terrestre
                    dist_real_m = np.linalg.norm(curr_pos_m - self.prev_pos_world[tid])
                    
                    # Compensação de Câmera em Metros
                    if self.ppm:
                        cam_m = np.linalg.norm(self.camera_motion) / self.ppm
                        dist_real_m = max(0, dist_real_m - cam_m * 0.15) 
                    
                    if dist_real_m < 0.02: dist_real_m = 0.0 # Deadzone
                    
                    v_kmh_raw = (dist_real_m * self.fps) * 3.6
                    
                    # FILTRAGEM ESTATÍSTICA
                    if tid not in self.speed_buffer: self.speed_buffer[tid] = []
                    self.speed_buffer[tid].append(v_kmh_raw)
                    if len(self.speed_buffer[tid]) > 15: self.speed_buffer[tid].pop(0)
                    
                    v_target = np.median(self.speed_buffer[tid])
                    
                    # Limite Físico de Aceleração
                    prev_v = data.get("speed", 0.0)
                    accel_limit = 10.0 / self.fps 
                    if abs(v_target - prev_v) > accel_limit:
                        v_target = prev_v + np.sign(v_target - prev_v) * accel_limit
                    
                    data["speed"] = 0.3 * v_target + 0.7 * prev_v
                    data["max_speed"] = max(data.get("max_speed", 0.0), data["speed"])
                    data["dist_total_m"] = data.get("dist_total_m", 0.0) + dist_real_m
                
                self.prev_pos_world[tid] = curr_pos_m.copy()
                
                # BBOX FINAL
                sw, sh = int(data["smooth_w"] * 1.05), int(data["smooth_h"] * 1.05)
                data["final_bbox"] = [int(data["smooth_c"][0] - sw/2), int(data["smooth_c"][1] - sh), sw, sh]

            if self.tracked_horses:
                best_tid = max(self.tracked_horses, key=lambda k: self.tracked_horses[k]["conf"])
                b = self.tracked_horses[best_tid]["final_bbox"]
                return b, (int(b[0]+b[2]/2), int(b[1]+b[3])), False
            
        return None, None, False

    def reset(self):
        with self.lock:
            self.tracked_horses = {}
            self.speed_buffer = {}
            self.prev_pos_world = {}
            self.prev_frame_gray = None
            self.next_id = 0

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
