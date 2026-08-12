import streamlit as st
import cv2
import numpy as np
import time
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="GreenGuard | Motiva",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CONFIGURAÇÃO DAS CÂMERAS
# ============================================================

CAMERAS = {
    "CAM-001": {
        "nome": "Ponto 01",
        "rodovia": "SP-XXX",
        "km": "123+400",
        "sentido": "Norte",
    },
    "CAM-002": {
        "nome": "Ponto 02",
        "rodovia": "SP-XXX",
        "km": "124+100",
        "sentido": "Sul",
    },
    "CAM-003": {
        "nome": "Ponto 03",
        "rodovia": "SP-XXX",
        "km": "126+700",
        "sentido": "Norte",
    },
    "CAM-004": {
        "nome": "Ponto 04",
        "rodovia": "SP-XXX",
        "km": "129+200",
        "sentido": "Sul",
    },
}

# ============================================================
# FONTES DAS CÂMERAS
# ============================================================
#
# Para testar:
# CAM-001 pode usar a webcam do computador com 0.
#
# Para câmera IP/RTSP:
#
# "rtsp://usuario:senha@192.168.1.100:554/stream"
#
# ============================================================

VIDEO_SOURCES = {
    "CAM-001": 0,
    "CAM-002": None,
    "CAM-003": None,
    "CAM-004": None,
}

VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

STATUS_NORMAL = "🟢 NORMAL"
STATUS_ATENCAO = "🟡 ATENÇÃO"
STATUS_CRITICO = "🔴 CRÍTICO"


# ============================================================
# VISÃO COMPUTACIONAL
# ============================================================

