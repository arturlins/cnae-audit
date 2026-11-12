"""Safe markdown rendering of the agent's answer (the text may be influenced by user input)."""

import html
import re

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from markupsafe import Markup

_SAFE_URL = re.compile(r"^https?://", re.IGNORECASE)
_INVISIBLE = re.compile(r"[\x00-\x20\x7f]+")


def url_segura(url: str) -> bool:
    """Only absolute http(s) URLs; entities and whitespace tricks are normalized first."""
    normalizada = _INVISIBLE.sub("", html.unescape(url or ""))
    return bool(_SAFE_URL.match(normalizada))


class _LinksSeguros(Treeprocessor):
    def run(self, root):
        for pai in root.iter():
            for filho in list(pai):
                if filho.tag == "img":
                    # Images are never expected; replace with their alt text.
                    texto = filho.get("alt", "")
                    filho.clear()
                    filho.tag = "span"
                    filho.text = texto
                elif filho.tag == "a":
                    href = filho.get("href", "")
                    if url_segura(href):
                        filho.set("rel", "noopener noreferrer nofollow")
                        filho.set("target", "_blank")
                    else:
                        filho.attrib.pop("href", None)
                        filho.tag = "span"
        return root


class LinksSegurosExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(_LinksSeguros(md), "links_seguros", 0)


def renderizar_markdown(texto: str) -> Markup:
    # Raw HTML from the model is neutralized before conversion; links are allowlisted after.
    seguro = (texto or "").replace("<", "&lt;")
    convertido = markdown.markdown(seguro, extensions=["sane_lists", LinksSegurosExtension()])
    return Markup(convertido)
