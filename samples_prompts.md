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

## Controllo C02 — Vendor Sourcing: coerenza RFQ / PO / Contratto

> **Scenario condiviso** per tutti e 6 i prompt di C02: gara per la "Fornitura
> servizi IT cloud 2026 — Q1", valore stimato ~180.000€, ente richiedente
> IT Department. Azienda medio-grande manifatturiera fittizia. Tutti i prompt
> riutilizzano gli stessi identificatori (numero RFQ, PO, contratto) così che
> il verificatore possa triangolare i 3 documenti. L'esito CONFORME richiede
> RFQ + PO + Contratto coerenti tra loro; l'esito NON CONFORME nasce da
> discrepanze **incrociate** che si vedono solo confrontando i tre file.

### C02 — RFQ CONFORME

```
Genera un file Word (.docx) chiamato "C02_RFQ_conforme.docx" che simuli una
Request for Quotation aziendale formale per la gara:

- Oggetto: "Fornitura servizi IT cloud 2026 — Q1"
- Numero RFQ: RFQ-2026-0087
- Data emissione: 12 gennaio 2026
- Scadenza invio quotation: 31 gennaio 2026
- Valore stimato: 180.000€
- Ente richiedente: IT Department (referente: Marco Bianchi, IT Director)
- Emessa e gestita da: Procurement Department
  (referente: Laura Conti, Procurement Manager — firma in calce)

Il documento deve contenere:

1. INTESTAZIONE aziendale (nome fittizio, es. "Lombardia Manufacturing S.p.A.")
   + data e numero RFQ.

2. PERIMETRO DELLA FORNITURA
   - Descrizione servizi richiesti (IaaS + PaaS, backup, SLA 99,5%,
     supporto 24/7)
   - Durata contrattuale: 24 mesi
   - Modalità di pagamento attese: "60 giorni data fattura fine mese"

3. VENDOR INVITATI (tabella a 3 righe)
   - CloudStack Solutions S.r.l. — P.IVA fittizia — email inviata 12/01/2026
   - Nimbus Tech Italia S.r.l. — P.IVA fittizia — email inviata 12/01/2026
   - DataHarbor Europe S.p.A. — P.IVA fittizia — email inviata 12/01/2026

4. CRITERI DI AGGIUDICAZIONE
   - 60% prezzo, 25% SLA/qualità tecnica, 15% referenze

5. FIRMA
   - "Per il Procurement Department: Laura Conti, Procurement Manager"
   - Data 12/01/2026

Tono formale, aziendale, italiano. Nessuna anomalia.
```

### C02 — RFQ NON CONFORME

```
Genera un file Word (.docx) chiamato "C02_RFQ_non_conforme.docx" che simuli la
stessa RFQ di cui sopra (gara "Fornitura servizi IT cloud 2026 — Q1",
RFQ-2026-0087, valore 180.000€), stessa struttura (intestazione, perimetro,
vendor invitati, criteri, firma).

Mantieni gli stessi 3 vendor invitati:
- CloudStack Solutions S.r.l.
- Nimbus Tech Italia S.r.l.
- DataHarbor Europe S.p.A.

Mantieni i Payment Terms attesi: "60 giorni data fattura fine mese".

Inserisci però le seguenti anomalie (sottili, plausibili):

1. La RFQ è emessa e firmata da **Marco Bianchi, IT Director** (business)
   invece che dal Procurement Manager. In calce NON compare alcuna firma
   Procurement. Nel corpo la dicitura è "Per l'IT Department" invece di
   "Per il Procurement Department".
2. Nel perimetro aggiungi questa riga in fondo: "Referente unico per
   l'aggiudicazione: IT Department".

Le anomalie qui non bastano da sole — l'irregolarità vera emerge dal confronto
con PO e Contratto. Tono formale, non caricaturale.
```

### C02 — PO CONFORME

