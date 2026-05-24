# 🚀 Anki Booster

> *"Se o Anki funciona tão bem, por que estudar só quando ele está aberto?"*

Um **Companion SRS de Reforço Contínuo para o Anki**.

O Anki Booster identifica seus cartões com mais erros e dificuldades e os reapresenta suavemente ao longo do dia em uma pequena janela flutuante, discreta e minimalista.

Sem alterar o scheduler.  
Sem modificar seu deck.  
Sem substituir o Anki.

---

## 💡 Filosofia

O Anki é excelente para sessões focadas de revisão ativa.

O Anki Booster adiciona uma segunda camada:
um fluxo contínuo de micro-revisões durante o dia inteiro.

Enquanto você trabalha, programa, estuda ou navega,
os cards mais difíceis reaparecem suavemente em uma pequena interface flutuante.

🎯 O objetivo é transformar tempo morto em reforço contínuo.

---

## ✨ Funcionalidades

- 🧠 **SRS Complementar Inteligente**
  - Respeita o scheduler original do Anki
  - Delay individual por resposta (`Fácil`, `Ok`, `Difícil`, `Errei`)
  - Prioridade baseada em lapses, erros recentes e favoritos

- 🔄 **Buffer Rotativo Infinito**
  - Cards entram e saem automaticamente
  - Revisões contínuas sem travar em um único deck
  - Ideal para 50, 100, 200+ revisões extras por dia

- ⭐ **Sistema de Favoritos com Progressão**
  - Níveis `N1 → N2 → N3`
  - Progressão automática
  - Destaque para cards críticos

- 📊 **Foco nos Pontos Fracos**
  - Priorização inteligente baseada em:
    - lapses
    - ease
    - erros recentes
    - favoritos

- 🌐 **Logger em Tempo Real**
  - Interface web em:
    ```txt
    http://127.0.0.1:8895
    ```
  - Logs humanos e filtráveis
  - Busca textual e níveis (`INFO`, `WARN`, `ERR`)

- 📡 **API TCP Local**
  - Controle externo via:
    - CLI
    - scripts
    - addons do Anki

- 🪶 **Leve & Não Invasivo**
  - `<1%` CPU em idle
  - Leitura segura do banco (`mode=ro`)
  - Zero alteração no scheduler ou cards

- 🎨 **UI Minimalista**
  - Janela pequena e discreta
  - Sempre no topo
  - Animações suaves
  - Temas dinâmicos
  - Suporte completo a áudio/imagens do Anki

- 🧩 **Controle via System Tray**
  - Iniciar
  - Pausar
  - Reiniciar
  - Abrir logs
  - Encerrar serviço

- 🔄 **Instalação Automática**
  - `install.py` configura:
    - arquivos
    - autostart
    - extensão do Anki
    - estrutura de dados

---

## 🖥️ Compatibilidade

| Sistema | Status |
|---|---|
| Linux (Wayland/X11) | ✅ |
| Hyprland | ✅ |
| KDE Plasma | ✅ |
| GNOME | ✅ |
| Windows | ⚠️ Experimental |
| macOS | ⚠️ Parcial |

---

## 📦 Instalação Rápida (Recomendado)

```bash
# 1. Clone o repositório
git clone https://github.com/SamSilSou/AnkiBooster.git

# 2. Entre na pasta
cd AnkiBooster

# 3. Execute o instalador
python3 install.py
```

O instalador irá:

- ✅ Copiar os arquivos para o diretório correto
- ✅ Criar `anki_booster/`
- ✅ Instalar a extensão no Anki
- ✅ Configurar autostart opcional
- ✅ Configurar reinício automático do serviço

---

## 🔄 Atualização

Basta executar novamente:

```bash
python3 install.py
```

Seus dados serão preservados automaticamente.

---

## 🛠️ Instalação Manual (Opcional)

Você também pode executar diretamente:

```bash
python3 booster_service.py
```

Os arquivos de estado serão criados no mesmo diretório do script.

---

## 🚀 Uso

1. Abra o Anki normalmente
2. Inicie o Booster
3. O Booster cria uma cópia segura do banco
4. Os cards começam a aparecer automaticamente

Para configurar:

```txt
Ferramentas → Anki Booster
```

---

## 📡 API TCP (Porta 8894)

| Comando | Descrição |
|---|---|
| `START` | Inicia sessão |
| `GET_FAVS` | Retorna favoritos |
| `TOGGLE_FAV:<CID>` | Alterna favorito |
| `SAVE_CONFIG:<JSON>` | Salva configuração |
| `TOGGLE_PAUSE` | Pausa/retoma |

### Exemplo via CLI

```bash
echo "START" | nc localhost 8894
```

---

## 💾 Backup dos Dados

| Sistema | Caminho |
|---|---|
| Linux | `~/.local/bin/Anki_Booster/anki_booster/` |
| Windows | `%LOCALAPPDATA%\Anki_Booster\anki_booster\` |
| macOS | `~/Applications/Anki_Booster/anki_booster/` |

Faça backup para preservar:

- configurações
- favoritos
- estado dos cards
- histórico diário

---

## 🐛 Solução de Problemas

| Problema | Solução |
|---|---|
| Permissão negada | Use sudo/Admin |
| Extensão não instalou | Feche o Anki e rode novamente |
| Autostart falhou | Verifique logs |
| TCP não responde | Verifique a porta 8894 |

### Logs no Linux

```bash
journalctl --user -u anki-booster
```

---

## 📂 Estrutura do Projeto

```txt
Anki_Booster/
├── booster_service.py
├── booster_utils.py
├── theme.qml
├── themes.json
├── install.py
└── anki_booster/
    ├── anki_booster.db
    ├── anki_booster_state.json
    ├── anki_booster_daily.json
    └── anki_booster_config.json
```

---

## ⚠️ Aviso Importante

Este projeto **não é afiliado ao AnkiWeb**.

O Booster:

- ❌ Não modifica o scheduler
- ❌ Não altera seus cards
- ❌ Não escreve no `collection.anki2`
- ✅ Funciona como ferramenta complementar externa

---

## ⚖️ Licença

Licenciado sob **GNU GPL v3.0**.

- ✔ Pode usar
- ✔ Pode modificar
- ✔ Pode redistribuir
- ✔ Deve manter código aberto

---

## 💙 Apoie o Projeto

Projeto gratuito e open-source.

Se quiser apoiar:

- ☕ Ko-fi
- 💸 Liberapay
- 🇧🇷 PIX

---

<p align="center">
<i>Feito com 💙 e café para a comunidade de estudos.</i>
</p>