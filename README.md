# Internal Audit POC — Procure-to-Pay

POC di Internal Audit che verifica, tramite ChatGPT, la conformità di documenti aziendali rispetto ai punti di controllo definiti in una procedura.

## Architettura

```
audit_poc/
├── app.py                     # Streamlit UI
├── requirements.txt
├── .env.example
├── samples_prompts.md         # prompt da usare in Claude Cowork per generare i sample
├── core/
│   ├── controls_tree.py       # albero dei 3 controlli (PR/PO, Vendor, Payment Terms)
│   ├── document_loader.py     # estrazione testo da PDF, DOCX, XLSX, CSV, TXT
│   ├── llm_verifier.py        # client OpenAI + prompt strutturato con output JSON
│   └── report_generator.py    # generazione PDF finale (reportlab)
└── reports/                   # output PDF
```

**Flusso logico:**
1. L'utente seleziona un controllo dalla sidebar (albero).
2. Carica i documenti relativi (uno o più file).
3. Clicca "Esegui verifica" → l'app estrae il testo dai file, costruisce un prompt strutturato e chiama ChatGPT con `response_format=json_object`.
4. L'esito (status + check points + mitigazioni) viene mostrato a schermo.
5. Ripete per gli altri controlli.
6. Al termine, un unico bottone genera un **report PDF** consolidato con executive summary, dettaglio per controllo e piano di mitigazione.

## Setup

```bash
# 1. Clona e installa
cd audit_poc
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configura la API key OpenAI
cp .env.example .env
# apri .env e inserisci la tua OPENAI_API_KEY

# 3. Lancia
streamlit run app.py
```

L'app si apre su http://localhost:8501.

## Come generare i documenti sample

Questa POC non include i documenti da verificare (come da assunzione). Il file `samples_prompts.md` contiene i prompt pronti da incollare in **Claude Cowork** per generare, per ogni controllo, **un documento conforme e uno non conforme**. Una volta generati, si caricano direttamente nell'UI Streamlit.

## Estendere i controlli

Aggiungere un controllo = aggiungere una `Control(...)` alla lista `CONTROLS_TREE` in `core/controls_tree.py`. L'albero in sidebar e il flusso di verifica si aggiornano automaticamente.

## Modello LLM

Di default viene usato `gpt-4o-mini` (bilanciato costo/qualità). Si può cambiare via variabile d'ambiente `OPENAI_MODEL`, es. `gpt-4o` per maggiore accuratezza.

## Note di design

- **Output strutturato**: il verificatore forza un JSON schema, quindi il risultato è sempre processabile a prescindere dalle "chiacchiere" del modello.
- **Segregation of prompt**: il system prompt contiene le regole auditor-generiche; l'user prompt contiene il controllo specifico e i documenti → facile aggiungere nuovi controlli senza toccare il verificatore.
- **Troncamento documenti**: per sicurezza tronco ogni documento a 15.000 caratteri nel prompt (gestione naive ma sufficiente per la POC). Per documenti lunghi va introdotto chunking + retrieval.
