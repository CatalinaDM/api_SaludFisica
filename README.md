#  Wellness App

Aplicación web de bienestar desarrollada con **Flask** y **Python**, creada por **Mirza y Catalina**. Integra múltiples APIs externas para ofrecer frases motivacionales, una biblioteca de ejercicios, consulta nutricional y un tracker de hábitos diarios, todo en español.

---

## 📁 Estructura del Proyecto

```
SALUD_API/
├── env/                        # Entorno virtual de Python
├── static/
│   └── css/
│       └── style.css           # Estilos personalizados
├── templates/
│   ├── base.html               # Plantilla base (navbar, footer, scripts)
│   ├── index.html              # Página principal con frase del día
│   ├── ejercicios.html         # Biblioteca de ejercicios con GIFs
│   ├── nutricion.html          # Consulta nutricional estilo FDA
│   ├── bienestar.html          # Tracker de hábitos diarios
│   └── frases.html             # Frases motivacionales
└── app.py                      # Servidor Flask y lógica principal
└── .env                        #Archivo donde se guardaran las llaves privadas de las apis
└── .gitignore                  #Ignorar el archivo .env para evitar fuga de información
```

---

# Documentación Técnica — Wellness App

---

## Rutas y Funcionalidades

---

### Inicio (`/`)

**Archivo:** `app.py` — función `index()`
**Método HTTP:** GET

Cuando el usuario entra a la página principal, Flask hace una petición GET a la API de ZenQuotes (`https://zenquotes.io/api/random`). Esta API devuelve un JSON con dos campos: `q` (la frase) y `a` (el autor). La frase se extrae y se pasa por la función `traducir_en_lote()` antes de enviarse al template.

El template `index.html` recibe las variables `frase` y `autor` y las renderiza dentro del carrusel de Bootstrap. Si la API falla (por timeout o error de red), se muestra un mensaje de fallback en lugar de romper la aplicación.

```python
@app.route("/")
def index():
    try:
        response   = requests.get("https://zenquotes.io/api/random", timeout=5)
        frase_data = response.json()[0]
        frase      = traducir_en_lote([frase_data["q"]])[0]
        autor      = frase_data["a"]
    except Exception:
        frase = "No se pudo obtener una frase."
        autor = "Error"
    return render_template("index.html", frase=frase, autor=autor)
```

---

### Frases (`/frases`)

**Archivo:** `app.py` — función `frases()`
**Método HTTP:** GET

Funciona igual que el índice pero en su propia página dedicada. Cada vez que el usuario recarga o hace clic en "Otra frase", Flask ejecuta una nueva petición a ZenQuotes y devuelve una frase diferente. No hay caché ni estado guardado entre peticiones — cada visita es independiente.

---

### Ejercicios (`/ejercicios`)

**Archivo:** `app.py` — función `ejercicios()`
**Método HTTP:** GET
**Parámetro de URL:** `bodyPart` (opcional, default: `"all"`)

Esta es la ruta más compleja del proyecto. Funciona así:

**1. Filtrado por grupo muscular**

El usuario selecciona un grupo muscular en los botones del template. Eso genera una URL como `/ejercicios?bodyPart=chest`. Flask lee ese parámetro con `request.args.get("bodyPart", "all")` y construye la URL de la API según corresponda:

```python
if body_part == "all":
    url = "https://exercisedb.p.rapidapi.com/exercises?limit=30&offset=0"
else:
    url = f"https://exercisedb.p.rapidapi.com/exercises/bodyPart/{body_part}?limit=30&offset=0"
```

La API de ExerciseDB requiere autenticación mediante headers de RapidAPI:

```python
EXERCISEDB_HEADERS = {
    "X-RapidAPI-Key":  RAPIDAPI_KEY,
    "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
}
```

**2. Traducción en lote**

La API devuelve todos los textos en inglés. En lugar de traducir cada ejercicio uno por uno (lo que generaría 180+ peticiones HTTP y tardaría hasta 60 segundos), se usa una estrategia de traducción en lote:

