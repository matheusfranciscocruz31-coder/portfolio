# Masterclass Analytics Landing Page

Landing page institucional inspirada em programas de formação em dados. O objetivo é apresentar a oferta da escola Dataclass Academy com destaque para benefícios, currículo, depoimentos e plano de assinatura.

## Conteúdo

- **Hero e barra de confiança** com CTA principal e empresas parceiras.
- **Seções de valor**: por que investir agora, trilhas, metodologia e credenciais.
- **Prova social** com depoimentos, perguntas frequentes e CTA final.
- **Componentes interativos** leves em `main.js` (scroll suave, FAQ, sticky CTA).

## Estrutura

```
projetos/masterclass-analytics
├── index.html
├── main.js
├── styles.css
└── README.md
```

## Como executar

1. Abra `index.html` diretamente no navegador, ou
2. Sirva a pasta com um servidor estático (`python -m http.server 8080`) para habilitar roteamento relativo.

## Personalização

- O layout usa fontes Google (`Inter`, `Montserrat`) e variáveis CSS no topo do `styles.css`.
- Ajuste CTAs e links no bloco `.hero__cta` e rodapé (`footer`).
- A lógica de expansão da FAQ e do banner fixo está em `main.js`.
