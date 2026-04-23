"""
Definizione dell'albero dei controlli di Internal Audit.
Ogni controllo è mappato su un punto della procedura allegata.

La struttura è volutamente semplice (dict) per facilitare l'estensione:
per aggiungere un controllo basta aggiungere una voce con gli stessi campi.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Control:
    id: str
    title: str
    area: str
    description: str
    check_points: List[str] = field(default_factory=list)
    expected_documents: List[str] = field(default_factory=list)


CONTROLS_TREE: List[Control] = [
    Control(
        id="C01",
        title="PR / PO Authorization & Segregation of Duties",
        area="Procure-to-Pay",
        description=(
            "Verifica che le Purchase Request (PR) campionate siano state "
            "correttamente autorizzate, processate dal dipartimento competente "
            "prima dell'emissione del PO, allineate al budget e che il creatore "
            "della PR sia diverso dal creatore del PO."
        ),
        check_points=[
            "Le PR sono autorizzate secondo la Delegation of Authority in vigore",
            "Le PR sono processate dal dipartimento di competenza PRIMA dell'emissione del PO da parte del Purchasing",
            "Le PR sono allineate al budget; per PR che eccedono il budget deve esistere un processo di approvazione specifico",
            "Il creatore della PR è diverso dal creatore del PO (segregation of duties)",
        ],
        expected_documents=[
            "Estratto PR/PO (Excel o PDF) con campi: PR#, PO#, importo, creatore PR, approvatore, creatore PO, centro di costo, budget disponibile",
            "Delegation of Authority (DoA) vigente",
        ],
    ),
    Control(
        id="C02",
        title="Vendor Evaluation & Sourcing Process",
        area="Vendor Management",
        description=(
            "Verifica che il processo di valutazione e selezione dei fornitori "
            "sia stato condotto in conformità con la procedura: RFQ, quotations, "
            "award minutes, benchmarking e documentazione del single sourcing."
        ),
        check_points=[
            "Esiste documentazione a supporto della selezione (RFQ, quotations, award minutes, comunicazioni, PR, PO, contratti)",
            "Il sourcing è stato gestito dal Procurement e non dal business",
            "I risultati della negoziazione sono documentati e archiviati (es. confronto prima quotation vs PO finale)",
            "Per fornitori ricorrenti/single/strategici (solo 2 vendor) sono effettuati benchmark periodici sui prezzi di mercato",
            "Per single sourcing (1 solo vendor) le ragioni sono documentate e approvate",
        ],
        expected_documents=[
            "RFQ inviate e quotations ricevute",
            "Award minutes / verbali di aggiudicazione",
            "Documentazione di benchmarking o giustificazione single sourcing",
        ],
    ),
    Control(
        id="C03",
        title="Payment Terms Alignment (Top 5 Suppliers)",
        area="Accounts Payable",
        description=(
            "Verifica che le fatture dei 5 fornitori principali siano pagate "
            "secondo i Payment Terms definiti nei contratti (o, in assenza, "
            "nel Purchase Order). Identifica eventuali scostamenti."
        ),
        check_points=[
            "Le fatture sono allineate ai Payment Terms definiti nei contratti",
            "In assenza di contratto, i PT sono quelli dichiarati nel PO",
            "Le eventuali discrepanze sono state oggetto di chiarimento documentato",
        ],
        expected_documents=[
            "Estratto fatture top 5 fornitori con data emissione, data pagamento, PT applicati",
            "Contratti o PO dei fornitori (per verifica PT attesi)",
        ],
    ),
]


def get_control(control_id: str) -> Control:
    for c in CONTROLS_TREE:
        if c.id == control_id:
            return c
    raise KeyError(f"Controllo {control_id} non trovato")
