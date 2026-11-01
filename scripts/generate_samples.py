"""Generate the synthetic Brisamar Seguros sample PDFs used by the demo, the tests and the eval.

Usage (from the repository root, with the backend dev dependencies installed):
    python scripts/generate_samples.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"

Section = tuple[str, list[str]]


def _autos_sections(
    declaration_days: str, expert_threshold: str, glass_excess: str
) -> list[list[Section]]:
    return [
        [
            (
                "1. Declaración del siniestro",
                [
                    f"El asegurado debe comunicar el siniestro a Brisamar Seguros en un plazo máximo "
                    f"de {declaration_days} desde la fecha del accidente.",
                    "La comunicación puede realizarse por teléfono, en la aplicación móvil o en "
                    "cualquier oficina. El analista registra el expediente y asigna un número de "
                    "siniestro con el prefijo AUT.",
                    "Si la declaración llega fuera de plazo, el analista documenta el motivo del "
                    "retraso y solicita aprobación del supervisor antes de continuar la tramitación.",
                ],
            ),
            (
                "2. Parte amistoso y documentación",
                [
                    "Cuando intervienen dos vehículos se solicita la Declaración Amistosa de Accidente "
                    "firmada por ambos conductores.",
                    "El analista debe pedir fotografías de los daños, el permiso de circulación y la "
                    "póliza vigente. Si hay heridos se requiere además el atestado policial.",
                ],
            ),
        ],
        [
            (
                "3. Peritación de daños",
                [
                    f"Los daños estimados superiores a {expert_threshold} requieren la visita "
                    "presencial de un perito antes de autorizar la reparación.",
                    "Por debajo de ese importe se acepta la peritación por videollamada o mediante "
                    "fotografías enviadas por el asegurado.",
                ],
            ),
            (
                "4. Rotura de lunas",
                [
                    "La rotura de lunas y cristales está cubierta en las pólizas a terceros "
                    f"ampliado y todo riesgo, con una franquicia de {glass_excess} por siniestro.",
                    "La reparación debe hacerse en un taller concertado; fuera de la red concertada "
                    "se reembolsa como máximo el precio de referencia del baremo.",
                ],
            ),
            (
                "5. Vehículo de sustitución",
                [
                    "El vehículo de sustitución se concede durante un máximo de 15 días cuando el "
                    "coche asegurado permanece inmovilizado en taller por un siniestro cubierto.",
                ],
            ),
        ],
    ]


DOCUMENTS: dict[str, tuple[str, list[list[Section]]]] = {
    "manual-siniestros-autos-v1.pdf": (
        "Manual de tramitación de siniestros de Autos (v1, 2025)",
        _autos_sections("7 días naturales", "3.000 euros", "90 euros"),
    ),
    "manual-siniestros-autos-v2.pdf": (
        "Manual de tramitación de siniestros de Autos (v2, 2026)",
        _autos_sections("5 días hábiles", "2.500 euros", "60 euros"),
    ),
    "manual-siniestros-hogar.pdf": (
        "Manual de tramitación de siniestros de Hogar",
        [
            [
                (
                    "1. Daños por agua",
                    [
                        "En los daños por agua el analista debe identificar el origen de la fuga "
                        "antes de autorizar la reparación de los daños estéticos.",
                        "La localización y reparación de la tubería averiada está cubierta hasta "
                        "600 euros por siniestro. Los daños causados a vecinos se tramitan por la "
                        "garantía de responsabilidad civil.",
                    ],
                ),
                (
                    "2. Robo en la vivienda",
                    [
                        "En caso de robo el asegurado debe presentar la denuncia ante la policía "
                        "en un plazo máximo de 48 horas y enviar una copia al expediente.",
                        "Las joyas solo están cubiertas si se guardaban en caja fuerte homologada "
                        "y hasta un límite de 3.000 euros.",
                    ],
                ),
            ],
            [
                (
                    "3. Fenómenos atmosféricos",
                    [
                        "Los daños por viento solo están cubiertos cuando las rachas superan los "
                        "80 km/h según la estación meteorológica oficial más cercana.",
                        "Los daños por lluvia requieren una precipitación superior a 40 litros por "
                        "metro cuadrado y hora.",
                    ],
                ),
                (
                    "4. Cerrajería urgente",
                    [
                        "El servicio de cerrajería urgente por pérdida de llaves se presta 24 horas "
                        "y está limitado a dos intervenciones por anualidad de seguro.",
                    ],
                ),
            ],
            [
                (
                    "5. Daños eléctricos",
                    [
                        "Los daños eléctricos en electrodomésticos por subidas de tensión se "
                        "indemnizan a valor real, aplicando una depreciación del 10 % por año de "
                        "antigüedad del aparato.",
                        "El técnico reparador debe emitir un informe que confirme que la avería se "
                        "debe a una sobretensión.",
                    ],
                ),
                (
                    "6. Infraseguro",
                    [
                        "Si el valor del continente declarado en la póliza es inferior al valor real, "
                        "se aplica la regla proporcional sobre la indemnización.",
                    ],
                ),
            ],
        ],
    ),
    "circular-prestaciones-vida.pdf": (
        "Circular de prestaciones del seguro de Vida",
        [
            [
                (
                    "1. Documentación por fallecimiento",
                    [
                        "Para tramitar la prestación por fallecimiento los beneficiarios deben "
                        "aportar el certificado de defunción, el certificado de últimas voluntades "
                        "y el DNI de cada beneficiario.",
                        "Si no hay beneficiarios designados en la póliza, se exige además la "
                        "declaración de herederos o el testamento.",
                    ],
                ),
                (
                    "2. Plazo de pago",
                    [
                        "Brisamar Seguros abonará el capital asegurado en un plazo máximo de 40 "
                        "días desde la recepción de la documentación completa.",
                    ],
                ),
            ],
            [
                (
                    "3. Exclusiones",
                    [
                        "El suicidio no está cubierto durante el primer año de vigencia de la "
                        "póliza.",
                        "Tampoco se cubren los fallecimientos derivados de la práctica profesional "
                        "de deportes de riesgo salvo pacto expreso en las condiciones particulares.",
                    ],
                ),
                (
                    "4. Incapacidad permanente",
                    [
                        "La incapacidad permanente absoluta se acredita con la resolución firme del "
                        "Instituto Nacional de la Seguridad Social.",
                    ],
                ),
            ],
            [
                (
                    "5. Rescate de la póliza",
                    [
                        "El tomador puede solicitar el rescate total a partir de la segunda "
                        "anualidad. Se aplica una penalización del 2 % sobre la provisión "
                        "matemática.",
                    ],
                ),
                (
                    "6. Fiscalidad de la prestación",
                    [
                        "El analista informa a los beneficiarios de que la prestación por "
                        "fallecimiento tributa en el Impuesto sobre Sucesiones y Donaciones.",
                    ],
                ),
            ],
        ],
    ),
    "circular-antifraude-autos.pdf": (
        "Circular de detección de fraude en siniestros de Autos",
        [
            [
                (
                    "1. Indicadores de fraude",
                    [
                        "Se consideran indicadores de fraude: siniestros declarados en los primeros "
                        "30 días de vigencia de la póliza, varios siniestros del mismo asegurado en "
                        "un año y testigos que son familiares del conductor.",
                        "Cuando concurren dos o más indicadores, el analista deriva el expediente a "
                        "la Unidad de Investigación de Fraude antes de cualquier pago.",
                    ],
                ),
            ],
            [
                (
                    "2. Comunicación con el asegurado",
                    [
                        "El analista no debe informar al asegurado de que su expediente está en "
                        "investigación por posible fraude.",
                        "La Unidad de Investigación de Fraude dispone de 20 días hábiles para emitir "
                        "su dictamen.",
                    ],
                ),
            ],
        ],
    ),
}


def _write_document(path: Path, title: str, pages: list[list[Section]]) -> None:
    styles = getSampleStyleSheet()
    story: list = [Paragraph(title, styles["Title"]), Spacer(1, 0.4 * cm)]
    for page_number, sections in enumerate(pages):
        if page_number:
            story.append(PageBreak())
        for heading, paragraphs in sections:
            story.append(Paragraph(heading, styles["Heading2"]))
            story.extend(Paragraph(text, styles["BodyText"]) for text in paragraphs)
            story.append(Spacer(1, 0.3 * cm))
    SimpleDocTemplate(str(path), pagesize=A4, title=title, author="Brisamar Seguros").build(story)


def _write_textless_pdf(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for offset in range(0, 500, 25):
        pdf.rect(2 * cm + offset * 0.3, 20 * cm - offset, 10 * cm, 0.4 * cm, fill=1)
    pdf.showPage()
    pdf.save()


def main() -> None:
    SAMPLES_DIR.mkdir(exist_ok=True)
    for filename, (title, pages) in DOCUMENTS.items():
        _write_document(SAMPLES_DIR / filename, title, pages)
    _write_textless_pdf(SAMPLES_DIR / "escaneado-sin-texto.pdf")
    (SAMPLES_DIR / "corrupto.pdf").write_bytes(
        b"%PDF-1.7\n1 0 obj << /Type /Catalog /Pages 2 0 R >>\nthis is not a valid pdf body\n"
    )
    print(f"Samples written to {SAMPLES_DIR}")


if __name__ == "__main__":
    main()
