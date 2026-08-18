"""
Protótipo: medição de comprimento de grama usando visão computacional clássica.

IDEIA GERAL:
1. Você coloca na cena um OBJETO DE REFERÊNCIA de tamanho conhecido
   (ex: uma folha de papel A4, largura = 21 cm) junto com a grama.
2. O programa detecta os dois objetos por cor.
3. Calcula quantos pixels equivalem a 1 cm, usando a referência.
4. Usa essa escala para converter o tamanho da grama (em pixels) para cm/m.

REQUISITOS:
    pip install opencv-python numpy

COMO USAR (primeira vez):
1. Rode o script.
2. Uma janela vai abrir mostrando a câmera com uma máscara (preto/branco).
3. Ajuste os valores HSV_REF_* e HSV_GRAMA_* abaixo até a máscara
   isolar bem cada objeto (ver seção "AJUSTE DE CORES" mais abaixo).
4. Aperte 'q' para sair.
"""

import cv2
import numpy as np
import os
from datetime import datetime

# Pasta onde as fotos com resultado da medição serão salvas.
PASTA_FOTOS = "fotos_medicoes"
os.makedirs(PASTA_FOTOS, exist_ok=True)
contador_fotos = 0

# =========================================================
# CONFIGURAÇÕES QUE VOCÊ VAI PRECISAR AJUSTAR
# =========================================================

# Tamanho real do objeto de referência (em cm).
# Folha A4 na VERTICAL (em pé): largura = 21 cm.
REFERENCIA_LARGURA_CM = 21.0

# Faixa de cor (HSV) do objeto de referência (folha A4 vermelha/laranja).
# Calibrado ao ar livre, luz do sol, com o calibracao_cor.py.
HSV_REF_MIN = (156, 56, 127)
HSV_REF_MAX = (179, 255, 189)

# Faixa de cor (HSV) da grama (tons de verde).
# Calibrado com grama real, ao ar livre, luz do sol (com leve overexposure).
HSV_GRAMA_MIN = (24, 41, 28)
HSV_GRAMA_MAX = (91, 255, 255)

# Área mínima (em pixels) para considerar um contorno válido.
# Evita que ruído pequeno seja detectado como objeto.
AREA_MINIMA = 500


def encontrar_maior_contorno(mascara):
    """Recebe uma máscara binária e retorna o maior contorno encontrado."""
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return None

    maior = max(contornos, key=cv2.contourArea)
    if cv2.contourArea(maior) < AREA_MINIMA:
        return None
    return maior


def criar_mascara(frame_hsv, cor_min, cor_max):
    """Cria uma máscara binária isolando pixels dentro da faixa de cor."""
    mascara = cv2.inRange(frame_hsv, cor_min, cor_max)
    # Operações morfológicas para limpar ruído
    kernel = np.ones((5, 5), np.uint8)
    mascara = cv2.erode(mascara, kernel, iterations=1)
    mascara = cv2.dilate(mascara, kernel, iterations=2)
    return mascara


def formatar_medida(cm):
    """Converte automaticamente para metros se a medida for grande."""
    if cm >= 100:
        return f"{cm / 100:.2f} m"
    return f"{cm:.1f} cm"


def main():
    cap = cv2.VideoCapture(0)  # 0 = webcam padrão
    global contador_fotos

    if not cap.isOpened():
        print("Erro: não consegui acessar a câmera.")
        return

    print("Pressione 'q' para sair.")
    print("Pressione ESPAÇO para salvar uma foto do resultado atual.")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Erro ao capturar frame.")
            break

        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # --- Detecta o objeto de referência ---
        mascara_ref = criar_mascara(frame_hsv, HSV_REF_MIN, HSV_REF_MAX)
        contorno_ref = encontrar_maior_contorno(mascara_ref)

        pixels_por_cm = None

        if contorno_ref is not None:
            x, y, w, h = cv2.boundingRect(contorno_ref)
            pixels_por_cm = w / REFERENCIA_LARGURA_CM
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(frame, "Referencia", (x, y - 10),cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        # --- Detecta a grama ---
        mascara_grama = criar_mascara(frame_hsv, HSV_GRAMA_MIN, HSV_GRAMA_MAX)
        contorno_grama = encontrar_maior_contorno(mascara_grama)

        if contorno_grama is not None:
            x, y, w, h = cv2.boundingRect(contorno_grama)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            if pixels_por_cm:
                largura_cm = w / pixels_por_cm
                altura_cm = h / pixels_por_cm
                texto_largura = formatar_medida(largura_cm)
                texto_altura = formatar_medida(altura_cm)
            else:
                texto_largura = "sem referencia"
                texto_altura = "sem referencia"

            # Mostra as duas medidas: largura (extensão horizontal) e
            # altura (crescimento vertical). Qual delas importa depende
            # do ângulo/posição em que a câmera está instalada.
            cv2.putText(frame, f"Largura: {texto_largura}", (x, y - 30),cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, f"Altura: {texto_altura}", (x, y - 10),cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # --- Mostra status da referência ---
            if pixels_por_cm is None:
                cv2.putText(frame, "REFERENCIA NAO ENCONTRADA", (10, 30),cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.putText(frame, f"Escala: {pixels_por_cm:.1f} px/cm", (10, 30),cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # --- Mostra quantas fotos foram tiradas ---
            cv2.putText(frame, f"Fotos salvas: {contador_fotos}", (10, 60),cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # --- Mostra as janelas ---
        cv2.imshow("Camera", frame)
        cv2.imshow("Mascara Referencia", mascara_ref)
        cv2.imshow("Mascara Grama", mascara_grama)

        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord('q'):
            break

        elif tecla == ord(' '):
            contador_fotos += 1
            nome_arquivo = f"medicao_{contador_fotos}_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.png"
            caminho_completo = os.path.join(PASTA_FOTOS, nome_arquivo)
            cv2.imwrite(caminho_completo, frame)
            print(f"Foto salva: {caminho_completo}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()