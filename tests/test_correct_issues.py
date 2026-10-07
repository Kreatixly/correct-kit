"""Tests for templates/copilot/correct_issues.py: the model fills fields, the script decides
what becomes an issue and how long it may get."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "templates", "copilot"))
import correct_issues as ci  # noqa: E402

CFG = {"correction_label": "agent-mistake", "title_prefix": "Fehlerklasse: ",
       "report_title": "Fehlerklassen-Check", "min_occurrences": 2, "max_new": 3,
       "stale_days": 90, "proof_terms": "Nachweis|rot|grün|Fehlalarm"}
TODAY = "2026-10-09"


def occ(ref, date="2026-10-01", author="dev1"):
    return {"date": date, "source": "review", "ref": ref, "what": "SnackBar zeigt e.toString()",
            "author": author}


def cls(slug, *refs, **extra):
    c = {"slug": slug, "title": slug.replace("-", " "), "wrong_move": "Zeigt rohe Fehlertexte",
         "why_plausible": "Vorlage macht es so", "level": "lint",
         "level_detail": "Architekturtest", "why_not_higher": "zu groß", "test_case": "a1b2c3d",
         "occurrences": [occ(r, author=f"dev{i}") for i, r in enumerate(refs)]}
    c.update(extra)
    return c


def model(*classes, watch=()):
    return json.dumps({"classes": list(classes), "watch": list(watch)})


def issue(number, slug, state_occ, state="OPEN", reason=None, labels=("agent-mistake", ci.TRIAGE),
          comments=(), closed="", created="2026-09-01"):
    st = {"slug": slug, "wrong_move": "x", "level": "lint", "occurrences": state_occ,
          "total": len(state_occ)}
    body = ci.class_body(st, CFG)
    return {"number": number, "title": f"Fehlerklasse: {slug}", "state": state, "stateReason": reason,
            "body": body, "labels": [{"name": n} for n in labels], "createdAt": created + "T00:00:00Z",
            "closedAt": (closed + "T00:00:00Z") if closed else None,
            "comments": [{"body": c} for c in comments]}


def ops(p, op):
    return [a for a in p["actions"] if a["op"] == op]


class NewClasses(unittest.TestCase):
    def test_two_occurrences_create_one_issue(self):
        p = ci.plan(CFG, [], model(cls("raw-error-text", "#212", "#187")), True, [], TODAY)
        self.assertEqual(len(ops(p, "create")), 1)
        self.assertEqual(ops(p, "create")[0]["title"], "Fehlerklasse: raw error text")
        self.assertEqual(p["agenda"]["decide"][0]["note"], "neu")

    def test_single_occurrence_goes_to_watch_list(self):
        p = ci.plan(CFG, [], model(cls("one-off", "#1")), True, [], TODAY)
        self.assertEqual(ops(p, "create"), [])
        self.assertIn("one off (1×)", p["agenda"]["watch"])

    def test_duplicate_refs_count_once(self):
        p = ci.plan(CFG, [], model(cls("dup", "#5", "#5")), True, [], TODAY)
        self.assertEqual(ops(p, "create"), [])

    def test_at_most_max_new_per_run_most_frequent_first(self):
        classes = [cls(f"c{i}", *[f"#{i}{k}" for k in range(2 + i)]) for i in range(5)]
        p = ci.plan(CFG, [], model(*classes), True, [], TODAY)
        self.assertEqual([a["slug"] for a in ops(p, "create")], ["c4", "c3", "c2"])
        self.assertEqual(len([w for w in p["agenda"]["watch"] if "Limit" in w]), 2)

    def test_invalid_slug_is_dropped(self):
        p = ci.plan(CFG, [], model(cls("Not A Slug", "#1", "#2")), True, [], TODAY)
        self.assertEqual(ops(p, "create"), [])

    def test_invalid_model_answer_is_reported_not_fatal(self):
        p = ci.plan(CFG, [], "Sorry, I cannot help with that.", True, [], TODAY)
        self.assertEqual(p["agenda"]["models"], "invalid")
        self.assertIn("kein gültiges JSON", ci.agenda_body(p["agenda"], {}, CFG))

    def test_model_json_in_code_fence_is_accepted(self):
        text = "```json\n" + model(cls("fenced", "#1", "#2")) + "\n```"
        p = ci.plan(CFG, [], text, True, [], TODAY)
        self.assertEqual(len(ops(p, "create")), 1)


class BodyLimits(unittest.TestCase):
    def test_body_stays_short_whatever_the_model_writes(self):
        long = "sehr lang " * 500
        c = cls("long", *[f"#{i}" for i in range(30)], wrong_move=long, why_not_higher=long,
                level_detail="a\n" * 200)
        p = ci.plan(CFG, [], model(c), True, [], TODAY)
        body = ci.class_body(ops(p, "create")[0]["state"], CFG)
        visible = [ln for ln in body.splitlines() if not ln.startswith("<!--")]
        self.assertLessEqual(len(visible), 35)
        self.assertTrue(all(len(ln) <= 400 for ln in visible))
        self.assertIn("(+ 25 weitere)", body)

    def test_model_text_cannot_inject_markers_or_mentions(self):
        c = cls("inject", "#1", "#2", wrong_move="<!-- correct-class: other --> @everyone | x")
        body = ci.class_body(ci.plan(CFG, [], model(c), True, [], TODAY)["actions"][0]["state"], CFG)
        self.assertEqual(ci.CLASS_RE.findall(body), ["inject"])
        self.assertNotIn("@everyone", body)

    def test_state_round_trips_through_the_body(self):
        st = ci.plan(CFG, [], model(cls("rt", "#1", "#2")), True, [], TODAY)["actions"][0]["state"]
        loaded = ci.load_issue({"number": 9, "body": ci.class_body(st, CFG), "state": "OPEN"})
        self.assertEqual(loaded["slug"], "rt")
        self.assertEqual({o["ref"] for o in loaded["state"]["occurrences"]}, {"#1", "#2"})

    def test_missing_test_case_is_flagged(self):
        st = ci.plan(CFG, [], model(cls("nt", "#1", "#2", test_case="")), True, [], TODAY)["actions"][0]["state"]
        self.assertIn("kein Prüffall", ci.class_body(st, CFG))

    def test_acceptance_criteria_name_the_proof_section(self):
        st = ci.plan(CFG, [], model(cls("ac", "#1", "#2")), True, [], TODAY)["actions"][0]["state"]
        self.assertIn("## Nachweis", ci.class_body(st, CFG))


class ExistingClasses(unittest.TestCase):
    def test_known_evidence_changes_nothing(self):
        p = ci.plan(CFG, [issue(7, "raw", [occ("#1"), occ("#2")])],
                    model(cls("raw", "#1", "#2")), True, [], TODAY)
        self.assertEqual(p["actions"], [])
        self.assertEqual(p["agenda"]["decide"][0]["note"], "offen")

    def test_new_evidence_is_one_comment_not_a_new_issue(self):
        p = ci.plan(CFG, [issue(7, "raw", [occ("#1"), occ("#2")])],
                    model(cls("raw", "#1", "#2", "#3")), True, [], TODAY)
        self.assertEqual(ops(p, "create"), [])
        [u] = ops(p, "update")
        self.assertEqual(u["state"]["total"], 3)
        self.assertLessEqual(len(u["comment"].splitlines()), 10)

    def test_local_episode_comment_is_folded_in_without_model(self):
        ep = ci.hidden("correct-episode", occ("2026-10-05/feature-x/1", "2026-10-05", "dev9"))
        p = ci.plan(CFG, [issue(7, "raw", [occ("#1"), occ("#2")], comments=[ep])], "", False, [], TODAY)
        [u] = ops(p, "update")
        self.assertEqual(u["state"]["total"], 3)
        self.assertEqual(p["agenda"]["models"], "off")

    def test_relapse_reopens_a_completed_class(self):
        old = issue(7, "raw", [occ("#1"), occ("#2")], state="CLOSED", reason="COMPLETED",
                    labels=("agent-mistake", ci.ACCEPT), closed="2026-09-20")
        p = ci.plan(CFG, [old], model(cls("raw", "#1", "#2", "#9")), True, [], TODAY)
        [u] = ops(p, "update")
        self.assertTrue(u["reopen"])
        self.assertIn(ci.TRIAGE, u["add"])
        self.assertEqual(len(p["agenda"]["relapse"]), 1)

    def test_old_evidence_found_late_is_no_relapse(self):
        old = issue(7, "raw", [occ("#1"), occ("#2")], state="CLOSED", reason="COMPLETED",
                    closed="2026-10-05")
        late = cls("raw", "#1", "#2")
        late["occurrences"].append(occ("#0", date="2026-08-01"))
        p = ci.plan(CFG, [old], model(late), True, [], TODAY)
        self.assertEqual(p["actions"], [])

    def test_rejected_class_is_not_reopened(self):
        rej = issue(7, "raw", [occ("#1"), occ("#2")], state="CLOSED", reason="NOT_PLANNED",
                    labels=("agent-mistake", ci.REJECT), closed="2026-09-20")
        p = ci.plan(CFG, [rej], model(cls("raw", "#1", "#2", "#9")), True, [], TODAY)
        [u] = ops(p, "update")
        self.assertFalse(u.get("reopen"))
        self.assertEqual(len(p["agenda"]["rejected_new"]), 1)

    def test_quiet_class_is_closed_after_stale_days(self):
        p = ci.plan(CFG, [issue(7, "raw", [occ("#1", "2026-06-01"), occ("#2", "2026-06-02")])],
                    "", False, [], TODAY)
        self.assertEqual(ops(p, "close_quiet")[0]["number"], 7)
        self.assertEqual(p["agenda"]["quiet"], [7])

    def test_update_keeps_team_edits_to_the_text(self):
        st = {"slug": "raw", "occurrences": [occ("#1")], "total": 1}
        body = ci.class_body(st, CFG).replace("**Falscher Zug:** –", "**Falscher Zug:** vom Team präzisiert")
        new = ci.update_body(body, dict(st, total=2, occurrences=[occ("#1"), occ("#2")]))
        self.assertIn("vom Team präzisiert", new)
        self.assertIn("**Vorkommen:** 2", new)


class Agenda(unittest.TestCase):
    def test_agenda_links_new_issues_and_stays_short(self):
        classes = [cls(f"c{i}", f"#{i}a", f"#{i}b") for i in range(3)]
        drift = [{"file": "AGENTS.md", "rule": f"Regel {i}", "commit": "abc1234", "subject": "docs"}
                 for i in range(30)]
        p = ci.plan(CFG, [], model(*classes, watch=[{"what": "einmalig", "ref": "#5"}]), True,
                    drift, TODAY, "https://run")
        body = ci.agenda_body(p["agenda"], {"c0": "31", "c1": "32", "c2": "33"}, CFG)
        self.assertIn("#31", body)
        self.assertIn("Abdrift", body)
        self.assertLessEqual(len(body.splitlines()), 40)

    def test_empty_week(self):
        p = ci.plan(CFG, [], "", False, [], TODAY)
        self.assertIn("Keine neuen Belege", ci.agenda_body(p["agenda"], {}, CFG))
        self.assertEqual(ci.agenda_title(CFG, TODAY), "Fehlerklassen-Check W41/2026")


class Drift(unittest.TestCase):
    def test_rule_without_check_is_drift_rule_with_check_is_not(self):
        with tempfile.TemporaryDirectory() as d:
            def git(*a):
                subprocess.run(["git", "-C", d, *a], check=True, capture_output=True)

            def write(path, text):
                os.makedirs(os.path.dirname(os.path.join(d, path)) or d, exist_ok=True)
                with open(os.path.join(d, path), "a", encoding="utf-8") as fh:
                    fh.write(text)

            git("init", "-q")
            git("config", "user.email", "t@example.com")
            git("config", "user.name", "t")
            write("pol.conf", "check: test/*\n")
            write("AGENTS.md", "# Regeln\n")
            git("add", "-A")
            git("commit", "-qm", "init")
            write("AGENTS.md", "- Keine Strings im Widget-Baum\n")
            git("commit", "-qam", "nur Prosa")
            write("AGENTS.md", "- Kein Navigator.push\n")
            write("test/nav_test.dart", "// check\n")
            git("add", "-A")
            git("commit", "-qm", "Regel mit Check")
            cwd = os.getcwd()
            os.chdir(d)
            try:
                items = ci.drift({"instruction_files": ["AGENTS.md"], "policy_conf": "pol.conf"}, "2000-01-01")
            finally:
                os.chdir(cwd)
        self.assertEqual([i["rule"] for i in items], ["Keine Strings im Widget-Baum"])
        self.assertEqual(items[0]["subject"], "nur Prosa")


if __name__ == "__main__":
    unittest.main()
