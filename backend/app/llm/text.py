import re
import unicodedata

_WORD = re.compile(r"[a-z0-9]+")

SPANISH_STOPWORDS = frozenset(
    """
    a al algo algun alguna algunas alguno algunos ante antes aqui asi cada como con contra cual
    cuales cuando cuanto de del desde donde dos el ella ellas ello ellos en entre era eran es esa
    esas ese eso esos esta estan estas este esto estos fue fueron ha han hasta hay la las le les lo
    los mas me mi mis mucho muy nada ni no nos nosotros o otra otras otro otros para pero poco por
    porque puede pueden que quien se sea segun ser si sin sobre son su sus tambien tanto te tiene
    tienen todo todos tu un una uno unos usted y ya debe deben hacer cuanto cuantos cuantas cual
    """.split()
)


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def content_terms(text: str, stem_length: int = 6) -> list[str]:
    """Lowercase, strip accents, drop stopwords and crudely stem by prefix truncation."""
    return [
        word[:stem_length]
        for word in _WORD.findall(fold(text))
        if word not in SPANISH_STOPWORDS and (len(word) > 2 or word.isdigit())
    ]
