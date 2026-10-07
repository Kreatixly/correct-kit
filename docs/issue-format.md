# Issues der Team-Triage (GitHub Copilot)

Was der Wochenlauf im Tracker anlegt, wie lang es wird und wer was entscheidet. Die Beispiele
unten sind echte Ausgaben von `templates/copilot/correct_issues.py` (Testdaten aus LernSnap).

## Grundregeln

- **Ein Issue = eine Klasse = ein falscher Zug = ein PR.** Jedes Klassen-Issue ist so
  geschnitten, dass man es direkt an Copilot zuweisen kann; die Beschreibung ist der Auftrag.
- **Das Modell füllt Felder, das Skript schreibt.** GitHub Models liefert nur JSON (Slug, Satz,
  Stufe, Belege). Das Skript prüft und kürzt jedes Feld und setzt das Issue aus einer festen
  Vorlage zusammen. Hunderte Zeilen oder vermischte Klassen sind so nicht möglich.
- **Beleg vor der Entscheidung, Nachweis im PR.** Das Issue zeigt, dass das Problem echt ist
  (mindestens 2 Vorkommen, ein Prüffall). Dass der Fix hält (rot / grün / keine Fehlalarme),
  zeigt der PR; der Pflicht-Check `correct-policy` verlangt den Abschnitt.

## Mengen

| Was | Grenze |
|---|---|
| Tagesordnung | genau 1 offen, höchstens ~40 Zeilen, je Abschnitt 15 Einträge |
| neue Klassen-Issues pro Lauf | höchstens 3 (`max_new`), häufigste zuerst; Rest unter „Beobachten“ |
| bekannte Klassen | 1 Kommentar pro Lauf (≤ 10 Zeilen), kein neues Issue |
| Einzelfälle | kein Issue, nur eine Zeile „Beobachten“ |
| Klassen-Issue | ~30 sichtbare Zeilen; Tabelle zeigt die letzten 5 Vorkommen |
| ruhige Klassen | nach 90 Tagen ohne Vorkommen geschlossen (`correct:ruhig`) |

Grenzen stehen in `.github/correct/weekly.json`; die Tests in `tests/test_correct_issues.py`
prüfen sie.

## Lebenslauf eines Klassen-Issues

| Zustand | Label | Was passiert bei neuen Belegen |
|---|---|---|
| offen, wartet aufs Team | `correct:triage` | Kommentar, Zähler steigt, Eintrag in „Zur Entscheidung“ |
| angenommen | `correct:umsetzen` | Kommentar, Eintrag „In Umsetzung, neue Belege“ |
| erledigt (PR gemergt, `Closes #n`) | – | **Rückfall:** wieder geöffnet, zurück in die Triage |
| verworfen | `correct:verworfen` | bleibt zu; Eintrag „Verworfen, aber neue Belege“ |
| ruhig geschlossen | `correct:ruhig` | wieder geöffnet als „wiederkehrend“ |

Bei geschlossenen Klassen zählen nur Vorkommen nach dem Schließdatum, damit spät gefundene alte
Belege keinen Rückfall vortäuschen.

## Beispiel: Klassen-Issue

Titel: `Fehlerklasse: Rohe Fehlertexte im UI` · Labels: `agent-mistake`, `correct:triage`

```markdown
<!-- correct-class: raw-error-text -->
<!-- correct-state {…Felder und bekannte Vorkommen, unsichtbar…} -->
**Falscher Zug:** Fehler werden mit `e.toString()` direkt in SnackBar/Dialog angezeigt statt über `userMessage(e)` aus `lib/core/errors.dart`.
**Warum lokal plausibel:** Im Screen fehlt jeder Hinweis auf `userMessage`; die nächste Kopiervorlage (`settings_screen.dart`) macht es selbst falsch.
**Vorkommen:** 4 · **Entwickler:** 3 · **Zuletzt gesehen:** 2026-10-02

| Datum | Quelle | Was |
|---|---|---|
| 2026-10-02 | review #212 | SnackBar mit e.toString() im Upload-Screen |
| 2026-09-28 | /correct log 2026-09-28/feature-login/1 | Dialog zeigt Exception-Text beim Login |
| 2026-09-24 | revert a1b2c3d | Fehlertext im Quiz-Screen zurückgenommen |
| 2026-09-15 | review #187 | gleiches Muster im Profil |

**Vorgeschlagene Stufe:** Lint/CI — Architekturtest: kein `.toString()` auf Exceptions in `lib/features/**/ui/`; Meldung nennt `userMessage(e)`.
**Warum nicht höher:** Ein eigener Fehlertyp in allen Services wäre groß; als Folgeschritt möglich.
**Prüffall für den Nachweis:** a1b2c3d (vor dem Revert), PR #212

### Akzeptanzkriterien (für die Umsetzung, auch durch Copilot)
- [ ] Check ist **rot** auf dem Prüffall, mit einer Meldung, die den richtigen Weg nennt
- [ ] Check ist **grün** auf dem aktuellen Stand (oder Altfälle per Baseline, die nur schrumpft)
- [ ] **Keine Fehlalarme:** alle Treffer im Repo geprüft und im PR aufgelistet
- [ ] Check läuft in den Verify-Kommandos (lokal = CI)
- [ ] Regeltabelle aktualisiert; die Prosa-Regel wird zum Verweis
- [ ] PR mit `Closes #<dieses Issue>` und Abschnitt `## Nachweis` (Befehle und Ausgabe)

