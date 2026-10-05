# correct-kit

**Korrigiere die Umgebung, nicht den Agenten.** Wenn ein KI-Agent denselben Fehler wiederholt,
bringt ihm das Repo diesen Fehler bei: ein Muster zum Kopieren, eine Regel nur als Prosa, ein
Check, den es nicht gibt. correct-kit macht daraus einen wöchentlichen Kreislauf: Fehler
belegen, zu Klassen bündeln, mit der stärksten möglichen Durchsetzung abstellen, als Draft-PR
vorlegen. Du mergst oder schließt.

Entstanden in [LernSnap](examples/lernsnap/) (Flutter), angelehnt an pstack von poteto.
Läuft mit **Claude Code** (vollautomatisch über GitHub Actions) oder mit **GitHub Copilot**
(Belege automatisch, Umsetzung über den Copilot Coding Agent).

## Die Methode

**Die Leiter** — jede Fehlerklasse auf der höchsten Stufe beheben, die sie wirklich verhindert:

1. **Architektur** — der falsche Weg existiert nicht mehr (ein Ort, ein Modul)
2. **Typ** — der falsche Weg kompiliert nicht (privater Konstruktor, eigener Typ)
3. **Lint/CI** — ein Architekturtest oder eine Regel schlägt an, mit einer Meldung, die den richtigen Weg nennt
4. **Test** — Verhalten festgenagelt
5. **Doku** — nur für Ermessensfragen

**Nachweis** — ein Fix zählt erst, wenn der Check auf dem historischen Fehler **rot**, heute
**grün** und ohne **Fehlalarme** ist. Dazu zwei, drei naheliegende Umgehungen rot machen, nicht
nur den alten Diff.

**Belege statt Gefühl** — eine Klasse braucht mindestens zwei unabhängige Vorkommen:
Review-Kommentare, Reverts und Fix-ups, Korrektur-Issues (Label `agent-mistake`), lokale
Chatverläufe über `/recall`.

## Der Wochenablauf

| Wann | Baustein | Darf | Ergebnis |
|---|---|---|---|
| laufend | automatisches Review auf PRs | kommentieren | Befunde = wichtigste Belege |
| laufend | Label `agent-mistake`, lokal `/recall` | Issues | ein Issue pro Fehlerklasse |
| wöchentlich | `correct-weekly` | nur lesen | **ein** Bericht-Issue: Klassen, neu / wiederkehrend / Rückfall, vorgeschlagene Ebene |
| danach | `correct-act` (Claude, Kill-Switch) | Draft-PR | Auswahl 🤖 auto / 👤 owner / ✖ skip als Kommentar; je 🤖-Klasse Umsetzung mit Nachweis, Gate, Draft-PR |
| du | mergen oder schließen | Freigabe | Merge = Freigabe; Schließen = abgelehnt, wird ohne neue Belege nicht wieder vorgeschlagen |

Bei Copilot ersetzt der Copilot Coding Agent `correct-act`: Du (oder ein Workflow) weist ihm ein
Klassen-Issue zu, er öffnet einen PR, die Pflicht-Prüfung `correct-policy` hält ihn im Rahmen.

## Konstruktionsregeln (teuer gelernt)

