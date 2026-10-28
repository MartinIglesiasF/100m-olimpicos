# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 09:28:30 2026

@author: Martín
"""

"""
02_analisis_100m.py
Congela el CSV de los 100 m y hace el análisis: evolución del ganador,
efecto del cronometraje, dispersión de los finalistas (idea de Gould) y ajuste
de una curva de tendencia.



"""

# %% ---------------------------------------------------------------
# 0. IMPORTS Y CONFIGURACIÓN
# ------------------------------------------------------------------
from pathlib import Path             # rutas de archivos

import numpy as np                   # cálculo numérico
import pandas as pd                  # tablas de datos
import matplotlib.pyplot as plt      # gráficos
from scipy.optimize import curve_fit # ajuste de curvas por mínimos cuadrados

# Carpeta del proyecto (la misma donde está el CSV del otro script)
RAIZ = Path(__file__).resolve().parent.parent   # sube de src/ a la raíz del proyecto
DATA_DIR = RAIZ / "data" / "processed"
FIG_DIR = RAIZ / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

CSV_ORIGINAL = DATA_DIR / "100m_finales.csv"
CSV_LIMPIO = DATA_DIR / "100m_finales_clean.csv"

# %% ---------------------------------------------------------------
# 1. Congelamos los datos.
# ------------------------------------------------------------------
# Si algún día vuelves a descargar datos, el análisis no cambia sin que tú lo decidas.
if CSV_LIMPIO.exists():
    print("Ya existe el CSV limpio: no se sobrescribe. Bórralo a mano si quieres rehacerlo.")
else:
    df0 = pd.read_csv(CSV_ORIGINAL)                       # leemos el CSV original

    # --- Comprobaciones: solo avisan, no paran el programa ---
    print("Ediciones:", df0["year"].nunique(), "(esperadas: 30)")
    print("Filas duplicadas (mismo año y atleta):",
          df0.duplicated(subset=["year", "athlete"]).sum())
    raros = df0[(df0["time_s"] < 9.5) | (df0["time_s"] > 13)]    # tiempos imposibles
    print("Tiempos fuera de 9.5-13 s:", len(raros))
    print(df0.groupby("year").size().to_string())          # finalistas por edición

    # Quitamos la columna 'wind' si está vacía (no aporta nada todavía)
    if df0["wind"].isna().all():
        df0 = df0.drop(columns="wind")

    df0.to_csv(CSV_LIMPIO, index=False)                    # guardamos la copia congelada
    print("CSV limpio guardado en:", CSV_LIMPIO)


# %% ---------------------------------------------------------------
# 2. CARGAR LOS DATOS CONGELADOS
# ------------------------------------------------------------------
df = pd.read_csv(CSV_LIMPIO)

# Los Juegos "de 2020" se celebraron en 2021: usamos el año REAL en los gráficos
df["year_real"] = df["year"].replace({2020: 2021})

print(df.head())                                           # vistazo rápido


# %% ---------------------------------------------------------------
# 3. GRÁFICO 1: TIEMPO DEL GANADOR POR AÑO (manual vs eléctrico)
# ------------------------------------------------------------------
# El ganador es el más rápido de cada final, así que usamos el mínimo por año.
# Hacemos dos series SEPARADAS para no mezclar tecnologías de cronometraje.
ganador_hand = df.groupby("year_real")["time_hand"].min().dropna()
ganador_auto = df.groupby("year_real")["time_auto"].min().dropna()

plt.figure(figsize=(9, 5))
plt.plot(ganador_hand.index, ganador_hand.values, "o-", label="Cronometraje manual")
plt.plot(ganador_auto.index, ganador_auto.values, "s-", label="Cronometraje eléctrico")
plt.xlabel("Año")
plt.ylabel("Tiempo del ganador (s)")
plt.title("100 m masculinos: tiempo del ganador en los Juegos Olímpicos")
plt.legend()
plt.grid(alpha=0.3)
plt.savefig(FIG_DIR / "01_ganador.png", dpi=150, bbox_inches="tight")  # lo guardamos
plt.show()


# %% ---------------------------------------------------------------
# 4. GRÁFICO 2: TODOS LOS FINALISTAS POR AÑO
# ------------------------------------------------------------------
plt.figure(figsize=(9, 5))
for tipo, grupo in df.groupby("timing_type"):              # un color por tipo de cronometraje
    plt.scatter(grupo["year_real"], grupo["time_s"], s=18, alpha=0.7, label=tipo)
plt.xlabel("Año")
plt.ylabel("Tiempo (s)")
plt.title("Todos los finalistas de los 100 m")
plt.legend()
plt.grid(alpha=0.3)
plt.savefig(FIG_DIR / "02_finalistas.png", dpi=150, bbox_inches="tight")
plt.show()


# %% ---------------------------------------------------------------
# 5. GRÁFICO 3: ¿CUÁNTO "REGALABA" EL CRONOMETRAJE MANUAL?
# ------------------------------------------------------------------
# Solo en filas que tienen LOS DOS tiempos: manual - eléctrico.
# Ojo: el manual se redondea a décimas, así que cada valor es ruidoso.
ambos = df.dropna(subset=["time_hand", "time_auto"]).copy()
ambos["dif"] = ambos["time_hand"] - ambos["time_auto"]

if ambos.empty:
    print("No hay filas con ambos tiempos.")
else:
    dif_por_año = ambos.groupby("year_real")["dif"].mean()  # media por edición
    plt.figure(figsize=(9, 4))
    plt.bar(dif_por_año.index.astype(str), dif_por_año.values)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xlabel("Año")
    plt.ylabel("Manual - eléctrico (s)")
    plt.title("Diferencia media entre cronometraje manual y eléctrico")
    plt.xticks(rotation=60)
    plt.savefig(FIG_DIR / "03_dif_cronometraje.png", dpi=150, bbox_inches="tight")
    plt.show()
    print(dif_por_año.round(3))


# %% ---------------------------------------------------------------
# 6. IDEA DE GOULD: ¿SE HOMOGENEIZA LA ÉLITE?
# ------------------------------------------------------------------
# Para comparar ediciones justas usamos SIEMPRE los 6 primeros de cada final
# (hay finales con 6, 7 y 8 corredores) y solo tiempos eléctricos.
top6 = df[(df["position"] <= 6) & df["time_auto"].notna()]
g = top6.groupby("year_real")["time_auto"].agg(["std", "min", "max", "count"])
g = g[g["count"] == 6].copy()                # solo ediciones con los 6 tiempos completos
g["rango"] = g["max"] - g["min"]             # distancia entre el 1.º y el 6.º

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(g.index, g["std"], "o-", label="Desviación típica")
ax.plot(g.index, g["rango"], "s-", label="Rango (1.º a 6.º)")
ax.set_xlabel("Año")
ax.set_ylabel("Dispersión de los 6 primeros (s)")
ax.set_title("¿Se parecen cada vez más los mejores velocistas?")
ax.legend()
ax.grid(alpha=0.3)
fig.savefig(FIG_DIR / "04_dispersion.png", dpi=150, bbox_inches="tight")
plt.show()
print(g.round(3))


# %% ---------------------------------------------------------------
# 7. ¿HAY UN LÍMITE? AJUSTE EXPONENCIAL DEL TIEMPO DEL GANADOR
# ------------------------------------------------------------------
# Modelo: t(año) = a * exp(-b * (año - 1932)) + c
#   c = asíntota (el "límite" al que tendería el tiempo)
w = ganador_auto[ganador_auto.index >= 1932]               # serie eléctrica del ganador
x = w.index.values.astype(float)
y = w.values


def modelo(x, a, b, c):
    """Exponencial decreciente hacia una asíntota c."""
    return a * np.exp(-b * (x - 1932)) + c


try:
    # p0 = valores iniciales; bounds = límites razonables para que el ajuste converja
    params, cov = curve_fit(modelo, x, y, p0=[1.0, 0.02, 9.5],
                            bounds=([0, 0, 8.0], [10, 1, 10.0]))
    errores = np.sqrt(np.diag(cov))                        # incertidumbres (1 sigma)
    print(f"a = {params[0]:.3f} ± {errores[0]:.3f}")
    print(f"b = {params[1]:.4f} ± {errores[1]:.4f}")
    print(f"Asíntota c = {params[2]:.3f} ± {errores[2]:.3f} s")

    xx = np.linspace(x.min(), 2060, 300)                   # años para dibujar la curva
    plt.figure(figsize=(9, 5))
    plt.plot(x, y, "o", label="Ganador (eléctrico)")
    plt.plot(xx, modelo(xx, *params), "-", label="Ajuste exponencial")
    #plt.axhline(params[2], linestyle="--", color="gray", label="Asíntota")
    plt.xlabel("Año")
    plt.ylabel("Tiempo del ganador (s)")
    plt.title("¿Hacia dónde tiende el 100 m?")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig(FIG_DIR / "05_ajuste.png", dpi=150, bbox_inches="tight")
    plt.show()
except RuntimeError as e:
    print("El ajuste no convergió:", e)
    
#%%
# Mediana de los 6 primeros por edición (menos sensible a un outlier que el mínimo)
mediana = top6.groupby("year_real")["time_auto"].median()
print(mediana.loc[1996:])

# Ajuste de la celda 7 repetido SIN 2008 y 2012, para ver cuánto cambia la asíntota
w_sin = w.drop([2008, 2012], errors="ignore")
x2, y2 = w_sin.index.values.astype(float), w_sin.values
params2, cov2 = curve_fit(modelo, x2, y2, p0=[1.0, 0.02, 9.5],
                          bounds=([0, 0, 8.0], [10, 1, 10.0]))
print("Asíntota sin Bolt:", params2[2], "±", np.sqrt(np.diag(cov2))[2])


# %% ---------------------------------------------------------------
# 8. NIVEL MEDIO DE LA FINAL (no solo el ganador)
# ------------------------------------------------------------------
# Los 6 primeros de cada final, solo con tiempos eléctricos y ediciones completas
top6 = df[(df["position"] <= 6) & df["time_auto"].notna()]
completas = top6.groupby("year_real")["time_auto"].count() == 6
top6 = top6[top6["year_real"].isin(completas[completas].index)]

media = top6.groupby("year_real")["time_auto"].mean()        # media de los 6 primeros
mediana = top6.groupby("year_real")["time_auto"].median()    # mediana (menos sensible a extremos)
# Media del resto de la final SIN el ganador (posiciones 2 a 6):
# así el efecto de un fuera de serie como Bolt no pesa en el resultado
sin_ganador = top6[top6["position"] >= 2].groupby("year_real")["time_auto"].mean()

plt.figure(figsize=(9, 5))
plt.plot(media.index, media.values, "o-", label="Media de los 6 primeros")
plt.plot(mediana.index, mediana.values, "s--", label="Mediana de los 6 primeros")
plt.plot(sin_ganador.index, sin_ganador.values, "^:", label="Media sin el ganador (2.º-6.º)")
plt.xlabel("Año")
plt.ylabel("Tiempo (s)")
plt.title("Nivel medio de la final de 100 m")
plt.legend()
plt.grid(alpha=0.3)
plt.savefig(FIG_DIR / "06_nivel_medio.png", dpi=150, bbox_inches="tight")
plt.show()

print(pd.DataFrame({"media": media, "mediana": mediana, "sin_ganador": sin_ganador}).round(3))

#%%
ultimo_2024 = df[df["year"] == 2024]["time_s"].max()          # tiempo del último finalista con registro
ganadores = df.groupby("year")["time_s"].min().drop(2024)     # ganador de cada edición anterior
print(ultimo_2024, (ganadores > ultimo_2024).sum(), "de", len(ganadores), "ediciones")