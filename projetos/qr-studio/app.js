(() => {
    const generatorForm = document.getElementById("generator-form");
    const generatorInput = document.getElementById("generator-input");
    const generatorFeedback = document.getElementById("generator-feedback");
    const generatorResult = document.getElementById("generator-result");
    const downloadBtn = document.getElementById("download-btn");
    const qrCanvas = document.getElementById("qr-preview");

    const decoderForm = document.getElementById("decoder-form");
    const decoderInput = document.getElementById("decoder-input");
    const decoderFeedback = document.getElementById("decoder-feedback");
    const decoderResult = document.getElementById("decoder-result");
    const decodedText = document.getElementById("decoded-text");
    const decodedPreview = document.getElementById("decoded-preview");
    const decoderCanvas = document.getElementById("decoder-canvas");

    let qrInstance = null;

    const resetMessage = (target) => {
        target.textContent = "";
        target.className = "message";
    };

    const showMessage = (target, type, text) => {
        target.textContent = text;
        target.className = `message ${type}`;
    };

    const isValidUrl = (value) => {
        try {
            const url = new URL(value);
            return Boolean(url.protocol.startsWith("http"));
        } catch {
            return false;
        }
    };

    generatorForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const value = generatorInput.value.trim();
        resetMessage(generatorFeedback);

        if (!value) {
            showMessage(generatorFeedback, "error", "Informe um link para gerar o QR Code.");
            generatorResult.classList.add("hidden");
            return;
        }

        if (!isValidUrl(value)) {
            showMessage(generatorFeedback, "error", "O link precisa começar com http:// ou https://.");
            generatorResult.classList.add("hidden");
            return;
        }

        if (typeof QRious !== "function") {
            showMessage(
                generatorFeedback,
                "error",
                "Biblioteca de geração indisponível. Verifique sua conexão e recarregue a página."
            );
            generatorResult.classList.add("hidden");
            return;
        }

        if (!qrInstance) {
            qrInstance = new QRious({
                element: qrCanvas,
                size: 240,
                value: "",
                level: "H",
                background: "#ffffff",
                foreground: "#000000"
            });
        }

        qrInstance.set({ value });
        generatorResult.classList.remove("hidden");
        showMessage(generatorFeedback, "success", "QR Code gerado com sucesso.");
    });

    downloadBtn.addEventListener("click", () => {
        if (!qrCanvas) {
            return;
        }
        const link = document.createElement("a");
        link.href = qrCanvas.toDataURL("image/png");
        link.download = "qr-code.png";
        link.click();
    });

    decoderForm.addEventListener("submit", (event) => {
        event.preventDefault();
        resetMessage(decoderFeedback);

        const file = decoderInput.files?.[0];
        if (!file) {
            showMessage(decoderFeedback, "error", "Selecione uma imagem contendo um QR Code.");
            decoderResult.classList.add("hidden");
            return;
        }

        if (!/^image\/(png|jpeg|webp)$/i.test(file.type)) {
            showMessage(decoderFeedback, "error", "Formatos aceitos: PNG, JPG ou WEBP.");
            decoderResult.classList.add("hidden");
            return;
        }

        if (typeof jsQR !== "function") {
            showMessage(decoderFeedback, "error", "Biblioteca de leitura indisponível. Recarregue a página e tente novamente.");
            decoderResult.classList.add("hidden");
            return;
        }

        const reader = new FileReader();
        reader.onload = () => {
            const image = new Image();
            image.onload = () => {
                const context = decoderCanvas.getContext("2d", { willReadFrequently: true });
                if (!context) {
                    showMessage(decoderFeedback, "error", "Seu navegador não suporta processamento de canvas.");
                    return;
                }

                const maxDimension = 512;
                const scale = Math.min(maxDimension / image.width, maxDimension / image.height, 1);
                decoderCanvas.width = Math.floor(image.width * scale);
                decoderCanvas.height = Math.floor(image.height * scale);
                context.drawImage(image, 0, 0, decoderCanvas.width, decoderCanvas.height);

                const imageData = context.getImageData(0, 0, decoderCanvas.width, decoderCanvas.height);
                const code = jsQR(imageData.data, imageData.width, imageData.height, { inversionAttempts: "attemptBoth" });

                decodedPreview.src = reader.result;
                decodedPreview.classList.remove("hidden");
                decoderResult.classList.remove("hidden");

                if (code && code.data) {
                    decodedText.textContent = code.data.trim();
                    showMessage(decoderFeedback, "success", "QR Code reconhecido com sucesso.");
                } else {
                    decodedText.textContent = "";
                    showMessage(decoderFeedback, "error", "Nenhum QR Code válido foi encontrado na imagem.");
                }
            };
            image.onerror = () => {
                showMessage(decoderFeedback, "error", "Não foi possível ler a imagem enviada.");
            };
            image.src = reader.result;
        };
        reader.onerror = () => {
            showMessage(decoderFeedback, "error", "Erro ao carregar o arquivo. Tente novamente.");
        };
        reader.readAsDataURL(file);
    });
})();
