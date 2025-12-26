from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import feedparser
import os
from google import genai

app = FastAPI()

# Esto permite que tu App de TikTok (Bolt) se conecte a este Python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/noticias")
def obtener_noticias():
    # Aquí configuramos Gemini (Render leerá la KEY de sus "Environment Variables")
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    # Leemos las noticias (puedes añadir más URLs aquí)
    url = "https://es.investing.com/rss/news.rss"
    feed = feedparser.parse(url)

    lista_final = []

    # Procesamos solo las primeras 5 noticias para que sea rápido
    for entrada in feed.entries[:5]:
        prompt = f"Resume esta noticia financiera para un TikToker: {entrada.title}. Devuelve solo un resumen de 2 frases, un emoji y un puntaje de impacto del 1 al 10."

        try:
            response = client.models.generate_content(model="gemini-2.0-flash-exp", contents=prompt)
            texto_ia = response.text

            # Guardamos la noticia en el formato que usará la App de TikTok
            lista_final.append({
                "titulo": entrada.title,
                "resumen": texto_ia,
                "link": entrada.link,
                "emoji": "💰"  # Podrías hacer que Gemini elija el emoji también
            })
        except:
            continue

    return lista_final