**Team-Entscheidung:** Label `correct:umsetzen` → Copilot zuweisen oder lokal `/correct apply raw-error-text`. Verwerfen → Label `correct:verworfen` und als „not planned“ schließen.
```

Fehlt ein Prüffall, steht dort „⚠️ kein Prüffall gefunden – Nachweis schwer“: ein Signal für die
Entscheidung. Änderungen des Teams am sichtbaren Text bleiben erhalten; der Lauf ändert danach
nur den unsichtbaren Zustand und die Zeile „Vorkommen“.

## Beispiel: Kommentar bei neuen Belegen

```markdown
**Neue Vorkommen (1)** · gesamt 3 · zuletzt 2026-10-04

| Datum | Quelle | Was |
|---|---|---|
| 2026-10-04 | /correct log 2026-10-04/feature-quiz/1 | Prompt im Quiz-Service hart kodiert |
```

## Beispiel: Tagesordnung

Titel: `Fehlerklassen-Check W41/2026` · Label: `correct-report` (die vorige wird geschlossen)

```markdown
**Zur Entscheidung (3):**
- #198 Prompts außerhalb der Prompt-Registry — 3×, 3 Entwickler — Architektur — +1 neu
- #231 Rohe Fehlertexte im UI — 4×, 3 Entwickler — Lint/CI — neu
- #232 Provider ohne autoDispose in Screens — 2×, 2 Entwickler — Lint/CI — neu

**Rückfall: Check hat nicht gehalten (1):**
- #176 Navigator.push statt go_router — 3×, 1 Entwickler — Lint/CI — +1 neu

**Abdrift: Regeln ohne Durchsetzung (1):**
- `.github/copilot-instructions.md` +„Keine Strings im Widget-Baum“ (9f8e7d6 Hinweis zu l10n ergänzt (#219))

**Beobachten (Einzelfälle, kein Issue):** 1 — Falscher Import-Pfad (1×)

Klassifizierung: GitHub Models (Entwurf, ohne Nachweis) · Rohbelege: https://github.com/org/app/actions/runs/123

**Nächster Schritt:** im Team entscheiden. Umsetzen → Label `correct:umsetzen`, dann Copilot zuweisen oder lokal `/correct apply <slug>`. Verwerfen → Label `correct:verworfen`, als „not planned“ schließen. Der Nachweis (rot / grün / keine Fehlalarme) kommt im PR.
```

**Abdrift** braucht kein Modell: Regeln (Aufzählungspunkte), die seit dem letzten Lauf in die
Agenten-Anweisungen kamen, mit einem Commit, der keinen Check (`check:` in der Policy) berührt.
Die Rohbelege stehen in der Zusammenfassung des Workflow-Laufs, nicht im Issue.

## Beispiel: Nachweis im PR

```markdown
Closes #231

## Nachweis

- **Rot** auf a1b2c3d: `flutter test test/arch/errors_test.dart` → 1 Fehler: „use userMessage(e)“
- **Grün** auf HEAD: 0 Fehler
- **Fehlalarme:** 14 Treffer geprüft, alle echt; Baseline mit 9 Altfällen
```

`check_proof.sh` prüft nur, dass der Abschnitt existiert und rot, grün und Fehlalarme nennt.
Ob der Nachweis stimmt, seht ihr im Review.
