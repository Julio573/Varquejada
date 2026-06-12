# Varquejada System 🐂🐎

Sistema de monitoramento e auxílio à arbitragem de Vaquejada utilizando Inteligência Artificial (YOLOv11) para detecção de queda e análise de conformidade em tempo real.

## 🚀 Funcionalidades

- **Detecção em Tempo Real:** Identificação de bois e cavalos na arena.
- **Análise de Queda:** Algoritmo especializado para detectar o momento exato da queda do boi.
- **Auxílio à Arbitragem:** Interface intuitiva para revisão de lances com controles de precisão (frame-a-frame).
- **Veredictos Rápidos:** Registro de "Válido", "Inválido" ou "Inconclusivo" com marcação visual no vídeo.
- **Otimizado para CPU:** Processamento eficiente que não exige placa de vídeo dedicada para rodar a interface.

## 📦 Instalação

### Pré-requisitos
- Python 3.10 ou superior
- Recomendado uso de ambiente virtual (venv)

### Passo a Passo

1. **Clonar o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/Varquejada_System.git
   cd Varquejada_System/back-end
   ```

2. **Criar e ativar ambiente virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```

3. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

## 🎮 Como Usar

Para subir a nova API do backend:

```bash
python3 server.py
```

Isso inicia o FastAPI em `http://localhost:8000` com:

- `GET /health`
- `GET /session`
- `POST /session/open-video`
- `POST /session/open-camera`
- `POST /session/pause`
- `POST /session/seek`
- `POST /session/speed`
- `POST /session/ppm`
- `POST /session/marker`
- `POST /session/calibrate`
- `POST /session/reset`
- `WS /ws/session`

O app PyQt antigo continua no arquivo `main.py`, mas a integração nova com Electron deve partir da API.

### Fluxo sugerido para o Electron

1. Abrir um vídeo com `POST /session/open-video`.
2. Ajustar pausa, velocidade e posição com `pause`, `speed` e `seek`.
3. Rodar a calibração automática com `POST /session/calibrate`.
4. Ler o estado atual com `GET /session` enquanto o front escuta `WS /ws/session` em tempo real.

### WebSocket da sessão

O endpoint `WS /ws/session` envia mensagens JSON com este formato:

```json
{
  "type": "session.updated",
  "timestamp": "2026-06-12T14:35:47.725075+00:00",
  "session": {
    "source_type": "video",
    "is_running": true
  }
}
```

Ao conectar, o cliente recebe um snapshot inicial da sessão e depois passa a receber novas versões sempre que os comandos HTTP alteram o estado.

## 🧠 Modelos (IA)

O sistema utiliza modelos YOLOv11 treinados especificamente para o cenário de Vaquejada.
- O modelo padrão está localizado em `models/best.pt`.
- O sistema busca automaticamente por modelos mais recentes na pasta `runs/` se disponíveis.

## 🛠️ Estrutura do Projeto

- `ui/`: Arquivos da interface gráfica (PyQt6).
- `processing/`: Lógica de detecção e rastreamento (YOLOv11).
- `capture/`: Gerenciamento de captura de vídeo e câmeras.
- `decision/`: Módulo de lógica de arbitragem e overlays.
- `models/`: Pesos do modelo de IA treinado.
- `training/`: Scripts e configurações de treino do modelo.
- `assets/`: Ícones e recursos visuais do backend.

---
Desenvolvido para modernizar e trazer mais precisão ao esporte da Vaquejada.
