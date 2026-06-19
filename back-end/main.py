import sys
import cv2
import queue
import threading
import time
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
from PyQt6.QtCore import QUrl, QThread, pyqtSignal, QObject
from ui.main_window import MainWindow, CameraSelectionDialog, CustomMessageBox
from capture.video_capture import VideoCapture
from processing.horse_tracker import HorseTracker
from processing.auto_calibration import AutoCalibrator

class CalibrationWorker(QObject):
    """
    Worker que tenta calibrar o PPM automaticamente em background.
    """
    finished = pyqtSignal(float)
    failed = pyqtSignal()

    def __init__(self, source):
        super().__init__()
        self.source = source
        self._is_running = True

    def run(self):
        # NÃO tenta calibrar automaticamente em Câmera (risco de conflito de hardware)
        if not isinstance(self.source, str):
            self.failed.emit()
            return

        try:
            cap = cv2.VideoCapture(self.source)
            if not cap.isOpened():
                self.failed.emit()
                return

            calibrator = AutoCalibrator()
            
            # Tenta calibrar em vários frames (pula os primeiros 30 para evitar telas pretas/carregamento)
            cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
            
            for _ in range(10):
                if not self._is_running: break
                ret, frame = cap.read()
                if not ret: break
                
                ppm = calibrator.calibrate(frame)
                if ppm:
                    cap.release()
                    self.finished.emit(ppm)
                    return
                
                curr = cap.get(cv2.CAP_PROP_POS_FRAMES)
                cap.set(cv2.CAP_PROP_POS_FRAMES, curr + 15)

            cap.release()
            self.failed.emit()
        except Exception as e:
            print(f"[CALIB_WORKER] Erro: {e}")
            self.failed.emit()

    def stop(self):
        self._is_running = False

