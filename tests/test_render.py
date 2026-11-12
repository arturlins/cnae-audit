import pytest

from web.render import renderizar_markdown, url_segura


@pytest.mark.parametrize(
    "texto",
    [
        "[clique](javascript:alert(1))",
        "[clique](JaVaScRiPt:alert(1))",
        "[clique](&#106;avascript:alert(1))",
        "[clique](java\tscript:alert(1))",
        "[clique](data:text/html;base64,PHNjcmlwdD4=)",
        "[clique](vbscript:msgbox(1))",
    ],
)
def test_links_perigosos_perdem_href(texto):
    html = str(renderizar_markdown(texto))
    assert "href" not in html
    assert "clique" in html


def test_link_https_mantido():
    html = str(renderizar_markdown("[IBGE](https://servicodados.ibge.gov.br/api/v2/cnae)"))
    assert 'href="https://servicodados.ibge.gov.br/api/v2/cnae"' in html
    assert 'rel="noopener noreferrer nofollow"' in html


def test_html_cru_e_imagem_neutralizados():
    html = str(renderizar_markdown('<script>alert(1)</script>\n\n![x](https://e.com/a.png "t")'))
    assert "<script" not in html and "<img" not in html


def test_url_segura():
    assert url_segura("http://a.b") and url_segura("HTTPS://a.b")
    assert not url_segura("/relativo") and not url_segura(" javascript:x")
