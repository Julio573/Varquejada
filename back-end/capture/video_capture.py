import cv2
import threading
import logging
import time
import queue

from PyQt6.QtCore import QObject, pyqtSignal

class VideoCapture(QObject):
    """
    Módulo de Captura: Responsável pela entrada do vídeo.
    Emite o sinal frame_ready diretamente para a UI para garantir FPS constante.
    """
    frame_ready = pyqtSignal(object)

    def __init__(self, source=0, target_res=(1280, 720)):
        super().__init__()
        self.source = source
        self.target_res = target_res
        self.cap = None
        self.running = False
        self.paused = False
        self.frame = None
        self.frame_count = 0
        self.queue = None 
        self.lock = threading.Lock() 
        self.cap_lock = threading.Lock() 
        self.thread = None
        self.speed = 1.0
        self.fps = 30.0
            
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("VideoCapture")

    def start(self):
        """Inicia a thread. A abertura REAL da câmera acontece dentro da thread para não travar a UI."""
        self.running = True
        self.paused = False
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return True

    def _capture_loop(self):
        """Loop interno de captura executado na thread com controle de tempo e velocidade."""
        # 1. ABERTURA ASSÍNCRONA (Garante que a UI não trave)
        with self.cap_lock:
            try:
                # No Linux, forçar V4L2 costuma ser muito mais estável para câmeras USB
                if isinstance(self.source, int):
                    self.cap = cv2.VideoCapture(self.source, cv2.CAP_V4L2)
                else:
                    self.cap = cv2.VideoCapture(self.source)

                if not self.cap or not self.cap.isOpened():
                    self.logger.error(f"Falha ao abrir fonte: {self.source}")
                    self.running = False
                    return

                # Configurações de hardware (opcional, ajuda na estabilidade)
                if isinstance(self.source, int):
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_res[0])
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_res[1])

                # Obtém propriedades iniciais
                source_fps = self.cap.get(cv2.CAP_PROP_FPS)
                if source_fps > 5 and source_fps < 120: 
                    self.fps = source_fps
                
                self.logger.info(f"Câmera/Vídeo OK: {self.source} ({self.fps:.1f} FPS)")
            except Exception as e:
                self.logger.error(f"Erro ao acessar hardware: {e}")
                self.running = False
                return

        # 2. LOOP DE CAPTURA
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            # Controle de tempo
            with self.cap_lock:
                fps = self.fps
                speed = self.speed
            
            delay = (1.0 / fps) / speed
            start_time = time.time()
            
            with self.cap_lock:
                if self.cap is None or not self.cap.isOpened():
                    self.running = False
                    break
                ret, frame = self.cap.read()
                
            if not ret or frame is None:
                self.running = False
                break
            
            # Pré-processamento
            processed_frame = self._preprocess(frame)
            
            with self.lock:
                self.frame = processed_frame
                self.frame_count += 1
                
                if self.queue:
                    try:
                        if self.queue.full(): self.queue.get_nowait()
                        self.queue.put_nowait((processed_frame.copy(), self.frame_count))
                    except: pass
                
                try:
                    self.frame_ready.emit(processed_frame)
                except:
                    self.running = False
                    break

            if isinstance(self.source, str):
                elapsed = time.time() - start_time
                time.sleep(max(0, delay - elapsed))

    def _preprocess(self, frame):
        """Aplica normalização e redimensionamento ao frame."""
        return cv2.resize(frame, self.target_res)

    def toggle_pause(self):
        """Alterna entre pausado e rodando."""
        self.paused = not self.paused
        self.logger.info(f"Captura {'pausada' if self.paused else 'retomada'}")

    def set_speed(self, speed):
        """Ajusta a velocidade de reprodução."""
        with self.cap_lock:
            self.speed = max(0.1, min(speed, 5.0))
        self.logger.info(f"Velocidade ajustada para: {self.speed}x")

    def set_position(self, seconds_offset):
        """Pula para uma posição relativa no vídeo (em segundos)."""
        if not isinstance(self.source, str):
            return
            
        with self.cap_lock:
            if not self.cap or not self.cap.isOpened(): return
            try:
                current_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
                target_ms = max(0, current_ms + (seconds_offset * 1000))
                self.cap.set(cv2.CAP_PROP_POS_MSEC, target_ms)
                self.logger.info(f"Pulando para {target_ms/1000:.2f}s")
            except Exception as e:
                self.logger.error(f"Erro ao tentar pular no vídeo: {e}")

    def get_frame(self):
        """Retorna o último frame processado de forma thread-safe."""
        with self.lock:
            return self.frame

    def stop(self):
        """Finaliza a captura e libera recursos de forma segura."""
        self.running = False
        # NÃO usamos join() aqui para evitar travar a interface (GUI Thread)
        # O hardware será liberado de forma assíncrona pela própria thread
        with self.cap_lock:
            if self.cap:
                self.cap.release()
                self.cap = None
        self.logger.info("Solicitação de parada enviada (Assíncrona).")

if __name__ == "__main__":
    # Teste rápido de inicialização
    vc = VideoCapture(0)
    if vc.start():
        import time
        time.sleep(2)
        frame = vc.get_frame()
        if frame is not None:
            print(f"Frame capturado com sucesso! Shape: {frame.shape}")
        vc.stop()
