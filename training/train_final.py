from ultralytics import YOLO
import os

def train_final():
    # Desativar WandB para evitar travamentos em background
    try:
        import ultralytics
        ultralytics.settings.update({'wandb': False})
    except:
        pass

    # Caminhos
    checkpoint_path = '/home/juliodev/Downloads/Varquejada_System/runs/detect/varquejada_yolo11_final/weights/last.pt'
    base_model_path = '/home/juliodev/Downloads/Varquejada_System/runs/detect/varquejada_yolo11_pro-2/weights/best.pt'
    
    # Se existir um checkpoint, retoma dele. Caso contrário, começa do modelo PRO-2
    if os.path.exists(checkpoint_path):
        print(f"Retomando treinamento a partir de: {checkpoint_path}")
        model = YOLO(checkpoint_path)
        resume_flag = True
    else:
        if not os.path.exists(base_model_path):
            print("Erro: Modelo PRO-2 não encontrado. Verifique o caminho.")
            return
        print(f"Iniciando novo treinamento a partir de: {base_model_path}")
        model = YOLO(base_model_path)
        resume_flag = False

    # Rodada FINAL
    model.train(
        data='/home/juliodev/Downloads/Varquejada_System/training/vaquejada_local.yaml',
        epochs=30,      
        imgsz=448,      
        batch=16,       
        name='varquejada_yolo11_final',
        device='cpu',
        resume=resume_flag
    )

if __name__ == "__main__":
    train_final()
