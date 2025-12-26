import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import feedparser
from google import genai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Permite que Bolt.new lea los datos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/noticias")
def obtener_noticias():
    try:
        # 1. Verificar API KEY
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return [{"titulo": "Error", "resumen": "No configuraste la GEMINI_API_KEY en Render", "emoji": "❌"}]

        # 2. Configurar Cliente
        client = genai.Client(api_key=api_key)
        
        # 3. Obtener Noticias (Simplificado para prueba)
        feed = feedparser.parse("https://es.investing.com/rss/news.rss")
        primera_noticia = feed.entries[0]
        
        # 4. Pedir a Gemini que resuma (Formato corto para TikTok)
        prompt = f"Resume esta noticia para TikTok en 15 palabras: {primera_noticia.title}"
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        
        return [{
            "id": 1,
            "titulo": primera_noticia.title[:50],
            "resumen": response.text,
            "emoji": "📈",
            "link": primera_noticia.link
        }]
    except Exception as e:
        # Esto te dirá el error real en la pantalla en lugar de "Internal Server Error"
        return [{"titulo": "Error de Python", "resumen": str(e), "emoji": "⚠️"}]
