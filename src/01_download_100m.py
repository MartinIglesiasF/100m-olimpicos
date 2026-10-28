# -*- coding: utf-8 -*-
"""
Created on Sat Oct 10 17:27:21 2026

@author: Martín
"""

"""
01_download_100m.py
Descarga las finales de 100 m lisos masculinos desde Olympedia y genera
data/processed/100m_finales.csv.

Desarrollado con ayuda de un asistente de IA (Claude), como parte de mi
aprendizaje en carga y limpieza de datos. Mantengo los comentarios
explicativos línea a línea como material de estudio.

Requisitos: pip install -r requirements.txt
"""

# ---------------------------------------------------------------
# 1. IMPORTS
# ---------------------------------------------------------------
import re                      # expresiones regulares (para limpiar los tiempos)
import time                    # hacer pausas entre peticiones al servidor
from io import StringIO        # permitir que pandas lea texto como si fuera un archivo
from pathlib import Path       # manejo de rutas de carpetas/archivos de forma limpia

import pandas as pd            # librería principal de análisis de datos
import requests                # descargar páginas web


# ---------------------------------------------------------------
# 2. CONFIGURACIÓN
# ---------------------------------------------------------------

RAIZ = Path(__file__).resolve().parent.parent
RAW_DIR = RAIZ / "data" / "raw"
PROCESSED_DIR = RAIZ / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)         # crea la carpeta si no existe
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)   # idem Diccionario {año: URL de la página de resultados de los 100 m masculinos}.
URLS = {
    1896: "https://www.olympedia.org/results/56000",
    1900: "https://www.olympedia.org/results/56034",
    1904: "https://www.olympedia.org/results/56117",
    1908: "https://www.olympedia.org/results/56265",
    1912: "https://www.olympedia.org/results/56530",
    1920: "https://www.olympedia.org/results/57032",
    1924: "https://www.olympedia.org/results/57285",
    1928: "https://www.olympedia.org/results/57590",
    1932: "https://www.olympedia.org/results/57919",
    1936: "https://www.olympedia.org/results/58143",
    1948: "https://www.olympedia.org/results/58482",
    1952: "https://www.olympedia.org/results/58826",
    1956: "https://www.olympedia.org/results/59241",
    1960: "https://www.olympedia.org/results/59618",
    1964: "https://www.olympedia.org/results/60072",
    1968: "https://www.olympedia.org/results/60512",
    1972: "https://www.olympedia.org/results/61005",
    1976: "https://www.olympedia.org/results/61607",
    1980: "https://www.olympedia.org/results/62161",
    1984: "https://www.olympedia.org/results/62625",
    1988: "https://www.olympedia.org/results/63261",
    1992: "https://www.olympedia.org/results/63952",
    1996: "https://www.olympedia.org/results/64629",
    2000: "https://www.olympedia.org/results/65310",
    2004: "https://www.olympedia.org/results/66009",
    2008: "https://www.olympedia.org/results/257142",
    2012: "https://www.olympedia.org/results/302122",
    2016: "https://www.olympedia.org/results/358560",
    2020: "https://www.olympedia.org/results/19000360",
    2024: "https://www.olympedia.org/results/2013500",
}

# Algunas webs bloquean peticiones "anónimas"; nos identificamos con un User-Agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (proyecto personal de analisis de datos)"}

PAUSA_SEGUNDOS = 2   # espera entre descargas para no saturar el servidor
N_FINALISTAS = 8     # nos quedamos con los 8 primeros de cada final


# ---------------------------------------------------------------
# 3. FUNCIÓN DE DESCARGA
# ---------------------------------------------------------------


def descargar_html(year: int, url: str) -> str:
    """Descarga la página de un año. Si ya está guardada, la reutiliza."""
    ruta = RAW_DIR / f"100m_{year}.html"          # dónde guardaremos este HTML

    if ruta.exists():                              # si ya lo descargamos antes
        return ruta.read_text(encoding="utf-8")    # lo leemos del disco

    respuesta = requests.get(url, headers=HEADERS, timeout=30)  # pedimos la página
    respuesta.raise_for_status()                                # si hay error (404, 500...), para aquí
    ruta.write_text(respuesta.text, encoding="utf-8")           # guardamos el HTML original
    time.sleep(PAUSA_SEGUNDOS)                                  # pausa de cortesía con el servidor
    return respuesta.text                                       # devolvemos el HTML


# ---------------------------------------------------------------
# 4. FUNCIÓN PARA LIMPIAR EL TIEMPO
# ---------------------------------------------------------------


def limpiar_tiempo(valor) -> float:
    """Convierte textos como '9.58', '10.3 (e)' o 'DQ' en un número (o NaN)."""
    if pd.isna(valor):                             # si está vacío, devuelve NaN
        return float("nan")
    # En las primeras ediciones los no ganadores figuran como 'at 2 metres' (distancia
    # al ganador, no un tiempo): no es un dato válido, lo dejamos como NaN.
    if str(valor).strip().lower().startswith("at "):
        return float("nan")
    # Busca el primer número con decimales dentro del texto (p.ej. 10.3 de '10.3 (e)')
    coincidencia = re.search(r"\d+\.\d+|\d+", str(valor))
    return float(coincidencia.group()) if coincidencia else float("nan")


