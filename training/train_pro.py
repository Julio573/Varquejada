from ultralytics import YOLO
import os

def train_model():
    # Carrega o modelo anterior como BASE (Incremental Learning)
    model_path = '/home/juliodev/Downloads/Varquejada_System/runs/detect/varquejada_yolo11/weights/best.pt'
    
    if not os.path.exists(model_path):
        model_path = '/home/juliodev/Downloads/Varquejada_System/yolo11n.pt'
        print("Aviso: best.pt não encontrado, começando do modelo base.")

    model = YOLO(model_path) 

    # Inicia o treinamento com o novo dataset massivo (2390 imagens)
    model.train(
        data='/home/juliodev/Downloads/Varquejada_System/training/vaquejada_local.yaml',
        epochs=30,      # 30 épocas são suficientes para ajuste fino com 2k imagens
        imgsz=416,      # Resolução equilibrada para CPU
        batch=16,       
        name='varquejada_yolo11_pro',
        device='cpu'    # Forçando CPU conforme hardware
    )

if __name__ == "__main__":
    train_model()
