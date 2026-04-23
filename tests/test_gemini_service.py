import json
from unittest.mock import MagicMock, patch
import gemini_service

MOCK_RESPONSE_JSON = json.dumps({
    "puntaje_asunto": 8,
    "puntaje_persuasion": 7,
    "puntaje_contexto": 9,
    "puntaje_propuesta": 6,
    "resumen": "Buen asunto pero propuesta débil.",
})

def _mock_model(response_text):
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    return mock_model

def test_analyze_email_returns_scores():
    with patch.object(gemini_service, "model", _mock_model(MOCK_RESPONSE_JSON)):
        result = gemini_service.analyze_email("Oferta única", "Hola, te escribo porque...")
    assert result["puntaje_asunto"] == 8
    assert result["puntaje_persuasion"] == 7
    assert result["puntaje_contexto"] == 9
    assert result["puntaje_propuesta"] == 6
    assert result["puntaje_total"] == 7.5
    assert "resumen" in result

def test_analyze_email_strips_markdown_code_block():
    wrapped = "```json\n" + MOCK_RESPONSE_JSON + "\n```"
    with patch.object(gemini_service, "model", _mock_model(wrapped)):
        result = gemini_service.analyze_email("Asunto", "Cuerpo")
    assert result["puntaje_total"] == 7.5

def test_puntaje_total_is_average():
    data = {
        "puntaje_asunto": 10,
        "puntaje_persuasion": 10,
        "puntaje_contexto": 10,
        "puntaje_propuesta": 10,
        "resumen": "Perfecto.",
    }
    with patch.object(gemini_service, "model", _mock_model(json.dumps(data))):
        result = gemini_service.analyze_email("X", "Y")
    assert result["puntaje_total"] == 10.0
