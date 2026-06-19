from ultralytics import YOLO
import os

def train_model():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Carrega o modelo anterior como BASE (Incremental Learning)
    model_path = os.path.join(project_root, 'runs', 'detect', 'varquejada_yolo11', 'weights', 'best.pt')
    
    if not os.path.exists(model_path):
        model_path = os.path.join(project_root, 'yolo11n.pt')
        print("Aviso: best.pt não encontrado, começando do modelo base.")

    model = YOLO(model_path)

    # Inicia o treinamento com o novo dataset massivo (2390 imagens)
    data_path = os.path.join(project_root, 'training', 'vaquejada_local.yaml')
    model.train(
        data=data_path,
        epochs=30,      # 30 épocas são suficientes para ajuste fino com 2k imagens
        imgsz=416,      # Resolução equilibrada para CPU
        batch=16,       
        name='varquejada_yolo11_pro',
        device='cpu'    # Forçando CPU conforme hardware
    )

if __name__ == "__main__":
    train_model()
