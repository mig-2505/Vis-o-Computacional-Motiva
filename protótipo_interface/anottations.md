# GreenSense — Central de Inteligência Operacional | Motiva

Protótipo de visão computacional para monitoramento de vegetação e priorização de roçada.

## O que foi corrigido

- Câmera do **celular** integrada ao Streamlit com `st.camera_input`.
- Upload de foto pelo celular como alternativa quando o navegador bloquear câmera.
- A mesma foto não é registrada repetidamente no histórico a cada rerender do Streamlit.
- Fotos recebidas do celular são salvas automaticamente em `fotos_medicoes/`.
- OpenCV trocado para `opencv-python-headless`, mais adequado para Streamlit Cloud/servidores.
- Leitura de `.kmz` corrigida para aceitar também KML puro salvo com extensão `.kmz`.
- Mapa, Índice de Prioridade, clima e histórico continuam funcionando.
- A foto real passa a substituir a simulação somente no KM escolhido.

## Estrutura

```text
greensense/
├── app.py
├── medir_grama.py
├── geo_data.py
├── priority.py
├── climate.py
├── historico.py
├── captura_camera.py
├── calibracao_cor.py
├── requirements.txt
├── data/
└── fotos_medicoes/
```

## 1. Instalação

### Windows

```powershell
cd greensense
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Linux/macOS

```bash
cd greensense
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Coloque os dados do challenge

Copie os arquivos geográficos `.kmz`/`.kml` para:

```text
greensense/data/
```

O sistema reconhece arquivos com nomes contendo `km`, `marco`, `rocada`, `roçada` ou `classificacao`.

Depois de colocar os arquivos, reinicie o Streamlit.

## 3. Rodar no computador

```bash
streamlit run app.py
```

## 4. Abrir no celular na mesma Wi-Fi

No computador:

```bash
streamlit run app.py --server.address 0.0.0.0
```

Descubra o IP do computador:

### Windows

```powershell
ipconfig
```

Procure o `IPv4`.

### Linux

```bash
ip a
```

No celular, abra:

```text
http://IP-DO-COMPUTADOR:8501
```

Exemplo:

```text
http://192.168.0.105:8501
```

## 5. Como tirar a foto pelo celular

Na barra lateral do GreenSense:

1. toque em **Tirar foto com a câmera do celular**;
2. fotografe a vegetação;
3. escolha o **KM/ponto** correspondente;
4. a foto é analisada pelo OpenCV;
5. a altura e cobertura entram no Índice de Prioridade;
6. a medição é salva no histórico.

### Importante: HTTPS

Os navegadores modernos podem bloquear acesso à câmera quando o site está em `http://IP:8501`.

Se isso acontecer, o problema é uma regra de segurança do navegador.

Você ainda pode usar **Enviar foto**, que funciona em HTTP.

Para usar a câmera diretamente pelo navegador, disponibilize o Streamlit por HTTPS, por exemplo com um túnel HTTPS (Cloudflare Tunnel/ngrok) ou certificado SSL local.

## 6. O que é real e o que é demonstração

| Componente | Situação |
|---|---|
| Foto do celular | Real |
| OpenCV | Real |
| Altura/cobertura da vegetação | Real quando a referência é detectada |
| KMZ/KML | Real quando os arquivos estão em `data/` |
| Mapa | Real |
| Clima Open-Meteo | Real quando ativado |
| Histórico | Real e persistente em CSV |
| Índice 0–100 | Protótipo, precisa validação de campo |
| Pontos sem foto | Demonstração |
| Rota operacional | Protótipo |

## 7. Referência para medir centímetros

O algoritmo atual usa uma referência de **21 cm** para converter pixels em centímetros.

A foto deve conter a referência configurada junto à vegetação.

Sem a referência, o sistema consegue detectar cobertura, mas não consegue calcular uma altura confiável em centímetros.

Se a iluminação ou as cores mudarem, ajuste os valores HSV em `medir_grama.py` ou use `calibracao_cor.py`.

## 8. Arquitetura

```text
Celular
   ↓
Foto
   ↓
OpenCV
   ↓
Altura + cobertura
   ↓
KM + áreas de roçada + clima + histórico
   ↓
Índice de Prioridade 0–100
   ↓
Mapa operacional
   ↓
Central de Operações
   ↓
Decisão: onde mandar a equipe primeiro?
```
