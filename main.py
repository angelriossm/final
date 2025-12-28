import os
import time
import json
import re
import feedparser
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CACHÉ ---
CACHE_PAGINAS = {}
ULTIMA_ACTUALIZACION = 0
TIEMPO_EXPIRACION = 900  # 15 minutos

def limpiar_json(texto):
    """Limpia el texto para extraer el bloque JSON"""
    texto = re.sub(r'```json\s*|\s*```', '', texto).strip()
    match = re.search(r'\[.*\]', texto, re.DOTALL) # Buscamos una LISTA []
    return match.group(0) if match else texto

# --- NUEVA FUNCIÓN: PROCESAMIENTO EN LOTE (BATCH) ---
def analizar_bloque_noticias(client, lista_entradas):
    """Envía 5 noticias juntas a Gemini para ahorrar llamadas y tiempo."""
    
    texto_combinado = ""
    for i, entry in enumerate(lista_entradas):
        resumen = getattr(entry, "summary", getattr(entry, "description", ""))
        texto_combinado += f"--- NOTICIA {i+1} ---\nLink: {entry.link}\nTítulo: {entry.title}\nTexto: {resumen}\n\n"

    prompt = f"""
    Eres un mentor de inversiones para principiantes en México.
    Analiza este BLOQUE de {len(lista_entradas)} noticias financieras.
    
    Tu objetivo: Filtrar el ruido y explicar si esto afecta al dinero de una persona normal.

    INPUT:
    {texto_combinado}

    INSTRUCCIONES DE SALIDA:
    Devuelve estrictamente un JSON que sea una LISTA (Array) de objetos.
    El orden debe corresponder exactamente a las noticias de entrada.
    
    Formato de cada objeto en la lista:
    {{
        "link_original": "El link provisto en la noticia (para mapear)",
        "titulo": "Título ultra sencillo (máx 8 palabras)",
        "que_paso": "Explicación simple (máx 20 palabras)",
        "me_afecta": "Alta, Media, Baja o Nula",
        "que_hacer": "Consejo de calma y mentalidad (NO financiero, máx 15 palabras)",
        "ruido": "Mucho, Medio o Poco (¿Es chisme o es estructural?)",
        "sentimiento": "Positivo, Negativo o Neutro",
        "impacto": 1 al 10
    }}
    """
    
    try:
        # Una sola llamada para procesar todo el bloque
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite", 
            contents=prompt
        )
        json_str = limpiar_json(response.text)
        datos_lista = json.loads(json_str)
        return datos_lista
    except Exception as e:
        print(f"Error en batch IA: {e}")
        return []

@app.get("/")
def home():
    return {"status": "OK", "mode": "Batch Optimization"}

@app.get("/feed")
def obtener_feed(page: int = Query(1, ge=1)):
    global CACHE_PAGINAS, ULTIMA_ACTUALIZACION

    ahora = time.time()
    
    # 1. Limpieza de caché por tiempo
    if ahora - ULTIMA_ACTUALIZACION > TIEMPO_EXPIRACION:
        CACHE_PAGINAS = {}
        ULTIMA_ACTUALIZACION = ahora

    # 2. Respuesta rápida si está en caché
    if page in CACHE_PAGINAS:
        return CACHE_PAGINAS[page]

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"error": "Falta API KEY"}
        
        client = genai.Client(api_key=api_key)
        feed = feedparser.parse("https://es.investing.com/rss/news.rss")

        # Paginación
        TAMANO = 5
        inicio = (page - 1) * TAMANO
        fin = inicio + TAMANO

        if inicio >= len(feed.entries):
            return {"mensaje_dia": "Has leído todo por hoy.", "noticias": []}

        # Seleccionamos el bloque de 5 noticias
        bloque_entradas = feed.entries[inicio:fin]
        
        # --- AQUÍ OCURRE LA MAGIA DEL BATCH ---
        # Enviamos las 5 juntas a la IA
        analisis_ia = analizar_bloque_noticias(client, bloque_entradas)
        
        # Combinamos la respuesta de la IA con los datos originales (por seguridad)
        noticias_finales = []
        for i, entry in enumerate(bloque_entradas):
            # Intentamos buscar el análisis correspondiente, si falla usamos fallback
            dato = {}
            if i < len(analisis_ia):
                dato = analisis_ia[i]
            
            noticias_finales.append({
                "id": entry.link,
                "titulo": dato.get("titulo", entry.title),
                "que_paso": dato.get("que_paso", "Analizando..."),
                "me_afecta": dato.get("me_afecta", "Baja"),
                "que_hacer": dato.get("que_hacer", "Mantén tu estrategia a largo plazo."),
                "ruido": dato.get("ruido", "Medio"),
                "sentimiento": dato.get("sentimiento", "Neutro"),
                "impacto": dato.get("impacto", 5),
                "link": entry.link
            })

        # Estructura de respuesta con el "Nivel Cero"
        respuesta_completa = {
            "mensaje_dia": "👋 Hola. Esto es lo que se mueve hoy en los mercados y cómo podría afectar tu bolsillo.",
            "noticias": noticias_finales
        }

        CACHE_PAGINAS[page] = respuesta_completa
        return respuesta_completa

    except Exception as e:
        print(f"Error server: {e}")
        return {"mensaje_dia": "Error de conexión", "noticias": []}