class ProcessingWorker(QObject):
    """
    Worker que consome frames de uma fila e os processa de forma assíncrona.
    """
    frame_ready = pyqtSignal(object)
    speed_ready = pyqtSignal(float)
    multi_speed_ready = pyqtSignal(dict) # {id: speed}
    distance_ready = pyqtSignal(float)
    time_ready = pyqtSignal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.running = False

    def process_loop(self):
        self.running = True
        import numpy as np
        while self.running:
            try:
                # Tenta pegar um frame da fila (timeout para não travar o loop)
                if self.controller.frame_queue.empty():
                    time.sleep(0.01)
                    continue
                    
                frame_data = self.controller.frame_queue.get(timeout=0.1)
                frame, frame_id = frame_data
                
                # Snapshot seguro da captura
                cap_ref = self.controller.capture
                if not cap_ref:
                    self.controller.frame_queue.task_done()
                    continue

                # Pipeline de Processamento
                process_frame = frame.copy()

                # 1. Rastreamento do Cavalo
                fps = cap_ref.fps if cap_ref else 30.0
                horse_bbox, horse_center, _ = self.controller.horse_tracker.track(process_frame, fps=fps)
                
                # 2. Métricas de Tempo
                total_ms = int((frame_id / fps) * 1000)
                minutes = (total_ms // 60000) % 60
                seconds = (total_ms // 1000) % 60
                millis = (total_ms // 100) % 10
                self.time_ready.emit(f"{minutes:02d}:{seconds:02d}.{millis}")

                # 3. Métricas de Velocidade e Distância
                with self.controller.horse_tracker.lock:
                    all_speeds = {}
                    if self.controller.horse_tracker.tracked_horses:
                        # Pega o cavalo com melhor confiança para o HUD principal
                        best_tid = max(self.controller.horse_tracker.tracked_horses, 
                                     key=lambda k: self.controller.horse_tracker.tracked_horses[k]["conf"])
                        primary_data = self.controller.horse_tracker.tracked_horses[best_tid]

                        self.speed_ready.emit(primary_data.get("speed", 0.0))
                        self.distance_ready.emit(primary_data.get("dist_total_m", 0.0))

                        # Coleta todos para o gráfico
                        for tid, data in self.controller.horse_tracker.tracked_horses.items():
                            all_speeds[tid] = data.get("speed", 0.0)
                    else:
                        self.speed_ready.emit(0.0)

                    self.multi_speed_ready.emit(all_speeds)

                # O desenho ocorre agora DENTRO do objeto frame (referência)
                self.controller.horse_tracker.draw_tracking(process_frame, horse_bbox, horse_center)

                # Envia o frame processado de volta para a UI
                self.frame_ready.emit(process_frame)
                self.controller.frame_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"[PROC_WORKER] Erro: {e}")
                continue

class AppController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = MainWindow(controller=self)
        
        # Fila de frames para desacoplar captura de processamento
        self.frame_queue = queue.Queue(maxsize=5) # Buffer pequeno para manter tempo real
        
        # Módulos
        self.capture = None
        self.horse_tracker = HorseTracker()
        
        # Estado
        self.current_verdict = "TELEMETRIA"
        
        # Thread de Processamento (Assíncrona - Não bloqueia vídeo)
        self.process_thread = QThread()
        self.worker = ProcessingWorker(self)
        self.worker.moveToThread(self.process_thread)
        self.process_thread.started.connect(self.worker.process_loop)
        
        # Conexões de Telemetria (Worker -> UI)
        self.worker.speed_ready.connect(self.window.speedometer.setValue)
        self.worker.distance_ready.connect(lambda d: self.window.lbl_header_dist.setText(f"{d:.1f} m"))
        self.worker.time_ready.connect(self.window.lbl_header_elapsed.setText)
        self.worker.frame_ready.connect(self.window.display_frame) # Conexão única
        self.worker.multi_speed_ready.connect(self.window.speed_graph.add_data)
        
        self.process_thread.start()
        
        # Conexão do Timer e Slider
        self.window.media_player.positionChanged.connect(self.update_timer_position)
        self.window.media_player.durationChanged.connect(self.update_timer_duration)
        self.window.video_slider.sliderMoved.connect(self.seek_slider)
        
        # Sinais da Barra de Transporte (Precisão)
        self.window.btn_pause_float.clicked.connect(self.toggle_pause)
        self.window.btn_prev_f.clicked.connect(lambda: self.seek(-5))
        self.window.btn_next_f.clicked.connect(lambda: self.seek(5))

    def run(self):
        self.window.show()
        sys.exit(self.app.exec())

    def start_camera(self):
        # 1. PAUSA DE SEGURANÇA (Libera a interface para abrir o diálogo)
        was_running = self.worker.running
        self.worker.running = False
        if self.capture: self.capture.paused = True

        try:
            # 2. DIÁLOGO (Aberto agora com interface livre)
            dialog = CameraSelectionDialog(self.window)
            result = dialog.exec()
            action = dialog.get_action_result()

            # 3. PROCESSA AÇÃO
            if result and action != -1:
                if action == -2: # Código para PARAR
                    self.stop_capture()
                else: # Iniciar ou Trocar
                    self.start_capture(action)
            else:
                # Se cancelado, volta ao estado anterior
                self.worker.running = was_running
                if self.capture: self.capture.paused = False
        except Exception as e:
            print(f"[START_CAMERA] Erro: {e}")
            self.worker.running = was_running
            if self.capture: self.capture.paused = False

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
            # 1. Limpeza Imediata e Assíncrona
            self.stop_auto_calibration()
            self.worker.running = False 
            
            if self.capture:
                try:
                    self.capture.stop()
                    self.capture.queue = None 
                except: pass
                self.capture = None
            
            # Esvazia fila física
            while not self.frame_queue.empty():
                try: self.frame_queue.get_nowait()
                except: break
            
            self.worker.running = True
            self.horse_tracker.reset()
            self.current_verdict = "TELEMETRIA"
            
            # 2. Nova Captura (A abertura real agora ocorre em background na VideoCapture)
            self.capture = VideoCapture(source=source)
            self.capture.queue = self.frame_queue
            
            # Se for Câmera, conectamos o sinal RAW diretamente para garantir vídeo
            if not isinstance(source, str):
                self.capture.frame_ready.connect(self.window.display_frame)
            
            if self.capture.start():
                if isinstance(source, str):
                    self.window.media_player.setSource(QUrl.fromLocalFile(source))
                    self.window.media_player.play()
                    self.run_auto_calibration(source)
                
                self.window.btn_pause_float.setText("⏸")
                self.window.log_list.addItem(f"Iniciada captura: {source}")
            else:
                self.stop_capture()
        except Exception as e:
            self.window.log_list.addItem(f"ERRO ao iniciar captura: {e}")
            self.stop_capture()

    def stop_auto_calibration(self):
        """Finaliza a thread de calibração se ela ainda estiver rodando."""
        if hasattr(self, 'calib_worker'):
            self.calib_worker.stop()
        if hasattr(self, 'calib_thread') and self.calib_thread.isRunning():
            self.calib_thread.quit()
            self.calib_thread.wait(300)
            self.calib_thread = None

    def run_auto_calibration(self, source):
        """Inicia o processo de calibração automática em uma thread separada."""
        self.calib_thread = QThread()
        self.calib_worker = CalibrationWorker(source)
        self.calib_worker.moveToThread(self.calib_thread)
        self.calib_thread.started.connect(self.calib_worker.run)
        self.calib_worker.finished.connect(self.on_auto_calibration_success)
        self.calib_worker.failed.connect(self.on_auto_calibration_failed)
        self.calib_worker.finished.connect(self.calib_thread.quit)
        self.calib_worker.failed.connect(self.calib_thread.quit)
        self.calib_thread.start()
        self.window.log_list.addItem("Iniciando calibração automática...")

    def on_auto_calibration_success(self, calib_data):
        self.horse_tracker.setup_homography(calib_data)
        self.window.log_list.addItem(f"Calibração Automática OK: {calib_data['ppm']:.2f} px/m")

    def on_auto_calibration_failed(self):
        self.window.log_list.addItem("Calibração Automática falhou. Use o modo manual se necessário.")

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
            
            # Feedback Visual OSD
            osd_text = f"+{int(seconds)}s" if seconds > 0 else f"{int(seconds)}s"
            self.window.show_osd(osd_text)

    def update_verdict(self, verdict):
        self.current_verdict = verdict
        # Adiciona marcador na timeline ao emitir um veredicto
        if self.capture:
            color = "#22C55E" if "VALIDO" in verdict else "#EF4444" if "INVALIDO" in verdict else "#F59E0B"
            curr_ms = self.window.media_player.position()
            self.window.video_slider.add_marker(curr_ms, color, verdict)
            self.window.log_list.addItem(f"[{self._format_time_ms(curr_ms)}] Veredicto: {verdict}")

    def add_manual_marker(self, label, color="#3B82F6"):
        """Adiciona um marcador manual no ponto atual (ex: Início da Corrida)."""
        if self.capture:
            curr_ms = self.window.media_player.position()
            self.window.video_slider.add_marker(curr_ms, color, label)
            self.window.log_list.addItem(f"[{self._format_time_ms(curr_ms)}] Evento: {label}")

    def set_ppm(self, ppm):
        """Define os pixels por metro para o rastreador."""
        self.horse_tracker.ppm = ppm

    def toggle_lane_lock(self, checked):
        """Ativa/Desativa o modo de calibração na UI."""
        self.window.toggle_lane_lock(checked)

    def set_speed(self, speed):
        if self.capture: self.capture.set_speed(speed)

    def stop_capture(self):
        """Para a captura atual e reseta a UI para o estado inicial."""
        self.stop_auto_calibration()
        if self.capture:
            try:
                self.capture.stop()
                self.capture.deleteLater()
            except: pass
            self.capture = None
            
        # Reseta Elementos da UI através do método centralizado
        self.window.media_player.stop()
        self.window.reset_ui()
        self.window.log_list.addItem("Captura encerrada. Player resetado.")

if __name__ == "__main__":
    controller = AppController()
    controller.run()