- Se recolectan todas las descripciones en una lista plana.
- Se recolectan todos los pasos de instrucciones en otra lista plana, guardando cuántos pasos tiene cada ejercicio en `instrucciones_lens`.
- Se hace UNA SOLA llamada a Google Translate con todos los textos unidos por el separador `" ||| "`.
- Se divide el resultado por ese separador y se reasigna cada fragmento a su ejercicio original.

```python
# Une todos los textos con un separador único
bloque    = " ||| ".join(textos)
traducido = GoogleTranslator(source="en", target="es").translate(bloque)
partes    = traducido.split(" ||| ")
```

Esto reduce el tiempo de traducción de ~60 segundos a ~1-2 segundos.

**3. Imágenes (GIFs)**

La API gratuita de ExerciseDB no siempre devuelve el campo `gifUrl`. Si está vacío, se construye una URL de fallback apuntando al repositorio público de GitHub `yuhonas/free-exercise-db`:

```python
if not e.get("gifUrl"):
    nombre_carpeta = e["name"].replace(" ", "_").title()
    e["gifUrl"] = f"https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/{nombre_carpeta}/0.jpg"
```

Si esa imagen tampoco carga, el template tiene un `onerror` en el tag `<img>` que muestra un placeholder gris en su lugar.

---

### Nutricion (`/nutricion`)

**Archivo:** `app.py` — función `nutricion()`
**Métodos HTTP:** GET y POST

En GET simplemente renderiza el formulario vacío. Cuando el usuario escribe un alimento y hace clic en buscar, el formulario hace POST con el campo `alimento`.

Flask toma ese valor y llama a la API de Edamam:

```python
url = (f"https://api.edamam.com/api/nutrition-data"
       f"?app_id={APP_ID}&app_key={APP_KEY}&ingr=1%20{alimento}")
```

El `1%20` al inicio es `1 ` (un espacio codificado para URL) — Edamam requiere que la consulta incluya una cantidad, por eso el formulario pide escribir en formato como `1 cup rice` o `100g chicken`.

La API devuelve un JSON con estructura anidada. Los nutrientes están dentro de `ingredients[0]["parsed"][0]["nutrients"]` y se pasan directamente al template como diccionario. Cada clave es un código nutricional estándar (por ejemplo `ENERC_KCAL` para calorías, `PROCNT` para proteína) y el template accede a `.quantity` de cada uno para mostrar el valor.

---

### Bienestar (`/bienestar`)

**Archivo:** `app.py` — función `bienestar()`
**Métodos HTTP:** GET y POST

En GET muestra el formulario. Al hacer POST, Flask recibe los tres campos del formulario: `agua`, `horas` y `estado`. En la versión actual, los datos no se persisten en base de datos — simplemente se muestra un mensaje de confirmación en pantalla.

Si se quisiera guardar el historial, el siguiente paso sería integrar SQLite con `flask-sqlalchemy` y crear un modelo `RegistroDiario` con esos tres campos más un timestamp.

---

## Función auxiliar: `traducir_en_lote()`

Esta función es transversal a toda la app y merece explicación aparte.

```python
_SEP = " ||| "

def traducir_en_lote(textos):
    if not TRADUCTOR_DISPONIBLE or not textos:
        return textos
    try:
        bloque    = _SEP.join(textos)
        traducido = GoogleTranslator(source="en", target="es").translate(bloque)
        partes    = traducido.split(_SEP)
        if len(partes) != len(textos):
            return textos          # fallback si Google alteró el separador
        return [p.strip() for p in partes]
    except Exception as e:
        print(f"Error al traducir: {e}")
        return textos
```

El separador `" ||| "` fue elegido porque es poco probable que aparezca en texto natural en inglés. Si Google Translate lo modifica o elimina al traducir, el `len(partes) != len(textos)` lo detecta y devuelve los textos originales sin crashear.

