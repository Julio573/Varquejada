# ROADMAP DE MELHORIAS - VARQUEJADA PRO

Este documento mapeia as possíveis evoluções para o sistema de arbitragem assistida VarQuejada, categorizadas por área de impacto e nível de dificuldade técnica de implementação.

---

## 1. INTERFACE (Visual e Experiência do Usuário)

**[Fácil] Timecode e Overlay no Vídeo**
*   **Descrição:** Mover o cronômetro da prova e o timecode atual (MM:SS.mmm) para dentro da área do vídeo (canto inferior esquerdo), com fundo translúcido, exatamente como na referência visual.
*   **Impacto:** Deixa a tela mais limpa e foca a atenção do juiz diretamente no lance.

**[Médio] Marker de Rastreamento Avançado (Crosshair)**
*   **Descrição:** Substituir o "quadrado verde" (Bounding Box) do boi por um *Glow Dot* (ponto brilhante no centro de massa) cruzado por linhas guias finas (vertical e horizontal) e uma trilha de movimento (trail).
*   **Impacto:** Visual mais limpo que não obstrui a visão das patas ou cauda do animal.

**[Médio] Marcadores Interativos na Timeline**
*   **Descrição:** Sempre que o juiz clicar em "Válido" ou "Nulo", um pequeno ponto colorido (Verde ou Vermelho) é desenhado na barra de progresso (timeline). Clicar nesse ponto faz o vídeo pular direto para o lance.
*   **Impacto:** Navegação instantânea pelos momentos críticos da prova.

**[Difícil] Suporte a Múltiplas Câmeras (Split-Screen)**
*   **Descrição:** Capacidade de carregar dois ângulos de vídeo simultâneos (ex: câmera lateral e câmera superior) rodando em sincronia perfeita no mesmo player.
*   **Impacto:** Permite tirar dúvidas em lances onde o ângulo principal tem um ponto cego.

---

## 2. FUNCIONALIDADES (Novos Recursos)

**[Fácil] Exportação de Relatório Oficial (PDF/CSV)**
*   **Descrição:** Ao final da análise de um boi, um botão "Gerar Súmula" exporta um PDF com os dados da corrida: Tempo, Veredicto Final e o Histórico de Eventos.
*   **Impacto:** Profissionalização e registro em ata das decisões tomadas via VAR.

**[Médio] Sistema de Replay Instantâneo (Clipping)**
*   **Descrição:** Um atalho que recorta automaticamente os últimos 10 segundos do vídeo e salva na pasta do projeto como `lance_boi_X.mp4`.
*   **Impacto:** Facilita o envio de lances polêmicos para a organização ou para transmissão em telões da arena.

**[Médio] Velocímetro em Tempo Real (Km/h)**
*   **Descrição:** Atualizar a ferramenta de "Calibração" para marcar as duas faixas de cal. O sistema calcula a distância em pixels, converte para metros e exibe a velocidade do boi na tela.
*   **Impacto:** Dados valiosos para estatísticas da competição e narradores esportivos.

**[Difícil] Pose Estimation (Análise Articular)**
*   **Descrição:** Treinar a IA não apenas para achar o "corpo" do boi, mas para traçar um "esqueleto" (pontos nas 4 patas e dorso).
*   **Impacto:** O sistema poderia acusar automaticamente, com precisão matemática, se as 4 patas perderam contato com o solo simultaneamente.

---

## 3. ROBUSTEZ (Performance e Estabilidade)

**[Fácil] Restauração de Sessão (Auto-Save)**
*   **Descrição:** Salvar o estado da análise atual (vídeo carregado, eventos marcados, calibração) em um arquivo temporário. Se o computador desligar ou a luz cair, o sistema volta exatamente de onde parou.
*   **Impacto:** Segurança crítica em ambientes de evento ao vivo (onde quedas de energia ocorrem).

**[Médio] Rastreamento Heurístico Avançado (ByteTrack)**
*   **Descrição:** Substituir o atual `TrackerKCF` do OpenCV por algoritmos modernos de tracking (como ByteTrack ou BoTSORT) que sabem que o boi é o mesmo boi, mesmo que ele desapareça atrás de um cavalo por 2 segundos.
*   **Impacto:** Reduz a chance do "box" do boi piscar ou pular para outro animal no meio da poeira.

**[Difícil] Aceleração de Hardware Dinâmica (TensorRT/ONNX)**
*   **Descrição:** Converter o modelo `.pt` gerado pelo treinamento para o formato `ONNX` ou `TensorRT`, que roda de forma muito mais otimizada no hardware, exigindo menos da CPU.
*   **Impacto:** Permite rodar a IA em 30 FPS cravados (analisando todo frame) sem precisar pular quadros, mesmo em computadores sem placa de vídeo dedicada.
