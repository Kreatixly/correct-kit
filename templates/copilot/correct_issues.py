#!/usr/bin/env python3
"""correct-kit: class issues and the weekly agenda for the team-triage loop.

    correct_issues.py known --issues issues.json
    correct_issues.py drift --config weekly.json --since YYYY-MM-DD
    correct_issues.py plan  --config weekly.json --issues issues.json --today YYYY-MM-DD
                            [--model analysis.md] [--models-enabled true] [--drift drift.json]
                            [--run-url URL]
    correct_issues.py apply --config weekly.json --plan plan.json [--dry-run]

The model only fills fields (JSON). This script validates and shortens them and renders every
issue from fixed templates, so an issue cannot grow to hundreds of lines or mix classes: one
issue is one class is one wrong move is one pull request. `apply` is the only part that writes
to GitHub (through `gh`). Standard library only.

Class issue body: `<!-- correct-class: <slug> -->` and `<!-- correct-state {json} -->` (fields
and known occurrences). Episodes recorded locally by `/correct log` arrive as comments carrying
`<!-- correct-episode {json} -->`; this run folds them into the state.
"""
import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import subprocess
import sys

TRIAGE, ACCEPT, REJECT, QUIET, REPORT = (
    "correct:triage", "correct:umsetzen", "correct:verworfen", "correct:ruhig", "correct-report")
LABELS = [
    (TRIAGE, "fbca04", "Fehlerklasse wartet auf Team-Entscheidung (correct-kit)"),
    (ACCEPT, "0e8a16", "Fehlerklasse wird umgesetzt (correct-kit)"),
    (REJECT, "b60205", "Fehlerklasse verworfen; ohne neue Belege nicht wieder vorschlagen"),
    (QUIET, "cccccc", "Fehlerklasse ohne Vorkommen geschlossen (correct-kit)"),
    (REPORT, "5319e7", "Wöchentliche Tagesordnung (correct-kit)"),
]
LEVELS = {"architecture": "Architektur", "types": "Typ", "lint": "Lint/CI", "test": "Test",
          "docs": "Doku"}
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CLASS_RE = re.compile(r"<!-- correct-class: ([a-z0-9-]+) -->")
STATE_RE = re.compile(r"<!-- correct-state (\{.*?\}) -->", re.S)
EPISODE_RE = re.compile(r"<!-- correct-episode (\{.*?\}) -->", re.S)
COUNTER_RE = re.compile(r"^\*\*Vorkommen:\*\*.*$", re.M)
TABLE_ROWS, MAX_STORED, SECTION_LINES, MAX_DRIFT = 5, 50, 15, 10


# ── text ─────────────────────────────────────────────────────────────────────

def clip(value, limit):
    """One line, at most `limit` characters, safe inside Markdown tables and comments."""
    text = " ".join(str(value or "").split())
    text = text.replace("<", "&lt;").replace("|", "/").replace("@", "@​")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def hidden(tag, data):
    # `>` escaped so the JSON can never close the HTML comment early.
    return f"<!-- {tag} " + json.dumps(data, ensure_ascii=False).replace(">", "\\u003e") + " -->"


def parse_hidden(regex, text):
    out = []
    for m in regex.finditer(text or ""):
        try:
            out.append(json.loads(m.group(1)))
        except ValueError:
            pass
    return out


# ── normalisation ────────────────────────────────────────────────────────────

def key(occ):
    return occ["ref"].lower()


def norm_occ(o):
    if not isinstance(o, dict):
        return None
    ref = clip(o.get("ref"), 120)
    if not ref:
        return None
    date = str(o.get("date") or "")
    return {"date": date if DATE_RE.match(date) else "", "source": clip(o.get("source"), 30),
            "ref": ref, "what": clip(o.get("what"), 120), "author": clip(o.get("author"), 40)}


def dedupe(occs):
    seen, out = set(), []
    for o in occs:
        if o and key(o) not in seen:
            seen.add(key(o))
            out.append(o)
    return out


