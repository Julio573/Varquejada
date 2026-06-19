# Corrida de Vaquejada + Visão computacional

Sistema de telemetria e análise de performance para corridas de Vaquejada utilizando Visão Computacional. O sistema realiza o processamento de vídeo em tempo real para rastrear cavalos, calcular sua velocidade instantânea e metrificar a distância percorrida, gerando relatórios detalhados para competidores e investidores.

---

## 💡 O Produto

O software foi desenvolvido com foco em telemetria esportiva, atendendo à necessidade de criadores, vaqueiros e investidores de mensurar com precisão a performance física de seus cavalos de corrida e identificar o potencial dos animais.

### O que o software faz:
- **Rastreamento de Performance:** Acompanha o trajeto do cavalo durante a corrida.
- **Métricas de Velocidade:** Mede a velocidade instantânea (Km/h), velocidade média e pico de aceleração.
- **Mapeamento de Distância por Projeção de Perspectiva:** Utiliza calibração de perspectiva baseada na pista para converter deslocamento em pixels para metros reais.
- **Gráficos e Histórico:** Plota a curva de velocidade ao longo do tempo para analisar consistência e aceleração em cada trecho da pista.
- **Relatórios Detalhados:** Gera súmulas de performance em formato PDF e registros de telemetria ao final das corridas.

---

## 🛠️ Tecnologias

### Frontend
- **React 19** & **TypeScript**
- **TanStack Start** & **TanStack Router** (File-based Routing)
- **TanStack Query** (Gerenciamento de Estado e Cache de Dados)
- **Electron** (Empacotamento Desktop Nativo)
- **Tailwind CSS** (Interface moderna e compacta)
- **Radix UI** (Componentes de interface acessíveis)
- **Recharts** (Visualização gráfica da curva de velocidade)

### Backend
- **Python 3.10+**
- **FastAPI** (API HTTP e WebSocket para streaming em tempo real)
- **Uvicorn** (Servidor de aplicação ASGI)
- **OpenCV** (Processamento de imagem, transformação de perspectiva e optical flow)
- **Ultralytics YOLO** (Modelo de Inteligência Artificial para rastreamento)
- **PyQt6 / PySide6** (Interface Desktop nativa legada)

---

## 🏗️ Arquitetura e Fluxo de Dados

O sistema opera de forma desacoplada, onde o frontend gerencia a interface do usuário nativa e o backend manipula a carga pesada de visão computacional.

### Fluxo de Processamento de Frames:

```
[Vídeo / Câmera] 
      │ (OpenCV VideoCapture)
      ▼
[Processamento de Imagem] ──► [Estabilização Optical Flow] ──► [Detecção YOLOv11]
      │
      ▼
[Transformação de Perspectiva (Pés)] ──► [Filtro de Ruído & Aceleração] ──► [Telemetria Real]
      │
      ▼
[WebSocket Streamer (Base64 + JSON)] ──► [Interface React / Electron (Recharts & Canvas)]
```

1. **Captura:** O frame é capturado do arquivo de vídeo local ou da câmera pelo OpenCV.
2. **Estabilização:** O fundo da arena é analisado via Optical Flow para compensar movimentações da câmera (panning).
3. **Detecção e Rastreamento:** O modelo YOLOv11 localiza os animais na cena, e um rastreador heurístico preserva a identidade (ID) do cavalo.
4. **Transformação de Perspectiva:** A posição do pé do cavalo é projetada para coordenadas em metros baseadas na calibração da pista.
5. **Streaming:** O frame processado (desenhado com overlays) é codificado em JPG/Base64 e enviado junto com os metadados JSON da telemetria via WebSocket para a aplicação Electron.

---

## 📁 Estrutura de Diretórios

```
Varquejada/
├── back-end/                  # Servidor de Processamento e IA (Python)
│   ├── api/                   # Rotas e controladores FastAPI
│   │   ├── routers/           # Endpoints de controle da mídia, sessão e relatórios
│   │   └── main.py            # Ponto de inicialização do FastAPI
│   ├── core/                  # Gerenciamento de estado, threads e streamer de frames
│   │   ├── frame_streamer.py  # Thread dedicada ao loop de processamento e stream
│   │   └── session_manager.py # Manager de sessões e mídias ativas
│   ├── processing/            # Algoritmos de rastreamento e calibração de câmera
│   │   ├── horse_tracker.py   # Rastreamento YOLOv11, Optical Flow e Transformação de Perspectiva
│   │   └── auto_calibration.py# Calibração automática da pista
│   ├── models/                # Pesos salvos do YOLO (best.pt)
│   ├── reports/               # Pasta de súmulas geradas em PDF
│   ├── ui/                    # Interface local em PyQt6 (legada)
│   ├── server.py              # Script de entrada para executar o backend FastAPI
│   └── requirements.txt       # Dependências Python
│
├── front-end/                 # Interface Desktop com Electron e React
│   ├── electron/              # Scripts de ciclo de vida e preload do Electron
│   ├── src/
│   │   ├── components/        # Componentes UI reusáveis (Radix & Tailwind)
│   │   ├── lib/               # Integração de rede e controle do WebSocket (backend.ts)
│   │   ├── routes/            # Roteamento baseado em arquivos (TanStack Router)
│   │   │   ├── index.tsx      # Dashboard principal de visualização da corrida
│   │   │   ├── analysis.tsx   # Painel de análise detalhada da curva de velocidade
│   │   │   └── settings.tsx   # Ajustes e calibragens preferenciais
│   │   └── styles.css         # Variáveis e temas globais CSS (oklch)
│   ├── package.json           # Scripts NPM e dependências frontend
│   └── vite.config.ts         # Configuração de bundler Vite
```

