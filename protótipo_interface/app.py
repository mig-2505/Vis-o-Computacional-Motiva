import streamlit as st
import pandas as pd
import numpy as np
import cv2
from datetime import datetime, timedelta
import time

# ============================================================
# GREEN SENSE — MONITORAMENTO INTELIGENTE DE VEGETAÇÃO
# ============================================================

st.set_page_config(
    page_title="GreenSense | Motiva",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CONFIGURAÇÕES DO PROJETO
# ============================================================

TOTAL_CAMERAS = 18
TOTAL_SENSORS = 36
TOTAL_KM = 180

# ============================================================
# CÂMERAS
# ============================================================

CAMERAS = {
    "CAM-01": {
        "km": "KM 001+200",
        "sentido": "Norte",
        "status": "online",
    },
    "CAM-02": {
        "km": "KM 014+800",
        "sentido": "Sul",
        "status": "online",
    },
    "CAM-03": {
        "km": "KM 027+500",
        "sentido": "Norte",
        "status": "online",
    },
    "CAM-04": {
        "km": "KM 041+100",
        "sentido": "Sul",
        "status": "online",
    },
    "CAM-05": {
        "km": "KM 055+700",
        "sentido": "Norte",
        "status": "online",
    },
    "CAM-06": {
        "km": "KM 068+300",
        "sentido": "Sul",
        "status": "online",
    },
    "CAM-07": {
        "km": "KM 081+900",
        "sentido": "Norte",
        "status": "online",
    },
    "CAM-08": {
        "km": "KM 095+400",
        "sentido": "Sul",
        "status": "online",
    },
    "CAM-09": {
        "km": "KM 108+200",
        "sentido": "Norte",
        "status": "online",
    },
    "CAM-10": {
        "km": "KM 121+600",
        "sentido": "Sul",
        "status": "online",
    },
    "CAM-11": {
        "km": "KM 134+100",
        "sentido": "Norte",
        "status": "online",
    },
    "CAM-12": {
        "km": "KM 146+800",
        "sentido": "Sul",
        "status": "online",
    },
    "CAM-13": {
        "km": "KM 158+300",
        "sentido": "Norte",
        "status": "online",
    },
    "CAM-14": {
        "km": "KM 166+700",
        "sentido": "Sul",
        "status": "online",
    },
    "CAM-15": {
        "km": "KM 171+200",
        "sentido": "Norte",
        "status": "online",
    },
    "CAM-16": {
        "km": "KM 175+400",
        "sentido": "Sul",
        "status": "online",
    },
    "CAM-17": {
        "km": "KM 178+100",
        "sentido": "Norte",
        "status": "online",
    },
    "CAM-18": {
        "km": "KM 179+600",
        "sentido": "Sul",
        "status": "offline",
    },
}

# ============================================================
# RTSP
# ============================================================
#
# Quando tiver as câmeras reais, coloque os endereços aqui.
#
# Exemplo:
#
# "CAM-01":
#     "rtsp://usuario:senha@192.168.1.100:554/stream"
#
# ============================================================

RTSP_URLS = {
    camera_id: ""
    for camera_id in CAMERAS
}


# ============================================================
# DADOS DOS SENSORES
# ============================================================

def dados_sensores(sensor_index):

    """
    Dados DEMONSTRATIVOS.

    Futuramente substituir por MQTT/API
    dos sensores reais.
    """

    temperatura = (
        23.5
        + (sensor_index % 5) * 0.8
    )

    umidade_solo = (
        48
        + (sensor_index * 3) % 35
    )

    chuva = (
        0.0
        if sensor_index % 4
        else 2.4
    )

    vento = (
        8
        + (sensor_index % 9)
    )

    return {
        "temperatura": temperatura,
        "umidade_solo": umidade_solo,
        "chuva": chuva,
        "vento": vento,
    }


# ============================================================
# VISÃO COMPUTACIONAL
# ============================================================

def dados_visao(camera_index):

    """
    Protótipo.

    Aqui futuramente entra o resultado
    real da visão computacional.
    """

    altura = (
        25
        + (camera_index * 7) % 60
    )

    cobertura = (
        92
        - (camera_index * 3) % 35
    )

    if altura >= 70:

        status = "CRÍTICO"

    elif altura >= 50:

        status = "ATENÇÃO"

    else:

        status = "NORMAL"

    return {
        "altura": float(altura),
        "cobertura": float(cobertura),
        "status": status,
    }


# ============================================================
# MACHINE LEARNING
# ============================================================

def dados_ia(
    camera_index,
    sensor,
):

    """
    PROTÓTIPO da camada preditiva.

    Não é um modelo treinado.

    Aqui futuramente entra o modelo
    de Machine Learning real.
    """

    crescimento = (
        2.0
        + sensor["temperatura"] * 0.10
        + sensor["umidade_solo"] * 0.015
        + camera_index * 0.08
    )

    crescimento = round(
        crescimento,
        1
    )

    if crescimento > 7:

        dias_corte = 3

    elif crescimento > 5:

        dias_corte = 5

    else:

        dias_corte = 7

    confianca = min(
        97,
        max(
            75,
            82 + camera_index % 15
        ),
    )

    data_corte = (
        datetime.now()
        + timedelta(
            days=dias_corte
        )
    )

    return {
        "crescimento": crescimento,
        "dias_corte": dias_corte,
        "confianca": confianca,
        "data_corte": data_corte,
    }


# ============================================================
# IMAGEM DEMONSTRATIVA DA CÂMERA
# ============================================================

def gerar_camera_demo(
    index,
    altura,
):

    frame = np.zeros(
        (420, 700, 3),
        dtype=np.uint8,
    )

    # Céu
    frame[:245] = (
        195,
        215,
        230,
    )

    # Solo
    frame[245:] = (
        52,
        92,
        42,
    )

    rng = np.random.default_rng(
        500 + index
    )

    quantidade = int(
        80 + altura * 2
    )

    for _ in range(
        quantidade
    ):

        x = int(
            rng.integers(
                0,
                700,
            )
        )

        base = int(
            rng.integers(
                275,
                420,
            )
        )

        h = int(
            rng.integers(
                max(
                    10,
                    int(
                        altura * 0.4
                    ),
                ),
                max(
                    20,
                    int(
                        altura * 1.4
                    ),
                ),
            )
        )

        cv2.line(
            frame,
            (x, base),
            (
                x
                + int(
                    rng.integers(
                        -8,
                        9,
                    )
                ),
                base - h,
            ),
            (
                35,
                145,
                45,
            ),
            2,
        )

    cv2.putText(
        frame,
        "CAMERA - DEMONSTRACAO",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (
            255,
            255,
            255,
        ),
        2,
    )

    return cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB,
    )


