import cv2
import os
import shutil
import glob
import logging

class DatasetBuilder:
    """
    Script para extrair frames de vídeos e organizar imagens existentes
    na estrutura de treinamento do YOLO.
    """
    def __init__(self, output_base=None):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if output_base is None:
            output_base = os.path.join(project_root, "training", "dataset", "images", "train")
        self.output_dir = output_base
        os.makedirs(self.output_dir, exist_ok=True)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("DatasetBuilder")

    def process_images(self, src_dir):
        """Copia imagens existentes para a pasta de treinamento."""
        extensions = ['*.jpg', '*.jpeg', '*.png']
        files = []
        for ext in extensions:
            files.extend(glob.glob(os.path.join(src_dir, ext)))
        
        count = 0
        for img_path in files:
            file_name = os.path.basename(img_path)
            dst_path = os.path.join(self.output_dir, f"img_{file_name}")
            shutil.copy2(img_path, dst_path)
            count += 1
        
        self.logger.info(f"Copiadas {count} imagens de {src_dir}")

    def extract_frames(self, video_dir, interval=30):
        """
        Extrai frames de vídeos em intervalos regulares.
        interval: Extrair 1 frame a cada X frames (padrão 30 = ~1s).
        """
        video_files = glob.glob(os.path.join(video_dir, "*.mp4"))
        total_extracted = 0

        for video_path in video_files:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            cap = cv2.VideoCapture(video_path)
            
            frame_count = 0
            extracted_from_video = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % interval == 0:
                    output_filename = f"frame_{video_name}_{frame_count}.jpg"
                    output_path = os.path.join(self.output_dir, output_filename)
                    cv2.imwrite(output_path, frame)
                    extracted_from_video += 1
                
                frame_count += 1
            
            cap.release()
            self.logger.info(f"Vídeo {video_name}: Extraídos {extracted_from_video} frames.")
            total_extracted += extracted_from_video

        self.logger.info(f"Total de frames extraídos: {total_extracted}")

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Caminhos baseados no seu ambiente
    IMAGE_SRC = "/home/juliodev/Downloads/imagens-bois"
    VIDEO_SRC = "/home/juliodev/Downloads/videos-bois"
    
    builder = DatasetBuilder()
    
    # 1. Processar imagens estáticas
    if os.path.exists(IMAGE_SRC):
        builder.process_images(IMAGE_SRC)
    
    # 2. Extrair frames dos vídeos (1 frame por segundo em média)
    if os.path.exists(VIDEO_SRC):
        builder.extract_frames(VIDEO_SRC, interval=30)