def analisar_vegetacao(frame):

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Faixa inicial para detectar vegetação
    lower = np.array([25, 35, 30])
    upper = np.array([95, 255, 255])

    mascara = cv2.inRange(
        hsv,
        lower,
        upper
    )

    kernel = np.ones(
        (5, 5),
        np.uint8
    )

    mascara = cv2.morphologyEx(
        mascara,
        cv2.MORPH_OPEN,
        kernel
    )

    mascara = cv2.morphologyEx(
        mascara,
        cv2.MORPH_CLOSE,
        kernel
    )

    # ========================================================
    # COBERTURA VEGETAL
    # ========================================================

    cobertura = (
        np.count_nonzero(mascara)
        / mascara.size
        * 100
    )

    resultado = frame.copy()

    # ========================================================
    # CONTORNOS
    # ========================================================

    contornos, _ = cv2.findContours(
        mascara,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    maior_area = 0
    maior_contorno = None

    for contorno in contornos:

        area = cv2.contourArea(contorno)

        if area > maior_area:

            maior_area = area
            maior_contorno = contorno

    altura_px = 0

    # ========================================================
    # DETECÇÃO DA VEGETAÇÃO
    # ========================================================

    if (
        maior_contorno is not None
        and maior_area > 500
    ):

        x, y, w, h = cv2.boundingRect(
            maior_contorno
        )

        altura_px = h

        cv2.rectangle(
            resultado,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            3
        )

        cv2.putText(
            resultado,
            "VEGETACAO",
            (x, max(30, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

    # ========================================================
    # CALIBRAÇÃO
    # ========================================================
    #
    # APENAS DEMONSTRATIVO.
    #
    # Na versão real:
    #
    # pixels_por_cm
    #
    # virá da calibração da câmera.
    #
    # ========================================================

    pixels_por_cm = 8.0

    if altura_px > 0:

        altura_cm = (
            altura_px
            / pixels_por_cm
        )

    else:

        altura_cm = 0

    # ========================================================
    # STATUS
    # ========================================================

    if altura_cm >= 80:

        status = STATUS_CRITICO

    elif altura_cm >= 50:

        status = STATUS_ATENCAO

    else:

        status = STATUS_NORMAL

    return (
        resultado,
        cobertura,
        altura_cm,
        status,
    )


# ============================================================
# CAPTURA DA CÂMERA
# ============================================================

def obter_frame(camera_id):

    source = VIDEO_SOURCES[camera_id]

    # --------------------------------------------------------
    # Procura vídeo local
    # --------------------------------------------------------

    video_file = (
        VIDEO_DIR
        / f"{camera_id.lower().replace('-', '')}.mp4"
    )

    if video_file.exists():

        source = str(video_file)

    # --------------------------------------------------------
    # Sem câmera configurada
    # --------------------------------------------------------

    if source is None:

        return None

    # --------------------------------------------------------
    # Abre câmera
    # --------------------------------------------------------

    cap = cv2.VideoCapture(
        source
    )

    if not cap.isOpened():

        return None

    ok, frame = cap.read()

    cap.release()

    if not ok:

        return None

    return frame


# ============================================================
# IMAGEM DEMONSTRATIVA
# ============================================================

def gerar_frame_demo(camera_index):

    frame = np.zeros(
        (480, 720, 3),
        dtype=np.uint8
    )

    # Céu
    frame[:280] = (
        210,
        225,
        235
    )

    # Solo
    frame[280:] = (
        55,
        95,
        45
    )

    # Vegetação fictícia
    rng = np.random.default_rng(
        camera_index + 100
    )

    for _ in range(120):

        x = int(
            rng.integers(
                0,
                720
            )
        )

        base_y = int(
            rng.integers(
                300,
                460
            )
        )

        altura = int(
            rng.integers(
                15,
                100
            )
        )

        cv2.line(
            frame,
            (x, base_y),
            (
                x + int(
                    rng.integers(
                        -8,
                        9
                    )
                ),
                base_y - altura,
            ),
            (40, 150, 45),
            2
        )

    cv2.putText(
        frame,
        "STREAM DEMONSTRATIVO",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2
    )

    return frame


# ============================================================
# DADOS AMBIENTAIS
# ============================================================

def dados_ambientais(index):

    # SIMULAÇÃO
    #
    # Depois substituir por:
    #
    # API meteorológica
    # sensor IoT
    # estação meteorológica
    #

    return {

        "temperatura":
            24.5 + index * 0.8,

        "umidade":
            67 + index * 2,

        "vento":
            11 + index,

        "chuva":
            0.0 if index % 3 else 1.2,

    }


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "GreenGuard"
    )

    st.caption(
        "Monitoramento de vegetação — Motiva"
    )

    st.divider()

    cameras_ativas = st.multiselect(

        "Câmeras exibidas",

        list(CAMERAS.keys()),

        default=list(
            CAMERAS.keys()
        ),
    )

    atualizar = st.slider(

        "Intervalo de atualização",

        min_value=1,

        max_value=10,

        value=2,
    )

    usar_demo = st.toggle(

        "Usar imagens demonstrativas",

        value=True,

        help=(
            "Ative enquanto "
            "as câmeras ainda "
            "não estiverem conectadas."
        ),
    )

    st.divider()

    st.subheader(
        "🔌 Conexão"
    )

    st.success(
        "Sistema online"
    )


# ============================================================
# CABEÇALHO
# ============================================================

st.title(
    "GreenGuard"
)

st.caption(
    "Central de Monitoramento de Vegetação — Motiva"
)


# ============================================================
# INDICADORES GERAIS
# ============================================================

h1, h2, h3, h4 = st.columns(4)

h1.metric(
    "Câmeras",
    f"{len(cameras_ativas)}/{len(CAMERAS)}"
)

h2.metric(
    "🟢 Normais",
    "3"
)

h3.metric(
    "🟡 Atenção",
    "1"
)

h4.metric(
    "🔴 Alertas",
    "0"
)

st.divider()


# ============================================================
# VERIFICAÇÃO
# ============================================================

if not cameras_ativas:

    st.warning(
        "Selecione pelo menos "
        "uma câmera no menu lateral."
    )

    st.stop()


# ============================================================
# CARDS DAS CÂMERAS
# ============================================================

for linha_inicio in range(
    0,
    len(cameras_ativas),
    2
):

    linha = cameras_ativas[
        linha_inicio:
        linha_inicio + 2
    ]

    cols = st.columns(2)

    for col, camera_id in zip(
        cols,
        linha
    ):

        info = CAMERAS[
            camera_id
        ]

        index = list(
            CAMERAS.keys()
        ).index(
            camera_id
        )

        ambiente = dados_ambientais(
            index
        )

        with col:

            st.subheader(
                f" {info['nome']} — {camera_id}"
            )

            st.caption(
                f"{info['rodovia']} • "
                f"KM {info['km']} • "
                f"Sentido {info['sentido']}"
            )

            # ------------------------------------------------
            # CAPTURA
            # ------------------------------------------------

            frame = None

            if not usar_demo:

                frame = obter_frame(
                    camera_id
                )

            # ------------------------------------------------
            # DEMO
            # ------------------------------------------------

            if frame is None:

                if usar_demo:

                    frame = gerar_frame_demo(
                        index
                    )

                    online = True

                else:

                    online = False

            else:

                online = True

            # ------------------------------------------------
            # ONLINE
            # ------------------------------------------------

            if online:

                (
                    resultado,
                    cobertura,
                    altura,
                    status,
                ) = analisar_vegetacao(
                    frame
                )

                resultado_rgb = cv2.cvtColor(
                    resultado,
                    cv2.COLOR_BGR2RGB
                )

                # ====================================================
                # IMAGEM DA CÂMERA
                # ====================================================

                st.image(
                    resultado_rgb,
                    use_container_width=True
                )

                # ====================================================
                # STATUS DA VEGETAÇÃO
                # ====================================================

                if status == STATUS_CRITICO:

                    st.error(
                        f"Status da vegetação: {status}"
                    )

                elif status == STATUS_ATENCAO:

                    st.warning(
                        f"Status da vegetação: {status}"
                    )

                else:

                    st.success(
                        f"Status da vegetação: {status}"
                    )

                # ====================================================
                # DADOS DA VEGETAÇÃO
                # ====================================================

                m1, m2 = st.columns(2)

                with m1:

                    st.metric(
                        "Altura",
                        f"{altura:.1f} cm"
                    )

                with m2:

                    st.metric(
                        "Cobertura",
                        f"{cobertura:.1f}%"
                    )

                # ====================================================
                # DADOS AMBIENTAIS
                # ====================================================

                e1, e2, e3, e4 = st.columns(4)

                with e1:

                    st.metric(
                        "Temperatura",
                        f"{ambiente['temperatura']:.1f} °C"
                    )

                with e2:

                    st.metric(
                        "Umidade",
                        f"{ambiente['umidade']}%"
                    )

                with e3:

                    st.metric(
                        "Vento",
                        f"{ambiente['vento']} km/h"
                    )

                with e4:

                    st.metric(
                        "Chuva",
                        f"{ambiente['chuva']:.1f} mm"
                    )

                st.caption(
                    "Última análise: "
                    + datetime.now().strftime(
                        "%d/%m/%Y %H:%M:%S"
                    )
                )

            # ------------------------------------------------
            # OFFLINE
            # ------------------------------------------------

            else:

                st.error(
                    "Câmera offline"
                )

                st.info(
                    "Configure o endereço RTSP "
                    "da câmera."
                )


# ============================================================
# ALERTAS
# ============================================================

st.divider()

st.header(
    "Alertas"
)

alertas = [

    {
        "camera": "CAM-002",
        "tipo": "Altura elevada",
        "descricao":
            "Vegetação acima do limite configurado.",
        "prioridade":
            "ATENÇÃO",
    },

    {
        "camera": "CAM-004",
        "tipo":
            "Cobertura reduzida",
        "descricao":
            "Possível alteração na cobertura vegetal.",
        "prioridade":
            "MONITORAR",
    },

]


for alerta in alertas:

    with st.container(
        border=True
    ):

        a, b, c = st.columns(
            [1, 2, 3]
        )

        with a:

            st.write(
                f"**{alerta['camera']}**"
            )

        with b:

            st.write(
                f"**{alerta['tipo']}**"
            )

        with c:

            st.write(
                alerta["descricao"]
            )


# ============================================================
# RESUMO
# ============================================================

st.divider()

st.header(
    "Resumo operacional"
)

r1, r2, r3, r4 = st.columns(4)

r1.metric(
    "Altura média",
    "42.8 cm"
)

r2.metric(
    "Cobertura média",
    "81.4%"
)

r3.metric(
    "Temperatura média",
    "25.7 °C"
)

r4.metric(
    "Pontos monitorados",
    len(cameras_ativas)
)

st.divider()

st.caption(
    "PROTÓTIPO — dados ambientais e "
    "imagens demonstrativas são simulados."
)


# ============================================================
# ATUALIZAÇÃO AUTOMÁTICA
# ============================================================

time.sleep(
    atualizar
)

st.rerun()