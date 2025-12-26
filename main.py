import os
import time
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import feedparser
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# --- CONFIGURACIÓN DE SEGURIDAD (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MEMORIA (CACHÉ) ---
# Guarda las noticias 15 minutos para no gastar peticiones si recargas mucho
CACHE_NOTICIAS = []
ULTIMA_ACTUALIZACION = 0
TIEMPO_CACHE = 900 

@app.get("/")
def home():
    return {"status": "Online", "model": "Gemini 2.5 Flash Lite", "mensaje": "Usa /noticias"}

@app.get("/noticias")
def obtener_noticias():
    global CACHE_NOTICIAS, ULTIMA_ACTUALIZACION
    
    ahora = time.time()
    
    # 1. Verificar Caché (Ahorra peticiones y tiempo)
    if CACHE_NOTICIAS and (ahora - ULTIMA_ACTUALIZACION < TIEMPO_CACHE):
        print("⚡ Usando caché (Memoria rápida)")
        return CACHE_NOTICIAS

    # 2. Llamar a la IA si el caché expiró
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return [{"titulo": "Error Config", "resumen": "Falta la API KEY", "emoji": "❌"}]

        client = genai.Client(api_key=api_key)
        
        # Fuente RSS
        rss_url = "https://es.investing.com/rss/news.rss"
        feed = feedparser.parse(rss_url)
        entradas = feed.entries[:5] # Analizamos 5 noticias
        noticias_procesadas = []

        for entry in entradas:
            prompt = f"""
            Eres un editor de noticias financieras virales. Resume esto: '{entry.title}'.
            SALIDA JSON EXACTA:
            {{
                "titulo": "Título clickbait corto",
                "resumen": "Resumen muy breve (max 15 palabras) para gente joven.",
                "emoji": "Un solo emoji",
                "impacto": "Positivo, Negativo o Neutro"
            }}
            """
            
            # --- AQUÍ ESTÁ EL CAMBIO AL MODELO LITE ---
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite", 
                contents=prompt
            )
            
            # Limpieza del JSON
            texto_limpio = response.text.replace("```json", "").replace("```", "").strip()
            datos_ia = json.loads(texto_limpio)
            
            noticias_procesadas.append({
                "id": entry.link,
                "titulo": datos_ia.get("titulo", entry.title),
                "resumen": datos_ia.get("resumen", "Ver más..."),
                "emoji": datos_ia.get("emoji", "⚡"),
                "impacto": datos_ia.get("impacto", "Neutro"),
                "link": entry.link
            })

        # Actualizar memoria
        CACHE_NOTICIAS = noticias_procesadas
        ULTIMA_ACTUALIZACION = ahora
        
        return noticias_procesadas

    except Exception as e:
        print(f"Error: {e}")
        return [{
            "titulo": "Error Técnico", 
            "resumen": f"Algo falló: {str(e)}", 
            "emoji": "⚠️", 
            "link": "#"
        }]
