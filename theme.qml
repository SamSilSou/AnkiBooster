import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine
import QtMultimedia  // Necessário para SoundEffect

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
    color: "transparent"

    // 🎯 Controle de direção do slide
    property int slideDirection: 1
    property bool isAnimating: false

    // 🎨 Tema
    property var theme: {
        "bg": "#251b1a",
        "surface": "#322826",
        "text": "#f1dfdc",
        "accent": "#ffb4a8",
        "accentText": "#561e16"
    }

    // 🔊 CONFIGURAÇÃO DE SONS (Edite aqui!)
    property bool soundsEnabled: true          // 🔇 false = silencia tudo
    property real soundVolume: 0.5             // 🎚️ 0.0 a 1.0
    
   // 📂 Caminhos dos arquivos (pasta 'sounds/' ao lado do theme.qml)
    property string soundClick: "sounds/Coffee2.wav"      // Fácil / Ok
    property string soundSoft: "sounds/Coffee2.wav"        // Difícil
    property string soundError: "sounds/Coffee1.wav"      // Errei
    property string soundWhoosh: "sounds/Coffee2.wav"    // Snooze
    property string soundPop: "sounds/Coffee2.wav"          // Mostrar resposta

    // 🔊 DEFINIÇÃO DOS EFEITOS SONOROS
    // ✅ Correção: usar 'muted: !soundsEnabled' em vez de 'enabled'
    SoundEffect { id: sndClick; source: soundClick; volume: soundVolume; muted: !soundsEnabled }
    SoundEffect { id: sndSoft;  source: soundSoft;  volume: soundVolume; muted: !soundsEnabled }
    SoundEffect { id: sndError; source: soundError; volume: soundVolume; muted: !soundsEnabled }
    SoundEffect { id: sndWhoosh;source: soundWhoosh;volume: soundVolume; muted: !soundsEnabled }
    SoundEffect { id: sndPop;   source: soundPop;   volume: soundVolume; muted: !soundsEnabled }

    // 🔘 Fullscreen Toggle
    MouseArea {
        z: 100
        width: 32; height: 32
        anchors.top: parent.top; anchors.left: parent.left; anchors.margins: 8
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: bridge.toggleFullscreen()
        
        Text {
            id: fsIcon
            anchors.centerIn: parent
            text: "⛶"
            font.pixelSize: 20
            color: "white"
            opacity: 0.5
            scale: 1.0
            Behavior on opacity { PropertyAnimation { duration: 150 } }
            Behavior on scale { NumberAnimation { duration: 80 } }
        }
        onEntered: fsIcon.opacity = 0.9
        onExited: fsIcon.opacity = 0.5
        onPressed: fsIcon.scale = 0.85
        onReleased: fsIcon.scale = 1.0
    }

    Rectangle {
        anchors.fill: parent
        color: theme.bg
        radius: 16
        clip: true
        focus: true
        activeFocusOnTab: false

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            // 🌐 Card com Slide Animation
            Rectangle {
                id: cardContainer
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 16
                color: theme.surface
                x: 0; opacity: 1; scale: 1.0

                WebEngineView {
                    id: webView
                    anchors.fill: parent
                    anchors.margins: 12
                    backgroundColor: "transparent"
                    clip: true
                }
            }

            // 👀 Botão "Mostrar Resposta" com bounce
            Rectangle {
                id: showBtn
                Layout.fillWidth: true
                height: 46
                radius: 12
                color: theme.surface
                scale: 1.0
                Behavior on scale { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
                Behavior on color { ColorAnimation { duration: 120 } }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: showBtn.scale = 1.02
                    onExited: showBtn.scale = 1.0
                    onPressed: showBtn.scale = 0.97
                    onClicked: {
                        if (soundsEnabled) sndPop.play()
                        revealAnim.start()
                    }
                }

                Text {
                    text: "Mostrar resposta 👀"
                    anchors.centerIn: parent
                    color: theme.text
                    font.pixelSize: 15
                    font.bold: true
                }

                Text {
                    id: feedbackShow
                    visible: false
                    anchors.centerIn: parent
                    font.pixelSize: 24
                    opacity: 0
                    SequentialAnimation {
                        id: fadeShowOut
                        running: false
                        PauseAnimation { duration: 200 }
                        NumberAnimation { target: feedbackShow; property: "opacity"; to: 0; duration: 150 }
                        PropertyAction { target: feedbackShow; property: "visible"; value: false }
                    }
                }
            }

            // 🔘 Botões de Resposta + Snooze
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                // 🌙 Snooze
                Rectangle {
                    id: snoozeBtn
                    Layout.preferredWidth: 48
                    height: 48
                    radius: 12
                    color: "#4a5568"
                    scale: 1.0
                    Behavior on scale { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
                    Behavior on color { ColorAnimation { duration: 100 } }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: snoozeBtn.scale = 1.03
                        onExited: snoozeBtn.scale = 1.0
                        onPressed: snoozeBtn.scale = 0.95
                        onClicked: {
                            snoozeBtn.color = "#718096"
                            feedbackSnooze.text = "🌙"
                            feedbackSnooze.opacity = 1
                            feedbackSnooze.visible = true
                            fadeSnoozeOut.start()
                            if (soundsEnabled) sndWhoosh.play()
                            bridge.snoozeCard()
                        }
                    }

                    Text { text: "🌙"; anchors.centerIn: parent; font.pixelSize: 20; color: theme.text; opacity: 0.9 }
                    Text {
                        id: feedbackSnooze; visible: false; anchors.centerIn: parent; font.pixelSize: 26; opacity: 0; z: 10
                        SequentialAnimation {
                            id: fadeSnoozeOut; running: false
                            PropertyAction { target: feedbackSnooze; property: "visible"; value: true }
                            ParallelAnimation {
                                NumberAnimation { target: feedbackSnooze; property: "opacity"; from: 0; to: 1; duration: 80 }
                                NumberAnimation { target: feedbackSnooze; property: "y"; from: 0; to: -35; duration: 350; easing.type: Easing.OutQuad }
                                NumberAnimation { target: feedbackSnooze; property: "scale"; from: 1; to: 1.6; duration: 350 }
                            }
                            PauseAnimation { duration: 150 }
                            NumberAnimation { target: feedbackSnooze; property: "opacity"; to: 0; duration: 200 }
                            PropertyAction { target: feedbackSnooze; property: "visible"; value: false }
                            PropertyAction { target: feedbackSnooze; property: "y"; value: 0 }
                            PropertyAction { target: feedbackSnooze; property: "scale"; value: 1 }
                        }
                    }
                }

                // 🔘 Respostas
                Repeater {
                    model: [
                        { label: "Fácil 😎", color: "#a5d6a7", press: "#81c784", emoji: "🚀", dir: 1 },
                        { label: "Ok 😐", color: "#ffe082", press: "#ffd54f", emoji: "👍", dir: 1 },
                        { label: "Difícil 😢", color: "#ffcc80", press: "#ffb74d", emoji: "💪", dir: -1 },
                        { label: "Errei 💀", color: "#ff6b6b", press: "#d64a4a", emoji: "🔄", txt: "white", dir: -1 }
                    ]

                    delegate: Rectangle {
                        id: ansBtn
                        Layout.fillWidth: true
                        height: 48
                        radius: 12
                        color: modelData.color
                        scale: 1.0
                        Behavior on color { ColorAnimation { duration: 100 } }
                        Behavior on scale { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: ansBtn.scale = 1.03
                            onExited: ansBtn.scale = 1.0
                            onPressed: {
                                ansBtn.scale = 0.95
                                feedbackTxt.text = modelData.emoji
                                feedbackTxt.color = modelData.txt || "black"
                                feedbackAnim.start()
                            }
                            onClicked: {
                                root.slideDirection = modelData.dir
                                if (soundsEnabled) {
                                    if (index <= 1) sndClick.play()
                                    else if (index === 2) sndSoft.play()
                                    else sndError.play()
                                }
                                if (index === 0) bridge.answerEasy()
                                else if (index === 1) bridge.answerOk()
                                else if (index === 2) bridge.answerHard()
                                else bridge.answerFail()
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

    // 🔥 ANIMAÇÕES (inalteradas)
    ParallelAnimation {
        id: exitAnim
        NumberAnimation { target: cardContainer; property: "x"; to: 60 * root.slideDirection; duration: 180; easing.type: Easing.InQuad }
        NumberAnimation { target: cardContainer; property: "opacity"; to: 0; duration: 140 }
        NumberAnimation { target: cardContainer; property: "scale"; to: 0.96; duration: 160 }
    }
    ParallelAnimation {
        id: enterAnim
        NumberAnimation { target: cardContainer; property: "x"; from: -60 * root.slideDirection; to: 0; duration: 220; easing.type: Easing.OutQuad }
        NumberAnimation { target: cardContainer; property: "opacity"; from: 0; to: 1; duration: 200 }
        NumberAnimation { target: cardContainer; property: "scale"; from: 0.94; to: 1.0; duration: 220; easing.type: Easing.OutBack }
    }
    SequentialAnimation {
        id: revealAnim
        NumberAnimation { target: cardContainer; property: "scale"; to: 0.95; duration: 120 }
        ScriptAction {
            script: {
                feedbackShow.text = "👁️"
                feedbackShow.opacity = 1
                feedbackShow.visible = true
                fadeShowOut.start()
                bridge.onShowAnswerClicked()
            }
        }
        NumberAnimation { target: cardContainer; property: "scale"; to: 1.0; duration: 160; easing.type: Easing.OutBack }
    }

    // 🔗 Conexões com Python
    Connections {
        target: bridge
        function onShow(html) {
            if (root.isAnimating) return
            root.isAnimating = true
            exitAnim.start()
            exitAnim.finished.connect(function onExitFinished() {
                exitAnim.finished.disconnect(onExitFinished)
                webView.loadHtml(`
                    <html><body style="background:transparent;color:${root.theme.text};
                    font-family:'Segoe UI',system-ui,sans-serif;font-size:16px;
                    text-align:center;margin:0;padding:0;">${html}</body></html>`)
                cardContainer.x = -60 * root.slideDirection
                cardContainer.opacity = 0
                cardContainer.scale = 0.94
                root.show(); root.raise(); root.requestActivate()
                enterAnim.start()
                enterAnim.finished.connect(function onEnterFinished() {
                    root.isAnimating = false
                    enterAnim.finished.disconnect(onEnterFinished)
                })
            })
        }
        function onHide() { root.hide() }
    }

    // ⏸️ Overlay de Pausa
    Rectangle {
        id: pauseOverlay
        visible: false
        anchors.fill: parent
        color: "#000000"; opacity: 0.65; z: 2000; radius: 16
        Column {
            anchors.centerIn: parent; spacing: 12
            Text { text: "⏸️ Booster Pausado"; font.pixelSize: 20; font.bold: true; color: "white"; horizontalAlignment: Text.AlignHCenter }
            Text { text: "Envie 'TOGGLE_PAUSE' para retomar"; font.pixelSize: 13; color: "#aaa"; horizontalAlignment: Text.AlignHCenter }
            Text {
                text: "▶️"; font.pixelSize: 32; color: "white"; opacity: 0.8; anchors.horizontalCenter: parent.horizontalCenter
                SequentialAnimation {
                    running: pauseOverlay.visible; loops: Animation.Infinite
                    NumberAnimation { property: "scale"; from: 1; to: 1.15; duration: 500; easing.type: Easing.InOutQuad }
                    NumberAnimation { property: "opacity"; from: 0.6; to: 1; duration: 500 }
                }
            }
        }
    }
}