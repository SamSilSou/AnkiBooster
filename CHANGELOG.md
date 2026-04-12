# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.2] - 2026-04-12

### ✨ Novas Funcionalidades
- **🌙 Botão Snooze**: Adia o card atual por 1h sem penalizar o SRS, remover do buffer ou resetar streak. Volta automaticamente quando o tempo vence.
- **🔊 Sistema de Sons**: Feedback auditivo opcional e configurável para respostas, snooze e revelar resposta.
  - Arquivos na pasta `sounds/` (WAV/OGG).
  - Controlado por `SOUNDS_ENABLED` e `SOUND_VOLUME`.
  - Desligado por padrão para não atrapalhar sessões em silêncio.
- **🈶 Furigana Hover**: CSS inteligente que oculta a leitura (`<rt>`) até passar o mouse sobre o Kanji. Ativável via `"HIDE_FURIGANA_ON_HOVER": true`.
- **🔍 Logs Humanos**: Mensagens de log claras que explicam *por que* um favorito não apareceu (snooze, limite diário ou agendamento), sem poluição técnica.

### 🎨 UI & Interação (antes estática)
- **Animações Fluidas**: Slide direcional no card, bounce no botão "Mostrar resposta", emojis flutuantes no feedback.
- **Micro-interações**: Hover, press e scale em todos os botões.
- **Fullscreen Toggle**: Ícone `⛶` no canto com feedback visual.
- **Overlay de Pausa**: Tela elegante com animação de pulso quando o booster está pausado.

### 🧠 Lógica & Estabilidade
- **Favoritos Robustos**: Carregados independentemente do `revlog`. Só somem se `next_due` estiver no futuro ou limite diário atingido.
- **Snooze Inteligente**: Card permanece no buffer mas é filtrado pelo loop. Zero perda de estado, zero quebra no ritmo.
- **Zero Keybinds Problemáticas**: Removido `Keys.onPressed`. Interação 100% via mouse/UI (evita conflitos com QtWebEngine e foco no Linux).
- **CPU <1% em idle**: Timer de 3s + guards eficientes.

### 📦 Configurações Novas
```json
{
  "SOUNDS_ENABLED": false,
  "SOUND_VOLUME": 0.5,
  "HIDE_FURIGANA_ON_HOVER": false
}
