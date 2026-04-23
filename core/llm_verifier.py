"""
Verificatore LLM (OpenAI / ChatGPT).
Invia il documento + i check points del controllo e ottiene
un esito strutturato in JSON.

Requisiti:
- OPENAI_API_KEY in variabile d'ambiente (o file .env)
- pacchetto: openai>=1.0.0
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

from openai import OpenAI

from .controls_tree import Control
from .preanalyzer import preanalyze_c01, preanalyze_c03


DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


@dataclass
class CheckPointResult:
    check_point: str
    status: str           # "conforme" | "non_conforme" | "parziale" | "non_verificabile"
    evidence: str         # citazione o riferimento al documento
    issue: str            # descrizione del problema se non conforme
    mitigation: str       # azione di mitigazione proposta


@dataclass
class VerificationResult:
    control_id: str
    control_title: str
    overall_status: str              # "conforme" | "non_conforme" | "parziale"
    summary: str
    check_points: List[CheckPointResult]
    mitigation_plan: List[str]       # piano di mitigazione consolidato
    raw_model_output: str = ""       # per debug

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


SYSTEM_PROMPT = """Sei un auditor interno esperto di procedure Procure-to-Pay.
Il tuo compito è verificare se i documenti forniti sono conformi ai check point di un controllo di audit.

Devi rispondere ESCLUSIVAMENTE con un oggetto JSON valido, senza testo aggiuntivo, \
senza markdown, senza backtick. Lo schema è:

{
  "overall_status": "conforme" | "non_conforme" | "parziale",
  "summary": "breve sintesi dell'esito (max 3 frasi)",
  "check_points": [
    {
      "check_point": "testo del check point",
      "status": "conforme" | "non_conforme" | "parziale" | "non_verificabile",
      "evidence": "riferimento al documento (es. 'riga 5 del foglio PR_PO', 'par. 3.2') o 'non presente nei documenti'",
      "issue": "descrizione sintetica del problema se non conforme, altrimenti stringa vuota",
      "mitigation": "azione specifica di mitigazione se non conforme, altrimenti stringa vuota"
    }
  ],
  "mitigation_plan": [
    "azione 1",
    "azione 2"
  ]
}

Regole generali:
- Se il documento non contiene informazioni sufficienti per valutare un check point, usa "non_verificabile".
- overall_status = "non_conforme" se almeno un check point è "non_conforme".
- overall_status = "parziale" se ci sono "non_verificabile" ma nessun "non_conforme".
- Le mitigazioni devono essere azioni concrete (non generiche).
- Rispondi in italiano.

Regole per i confronti numerici (applica con massima precisione):
- Verifica DoA: una PR è CONFORME se PR_Amount_EUR <= DoA_Threshold_EUR dell'approvatore. \
  Esempio: importo 75.000 EUR con soglia DoA 100.000 EUR → CONFORME (75.000 < 100.000).
- Verifica budget: una PR è CONFORME se PR_Amount_EUR <= Budget_Available_EUR. \
  Esempio: importo 75.000 EUR con budget 120.000 EUR → CONFORME (75.000 < 120.000).
- Prima di classificare "non_conforme" su base numerica, ripeti mentalmente il confronto \
  esplicitando i due valori (es. "75.000 <= 100.000 → conforme").
- Segregation of duties: verifica che il nome del PR_Creator sia diverso dal nome del PO_Creator \
  per ogni riga. Se sono la stessa persona → NON CONFORME.
"""


def _build_user_prompt(
    control: Control,
    documents: List[tuple[str, str]],
    file_paths: List[Path] | None = None,
) -> str:
    docs_section = "\n\n".join(
        f"### Documento: {name}\n```\n{content[:15000]}\n```"
        for name, content in documents
    )
    check_points_block = "\n".join(
        f"{i+1}. {cp}" for i, cp in enumerate(control.check_points)
    )

    preanalysis_block = ""
    if file_paths:
        if control.id == "C01":
            preanalysis_block = preanalyze_c01(file_paths)
        elif control.id == "C03":
            preanalysis_block = preanalyze_c03(file_paths)

    preanalysis_section = (
        f"\n\nPRE-ANALISI AUTOMATICA:\n{preanalysis_block}\n"
        if preanalysis_block
        else ""
    )

    return f"""CONTROLLO DI AUDIT

ID: {control.id}
Titolo: {control.title}
Area: {control.area}
Descrizione: {control.description}

CHECK POINTS DA VERIFICARE:
{check_points_block}
{preanalysis_section}
DOCUMENTI FORNITI (per il testo narrativo):
{docs_section}

Valuta ogni check point usando la PRE-ANALISI AUTOMATICA (se presente) per lo status, \
e i documenti per l'evidenza testuale. Rispondi con il JSON richiesto.
"""


class LLMVerifier:
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model

    def verify(
        self,
        control: Control,
        documents: List[tuple[str, str]],
        file_paths: List[Path] | None = None,
    ) -> VerificationResult:
        """
        documents: lista di tuple (filename, text_content).
        file_paths: percorsi originali dei file (per la pre-analisi).
        """
        user_prompt = _build_user_prompt(control, documents, file_paths)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)

        check_points = [
            CheckPointResult(
                check_point=cp.get("check_point", ""),
                status=cp.get("status", "non_verificabile"),
                evidence=cp.get("evidence", ""),
                issue=cp.get("issue", ""),
                mitigation=cp.get("mitigation", ""),
            )
            for cp in data.get("check_points", [])
        ]

        return VerificationResult(
            control_id=control.id,
            control_title=control.title,
            overall_status=data.get("overall_status", "non_verificabile"),
            summary=data.get("summary", ""),
            check_points=check_points,
            mitigation_plan=data.get("mitigation_plan", []),
            raw_model_output=raw,
        )
