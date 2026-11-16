# AMIAUIA

**Análisis Multivariable Inteligente Aplicado a la Unificación de Imagen y Archivos**

AMIAUIA es una IA estadística y explicable que analiza tus archivos y fotografías y te devuelve **soluciones lógicas**. Cada respuesta tiene siempre la misma estructura:

| | |
|---|---|
| **Hallazgo** | Qué ha detectado |
| **Evidencia** | Los números que lo demuestran |
| **Confianza** | Lo seguro que está (0–100 %) |
| **Acción** | Qué hacer a continuación |

Todo el análisis se hace **en tu ordenador**: no se sube ningún archivo y AMIAUIA **nunca borra ni mueve nada** por su cuenta.

---

## Qué hace

### 🗂️ Módulo Archivos (informática)
- **Duplicados exactos** en tres pasos (tamaño → hash parcial → SHA-256 completo) y espacio recuperable.
- **Reparto del espacio** por tipo de archivo.
- **Archivos olvidados**: los más grandes (percentil 90) sin modificar desde hace más de un año.
- **Alerta temprana de ransomware**: archivos de texto modificados en las últimas 24 h cuya entropía de Shannon supera 7,5 bits/byte (aspecto de cifrado) y extensiones típicas de secuestro (`.locked`, `.encrypted`…).
- **Predicción de capacidad**: regresión lineal sobre mediciones diarias del disco para estimar cuándo se llenará, con un intervalo.

### 📷 Módulo Fotos
- **Selección automática (culling)**: puntúa cada foto por nitidez (varianza del laplaciano), exposición y luces quemadas, en relación con el resto de la sesión (z-score robusto).
- **Ráfagas**: agrupa fotos casi iguales mediante hash perceptual (dHash) y hora de la cámara, y se queda con la mejor de cada grupo.
- **Auditoría técnica de tus hábitos** a partir del EXIF, con contraste estadístico de dos proporciones (p < 0,05):
  - ¿Fallas más el foco a f/2 o más abierto?
  - ¿Por debajo de la velocidad 1/focal?
  - ¿Con ISO 3200 o más?
  - ¿Con un objetivo concreto?

Ejemplo de resultado:

```
🟠 [MEDIA] [fotos] Con el objetivo 85mm F1.4: 31 % de fotos desenfocadas frente a 9 % en el resto
   Confianza: 99%
   · fotos_condicion: 412
   · intervalo95_condicion: [26.8, 35.6]
   · p_valor: 0.0001
   → Acción: Calibra el microajuste de enfoque de este objetivo o revisa su estado.
```

---

## Instalación

Requiere Python 3.10 o superior.

```bash
git clone https://github.com/TU_USUARIO/amiauia.git
cd amiauia
pip install -e .
```

## Uso

```bash
# Archivos: duplicados, espacio, olvidados y ransomware
amiauia archivos /ruta/a/tu/disco

# Fotos: selección, ráfagas, exposición y auditoría EXIF
amiauia fotos /ruta/a/la/sesion --seleccion elegidas.txt

# Capacidad: ejecútalo a diario (por ejemplo con cron o el Programador de tareas)
amiauia capacidad /

# Todo a la vez, con informes
amiauia todo /ruta --json informe.json --md informe.md
```

Opciones comunes: `--json FICHERO`, `--md FICHERO`, `--ocultos` (incluye archivos ocultos).

> En esta versión el módulo de fotos analiza JPEG, PNG, TIFF, WebP y BMP. Los RAW se cuentan como archivos, pero no se analizan todavía (ver hoja de ruta).

---

## Arquitectura

```
amiauia/
├── scanner.py         # Ingesta: recorre carpetas, hashes, entropía
├── stats.py           # Motor estadístico propio (z robusto, regresión, Wilson, test de proporciones, entropía)
├── files_analysis.py  # Módulo Archivos
├── capacity.py        # Predicción de capacidad
├── photo_analysis.py  # Módulo Fotos
├── findings.py        # Estructura Hallazgo / Evidencia / Confianza / Acción
├── report.py          # Salida en consola, JSON y Markdown
└── cli.py             # Línea de comandos
```

El motor estadístico está escrito desde cero con la biblioteca estándar de Python; solo se usan `numpy` y `Pillow` para leer y procesar imágenes.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

GitHub Actions ejecuta los tests en Linux, Windows y macOS en cada *push*.

---

## Hoja de ruta

- [ ] Lectura de RAW (vista previa embebida) y HEIC
- [ ] Detección de ojos cerrados y caras
- [ ] Duplicados visuales entre discos (no solo exactos)
- [ ] Comparación de origen y copia de seguridad
- [ ] Vigilancia en tiempo real para ransomware
- [ ] Explicaciones en lenguaje natural con un modelo local
- [ ] Interfaz de escritorio y plugin para Lightroom
- [ ] API para integradores

## Licencia

MIT. Consulta [LICENSE](LICENSE).
