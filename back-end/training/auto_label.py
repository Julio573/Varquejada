import os
import cv2
from ultralytics import YOLO
import logging

def auto_label():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Caminhos
    model_path = os.path.join(project_root, 'runs', 'detect', 'varquejada_yolo11', 'weights', 'best.pt')
    image_dir = os.path.join(project_root, 'training', 'dataset', 'images', 'train')
    label_dir = os.path.join(project_root, 'training', 'dataset', 'labels', 'train')
    
    # Garantir que a pasta de labels existe
    os.makedirs(label_dir, exist_ok=True)
    
    if not os.path.exists(model_path):
        print("Erro: Modelo treinado (best.pt) não encontrado.")
        return

    # Carrega o modelo
    model = YOLO(model_path)
    print(f"Iniciando Auto-rotulagem com o modelo: {model_path}")

    # Processa cada imagem
    images = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    count = 0

    for img_name in images:
        img_path = os.path.join(image_dir, img_name)
        label_path = os.path.join(label_dir, os.path.splitext(img_name)[0] + '.txt')
        
        # Só rotula se o arquivo .txt ainda não existir
        if not os.path.exists(label_path):
            # Validação extra: tenta carregar a imagem para evitar crashes se o arquivo estiver corrompido
            test_img = cv2.imread(img_path)
            if test_img is None:
                print(f"Aviso: Pulando imagem corrompida ou inválida: {img_name}")
                continue

            results = model(img_path, conf=0.3, verbose=False)
            
            yolo_labels = []
            for box in results[0].boxes:
                # YOLO format: cls, x_center, y_center, width, height (normalized 0-1)
                cls = int(box.cls[0])
                # Coordenadas normalizadas
                xywhn = box.xywhn[0].cpu().numpy()
                yolo_labels.append(f"{cls} {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f}")
            
            # Salva o arquivo de label
            if yolo_labels:
                with open(label_path, 'w') as f:
                    f.write('\n'.join(yolo_labels))
                count += 1
                if count % 10 == 0:
                    print(f"Processadas {count} imagens...")

    print(f"Auto-rotulagem concluída! {count} novos arquivos de rótulos gerados em {label_dir}")

if __name__ == "__main__":
    auto_label()