```
Genera un file Word (.docx) chiamato "C02_PO_conforme.docx" che simuli un
Purchase Order aziendale in forma di documento formale (intestazione +
tabella + firme).

Dati del PO (tutti COERENTI con la RFQ-2026-0087):

- Numero PO: PO-2026-0412
- Data emissione: 10 febbraio 2026
- Riferimento RFQ: RFQ-2026-0087
- Vendor aggiudicato: **CloudStack Solutions S.r.l.**
  (deve essere UNO dei 3 vendor invitati nella RFQ)
- Importo: 162.500€ (quotation iniziale 168.000€, poi ridotta in negoziazione —
  aggiungi una riga note: "Sconto negoziato 3,3% su quotation iniziale")
- Payment Terms: "60 giorni data fattura fine mese" (come RFQ)
- SLA: 99,5%
- Durata: 24 mesi

Struttura del documento:
1. Intestazione azienda "Lombardia Manufacturing S.p.A." + numero PO + data
2. Sezione "Fornitore" con ragione sociale CloudStack Solutions S.r.l.
3. Tabella "Oggetto della fornitura" (descrizione, quantità/durata, importo)
4. Sezione "Condizioni economiche": importo 162.500€, PT 60gg DFFM, SLA 99,5%
5. Sezione "Riferimenti": RFQ-2026-0087, Award del 05/02/2026
6. Sezione "Firme di approvazione" — DEVONO comparire TUTTE queste firme:
   - Laura Conti — Procurement Manager (ownership)
   - Marco Bianchi — IT Director (business sponsor)
   - Giulia Romano — Chief Financial Officer
     (escalation obbligatoria per importi > 150.000€)

Tono formale. Nessuna anomalia.
```

### C02 — PO NON CONFORME

```
Genera un file Word (.docx) chiamato "C02_PO_non_conforme.docx" con la stessa
struttura del PO conforme (intestazione, fornitore, oggetto, condizioni,
riferimenti, firme).

Dati da usare, con anomalie incrociate rispetto a RFQ-2026-0087:

- Numero PO: PO-2026-0412
- Data emissione: 10 febbraio 2026
- Riferimento RFQ: RFQ-2026-0087
- Vendor aggiudicato: **Cloud9 Enterprise S.r.l.**
  (ATTENZIONE: questo vendor NON è fra i 3 invitati nella RFQ — anomalia
  "vendor a sorpresa" rilevabile solo incrociando RFQ e PO)
- Importo: 178.000€
  (ATTENZIONE: non coerente con la quotation di riferimento della RFQ e
  molto vicino al tetto stimato — nessuna nota di negoziazione)
- Payment Terms indicati nel PO: "30 giorni data fattura"
  (ATTENZIONE: diverso dai 60gg DFFM della RFQ)
- SLA: 99,5%
- Durata: 24 mesi

Aggiungi in "Riferimenti" il rimando a RFQ-2026-0087 (ma senza una vera
award minutes allegata, scrivi solo "Selezione interna").

Firme di approvazione — DEVONO comparire SOLO queste:
- Marco Bianchi — IT Director
- (NESSUNA firma del Procurement Manager)
- (NESSUNA firma del CFO, nonostante l'importo 178.000€ superi la soglia DoA
  di 150.000€ che richiede escalation)

Le anomalie devono essere plausibili: un PO reale con questi difetti passerebbe
una prima occhiata distratta.
```

### C02 — Contratto CONFORME

```
Genera un file Word (.docx) chiamato "C02_contract_conforme.docx" che simuli
un contratto di fornitura di servizi IT cloud. Stile giuridico-commerciale
italiano, sobrio, 3-5 pagine.

Dati del contratto (tutti COERENTI con PO-2026-0412):

- Numero contratto: CT-2026-0189
- Data: 20 febbraio 2026
- Parti:
  * Cliente: Lombardia Manufacturing S.p.A. (sede, C.F./P.IVA fittizi)
  * Fornitore: **CloudStack Solutions S.r.l.** (stesso vendor del PO)
- Oggetto: servizi IT cloud (IaaS + PaaS + backup) secondo il perimetro
  tecnico già descritto nel PO-2026-0412
- Valore complessivo: **162.500€** (identico al PO)
- Payment Terms: **"60 giorni data fattura fine mese"** (identici al PO)
- SLA: 99,5% (identico al PO)
- Durata: 24 mesi dalla data di firma
- Riferimenti espliciti: "Il presente contratto dà attuazione al
  PO-2026-0412 del 10/02/2026, a seguito della RFQ-2026-0087."

Struttura (articoli numerati):
Art. 1 Oggetto — Art. 2 Corrispettivo e fatturazione (con PT) —
Art. 3 SLA e penali — Art. 4 Durata — Art. 5 Riservatezza —
Art. 6 Recesso — Art. 7 Foro competente.

Firme finali in calce:
- Per il Cliente: Laura Conti, Procurement Manager + Giulia Romano, CFO
- Per il Fornitore: legale rappresentante CloudStack Solutions S.r.l.
  (nome fittizio)

Tono formale, nessuna anomalia.
```

