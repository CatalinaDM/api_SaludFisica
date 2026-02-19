from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv

load_dotenv()  # carga el archivo .env automáticamente

# ExerciseDB
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

EXERCISEDB_HEADERS = {
    "X-RapidAPI-Key":  RAPIDAPI_KEY,
    "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
}

# Edamam
APP_ID  = os.getenv("EDAMAM_APP_ID")
APP_KEY = os.getenv("EDAMAM_APP_KEY")


# pip install deep-translator
try:
    from deep_translator import GoogleTranslator
    TRADUCTOR_DISPONIBLE = True
except ImportError:
    TRADUCTOR_DISPONIBLE = False
    print("⚠️  deep-translator no instalado. pip install deep-translator")

app = Flask(__name__)

# Separador que NO aparece en texto normal, para unir todo en 1 solo request
_SEP = " ||| "


def traducir_en_lote(textos):
    """
    Traduce una lista de strings con UNA SOLA llamada a Google Translate.

    Antes: 1 llamada HTTP por texto  → 180+ requests, ~30-60 seg de espera
    Ahora: 1 llamada HTTP total      → ~1-2 seg extra nada más
    """
    if not TRADUCTOR_DISPONIBLE or not textos:
        return textos
    try:
        bloque    = _SEP.join(textos)
        traducido = GoogleTranslator(source="en", target="es").translate(bloque)
        partes    = traducido.split(_SEP)
        # Si Google alteró el separador, fallback al original sin crashear
        if len(partes) != len(textos):
            return textos
        return [p.strip() for p in partes]
    except Exception as e:
        print(f"Error al traducir: {e}")
        return textos

# -------------------------------------------------------
#           FRASES (ZenQuotes)
# -------------------------------------------------------
@app.route("/")
def index():
    try:
        response   = requests.get("https://zenquotes.io/api/random", timeout=5)
        frase_data = response.json()[0]
        frase      = frase_data["q"]
        autor      = frase_data["a"]

        frase_en = frase_data["q"]
        frase = traducir_en_lote([frase_en])[0]

    except Exception:
        frase = "No se pudo obtener una frase."
        autor = "Error"

    return render_template("index.html", frase=frase, autor=autor, title="Principal Principal")

# -------------------------------------------------------
#    EJERCICIOS (ExerciseDB — RapidAPI)
# -------------------------------------------------------


EXERCISEDB_HEADERS = {
    "X-RapidAPI-Key":   RAPIDAPI_KEY,
    "X-RapidAPI-Host":  "exercisedb.p.rapidapi.com"
}


@app.route("/ejercicios")
def ejercicios():
    body_part = request.args.get("bodyPart", "all")

    try:
        if body_part == "all":
            url = "https://exercisedb.p.rapidapi.com/exercises?limit=30&offset=0"
        else:
            url = (f"https://exercisedb.p.rapidapi.com/exercises/bodyPart/"
                   f"{body_part}?limit=30&offset=0")

        r    = requests.get(url, headers=EXERCISEDB_HEADERS, timeout=8)
        data = r.json()

        ejercicios_raw = data if isinstance(data, list) else []

        # ── Traducción EN LOTE: 1 sola llamada HTTP para TODOS los ejercicios ──
        # Recolectamos descripciones e instrucciones en listas planas
        descripciones = [e.get("description", "") for e in ejercicios_raw]
        instrucciones_flat  = []   # lista plana de todos los pasos
        instrucciones_lens  = []   # cuántos pasos tiene cada ejercicio

        for e in ejercicios_raw:
            pasos = e.get("instructions", [])
            instrucciones_lens.append(len(pasos))
            instrucciones_flat.extend(pasos)

        # UNA llamada para descripciones, UNA para instrucciones
        desc_traducidas  = traducir_en_lote(descripciones)
        instr_traducidas = traducir_en_lote(instrucciones_flat)

        # Repartir instrucciones traducidas de vuelta a cada ejercicio
        cursor = 0
        for i, e in enumerate(ejercicios_raw):
            e["descripcion"]  = desc_traducidas[i] if desc_traducidas else e.get("description", "")

            n = instrucciones_lens[i]
            e["instrucciones"] = instr_traducidas[cursor:cursor + n]
            cursor += n

            # Imagen: gifUrl del plan pago, o GitHub repo como fallback
            if not e.get("gifUrl"):
                nombre_carpeta = e["name"].replace(" ", "_").title()
                e["gifUrl"] = (
                    f"https://raw.githubusercontent.com/yuhonas/free-exercise-db"
                    f"/main/exercises/{nombre_carpeta}/0.jpg"
                )

    except Exception as ex:
        print(f"Error al obtener ejercicios: {ex}")
        ejercicios_raw = []

    return render_template(
        "ejercicios.html",
        ejercicios=ejercicios_raw,
        bodyPart=body_part,
        title="Ejercicios"
    )


# -------------------------------------------------------
#           NUTRICIÓN (Edamam)
# -------------------------------------------------------

@app.route("/nutricion", methods=["GET", "POST"])
def nutricion():
    alimento = None
    nutrientes = None

    if request.method == "POST":
        alimento = request.form.get("alimento", "").strip()

        try:
            url = (f"https://api.edamam.com/api/nutrition-data"
                   f"?app_id={APP_ID}&app_key={APP_KEY}&ingr=1%20{alimento}")

            r = requests.get(url, timeout=6)
            datos = r.json()

            # Extraer nutrientes de la nueva estructura
            ingredientes = datos.get("ingredients", [])
            if ingredientes and "parsed" in ingredientes[0] and ingredientes[0]["parsed"]:
                nutrientes = ingredientes[0]["parsed"][0]["nutrients"]

        except Exception:
            nutrientes = None

    return render_template("nutricion.html",
                           alimento=alimento,
                           nutrientes=nutrientes,
                           title="Nutrición")

# -------------------------------------------------------
#           EJECUCIÓN DEL SERVIDOR
# -------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)