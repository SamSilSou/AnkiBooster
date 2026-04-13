import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

Window {
    id: root
    visible: false
    width: 440; height: 320
    minimumWidth: 440; minimumHeight: 320
    maximumWidth: 440; maximumHeight: 320
    flags: Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint
    color: "transparent"

    property var theme: {
        "bg": "#251b1a", "surface": "#322826", "text": "#f1dfdc",
        "accent": "#ffb4a8", "accentText": "#561e16"
    }

    // 🔳 Botão fullscreen animado (sutil)
    MouseArea {
        z: 100; width: 28; height: 28
        anchors.top: parent.top; anchors.left: parent.left; anchors.margins: 12
        onClicked: bridge.toggleFullscreen()
        hoverEnabled: true
        onContainsMouseChanged: {
            if (containsMouse) {
                fsAnim.running = true
                fsPulse.running = true
                fsOpacity.to = 0.9
                fsOpacity.start()
            } else {
                fsAnim.running = false
                fsPulse.running = false
                fsText.rotation = 0
                fsText.scale = 1.0
                fsOpacity.to = 0.4
                fsOpacity.start()
            }
        }
        cursorShape: Qt.PointingHandCursor

        Text {
            id: fsText; anchors.centerIn: parent
            text: "⛶"; font.pixelSize: 22; color: "white"; opacity: 0.4
            style: Text.Outline; styleColor: "black"
        }
        
        NumberAnimation { 
            id: fsAnim; target: fsText; property: "rotation"
            from: 0; to: 15; duration: 150
            loops: Animation.Infinite; running: false 
        }
        NumberAnimation { 
            id: fsPulse; target: fsText; property: "scale"
            from: 1.0; to: 1.15; duration: 400
            loops: Animation.Infinite; running: false 
        }
        NumberAnimation { 
            id: fsOpacity; target: fsText; property: "opacity"
            duration: 200; running: false 
        }
    }

    Rectangle {
        anchors.fill: parent; color: theme.bg; radius: 16; clip: true

        ColumnLayout {
            anchors.fill: parent; anchors.margins: 12; spacing: 10

            // WebEngineView (cards)
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 16; color: theme.surface; border.width: 0
                WebEngineView {
                    id: web; anchors.fill: parent; anchors.margins: 12
                    backgroundColor: "transparent"; clip: true
                }
            }

            // Botão "Mostrar resposta"
            Rectangle {
                id: showBtn; Layout.fillWidth: true; height: 44; radius: 12
                color: theme.surface
                Behavior on color { ColorAnimation { duration: 120 } }
                MouseArea {
                    id: showMouse; anchors.fill: parent; hoverEnabled: true
                    onEntered: showBtn.scale = 1.02; onExited: showBtn.scale = 1.0; onPressed: showBtn.scale = 0.98
                    onClicked: {
                        bridge.onShowAnswerClicked()
                        emojiShow.text = "👁️"; emojiShowAnim.start()
                    }
                }
                Text {
                    text: "Mostrar resposta 👀"; anchors.centerIn: parent
                    color: theme.text; font.pixelSize: 15; font.bold: true
                }
                Text {
                    id: emojiShow; visible: false; anchors.centerIn: showBtn
                    font.pixelSize: 24; opacity: 0
                    SequentialAnimation {
                        id: emojiShowAnim
                        PropertyAction { target: emojiShow; property: "visible"; value: true }
                        ParallelAnimation {
                            NumberAnimation { target: emojiShow; property: "opacity"; from: 0; to: 1; duration: 100 }
                            NumberAnimation { target: emojiShow; property: "y"; from: 0; to: -20; duration: 300; easing.type: Easing.OutQuad }
                            NumberAnimation { target: emojiShow; property: "scale"; from: 1; to: 1.5; duration: 300 }
                        }
                        PauseAnimation { duration: 200 }
                        NumberAnimation { target: emojiShow; property: "opacity"; to: 0; duration: 150 }
                        PropertyAction { target: emojiShow; property: "visible"; value: false }
                        PropertyAction { target: emojiShow; property: "y"; value: 0 }
                        PropertyAction { target: emojiShow; property: "scale"; value: 1 }
                    }
                }
            }

            // Botões de resposta
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Repeater {
                    model: [
                        { label: "Fácil 😎", color: "#a5d6a7", press: "#81c784", emoji: "🚀" },
                        { label: "Ok 😐", color: "#ffe082", press: "#ffd54f", emoji: "👍" },
                        { label: "Difícil 😢", color: "#ffcc80", press: "#ffb74d", emoji: "💪" },
                        { label: "Errei 💀", color: "#ff6b6b", press: "#d64a4a", emoji: "🔄", txt: "white" }
                    ]
                    delegate: Rectangle {
                        id: btn; Layout.fillWidth: true; height: 46; radius: 12
                        color: modelData.color; scale: 1.0
                        Behavior on color { ColorAnimation { duration: 100 } }
                        Behavior on scale { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
                        MouseArea {
                            anchors.fill: parent; hoverEnabled: true
                            onEntered: btn.scale = 1.03; onExited: btn.scale = 1.0; onPressed: btn.scale = 0.96
                            onClicked: {
                                if (index === 0) bridge.answerEasy()
                                else if (index === 1) bridge.answerOk()
                                else if (index === 2) bridge.answerHard()
                                else bridge.answerFail()
                                feedbackEmoji.text = modelData.emoji
                                feedbackEmoji.color = modelData.txt || "black"
                                feedbackAnim.start()
                            }
                        }
                        Text {
                            text: modelData.label; anchors.centerIn: parent
                            color: modelData.txt || "black"; font.bold: true; font.pixelSize: 14
                        }
                    }
                }
                // Emoji de feedback (aparece só no click)
                Text {
                    id: feedbackEmoji; visible: false; anchors.centerIn: parent
                    font.pixelSize: 28; opacity: 0; z: 50
                    SequentialAnimation {
                        id: feedbackAnim
                        PropertyAction { target: feedbackEmoji; property: "visible"; value: true }
                        ParallelAnimation {
                            NumberAnimation { target: feedbackEmoji; property: "opacity"; from: 0; to: 1; duration: 80 }
                            NumberAnimation { target: feedbackEmoji; property: "y"; from: 0; to: -40; duration: 400; easing.type: Easing.OutQuad }
                            NumberAnimation { target: feedbackEmoji; property: "scale"; from: 1; to: 1.8; duration: 400 }
                            RotationAnimation { target: feedbackEmoji; from: -10; to: 10; duration: 400; loops: 2 }
                        }
                        PauseAnimation { duration: 150 }
                        NumberAnimation { target: feedbackEmoji; property: "opacity"; to: 0; duration: 200 }
                        PropertyAction { target: feedbackEmoji; property: "visible"; value: false }
                        PropertyAction { target: feedbackEmoji; property: "y"; value: 0 }
                        PropertyAction { target: feedbackEmoji; property: "scale"; value: 1 }
                    }
                }
            }
        }
    }

    // Conexões com Python
    Connections {
        target: bridge
        function onShow(html) {
            web.loadHtml(`
                <html><body style="background:transparent;color:${theme.text};font-family:'Google Sans Flex';font-size:16px;text-align:center;margin:0;padding:0;">
                ${html}</body></html>`)
            root.show(); root.raise(); root.requestActivate()
        }
        function onHide() { root.hide() }
    }
}