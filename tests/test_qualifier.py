"""Tests del clasificador de leads.

El foco esta en la logica que NO depende de la red:
  - la defensa anti-alucinacion (forzar `qualified=false` si algun criterio falla),
  - el parseo/validacion defensiva de la respuesta del LLM,
  - el truncado de entradas largas,
  - el formateo del mensaje al usuario.

La llamada a Groq se mockea (`_call_groq`), asi que ningun test toca la API.
"""

from __future__ import annotations

import json

import pytest

import qualifier
from config import settings
from qualifier import QualificationResult


def _parsed(**overrides):
    """JSON de ejemplo (todos los criterios en true) con overrides opcionales."""
    base = {
        "extracted": {
            "company_type": "consulting",
            "employee_count_estimate": 20,
            "country_or_region": "spain",
            "country_detail": "Madrid",
            "automation_or_ai_interest": "explicit",
        },
        "criteria_checks": {
            "is_services_or_consulting": True,
            "has_min_5_employees": True,
            "is_spain_or_latam": True,
            "shows_automation_interest": True,
        },
        "qualified": True,
        "confidence": "high",
        "suspicious_input": False,
        "reasoning": "Consultora en Madrid con interes explicito en IA.",
    }
    base.update(overrides)
    return base


class TestBuildMessages:
    def test_envuelve_el_lead_en_delimitadores(self):
        msgs = qualifier._build_messages("consultora en Bogota")
        assert msgs[0]["role"] == "system"
        user = msgs[1]["content"]
        assert "<<<LEAD>>>" in user and "<<<END_LEAD>>>" in user
        assert "consultora en Bogota" in user


class TestQualifyEntradaVacia:
    def test_cadena_vacia(self):
        r = qualifier.qualify("")
        assert r.qualified is False
        assert r.error == "empty_input"

    def test_solo_espacios(self):
        assert qualifier.qualify("   \n  ").error == "empty_input"


class TestValidateAndBuild:
    def test_se_mantiene_cualificado_si_todos_los_checks_pasan(self):
        r = qualifier._validate_and_build(_parsed(), "raw")
        assert r.qualified is True

    def test_fuerza_no_cualificado_por_incoherencia(self):
        # El LLM dijo qualified=true pero un criterio es false: defensa clave.
        parsed = _parsed()
        parsed["criteria_checks"]["has_min_5_employees"] = False
        r = qualifier._validate_and_build(parsed, "raw")
        assert r.qualified is False
        assert "Forzado" in r.reasoning

    def test_confianza_invalida_cae_a_low(self):
        r = qualifier._validate_and_build(_parsed(confidence="altisima"), "raw")
        assert r.confidence == "low"

    def test_reasoning_vacio_recibe_placeholder(self):
        r = qualifier._validate_and_build(_parsed(reasoning="  "), "raw")
        assert r.reasoning == "Sin razonamiento."

    def test_campos_ausentes_no_rompen(self):
        r = qualifier._validate_and_build({}, "raw")
        assert r.qualified is False
        assert r.confidence == "low"
        assert r.extracted == {}
        assert r.criteria_checks == {}


class TestQualifyPipeline:
    def test_flujo_completo_ok(self, monkeypatch):
        monkeypatch.setattr(qualifier, "_call_groq", lambda m: json.dumps(_parsed()))
        r = qualifier.qualify("Consultora en Madrid, 20 personas, quieren IA")
        assert r.qualified is True
        assert r.confidence == "high"
        assert r.error is None

    def test_json_invalido_del_llm(self, monkeypatch):
        monkeypatch.setattr(qualifier, "_call_groq", lambda m: "esto no es json")
        r = qualifier.qualify("cualquier cosa")
        assert r.error == "invalid_json"
        assert r.qualified is False

    def test_incoherencia_end_to_end(self, monkeypatch):
        parsed = _parsed()
        parsed["criteria_checks"]["is_spain_or_latam"] = False
        monkeypatch.setattr(qualifier, "_call_groq", lambda m: json.dumps(parsed))
        r = qualifier.qualify("Consultora en Berlin")
        assert r.qualified is False

    def test_trunca_entrada_larga(self, monkeypatch):
        capturado = {}

        def fake(messages):
            capturado["messages"] = messages
            return json.dumps(_parsed())

        monkeypatch.setattr(qualifier, "_call_groq", fake)
        largo = "a" * (settings.MAX_LEAD_LENGTH + 100)
        qualifier.qualify(largo)
        assert "[...truncado]" in capturado["messages"][1]["content"]

    def test_error_transitorio_agota_reintentos(self, monkeypatch):
        def boom(messages):
            raise qualifier.GroqTransientError("red caida")

        monkeypatch.setattr(qualifier, "_call_groq", boom)
        r = qualifier.qualify("consultora")
        assert r.error == "llm_unreachable"

    def test_error_no_transitorio(self, monkeypatch):
        def boom(messages):
            raise RuntimeError("clave invalida")

        monkeypatch.setattr(qualifier, "_call_groq", boom)
        r = qualifier.qualify("consultora")
        assert r.error and r.error.startswith("llm_error")


class TestFormatResponse:
    def test_mensaje_cualificado(self):
        msg = qualifier.format_response_for_user(_res(qualified=True))
        assert "[CUALIFICADO]" in msg
        assert "Criterios:" in msg

    def test_mensaje_no_cualificado(self):
        assert "[NO CUALIFICADO]" in qualifier.format_response_for_user(
            _res(qualified=False)
        )

    def test_mensaje_error_generico(self):
        msg = qualifier.format_response_for_user(
            QualificationResult(False, "low", "x", error="llm_error: x")
        )
        assert "problema" in msg.lower()

    def test_mensaje_entrada_vacia(self):
        msg = qualifier.format_response_for_user(
            QualificationResult(False, "low", "x", error="empty_input")
        )
        assert "Ejemplo" in msg

    def test_aviso_sospechoso(self):
        msg = qualifier.format_response_for_user(_res(qualified=False, suspicious=True))
        assert "sospechos" in msg.lower()


def _res(qualified=True, suspicious=False):
    return QualificationResult(
        qualified=qualified,
        confidence="high",
        reasoning="razon de prueba",
        extracted={},
        criteria_checks={
            "is_services_or_consulting": True,
            "has_min_5_employees": True,
            "is_spain_or_latam": True,
            "shows_automation_interest": qualified,
        },
        suspicious_input=suspicious,
    )