### C02 — Contratto NON CONFORME

```
Genera un file Word (.docx) chiamato "C02_contract_non_conforme.docx" con la
stessa struttura del contratto conforme (7 articoli, intestazione, firme).

Dati da usare, progettati per essere INCOERENTI col PO-2026-0412 non conforme:

- Numero contratto: CT-2026-0189
- Data: 20 febbraio 2026
- Parti:
  * Cliente: Lombardia Manufacturing S.p.A.
  * Fornitore: **CloudStack Solutions S.r.l.**
    (ATTENZIONE: il PO-2026-0412 non conforme è intestato a Cloud9 Enterprise
    S.r.l. — discrepanza vendor PO vs Contratto, rilevabile solo incrociando
    i due documenti)
- Valore complessivo: **162.500€**
  (ATTENZIONE: il PO riporta 178.000€ — discrepanza di importo)
- Payment Terms: **"90 giorni data fattura"**
  (ATTENZIONE: diversi sia dalla RFQ — 60gg DFFM — sia dal PO — 30gg;
  tre valori diversi sui tre documenti)
- SLA: 99,5%
- Durata: 24 mesi
- Riferimenti: cita PO-2026-0412 e RFQ-2026-0087 come se fossero coerenti
  (il contratto "finge" coerenza — sta all'auditor scoprire che non lo sono).

Firme finali:
- Per il Cliente: Marco Bianchi, IT Director
  (ATTENZIONE: nessuna firma Procurement, nessuna firma CFO)
- Per il Fornitore: legale rappresentante CloudStack Solutions S.r.l.

Le anomalie devono emergere dal confronto con RFQ e PO — il Contratto, letto
da solo, sembra un documento ordinato. È la triangolazione che lo inchioda.
```

> **Sintesi delle anomalie incrociate del set NON CONFORME** (cosa dovrebbe
> trovare l'auditor confrontando i 3 file):
> 1. RFQ firmata da IT Director invece che da Procurement Manager
> 2. PO emesso a un vendor (Cloud9 Enterprise) NON presente nella RFQ
> 3. Contratto intestato a un vendor diverso dal PO (CloudStack ≠ Cloud9)
> 4. Importi disallineati: PO 178.000€ vs Contratto 162.500€
> 5. Payment Terms con tre valori diversi sui tre documenti (60gg / 30gg / 90gg)
> 6. PO non firmato dal CFO pur superando la soglia DoA di 150.000€
> 7. Nessuna firma Procurement né su PO né su Contratto

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

Dopo aver generato i file con Cowork, caricali nell'UI Streamlit come segue.
Per dimostrare entrambi gli esiti, **esegui 6 verifiche separate**: un set di file alla volta.
Per C02 vanno caricati **3 file insieme** (RFQ + PO + Contratto) perché il controllo si basa sulla triangolazione documentale.

| Controllo | File da caricare                                                                    | Esito atteso    |
|-----------|-------------------------------------------------------------------------------------|-----------------|
| C01       | C01_PR_PO_register_conforme.xlsx                                                    | 🟢 Conforme     |
| C01       | C01_PR_PO_register_non_conforme.xlsx                                                | 🔴 Non conforme |
| C02       | C02_RFQ_conforme.docx + C02_PO_conforme.docx + C02_contract_conforme.docx           | 🟢 Conforme     |
| C02       | C02_RFQ_non_conforme.docx + C02_PO_non_conforme.docx + C02_contract_non_conforme.docx | 🔴 Non conforme |
| C03       | C03_top5_suppliers_payments_conforme.xlsx                                           | 🟢 Conforme     |
| C03       | C03_top5_suppliers_payments_non_conforme.xlsx                                       | 🔴 Non conforme |
