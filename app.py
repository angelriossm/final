import streamlit as st
import feedparser
import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- 1. CONFIGURACIÓN ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="ZenInvestor Pro", page_icon="🛡️", layout="centered")

if not api_key:
    st.error("❌ Error: No se encontró la API KEY.")
    st.stop()

client = genai.Client(api_key=api_key)

SOURCES = {
    "🇺🇸 Wall Street (CNBC)": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069",
    "🇪🇸 Mercados Europa (Investing)": "https://es.investing.com/rss/news.rss"
}


# --- 2. CEREBRO IA (MODELO 2.5 + PROCESAMIENTO EN LOTE) ---
@st.cache_data(ttl=3600, show_spinner=False)
def analizar_bloque_noticias(lista_noticias_texto):
    """
    Envía TODAS las noticias juntas al modelo 2.5 Flash.
    Al ser una sola llamada, evitamos el bloqueo de velocidad.
    """
    prompt = f"""
    Eres un analista financiero experto. Analiza esta LISTA de noticias.

    NOTICIAS A ANALIZAR:
    {lista_noticias_texto}

    INSTRUCCIONES:
    1. Devuelve un JSON que sea una LISTA de objetos (Array).
    2. Traduce al español (México) y resume.
    3. Sé breve y directo.

    Formato JSON requerido:
    [
        {{
            "titulo_es": "Título traducido",
            "resumen": "Resumen breve",
            "impacto": (Número 1-10),
            "trampa": "Trampa emocional",
            "accion": "Consejo",
            "detalle": "Detalle técnico"
        }},
        ... (repetir para cada noticia en orden)
    ]
    """

    try:
        # VOLVEMOS AL MODELO 2.5 QUE SÍ TIENES
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        # Si falla, mostramos el error en pantalla para depurar
        st.error(f"Error técnico: {e}")
        return []


# --- 3. INTERFAZ ---
st.title("🛡️ ZenInvestor: Modo 2.5")
st.caption("Usando Gemini 2.5 Flash con estrategia Anti-Bloqueo")

if st.button("🔄 Refrescar"):
    st.cache_data.clear()
    st.rerun()

st.markdown("<style>div.block-container{padding-top:2rem;}</style>", unsafe_allow_html=True)

for fuente, url in SOURCES.items():
    st.markdown(f"### {fuente}")

    # 1. Descargamos el feed
    feed = feedparser.parse(url)

    # TRUCO: Solo enviamos 2 noticias para garantizar que el paquete sea ligero
    noticias_a_procesar = feed.entries[:2]

    if not noticias_a_procesar:
        st.warning("No hay noticias en esta fuente.")
        continue

    # 2. Preparamos el TEXTO en bloque (Batching)
    texto_para_ia = ""
    for i, entry in enumerate(noticias_a_procesar):
        texto_para_ia += f"Noticia {i + 1}: {entry.title} - {entry.get('summary', '')}\n---\n"

    # 3. Llamamos a la IA (1 sola llamada = No Bloqueo)
    with st.spinner(f'Procesando bloque de {fuente}...'):
        # Pequeña pausa de seguridad de 1 segundo entre fuentes
        time.sleep(1)
        resultados = analizar_bloque_noticias(texto_para_ia)

    # 4. Dibujamos las tarjetas
    if resultados:
        for i, data in enumerate(resultados):
            # Enlace original seguro
            link_original = noticias_a_procesar[i].link if i < len(noticias_a_procesar) else "#"

            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"**{data.get('titulo_es', 'Sin título')}**")
                with c2:
                    imp = data.get('impacto', 5)
                    color = "normal"
                    if imp >= 8: color = "inverse"
                    st.metric("Impacto", f"{imp}/10", delta_color=color)

                st.info(f"🧐 {data.get('resumen', '...')}")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.warning(f"⚠️ {data.get('trampa', '...')}")
                with col_b:
                    if imp > 6:
                        st.error(f"🛡️ {data.get('accion', '...')}")
                    else:
                        st.success(f"✅ {data.get('accion', '...')}")

                with st.expander("Ver detalle"):
                    st.write(data.get('detalle', ''))
                    st.markdown(f"[Leer original]({link_original})")
    else:
        st.warning("No pudimos analizar estas noticias.")