# ============================================================
# RTSP
# ============================================================

def obter_frame_rtsp(
    camera_id
):

    url = RTSP_URLS.get(
        camera_id,
        "",
    )

    if not url:

        return None

    cap = cv2.VideoCapture(
        url
    )

    if not cap.isOpened():

        return None

    ok, frame = cap.read()

    cap.release()

    if not ok:

        return None

    return cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB,
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title(
        "🌱 GreenSense"
    )

    st.caption(
        "Monitoramento inteligente"
    )

    st.divider()

    modo_demo = st.toggle(
        "Modo demonstração",
        value=True,
    )

    intervalo = st.slider(
        "Atualização",
        min_value=1,
        max_value=10,
        value=3,
    )

    st.divider()

    cameras_selecionadas = st.multiselect(
        "Câmeras exibidas",
        list(
            CAMERAS.keys()
        ),
        default=list(
            CAMERAS.keys()
        )[:4],
    )

    st.divider()

    st.subheader(
        "Conexões"
    )

    st.success(
        "Sensores: preparado para MQTT"
    )

    st.success(
        "Câmeras: preparado para RTSP"
    )

    st.info(
        "IA: preparado para modelo ML"
    )


# ============================================================
# CABEÇALHO
# ============================================================

st.title(
    "🌱 GreenSense"
)

