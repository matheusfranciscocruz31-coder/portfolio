# QR Code Studio

Ferramenta completa para criação, personalização e leitura de QR Codes, composta por uma interface web responsiva e uma API/CLI em Python.

## Componentes

- `index.html` + `styles.css`: interface SPA leve com temas e histórico.
- `app.js`: lógica front-end para gerar e baixar códigos em PNG/SVG usando Canvas.
- `gerador qr.py`: servidor Flask com endpoints para geração e leitura via OpenCV (opcional, para uso em equipes sem front-end).

## Como usar

### Interface Web
1. Abra `index.html` no navegador.
2. Informe o conteúdo (texto, URL, Wi-Fi etc.).
3. Ajuste cor, margem e tamanho.
4. Clique em **Gerar QR Code** e baixe o arquivo.

### API Python

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt  # se disponível; libs essenciais: flask, qrcode, pillow, opencv-python
python "gerador qr.py"
```

Endpoints principais:

- `POST /api/qrcode` – gera QR Code e retorna Base64 / PNG.
- `POST /api/decode` – decodifica imagem enviada e retorna o texto.

## Estrutura

```
projetos/qr-studio
├── index.html
├── styles.css
├── app.js
├── gerador qr.py
└── README.md
```

## Observações

- O script Python usa `cv2` (OpenCV) e `numpy` de forma opcional. Caso não estejam instalados, a leitura de QR Code fica indisponível, mas a geração funciona normalmente.
- Atualize `app.config["SECRET_KEY"]` antes de publicar o backend.
- Ajuste CORS se for servir o front-end e a API em domínios distintos.
