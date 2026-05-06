import sys
import cv2
import queue
import threading
import time
from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtCore import QUrl, QThread, pyqtSignal, QObject
from ui.main_window import MainWindow
from capture.video_capture import VideoCapture
from processing.lane_detector import LaneDetector
from processing.bull_tracker import BullTracker
from decision.decision_module import DecisionModule

class ProcessingWorker(QObject):
    """
    Worker que consome frames de uma fila e os processa de forma assíncrona.
    """
    frame_ready = pyqtSignal(object)
    verdict_ready = pyqtSignal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.running = False

    def process_loop(self):
        self.running = True
        while self.running:
            try:
                # Tenta pegar um frame da fila (timeout para não travar o loop)
                frame_data = self.controller.frame_queue.get(timeout=0.1)
                frame, frame_id = frame_data
                
                # Pipeline de Processamento
                process_frame = frame.copy()

                # 1. Detecção da Faixa
                lane_bbox = self.controller.lane_detector.detect(process_frame)
                if lane_bbox:
                    self.controller.current_lane_bbox = lane_bbox

                # 2. Rastreamento do Boi e Detecção de Queda
                bull_bbox, bull_center, is_falling = self.controller.bull_tracker.track(process_frame)
                process_frame = self.controller.bull_tracker.draw_tracking(process_frame, bull_bbox, bull_center)

                # 3. Decisão
                if is_falling and self.controller.bull_tracker.fall_coords:
                    verdict = self.controller.decision.evaluate(self.controller.bull_tracker.fall_coords, self.controller.current_lane_bbox)
                    if verdict != self.controller.current_verdict:
                        self.controller.current_verdict = verdict
                        self.verdict_ready.emit(verdict)

                # 4. Aplica Overlay Final
                if self.controller.current_verdict != "AGUARDANDO...":
                    process_frame = self.controller.decision.apply_overlay(process_frame, self.controller.current_verdict, 
                                                        self.controller.bull_tracker.fall_coords, 
                                                        self.controller.current_lane_bbox)
                elif self.controller.current_lane_bbox:
                    lx, ly, lw, lh = self.controller.current_lane_bbox
                    cv2.rectangle(process_frame, (lx, ly), (lx + lw, ly + lh), (0, 255, 0), 2)

                # Envia apenas o veredicto se necessário (frames são movidos para display_frame via sinal direto)
                self.controller.frame_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                continue

