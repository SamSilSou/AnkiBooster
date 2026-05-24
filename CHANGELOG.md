# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).


## [ V1.0 ] - 2026-05-23

### 🎉 Lançamento da Versão 1.0

Primeira versão estável do Anki Booster. O motor de revisão agora combina a lógica própria do Booster com dados reais do histórico do Anki, entregando priorização inteligente, UI fluida e estabilidade total em Wayland/Hyprland.

> 💡 *Filosofia da v1.0:* O Booster foi redesenhado para estender o Anki, não substituí-lo. Ele respeita o agendamento original, lê métricas reais do seu banco e adiciona uma camada focada nos seus pontos fracos.

---

### ✨ Novas Funcionalidades

- **🌐 Logger em Tempo Real (Browser-Based)**:
  - Interface web automática em `http://127.0.0.1:8895`
  - Logs humanos explicando por que um card foi selecionado, filtrado ou adiado.
  - Filtros por nível (`INFO`, `OK`, `WARN`, `ERR`) e busca textual.
  - Zero configuração. Funciona em Linux, Windows e macOS.

- **🧩 Controle via System Tray**:
  - Ícone nativo na bandeja do sistema.
  - Menu contextual com:
    - ▶️ Iniciar
    - ⏸️ Pausar/Retomar
    - 📋 Ver Logs
    - 🔄 Reiniciar Serviço
  - Indicador visual de estado (rodando/pausado).

- **🎨 Sistema de Temas Dinâmicos**:
  - Suporte a múltiplos temas via `themes.json`
  - Alternância instantânea entre:
    - `light`
    - `dark`
    - `medium`
  - Preservação automática de `accent` e `accentText`.
  - Fallback seguro se o tema ainda não estiver carregado.

- **🧠 Priorização Baseada no Anki**:
  - O Booster agora utiliza métricas reais do `collection.anki2`:
    - `lapses`
    - `ease`
    - `interval`
    - `lapse_ratio`
  - Cards mais problemáticos sobem naturalmente na fila.
  - Métricas internas (`errors_recent`, `streak`) agora atuam apenas como desempate.

- **📊 Relatório de Estatísticas**:
  - Geração automática de `anki_booster_stats.txt`
  - Inclui:
    - Cards ordenados por lapsos totais
    - Frente limpa do card
    - ID do Anki
    - Total de revisões
    - Acertos/erros

- **🖼️ Suporte Completo a Mídia**:
  - Conversão automática:
    - `[sound:xxx.mp3]` → `<audio controls>`
    - `<img src="xxx.jpg">` → Base64
  - Prefixo `data:` corrigido.
  - Imagens limitadas com `max-width: 100%`.

---

### 🎨 UI & Interação

- **✨ Animações Restauradas + Fix de Wayland**:
  - Fade suave entre frente e verso usando `webView.runJavaScript()`.
  - Zero uso de `root.show()/hide()` durante troca de conteúdo.
  - Compatibilidade total com Hyprland/Wayland sem maximização involuntária.
  - Animações QML preservadas (`exitAnim` / `enterAnim`).

- **🖱️ Botões com Feedback Visual**:
  - Hover
  - Press
  - Scale
  - Ripple

- **⭐ Indicadores de Favorito**:
  - Exibição visual:
    ```txt
    [N1: 3/6]
    ```
  - Destaque dourado para favoritos.

- **⏰ Overlay de Snooze Elegante**:
  - Controles rápidos:
    - `+1m`
    - `+5m`
    - `-1m`
    - `-5m`
  - Botões de confirmar/cancelar.

---

### 🧠 Lógica & Estabilidade

- **📦 Buffer Pré-Ordenado**:
  - Cards são ordenados antes de preencher `active_cards`.
  - Os primeiros cards do buffer são sempre os mais problemáticos.

- **🛡️ Fallbacks Seguros**:
  - Proteção contra:
    - `null`
    - `undefined`
    - temas ainda não carregados

- **⚡ Query SQL Otimizada**:
  - Uso de `LEFT JOIN` e subqueries seguras para leitura do `revlog`.
  - Evita corrupção do campo `n.flds`.

- **🔒 Thread-Safety**:
  - Uso consistente de `_state_lock`.

- **🧹 Refatoração Geral**:
  - Remoção de duplicações
  - Tratamento de erros consistente
  - Tipagem mais segura
  - Correções de bugs "fantasmas"

---

### 📦 Configurações Novas

```json
{
  "LOGGER_PORT": 8895,
  "ENABLE_TRAY": true,
  "DEFAULT_THEME": "dark",
  "ENABLE_ANKI_PRIORITY": true
}
```

---

### ⚠️ Notas de Migração (v0.2 → v1.0)

- **💾 Backup recomendado**:
  - Faça cópia da pasta `anki_booster/`

- **🎨 themes.json**
  - Crie o arquivo na raiz do projeto para usar múltiplos temas.

- **🔄 Reset opcional**
  - Para aplicar imediatamente a nova priorização:
    ```txt
    anki_booster_state.json
    anki_booster_daily.json
    ```

- **🖥️ Hyprland/Wayland**
  - O fix de fullscreen é automático.

- **🧩 Tray no Linux**
  - Necessário suporte a `QSystemTrayIcon`.

---

### 🐛 Bugs Corrigidos

- ❌ Janela maximizando sozinha ao revelar resposta no Hyprland/Wayland.
- ❌ Áudios e imagens não aparecendo nos cards.
- ❌ Crash ao iniciar sem `bridge.theme`.
- ❌ Priorização ignorando lapses reais do Anki.
- ❌ Buffer carregando cards aleatórios.
- ❌ Logs excessivamente técnicos.
- ❌ Controle limitado apenas via TCP.

---










## [ V0.2 ] - 2026-04-12

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









## [ V0.1 ] - 2026-03-28

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

```txt
Anki_Booster/
├── booster_service.py
├── theme.qml
├── booster_utils.py
└── anki_booster/
    ├── anki_booster.db
    ├── anki_booster_state.json
    ├── anki_booster_daily.json
    └── anki_booster_config.json
```

> 💡 *A v0.1 entregou o núcleo: motor funcionando, estado salvo, comunicação estável. A base necessária para transformar uma ferramenta crua em uma experiência fluida na v0.2.*