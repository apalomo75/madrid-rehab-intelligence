"""Data-free landing page for the commercial application."""

from base64 import b64encode
from html import escape
from importlib.resources import files

import streamlit as st

from .i18n import language_selector, t
from .navigation import PRIMARY, open_product

MAP_URI = "data:image/svg+xml;base64," + b64encode(
    files("madrid_rehab").joinpath("assets", "madrid_layers.svg").read_bytes()
).decode("ascii")

STYLE = """
<style>
body:has(.st-key-welcome) :is(
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stExpandSidebarButton"]
) { display: none; }
body:has(.st-key-welcome) [data-testid="stHeader"] { background: transparent; }

.st-key-welcome {
    --welcome-ink: #edf5f7;
    --welcome-muted: #b6c9d2;
    --welcome-accent: #83e2cf;
    max-width: 82rem;
    margin-inline: auto;
}
.st-key-welcome_hero {
    position: relative;
    isolation: isolate;
    overflow: hidden;
    padding: clamp(1rem, 2vw, 1.75rem);
    border: 1px solid #2c5059;
    border-radius: 1.25rem;
    background: #101e2b;
    color: var(--welcome-ink);
}
.st-key-welcome_language {
    width: fit-content;
    align-self: flex-end;
}
.st-key-welcome_language [role="radiogroup"] label > div:first-child {
    background-color: #38505f;
}
.st-key-welcome_language [role="radiogroup"] label:has(input:checked) > div:first-child {
    background-color: #83e2cf;
}
.st-key-welcome_language [data-testid="stMarkdownContainer"] p { color: var(--welcome-ink); }
.st-key-welcome_hero h1 {
    color: inherit;
    padding-block: 0;
    font-size: clamp(2rem, 4vw, 3.75rem);
    line-height: 1.05;
    letter-spacing: -.045em;
}
.st-key-welcome_hero p { max-width: 76ch; color: var(--welcome-muted); }
.st-key-welcome_hero strong {
    color: var(--welcome-accent);
    font-size: clamp(1.05rem, 2vw, 1.4rem);
    font-weight: 600;
}
.st-key-welcome_hero em { font-style: normal; color: var(--welcome-ink); }
.welcome-map {
    margin: 0;
    border: 1px solid #2c5059;
    border-radius: .9rem;
    overflow: hidden;
    background: #101e2b;
    color: var(--welcome-muted);
}
.welcome-map-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) max-content;
    align-items: stretch;
}
.welcome-map img {
    display: block;
    width: 100%;
    height: clamp(6rem, 13vw, 10rem);
    object-fit: fill;
}
.welcome-map ul {
    display: grid;
    grid-template-rows: repeat(4, 1fr);
    list-style: none;
    margin: 0;
    padding: 0 .85rem 0 .5rem;
    font-size: .85rem;
    line-height: 1.2;
}
.welcome-map li { display: flex; align-items: center; gap: .45rem; margin: 0; }
.welcome-map li::before {
    content: "";
    flex: 0 0 .4rem;
    height: .4rem;
    border-radius: 50%;
    background: var(--welcome-accent);
}
.welcome-map li:nth-child(even)::before { background: #91bee8; }
.welcome-map figcaption {
    padding: .35rem .75rem;
    border-top: 1px solid #2c5059;
    font-size: .8rem;
}
.st-key-welcome_cards [data-testid="stColumn"] > div,
.st-key-welcome_cards [data-testid="stButton"] { height: 100%; }
.st-key-welcome_cards button {
    min-height: 8.5rem;
    height: 100%;
    padding: 1.1rem 1.25rem;
    gap: .8rem;
    align-items: flex-start;
    justify-content: flex-start;
    text-align: start;
    border: 1px solid #37525e;
    border-radius: .9rem;
    background: #142633;
    color: var(--welcome-ink);
}
.st-key-welcome_cards button :is([data-testid="stIconMaterial"], [data-testid="stIconEmoji"]) {
    color: var(--welcome-accent);
    font-size: 1.5rem;
}
.st-key-welcome_cards button p { color: var(--welcome-muted); line-height: 1.45; }
.st-key-welcome_cards button strong {
    display: inline-block;
    margin-bottom: .25rem;
    color: var(--welcome-ink);
    font-size: 1.1rem;
}
.st-key-welcome_cards button:hover { background: #1b3642; border-color: var(--welcome-accent); }
.st-key-welcome_cards button:focus-visible {
    outline: 2px solid var(--welcome-accent);
    outline-offset: 2px;
}
.st-key-welcome_sections {
    padding: 1rem .2rem 0;
    border-top: 1px solid #56717d;
}
.st-key-welcome_sections h2 { font-size: 1.15rem; padding-block: 0; }
.st-key-welcome_sections p { max-width: 65ch; }
@media (min-width: 1000px) {
    .st-key-welcome_language { position: absolute; top: 1rem; right: 1rem; }
    .st-key-welcome_hero h1 { padding-inline-end: 8rem; }
}
@media (max-width: 800px) {
    .st-key-welcome :is(.st-key-welcome_cards, .st-key-welcome_sections)
        [data-testid="stHorizontalBlock"] { flex-direction: column; gap: 1rem; }
    .st-key-welcome :is(.st-key-welcome_cards, .st-key-welcome_sections)
        [data-testid="stColumn"] { width: 100%; flex: 1 1 auto; }
    .st-key-welcome_cards button { min-height: 0; }
}
@media (max-width: 600px) {
    .welcome-map-layout { grid-template-columns: minmax(0, 1fr); }
    .welcome-map ul {
        grid-template: auto auto / minmax(0, 1fr) minmax(0, 1fr);
        gap: .45rem;
        padding: .5rem .75rem;
    }
}
</style>
"""


def render():
    st.html(STYLE)
    with st.container(key="welcome"):
        with st.container(key="welcome_hero"):
            with st.container(key="welcome_language"):
                language_selector(sidebar=False)
            st.title("Madrid Rehab Intelligence", anchor=False)
            st.markdown(f"**{t('welcome.subtitle')}**")
            st.markdown(t("welcome.intro"))
            st.markdown(f"*{t('welcome.author')}*")
        st.html(
            f'<figure class="welcome-map"><div class="welcome-map-layout">'
            f'<img src="{MAP_URI}" alt="{escape(t("welcome.map_alt"))}">'
            f"<ul><li>CEEE</li><li>NextGenerationEU</li>"
            f"<li>{escape(t('welcome.map_inspections'))}</li>"
            f"<li>{escape(t('welcome.map_building_book'))}</li></ul></div>"
            f"<figcaption>{escape(t('welcome.map_caption'))}</figcaption></figure>"
        )
        with st.container(key="welcome_cards"):
            cards = zip(
                st.columns(3),
                PRIMARY,
                ("explore", "address", "about"),
                ("map", "search", "info"),
                strict=True,
            )
            for column, route, name, icon in cards:
                column.button(
                    f"**{t(f'nav.{name}')}**  \n{t(f'welcome.{name}')}",
                    icon=f":material/{icon}:",
                    width="stretch",
                    key=f"welcome_open_{name}",
                    on_click=open_product,
                    args=(route,),
                )
        with st.container(key="welcome_sections"):
            data, collaborate = st.columns([3, 2], gap="large")
            data.header(t("welcome.data_title"), anchor=False)
            data.markdown(t("welcome.data"))
            collaborate.header(t("welcome.collaborate_title"), anchor=False)
            collaborate.markdown(t("welcome.collaborate"))
