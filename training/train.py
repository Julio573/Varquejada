from ultralytics import YOLO
import os

def train_model():
    # Carrega o modelo mais leve e recente (YOLOv11 Nano) para performance
    # Usando caminho absoluto para evitar erros de diretório
    model_path = '/home/juliodev/Downloads/Varquejada_System/yolo11n.pt'
    model = YOLO(model_path) 

    # Inicia o treinamento usando o dataset do Roboflow
    model.train(
        data='/home/juliodev/Downloads/Varquejada_System/training/vaquejada_roboflow.yaml',
        epochs=50,      # Começamos com 50 épocas para ver os resultados
        imgsz=640,      # Tamanho padrão de imagem YOLO
        batch=16,       # Ajustável conforme a memória da sua GPU/CPU
        name='varquejada_yolo11',
        device=None      # Auto-seleciona GPU (0, 1...) se disponível, senão usa CPU
    )

if __name__ == "__main__":
    train_model()