class AppController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = MainWindow(controller=self)
        
        # Fila de frames para desacoplar captura de processamento
        self.frame_queue = queue.Queue(maxsize=5) # Buffer pequeno para manter tempo real
        
        # Módulos
        self.capture = None
        self.lane_detector = LaneDetector()
        self.bull_tracker = BullTracker()
        self.decision = DecisionModule()
        
        # Estado
        self.current_lane_bbox = None
        self.current_verdict = "AGUARDANDO..."
        
        # Thread de Processamento (Assíncrona - Não bloqueia vídeo)
        self.process_thread = QThread()
        self.worker = ProcessingWorker(self)
        self.worker.moveToThread(self.process_thread)
        self.process_thread.started.connect(self.worker.process_loop)
        self.worker.verdict_ready.connect(self.window.update_verdict)
        self.process_thread.start()
        
        # Conexão do Timer e Slider
        self.window.media_player.positionChanged.connect(self.update_timer_position)
        self.window.media_player.durationChanged.connect(self.update_timer_duration)
        self.window.video_slider.sliderMoved.connect(self.seek_slider)
        
        # Sinais da Barra de Transporte (Precisão)
        self.window.btn_pause_float.clicked.connect(self.toggle_pause)
        self.window.btn_prev_f.clicked.connect(lambda: self.seek(-0.033))
        self.window.btn_next_f.clicked.connect(lambda: self.seek(0.033))
        
        # Conexões de Veredicto Rápido
        self.window.btn_quick_valid.clicked.connect(lambda: self.update_verdict("Válido"))
        self.window.btn_quick_null.clicked.connect(lambda: self.update_verdict("Inválido"))
        self.window.btn_quick_review.clicked.connect(lambda: self.update_verdict("Inconclusivo"))

    def run(self):
        self.window.show()
        sys.exit(self.app.exec())

    def start_camera(self):
        self.start_capture(0)

    def open_video_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self.window, "Selecionar Arquivo de Vídeo", "", "Vídeos (*.mp4 *.avi *.mkv)"
        )
        if file_name:
            self.start_capture(file_name)

    def update_timer_position(self, position):
        self.window.video_slider.setValue(position)
        curr_time = self._format_time_ms(position)
        total_duration = self.window.media_player.duration()
        total_time = self._format_time_ms(total_duration)
        self.window.lbl_time.setText(curr_time)
        self.window.lbl_time_total.setText(f"/ {total_time}")

    def update_timer_duration(self, duration):
        self.window.video_slider.setRange(0, duration)

    def seek_slider(self, position):
        self.window.media_player.setPosition(position)
        if self.capture:
            with self.capture.cap_lock:
                self.capture.cap.set(cv2.CAP_PROP_POS_MSEC, position)

    def _format_time_ms(self, ms):
        """Formato MM:SS.mmm para precisão de arbitragem."""
        if ms < 0: ms = 0
        seconds = (ms // 1000) % 60
        minutes = (ms // (1000 * 60)) % 60
        milliseconds = ms % 1000
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    def start_capture(self, source):
        try:
            self.stop_capture()
            time.sleep(0.1)
            
            self.bull_tracker.reset()
            self.lane_detector.unlock_lane()
            self.window.btn_lock_lane.setChecked(False)
            self.current_lane_bbox = None
            self.current_verdict = "AGUARDANDO..."
            
            while not self.frame_queue.empty():
                try: self.frame_queue.get_nowait()
                except queue.Empty: break
                
            self.window.update_verdict(self.current_verdict)
            
            self.capture = VideoCapture(source=source)
            self.capture.queue = self.frame_queue
            
            # Conexão Direta (Capture -> UI) garante FPS Máximo
            self.capture.frame_ready.connect(self.window.display_frame)
            
            if self.capture.start():
                if isinstance(source, str):
                    self.window.media_player.setSource(QUrl.fromLocalFile(source))
                    self.window.media_player.play()
                
                # Inicia com o ícone de PAUSE pois o vídeo começou a rodar
                self.window.btn_pause_float.setText("⏸")
                self.window.log_list.addItem(f"Iniciada captura: {source}")
        except Exception as e:
            self.window.log_list.addItem(f"ERRO ao abrir vídeo: {e}")

    def toggle_lane_lock(self, locked):
        if locked: self.lane_detector.lock_lane()
        else: self.lane_detector.unlock_lane()

    def toggle_pause(self):
        if self.capture:
            self.capture.toggle_pause()
            self.window.btn_pause_float.setText("▶" if self.capture.paused else "⏸")
            if self.capture.paused: self.window.media_player.pause()
            else: self.window.media_player.play()

    def seek(self, seconds):
        if self.capture:
            while not self.frame_queue.empty():
                try: self.frame_queue.get_nowait()
                except queue.Empty: break
            self.capture.set_position(seconds)
            new_pos = self.window.media_player.position() + (seconds * 1000)
            self.window.media_player.setPosition(max(0, int(new_pos)))

    def update_verdict(self, verdict):
        self.current_verdict = verdict
        self.window.update_verdict(verdict)

    def set_speed(self, speed):
        if self.capture: self.capture.set_speed(speed)

    def stop_capture(self):
        if self.capture:
            try:
                self.window.media_player.stop()
                self.capture.running = False
                if self.capture.thread and self.capture.thread.is_alive():
                    self.capture.thread.join(timeout=0.5)
            except: pass
            self.capture = None
            self.window.video_label.setText("Captura Encerrada")
            self.window.log_list.addItem("Captura encerrada.")

if __name__ == "__main__":
    controller = AppController()
    controller.run()
