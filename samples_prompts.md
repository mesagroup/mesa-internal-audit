# Prompt per generare i documenti sample in Claude Cowork

Per ogni controllo vanno generati **2 documenti**: uno **conforme** e uno **non conforme**. Copia i prompt qui sotto in Claude Cowork (uno per volta). I file generati vanno poi caricati nell'UI Streamlit nel controllo corrispondente.

> Suggerimento: in Cowork chiedi esplicitamente l'output come file (XLSX o DOCX). I nomi dei file suggeriti aiutano a tenere traccia.

---

## Controllo C01 — PR/PO Authorization & Segregation of Duties

### C01 — Documento CONFORME

```
Sei un controller di azienda manifatturiera. Genera un file Excel (.xlsx) chiamato
"C01_PR_PO_register_conforme.xlsx" che simuli un estratto del registro PR/PO
del mese di marzo 2026 contenente 12 righe.

Colonne richieste:
- PR_Number (formato PR-2026-XXXX)
- PR_Date
- PR_Creator (nome e cognome + dipartimento)
- PR_Approver (nome e cognome + ruolo)
- PR_Amount_EUR
- Cost_Center
- Budget_Available_EUR
- PO_Number (formato PO-2026-XXXX)
- PO_Date (sempre successiva alla PR_Date)
- PO_Creator (deve essere SEMPRE una persona del Purchasing Department, diversa dal PR_Creator)
- DoA_Threshold_EUR (limite di approvazione del PR_Approver secondo DoA)
- Notes

Vincoli per rendere il dataset CONFORME:
- Ogni PR ha un approver con DoA_Threshold_EUR >= PR_Amount_EUR
- PO_Creator è sempre diverso da PR_Creator
- Nessuna PR supera il Budget_Available_EUR
- La PO_Date è sempre almeno 1 giorno dopo la PR_Date
- Importi realistici tra 500€ e 80.000€

Aggiungi un secondo foglio "Delegation_of_Authority" con la tabella dei limiti
per ruolo (es. Team Lead: 5.000€, Manager: 25.000€, Director: 100.000€, VP: 500.000€).
```

### C01 — Documento NON CONFORME

```
Sei un controller di azienda manifatturiera. Genera un file Excel (.xlsx) chiamato
"C01_PR_PO_register_non_conforme.xlsx" che simuli un estratto del registro PR/PO
del mese di marzo 2026 contenente 12 righe.

Colonne richieste (stesse del file conforme):
PR_Number, PR_Date, PR_Creator, PR_Approver, PR_Amount_EUR, Cost_Center,
Budget_Available_EUR, PO_Number, PO_Date, PO_Creator, DoA_Threshold_EUR, Notes.

Inserisci deliberatamente le seguenti anomalie (mescolate tra righe regolari):
1. Almeno 2 righe in cui PR_Creator = PO_Creator (violazione SoD)
2. Almeno 2 righe in cui PR_Amount_EUR > DoA_Threshold_EUR del PR_Approver
   (approvazione oltre delega)
3. Almeno 1 riga in cui PR_Amount_EUR > Budget_Available_EUR senza evidenza
   di approvazione speciale nella colonna Notes
4. Almeno 1 riga in cui PO_Date precede la PR_Date (PO emesso prima della PR)

Aggiungi un secondo foglio "Delegation_of_Authority" con la tabella dei limiti
per ruolo. Le anomalie devono essere plausibili, non caricaturali.
```

---

## Controllo C02 — Vendor Evaluation & Sourcing Process

### C02 — Documento CONFORME

```
Genera un file Word (.docx) chiamato "C02_vendor_selection_dossier_conforme.docx"
che simuli un dossier di selezione fornitore per la gara "Fornitura servizi IT
cloud 2026 — Q1" di un'azienda medio-grande.

Il documento deve contenere le seguenti sezioni:

1. COPERTINA
   - Oggetto della gara
   - Valore stimato: 180.000€
   - Ente richiedente: IT Department
   - Gestito da: Procurement Department (indica referente con nome)

2. RFQ
   - Elenco di 3 fornitori invitati con date di invio RFQ

3. QUOTATIONS RICEVUTE
   - Tabella con 3 fornitori: Vendor A (175.000€), Vendor B (168.000€),
     Vendor C (182.000€)

4. NEGOZIAZIONE
   - Note della trattativa con Vendor B (quotation vincente)
   - Quotation iniziale 168.000€ → PO finale 162.500€ (sconto ottenuto)

5. AWARD MINUTES
   - Verbale di aggiudicazione firmato da: Procurement Manager, IT Director,
     CFO (per importo > 150k€)
   - Data, criteri di scelta (prezzo + SLA + referenze)

6. PO / CONTRACT
   - Riferimento PO-2026-0412 emesso a Vendor B

Tono formale, aziendale. Usa nomi plausibili ma fittizi.
```

### C02 — Documento NON CONFORME