def norm_class(c):
    if not isinstance(c, dict):
        return None
    slug = str(c.get("slug") or "").strip().lower()
    if not SLUG_RE.match(slug) or len(slug) > 50:
        return None
    level = str(c.get("level") or "").strip().lower()
    return {
        "slug": slug,
        "title": clip(c.get("title") or slug, 80),
        "wrong_move": clip(c.get("wrong_move"), 300),
        "why_plausible": clip(c.get("why_plausible"), 200),
        "level": level if level in LEVELS else "",
        "level_detail": clip(c.get("level_detail"), 250),
        "why_not_higher": clip(c.get("why_not_higher"), 250),
        "test_case": clip(c.get("test_case"), 150),
        "occurrences": dedupe([norm_occ(o) for o in (c.get("occurrences") or [])][:30]),
    }


def parse_model(text):
    if not text or not text.strip():
        return None
    t = text.strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i:
        return None
    try:
        data = json.loads(t[i: j + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def load_issue(issue):
    body = issue.get("body") or ""
    m = CLASS_RE.search(body)
    if not m:
        return None
    states = parse_hidden(STATE_RE, body)
    state = states[0] if states and isinstance(states[0], dict) else {}
    texts = [body] + [c.get("body") or "" for c in issue.get("comments") or []]
    episodes = [norm_occ(e) for t in texts for e in parse_hidden(EPISODE_RE, t)]
    return {
        "number": issue["number"],
        "slug": m.group(1),
        "title": issue.get("title") or "",
        "open": issue.get("state") == "OPEN",
        "reason": (issue.get("stateReason") or "").upper(),
        "labels": {lb.get("name") for lb in issue.get("labels") or []},
        "created": (issue.get("createdAt") or "")[:10],
        "closed": (issue.get("closedAt") or "")[:10],
        "state": state,
        "episodes": dedupe(episodes),
    }


# ── rendering ────────────────────────────────────────────────────────────────

def authors(occs):
    return len({o["author"] for o in occs if o.get("author")})


def last_seen(occs, fallback=""):
    dates = [o["date"] for o in occs if o.get("date")]
    return max(dates) if dates else fallback


def counter_line(state):
    occs = state.get("occurrences", [])
    dev = authors(occs)
    return (f"**Vorkommen:** {state.get('total', len(occs))}"
            + (f" · **Entwickler:** {dev}" if dev else "")
            + f" · **Zuletzt gesehen:** {last_seen(occs) or '–'}")


def table(occs, total=None):
    rows = sorted(occs, key=lambda o: o.get("date") or "", reverse=True)
    lines = ["| Datum | Quelle | Was |", "|---|---|---|"]
    lines += [f"| {o['date'] or '–'} | {o['source']} {o['ref']}".rstrip() + f" | {o['what']} |"
              for o in rows[:TABLE_ROWS]]
    more = (total if total is not None else len(rows)) - min(len(rows), TABLE_ROWS)
    if more > 0:
        lines.append(f"\n(+ {more} weitere)")
    return lines


def class_body(state, cfg):
    proof = proof_heading(cfg)
    level = LEVELS.get(state.get("level"), "unklar")
    detail = state.get("level_detail")
    test_case = state.get("test_case") or "⚠️ kein Prüffall gefunden – Nachweis schwer, bitte im Team prüfen"
    lines = [
        f"<!-- correct-class: {state['slug']} -->",
        hidden("correct-state", state),
        f"**Falscher Zug:** {state.get('wrong_move') or '–'}",
        f"**Warum lokal plausibel:** {state.get('why_plausible') or '–'}",
        counter_line(state),
        "",
        *table(state.get("occurrences", []), state.get("total")),
        "",
        f"**Vorgeschlagene Stufe:** {level}" + (f" — {detail}" if detail else ""),
        f"**Warum nicht höher:** {state.get('why_not_higher') or '–'}",
        f"**Prüffall für den Nachweis:** {test_case}",
        "",
        "### Akzeptanzkriterien (für die Umsetzung, auch durch Copilot)",
        "- [ ] Check ist **rot** auf dem Prüffall, mit einer Meldung, die den richtigen Weg nennt",
        "- [ ] Check ist **grün** auf dem aktuellen Stand (oder Altfälle per Baseline, die nur schrumpft)",
        "- [ ] **Keine Fehlalarme:** alle Treffer im Repo geprüft und im PR aufgelistet",
        "- [ ] Check läuft in den Verify-Kommandos (lokal = CI)",
        "- [ ] Regeltabelle aktualisiert; die Prosa-Regel wird zum Verweis",
        f"- [ ] PR mit `Closes #<dieses Issue>` und Abschnitt `## {proof}` (Befehle und Ausgabe)",
        "",
        f"**Team-Entscheidung:** Label `{ACCEPT}` → Copilot zuweisen oder lokal "
        f"`/correct apply {state['slug']}`. Verwerfen → Label `{REJECT}` und als „not planned“ schließen.",
    ]
    return "\n".join(lines) + "\n"


def update_body(body, state):
    """Only the state and the counter line change, so team edits to the text survive."""
    body = STATE_RE.sub(lambda _: hidden("correct-state", state), body, count=1)
    if not STATE_RE.search(body):
        body = hidden("correct-state", state) + "\n" + body
    if COUNTER_RE.search(body):
        return COUNTER_RE.sub(counter_line(state), body, count=1)
    return body.rstrip("\n") + "\n\n" + counter_line(state) + "\n"


def episodes_comment(new, state, prefix=""):
    head = f"**Neue Vorkommen ({len(new)})** · gesamt {state['total']} · zuletzt {last_seen(new) or '–'}"
    return "\n".join(([prefix, ""] if prefix else []) + [head, ""] + table(new)) + "\n"


def proof_heading(cfg):
    return (cfg.get("proof_terms") or "Nachweis").split("|")[0].strip() or "Nachweis"


# ── plan ─────────────────────────────────────────────────────────────────────

def merge_state(state, fields, new):
    merged = dict(state)
    for k, v in (fields or {}).items():
        if k != "occurrences" and v and not merged.get(k):
            merged[k] = v  # the model fills gaps; it never overwrites what is there
    known = dedupe(list(state.get("occurrences", [])) + new)
    merged["occurrences"] = sorted(known, key=lambda o: o.get("date") or "")[-MAX_STORED:]
    merged["total"] = int(state.get("total", len(state.get("occurrences", [])))) + len(new)
    return merged


def plan(cfg, issues, model_text, models_enabled, drift, today, run_url=""):
    min_occ, max_new = int(cfg.get("min_occurrences", 2)), int(cfg.get("max_new", 3))
    stale_days = int(cfg.get("stale_days", 90))
    stale_before = (dt.date.fromisoformat(today) - dt.timedelta(days=stale_days)).isoformat()
    existing = {}
    for i in issues:
        loaded = load_issue(i)
        if loaded and loaded["slug"] not in existing:
            existing[loaded["slug"]] = loaded

    model = parse_model(model_text)
    status = "off" if not models_enabled else ("ok" if model is not None else "invalid")
    fields, watch = {}, []
    for c in (model or {}).get("classes") or []:
        n = norm_class(c)
        if n and n["slug"] not in fields:
            fields[n["slug"]] = n
    for w in ((model or {}).get("watch") or [])[:SECTION_LINES]:
        if isinstance(w, dict) and w.get("what"):
            watch.append(clip(w.get("what"), 100) + (f" ({clip(w.get('ref'), 40)})" if w.get("ref") else ""))

    actions = []
    agenda = {"decide": [], "relapse": [], "rejected_new": [], "in_progress": [], "quiet": [],
              "watch": watch, "drift": (drift or [])[:MAX_DRIFT], "models": status,
              "run_url": run_url, "today": today}

    prefix = cfg.get("title_prefix", "")

    def item(ref, title, state, note):
        occs = state.get("occurrences", [])
        if prefix and title.startswith(prefix):
            title = title[len(prefix):]
        return {"ref": ref, "title": clip(title, 80), "count": state.get("total", len(occs)),
                "devs": authors(occs), "level": LEVELS.get(state.get("level"), "unklar"), "note": note}

    for slug, ex in sorted(existing.items(), key=lambda kv: kv[1]["number"]):
        incoming = ex["episodes"] + (fields.get(slug, {}).get("occurrences") or [])
        known = {key(o) for o in ex["state"].get("occurrences", [])}
        new = dedupe([o for o in incoming if key(o) not in known])
        if not ex["open"]:
            # A closed class only counts what happened after it was closed (dated), so evidence
            # the model finds late for the old period does not look like a relapse.
            new = [o for o in new if o["date"] and o["date"] > ex["closed"]]
        ref = {"number": ex["number"]}
        if not new:
            seen = last_seen(ex["state"].get("occurrences", []), ex["created"])
            if ex["open"] and seen and seen < stale_before:
                actions.append({"op": "close_quiet", "number": ex["number"], "days": stale_days})
                agenda["quiet"].append(ex["number"])
            elif ex["open"] and TRIAGE in ex["labels"]:
                agenda["decide"].append(item(ref, ex["title"], ex["state"], "offen"))
            continue
        state = merge_state(dict(ex["state"], slug=slug), fields.get(slug), new)
        if ex["open"]:
            actions.append({"op": "update", "number": ex["number"], "state": state,
                            "comment": episodes_comment(new, state)})
            if ACCEPT in ex["labels"]:
                agenda["in_progress"].append(item(ref, ex["title"], state, f"+{len(new)} neu"))
            else:
                agenda["decide"].append(item(ref, ex["title"], state, f"+{len(new)} neu"))
        elif ex["reason"] == "COMPLETED":
            actions.append({"op": "update", "number": ex["number"], "state": state,
                            "reopen": True, "add": [TRIAGE], "remove": [ACCEPT, QUIET],
                            "comment": episodes_comment(new, state, "**Rückfall:** Die Klasse war als "
                                                        "erledigt geschlossen; der Fix hat diese Fälle nicht verhindert.")})
            agenda["relapse"].append(item(ref, ex["title"], state, f"+{len(new)} neu"))
        elif REJECT in ex["labels"]:
            actions.append({"op": "update", "number": ex["number"], "state": state,
                            "comment": episodes_comment(new, state, "Neue Belege für eine verworfene Klasse.")})
            agenda["rejected_new"].append(item(ref, ex["title"], state, f"+{len(new)} neu"))
        else:
            actions.append({"op": "update", "number": ex["number"], "state": state,
                            "reopen": True, "add": [TRIAGE], "remove": [QUIET],
                            "comment": episodes_comment(new, state, "Wieder aufgetreten.")})
            agenda["decide"].append(item(ref, ex["title"], state, "wiederkehrend"))

    candidates = [f for s, f in fields.items() if s not in existing]
    candidates.sort(key=lambda f: (len(f["occurrences"]), last_seen(f["occurrences"])), reverse=True)
    created = 0
    for f in candidates:
        if len(f["occurrences"]) < min_occ:
            watch.append(f"{f['title']} ({len(f['occurrences'])}×)")
            continue
        if created >= max_new:
            watch.append(f"{f['title']} ({len(f['occurrences'])}×, Limit {max_new} neue pro Lauf)")
            continue
        created += 1
        state = merge_state({}, f, f["occurrences"])
        state.update(slug=f["slug"], total=len(f["occurrences"]))
        actions.append({"op": "create", "slug": f["slug"], "title": cfg.get("title_prefix", "") + f["title"],
                        "state": state})
        agenda["decide"].append(item({"slug": f["slug"]}, f["title"], state, "neu"))
    return {"actions": actions, "agenda": agenda}


def agenda_body(agenda, numbers, cfg):
    def ref(r):
        n = r.get("number") or numbers.get(r.get("slug"))
        return f"#{n}" if n else f"`{r.get('slug')}`"

    def section(title, lines):
        if not lines:
            return []
        shown = lines[:SECTION_LINES]
        more = [f"- … +{len(lines) - len(shown)} weitere"] if len(lines) > len(shown) else []
        return [f"**{title} ({len(lines)}):**", *shown, *more, ""]

    def fmt(i):
        devs = f", {i['devs']} Entwickler" if i["devs"] else ""
        return f"- {ref(i['ref'])} {i['title']} — {i['count']}×{devs} — {i['level']} — {i['note']}"

    out = []
    out += section("Zur Entscheidung", [fmt(i) for i in agenda["decide"]])
    out += section("Rückfall: Check hat nicht gehalten", [fmt(i) for i in agenda["relapse"]])
    out += section("Verworfen, aber neue Belege", [fmt(i) for i in agenda["rejected_new"]])
    out += section("In Umsetzung, neue Belege", [fmt(i) for i in agenda["in_progress"]])
    out += section("Abdrift: Regeln ohne Durchsetzung",
                   [f"- `{d['file']}` +„{d['rule']}“ ({d['commit']} {d['subject']})" for d in agenda["drift"]])
    if not out:
        out = ["Keine neuen Belege, nichts zu entscheiden.", ""]
    if agenda["watch"]:
        out.append(f"**Beobachten (Einzelfälle, kein Issue):** {len(agenda['watch'])} — "
                   + "; ".join(agenda["watch"][:5]) + (" …" if len(agenda["watch"]) > 5 else ""))
    if agenda["quiet"]:
        out.append(f"**Aufgeräumt ({cfg.get('stale_days', 90)} Tage ohne Vorkommen):** "
                   + ", ".join(f"#{n}" for n in agenda["quiet"]))
    models = {"ok": "GitHub Models (Entwurf, ohne Nachweis)",
              "off": "aus – nur lokal geloggte Episoden (CORRECT_MODELS_ENABLED)",
              "invalid": "⚠️ Antwort von GitHub Models war kein gültiges JSON – nur lokale Episoden"}[agenda["models"]]
    out += ["", f"Klassifizierung: {models} · Rohbelege: {agenda['run_url'] or '–'}",
            "",
            f"**Nächster Schritt:** im Team entscheiden. Umsetzen → Label `{ACCEPT}`, dann Copilot "
            f"zuweisen oder lokal `/correct apply <slug>`. Verwerfen → Label `{REJECT}`, als „not planned“ schließen. "
            "Der Nachweis (rot / grün / keine Fehlalarme) kommt im PR."]
    return "\n".join(out).rstrip() + "\n"


def agenda_title(cfg, today):
    year, week, _ = dt.date.fromisoformat(today).isocalendar()
    return f"{cfg.get('report_title', 'Fehlerklassen-Check')} W{week:02d}/{year}"


# ── drift ────────────────────────────────────────────────────────────────────

RULE_LINE = re.compile(r"^\s*([-*]|\d+\.)\s+\S")


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def check_patterns(policy_conf):
    pats = []
    try:
        with open(policy_conf, encoding="utf-8") as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if line.startswith("check:"):
                    pats.append(line.split(":", 1)[1].strip())
    except OSError:
        pass
    return pats


def drift(cfg, since):
    """Rules added to agent instructions by a commit that touched no check: prose without enforcement."""
    specs = [f":(glob){p}" for p in cfg.get("instruction_files", [])]
    checks = check_patterns(cfg.get("policy_conf", ".github/correct/correct_policy.conf"))
    if not specs:
        return []
    items = []
    for line in git("log", f"--since={since}", "--format=%H%x09%s", "--", *specs).splitlines():
        sha, _, subject = line.partition("\t")
        changed = git("show", "--name-only", "--format=", sha).split()
        if any(fnmatch.fnmatchcase(p, c) for p in changed for c in checks):
            continue
        current = ""
        for d in git("show", "-U0", "--format=", sha, "--", *specs).splitlines():
            if d.startswith("+++ "):
                current = d[6:] if d.startswith("+++ b/") else ""
            elif d.startswith("+") and current and RULE_LINE.match(d[1:]):
                items.append({"file": current, "rule": clip(d[1:].strip().lstrip("-*0123456789. "), 100),
                              "commit": sha[:7], "subject": clip(subject, 70)})
    return items[:MAX_DRIFT]


# ── apply ────────────────────────────────────────────────────────────────────

def gh(*args, stdin=None):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True, input=stdin).stdout.strip()


def apply(cfg, the_plan, dry_run=False):
    run = (lambda *a, stdin=None: print("gh", *a, file=sys.stderr) or "https://x/issues/0") if dry_run else gh
    label = cfg["correction_label"]
    if not dry_run:
        for name, color, desc in LABELS + [(label, "d93f0b", "Ein Agent wurde korrigiert (correct-kit)")]:
            subprocess.run(["gh", "label", "create", name, "--color", color, "--description", desc],
                           capture_output=True)
    numbers = {}
    for a in the_plan["actions"]:
        if a["op"] == "create":
            url = run("issue", "create", "--title", a["title"], "--label", label, "--label", TRIAGE,
                      "--body-file", "-", stdin=class_body(a["state"], cfg))
            numbers[a["slug"]] = url.rstrip("/").rsplit("/", 1)[-1]
        elif a["op"] == "update":
            n = str(a["number"])
            body = "" if dry_run else gh("issue", "view", n, "--json", "body", "--jq", ".body")
            run("issue", "edit", n, "--body-file", "-", stdin=update_body(body, a["state"]))
            if a.get("reopen"):
                run("issue", "reopen", n)
            for lb in a.get("add", []):
                run("issue", "edit", n, "--add-label", lb)
            for lb in a.get("remove", []):
                if not dry_run:  # removing a label the issue does not carry fails; that is fine
                    subprocess.run(["gh", "issue", "edit", n, "--remove-label", lb], capture_output=True)
            run("issue", "comment", n, "--body-file", "-", stdin=a["comment"])
        elif a["op"] == "close_quiet":
            n = str(a["number"])
            run("issue", "edit", n, "--add-label", QUIET)
            run("issue", "close", n, "--reason", "not planned",
                "--comment", f"Seit {a['days']} Tagen kein Vorkommen. Neue Belege öffnen das Issue wieder.")

    agenda = the_plan["agenda"]
    prev = [] if dry_run else gh("issue", "list", "--label", REPORT, "--state", "open",
                                 "--json", "number", "--jq", ".[].number").split()
    assign = ["--assignee", os.environ["CORRECT_REPORT_ASSIGNEE"]] if os.environ.get("CORRECT_REPORT_ASSIGNEE") else []
    url = run("issue", "create", "--label", REPORT, *assign, "--title", agenda_title(cfg, agenda["today"]),
              "--body-file", "-", stdin=agenda_body(agenda, numbers, cfg))
    for n in prev:
        run("issue", "close", n, "--reason", "not planned", "--comment", f"Ersetzt durch {url}.")
    print(url)


# ── cli ──────────────────────────────────────────────────────────────────────

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["known", "drift", "plan", "apply"])
    p.add_argument("--config")
    p.add_argument("--issues")
    p.add_argument("--model", default="")
    p.add_argument("--models-enabled", default="false")
    p.add_argument("--drift")
    p.add_argument("--since")
    p.add_argument("--today")
    p.add_argument("--run-url", default="")
    p.add_argument("--plan")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    load = lambda path, default: json.load(open(path, encoding="utf-8")) if path and os.path.exists(path) else default
    cfg = load(a.config, {})
    if a.command == "known":
        for i in load(a.issues, []):
            c = load_issue(i)
            if c:
                print(f"- {c['slug']}: {clip(c['title'], 80)}")
    elif a.command == "drift":
        json.dump(drift(cfg, a.since), sys.stdout, ensure_ascii=False, indent=1)
    elif a.command == "plan":
        model_text = open(a.model, encoding="utf-8").read() if a.model and os.path.exists(a.model) else ""
        json.dump(plan(cfg, load(a.issues, []), model_text, a.models_enabled == "true",
                       load(a.drift, []), a.today, a.run_url), sys.stdout, ensure_ascii=False, indent=1)
    else:
        apply(cfg, load(a.plan, {}), a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
