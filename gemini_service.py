import json
from google import genai
from config import GEMINI_API_KEY

_PROMPT = """Eres un evaluador EQUILIBRADO de correos electrónicos comerciales escritos por vendedores que usan IA.
Tu objetivo es distinguir lo bueno de lo mediocre, pero sin castigar injustamente. Un correo bien estructurado y claro merece entre 6 y 7. Reserva los extremos (1-3 y 9-10) para casos realmente malos o brillantes.

Evalúa el siguiente correo enviado a COLMEN IA (empresa colombiana de inteligencia artificial aplicada a negocios).
Devuelve SOLO un JSON con exactamente estas 9 claves, sin texto adicional antes ni después:

{{
  "puntaje_asunto": <1-10>,
  "puntaje_persuasion": <1-10>,
  "puntaje_contexto": <1-10>,
  "puntaje_propuesta": <1-10>,
  "puntaje_gancho": <1-10>,
  "puntaje_personalizacion": <1-10>,
  "puntaje_unicidad": <1-10>,
  "puntaje_cta": <1-10>,
  "resumen": "<2-3 líneas: qué lo hace destacar o en qué puede mejorar>"
}}

ESCALA DE REFERENCIA: 5=suficiente, 6=bueno, 7=muy bueno, 8=excelente, 9-10=excepcional. No des menos de 4 salvo que sea spam puro o completamente irrelevante.

RUBRICA (evalúa todo en una sola lectura):

1. puntaje_asunto — ¿El subject invita a abrir? 4=genérico pero correcto, 6=claro y relevante, 8=llamativo y específico, 10=irresistible
2. puntaje_persuasion — ¿Tono natural y convincente? Penaliza levemente frases robóticas ("soluciones innovadoras"), pero valora la intención de comunicar beneficios
3. puntaje_contexto — ¿Queda claro quién es, de qué empresa y por qué escribe? Un correo con presentación completa merece al menos 6
4. puntaje_propuesta — ¿Hay una propuesta de valor entendible? Con propuesta clara aunque sin números merece 6; con datos concretos sube a 8+
5. puntaje_gancho — ¿La primera línea engancha o es plana? Una apertura directa al punto merece 6; solo penaliza fuerte si empieza con presentación aburrida
6. puntaje_personalizacion — ¿Menciona algo de COLMEN IA o del sector IA en Colombia? Cualquier referencia al contexto suma; 5 si es genérico pero pertinente
7. puntaje_unicidad — ¿Podría enviarse solo a COLMEN IA o a cualquier empresa? Correo adaptado al sector merece 6; solo penaliza fuerte si es plantilla 100% genérica
8. puntaje_cta — ¿Hay un llamado a la acción claro? Un CTA simple pero presente merece 6; uno con fecha o propuesta concreta llega a 8+

ASUNTO: {asunto}

CUERPO:
{cuerpo}
"""


class _GeminiModel:
    def __init__(self):
        self._client = None

    def generate_content(self, prompt: str):
        if self._client is None:
            self._client = genai.Client(api_key=GEMINI_API_KEY)
        return self._client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )


model = _GeminiModel()

_KEYS = ["puntaje_asunto", "puntaje_persuasion", "puntaje_contexto", "puntaje_propuesta",
         "puntaje_gancho", "puntaje_personalizacion", "puntaje_unicidad", "puntaje_cta"]


def analyze_email(asunto: str, cuerpo: str) -> dict:
    prompt = _PROMPT.format(asunto=asunto, cuerpo=cuerpo)
    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    data = json.loads(text)
    data["puntaje_total"] = round(sum(data[k] for k in _KEYS) / len(_KEYS), 2)
    return data
