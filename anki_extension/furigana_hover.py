from aqt.gui_hooks import webview_will_set_content

CSS = """
ruby rt {
    opacity: 0;
    transition: opacity 0.2s ease;
}

/* Mostra o furigana só da palavra que você passar o mouse */
ruby:hover rt {
    opacity: 1;
}
"""

def inject_css(web_content, context):
    web_content.head += f"<style>{CSS}</style>"

webview_will_set_content.append(inject_css)