Si `deep-translator` no está instalado, `TRADUCTOR_DISPONIBLE` es `False` y la función simplemente devuelve el texto en inglés sin intentar traducir.

---

## Variables de entorno

Las claves de API deben guardarse en un archivo `.env` en la raíz del proyecto y nunca subirse a Git:

```
RAPIDAPI_KEY=tu_clave_de_rapidapi
EDAMAM_APP_ID=tu_app_id
EDAMAM_APP_KEY=tu_app_key
```

En `app.py` se cargan así:

```python
import os
from dotenv import load_dotenv
load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
APP_ID       = os.getenv("EDAMAM_APP_ID")
APP_KEY      = os.getenv("EDAMAM_APP_KEY")
```

---

## Dependencias

```
flask
requests
deep-translator
python-dotenv
```

Instalación:

```bash
pip install flask requests deep-translator python-dotenv
```

##  Tecnologías Utilizadas

| Tecnología | Uso |
|---|---|
| Python + Flask | Backend y servidor web |
| Jinja2 | Motor de plantillas HTML |
| Bootstrap 5 | Diseño responsive |
| Bootstrap Icons | Iconografía |
| AOS (Animate on Scroll) | Animaciones de entrada |
| Google Fonts (Poppins + Playfair Display) | Tipografía |
| deep-translator | Traducción EN → ES |

---

##  APIs Externas

| API | Uso | Documentación |
|---|---|---|
| ZenQuotes | Frases motivacionales | https://zenquotes.io |
| ExerciseDB (RapidAPI) | Biblioteca de ejercicios | https://rapidapi.com/justin-WFnsXH_t6/api/exercisedb |
| Edamam Nutrition | Datos nutricionales | https://developer.edamam.com |
| Google Translate (via deep-translator) | Traducción automática | https://pypi.org/project/deep-translator |

---

##  Instalación y Uso

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd SALUD_API
```

### 2. Crear y activar el entorno virtual

```bash
# Crear entorno virtual
python -m venv env

# Activar en Windows
env\Scripts\activate

# Activar en Mac/Linux
source env/bin/activate
```

### 3. Instalar dependencias

```bash
pip install flask requests deep-translator

```

### 4. Ejecutar la aplicación

```bash
python app.py
```

### 5. Abrir en el navegador

```
http://127.0.0.1:5000
```

---

##  Configuración de API Keys

Las claves de API se encuentran directamente en `app.py`. Para un entorno de producción, se recomienda moverlas a variables de entorno:


## Instala python-dotenv
bashpip install python-dotenv

importar python-detenv en app.py y después crear tu archivo .env donde pondras tus propias API Keys

---

##  Rutas de la Aplicación

| Ruta | Método | Descripción |
|---|---|---|
| `/` | GET | Página principal con frase del día |
| `/frases` | GET | Frase motivacional aleatoria |
| `/ejercicios` | GET | Biblioteca de ejercicios (filtro: `?bodyPart=back`) |
| `/nutricion` | GET / POST | Consulta nutricional por alimento |
| `/bienestar` | GET / POST | Registro de hábitos diarios |

---

##Evidencia 
<img width="1920" height="1019" alt="image" src="https://github.com/user-attachments/assets/320a4b3b-4a47-4a68-ab17-a6f8118ce05c" />
<img width="1871" height="952" alt="image" src="https://github.com/user-attachments/assets/277ca06a-c019-46ef-a775-ba7c8c25b52b" />
<img width="1920" height="947" alt="image" src="https://github.com/user-attachments/assets/b7f8f8b8-62bc-4dce-9650-3130f85050f2" />
<img width="1920" height="967" alt="image" src="https://github.com/user-attachments/assets/067613aa-3283-4c71-8eec-718a8fd41b9a" />
<img width="1920" height="1025" alt="image" src="https://github.com/user-attachments/assets/0b67d40b-8398-4fb0-9289-1691932c63af" />







##  Autoras

Desarrollado  por **Mirza Natzielly Morales Lezama y Carmen Catalina Delgado Manzano** — 2026
