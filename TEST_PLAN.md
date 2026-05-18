# Test Plan — MESA ERM Prototype
**Data:** 2026-05-15  
**Ambiente:** `python -m streamlit run app.py` → http://localhost:8501  
**DB stato iniziale:** 3 controlli (C01, C02, C03) · 1 owner · nessun altro dato

---

## Credenziali di test

| Utente | Password | Ruolo |
|--------|----------|-------|
| `head_ia` | `head123` | Head of Internal Audit |
| `auditor1` | `audit123` | Auditor |
| `auditee1` | `aud123` | Auditee (sola lettura) |

---

## Flusso end-to-end (eseguire nell'ordine)

---

### FASE 1 — Anagrafica (login: `auditor1`)

**TC-01 — Visualizzazione controlli**
1. Accedere come `auditor1`
2. Navigare su **Anagrafica**
3. **Atteso:** 3 controlli visibili (C01, C02, C03) con descrizione e check points

**TC-02 — Modifica controllo**
1. Aprire l'expander di C01
2. Modificare il campo *Titolo* aggiungendo "(test)" in coda
3. Cliccare **Salva**
4. **Atteso:** banner verde ✅, titolo aggiornato al refresh della pagina

**TC-03 — Ripristino default**
1. Cliccare **↺ Reset to defaults**
2. **Atteso:** C01 torna al titolo originale; i 3 controlli sono invariati

**TC-04 — Aggiunta owner**
1. Sezione *Responsabili* → compilare Nome e Reparto → **Aggiungi**
2. **Atteso:** nuovo owner appare nella lista

**TC-05 — RBAC anagrafica (login: `auditee1`)**
1. Accedere come `auditee1`, navigare su **Anagrafica**
2. **Atteso:** nessun pulsante Salva/Elimina/Reset visibile; messaggio sola lettura

---

### FASE 2 — Risk Assessment (login: `auditor1`)

**TC-06 — Inserimento scoring**
1. Navigare su **Risk Assessment**
2. Selezionare anno *2026*
3. Nella tabella editabile impostare per C01: Likelihood=4, Impact=5; per C02: L=2, I=3; per C03: L=3, I=4
4. Cliccare **Salva scoring 2026**
5. **Atteso:** banner ✅; heat map aggiornata con i 3 punti posizionati correttamente per quadrante

**TC-07 — Heat map e ranking**
1. Verificare che C01 (score 20) sia nel quadrante rosso in alto a destra
2. Verificare che la tabella *Ranking rischi* ordini C01 > C03 > C02
3. **Atteso:** colore rosso per score ≥ 15, arancio per 6-14, verde per ≤ 5

**TC-08 — RBAC risk (login: `auditee1`)**
1. Navigare su **Risk Assessment** come `auditee1`
2. **Atteso:** tabella in sola lettura (st.dataframe), nessun pulsante Salva

---

### FASE 3 — Piano di Audit (login: `head_ia`)

**TC-09 — Creazione piano**
1. Accedere come `head_ia`, navigare su **Piano di Audit**
2. Compilare: Nome = "Audit P2P 2026", Anno = 2026, Note = "Piano annuale"
3. Cliccare **Crea Piano**
4. **Atteso:** banner ✅, piano appare nell'expander

**TC-10 — Aggiunta controlli al piano**
1. Nel piano appena creato, aggiungere C01 → assegnato a "Mario Rossi" → Data 2026-06-30 → **Aggiungi**
2. Aggiungere C02 → "Anna Bianchi" → 2026-09-30 → **Aggiungi**
3. **Atteso:** entrambi i controlli appaiono nella lista con stato *Pianificato*

**TC-11 — Avvio Engagement da Piano**
1. Cliccare **▶ Avvia Engagement** accanto a C01
2. **Atteso:** banner ✅ "Engagement creato"; stato dell'item passa a *In corso*; engagement visibile in **Engagement**

**TC-12 — RBAC piano (login: `auditee1`)**
1. Navigare su **Piano di Audit** come `auditee1`
2. **Atteso:** pagina bloccata con messaggio "accesso riservato"

---

### FASE 4 — Engagement + Verifica AI (login: `auditor1`)

> Prerequisito: avere un file di test da caricare (va bene un `.txt` qualsiasi con contenuto inventato)

**TC-13 — Selezione engagement**
1. Navigare su **Engagement**
2. Selezionare l'engagement creato al TC-11 (o crearne uno nuovo)
3. **Atteso:** sidebar mostra progresso 0/3 controlli

**TC-14 — Caricamento documento e verifica AI**
1. Selezionare controllo C01
2. Caricare un file `.txt` con contenuto di prova (es. "Procedura P2P versione 2026...")
3. Cliccare **Esegui verifica AI**
4. **Atteso:** spinner "Verifica AI in corso…"; risultato con esito complessivo, dettaglio check points, piano di mitigazione

**TC-15 — Riapertura esito precedente**
1. Senza ricaricare documenti, selezionare di nuovo C01
2. **Atteso:** banner info "Verifica già eseguita il..."; esito ricostruito dal DB, pulsante "Apri Finding" se non conforme

