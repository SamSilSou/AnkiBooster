import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine
import QtMultimedia

Window {
    id: root
    visible: false
    width: 440
    height: 320
    minimumWidth: 440
    minimumHeight: 320
    maximumWidth: 440
    maximumHeight: 320
    flags: Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint
    color: SystemPalette.window

    property int slideDirection: 1
    property bool isAnimating: false
    property string pendingHtml: ""

    // NOVO: tempo padrão de snooze (usado tanto como valor inicial do
    // modal quanto pelo snooze rápido de long-press no botão 🌙)
    property int defaultSnoozeMinutes: 30

    // Alias para o tema dinâmico
    property var t: bridge.theme

    Connections {
        target: bridge
        function onThemeChanged() {
            root.t = bridge.theme
        }
        // NOVO: feedback informativo pós-resposta (streak / tempo até
        // reaparecer), emitido pelo Bridge antes de esconder a janela.
        function onAnswered(text) {
            answerFeedbackText.text = text
            answerFeedbackAnim.start()
        }
    }

    // Configuracao de sons
    property bool soundsEnabled: true
    property real soundVolume: 0.5
    property string soundClick: "sounds/Coffee2.wav"
    property string soundSoft: "sounds/Coffee2.wav"
    property string soundError: "sounds/Coffee1.wav"
    property string soundWhoosh: "sounds/Coffee2.wav"
    property string soundPop: "sounds/Coffee2.wav"

    SoundEffect { id: sndClick; source: soundClick; volume: soundVolume; muted: !soundsEnabled }
    SoundEffect { id: sndSoft;  source: soundSoft;  volume: soundVolume; muted: !soundsEnabled }
    SoundEffect { id: sndError; source: soundError; volume: soundVolume; muted: !soundsEnabled }
    SoundEffect { id: sndWhoosh;source: soundWhoosh;volume: soundVolume; muted: !soundsEnabled }
    SoundEffect { id: sndPop;   source: soundPop;   volume: soundVolume; muted: !soundsEnabled }

    // Timers para delay das respostas
    Timer { id: timerEasy; interval: 350; running: false; repeat: false; onTriggered: bridge.answerEasy() }
    Timer { id: timerOk; interval: 350; running: false; repeat: false; onTriggered: bridge.answerOk() }
    Timer { id: timerHard; interval: 350; running: false; repeat: false; onTriggered: bridge.answerHard() }
    Timer { id: timerFail; interval: 350; running: false; repeat: false; onTriggered: bridge.answerFail() }

    // Fullscreen Toggle (Esquerda)
    MouseArea {
        z: 100
        width: 32; height: 32
        anchors.top: parent.top; anchors.left: parent.left; anchors.margins: 8
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            rippleFS.start()
            bridge.toggleFullscreen()
        }
        Item {
            id: rippleFSContainer; anchors.centerIn: parent; width: 0; height: 0
            Rectangle {
                anchors.centerIn: parent
                width: rippleFSContainer.width; height: rippleFSContainer.height
                radius: width/2; color: "#ffffff"; opacity: 0.4
            }
            ParallelAnimation {
                id: rippleFS
                onStarted: rippleFSContainer.width = 0
                NumberAnimation { target: rippleFSContainer; property: "width"; to: 60; duration: 400; easing.type: Easing.OutQuad }
                NumberAnimation { target: rippleFSContainer; property: "height"; to: 60; duration: 400; easing.type: Easing.OutQuad }
                NumberAnimation { target: rippleFSContainer; property: "opacity"; from: 0.4; to: 0; duration: 400 }
            }
        }
        Text {
            id: fsIcon; anchors.centerIn: parent
            text: "⛶"; font.pixelSize: 20; color: t.text; opacity: 0.7; scale: 1.0
            Behavior on opacity { PropertyAnimation { duration: 150 } }
            Behavior on scale { NumberAnimation { duration: 80 } }
        }
        onEntered: fsIcon.opacity = 1.0
        onExited: fsIcon.opacity = 0.7
        onPressed: fsIcon.scale = 0.85
        onReleased: fsIcon.scale = 1.0
    }

    // Botao de Troca de Tema (Direita)
    MouseArea {
        z: 100
        width: 32; height: 32
        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 8
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            const current = t.surface === "#ffffff" ? "light" : "dark"
            const next = current === "light" ? "dark" : "light"
            bridge.setTheme(next)
        }
        Rectangle {
            id: themeBg
            anchors.fill: parent
            radius: 16
            color: t.surface
            opacity: 0.8
            Behavior on color { ColorAnimation { duration: 150 } }
        }
        Text {
            id: themeIcon
            anchors.centerIn: parent
            text: t.surface === "#ffffff" ? "🌙" : "☀️"
            font.pixelSize: 16
            color: t.text
            Behavior on scale { NumberAnimation { duration: 80 } }
        }
        onEntered: themeBg.opacity = 1.0
        onExited: themeBg.opacity = 0.8
        onPressed: themeIcon.scale = 0.85
        onReleased: themeIcon.scale = 1.0
    }

    Rectangle {
        anchors.fill: parent
        color: t.bg
        radius: 16
        clip: true
        focus: true
        activeFocusOnTab: false

        // NOVO: atalhos de teclado. 1/2/3/4 = Fácil/Ok/Difícil/Errei,
        // Espaço = mostrar resposta, Esc = fechar modal de snooze se
        // estiver aberto. Ignorado durante a animação de troca de card
        // para não empilhar respostas.
        Keys.onPressed: (event) => {
            if (root.isAnimating) return
            switch (event.key) {
                case Qt.Key_1:
                    answerRepeater.itemAt(0).trigger()
                    event.accepted = true
                    break
                case Qt.Key_2:
                    answerRepeater.itemAt(1).trigger()
                    event.accepted = true
                    break
                case Qt.Key_3:
                    answerRepeater.itemAt(2).trigger()
                    event.accepted = true
                    break
                case Qt.Key_4:
                    answerRepeater.itemAt(3).trigger()
                    event.accepted = true
                    break
                case Qt.Key_Space:
                    if (snoozeOverlay.opacity === 0) {
                        if (soundsEnabled) sndPop.play()
                        revealAnim.start()
                    }
                    event.accepted = true
                    break
                case Qt.Key_Escape:
                    if (snoozeOverlay.opacity > 0) {
                        snoozeOverlay.opacity = 0
                        if (soundsEnabled) sndSoft.play()
                    }
                    event.accepted = true
                    break
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            // Card Container
            Rectangle {
                id: cardContainer
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 16
                color: t.surface
                x: 0; opacity: 1; scale: 1.0
                clip: true
                implicitWidth: 416
                implicitHeight: 250

                WebEngineView {
                    id: webView
                    anchors.fill: parent
                    anchors.margins: 12
                    backgroundColor: "transparent"
                    clip: true
                    settings.fullScreenSupportEnabled: false
                    onFullScreenRequested: function(request) { request.reject() }
                }

                // NOVO: NÃO é um ícone novo - é uma área de clique
                // invisível posicionada sobre a estrela que JÁ EXISTE
                // dentro do HTML (renderizada por _wrap_html, top:8px
                // right:12px dentro do webView). Antes só dava pra
                // favoritar saindo do Booster (Anki/TCP); agora clicar
                // ali chama bridge.toggleFavorite() E atualiza o span
                // #oboete-fav-star via JS pra feedback visual instantâneo
                // (glifo ⭐/☆ + classe on/off + animação de "pop"), sem
                // esperar o próximo card aparecer.
                // z:5 (abaixo do snoozeOverlay, z:100) garante que o
                // modal de snooze bloqueia esse clique quando aberto.
                MouseArea {
                    z: 5
                    width: 42; height: 34
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.topMargin: 20   // margin do webView (12) + css top (8)
                    anchors.rightMargin: 22 // margin do webView (12) + css right (12), com folga
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        bridge.toggleFavorite()
                        if (soundsEnabled) sndPop.play()
                        webView.runJavaScript(`
                            (function() {
                                var el = document.getElementById('oboete-fav-star');
                                if (!el) return;
                                var isOn = el.classList.contains('oboete-star-on');
                                if (isOn) {
                                    el.classList.remove('oboete-star-on');
                                    el.classList.add('oboete-star-off');
                                    el.textContent = '☆';
                                } else {
                                    el.classList.remove('oboete-star-off');
                                    el.classList.add('oboete-star-on');
                                    el.textContent = '⭐';
                                }
                                // Reinicia a animação de "pop" mesmo que já
                                // tenha rodado antes (forçando reflow).
                                el.classList.remove('oboete-star-pop');
                                void el.offsetWidth;
                                el.classList.add('oboete-star-pop');
                            })();
                        `)
                    }
                }

                // NOVO: banner de feedback informativo pós-resposta
                // (streak / tempo até reaparecer). Some sozinho antes do
                // Bridge mandar esconder a janela (~0.9s de delay em
                // service.py, sincronizado com a duração desta animação).
                Text {
                    id: answerFeedbackText
                    visible: false
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 14
                    z: 200
                    font.pixelSize: 13
                    font.bold: true
                    color: t.text
                    opacity: 0
                    padding: 8

                    Rectangle {
                        anchors.fill: parent
                        radius: 10
                        color: t.surface
                        border.color: t.accent
                        border.width: 1
                        opacity: 0.95
                        z: -1
                    }

                    SequentialAnimation {
                        id: answerFeedbackAnim
                        running: false
                        PropertyAction { target: answerFeedbackText; property: "visible"; value: true }
                        NumberAnimation { target: answerFeedbackText; property: "opacity"; from: 0; to: 1; duration: 120 }
                        PauseAnimation { duration: 620 }
                        NumberAnimation { target: answerFeedbackText; property: "opacity"; to: 0; duration: 160 }
                        PropertyAction { target: answerFeedbackText; property: "visible"; value: false }
                    }
                }

                // OVERLAY DE SNOOZE
                // FIX (2ª rodada - bug real de novo): minha tentativa
                // anterior trocou o conceito original (painel SÓLIDO e
                // opaco, cor fixa "#4a5568", botões quase da MESMA cor do
                // painel, só se destacando no hover) por um conceito
                // diferente ("scrim escuro translúcido + botões soltos
                // com t.surface"). Isso quebra visualmente em qualquer
                // tema onde t.surface fica parecido com o preto do scrim
                // (tema escuro) - tudo parece "transparente"/sem definição.
                // Voltei ao conceito ORIGINAL: um painel 100% opaco e
                // sólido (mesmo estilo de antes), só que a cor agora vem
                // do tema (t.surface) em vez de fixa, e a opacidade vai
                // de 0→1 de verdade (sem scrim, sem multiplicação estranha).
                Rectangle {
                    id: snoozeOverlay
                    anchors.fill: parent
                    radius: 16
                    color: "#4a5568"
                    opacity: 0
                    visible: opacity > 0
                    z: 100
                    Behavior on opacity { NumberAnimation { duration: 200 } }

                    ColumnLayout {
                        anchors.centerIn: parent
                        anchors.margins: 20
                        spacing: 16
                        width: parent.width * 0.9

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            // FIX: painel agora é t.surface (pode ser claro
                            // OU escuro dependendo do tema), então o texto
                            // volta a usar t.text - branco fixo só fazia
                            // sentido quando o fundo era sempre escuro (scrim),
                            // o que não é mais o caso.
                            Text { text: "🌙"; font.pixelSize: 24 }
                            Text {
                                text: "Quanto tempo de soneca?"
                                color: "#ffffff"
                                font.pixelSize: 16
                                font.bold: true
                                Layout.fillWidth: true
                            }
                            MouseArea {
                                width: 28; height: 28
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    snoozeOverlay.opacity = 0
                                    if (soundsEnabled) sndSoft.play()
                                }
                                Text {
                                    text: "✖"
                                    anchors.centerIn: parent
                                    color: "#ffffff"
                                    font.pixelSize: 18
                                    opacity: 0.7
                                    Behavior on opacity { NumberAnimation { duration: 100 } }
                                }
                                onEntered: parent.opacity = 1.0
                                onExited: parent.opacity = 0.7
                            }
                        }

                        RowLayout {
                            id: timeControls
                            Layout.fillWidth: true
                            spacing: 8
                            // FIX: agora referencia a constante central
                            // root.defaultSnoozeMinutes (30) em vez de um
                            // número mágico solto aqui.
                            property int minutes: root.defaultSnoozeMinutes

                            // FIX: usa Qt.darker/lighter em cima de t.bg (não
                            // t.surface, que É a cor do painel - usar a
                            // mesma cor do fundo deixaria os botões
                            // "sumindo" de novo). t.bg costuma ser
                            // levemente diferente de t.surface em qualquer
                            // tema (claro ou escuro), garantindo contraste
                            // visível do botão contra o painel.
                            Rectangle {
                                Layout.preferredWidth: 48; height: 36; radius: 8; color: "#4a5568"
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent; hoverEnabled: true
                                    onEntered: parent.color = "#5a6578"
                                    onExited: parent.color = "#4a5568"
                                    onClicked: {
                                        timeControls.minutes = Math.max(1, timeControls.minutes - 5)
                                        if (soundsEnabled) sndClick.play()
                                    }
                                    Text { text: "-5m"; anchors.centerIn: parent; color: t.text; font.pixelSize: 14; font.bold: true }
                                }
                            }
                            Rectangle {
                                Layout.preferredWidth: 48; height: 36; radius: 8; color: "#4a5568"
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent; hoverEnabled: true
                                    onEntered: parent.color = "#5a6578"
                                    onExited: parent.color = "#4a5568"
                                    onClicked: {
                                        timeControls.minutes = Math.max(1, timeControls.minutes - 1)
                                        if (soundsEnabled) sndClick.play()
                                    }
                                    Text { text: "-1m"; anchors.centerIn: parent; color: t.text; font.pixelSize: 14; font.bold: true }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 36; radius: 8
                                color: "#251b1a"
                                border.color: t.accent
                                border.width: 2
                                Text {
                                    text: timeControls.minutes + " minutos"
                                    anchors.centerIn: parent
                                    color: t.text
                                    font.pixelSize: 15
                                    font.bold: true
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: 48; height: 36; radius: 8; color: "#4a5568"
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent; hoverEnabled: true
                                    onEntered: parent.color = "#5a6578"
                                    onExited: parent.color = "#4a5568"
                                    onClicked: {
                                        timeControls.minutes = Math.min(120, timeControls.minutes + 1)
                                        if (soundsEnabled) sndClick.play()
                                    }
                                    Text { text: "+1m"; anchors.centerIn: parent; color: t.text; font.pixelSize: 14; font.bold: true }
                                }
                            }
                            Rectangle {
                                Layout.preferredWidth: 48; height: 36; radius: 8; color: "#4a5568"
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent; hoverEnabled: true
                                    onEntered: parent.color = "#5a6578"
                                    onExited: parent.color = "#4a5568"
                                    onClicked: {
                                        timeControls.minutes = Math.min(120, timeControls.minutes + 5)
                                        if (soundsEnabled) sndClick.play()
                                    }
                                    Text { text: "+5m"; anchors.centerIn: parent; color: t.text; font.pixelSize: 14; font.bold: true }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Rectangle {
                                Layout.fillWidth: true; height: 40; radius: 10; color: "#4a5568"
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent; hoverEnabled: true
                                    onEntered: parent.color = "#5a6578"
                                    onExited: parent.color = "#4a5568"
                                    onClicked: {
                                        snoozeOverlay.opacity = 0
                                        if (soundsEnabled) sndSoft.play()
                                    }
                                    Text {
                                        text: "Cancelar"
                                        anchors.centerIn: parent
                                        color: t.text
                                        font.bold: true
                                        font.pixelSize: 14
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 40; radius: 10; color: t.accent
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent; hoverEnabled: true
                                    onEntered: parent.color = Qt.lighter(t.accent, 1.1)
                                    onExited: parent.color = t.accent
                                    onClicked: {
                                        var mins = timeControls.minutes
                                        bridge.snoozeWithMinutes(mins)
                                        snoozeOverlay.opacity = 0
                                        if (soundsEnabled) sndWhoosh.play()
                                    }
                                    Text {
                                        text: "Confirmar"
                                        anchors.centerIn: parent
                                        color: t.accentText
                                        font.bold: true
                                        font.pixelSize: 14
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Botao Mostrar Resposta
            Rectangle {
                id: showBtn
                Layout.fillWidth: true
                height: 46
                radius: 12
                color: t.surface
                scale: 1.0
                clip: true
                Behavior on scale { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
                Behavior on color { ColorAnimation { duration: 120 } }

                Item {
                    id: rippleShow; anchors.centerIn: parent; width: 0; height: 0
                    Rectangle {
                        anchors.centerIn: parent
                        width: rippleShow.width; height: rippleShow.height
                        radius: width/2; color: t.accent; opacity: 0.5
                    }
                    ParallelAnimation {
                        id: rippleShowAnim
                        NumberAnimation { target: rippleShow; property: "width"; from: 0; to: 300; duration: 450; easing.type: Easing.OutQuad }
                        NumberAnimation { target: rippleShow; property: "height"; from: 0; to: 300; duration: 450; easing.type: Easing.OutQuad }
                        NumberAnimation { target: rippleShow; property: "opacity"; from: 0.5; to: 0; duration: 450 }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: showBtn.scale = 1.02
                    onExited: showBtn.scale = 1.0
                    onPressed: { showBtn.scale = 0.97; rippleShowAnim.start() }
                    onClicked: {
                        mouse.accepted = true
                        if (soundsEnabled) sndPop.play()
                        revealAnim.start()
                    }
                }
                Text {
                    text: "Mostrar resposta 👀"
                    anchors.centerIn: parent
                    color: t.text
                    font.pixelSize: 15
                    font.bold: true
                }
                Text {
                    id: feedbackShow; visible: false; anchors.centerIn: parent; font.pixelSize: 24; opacity: 0
                    SequentialAnimation {
                        id: fadeShowOut; running: false
                        PauseAnimation { duration: 200 }
                        NumberAnimation { target: feedbackShow; property: "opacity"; to: 0; duration: 150 }
                        PropertyAction { target: feedbackShow; property: "visible"; value: false }
                    }
                }
            }

            // Botoes de Resposta + Snooze
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    id: snoozeBtn
                    Layout.preferredWidth: 48
                    height: 48
                    radius: 12
                    color: t.surface
                    // FIX: t.surface e t.bg podem ficar muito parecidos
                    // dependendo do tema (ex: #fafafa vs #ffffff), fazendo
                    // o botão "sumir" contra o fundo da janela. Uma borda
                    // sutil com t.accent garante contraste em qualquer tema.
                    border.color: t.accent
                    border.width: 1
                    scale: 1.0
                    clip: true
                    Behavior on scale { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
                    Behavior on color { ColorAnimation { duration: 100 } }

                    SequentialAnimation on y {
                        id: floatSnooze; running: false; loops: Animation.Infinite
                        NumberAnimation { duration: 700; easing.type: Easing.InOutQuad; to: -4 }
                        NumberAnimation { duration: 700; easing.type: Easing.InOutQuad; to: 0 }
                    }

                    Item {
                        id: rippleSnooze; anchors.centerIn: parent; width: 0; height: 0
                        Rectangle {
                            anchors.centerIn: parent
                            width: rippleSnooze.width; height: rippleSnooze.height
                            radius: width/2; color: "#718096"; opacity: 0.5
                        }
                        ParallelAnimation {
                            id: rippleSnoozeAnim
                            NumberAnimation { target: rippleSnooze; property: "width"; from: 0; to: 100; duration: 400; easing.type: Easing.OutQuad }
                            NumberAnimation { target: rippleSnooze; property: "height"; from: 0; to: 100; duration: 400; easing.type: Easing.OutQuad }
                            NumberAnimation { target: rippleSnooze; property: "opacity"; from: 0.5; to: 0; duration: 400 }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: { snoozeBtn.scale = 1.03; floatSnooze.running = true }
                        onExited: { snoozeBtn.scale = 1.0; floatSnooze.running = false; snoozeBtn.y = 0 }
                        onPressed: { snoozeBtn.scale = 0.95; rippleSnoozeAnim.start() }
                        // NOVO: clique curto abre o modal (comportamento
                        // antigo, pra ajustar o tempo). Segurar (long-press)
                        // dispara snooze rápido de root.defaultSnoozeMinutes
                        // direto, sem abrir modal nenhum.
                        onClicked: {
                            snoozeOverlay.opacity = 1
                            if (soundsEnabled) sndClick.play()
                        }
                        onPressAndHold: {
                            bridge.snoozeWithMinutes(root.defaultSnoozeMinutes)
                            if (soundsEnabled) sndWhoosh.play()
                            rippleSnoozeAnim.start()
                        }
                    }
                    Text { text: "🌙"; anchors.centerIn: parent; font.pixelSize: 20; color: t.text; opacity: 0.9 }
                }

                Repeater {
                    id: answerRepeater
                    model: [
                        { label: "Fácil 😎", color: "#a5d6a7", press: "#81c784", emoji: "🚀", dir: 1, txt: "black" },
                        { label: "Ok 😐", color: "#ffe082", press: "#ffd54f", emoji: "👍", dir: 1, txt: "black" },
                        { label: "Difícil 😢", color: "#ffcc80", press: "#ffb74d", emoji: "💪", dir: -1, txt: "black" },
                        { label: "Errei 💀", color: "#ff6b6b", press: "#d64a4a", emoji: "🔄", dir: -1, txt: "white" }
                    ]
                    delegate: Rectangle {
                        id: ansBtn
                        Layout.fillWidth: true
                        height: 48
                        radius: 12
                        color: modelData.color
                        scale: 1.0
                        clip: true
                        Behavior on color { ColorAnimation { duration: 100 } }
                        Behavior on scale { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }

                        // NOVO: lógica de resposta extraída pra uma função
                        // própria (performAnswer), reusada tanto pelo
                        // clique do mouse quanto pelo atalho de teclado
                        // (trigger()), em vez de duplicar a lógica em dois
                        // lugares.
                        function performAnswer() {
                            root.slideDirection = modelData.dir
                            if (index === 3) wobbleAnim.start()
                            if (soundsEnabled) {
                                if (index <= 1) sndClick.play()
                                else if (index === 2) sndSoft.play()
                                else sndError.play()
                            }
                            if (index === 0) timerEasy.start()
                            else if (index === 1) timerOk.start()
                            else if (index === 2) timerHard.start()
                            else timerFail.start()
                        }

                        // NOVO: chamado pelo atalho de teclado (1/2/3/4).
                        // Reaplica a mesma animação de "pressed" que o
                        // mouse dispara, pra dar o mesmo feedback visual
                        // independente de como o usuário respondeu.
                        function trigger() {
                            ansBtn.scale = 0.95
                            ansBtn.color = modelData.press
                            rippleAnim.start()
                            feedbackTxt.text = modelData.emoji
                            feedbackTxt.color = modelData.txt || "black"
                            feedbackAnim.start()
                            keyboardResetTimer.restart()
                            performAnswer()
                        }

                        Timer {
                            id: keyboardResetTimer
                            interval: 120
                            repeat: false
                            onTriggered: { ansBtn.color = modelData.color; ansBtn.scale = 1.0 }
                        }

                        SequentialAnimation on y {
                            id: floatAnim; running: false; loops: Animation.Infinite
                            NumberAnimation { duration: 650; easing.type: Easing.InOutQuad; to: -3 }
                            NumberAnimation { duration: 650; easing.type: Easing.InOutQuad; to: 0 }
                        }

                        Item {
                            id: rippleAns; anchors.centerIn: parent; width: 0; height: 0
                            Rectangle {
                                anchors.centerIn: parent
                                width: rippleAns.width; height: rippleAns.height
                                radius: width/2; color: "#ffffff"; opacity: 0.4
                            }
                            ParallelAnimation {
                                id: rippleAnim
                                NumberAnimation { target: rippleAns; property: "width"; from: 0; to: 250; duration: 400; easing.type: Easing.OutQuad }
                                NumberAnimation { target: rippleAns; property: "height"; from: 0; to: 250; duration: 400; easing.type: Easing.OutQuad }
                                NumberAnimation { target: rippleAns; property: "opacity"; from: 0.4; to: 0; duration: 400 }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: { ansBtn.scale = 1.03; floatAnim.running = true }
                            onExited: { ansBtn.scale = 1.0; floatAnim.running = false; ansBtn.y = 0 }
                            onPressed: {
                                ansBtn.scale = 0.95
                                ansBtn.color = modelData.press
                                rippleAnim.start()
                                feedbackTxt.text = modelData.emoji
                                feedbackTxt.color = modelData.txt || "black"
                                feedbackAnim.start()
                            }
                            onReleased: ansBtn.color = modelData.color
                            onClicked: {
                                ansBtn.performAnswer()
                            }
                        }
                        Text { text: modelData.label; anchors.centerIn: parent; color: modelData.txt || "black"; font.bold: true; font.pixelSize: 14 }
                        Text {
                            id: feedbackTxt; visible: false; anchors.centerIn: parent; font.pixelSize: 26; opacity: 0; z: 10
                            SequentialAnimation {
                                id: feedbackAnim; running: false
                                PropertyAction { target: feedbackTxt; property: "visible"; value: true }
                                ParallelAnimation {
                                    NumberAnimation { target: feedbackTxt; property: "opacity"; from: 0; to: 1; duration: 80 }
                                    NumberAnimation { target: feedbackTxt; property: "y"; from: 0; to: -35; duration: 350; easing.type: Easing.OutQuad }
                                    NumberAnimation { target: feedbackTxt; property: "scale"; from: 1; to: 1.6; duration: 350 }
                                }
                                PauseAnimation { duration: 150 }
                                NumberAnimation { target: feedbackTxt; property: "opacity"; to: 0; duration: 200 }
                                PropertyAction { target: feedbackTxt; property: "visible"; value: false }
                                PropertyAction { target: feedbackTxt; property: "y"; value: 0 }
                                PropertyAction { target: feedbackTxt; property: "scale"; value: 1 }
                            }
                        }
                    }
                }
            }
        }
    }

    // Wobble animation
    SequentialAnimation {
        id: wobbleAnim; running: false
        NumberAnimation { target: cardContainer; property: "rotation"; to: -4; duration: 60; easing.type: Easing.OutQuad }
        NumberAnimation { target: cardContainer; property: "rotation"; to: 4; duration: 100; easing.type: Easing.InOutQuad }
        NumberAnimation { target: cardContainer; property: "rotation"; to: -3; duration: 100 }
        NumberAnimation { target: cardContainer; property: "rotation"; to: 2; duration: 80 }
        NumberAnimation { target: cardContainer; property: "rotation"; to: 0; duration: 60; easing.type: Easing.OutBack }
    }

    // Exit animation (agora com onFinished para o swap JS)
    ParallelAnimation {
        id: exitAnim
        onFinished: {
            // Troca o HTML via JavaScript enquanto o container está invisível
            var safe = root.pendingHtml
                .replace(/\\/g, "\\\\")
                .replace(/'/g, "\\'")
                .replace(/\n/g, "\\n")
                .replace(/\r/g, "")
                .replace(/`/g, "\\`");

            var textColor = root.t?.text || "#2d3748";
            webView.runJavaScript(`
                (function() {
                    var el = document.body;
                    if (el) {
                        el.style.transition = 'opacity 0.12s ease-in-out';
                        el.style.opacity = '0';
                        setTimeout(function() {
                            el.innerHTML = '${safe}';
                            el.style.opacity = '1';
                        }, 120);
                    }
                })();
            `)

            // Reseta posição para a entrada
            cardContainer.x = -60 * root.slideDirection
            cardContainer.opacity = 0
            cardContainer.scale = 0.94
            cardContainer.rotation = 0
            
            // Libera interações após a transição
            swapTimer.restart()
            enterAnim.start()
        }
        NumberAnimation { target: cardContainer; property: "x"; to: 60 * root.slideDirection; duration: 180; easing.type: Easing.InQuad }
        NumberAnimation { target: cardContainer; property: "opacity"; to: 0; duration: 140 }
        NumberAnimation { target: cardContainer; property: "scale"; to: 0.96; duration: 160 }
    }

    // Enter animation
    ParallelAnimation {
        id: enterAnim
        NumberAnimation { target: cardContainer; property: "x"; from: -60 * root.slideDirection; to: 0; duration: 220; easing.type: Easing.OutQuad }
        NumberAnimation { target: cardContainer; property: "opacity"; from: 0; to: 1; duration: 200 }
        NumberAnimation { target: cardContainer; property: "scale"; from: 0.94; to: 1.0; duration: 220; easing.type: Easing.OutBack }
    }

    // Reveal animation
    SequentialAnimation {
        id: revealAnim
        ScriptAction {
            script: {
                bridge.onShowAnswerClicked()
                feedbackShow.text = "👁️"
                feedbackShow.opacity = 1
                feedbackShow.visible = true
                fadeShowOut.start()
            }
        }
        NumberAnimation { target: showBtn; property: "scale"; to: 1.03; duration: 100; easing.type: Easing.OutBack }
        NumberAnimation { target: showBtn; property: "scale"; to: 1.0; duration: 80; easing.type: Easing.OutQuad }
    }

    // Conexoes com Python
    Connections {
        target: bridge
        function onShow(html) {
            if (root.isAnimating) return
            root.isAnimating = true
            root.pendingHtml = html

            if (!root.visible) {
                // Primeiro carregamento: precisa mostrar a janela e ajustar geometria
                var textColor = root.t?.text || "#2d3748"
                webView.loadHtml(`
                    <html><body style="background:transparent;color:${textColor};
                    font-family:'Segoe UI',system-ui,sans-serif;font-size:16px;
                    text-align:center;margin:0;padding:0;word-wrap:break-word;">${html}</body></html>`)
                
                root.width = 440
                root.height = 320
                root.show()
                root.raise()
                root.requestActivate()
                root.isAnimating = false
            } else {
                // Trocas subsequentes: só anima o container e usa JS no WebView
                exitAnim.start()
            }
        }
        function onHide() { root.hide() }
    }

    // Timer para liberar interações após o swap
    Timer {
        id: swapTimer
        interval: 300
        repeat: false
        onTriggered: root.isAnimating = false
    }

    // Focus glow
    Rectangle {
        id: focusGlow
        anchors.fill: cardContainer
        radius: cardContainer.radius
        color: "transparent"
        border.color: t.accent
        border.width: 2
        opacity: 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 200 } }
    }
    onActiveChanged: {
        if (active && visible) {
            focusGlow.opacity = 0.3
            fadeGlowOut.start()
        }
    }
    SequentialAnimation {
        id: fadeGlowOut
        PauseAnimation { duration: 1500 }
        NumberAnimation { target: focusGlow; property: "opacity"; to: 0; duration: 400 }
    }
}