1. **Das Modell liest, der Workflow schreibt.** Issues, Pushes, PRs legt ein Workflow-Schritt ohne Modell an.
2. **Grenzen in Skript und Rechten, nicht im Prompt.** `correct_policy.sh` prüft Pfade, Größe, Tests, Muster der harten Regeln. Gate mit Lese-Token; Publish mit Schreibrechten, aber ohne Repo-Code. Das Policy-Skript liegt in `.github/` und ist damit selbst gesperrt.
3. **Jede Autonomiestufe hat Kill-Switch und Probezeit** (Repo-Variable; am Ende zählen: gemergt / verworfen / Fehlalarm).
4. **„Grün“ heißt nicht „geprüft“.** Jeder Lauf hat ein sichtbares Ergebnis oder ein Fallback-Issue.
5. **Headless-Fallen:** Unteragenten im Vordergrund (`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, mit Wächter-Test); Werkzeug-Allowlist passend zum Kommando; geänderte Workflows wirken erst nach dem Merge.
6. **Tracker klein halten:** ein Issue pro Klasse, ein offener Bericht; Erledigtes schließt der Fix-PR per `Closes #n`.
7. **Erst nachsehen, dann anlegen:** bestehende ADRs, Glossar, Kontext und Agenten-Anweisungen werden erweitert, nicht dupliziert.

## Installation

### Claude Code

```text
/plugin marketplace add Kreatixly/correct-kit
/plugin install correct-kit@correct-kit
```

Dann im Ziel-Repo: **„Richte correct-kit ein“** (Skill `correct-setup`). Das Setup fragt zuerst
nach dem Ziel (Claude Code, GitHub Copilot oder beides), macht eine Bestandsaufnahme und legt
alles als **einen Draft-PR** an.

### GitHub Copilot (ohne Claude)

Repo klonen oder als Ordner neben das Ziel-Repo legen und im Copilot-Chat (Agent-Modus) im
Ziel-Repo ausführen:

```text
Lies <pfad-zu-correct-kit>/skills/correct-setup/SKILL.md und folge ihm. Ziel: GitHub Copilot.
```

Copilot-Dateinamen und -Funktionen (Prompt-Dateien, Coding Agent, GitHub Models) ändern sich
zwischen GitHub-Versionen; das Setup prüft sie gegen die aktuelle Doku deiner GitHub-Variante.

## Inhalt

| Pfad | Was |
|---|---|
| `skills/correct/` | `/correct` (Analyse), `/correct init`, `/correct apply <Klasse>` |
| `skills/architect/` | Schnittstelle zuerst, agentenfreundliches Design |
| `skills/recall/` | Korrekturen aus lokalen Claude-Code-Chatverläufen (nur CLI, lokal) |
| `skills/correct-setup/` | Installation in ein Repo |
| `templates/contract.md` | Projektvertrag (alles Projektspezifische an einem Ort) |
| `templates/policy/` | `correct_policy.sh` + Konfiguration |
| `templates/claude/workflows/` | `correct-weekly`, `correct-act`, `claude-code-review` |
| `templates/copilot/` | Workflows, Prompt-Dateien, Instructions |
| `templates/adr/`, `templates/docs/`, `templates/guards/` | Entscheidungs-, Doku- und Wächter-Vorlagen |
| `scripts/render.py` | füllt Platzhalter, verweigert halb gefüllte Dateien |
| `examples/lernsnap/` | vollständige Werte, Policy und Wächter-Test aus dem Ursprungsprojekt |
| `tests/selftest.sh` | Render-, YAML-, Shell- und Policy-Prüfung des Kits |

## Was du selbst tun musst

- Claude: Secret `CLAUDE_CODE_OAUTH_TOKEN`; Actions-Einstellung „Allow GitHub Actions to create
  and approve pull requests“; Repo-Variable `CORRECT_ACT_ENABLED=true`, wenn Auto-PRs starten sollen.
- Copilot: `correct-policy` als Pflicht-Prüfung; Coding Agent aktiv, Workflows auf seinen PRs
  erlaubt; optional `CORRECT_MODELS_ENABLED=true` für GitHub Models.
- Nach dem Merge: `correct-weekly` einmal von Hand starten und den Bericht lesen.

## Grenzen

- Für GitHub gebaut (github.com; GHE.com und GHES mit Prüfung im Setup).
- Toolchain-Setup und Wächter-Test werden pro Stack erzeugt; der erste Lauf in einem neuen
  Stack braucht einen Blick von dir.
- Die Copilot-Variante ist halbautomatisch: Die Analyse der Woche stößt du im Chat an.