```
Genera un file Word (.docx) chiamato "C02_vendor_selection_dossier_non_conforme.docx"
che simuli un dossier di selezione fornitore per la gara "Fornitura servizi IT
cloud 2026 — Q1" di un'azienda medio-grande.

Stessa struttura del file conforme (copertina, RFQ, quotations, negoziazione,
award minutes, PO) ma con le seguenti anomalie deliberate:

1. Nella COPERTINA indica che il processo è stato "coordinato dal Responsabile IT"
   senza menzione del Procurement Department (violazione: sourcing gestito dal
   business invece che dal Procurement)
2. Nella sezione RFQ indica che è stato contattato un solo fornitore
   (Vendor B) perché "fornitore già consolidato" — SENZA giustificazione formale
   di single sourcing e SENZA approvazione
3. NON includere la sezione NEGOZIAZIONE (nessuna evidenza di trattativa)
4. Nelle AWARD MINUTES: il verbale è firmato solo dal Responsabile IT, manca
   la firma del Procurement Manager e del CFO (nonostante l'importo di 180k€
   richieda escalation)
5. Aggiungi una nota finale: "Benchmarking di mercato non effettuato da oltre
   18 mesi."

Le anomalie devono risultare plausibili in un contesto aziendale reale —
niente di esagerato o caricaturale.
```

---

## Controllo C03 — Payment Terms Alignment (Top 5 Suppliers)

### C03 — Documento CONFORME

```
Genera un file Excel (.xlsx) chiamato "C03_top5_suppliers_payments_conforme.xlsx"
contenente due fogli.

FOGLIO 1 — "Contract_Payment_Terms":
Tabella dei Payment Terms contrattuali per i 5 fornitori principali.
Colonne: Supplier_Name, Contract_Reference, Contract_Payment_Terms
(es. "60gg DFFM", "30gg FM", "45gg data fattura"), Annual_Spend_EUR.
Indicazione dei 5 fornitori top con spend totale tra 500k€ e 2M€ ciascuno.

FOGLIO 2 — "Invoices_Q1_2026":
Estratto fatture del Q1 2026 per i 5 fornitori (circa 4-5 fatture per fornitore,
totale ~22 righe).
Colonne: Supplier_Name, Invoice_Number, Invoice_Date, Invoice_Amount_EUR,
Due_Date_Calculated (calcolata in base ai PT contrattuali),
Actual_Payment_Date, Days_Late (0 o negativo se pagata in tempo).

Vincoli per CONFORMITÀ:
- Actual_Payment_Date rispetta SEMPRE Due_Date_Calculated
  (Days_Late <= 0 per tutte le fatture)
- Le Due_Date_Calculated sono coerenti con i PT del foglio 1
- Importi realistici tra 5.000€ e 150.000€ per fattura
```

### C03 — Documento NON CONFORME

```
Genera un file Excel (.xlsx) chiamato "C03_top5_suppliers_payments_non_conforme.xlsx"
contenente due fogli.

FOGLIO 1 — "Contract_Payment_Terms":
Tabella dei Payment Terms contrattuali per i 5 fornitori principali.
Colonne: Supplier_Name, Contract_Reference, Contract_Payment_Terms, Annual_Spend_EUR.
IMPORTANTE: per uno dei 5 fornitori lascia la cella Contract_Reference VUOTA
(fornitore senza contratto formale). Per questo fornitore aggiungi nella colonna
Contract_Payment_Terms il valore "PT da PO" e crea un mini-blocco sotto la tabella
che mostra i PT riportati nel PO emesso.

FOGLIO 2 — "Invoices_Q1_2026":
Estratto fatture del Q1 2026 per i 5 fornitori (circa 4-5 fatture per fornitore).
Colonne: Supplier_Name, Invoice_Number, Invoice_Date, Invoice_Amount_EUR,
Due_Date_Calculated, Actual_Payment_Date, Days_Late.

Anomalie deliberate da inserire:
1. Almeno 3 fatture con Days_Late > 15 (pagamenti in ritardo oltre i PT contrattuali)
2. Almeno 2 fatture di fornitori diversi pagate con PT più lunghi di quelli a
   contratto (es. contratto 30gg ma Actual_Payment_Date a 55gg)
3. Nessuna colonna "Clarification_Requested" o nota a margine che documenti
   i ritardi (i ritardi sono lì, ma nessuno ha chiesto chiarimenti)
4. Per il fornitore senza contratto, almeno 1 fattura pagata con PT diverso
   rispetto ai PT del PO citato

Le anomalie devono essere distribuite tra diversi fornitori, non concentrate
su uno solo.
```

---

## Checklist di caricamento

Dopo aver generato i 6 file con Cowork, caricali nell'UI Streamlit come segue.

Per dimostrare entrambi gli esiti, **esegui 6 verifiche separate**: una sola coppia di file alla volta.

| Controllo | File da caricare               | Esito atteso       |
|-----------|--------------------------------|--------------------|
| C01       | C01_PR_PO_register_conforme    | 🟢 Conforme        |
| C01       | C01_PR_PO_register_non_conforme| 🔴 Non conforme    |
| C02       | C02_vendor_selection_...conforme| 🟢 Conforme       |
| C02       | C02_vendor_selection_...non_conforme| 🔴 Non conforme |
| C03       | C03_top5_suppliers_...conforme | 🟢 Conforme        |
| C03       | C03_top5_suppliers_...non_conforme | 🔴 Non conforme |
