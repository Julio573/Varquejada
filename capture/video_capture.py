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
        self.cap = cv2.VideoCapture(self.source)
        self.running = False
        self.paused = False
        self.frame = None
        self.frame_count = 0
        self.queue = None # Será injetado pelo AppController
        self.lock = threading.Lock() # Lock para o frame processado
        self.cap_lock = threading.Lock() # Lock para o objeto cv2.VideoCapture
        self.thread = None
        self.speed = 1.0
        
        # Obter FPS original para manter a velocidade normal em arquivos
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30  # Fallback para 30 FPS
            
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("VideoCapture")

    def start(self):
        """Inicia a captura em uma thread separada."""
        if not self.cap.isOpened():
            self.logger.error(f"Não foi possível abrir a fonte de vídeo: {self.source}")
            return False
        
        self.running = True
        self.paused = False
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        self.logger.info(f"Captura iniciada na fonte: {self.source} ({self.fps} FPS)")
        return True

    def toggle_pause(self):
        """Alterna entre pausado e rodando."""
        self.paused = not self.paused
        self.logger.info(f"Captura {'pausada' if self.paused else 'retomada'}")

    def set_speed(self, speed):
        """Ajusta a velocidade de reprodução."""
        self.speed = max(0.1, min(speed, 5.0))
        self.logger.info(f"Velocidade ajustada para: {self.speed}x")

    def set_position(self, seconds_offset):
        """Pula para uma posição relativa no vídeo (em segundos)."""
        if not isinstance(self.source, str):
            return
            
        with self.cap_lock:
            try:
                current_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
                target_ms = max(0, current_ms + (seconds_offset * 1000))
                self.cap.set(cv2.CAP_PROP_POS_MSEC, target_ms)
                self.logger.info(f"Pulando para {target_ms/1000:.2f}s")
            except Exception as e:
                self.logger.error(f"Erro ao tentar pular no vídeo: {e}")

    def _capture_loop(self):
        """Loop interno de captura executado na thread com controle de tempo e velocidade."""
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            # O delay ajustado pela velocidade
            delay = (1.0 / self.fps) / self.speed
            start_time = time.time()
            
            with self.cap_lock:
                ret, frame = self.cap.read()
                
            if not ret:
                if isinstance(self.source, str):
                    self.logger.info("Fim do arquivo de vídeo atingido.")
                else:
                    self.logger.warning("Falha ao capturar frame da câmera.")
                self.running = False
                break
            
            # Pré-processamento: Normalização de resolução (720p padrão)
            processed_frame = self._preprocess(frame)
            
            with self.lock:
                self.frame = processed_frame
                self.frame_count += 1
                
                # Alimenta a fila e emite sinal direto para UI
                if self.queue:
                    try:
                        if self.queue.full():
                            self.queue.get_nowait()
                        self.queue.put_nowait((processed_frame.copy(), self.frame_count))
                    except: pass
                
                self.frame_ready.emit(processed_frame)

            # Controle de Velocidade: Apenas para arquivos de vídeo
            if isinstance(self.source, str):
                elapsed = time.time() - start_time
                sleep_time = max(0, delay - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def _preprocess(self, frame):
        """Aplica normalização e redimensionamento ao frame."""
        # Redimensionamento para 720p (ou resolução alvo)
        return cv2.resize(frame, self.target_res)

    def get_frame(self):
        """Retorna o último frame processado de forma thread-safe."""
        with self.lock:
            return self.frame

    def stop(self):
        """Finaliza a captura e libera recursos."""
        self.running = False
        if self.thread:
            self.thread.join()
        self.cap.release()
        self.logger.info("Captura encerrada e recursos liberados.")

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