# ---------------------------------------------------------------
# 5. FUNCIÓN QUE EXTRAE LA FINAL DE UNA PÁGINA
# ---------------------------------------------------------------


def extraer_final(html: str, year: int) -> pd.DataFrame:
    """Lee las tablas del HTML y devuelve un DataFrame con los finalistas."""
    # read_html devuelve una LISTA con todas las tablas que encuentra en la página
    tablas = pd.read_html(StringIO(html))

    # En Olympedia la página tiene: (1) una tabla resumen con todos los participantes
    # (columna 'Final', sin tiempos), (2) las tablas de series/semis, y (3) al final
    # la tabla de la final. Las de rondas tienen la columna 'Competitor' y alguna
    # columna que EMPIEZA por 'Time'. Ojo: según la época puede ser 'Time' (una sola)
    # o 'Time (Hand)' + 'Time (Automatic)' (cronometraje manual y eléctrico a la vez).
    def tiene_tiempo(t):
        return any(str(c).startswith("Time") for c in t.columns)

    tablas_resultados = [t for t in tablas if "Competitor" in t.columns and tiene_tiempo(t)]
    if not tablas_resultados:
        raise ValueError(f"No se encontró tabla de resultados en {year}")

    # Las rondas van en orden cronológico, así que la ÚLTIMA tabla es la final.
    # (Compruébalo a mano con algunos años, sobre todo los de formatos raros.)
    final = tablas_resultados[-1].copy()

    # Renombramos a nombres en minúsculas
    final = final.rename(columns={"Pos": "position", "Competitor": "athlete",
                                  "NOC": "country"})

    # 'position' puede traer '=3' (empate) o 'DQ': quitamos el '=' y convertimos
    # a número; lo que no sea número (DQ, DNS...) queda como NaN y se descarta luego.
    final["position"] = pd.to_numeric(
        final["position"].astype(str).str.replace("=", "", regex=False),
        errors="coerce")

    # --- Tiempos ---------------------------------------------------------
    # Creamos columnas numéricas (en segundos) según lo que haya en esa edición.
    nan = pd.Series(float("nan"), index=final.index)    # columna vacía de reserva
    if "Time (Hand)" in final.columns:                  # cronometraje manual
        final["time_hand"] = final["Time (Hand)"].apply(limpiar_tiempo)
    else:
        final["time_hand"] = nan
    if "Time (Automatic)" in final.columns:             # cronometraje eléctrico
        final["time_auto"] = final["Time (Automatic)"].apply(limpiar_tiempo)
    else:
        final["time_auto"] = nan
    if "Time" in final.columns:                         # una sola columna de tiempo
        tiempo_unico = final["Time"].apply(limpiar_tiempo)
        # Regla simple: antes de 1932 todo era manual; después, eléctrico.
        # (Compruébalo con las ediciones intermedias.)
        if year < 1932:
            final["time_hand"] = tiempo_unico
        else:
            final["time_auto"] = tiempo_unico

    # time_s = tiempo eléctrico si existe; si no, el manual. Anotamos cuál se usó.
    final["time_s"] = final["time_auto"].fillna(final["time_hand"])
    final["timing_type"] = final["time_auto"].notna().map(
        {True: "automatico", False: "manual"})

    # Nos quedamos solo con las columnas finales que nos interesan
    final = final[["position", "athlete", "country",
                   "time_hand", "time_auto", "time_s", "timing_type"]].copy()

    final["year"] = year                           # añadimos el año de la edición

    # Nos quedamos solo con los N primeros clasificados con posición válida
    final = final.dropna(subset=["position"]).sort_values("position").head(N_FINALISTAS)
    return final


# ---------------------------------------------------------------
# 6. PROGRAMA PRINCIPAL
# ---------------------------------------------------------------
def main():
    if not URLS:
        print("El diccionario URLS está vacío. Rellénalo con las URLs de Olympedia.")
        return

    todas = []                                     # aquí iremos juntando cada año

    for year, url in sorted(URLS.items()):         # recorremos los años en orden
        print(f"Procesando {year}...")
        try:
            html = descargar_html(year, url)       # descargamos (o leemos de disco)
            todas.append(extraer_final(html, year))  # extraemos y guardamos la tabla
        except Exception as e:                     # si falla un año, seguimos con el resto
            print(f"  ⚠ Error en {year}: {e}")

    if not todas:
        print("No se ha podido extraer ningún dato.")
        return

    df = pd.concat(todas, ignore_index=True)       # unimos todas las tablas en una sola

    # Columnas que rellenarás a mano o con otra lógica más adelante:
    df["wind"] = pd.NA                             # viento (m/s), suele estar fuera de la tabla
    # (timing_type ya viene calculado por fila en extraer_final)

    ruta_csv = PROCESSED_DIR / "100m_finales.csv"
    df.to_csv(ruta_csv, index=False)               # guardamos el CSV limpio
    print(f"Listo: {len(df)} filas guardadas en {ruta_csv}")
    print(df.head(10))                             # vistazo rápido para comprobar


# Esto hace que main() solo se ejecute si lanzas el archivo directamente
if __name__ == "__main__":
    main()