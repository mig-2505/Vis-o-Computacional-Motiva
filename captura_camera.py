"""
Captura básica de vídeo e foto da webcam usando OpenCV.

REQUISITOS:
    pip install opencv-python

COMO USAR:
    - Rode o script.
    - Uma janela vai abrir mostrando o vídeo ao vivo da câmera.
    - Pressione 'espaço' para tirar uma foto (salva como .png na pasta).
    - Pressione 'q' para sair.
"""

import cv2
import os
from datetime import datetime

# Índice da câmera. 0 = câmera padrão do PC.
# Se você tiver mais de uma câmera (ex: webcam + celular via USB),
# tente 1, 2, etc. até achar a certa.
CAMERA_INDEX = 0

# Pasta onde as fotos serão salvas.
# Pode ser um nome simples (cria na mesma pasta do script)
# ou um caminho, ex: "dados/fotos_tiradas"
PASTA_FOTOS = "fotos_tiradas"

# Cria a pasta se ela ainda não existir.
# exist_ok=True evita erro caso a pasta já exista.
os.makedirs(PASTA_FOTOS, exist_ok=True)

contador_fotos = 0

def main():
    global contador_fotos

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Erro: não consegui acessar a câmera.")
        return

    print("Câmera aberta com sucesso.")
    print("Pressione ESPAÇO para tirar uma foto.")
    print("Pressione 'q' para sair.")

    while True:
        # cap.read() retorna:
        #   ok -> True/False, se conseguiu ler o frame
        #   frame -> a imagem em si (matriz numpy, formato BGR)
        ok, frame = cap.read()

        if not ok:
            print("Erro ao capturar frame. Encerrando.")
            break

        # Mostra o vídeo ao vivo numa janela
        cv2.imshow("Webcam - pressione ESPACO para foto, 'q' para sair", frame)

        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord('q'):
            break

        elif tecla == ord(' '):
            contador_fotos += 1
            nome_arquivo = f"foto_{contador_fotos}_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.png"

            # os.path.join junta pasta + nome do arquivo do jeito certo
            caminho_completo = os.path.join(PASTA_FOTOS, nome_arquivo)

            cv2.imwrite(caminho_completo, frame)
            print(f"Foto salva: {caminho_completo}")

    # Libera a câmera e fecha as janelas ao final
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()