**TC-16 — Creazione Finding**
1. Se C01 risulta non conforme, selezionare severità **Alto**
2. Cliccare **⚠️ Apri Finding**
3. **Atteso:** banner ✅ "Finding #N creato"; pulsante disabilitato al secondo click

**TC-17 — Progresso sidebar**
1. Verificare che la sidebar mostri C01 con badge colorato (non più il pallino grigio "pending")
2. **Atteso:** progress bar aggiornata a 1/3

---

### FASE 5 — Findings & Remediation (login: `auditor1`)

**TC-18 — Visualizzazione finding**
1. Navigare su **Findings & Remediation**
2. **Atteso:** finding creato al TC-16 visibile con badge severità e stato "open"

**TC-19 — Aggiunta action plan**
1. Aprire il finding → form *Aggiungi Action Plan*
2. Compilare: Descrizione = "Aggiornare procedura P2P", Responsabile = "Mario Rossi", Scadenza = 2026-06-30
3. Cliccare **Aggiungi**
4. **Atteso:** action plan appare nella lista con stato "open"

**TC-20 — Aggiornamento stato action plan**
1. Cambiare stato action plan a "in_progress" → cliccare ✓
2. **Atteso:** stato aggiornato, colore neutro (non rosso)

**TC-21 — Validazione finding (login: `head_ia`)**
1. Accedere come `head_ia`
2. Sul finding, selezionare stato "validated" → **Aggiorna**
3. **Atteso:** badge passa a "Validato"

**TC-22 — RBAC findings (login: `auditee1`)**
1. Navigare su **Findings & Remediation** come `auditee1`
2. **Atteso:** stato finding in sola lettura, caption "Sola lettura"; action plan aggiornabili (auditee può aggiornare i propri AP)

**TC-23 — Tab Action Plans globale**
1. Cliccare tab **Action Plans**
2. **Atteso:** action plan creato al TC-19 visibile; checkbox "Solo scaduti" non attiva (scadenza futura)

---

### FASE 6 — Reporting (login: `head_ia`)

**TC-24 — Dashboard KPI**
1. Navigare su **Reporting**
2. **Atteso:** 4 KPI card mostrano valori coerenti (controlli=3, engagement attivi≥1, finding aperti≥1, AP scaduti=0)

**TC-25 — Grafici**
1. Tab **Grafici**: verificare i 3 chart Plotly (finding per severità, per stato, AP per stato)
2. Scorrere in basso: *Finding recenti* elenca il finding creato
3. **Atteso:** tutti i grafici renderizzati senza errori

**TC-26 — Completamento piano**
1. Tab **Completamento Piano**
2. **Atteso:** piano "Audit P2P 2026" con barra stacked orizzontale; C01 in arancio "in corso", C02 in grigio "pianificato"

**TC-27 — Export PDF engagement**
1. Tab **Export Report** → selezionare l'engagement usato
2. Cliccare **Genera PDF Engagement**
3. **Atteso:** pulsante *Scarica PDF* appare; il file scaricato è apribile e contiene i dati dell'engagement

**TC-28 — Export CSV**
1. Cliccare **Scarica Findings (CSV)** e **Scarica Action Plans (CSV)**
2. **Atteso:** download dei file CSV con header e dati corretti

**TC-29 — Audit Log**
1. Tab **Audit Log**
2. **Atteso:** righe con operazioni create/update_status colorate per tipo; contatore totale > 0

---

### FASE 7 — Gestione sessioni (tutti i ruoli)

**TC-30 — Logout e re-login**
1. Cliccare **Esci** nella sidebar come `head_ia`
2. **Atteso:** redirect al login; altri moduli non accessibili
3. Accedere come `auditor1`
4. **Atteso:** sessione ripristinata, dati precedenti visibili

**TC-31 — Navigazione diretta URL**
1. Da browser, aprire direttamente `http://localhost:8501/Engagement` senza essere loggati
2. **Atteso:** redirect al login, pagina bloccata

---

## Matrice riepilogativa

| TC | Area | Ruolo | Priorità |
|----|------|-------|----------|
| 01-05 | Anagrafica | auditor1 / auditee1 | P1 |
| 06-08 | Risk Assessment | auditor1 / auditee1 | P1 |
| 09-12 | Piano di Audit | head_ia / auditee1 | P1 |
| 13-17 | Engagement + AI | auditor1 | P1 ⚠️ richiede API key OpenAI |
| 18-23 | Findings & Remediation | tutti | P1 |
| 24-29 | Reporting | head_ia | P2 |
| 30-31 | Auth / Sessioni | tutti | P1 |

> **TC-14** richiede `OPENAI_API_KEY` configurata nel file `.env`. Se assente, la verifica AI non partirà; si può comunque testare TC-15/16 usando un engagement con verifica già salvata da sessione precedente.

---

## Criteri di accettazione

- Tutti i TC P1 devono passare senza errori a console
- I PDF scaricati devono essere apribili e contenere dati reali
- Nessuna azione di scrittura deve essere accessibile all'utente `auditee1` dove non previsto
- L'Audit Log deve registrare ogni operazione di create/update eseguita durante il test