---

## 🔗 Integração API e Endpoints Principais

A comunicação entre a interface Electron e a API FastAPI utiliza endpoints REST para controle de estado e WebSockets para streaming contínuo.

### Endpoints de Controle (REST API - `port 8000`)
- `POST /session/open-video`: Carrega um arquivo de vídeo local no pipeline de processamento.
- `POST /session/open-camera`: Inicializa captura a partir de um índice de câmera USB/HDMI conectado.
- `POST /session/pause`: Alterna o estado de reprodução do vídeo analisado.
- `POST /session/seek`: Avança ou retrocede a posição do vídeo em segundos.
- `POST /session/speed`: Altera o multiplicador de velocidade de reprodução (0.5x, 1x, 2x).
- `POST /session/calibrate`: Dispara o algoritmo de calibração automática da pista.
- `GET /reports`: Lista todos os relatórios PDF salvos de sessões anteriores.
- `GET /reports/latest`: Faz download do último PDF gerado após o encerramento da corrida.

### Streaming em Tempo Real (WebSocket)
- `WS /ws/session`: O frontend conecta-se a esta rota para receber eventos de atualização. A cada frame processado, o backend envia dados estruturados:
  - `frame`: Payload contendo a imagem JPEG convertida em Base64 para renderização no canvas.
  - `telemetry`: JSON com velocidade em tempo real (`speed_kmh`), distância acumulada (`distance_m`), timecode com precisão de milissegundos e Bounding Box do animal.

---

## 🎮 Como Executar

### 1. Inicializar o Backend

1. Acesse o diretório do backend:
   ```bash
   cd back-end
   ```

2. Crie e ative seu ambiente virtual Python:
   * **Windows (PowerShell):**
     ```bash
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   * **Linux/macOS:**
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Inicie o servidor:
   ```bash
   python server.py
   ```
   *O backend ficará ativo na porta `http://localhost:8000`.*

---

### 2. Inicializar o Frontend (Electron)

1. Acesse o diretório do frontend em outro terminal:
   ```bash
   cd front-end
   ```

2. Instale as dependências:
   ```bash
   npm install
   ```

3. Execute o aplicativo:
   ```bash
   npm run dev:app
   ```

---

## 📐 Detalhes Técnicos de Projeção e IA

O cálculo de velocidade é feito localmente usando algoritmos de visão computacional:

### Cálculo de Velocidade e Distância por Transformação de Perspectiva
* **Transformação de Perspectiva:** Para compensar a distorção de perspectiva causada pelo ângulo de inclinação da câmera, o sistema usa uma transformação matemática (`cv2.getPerspectiveTransform`). Ele mapeia a área trapezoidal da pista (delimitada pelas faixas de cal) para um plano terrestre retangular virtual de 1,5m de largura por 20m de comprimento.
* **Projeção de Posição:** A base da Bounding Box do cavalo (ponto médio inferior, correspondente ao contato do animal com o solo) é projetada através da matriz de transformação de perspectiva para estimar a posição exata do animal em metros no plano do mundo real.
* **Compensação de Movimento da Câmera (Optical Flow):** Quando a câmera se move para acompanhar a corrida, o movimento da imagem introduz ruído. O sistema calcula o deslocamento da câmera calculando o fluxo óptico (Lucas-Kanade) no fundo estável da arena e desconta essa movimentação no cálculo final de deslocamento do cavalo.
* **Filtragem:** As leituras de velocidade bruta passam por um filtro de mediana móvel (buffer de 15 frames) e um limitador de aceleração para atenuar ruídos de detecção antes de exibir na interface.

### Configurações do Modelo de Inteligência Artificial
* **Modelo Utilizado:** **YOLOv11** (Ultralytics) especializado para o esporte de Vaquejada.
* **Processamento Local (CPU):** O pipeline é otimizado para execução local em CPU.
* **Tamanho da Imagem (`imgsz`):** Reduzido para `320x320` para maximizar a taxa de processamento.
* **Limiar de Confiança (`conf_threshold`):** Ajustado em **50% (0.50)** para evitar falsas detecções.
* **Tolerância a Perda de Frames (`max_lost_frames`):** Ajustada em **2 frames** para evitar oscilações de rastreamento do animal decorrentes de poeira ou oclusões parciais durante a corrida.
