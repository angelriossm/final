import os
import time
import json
import re
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
CACHE_NOTICIAS = []
ULTIMA_ACTUALIZACION = 0
TIEMPO_CACHE = 900  # 15 minutos

def limpiar_json(texto):
    """Limpia la respuesta de la IA para obtener solo el JSON."""
    texto = re.sub(r'```json\s*|\s*```', '', texto).strip()
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        return match.group(0)
    return texto

@app.get("/")
def home():
    return {"status": "Online", "style": "Robust Mode", "mensaje": "Usa /noticias"}

@app.get("/noticias")
def obtener_noticias():
    global CACHE_NOTICIAS, ULTIMA_ACTUALIZACION
    
    ahora = time.time()
    
    # 1. Verificar Caché
    if CACHE_NOTICIAS and (ahora - ULTIMA_ACTUALIZACION < TIEMPO_CACHE):
        print("⚡ Usando caché (Memoria rápida)")
        return CACHE_NOTICIAS

    # 2. Llamar a la IA
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return [{"titulo": "Error Config", "que_paso": "Falta API KEY", "sentimiento": "Negativo"}]

        client = genai.Client(api_key=api_key)
        
        rss_url = "https://es.investing.com/rss/news.rss"
        feed = feedparser.parse(rss_url)
        entradas = feed.entries[:5]
        noticias_procesadas = []

        for entry in entradas:
            # --- CORRECCIÓN DEL ERROR 'NO ATTRIBUTE' ---
            # Intentamos obtener 'summary' o 'description', si no existen, usamos vacío.
            resumen_rss = getattr(entry, "summary", getattr(entry, "description", ""))
            
            prompt = f"""
            Analiza esta noticia financiera: '{entry.title} - {resumen_rss}'.
            
            Actúa como un analista financiero senior de alto nivel.
            Tu tono es serio, directo y minimalista. NO uses emojis ni lenguaje sensacionalista.
            
            Genera un JSON con estos campos exactos:
            {{
                "titulo": "Título profesional y sobrio (máx 8 palabras)",
                "que_paso": "Resumen ejecutivo del evento (máx 25 palabras)",
                "por_que_importa": "Análisis de la implicación financiera (máx 25 palabras)",
                "sentimiento": "Debe ser exactamente uno de estos tres: 'Positivo', 'Negativo', 'Neutro'",
                "impacto": "Número entero del 1 al 10 indicando la fuerza del movimiento"
            }}
            """
            
            try:
                # Usamos el modelo Lite
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite", 
                    contents=prompt
                )
                
                texto_limpio = limpiar_json(response.text)
                datos_ia = json.loads(texto_limpio)
                
                noticias_procesadas.append({
                    "id": entry.link,
                    "titulo": datos_ia.get("titulo", entry.title),
                    "que_paso": datos_ia.get("que_paso", "No disponible"),
                    "por_que_importa": datos_ia.get("por_que_importa", "No disponible"),
                    "sentimiento": datos_ia.get("sentimiento", "Neutro"),
                    "impacto": datos_ia.get("impacto", 5),
                    "link": entry.link
                })
            except Exception as e_gemini:
                print(f"Error IA: {e_gemini}")
                continue

        if noticias_procesadas:
            CACHE_NOTICIAS = noticias_procesadas
            ULTIMA_ACTUALIZACION = ahora
        
        return noticias_procesadas

    except Exception as e:
        print(f"Error general: {e}")
        # Devuelve un error visible en la App en lugar de romperla
        return [{
            "titulo": "Mantenimiento", 
            "que_paso": "Estamos ajustando los servidores de noticias.",
            "por_que_importa": "Intenta recargar en 1 minuto.",
            "sentimiento": "Neutro",
            "impacto": 1,
            "link": "#"
        }]