st.caption(
    "Sistema de Monitoramento Inteligente de Vegetação"
)

st.markdown(
    """
    **Monitoramento preditivo •
    Visão Computacional •
    IoT •
    Machine Learning**
    """
)

st.divider()


# ============================================================
# INDICADORES GERAIS
# ============================================================

camera_online = sum(
    1
    for camera in CAMERAS.values()
    if camera["status"] == "online"
)

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "📹 Câmeras",
    f"{camera_online}/{TOTAL_CAMERAS}",
)

k2.metric(
    "📡 Sensores IoT",
    f"{TOTAL_SENSORS}/{TOTAL_SENSORS}",
)

k3.metric(
    "🛣️ Trecho monitorado",
    f"{TOTAL_KM} km",
)

k4.metric(
    "⚠️ Alertas",
    "3",
)

k5.metric(
    "🤖 Confiança IA",
    "91%",
)

st.divider()


# ============================================================
# CÂMERAS
# ============================================================

st.header(
    "📹 Monitoramento das câmeras"
)

if not cameras_selecionadas:

    st.warning(
        "Selecione pelo menos "
        "uma câmera."
    )

else:

    for inicio in range(
        0,
        len(
            cameras_selecionadas
        ),
        2,
    ):

        linha = cameras_selecionadas[
            inicio:inicio + 2
        ]

        colunas = st.columns(
            2
        )

        for coluna, camera_id in zip(
            colunas,
            linha,
        ):

            camera_index = list(
                CAMERAS.keys()
            ).index(
                camera_id
            )

            camera = CAMERAS[
                camera_id
            ]

            sensor = dados_sensores(
                camera_index
            )

            visao = dados_visao(
                camera_index
            )

            ia = dados_ia(
                camera_index,
                sensor,
            )

            with coluna:

                # ============================================
                # IDENTIFICAÇÃO
                # ============================================

                st.subheader(
                    f"📍 {camera_id}"
                )

                st.caption(
                    f"{camera['km']} • "
                    f"Sentido {camera['sentido']}"
                )

                # ============================================
                # IMAGEM
                # ============================================

                frame = None

                if not modo_demo:

                    frame = obter_frame_rtsp(
                        camera_id
                    )

                if frame is None:

                    frame = gerar_camera_demo(
                        camera_index,
                        visao["altura"],
                    )

                st.image(
                    frame,
                    use_container_width=True,
                )

                # ============================================
                # STATUS
                # ============================================

                status = visao[
                    "status"
                ]

                if status == "CRÍTICO":

                    st.error(
                        "🔴 VEGETAÇÃO CRÍTICA"
                    )

                elif status == "ATENÇÃO":

                    st.warning(
                        "🟡 ATENÇÃO — crescimento elevado"
                    )

                else:

                    st.success(
                        "🟢 VEGETAÇÃO NORMAL"
                    )

                # ============================================
                # VISÃO COMPUTACIONAL
                # ============================================

                st.markdown(
                    "**🌱 Análise da vegetação**"
                )

                v1, v2, v3 = st.columns(
                    3
                )

                v1.metric(
                    "Altura",
                    f"{visao['altura']:.1f} cm",
                )

                v2.metric(
                    "Cobertura",
                    f"{visao['cobertura']:.1f}%",
                )

                v3.metric(
                    "Local",
                    camera["km"],
                )

                # ============================================
                # SENSORES
                # ============================================

                st.markdown(
                    "**📡 Dados dos sensores IoT**"
                )

                s1, s2, s3, s4 = st.columns(
                    4
                )

                s1.metric(
                    "🌡️ Temperatura",
                    f"{sensor['temperatura']:.1f} °C",
                )

                s2.metric(
                    "💧 Umidade solo",
                    f"{sensor['umidade_solo']}%",
                )

                s3.metric(
                    "🌧️ Chuva",
                    f"{sensor['chuva']:.1f} mm",
                )

                s4.metric(
                    "💨 Vento",
                    f"{sensor['vento']} km/h",
                )

                # ============================================
                # IA
                # ============================================

                st.markdown(
                    "**🤖 Previsão do modelo**"
                )

                p1, p2, p3 = st.columns(
                    3
                )

                p1.metric(
                    "Crescimento",
                    f"{ia['crescimento']} cm/dia",
                )

                p2.metric(
                    "Próximo corte",
                    f"{ia['dias_corte']} dias",
                )

                p3.metric(
                    "Confiança",
                    f"{ia['confianca']}%",
                )

                st.caption(
                    "Corte previsto para "
                    + ia[
                        "data_corte"
                    ].strftime(
                        "%d/%m/%Y"
                    )
                )


