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
        title="Vendor Sourcing — Coerenza documentale RFQ / PO / Contratto",
        area="Vendor Management",
        description=(
            "Verifica la coerenza incrociata tra i tre documenti chiave di "
            "un'iniziativa di sourcing: RFQ (Request for Quotation), Purchase "
            "Order e Contratto. Controlla che vendor, importi, Payment Terms e "
            "ownership delle firme siano allineati tra i documenti e conformi "
            "alla procedura. NOTA: verifiche sul benchmarking periodico e "
            "sullo storico delle approvazioni di single sourcing richiedono "
            "accesso ai sistemi SRM/ERP e sono fuori scope per questa POC."
        ),
        check_points=[
            "Sono presenti tutti e tre i documenti (RFQ, PO, Contratto) riferiti alla stessa iniziativa di sourcing",
            "Il vendor aggiudicato nel PO corrisponde a uno dei vendor invitati nella RFQ (no 'vendor a sorpresa')",
            "Il vendor del Contratto coincide con il vendor del PO",
            "Le condizioni economiche (importo, Payment Terms, SLA) del Contratto sono coerenti con quelle del PO",
            "La RFQ e il PO sono emessi/firmati dal Procurement Department (ownership corretta), non esclusivamente dal business richiedente",
            "Le firme di approvazione del PO rispettano la Delegation of Authority (per importi > 150.000€ è richiesta l'approvazione del CFO)",
        ],
        expected_documents=[
            "RFQ (.docx): oggetto della gara, elenco vendor invitati, perimetro tecnico/economico, firma dell'emittente",
            "Purchase Order (.docx): vendor aggiudicato, importo, Payment Terms, SLA, firme di approvazione",
            "Contratto (.docx): vendor, importo, condizioni economiche e di servizio, firme delle parti",
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
