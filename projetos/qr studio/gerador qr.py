import base64
from io import BytesIO
from typing import Optional

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

import qrcode
from flask import Flask, render_template_string, request

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"

TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>QR Code Studio</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            color-scheme: light;
        }
        * {
            box-sizing: border-box;
        }
        body {
            margin: 0;
            font-family: "Poppins", "Segoe UI", sans-serif;
            background: radial-gradient(circle at top right, #7f5af0, #2cb1bc);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 32px 16px;
            color: #0f172a;
        }
        main {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            max-width: 1100px;
            width: 100%;
            padding: 48px;
            box-shadow: 0 30px 60px rgba(15, 23, 42, 0.25);
        }
        h1 {
            margin: 0 0 32px;
            font-size: 2rem;
            font-weight: 600;
            text-align: center;
            color: #1e1b4b;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
            gap: 32px;
        }
        .card {
            background: white;
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 20px 45px rgba(15, 23, 42, 0.15);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        label {
            font-size: 0.95rem;
            font-weight: 500;
            color: #475569;
        }
        input[type="url"],
        input[type="file"] {
            width: 100%;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 12px 14px;
            font-size: 0.98rem;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        input[type="url"]:focus,
        input[type="file"]:focus {
            outline: none;
            border-color: #7f5af0;
            box-shadow: 0 0 0 4px rgba(127, 90, 240, 0.18);
        }
        button {
            background: linear-gradient(135deg, #7f5af0, #2cb1bc);
            color: white;
            border: none;
            border-radius: 14px;
            padding: 12px 18px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.15s ease, box-shadow 0.2s ease;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 24px rgba(127, 90, 240, 0.25);
        }
        button:active {
            transform: translateY(0);
            box-shadow: none;
        }
        .result {
            border-radius: 16px;
            background: rgba(15, 23, 42, 0.04);
            padding: 20px;
            text-align: center;
        }
        .result img {
            width: 200px;
            height: 200px;
            object-fit: contain;
            border-radius: 12px;
            background: white;
            padding: 10px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.1);
        }
        .message {
            border-radius: 14px;
            padding: 12px 16px;
            font-size: 0.95rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .message.success {
            background: rgba(16, 185, 129, 0.15);
            color: #0f766e;
        }
        .message.error {
            background: rgba(248, 113, 113, 0.18);
            color: #b91c1c;
        }
        .decoded {
            font-family: "Fira Code", "Courier New", monospace;
            word-break: break-word;
            font-size: 0.95rem;
        }
        @media (max-width: 640px) {
            main {
                padding: 32px 20px;
            }
            h1 {
                font-size: 1.6rem;
            }
        }
    </style>
</head>
<body>
    <main>
        <h1>QR Code Studio</h1>
        {% if feedback %}
        <div class="message {{ feedback.type }}">{{ feedback.text }}</div>
        {% endif %}
        <div class="grid">
            <section class="card">
                <h2 style="margin: 0; font-weight: 600; color: #1f2937;">Gerar QR Code</h2>
                <p style="margin: 0; color: #64748b; font-size: 0.95rem;">
                    Cole qualquer link para criar um QR Code pronto para compartilhar.
                </p>
                <form method="post">
                    <input type="hidden" name="action" value="generate">
                    <label for="link">Link</label>
                    <input type="url" id="link" name="link" placeholder="https://exemplo.com/qualquer/coisa" value="{{ link_input }}" required>
                    <button type="submit">Gerar QR Code</button>
                </form>
                {% if qr_preview %}
                <div class="result">
                    <img src="{{ qr_preview }}" alt="QR Code gerado">
                    <p style="margin-top: 16px; color: #1e293b; font-size: 0.9rem;">
                        Escaneie ou salve a imagem gerada acima.
                    </p>
                </div>
                {% endif %}
            </section>
            <section class="card">
                <h2 style="margin: 0; font-weight: 600; color: #1f2937;">Ler QR Code</h2>
                <p style="margin: 0; color: #64748b; font-size: 0.95rem;">
                    Envie uma imagem contendo um QR Code e descubra o link escondido.
                </p>
                <form method="post" enctype="multipart/form-data">
                    <input type="hidden" name="action" value="decode">
                    <label for="qr_image">Imagem do QR Code</label>
                    <input type="file" id="qr_image" name="qr_image" accept="image/png, image/jpeg, image/webp" required>
                    <button type="submit">Ler QR Code</button>
                </form>
                {% if decoded_text %}
                <div class="result decoded">
                    {{ decoded_text }}
                </div>
                {% endif %}
            </section>
        </div>
    </main>
</body>
</html>
"""


def generate_qr_code(data: str) -> str:
    """retorna o QR Code como uma URL pronta para visualizar."""
    qr = qrcode.QRCode(version=None, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def decode_qr_code(file_bytes: bytes) -> Optional[str]:
    """tenta decodificar a informação do QR Code a partir de bytes."""
    if cv2 is None or np is None:
        raise RuntimeError(
            "Dependências para leitura de QR Code não encontradas. "
            "Instale 'opencv-python' e 'numpy' para usar esse recurso."
        )
    array = np.frombuffer(file_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        return None
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(image)
    if points is None or not data:
        return None
    return data.strip()


@app.route("/", methods=["GET", "POST"])
def index():
    qr_preview = None
    decoded_text = None
    feedback = None
    link_input = ""

    if request.method == "POST":
        action = request.form.get("action")
        if action == "generate":
            link_input = request.form.get("link", "").strip()
            if not link_input:
                feedback = {"type": "error", "text": "Informe um link válido para gerar o QR Code."}
            else:
                try:
                    qr_preview = generate_qr_code(link_input)
                    feedback = {"type": "success", "text": "QR Code gerado com sucesso."}
                except Exception:
                    feedback = {"type": "error", "text": "Erro ao gerar o QR Code. Tente novamente."}
        elif action == "decode":
            upload = request.files.get("qr_image")
            if not upload or not upload.filename:
                feedback = {"type": "error", "text": "Envie uma imagem contendo um QR Code."}
            else:
                file_bytes = upload.read()
                try:
                    decoded = decode_qr_code(file_bytes)
                except RuntimeError as exc:
                    feedback = {"type": "error", "text": str(exc)}
                else:
                    if decoded:
                        decoded_text = decoded
                        feedback = {"type": "success", "text": "QR Code reconhecido com sucesso."}
                    else:
                        feedback = {"type": "error", "text": "Nenhum QR Code válido foi detectado."}

    return render_template_string(
        TEMPLATE,
        qr_preview=qr_preview,
        decoded_text=decoded_text,
        feedback=feedback,
        link_input=link_input,
    )


if __name__ == "__main__":
    app.run(debug=True)
