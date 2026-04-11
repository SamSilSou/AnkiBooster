# AnkiBooster

🚀 Anki Booster
"Se o Anki é tão incrível, por que não utilizá-lo o dia todo?"



📖 O que é?
Um Companion SRS de Reforço Contínuo para o Anki.
Ele identifica seus cartões com mais erros e dificuldades, e os exibe ao longo do dia em uma interface minimalista, sempre no topo, sem atrapalhar seu fluxo.
🎯 Foco: Levar suas dificuldades do Anki para o próximo nível, sem modificar o scheduler original, através da exibição contínua e rotativa dos seus pontos fracos.
✨ Funcionalidades
🧠 SRS Complementar: Respeita o ritmo global + delay individual por resposta (Fácil/Ok/Difícil/Errei)
🔄 Buffer Rotativo Infinito: Cards saem e entram automaticamente. Revise 50, 100, 200+ cards/dia
⭐ Sistema de Favoritos com Progressão: Marque os difíceis, suba de nível (N1→N2→N3) e gradue quando dominar
📊 Foco nas Fraquezas: Ordenação automática por erros recentes > streak < bônus de favorito
📡 API TCP Local: Controle via CLI, scripts ou addons do Anki (START, SAVE_CONFIG, TOGGLE_FAV, etc.)
🪶 Leve & Não Invasivo: <1% CPU, leitura segura do DB do Anki (cópia temporária + mode=ro), zero alteração no seu baralho
🎨 UI Minimalista: Janela 440×320, sempre no topo, animações sutis, áudio embutido em Base64
🔄 Instalação Automática: Script install.py configura tudo + autostart no sistema
📦 Instalação Rápida (Recomendado)
bash
123456
O instalador vai:
✅ Copiar os arquivos para o diretório padrão do seu sistema
✅ Criar a pasta de dados anki_booster/ com config padrão
✅ Instalar a extensão no Anki (se encontrado)
✅ Configurar autostart opcional (reinicia com o sistema + se fechar)
🔄 Atualização
Basta rodar install.py novamente sobre a instalação existente. Ele sobrescreve os arquivos mantendo seus dados (anki_booster/) intactos.
🛠️ Instalação Manual (Opcional)
Caso seja necessário, você pode rodar o Anki Booster diretamente da pasta de downloads.
Os arquivos de registro serão criados no mesmo diretório onde o script booster_service.py estiver localizado.
bash
123456789
🚀 Uso
Abra o Anki normalmente (o Booster lê uma cópia segura do banco)
O Booster deve iniciar automaticamente se configurou autostart, ou rode manualmente
Ao fechar o Anki, a extensão de integração envia um comando via TCP/IP START, e então o sistema SRS entra em ação
Para configurar, basta abrir o Anki e na barra superior: Ferramentas > Anki Booster. Lá estão as configurações e explicações sobre cada opção, detalhando sua alteração.
📡 Comandos TCP (Porta 8894)
Comando
Descrição
START
Carrega cards do Anki, prepara buffer e inicia sessão
GET_FAVS
Retorna lista JSON de IDs favoritos
TOGGLE_FAV:<CID>
Adiciona/remove favorito por ID
SAVE_CONFIG:<JSON>
Salva e aplica configurações em tempo real
TOGGLE_PAUSE
Pausa/retoma a exibição de cards
Exemplo de uso via CLI:
bash
12345
💾 Backup dos Dados
Seus dados ficam em:
Sistema
Caminho
Linux
~/.local/bin/Anki_Booster/anki_booster/
Windows
%LOCALAPPDATA%\Anki_Booster\anki_booster\
macOS
~/Applications/Anki_Booster/anki_booster/
Faça backup dessa pasta para preservar: configurações, favoritos, estado dos cards e histórico diário.
🐛 Solução de Problemas
Problema
Solução
❌ "Permissão negada" na instalação
Execute com sudo (Linux/macOS) ou como Administrador (Windows)
❌ Extensão não instalou no Anki
Feche o Anki e rode install.py novamente
❌ Booster não inicia no autostart
Verifique logs: journalctl --user -u anki-booster (Linux) ou %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup (Windows)
❌ TCP não responde
Confirme que o Booster está rodando e a porta 8894 não está bloqueada
💙 Apoie o Projeto
Este projeto é 100% gratuito e open-source.
Se ele te ajuda nos estudos, considere retribuir como puder:
☕ Pague um café (Ko-fi)
💸 Liberapay
🇧🇷 PIX: sua-chave-pix@exemplo.com
Cada contribuição, issue, pull request ou simples "obrigado" ajuda a manter o projeto vivo.
⚖️ Licença
Este projeto está licenciado sob a GNU General Public License v3.0.
Você pode usar, modificar e redistribuir livremente, desde que mantenha o código aberto sob a mesma licença. Uso em software proprietário ou fechado é expressamente proibido.
⚠️ Aviso Importante
Este projeto não é afiliado, endossado ou distribuído pela AnkiWeb.
Ele funciona como uma ferramenta externa complementar e não modifica o banco de dados, scheduler ou código oficial do Anki.
<p align="center">
<i>Feito com 💙 e café para a comunidade de estudos.</i>
</p>
