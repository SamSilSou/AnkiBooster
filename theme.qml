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
    property bool isAnimating: falses

    property var theme: {
        "bg": "#251b1a",
        "surface": "#322826",
        "text": "#f1dfdc",
        "accent": "#ffb4a8",
        "accentText": "#561e16"
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

    // Fullscreen Toggle
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
            text: "⛶"; font.pixelSize: 20; color: "white"; opacity: 0.5; scale: 1.0
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

            // Card Container
            Rectangle {
                id: cardContainer
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 16
                color: theme.surface
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

                // OVERLAY DE SNOOZE
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

                        // Header
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "🌙"; font.pixelSize: 24 }
                            Text {
                                text: "Quanto tempo de soneca?"
                                color: theme.text
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
                                    color: theme.text
                                    font.pixelSize: 18
                                    opacity: 0.7
                                    Behavior on opacity { NumberAnimation { duration: 100 } }
                                }
                                onEntered: parent.opacity = 1.0
                                onExited: parent.opacity = 0.7
                            }
                        }

                        // Controles de tempo
                        RowLayout {
                            id: timeControls
                            Layout.fillWidth: true
                            spacing: 8
                            property int minutes: 30

                            Rectangle {
                                Layout.preferredWidth: 48; height: 36; radius: 8; color: "#4a5568"
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: parent.color = "#5a6578"
                                    onExited: parent.color = "#4a5568"
                                    onClicked: {
                                        timeControls.minutes = Math.max(1, timeControls.minutes - 5)
                                        if (soundsEnabled) sndClick.play()
                                    }
                                    Text { text: "-5m"; anchors.centerIn: parent; color: theme.text; font.pixelSize: 14; font.bold: true }
                                }
                            }
                            Rectangle {
                                Layout.preferredWidth: 48; height: 36; radius: 8; color: "#4a5568"
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: parent.color = "#5a6578"
                                    onExited: parent.color = "#4a5568"
                                    onClicked: {
                                        timeControls.minutes = Math.max(1, timeControls.minutes - 1)
                                        if (soundsEnabled) sndClick.play()
                                    }
                                    Text { text: "-1m"; anchors.centerIn: parent; color: theme.text; font.pixelSize: 14; font.bold: true }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 36; radius: 8
                                color: "#251b1a"
                                border.color: theme.accent
                                border.width: 2
                                Text {
                                    text: timeControls.minutes + " minutos"
                                    anchors.centerIn: parent
                                    color: theme.text
                                    font.pixelSize: 15
                                    font.bold: true
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: 48; height: 36; radius: 8; color: "#4a5568"
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: parent.color = "#5a6578"
                                    onExited: parent.color = "#4a5568"
                                    onClicked: {
                                        timeControls.minutes = Math.min(120, timeControls.minutes + 1)
                                        if (soundsEnabled) sndClick.play()
                                    }
                                    Text { text: "+1m"; anchors.centerIn: parent; color: theme.text; font.pixelSize: 14; font.bold: true }
                                }
                            }
                            Rectangle {
                                Layout.preferredWidth: 48; height: 36; radius: 8; color: "#4a5568"
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: parent.color = "#5a6578"
                                    onExited: parent.color = "#4a5568"
                                    onClicked: {
                                        timeControls.minutes = Math.min(120, timeControls.minutes + 5)
                                        if (soundsEnabled) sndClick.play()
                                    }
                                    Text { text: "+5m"; anchors.centerIn: parent; color: theme.text; font.pixelSize: 14; font.bold: true }
                                }
                            }
                        }

                        // Botoes de acao
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Rectangle {
                                Layout.fillWidth: true; height: 40; radius: 10; color: "#4a5568"
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: parent.color = "#5a6578"
                                    onExited: parent.color = "#4a5568"
                                    onClicked: {
                                        snoozeOverlay.opacity = 0
                                        if (soundsEnabled) sndSoft.play()
                                    }
                                    Text {
                                        text: "Cancelar"
                                        anchors.centerIn: parent
                                        color: theme.text
                                        font.bold: true
                                        font.pixelSize: 14
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 40; radius: 10; color: theme.accent
                                Behavior on color { ColorAnimation { duration: 100 } }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: parent.color = "#ff9a8e"
                                    onExited: parent.color = theme.accent
                                    onClicked: {
                                        var mins = timeControls.minutes
                                        bridge.snoozeWithMinutes(mins)
                                        snoozeOverlay.opacity = 0
                                        if (soundsEnabled) sndWhoosh.play()
                                    }
                                    Text {
                                        text: "Confirmar"
                                        anchors.centerIn: parent
                                        color: theme.accentText
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
                color: theme.surface
                scale: 1.0
                clip: true
                Behavior on scale { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
                Behavior on color { ColorAnimation { duration: 120 } }

                Item {
                    id: rippleShow; anchors.centerIn: parent; width: 0; height: 0
                    Rectangle {
                        anchors.centerIn: parent
                        width: rippleShow.width; height: rippleShow.height
                        radius: width/2; color: theme.accent; opacity: 0.5
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
                    color: theme.text
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
                    color: "#4a5568"
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
                        onClicked: {
                            snoozeOverlay.opacity = 1
                            if (soundsEnabled) sndClick.play()
                        }
                    }
                    Text { text: "🌙"; anchors.centerIn: parent; font.pixelSize: 20; color: theme.text; opacity: 0.9 }
                }

                Repeater {
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

    // Exit animation
    ParallelAnimation {
        id: exitAnim
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
        NumberAnimation { target: cardContainer; property: "scale"; to: 0.96; duration: 60; easing.type: Easing.InQuad }
        ScriptAction {
            script: {
                bridge.onShowAnswerClicked()
                feedbackShow.text = "👁️"
                feedbackShow.opacity = 1
                feedbackShow.visible = true
                fadeShowOut.start()
            }
        }
        NumberAnimation { target: cardContainer; property: "scale"; to: 1.03; duration: 100; easing.type: Easing.OutBack }
        NumberAnimation { target: cardContainer; property: "scale"; to: 1.0; duration: 80; easing.type: Easing.OutQuad }
    }

    // Conexoes com Python
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
                    text-align:center;margin:0;padding:0;word-wrap:break-word;">${html}</body></html>`)
                cardContainer.x = -60 * root.slideDirection
                cardContainer.opacity = 0
                cardContainer.scale = 0.94
                cardContainer.rotation = 0
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

    // Focus glow
    Rectangle {
        id: focusGlow
        anchors.fill: cardContainer
        radius: cardContainer.radius
        color: "transparent"
        border.color: theme.accent
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
