# AnkiBooster

# 🚀 Anki Booster
*"Se o Anki é tão incrível, por que não utilizá-lo o dia todo?"*

---

## 📖 O que é?
Um **Companion SRS de Reforço Contínuo para o Anki**.  
Ele identifica seus cartões com mais erros e dificuldades, e os exibe ao longo do dia em uma interface minimalista, sempre no topo, sem atrapalhar seu fluxo.

🎯 **Foco:** Levar suas dificuldades do Anki para o próximo nível, sem modificar o scheduler original, através da exibição contínua e rotativa dos seus pontos fracos.

---

## ✨ Funcionalidades

- 🧠 **SRS Complementar:** Respeita o ritmo global + delay individual por resposta (Fácil / Ok / Difícil / Errei)  
- 🔄 **Buffer Rotativo Infinito:** Cards saem e entram automaticamente. Revise 50, 100, 200+ cards/dia  
- ⭐ **Sistema de Favoritos com Progressão:** Marque os difíceis, suba de nível (N1 → N2 → N3) e gradue quando dominar  
- 📊 **Foco nas Fraquezas:** Ordenação automática por erros recentes > streak < bônus de favorito  
- 📡 **API TCP Local:** Controle via CLI, scripts ou addons do Anki (START, SAVE_CONFIG, TOGGLE_FAV, etc.)  
- 🪶 **Leve & Não Invasivo:** <1% CPU, leitura segura do DB do Anki (cópia temporária + mode=ro), zero alteração no seu baralho  
- 🎨 **UI Minimalista:** Janela 440×320, sempre no topo, animações sutis, áudio embutido em Base64  
- 🔄 **Instalação Automática:** Script install.py configura tudo + autostart no sistema  

---

## 📦 Instalação Rápida (Recomendado)

```bash
python install.py
```

O instalador vai:

- ✅ Copiar os arquivos para o diretório padrão do seu sistema  
- ✅ Criar a pasta de dados `anki_booster/` com config padrão  
- ✅ Instalar a extensão no Anki (se encontrado)  
- ✅ Configurar autostart opcional (reinicia com o sistema + se fechar)  

---

## 🔄 Atualização

Basta rodar `install.py` novamente sobre a instalação existente.  
Ele sobrescreve os arquivos mantendo seus dados (`anki_booster/`) intactos.

---

## 🛠️ Instalação Manual (Opcional)

Caso seja necessário, você pode rodar o Anki Booster diretamente da pasta de downloads.

Os arquivos de registro serão criados no mesmo diretório onde o script `booster_service.py` estiver localizado.

```bash
python booster_service.py
```

---

## 🚀 Uso

1. Abra o Anki normalmente (o Booster lê uma cópia segura do banco)  
2. O Booster deve iniciar automaticamente (se configurado) ou rode manualmente  
3. Ao fechar o Anki, a extensão envia um comando TCP/IP `START`, iniciando o sistema SRS  
4. Para configurar:
   - Abra o Anki  
   - Vá em **Ferramentas > Anki Booster**  
   - Ajuste conforme necessário  

---

## 📡 Comandos TCP (Porta 8894)

| Comando              | Descrição |
|----------------------|----------|
| START                | Carrega cards do Anki e inicia sessão |
| GET_FAVS             | Retorna lista JSON de favoritos |
| TOGGLE_FAV:<CID>     | Adiciona/remove favorito |
| SAVE_CONFIG:<JSON>   | Salva config em tempo real |
| TOGGLE_PAUSE         | Pausa/retoma |

### Exemplo via CLI:

```bash
echo "START" | nc localhost 8894
```

---

## 💾 Backup dos Dados

| Sistema | Caminho |
|--------|--------|
| Linux  | ~/.local/bin/Anki_Booster/anki_booster/ |
| Windows | %LOCALAPPDATA%\Anki_Booster\anki_booster\ |
| macOS | ~/Applications/Anki_Booster/anki_booster/ |

Faça backup dessa pasta para preservar:
- configurações  
- favoritos  
- estado dos cards  
- histórico diário  

---

## 🐛 Solução de Problemas

| Problema | Solução |
|----------|--------|
| Permissão negada | Use sudo (Linux/macOS) ou Administrador (Windows) |
| Extensão não instalou | Feche o Anki e rode install.py novamente |
| Autostart não funciona | Verifique logs (journalctl --user -u anki-booster) |
| TCP não responde | Verifique se a porta 8894 está livre |

---

## 💙 Apoie o Projeto

Projeto 100% gratuito e open-source.

Se quiser apoiar:

- ☕ Ko-fi  
- 💸 Liberapay  
- 🇧🇷 PIX: sua-chave-pix@exemplo.com  

---

## ⚖️ Licença

Licenciado sob **GNU GPL v3.0**.

- ✔ Pode usar, modificar e redistribuir  
- ✔ Deve manter código aberto  
- ❌ Uso em software proprietário é proibido  

---

## ⚠️ Aviso Importante

Este projeto **não é afiliado ao AnkiWeb**.

- Não modifica o banco de dados  
- Não altera o scheduler  
- Funciona como ferramenta externa complementar  

---

<p align="center">
<i>Feito com 💙 e café para a comunidade de estudos.</i>
</p>