# ============================================================
# MAPA
# ============================================================

st.divider()

st.header(
    "🗺️ Pontos de monitoramento"
)

mapa = pd.DataFrame(
    {
        "latitude": [
            -23.45,
            -23.47,
            -23.49,
            -23.51,
            -23.53,
            -23.55,
            -23.57,
            -23.59,
        ],
        "longitude": [
            -46.65,
            -46.67,
            -46.69,
            -46.71,
            -46.73,
            -46.75,
            -46.77,
            -46.79,
        ],
    }
)

st.map(
    mapa,
    latitude="latitude",
    longitude="longitude",
    size=30,
)


# ============================================================
# ALERTAS
# ============================================================

st.divider()

st.header(
    "🚨 Central de alertas"
)

alertas = pd.DataFrame(
    [
        {
            "Prioridade": "🔴 CRÍTICO",
            "Ponto": "CAM-11",
            "Local": "KM 134+100",
            "Evento": "Vegetação acima do limite",
            "Ação": "Programar manutenção",
        },
        {
            "Prioridade": "🟡 ATENÇÃO",
            "Ponto": "CAM-04",
            "Local": "KM 041+100",
            "Evento": "Crescimento acelerado",
            "Ação": "Monitorar",
        },
        {
            "Prioridade": "🟡 ATENÇÃO",
            "Ponto": "CAM-15",
            "Local": "KM 171+200",
            "Evento": "Baixa cobertura vegetal",
            "Ação": "Investigar",
        },
    ]
)

st.dataframe(
    alertas,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# HISTÓRICO
# ============================================================

st.divider()

st.header(
    "📈 Histórico"
)

historico = pd.DataFrame(
    {
        "Dia": [
            "06/08",
            "07/08",
            "08/08",
            "09/08",
            "10/08",
            "11/08",
            "12/08",
        ],
        "Altura média (cm)": [
            35,
            36,
            38,
            40,
            42,
            43,
            45,
        ],
        "Cobertura (%)": [
            91,
            89,
            88,
            86,
            85,
            83,
            81,
        ],
    }
)

c1, c2 = st.columns(
    2
)

with c1:

    st.markdown(
        "**🌱 Altura média**"
    )

    st.line_chart(
        historico.set_index(
            "Dia"
        )[
            "Altura média (cm)"
        ]
    )

with c2:

    st.markdown(
        "**🌿 Cobertura vegetal**"
    )

    st.line_chart(
        historico.set_index(
            "Dia"
        )[
            "Cobertura (%)"
        ]
    )


# ============================================================
# RODAPÉ
# ============================================================

st.divider()

st.caption(
    "GreenSense — Protótipo de interface. "
    "Dados demonstrativos preparados para "
    "integração com RTSP, MQTT e Machine Learning."
)


# ============================================================
# ATUALIZAÇÃO
# ============================================================

time.sleep(
    intervalo
)

st.rerun()