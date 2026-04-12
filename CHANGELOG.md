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
```

--- 


## [0.1] - 2026-03-XX

### 🚀 Lançamento Inicial (MVP)
Primeira versão funcional do Anki Booster. Foco absoluto no motor de repetição espaçada (SRS), na leitura direta do banco do Anki e na estabilidade do serviço. Interface mínima e estática, sem recursos visuais ou interações avançadas.

### ✨ Adicionado
- **Motor SRS Independente**: Lógica própria de agendamento com `GLOBAL_CORRECT`, `GLOBAL_WRONG`, `BUFFER_SIZE` e `MAX_DAILY`.
- **Leitura Direta do `collection.anki2`**: Parser nativo sem depender da API do Anki ou de add-ons externos.
- **Sistema de Favoritos**: Banco SQLite local (`anki_booster.db`) com níveis (N1→N2→N3), contagem consecutiva e graduação automática.
- **Interface Mínima (QML)**: Exibição crua do card (frente/verso) + 4 botões de resposta. Sem animações, sem hover, sem transições.
- **Estado Persistente**: `state.json` (streak, erros recentes, `next_due`, nível de favorito) e `daily.json` (contadores diários por card).
- **API TCP Local**: Controle externo via `127.0.0.1:8894` com comandos: `START`, `GET_FAVS`, `TOGGLE_FAV:<cid>`, `SAVE_CONFIG`, `GET_CONFIG`, `TOGGLE_PAUSE`.
- **Parser de Mídia**: Conversão automática de tags `[sound:xxx]` do Anki para `<audio controls>` embutido em Base64.
- **Configuração com Merge Inteligente**: `anki_booster_config.json` com valores padrão e aplicação segura de novas chaves.

### ⚠️ Limitações Conhecidas (v0.1)
- Interface 100% estática: zero animações, zero feedback visual, zero micro-interações.
- Sem botão de "Snooze" ou adiamento temporário.
- Sem suporte a Furigana Hover.
- Sem feedback sonoro.
- Sem fullscreen ou redimensionamento dinâmico.
- Atalhos de teclado removidos por instabilidade com QtWebEngine no Linux.

### 📦 Estrutura de Arquivos
