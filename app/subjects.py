"""Matières (modules MIT) auxquelles rattacher les cours enregistrés."""

SUBJECTS = [
    {"code": "6.7900", "titre": "Machine Learning"},
    {"code": "6.7960", "titre": "Deep Learning"},
    {"code": "6.C57", "titre": "Optimization Methods"},
    {"code": "18.675", "titre": "Theory of Probability"},
    {"code": "autres", "titre": "Autres"},
]

UNCLASSIFIED_CODE = ""
UNCLASSIFIED_TITLE = "Non classé"

_BY_CODE = {s["code"]: s["titre"] for s in SUBJECTS}


def subject_title(code: str) -> str:
    return _BY_CODE.get(code, UNCLASSIFIED_TITLE)
