from ultralytics import YOLO
import os

def train_model():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Carrega o modelo mais leve e recente (YOLOv11 Nano) para performance
    model_path = os.path.join(project_root, 'yolo11n.pt')
    model = YOLO(model_path)

    # Inicia o treinamento usando o dataset local reorganizado no backend
    data_path = os.path.join(project_root, 'training', 'vaquejada_local.yaml')
    model.train(
        data=data_path,
        epochs=50,      # Começamos com 50 épocas para ver os resultados
        imgsz=640,      # Tamanho padrão de imagem YOLO
        batch=16,       # Ajustável conforme a memória da sua GPU/CPU
        name='varquejada_yolo11',
        device=None      # Auto-seleciona GPU (0, 1...) se disponível, senão usa CPU
    )

if __name__ == "__main__":
    train_model()
