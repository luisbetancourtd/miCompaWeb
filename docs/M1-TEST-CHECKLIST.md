# Checklist de Pruebas M1 — miCompaWeb v1.2.0

Marcar cada casilla con [x] tras confirmar que funciona en tu entorno Windows.

---

## 1. Entorno & Instalacion

- [ ] Python 3.12 instalado (`python --version` dice 3.12.x, NO 3.14)
- [ ] venv activado (prompt empieza con `(.venv) PS`)
- [ ] `pip install -e .` completo sin errores de compilacion
- [ ] `micompaweb doctor` muestra todos los checks OK (o skip de opcionales)
- [ ] Encoding UTF-8 configurado (`$env:PYTHONIOENCODING="utf-8"; chcp 65001`)

---

## 2. Modo Fixture (sin API keys, datos de prueba)

- [ ] `micompaweb m1 --fixture -n roofin -l "Atlanta" -m 10` completa sin crash
- [ ] Pipeline muestra progress bar con los 7 stages
- [ ] ClosingScreen muestra leads > 0, ultra_hot/hot/warm correctos
- [ ] **HTML export**: abre `projects/.../exports/..._report.html` y muestra conteos reales (no 0)
- [ ] **CSV export** desde closing menu: genera archivo sin error `coroutine object...`
- [ ] **JSON export** desde closing menu: genera archivo sin error
- [ ] Closing menu permite navegar entre opciones y "Salir" termina limpio
- [ ] `projects/` contiene carpeta del proyecto con `leads.json`, `scores.json`, `cache.db`

---

## 3. Wizard Interactivo

- [ ] `micompaweb m1 --wizard` inicia sin error (`int object has no attribute get` resuelto)
- [ ] Wizard muestra lista de nichos con autocomplete fuzzy
- [ ] Autocorreccion de ciudad funciona (ej: "cdmx" → "Ciudad de México")
- [ ] Seleccion de idioma (es/en/fr) funciona
- [ ] Seleccion de profundidad (rapida/estandar/exhaustiva) funciona
- [ ] Seleccion de max leads (5/10/20/50/100) funciona
- [ ] Pipeline ejecuta tras confirmar configuracion

---

## 4. M1 con Datos Reales (requiere GOOGLE_PLACES_API_KEY)

- [ ] `.env` contiene `GOOGLE_PLACES_API_KEY=AIza...` (key valida)
- [ ] `micompaweb m1 -n plomeros -l "Miami" -m 5` completa sin `400 Bad Request`
- [ ] Leads tienen datos reales: nombre, direccion, rating, review_count
- [ ] `website_status` detecta correctamente: sin web / sin SSL / web OK
- [ ] `review_count` y `rating` se muestran en export HTML/CSV
- [ ] Cost tracking muestra estimacion antes de ejecutar
- [ ] `doctor` reporta "Google Places API" como OK

---

## 5. Exportacion & Persistencia

- [ ] `micompaweb export SLUG --format html` genera `informe.html`
- [ ] `micompaweb export SLUG --format csv` genera `leads.csv`
- [ ] `micompaweb export SLUG --format json` genera `leads.json`
- [ ] `micompaweb m1 --list` muestra tabla de proyectos completados
- [ ] `micompaweb m1 --resume SLUG` muestra resumen del proyecto

---

## 6. Email Outreach

- [ ] Desde closing menu "Generar email borrador (top lead)" genera email personalizado
- [ ] Con nicho `plomeros` → usa template de plomeros (no generico)
- [ ] Con nicho `electricistas` → usa template de electricistas
- [ ] Email incluye pain points detectados (signals)
- [ ] Archivo `.txt` se guarda en `projects/.../emails/`
- [ ] Email batch genera 1 archivo por lead HOT+

---

## 7. Edge Cases & Errores

- [ ] Cancelar con Ctrl+C durante pipeline: no deja lock ni db corrupta
- [ ] Sin internet / offline: `micompaweb m1 --offline` usa solo cache
- [ ] Sin API key: `micompaweb m1` sin `--fixture` muestra advertencia clara
- [ ] Nicho invalido: wizard muestra error amigable
- [ ] Ubicacion vacia: wizard re-pregunta

---

## 8. Performance

- [ ] Fixture con 10 leads: < 30 segundos
- [ ] Fixture con 50 leads: < 2 minutos
- [ ] Google Places con 10 leads: < 2 minutos
- [ ] No hay memory leak evidente (RAM estable)

---

## Sign-off

| Tester | Fecha | Resultado |
|--------|-------|-----------|
|        |       |           |

**Criterio de exito:** Todas las casillas marcadas [x] = M1 v1.2.0 listo para produccion.

**Si algo falla:**
1. Copiar el comando exacto que fallo
2. Copiar el traceback completo
3. Decir si es en PowerShell Windows o WSL
4. Adjuntar si usas `--fixture` o API key real
