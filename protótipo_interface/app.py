import os
import sys
import glob
import hashlib
from datetime import datetime

import cv2
import numpy as np
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

# ============================================================
# GREENSENSE — CENTRAL DE INTELIGÊNCIA OPERACIONAL
# ============================================================

st.set_page_config(
    page_title="GreenSense | Motiva",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOTOS_DIR = os.path.join(BASE_DIR, "fotos_medicoes")
os.makedirs(FOTOS_DIR, exist_ok=True)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from protótipo_interface.medir_grama import (
    REFERENCIA_LARGURA_CM,
    HSV_REF_MIN,
    HSV_REF_MAX,
    HSV_GRAMA_MIN,
    HSV_GRAMA_MAX,
    criar_mascara,
    encontrar_maior_contorno,
    formatar_medida,
)
import geo_data
import priority
import climate
import historico

# ============================================================
# ESTILO RESPONSIVO
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    div[data-testid="stMetricValue"] { font-size: 1.35rem; }
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        color: white;
    }
    @media (max-width: 700px) {
        .block-container { padding-left: .8rem; padding-right: .8rem; }
        div[data-testid="stMetricValue"] { font-size: 1.1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# VISÃO COMPUTACIONAL
# ============================================================

def analisar_imagem_grama(caminho_ou_frame):
    """Analisa caminho de imagem ou frame BGR do OpenCV."""
    if isinstance(caminho_ou_frame, str):
        frame = cv2.imread(caminho_ou_frame)
    else:
        frame = caminho_ou_frame.copy()

    if frame is None:
        return {"ok": False, "erro": "Não foi possível abrir a imagem."}

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mascara_ref = criar_mascara(hsv, HSV_REF_MIN, HSV_REF_MAX)
    mascara_grama = criar_mascara(hsv, HSV_GRAMA_MIN, HSV_GRAMA_MAX)

    contorno_ref = encontrar_maior_contorno(mascara_ref)
    contorno_grama = encontrar_maior_contorno(mascara_grama)

    pixels_por_cm = None

    if contorno_ref is not None:
        rx, ry, rw, rh = cv2.boundingRect(contorno_ref)
        if rw > 0:
            pixels_por_cm = rw / REFERENCIA_LARGURA_CM
        cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (255, 0, 0), 3)
        cv2.putText(
            frame,
            f"Referencia ({REFERENCIA_LARGURA_CM:.0f} cm)",
            (rx, max(25, ry - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 0, 0),
            2,
        )

    cobertura_pct = round(
        100.0 * np.count_nonzero(mascara_grama) / mascara_grama.size, 1
    )

    largura_cm = None
    altura_cm = None

    if contorno_grama is not None:
        gx, gy, gw, gh = cv2.boundingRect(contorno_grama)
        cv2.rectangle(frame, (gx, gy), (gx + gw, gy + gh), (0, 200, 0), 3)

        if pixels_por_cm:
            largura_cm = round(gw / pixels_por_cm, 1)
            altura_cm = round(gh / pixels_por_cm, 1)

            texto = (
                f"Largura: {formatar_medida(largura_cm)} | "
                f"Altura: {formatar_medida(altura_cm)}"
            )
            cv2.putText(
                frame,
                texto,
                (max(10, gx - 10), max(25, gy - 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.62,
                (0, 200, 0),
                2,
            )
    else:
        cv2.putText(
            frame,
            "VEGETACAO NAO DETECTADA",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 0, 255),
            2,
        )

    return {
        "ok": True,
        "pixels_por_cm": pixels_por_cm,
        "largura_cm": largura_cm,
        "altura_cm": altura_cm,
        "cobertura_pct": cobertura_pct,
        "mascara_ref": mascara_ref,
        "mascara_grama": mascara_grama,
        "imagem_anotada": cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
    }


def analisar_bytes_imagem(data):
    """Converte uma foto recebida do celular para OpenCV."""
    if not data:
        return {"ok": False, "erro": "Imagem vazia."}

    array = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)

    if frame is None:
        return {"ok": False, "erro": "O arquivo recebido não é uma imagem válida."}

    return analisar_imagem_grama(frame)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def listar_fotos_reais():
    extensoes = ("*.png", "*.jpg", "*.jpeg", "*.JPG", "*.PNG", "*.JPEG")
    arquivos = []
    for ext in extensoes:
        arquivos.extend(glob.glob(os.path.join(FOTOS_DIR, ext)))
    return sorted(arquivos, key=os.path.getmtime, reverse=True)


@st.cache_data(show_spinner=False)
def analisar_foto_cache(caminho, mtime):
    return analisar_imagem_grama(caminho)


@st.cache_data(show_spinner=False, ttl=1800)
def clima_cache(lat_round, lon_round):
    return climate.obter_clima_atual(lat_round, lon_round)


@st.cache_data(show_spinner=False)
def carregar_geo():
    return geo_data.carregar_dados_geograficos()


def id_deterministico(texto, mod, offset=0):
    h = int(hashlib.md5(texto.encode()).hexdigest(), 16)
    return offset + (h % mod)


def status_vegetacao(altura_cm):
    if altura_cm is None:
        return "SEM LEITURA"
    if altura_cm >= 70:
        return "CRÍTICO"
    if altura_cm >= 50:
        return "ATENÇÃO"
    return "NORMAL"


# ============================================================
# DADOS GEOGRÁFICOS
# ============================================================

geo = carregar_geo()

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("🌱 GreenSense")
    st.caption("Central de Inteligência Operacional")
    st.divider()

    if geo.fonte_real:
        st.success(
            f"Dados geográficos reais carregados "
            f"({', '.join(geo.arquivos_usados)})"
        )
    else:
        st.warning(
            "Modo demonstração geográfico. Coloque os arquivos .KMZ/.KML "
            "em `data/` para carregar as coordenadas reais."
        )

    st.caption(
        f"{len(geo.marcos)} marcos de KM • "
        f"{len(geo.areas_rocada)} áreas de roçada"
    )

    st.divider()
    st.subheader(" Medição")

    st.info(
        "No celular, use **Tirar foto** abaixo. "
        "Se o navegador bloquear a câmera por estar em HTTP, use "
        "**Enviar foto** ou abra o app por HTTPS."
    )

    camera_upload = st.camera_input(
        "Tirar foto com a câmera do celular",
        help="Requer HTTPS no navegador quando acessado pela rede.",
    )

    arquivo_upload = st.file_uploader(
        "Enviar foto",
        type=["jpg", "jpeg", "png"],
        help="Funciona mesmo em HTTP na rede local.",
    )

    fotos = listar_fotos_reais()
    caminho_foto = None
    foto_escolhida_nome = None
    analise_upload = None
    upload_id = None
    fonte_upload = None

    # Prioridade: câmera > upload de arquivo > foto já salva
    if camera_upload is not None:
        dados = camera_upload.getvalue()
        upload_id = sha256_bytes(dados)
        fonte_upload = "camera"
        analise_upload = analisar_bytes_imagem(dados)

        nome_salvo = f"celular_{upload_id[:16]}.jpg"
        caminho_salvo = os.path.join(FOTOS_DIR, nome_salvo)
        if not os.path.exists(caminho_salvo):
            with open(caminho_salvo, "wb") as f:
                f.write(dados)

    elif arquivo_upload is not None:
        dados = arquivo_upload.getvalue()
        upload_id = sha256_bytes(dados)
        fonte_upload = "upload"
        analise_upload = analisar_bytes_imagem(dados)

        extensao = os.path.splitext(arquivo_upload.name)[1].lower() or ".jpg"
        nome_salvo = f"celular_{upload_id[:16]}{extensao}"
        caminho_salvo = os.path.join(FOTOS_DIR, nome_salvo)
        if not os.path.exists(caminho_salvo):
            with open(caminho_salvo, "wb") as f:
                f.write(dados)

    elif fotos:
        opcoes_fotos = [os.path.basename(f) for f in fotos]
        foto_escolhida_nome = st.selectbox("Foto já salva", opcoes_fotos)
        caminho_foto = os.path.join(FOTOS_DIR, foto_escolhida_nome)

    marcos_labels = [m.km_label for m in geo.marcos] or ["—"]
    ponto_associado = st.selectbox(
        " Associar medição ao ponto/KM",
        marcos_labels,
        help="A medição fica vinculada a este marco no mapa e no histórico.",
    )

    mostrar_mascaras = st.toggle("Mostrar máscaras OpenCV", value=False)

    usar_clima_real = st.toggle(
        "Buscar clima real",
        value=False,
        help="Usa Open-Meteo para consultar temperatura, chuva, umidade e vento.",
    )

    st.divider()
    with st.expander("⚙️ Pesos do Índice de Prioridade"):
        pesos = {}
        for chave, valor_padrao in priority.PESOS_PADRAO.items():
            pesos[chave] = st.slider(
                chave.replace("_", " ").title(),
                0,
                40,
                valor_padrao,
            )


# ============================================================
# ANÁLISE DA FOTO
# ============================================================

analise_foto = analise_upload

if analise_foto is None and caminho_foto:
    try:
        analise_foto = analisar_foto_cache(
            caminho_foto,
            os.path.getmtime(caminho_foto),
        )
        if analise_foto.get("ok"):
            with open(caminho_foto, "rb") as f:
                upload_id = sha256_bytes(f.read())
            fonte_upload = "arquivo"
    except Exception as exc:
        analise_foto = {"ok": False, "erro": str(exc)}

# Registra a foto somente uma vez.
if (
    analise_foto
    and analise_foto.get("ok")
    and analise_foto.get("altura_cm") is not None
    and upload_id
):
    historico.registrar_medicao(
        ponto_associado,
        analise_foto.get("altura_cm"),
        analise_foto.get("cobertura_pct"),
        analise_foto.get("largura_cm"),
        fonte=fonte_upload or "foto",
        medicao_id=upload_id,
    )


# ============================================================
# PONTOS OPERACIONAIS
# ============================================================

def montar_pontos_operacionais():
    pontos = []

    for marco in geo.marcos:
        pid = marco.km_label

        eh_foto_real = (
            pid == ponto_associado
            and analise_foto
            and analise_foto.get("ok")
            and analise_foto.get("altura_cm") is not None
        )

        if eh_foto_real:
            altura = analise_foto.get("altura_cm")
            cobertura = analise_foto.get("cobertura_pct")
            tendencia = historico.tendencia_cm(pid)
            crescimento = max(tendencia, 0) if tendencia is not None else 1.5
            fonte = "foto real"
        else:
            seed = id_deterministico(pid, 1000)
            altura = 10 + (seed % 75)
            cobertura = 20 + (seed % 70)
            crescimento = 0.8 + (seed % 5) * 0.7
            tendencia = None
            fonte = "demonstração"

        criticidade_local = marco.extra.get("criticidade")
        try:
            criticidade_local = (
                float(criticidade_local)
                if criticidade_local is not None
                else None
            )
        except (TypeError, ValueError):
            criticidade_local = None

        if criticidade_local is None:
            criticidade_local = 30 + id_deterministico(pid + "loc", 60)

        dist_rocada, area_prox = geo_data.distancia_area_rocada_mais_proxima(
            marco.lat,
            marco.lon,
            geo.areas_rocada,
        )

        if usar_clima_real:
            clima_info = clima_cache(round(marco.lat, 2), round(marco.lon, 2))
        else:
            seed_clima = id_deterministico(pid + "clima", 100)
            clima_info = {
                "ok": False,
                "chuva_mm": (seed_clima % 15) / 2.0,
                "umidade_pct": 40 + (seed_clima % 40),
                "vento_kmh": 5 + (seed_clima % 20),
                "temperatura_c": 20 + (seed_clima % 10),
            }

        resultado = priority.calcular_prioridade(
            altura_cm=altura,
            cobertura_pct=cobertura,
            crescimento_cm_dia=crescimento,
            criticidade_local=criticidade_local,
            distancia_rocada_km=dist_rocada,
            chuva_mm=clima_info.get("chuva_mm"),
            umidade_pct=clima_info.get("umidade_pct"),
            tendencia_historica_cm=tendencia,
            pesos=pesos,
        )

        pontos.append(
            {
                "ponto_id": pid,
                "marco": marco,
                "altura_cm": altura,
                "cobertura_pct": cobertura,
                "crescimento_cm_dia": round(crescimento, 1),
                "fonte": fonte,
                "distancia_rocada_km": (
                    round(dist_rocada, 2)
                    if dist_rocada is not None
                    else None
                ),
                "area_rocada_proxima": area_prox.nome if area_prox else None,
                "clima": clima_info,
                "resultado": resultado,
            }
        )

    return pontos


pontos_operacionais = montar_pontos_operacionais()
pontos_ordenados = sorted(
    pontos_operacionais,
    key=lambda p: p["resultado"].indice,
    reverse=True,
)


# ============================================================
# CABEÇALHO
# ============================================================

st.title("🌱 GreenSense")
st.caption("Onde devemos mandar a equipe primeiro — e por quê.")

if analise_foto and analise_foto.get("ok") and upload_id:
    st.success(
        f" Foto recebida e associada a **{ponto_associado}**. "
        "A medição real já foi considerada no índice."
    )

tab_geral, tab_mapa, tab_ops, tab_analise, tab_historico, tab_sobre = st.tabs(
    [
        " Visão Geral",
        " Mapa",
        " Operações",
        " Análise",
        " Histórico",
        " Sobre",
    ]
)


# ============================================================
# VISÃO GERAL
# ============================================================

with tab_geral:
    n_intervencao = sum(
        p["resultado"].nivel == "Intervenção"
        for p in pontos_operacionais
    )
    n_alta = sum(
        p["resultado"].nivel == "Alta prioridade"
        for p in pontos_operacionais
    )
    n_monitorar = sum(
        p["resultado"].nivel == "Monitorar"
        for p in pontos_operacionais
    )
    n_normal = sum(
        p["resultado"].nivel == "Normal"
        for p in pontos_operacionais
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Pontos", len(pontos_operacionais))
    c2.metric(" Intervenção", n_intervencao)
    c3.metric(" Alta", n_alta)
    c4.metric(" Monitorar", n_monitorar)
    c5.metric(" Normal", n_normal)

    if not geo.fonte_real:
        st.info(
            "Os pontos geográficos estão em modo demonstração. "
            "Adicione os arquivos reais em `data/`."
        )

    st.divider()
    st.subheader("Top 5 — atenção imediata")

    for p in pontos_ordenados[:5]:
        r = p["resultado"]
        col_a, col_b = st.columns([3, 1])

        with col_a:
            st.markdown(
                f"<span class='badge' style='background:{r.cor}'>{r.nivel}</span> "
                f"**{p['ponto_id']}** — "
                f"{p['altura_cm']:.0f} cm de altura, "
                f"{p['cobertura_pct']:.0f}% de cobertura",
                unsafe_allow_html=True,
            )

        with col_b:
            st.metric("Índice", f"{r.indice:.0f}/100")


# ============================================================
# MAPA
# ============================================================

with tab_mapa:
    st.subheader(" Mapa operacional")

    if not geo.fonte_real:
        st.warning("Coordenadas demonstrativas — adicione os KMZ/KML reais.")

    if pontos_operacionais:
        lat_centro = sum(p["marco"].lat for p in pontos_operacionais) / len(
            pontos_operacionais
        )
        lon_centro = sum(p["marco"].lon for p in pontos_operacionais) / len(
            pontos_operacionais
        )
    else:
        lat_centro, lon_centro = -23.5, -46.7

    mapa = folium.Map(
        location=[lat_centro, lon_centro],
        zoom_start=10,
        tiles="CartoDB positron",
    )

    for p in pontos_operacionais:
        r = p["resultado"]

        folium.CircleMarker(
            location=[p["marco"].lat, p["marco"].lon],
            radius=9,
            color=r.cor,
            fill=True,
            fill_color=r.cor,
            fill_opacity=0.85,
            popup=folium.Popup(
                f"<b>{p['ponto_id']}</b><br>"
                f"Índice: {r.indice:.0f}/100 — {r.nivel}<br>"
                f"Altura: {p['altura_cm']:.0f} cm<br>"
                f"Fonte: {p['fonte']}",
                max_width=260,
            ),
            tooltip=f"{p['ponto_id']} — {r.nivel} ({r.indice:.0f})",
        ).add_to(mapa)

    for area in geo.areas_rocada[:300]:
        folium.CircleMarker(
            location=[area.centroid_lat, area.centroid_lon],
            radius=3,
            color="#607d8b",
            fill=True,
            fill_opacity=0.5,
            tooltip=f"Roçada: {area.nome}",
        ).add_to(mapa)

    st_folium(mapa, width=None, height=520, returned_objects=[])

    st.markdown(
        " Intervenção &nbsp;&nbsp;  Alta prioridade &nbsp;&nbsp; "
        " Monitorar &nbsp;&nbsp;  Normal &nbsp;&nbsp; "
        " Área de roçada"
    )


# ============================================================
# CENTRAL DE OPERAÇÕES
# ============================================================

with tab_ops:
    st.subheader(" Central de Operações")

    ordenar_por = st.radio(
        "Ordenar por",
        ["Prioridade (recomendado)", "KM (rota sequencial)"],
        horizontal=True,
    )

    lista = (
        pontos_ordenados
        if ordenar_por.startswith("Prioridade")
        else sorted(pontos_operacionais, key=lambda p: p["ponto_id"])
    )

    tabela = pd.DataFrame(
        [
            {
                "Prioridade": p["resultado"].nivel,
                "Ponto": p["ponto_id"],
                "Índice": p["resultado"].indice,
                "Altura (cm)": p["altura_cm"],
                "Crescimento (cm/dia)": p["crescimento_cm_dia"],
                "Roçada mais próxima": (
                    f"{p['distancia_rocada_km']} km"
                    if p["distancia_rocada_km"] is not None
                    else "—"
                ),
                "Fonte": p["fonte"],
            }
            for p in lista
        ]
    )

    st.dataframe(tabela, width="stretch", hide_index=True)

    st.divider()
    st.subheader("Rota de inspeção sugerida")
    st.caption(
        "Protótipo: prioriza os trechos com maior índice. "
        "A rota final deve considerar logística, sentido e acesso real."
    )

    for i, p in enumerate(pontos_ordenados[:10], start=1):
        r = p["resultado"]
        st.markdown(
            f"**{i}.** {p['ponto_id']} — "
            f"{r.nivel} ({r.indice:.0f}/100)"
        )

    if pontos_ordenados:
        with st.expander(
            f"Por que {pontos_ordenados[0]['ponto_id']} está no topo?"
        ):
            r = pontos_ordenados[0]["resultado"]

            for fator, contrib in sorted(
                r.contribuicoes.items(),
                key=lambda x: -x[1],
            ):
                st.write(
                    f"- **{fator.replace('_', ' ').title()}**: "
                    f"{contrib:.1f} pontos "
                    f"(nota bruta {r.fatores[fator]:.0f}/100)"
                )


# ============================================================
# ANÁLISE
# ============================================================

with tab_analise:
    st.subheader("📷 Análise de Vegetação")

    if not analise_foto:
        st.info(
            "Abra a barra lateral e use **Tirar foto** ou **Enviar foto**. "
            "No computador, também é possível selecionar uma foto já salva."
        )

    elif not analise_foto.get("ok"):
        st.error(analise_foto.get("erro", "Erro desconhecido na análise."))

    else:
        left, right = st.columns([1.6, 1])

        with left:
            st.image(
                analise_foto["imagem_anotada"],
                caption="Resultado da análise OpenCV",
                width="stretch",
            )

        with right:
            altura = analise_foto.get("altura_cm")
            largura = analise_foto.get("largura_cm")
            cobertura = analise_foto.get("cobertura_pct")
            escala = analise_foto.get("pixels_por_cm")

            if altura is not None:
                st.success(
                    f"🌿 Vegetação detectada — {status_vegetacao(altura)}"
                )

                a1, a2 = st.columns(2)
                a1.metric("Altura", formatar_medida(altura))
                a2.metric(
                    "Largura",
                    formatar_medida(largura) if largura else "—",
                )
                st.metric(
                    "Cobertura da cena",
                    f"{cobertura:.0f}%",
                )

                if pontos_operacionais:
                    ponto = next(
                        (
                            p
                            for p in pontos_operacionais
                            if p["ponto_id"] == ponto_associado
                        ),
                        None,
                    )
                    if ponto:
                        st.metric(
                            "Índice do trecho",
                            f"{ponto['resultado'].indice:.0f}/100",
                        )
                        st.caption(
                            f"Classificação: **{ponto['resultado'].nivel}**"
                        )
            else:
                st.warning(
                    "Vegetação não detectada. "
                    "Confira a iluminação, enquadramento e calibração HSV."
                )

            st.metric(
                "Escala",
                f"{escala:.1f} px/cm" if escala else "sem referência",
            )

            st.caption(
                f" Ponto associado: **{ponto_associado}**"
            )

        if mostrar_mascaras:
            m1, m2 = st.columns(2)
            m1.image(
                analise_foto["mascara_ref"],
                caption="Máscara — referência",
                clamp=True,
            )
            m2.image(
                analise_foto["mascara_grama"],
                caption="Máscara — vegetação",
                clamp=True,
            )

    st.divider()
    st.markdown(
        """
### 📱 Como usar com o celular

**Opção 1 — HTTPS:** use **Tirar foto** diretamente.

**Opção 2 — rede local HTTP:** se o navegador bloquear a câmera,
use **Enviar foto**. O processamento continua sendo feito pelo computador.

Isso é uma limitação de segurança do navegador, não do OpenCV/GreenSense.
        """
    )


# ============================================================
# HISTÓRICO
# ============================================================

with tab_historico:
    st.subheader(" Histórico de medições")

    pontos_com_historico = historico.todos_pontos_com_historico()

    if not pontos_com_historico:
        st.info(
            "Ainda não há medições reais. "
            "Tire ou envie uma foto para começar o histórico."
        )
    else:
        ponto_hist = st.selectbox(
            "Ponto",
            pontos_com_historico,
        )

        df_hist = historico.historico_do_ponto(ponto_hist)

        st.dataframe(
            df_hist,
            width="stretch",
            hide_index=True,
        )

        if len(df_hist.dropna(subset=["altura_cm"])) >= 2:
            st.line_chart(
                df_hist.set_index("timestamp")["altura_cm"]
            )

            tendencia = historico.tendencia_cm(ponto_hist)

            if tendencia is not None:
                direcao = (
                    "crescendo"
                    if tendencia > 0
                    else "estável/reduzindo"
                )

                st.caption(
                    f"Tendência recente: {tendencia:+.1f} cm "
                    f"({direcao})."
                )
        else:
            st.caption(
                "Registre pelo menos duas medições do ponto "
                "para visualizar a evolução."
            )


# ============================================================
# SOBRE
# ============================================================

with tab_sobre:
    st.subheader(" Sobre o GreenSense")

    st.markdown(
        """
O GreenSense não quer apenas responder **"quanto mede a grama?"**.

Ele foi pensado para responder:

> **"Onde a Motiva deve mandar a equipe primeiro e por quê?"**

### Arquitetura

```text
 Câmera do celular
        ↓
 Foto
        ↓
OpenCV
        ↓
Detecção da vegetação
        ↓
Altura + cobertura
        ↓
 KM + área de roçada
 Clima
 Histórico
        ↓
 Índice de Prioridade 0–100
        ↓
 Mapa operacional
        ↓
 Central de Operações
        ↓
 Decisão de campo
```

### Status do protótipo

-  Interface Streamlit
-  Câmera/upload pelo celular
-  OpenCV para análise da foto
-  Dados geográficos KMZ/KML
-  Mapa Folium
-  Índice de Prioridade
-  Histórico sem duplicar a mesma foto
-  Clima real via Open-Meteo
-  Índice ainda precisa de validação de campo
        """
    )

    st.divider()

    if geo.fonte_real:
        st.success(
            "Os dados geográficos atuais estão sendo carregados dos arquivos reais."
        )
    else:
        st.warning(
            "Os dados geográficos ainda estão em modo demonstração."
        )

    st.markdown(
        """
###  Acesso pelo celular

Para rodar na mesma rede:

```bash
streamlit run app.py --server.address 0.0.0.0
```

Depois abra no celular:

```text
http://IP-DO-COMPUTADOR:8501
```

Para usar a câmera diretamente, prefira uma URL **HTTPS**.
        """
    )

st.divider()
st.caption(
    "GreenSense — protótipo Motiva • Visão computacional + geointeligência + priorização operacional"
)
