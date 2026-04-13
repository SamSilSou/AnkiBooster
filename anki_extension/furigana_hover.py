from aqt.gui_hooks import webview_will_set_content

CSS = """
@media (hover: hover) {
    ruby rt {
        opacity: 0;
        transition: opacity 0.2s ease;
    }
    ruby:hover rt {
        opacity: 1;
    }
}
"""

def inject_css(web_content, context):
    if context != "reviewer":
        return
    web_content.head += f"<style>{CSS}</style>"

webview_will_set_content.append(inject_css)