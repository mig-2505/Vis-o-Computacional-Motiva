"""
Calibração de cor HSV com sliders (trackbars) em tempo real.

OBJETIVO:
    Descobrir os valores HSV (Matiz, Saturação, Valor) que isolam
    uma cor específica (ex: verde da grama) na imagem da câmera.

REQUISITOS:
    pip install opencv-python numpy

COMO USAR:
    1. Rode o script.
    2. Aponte a câmera para o objeto/cor que quer isolar (ex: grama).
    3. Mexa nos sliders da janela "Ajustes" até a janela "Mascara"
       mostrar BRANCO só onde tem a cor desejada, e PRETO no resto.
    4. Anote os 6 valores finais (aparecem no terminal ao apertar 's').
    5. Pressione 'q' para sair.
"""

import  cv2
import numpy as np

CAMERA_INDEX = 0


def nada(x):
    """Função vazia exigida pelo cv2.createTrackbar (não faz nada)."""
    pass


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Erro: não consegui acessar a câmera.")
        return

    # Cria uma janela separada só para os sliders
    cv2.namedWindow("Ajustes")
    cv2.resizeWindow("Ajustes", 400, 300)

    # Cria os 6 sliders: Hue min/max, Saturation min/max, Value min/max
    # Hue vai de 0 a 179 no OpenCV (não 0-360 como em outros programas)
    cv2.createTrackbar("H min", "Ajustes", 35, 179, nada)
    cv2.createTrackbar("H max", "Ajustes", 85, 179, nada)
    cv2.createTrackbar("S min", "Ajustes", 40, 255, nada)
    cv2.createTrackbar("S max", "Ajustes", 255, 255, nada)
    cv2.createTrackbar("V min", "Ajustes", 40, 255, nada)
    cv2.createTrackbar("V max", "Ajustes", 255, 255, nada)

    print("Ajuste os sliders até isolar a cor desejada.")
    print("Pressione 's' para salvar/mostrar os valores no terminal.")
    print("Pressione 'q' para sair.")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Erro ao capturar frame.")
            break

        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Lê a posição atual de cada slider
        h_min = cv2.getTrackbarPos("H min", "Ajustes")
        h_max = cv2.getTrackbarPos("H max", "Ajustes")
        s_min = cv2.getTrackbarPos("S min", "Ajustes")
        s_max = cv2.getTrackbarPos("S max", "Ajustes")
        v_min = cv2.getTrackbarPos("V min", "Ajustes")
        v_max = cv2.getTrackbarPos("V max", "Ajustes")

        cor_min = (h_min, s_min, v_min)
        cor_max = (h_max, s_max, v_max)

        # Cria a máscara: branco onde a cor está dentro da faixa, preto fora
        mascara = cv2.inRange(frame_hsv, cor_min, cor_max)

        # Aplica a máscara na imagem original, só para visualizar melhor
        resultado = cv2.bitwise_and(frame, frame, mask=mascara)

        cv2.imshow("Camera", frame)
        cv2.imshow("Mascara", mascara)
        cv2.imshow("Resultado (cor isolada)", resultado)

        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord('q'):
            break
        elif tecla == ord('s'):
            print("\n--- Valores atuais ---")
            print(f"HSV_MIN = ({h_min}, {s_min}, {v_min})")
            print(f"HSV_MAX = ({h_max}, {s_max}, {v_max})")
            print("-----------------------\n")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()