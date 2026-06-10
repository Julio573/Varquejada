import os
import subprocess

def extract_frames(video_path, output_dir, start_time, end_time, arena_name):
    """
    Extrai frames de um intervalo específico usando FFmpeg.
    vf "select=not(mod(n\,3))" -> Pega 1 a cada 3 frames.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_pattern = os.path.join(output_dir, f"{arena_name}_%04d.jpg")
    
    # Comando FFmpeg para extração precisa com tempo
    cmd = [
        'ffmpeg',
        '-ss', start_time,        # Início (HH:MM:SS)
        '-to', end_time,          # Fim (HH:MM:SS)
        '-i', video_path,
        '-vf', 'select=not(mod(n\,3))', # 1 a cada 3 frames
        '-vsync', 'vfr',
        '-q:v', '2',              # Alta qualidade
        output_pattern
    ]
    
    print(f"Executando: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == "__main__":
    # Exemplo de uso (Você deve preencher os tempos após revisar os vídeos):
    # video_base = "/home/juliodev/Downloads/videos-bois/"
    # extract_frames(video_base + "Disputa-Vaquejada.mp4", "training/enriched_dataset/arena_01", "00:01:20", "00:01:45", "disputa_v")
    print("Script de extração pronto. Aguardando definições de tempo dos momentos críticos.")
