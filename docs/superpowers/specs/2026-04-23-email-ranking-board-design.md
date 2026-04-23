# Email Ranking Board — Design Spec
**Date:** 2026-04-23  
**Project:** COLMEN IA — Clase de Claude Code  
**Target inbox:** claude.comercial@gmail.com

---

## Overview

Interfaz web en tiempo real que conecta con Gmail, analiza correos comerciales entrantes usando Gemini API, y muestra un ranking público ordenado por puntaje total. Diseñado para ser proyectado en clase durante un webinar (~150 asistentes, ~75 participantes enviando correos).

---

## Architecture

```
Gmail (claude.comercial@gmail.com)
        │
        │  Gmail API Push Notifications (via Google Cloud Pub/Sub webhook)
        ▼
┌─────────────────────┐
│   Flask Backend     │
│                     │
│  POST /webhook      │  ← Gmail notifica nuevo mensaje
│  GET  /api/emails   │  → devuelve ranking JSON ordenado
│  GET  /             │  → sirve el board HTML
│                     │
│  GmailService       │  → lee correo completo via Gmail API
│  GeminiService      │  → analiza y devuelve puntajes + resumen
│  SQLite DB          │  → persiste resultados
└─────────────────────┘
        │
        │  HTTP polling cada 3 segundos
        ▼
┌─────────────────────┐
│  Board HTML/CSS/JS  │
│  (servido por Flask)│
└─────────────────────┘
```

**Flujo completo:**
1. Estudiante envía correo a claude.comercial@gmail.com
2. Gmail detecta mensaje nuevo → envía notificación webhook a Flask
3. Flask recibe notificación → lee correo completo via Gmail API
4. Flask envía contenido a Gemini API con prompt estructurado
5. Gemini devuelve JSON con 4 puntajes + resumen de feedback
6. Resultado se guarda en SQLite
7. Board (abierto en el navegador del profesor) hace polling cada 3s
8. Board recibe datos actualizados → reordena ranking con animación

---

## Data Model

```sql
CREATE TABLE emails (
  id               TEXT PRIMARY KEY,   -- Gmail message ID
  remitente_nombre TEXT,               -- Display name del remitente
  remitente_email  TEXT,               -- Email del remitente
  asunto           TEXT,               -- Subject del correo
  cuerpo           TEXT,               -- Cuerpo completo (plain text)
  fecha_recibido   DATETIME,           -- Timestamp de recepción
  
  puntaje_asunto      INTEGER,         -- 1-10: ¿qué tan atractivo/intrigante?
  puntaje_persuasion  INTEGER,         -- 1-10: ¿qué tan convincente y amable?
  puntaje_contexto    INTEGER,         -- 1-10: ¿qué tan bien contextualizado?
  puntaje_propuesta   INTEGER,         -- 1-10: ¿qué tan valiosa es la oferta?
  puntaje_total       REAL,            -- promedio de los 4 (1.0-10.0)
  
  resumen_gemini   TEXT,               -- feedback de 2-3 líneas de Gemini
  analizado_en     DATETIME            -- timestamp del análisis
);
```

---

## Gemini Scoring

**Dimensiones (1-10 cada una, promedio = puntaje_total):**

| Dimensión | Qué evalúa |
|-----------|------------|
| Asunto (`puntaje_asunto`) | ¿Qué tan atractivo, intrigante y no-spam es el subject? |
| Persuasión (`puntaje_persuasion`) | ¿Qué tan convincente, amable y bien redactado está el cuerpo? |
| Contexto (`puntaje_contexto`) | ¿Aporta suficiente contexto? ¿Se entiende quién escribe y por qué? |
| Propuesta de valor (`puntaje_propuesta`) | ¿La oferta es clara, relevante e interesante? |

**Prompt a Gemini** devuelve JSON estricto:
```json
{
  "puntaje_asunto": 8,
  "puntaje_persuasion": 7,
  "puntaje_contexto": 9,
  "puntaje_propuesta": 6,
  "resumen": "El asunto es llamativo y evita parecer spam. El cuerpo está bien redactado pero la propuesta de valor podría ser más específica."
}
```

---

## UI — Board

**Header:**
- Título: "RANKING DE CORREOS COMERCIALES"
- Indicador de estado: badge verde pulsante "● EN VIVO"

**Tarjeta de correo (estado colapsado):**
- Posición en ranking (#1, #2, #3...)
- Nombre y email del remitente
- Barra de progreso visual con puntaje total (ej. 8.5/10)
- Badge de color: verde (≥8), amarillo (5-7.9), rojo (<5)

**Tarjeta expandida (al hacer clic):**
- Asunto del correo
- Cuerpo completo
- Desglose de dimensiones: Asunto 8/10 | Persuasión 7/10 | Contexto 9/10 | Propuesta 6/10
- Resumen/feedback de Gemini

**Comportamiento en vivo:**
- Polling cada 3 segundos a `/api/emails`
- Correo nuevo: animación de entrada (fade-in desde arriba)
- Reordenamiento: transición CSS suave al cambiar posiciones
- Hasta ~75 tarjetas con scroll vertical

---

## Stack Técnico

| Componente | Tecnología |
|------------|------------|
| Backend | Python + Flask |
| Base de datos | SQLite (archivo local) |
| Email | Gmail API (OAuth2) + Google Cloud Pub/Sub |
| Análisis | Gemini API (gemini-1.5-flash o gemini-2.0-flash) |
| Frontend | HTML + CSS + Vanilla JS (sin frameworks) |
| Despliegue | Local (`python app.py`) con ngrok para el webhook de Gmail |

---

## Configuración Requerida

- `GMAIL_CREDENTIALS` — OAuth2 credentials de Google Cloud Console
- `GEMINI_API_KEY` — API key de Google AI Studio
- `NGROK_URL` — URL pública para recibir webhooks de Gmail (durante el demo)

---

## Constraints y Decisiones

- **Sin autenticación** — board público, diseñado para proyectar en clase
- **Sin paginación** — scroll vertical para ~75 correos
- **Polling vs WebSockets** — polling cada 3s elegido por simplicidad; imperceptible en demo en vivo
- **SQLite** — suficiente para ~75 registros en sesión de clase; no requiere servidor de BD
- **ngrok** — solución pragmática para recibir webhooks de Gmail en máquina local durante el webinar
