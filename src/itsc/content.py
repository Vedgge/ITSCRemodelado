"""Editorial content held as data.

Everything factual here comes from the existing site: the FAQ answers were
already written (homepage accordion), the contact details and social links come
from the footer, and the career names come from the nav dropdown.

Nothing that could mislead a prospective student is invented. Where a fact is
not available -- exam dates, resolution numbers, the cooperadora's fee, staff
names, curricula -- the page says so and points at the institution, rather than
guessing. A student who acts on a fabricated exam date suffers real harm.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FAQItem:
    pregunta: str
    respuesta: str
    #: Groups questions on the full FAQ page.
    categoria: str = "General"


#: Answers 1-7 are reproduced from the homepage accordion, with typos corrected
#: ("haa" -> "haya", "caracter" -> "carácter") and a dated 2020 aside removed.
FAQ: tuple[FAQItem, ...] = (
    FAQItem(
        "¿Qué carreras se dictan en el ITSC?",
        "Las carreras que se dictan actualmente están publicadas en la sección "
        "**Carreras** de este sitio. Son tecnicaturas de nivel superior, con "
        "título oficial.",
        "Carreras",
    ),
    FAQItem(
        "¿Todas las carreras son gratuitas?",
        "Sí. Se pide que contribuyas abonando la **cuota social de la cooperadora**. "
        "Esa cuota se utiliza, entre otras cosas, para abonar el seguro y el "
        "servicio de urgencias, indispensables para nuestros estudiantes.",
        "Inscripción",
    ),
    FAQItem(
        "¿Tengo que asistir a clases todos los días?",
        "Sí. Todas las tecnicaturas son de **carácter presencial**. La virtualidad "
        "es la excepción y no el formato habitual de cursado.",
        "Cursado",
    ),
    FAQItem(
        "¿Dónde debo inscribirme?",
        "Las inscripciones se realizan a través de la **página del Gobierno de "
        "Córdoba**. Necesitás contar con una cuenta de **Ciudadano Digital (CiDi)**: "
        "sin ella no vas a poder inscribirte en ninguna institución pública.",
        "Inscripción",
    ),
    FAQItem(
        "¿Cuándo son las inscripciones?",
        "Las inscripciones son **anuales**: se realizan una vez al año. Las fechas "
        "las indica el Ministerio de Educación de la Provincia de Córdoba y, por lo "
        "general, se definen hacia fin de año. Cuando tengamos las fechas "
        "confirmadas se publican en este sitio, así que te recomendamos visitarlo "
        "periódicamente para mantenerte informado.",
        "Inscripción",
    ),
    FAQItem(
        "¿Puedo pedir el pase desde otro instituto al ITSC?",
        "Los pases aplican cuando la carrera que cursás tiene el **mismo plan de "
        "estudios** que la que se dicta en el Instituto. Antes de iniciar el trámite "
        "consultá si hay **disponibilidad áulica**, porque de eso depende que el "
        "pase pueda otorgarse.",
        "Trámites",
    ),
    FAQItem(
        "¿Puedo estudiar sin el secundario completo?",
        "Si tenés **más de 25 años**, la primaria completa y trabajás en algo idóneo "
        "a la carrera que querés estudiar (y podés acreditarlo), podés inscribirte y "
        "rendir un **examen de idoneidad**. Si aprobás ese examen, podés cursar la "
        "carrera en el mismo año en que lo hayas rendido.",
        "Inscripción",
    ),
    # The remaining entries restate facts established above; they add no new claims.
    FAQItem(
        "¿El título tiene validez nacional?",
        "Las tecnicaturas del ITSC son carreras de nivel superior dictadas en el "
        "marco del sistema educativo público de la Provincia de Córdoba. Para "
        "consultas sobre la titulación concreta de una carrera, escribinos desde la "
        "sección Contacto.",
        "Carreras",
    ),
    FAQItem(
        "¿Cómo obtengo una cuenta de Ciudadano Digital?",
        "Ciudadano Digital (CiDi) es la plataforma de identidad del Gobierno de la "
        "Provincia de Córdoba y se gestiona en su sitio oficial. Es un requisito "
        "previo a la inscripción y conviene tramitarla con anticipación, antes de "
        "que abra el período de inscripción.",
        "Inscripción",
    ),
    FAQItem(
        "¿Dónde queda el Instituto?",
        "Estamos en **Río Negro 77, Córdoba Capital**. Podés comunicarte al "
        "**(0351) 4337074** o escribirnos desde la sección Contacto.",
        "General",
    ),
    FAQItem(
        "¿Qué es la cooperadora y para qué se usa la cuota?",
        "La cooperadora es la asociación que acompaña el funcionamiento cotidiano "
        "del Instituto. La cuota social cubre, entre otras cosas, el seguro y el "
        "servicio de urgencias para estudiantes. El monto y la forma de pago se "
        "informan en el Instituto.",
        "Inscripción",
    ),
)


@dataclass(frozen=True)
class Carrera:
    nombre: str
    slug: str
    resumen: str
    icon: str = "file"


#: The ten tecnicaturas, from the existing nav dropdown. The summaries describe
#: each field of study in general terms -- they deliberately do NOT state
#: durations, subject lists or titles, none of which are available here.
CARRERAS: tuple[Carrera, ...] = (
    Carrera(
        "Administración",
        "administracion",
        "Formación en gestión administrativa, contable y organizacional para "
        "empresas y organismos públicos.",
    ),
    Carrera(
        "Bromatología",
        "bromatologia",
        "Control de calidad e inocuidad de los alimentos, higiene alimentaria y normativa vigente.",
    ),
    Carrera(
        "Desarrollo de Software",
        "desarrollo-de-software",
        "Programación, bases de datos y desarrollo de aplicaciones web y de escritorio.",
    ),
    Carrera(
        "Enfermería",
        "enfermeria",
        "Cuidado integral de la salud de las personas en instituciones "
        "sanitarias y en la comunidad.",
    ),
    Carrera(
        "Gestión Ambiental",
        "gestion-ambiental",
        "Gestión de recursos naturales, tratamiento de residuos y evaluación de impacto ambiental.",
    ),
    Carrera(
        "Gestión y Mantenimiento",
        "gestion-y-mantenimiento",
        "Planificación y mantenimiento de instalaciones, equipos y servicios industriales.",
    ),
    Carrera(
        "Higiene y Seguridad",
        "higiene-y-seguridad",
        "Prevención de riesgos laborales, seguridad e higiene en el trabajo y normativa aplicable.",
    ),
    Carrera(
        "Instrumentación Quirúrgica",
        "instrumentacion-quirurgica",
        "Asistencia instrumental en el quirófano, asepsia y preparación del campo quirúrgico.",
    ),
    Carrera(
        "Óptica y Contactología",
        "optica-y-contactologia",
        "Óptica oftálmica, adaptación de lentes de contacto y atención en gabinete.",
    ),
    Carrera(
        "Prótesis Dental",
        "protesis-dental",
        "Diseño y confección de prótesis dentales fijas y removibles en laboratorio.",
    ),
)

CARRERAS_BY_SLUG = {c.slug: c for c in CARRERAS}


@dataclass(frozen=True)
class GalleryItem:
    titulo: str
    slug: str
    descripcion: str = ""


#: The six captions already present on the homepage carousel, with their
#: existing WebP assets.
FOTOGALERIA: tuple[GalleryItem, ...] = (
    GalleryItem(
        "Visita a Fábrica INSTRELEC",
        "carrusel-fotogaleria-1",
        "Estudiantes recorrieron la planta y conocieron sus procesos productivos.",
    ),
    GalleryItem(
        "Visita de la Asociación Cordobesa de Protesistas Dentales",
        "carrusel-fotogaleria-2",
        "Encuentro con profesionales del sector en el Instituto.",
    ),
    GalleryItem(
        "Prótesis visita el Museo Anatómico",
        "carrusel-fotogaleria-3",
        "Actividad de formación práctica fuera del aula.",
    ),
    GalleryItem(
        "Practicando con prótesis",
        "carrusel-fotogaleria-4",
        "Trabajo de laboratorio de la Tecnicatura en Prótesis Dental.",
    ),
    GalleryItem(
        "Prácticas en DENSO S.A.",
        "carrusel-fotogaleria-5",
        "Prácticas profesionalizantes en planta industrial.",
    ),
    GalleryItem(
        "Jornada de RCP avanzada y primeros auxilios",
        "carrusel-fotogaleria-6",
        "Capacitación abierta a estudiantes del Instituto.",
    ),
)


#: Sample testimonials, shown behind a visible "contenido de muestra" label.
#: The originals were real strangers' photographs pulled from randomuser.me on
#: every page load and captioned with invented quotes -- fabricated testimonials
#: using real people's likenesses. Avatars are now generated locally from
#: initials, so no third-party request is made and no real person is depicted.
TESTIMONIOS_DEMO = (
    (
        "M. B.",
        "Enfermería",
        "Las prácticas desde el primer año me dieron una seguridad que no esperaba.",
    ),
    ("J. R.", "Desarrollo de Software", "Entré sin saber programar y salí trabajando en el rubro."),
    (
        "L. G.",
        "Bromatología",
        "Los laboratorios y el acompañamiento de los docentes hacen la diferencia.",
    ),
)
