"""Session-local presentation translations; source identities and data stay unchanged.

Messages have stable keys. The Streamlit adapter localises only presentation calls,
never the model, readers, cache keys, callback arguments or stored widget values.
Original source fields in evidence tables remain verbatim.
"""

from functools import lru_cache
import hashlib
import html
from html.parser import HTMLParser
import re
from string import Formatter

import pandas as pd
import streamlit as _st

DEFAULT_LANGUAGE = "es"
LANGUAGES = ("ES", "EN")

MESSAGES = {
    "nav.explore": {"es": "Explorar inmuebles", "en": "Explore properties"},
    "nav.address": {"es": "Buscar por dirección", "en": "Search by address"},
    "nav.about": {"es": "Acerca del proyecto", "en": "About the project"},
    "message.0003": {"es": "Consulta técnica · direcciones", "en": "Technical address search"},
    "message.0004": {"es": "Explorar municipios", "en": "Explore municipalities"},
    "message.0005": {"es": "Madrid capital", "en": "Madrid city"},
    "message.0006": {
        "es": "Comunidad de Madrid · Municipios y cobertura",
        "en": "Comunidad de Madrid · Municipalities and coverage",
    },
    "message.0007": {"es": "Navegación", "en": "Navigation"},
    "message.0008": {"es": "Herramientas de desarrollo", "en": "Development tools"},
    "message.0009": {"es": "Consulta técnica", "en": "Technical query"},
    "message.0010": {"es": "Combinar evidencias", "en": "Combine evidence"},
    "filters.clear": {"es": "Limpiar filtros", "en": "Clear filters"},
    "explore.count": {"es": "Inmuebles encontrados", "en": "Properties found"},
    "message.0013": {
        "es": "Se cuentan parcelas catastrales distintas, no necesariamente edificios únicos. Mapa y lista muestran páginas del mismo conjunto.",
        "en": "Counts refer to distinct cadastral parcels, not necessarily individual buildings. The map and list show pages from the same result set.",
    },
    "message.0014": {"es": "Página del mapa", "en": "Map page"},
    "message.0015": {"es": "Lista de inmuebles", "en": "Property list"},
    "message.0016": {"es": "Página de inmuebles", "en": "Results page"},
    "message.0017": {
        "es": "Obligaciones ITE/IEE y menciones documentadas; no son resultados de inspección ni un diagnóstico del estado actual.",
        "en": "ITE/IEE filing requirements and documented references; these are not inspection results or a diagnosis of current building condition.",
    },
    "message.0018": {
        "es": "No hay resultados disponibles para esta combinación. Una fuente no integrada o restringida no acredita ausencia de antecedentes.",
        "en": "No results are available for this combination. A missing or restricted source does not establish the absence of records.",
    },
    "message.0019": {"es": "Explorar una zona del mapa", "en": "Explore an area of the map"},
    "message.0020": {"es": "Explorar área", "en": "Explore area"},
    "message.0021": {
        "es": "Áreas de navegación para acotar el mapa; no son barrios oficiales.",
        "en": "Navigation areas help narrow the map; they are not official neighbourhoods.",
    },
    "message.0022": {
        "es": " parcelas en esta página del mapa; máximo 500 por carga. La lista permite recorrer todo el conjunto filtrado.",
        "en": " parcels on this map page; up to 500 per load. Use the list to browse the full filtered result set.",
    },
    "message.0023": {"es": "Abrir ficha", "en": "View details"},
    "message.0024": {"es": "Ficha del inmueble", "en": "Property details"},
    "fiche.back": {"es": "Volver al mapa", "en": "Back to map"},
    "message.0026": {
        "es": "Ver expedientes de Plan Rehabilita",
        "en": "View Plan Rehabilita cases",
    },
    "message.0027": {"es": "Al menos una (OR)", "en": "Match any selected filter (OR)"},
    "message.0028": {"es": "Todas (AND)", "en": "Match all selected filters (AND)"},
    "message.0029": {"es": "Parcela documentada en ", "en": "Documented parcel in "},
    "message.0030": {
        "es": "Consulta bloqueada: licencia y redistribución pendientes de verificar.",
        "en": "Query blocked: reuse licence and redistribution permissions remain unverified.",
    },
    "message.0031": {"es": "Mostrar consulta de expedientes", "en": "Show case search"},
    "message.0032": {"es": "Todos los distritos", "en": "All districts"},
    "message.0033": {"es": "Mapa general", "en": "Map overview"},
    "message.0034": {"es": "Área ", "en": "Area "},
    "message.0035": {
        "es": "Conoce las características y la información pública disponible sobre los inmuebles de seis municipios.",
        "en": "Explore property characteristics and available public information across six municipalities.",
    },
    "message.0036": {
        "es": ". Ámbitos documentales; no diagnóstico del edificio.",
        "en": ". Documentary scope only; not a building diagnosis.",
    },
    "message.0037": {
        "es": "Cobertura catastral parcial. Este municipio dispone de mapa de parcelas y sus fichas; no de búsqueda postal fiable.",
        "en": "Partial cadastral coverage. Parcel maps and details are available here; reliable address search is not.",
    },
    "message.0038": {"es": "Fuentes y alcance", "en": "Sources and scope"},
    "message.0039": {
        "es": "Catastro INSPIRE · Dirección General del Catastro; CEEE · Comunidad de Madrid (CC BY 4.0); conservación y callejero · Ayuntamiento de Madrid; PRTR · visor de rehabilitación de la Comunidad de Madrid alojado en COAM; Plan Rehabilita · Ayuntamiento de Madrid, captura local facilitada por el usuario. Cada ficha detalla procedencia, fecha, ámbito y vínculo. PRTR y Plan Rehabilita: reutilización pendiente de verificar; bloqueados en público.",
        "en": "Catastro INSPIRE · Dirección General del Catastro; CEEE · Comunidad de Madrid (CC BY 4.0); maintenance records and street directory · Ayuntamiento de Madrid; PRTR · Comunidad de Madrid rehabilitation viewer hosted by COAM; Plan Rehabilita · Ayuntamiento de Madrid, local capture supplied by the owner. Each property record explains its source, date, scope and link. PRTR and Plan Rehabilita: reuse remains unverified and public access is blocked.",
    },
    "message.0040": {
        "es": "Buscar por dirección en Madrid",
        "en": "Search for an address in Madrid",
    },
    "message.0041": {
        "es": "Nivel de la parcela de origen: ",
        "en": "Origin parcel information level: ",
    },
    "message.0042": {
        "es": "Catálogo no disponible o incompatible. La consulta completa se conserva en la capa técnica.",
        "en": "The catalogue is unavailable or incompatible. The full query remains available in the technical tools.",
    },
    "message.0043": {"es": "Detalle del catálogo", "en": "Catalogue details"},
    "message.0044": {
        "es": "Vínculo documental confirmado a parcela",
        "en": "Confirmed documentary link to a parcel",
    },
    "message.0045": {
        "es": "Relación ambigua · requiere revisión",
        "en": "Ambiguous link · review required",
    },
    "message.0046": {
        "es": "Sin parcela confirmada en las fuentes integradas",
        "en": "No confirmed parcel in the integrated sources",
    },
    "message.0047": {"es": "Buscar un inmueble por dirección", "en": "Search by address"},
    "message.0048": {
        "es": "Introduzca la dirección, seleccione el acceso correcto y abra su ficha. El mapa es opcional.",
        "en": "Enter an address, select the correct entrance and open its details. The map is optional.",
    },
    "message.0049": {"es": "Limpiar búsqueda", "en": "Clear search"},
    "message.0050": {"es": "Seleccione la dirección correcta", "en": "Select the correct address"},
    "message.0051": {"es": "Abrir ficha del inmueble", "en": "View property details"},
    "message.0052": {"es": "Volver a los resultados", "en": "Back to results"},
    "message.0053": {
        "es": "Consulta técnica completa: incluye registros excluidos del catálogo comercial.",
        "en": "Full technical query: includes records excluded from the commercial catalogue.",
    },
    "message.0054": {
        "es": "Este municipio no dispone de calles y números recuperables en las fuentes locales integradas. Se necesita una fuente postal oficial adicional. Puede seguir explorando sus parcelas y construcciones desde Explorar municipios.",
        "en": "Usable street names and house numbers are not available for this municipality in the integrated local sources. An additional official address source is required. You can still explore its parcels and structures through Explore properties.",
    },
    "message.0055": {"es": "Calle o dirección", "en": "Street or address"},
    "message.0056": {"es": "Número", "en": "House number"},
    "message.0057": {"es": "Complemento (opcional)", "en": "Additional details (optional)"},
    "message.0058": {
        "es": "No hemos encontrado esta dirección en las fuentes integradas.",
        "en": "We could not find this address in the integrated sources.",
    },
    "message.0059": {"es": " coincidencias · página ", "en": " matches · page "},
    "message.0060": {"es": "Resultados anteriores", "en": "Previous results"},
    "message.0061": {"es": "Más resultados", "en": "More results"},
    "message.0062": {"es": " / versión ", "en": " / version "},
    "message.0063": {
        "es": "Seleccione expresamente una coincidencia; no se abre la primera automáticamente.",
        "en": "Select a result explicitly; the first match is not opened automatically.",
    },
    "message.0064": {"es": "Seleccione la parcela vinculada", "en": "Select the linked parcel"},
    "message.0065": {
        "es": "Este acceso tiene varias parcelas vinculadas. Sus atributos y expedientes se consultan por separado.",
        "en": "This entrance is linked to several parcels. Their characteristics and cases must be viewed separately.",
    },
    "message.0066": {
        "es": "Índice postal no disponible o incompatible. Regenere el índice según la documentación.",
        "en": "The address index is unavailable or incompatible. Rebuild it as described in the documentation.",
    },
    "message.0067": {"es": "Por ejemplo: Calle Bailén 12", "en": "For example: Calle Bailén 12"},
    "message.0068": {
        "es": ". No se puede abrir una ficha con identidad confirmada.",
        "en": ". Details cannot be opened with a confirmed identity.",
    },
    "message.0069": {
        "es": "Procedencia y motivo de revisión",
        "en": "Source and reason for review",
    },
    "message.0070": {
        "es": "Vías documentadas que comienzan así: ",
        "en": "Documented streets starting with this text: ",
    },
    "message.0071": {"es": "Fuente SHA-256: ", "en": "Source SHA-256: "},
    "message.0072": {
        "es": "Referencias candidatas (sin confirmar): ",
        "en": "Candidate references (unconfirmed): ",
    },
    "message.0073": {
        "es": "Acerca de Madrid Rehab Intelligence",
        "en": "About Madrid Rehab Intelligence",
    },
    "message.0074": {
        "es": "Conoce mejor los edificios de tu ciudad",
        "en": "Get to know your city's buildings",
    },
    "message.0075": {
        "es": "Esta es una primera versión experimental: un primer prototipo o boceto funcional.",
        "en": "This is an early experimental version: an initial working prototype.",
    },
    "message.0076": {
        "es": "Proyecto personal e independiente, en fase experimental. No constituye una certificación técnica de los inmuebles ni está afiliado oficialmente a las administraciones que publican los datos.",
        "en": "An independent personal project in its experimental phase. It does not provide technical certification of properties and is not officially affiliated with the public authorities that publish the source data.",
    },
    "message.0077": {
        "es": "Un proyecto que acaba de empezar",
        "en": "A project that is just getting started",
    },
    "message.0078": {"es": "¿Qué puedes hacer actualmente?", "en": "What can you do today?"},
    "message.0079": {
        "es": "¿De dónde procede la información? Fuentes y metodología",
        "en": "Where does the information come from? Sources and methodology",
    },
    "message.0080": {
        "es": "Cobertura de Comunidad de Madrid",
        "en": "Coverage across Comunidad de Madrid",
    },
    "message.0081": {
        "es": "Algunas cosas importantes que debes saber",
        "en": "A few important things to know",
    },
    "message.0082": {
        "es": "¿Qué queremos mejorar próximamente?",
        "en": "What would we like to improve next?",
    },
    "message.0083": {"es": "Vivienda individual", "en": "Individual dwelling"},
    "message.0084": {"es": "Edificio completo declarado", "en": "Declared whole building"},
    "message.0085": {
        "es": "Órdenes de ejecución históricas",
        "en": "Historical enforcement orders",
    },
    "message.0086": {"es": "Obligaciones ITE", "en": "ITE filing requirements"},
    "message.0087": {"es": "Obligaciones IEE", "en": "IEE filing requirements"},
    "message.0088": {"es": "Declaraciones responsables", "en": "Responsible declarations"},
    "message.0089": {"es": "### Características principales", "en": "### Main characteristics"},
    "message.0090": {
        "es": "Fuente: Catastro INSPIRE. Los años y usos pertenecen a objetos constructivos asociados; no son características verificadas del portal. BuildingPart es una parte catastral, no un edificio físico independiente.",
        "en": "Source: Catastro INSPIRE. Years and uses describe linked cadastral structures, not verified characteristics of an entrance. BuildingPart is a cadastral part, not an independent physical building.",
    },
    "message.0091": {
        "es": "Consultar valores constructivos y procedencia por objeto",
        "en": "View construction values and sources by object",
    },
    "message.0092": {"es": "### Información energética", "en": "### Energy information"},
    "message.0093": {
        "es": "Cada certificado conserva su ámbito. Una vivienda no califica todo el edificio; no se acredita vigencia ni cobertura física.",
        "en": "Each certificate retains its scope. A dwelling's rating does not rate the entire building; current validity and physical coverage have not been verified.",
    },
    "message.0094": {
        "es": "Consultar certificados, fechas y fuentes",
        "en": "View certificates, dates and sources",
    },
    "message.0095": {"es": "### Ayudas y subvenciones", "en": "### Grants and subsidies"},
    "message.0096": {
        "es": "Concesión no acredita pago, obra iniciada ni terminada. Importe por expediente, sin suma entre parcelas.",
        "en": "An award does not establish payment or that work has started or finished. Amounts belong to individual cases and must not be added across parcels.",
    },
    "message.0097": {
        "es": "Consultar expedientes y procedencia",
        "en": "View grant cases and sources",
    },
    "message.0098": {
        "es": "Importes por expediente, sin suma entre capas ni parcelas. Subvención revisada no acredita pago ni obra ejecutada.",
        "en": "Amounts belong to individual cases and must not be added across layers or parcels. A revised subsidy does not establish payment or completed work.",
    },
    "message.0099": {
        "es": "Consultar Plan Rehabilita y procedencia",
        "en": "View Plan Rehabilita records and sources",
    },
    "message.0100": {
        "es": "### Conservación e inspecciones",
        "en": "### Building maintenance and inspections",
    },
    "message.0101": {
        "es": "Resultados actuales de inspección: no acreditados por estos antecedentes. REC: sin consulta automática; las consultas expresas y sus resultados se mantienen en detalles técnicos. Obligaciones y órdenes históricas no son diagnósticos actuales.",
        "en": "Current inspection results are not established by these records. REC is not queried automatically; explicit queries and their results remain in technical details. Filing requirements and historical orders are not current diagnoses.",
    },
    "message.0102": {
        "es": "Consultar antecedentes, fechas y fuentes",
        "en": "View administrative records, dates and sources",
    },
    "message.0103": {
        "es": "### Antes de preparar una propuesta",
        "en": "### Before preparing a proposal",
    },
    "message.0104": {
        "es": "Dirección vinculada documentalmente a una parcela catastral. No acredita un edificio físico único.",
        "en": "Address linked to a cadastral parcel by documentary evidence. This does not establish a unique physical building.",
    },
    "message.0105": {
        "es": "Consulta documental de parcela u objeto catastral; dirección seleccionada no disponible.",
        "en": "Documentary query for a parcel or cadastral object; no selected address is available.",
    },
    "message.0106": {"es": "Referencia de consulta", "en": "Query reference"},
    "message.0107": {
        "es": "Información no disponible; consulta de ayudas no verificable.",
        "en": "Information unavailable; the grant query cannot be verified.",
    },
    "message.0108": {
        "es": "Existen relaciones con incidencias; consultar detalles sin atribuir concesiones confirmadas.",
        "en": "Some links have issues; consult their details without treating them as confirmed awards.",
    },
    "message.0109": {
        "es": "Fuente municipal no disponible o no verificable en esta consulta.",
        "en": "The municipal source is unavailable or cannot be verified for this query.",
    },
    "message.0110": {
        "es": "No hay comprobaciones adicionales derivadas de las evidencias disponibles.",
        "en": "No additional checks follow from the available evidence.",
    },
    "message.0111": {"es": "Dirección seleccionada", "en": "Selected address"},
    "message.0112": {
        "es": ". No se puede determinar la disponibilidad de certificados.",
        "en": ". Certificate availability cannot be determined.",
    },
    "message.0113": {
        "es": "Sin certificados energéticos asociados en las fuentes integradas.",
        "en": "No linked energy certificates in the integrated sources.",
    },
    "message.0114": {
        "es": "Sin expedientes PRTR confirmados en esta captura; no acredita ausencia real de ayudas.",
        "en": "No confirmed PRTR cases in this capture; this does not establish the absence of grants.",
    },
    "message.0115": {
        "es": "Sin antecedentes administrativos confirmados en la captura integrada.",
        "en": "No confirmed administrative records in the integrated capture.",
    },
    "message.0116": {
        "es": "Vinculación ambigua: existen antecedentes con incidencias; no se cuentan como confirmados.",
        "en": "Ambiguous link: some records have issues and are not counted as confirmed.",
    },
    "message.0117": {
        "es": ": consulta no verificable. No se interpreta como ausencia de registros.",
        "en": ": query cannot be verified. This is not interpreted as an absence of records.",
    },
    "message.0118": {"es": "Entidad de origen", "en": "Source entity"},
    "message.0119": {"es": "Ámbito del dato", "en": "Evidence scope"},
    "message.0120": {"es": "Fecha / periodo", "en": "Date / period"},
    "message.0121": {"es": "Límite de interpretación", "en": "Interpretation limits"},
    "message.0122": {"es": "Parcela vinculada", "en": "Linked parcel"},
    "message.0123": {"es": "Objeto BU independiente", "en": "Independent BU object"},
    "message.0124": {"es": "Corte catastral: ", "en": "Cadastral snapshot: "},
    "message.0125": {
        "es": "Accesos documentales de la parcela",
        "en": "Documented entrances to the parcel",
    },
    "message.0126": {"es": "Parcelas vinculadas al acceso", "en": "Parcels linked to the entrance"},
    "message.0127": {
        "es": "Objetos constructivos documentados",
        "en": "Documented cadastral structures",
    },
    "message.0128": {
        "es": " contenidos CEEE vinculados documentalmente a parcela.",
        "en": " CEEE records linked to the parcel by documentary evidence.",
    },
    "message.0129": {"es": "Ámbitos: ", "en": "Scopes: "},
    "message.0130": {"es": "Fechas declaradas: ", "en": "Declared dates: "},
    "message.0131": {
        "es": " expedientes PRTR con concesión asociada documentalmente a parcela.",
        "en": " PRTR award cases linked to the parcel by documentary evidence.",
    },
    "message.0132": {"es": "Concesión del expediente (€)", "en": "Case award (€)"},
    "message.0133": {
        "es": " expedientes municipales con relación documental confirmada a la parcela.",
        "en": " municipal cases with confirmed documentary links to the parcel.",
    },
    "message.0134": {
        "es": "Sin expediente municipal confirmado en esta captura; no acredita ausencia real de ayudas.",
        "en": "No confirmed municipal case in this capture; this does not establish the absence of grants.",
    },
    "message.0135": {
        "es": "Consulta municipal disponible exclusivamente en parcelas de Madrid.",
        "en": "Municipal query available only for parcels in Madrid.",
    },
    "message.0136": {"es": "Características", "en": "Characteristics"},
    "message.0137": {"es": "Conservación", "en": "Building maintenance"},
    "message.0138": {"es": "Energía", "en": "Energy"},
    "message.0139": {"es": "Detalle de consulta · ", "en": "Query details · "},
    "message.0140": {"es": "No disponible", "en": "Unavailable"},
    "message.0141": {"es": "Fecha declarada", "en": "Declared date"},
    "message.0142": {"es": "No disponibles", "en": "Unavailable"},
    "message.0143": {"es": " · Fuente: ", "en": " · Source: "},
    "message.0144": {
        "es": "P4 corresponde a vivienda; no se extiende al conjunto del edificio.",
        "en": "P4 relates to a dwelling; it does not extend to the entire building.",
    },
    "message.0145": {
        "es": ". No es un recuento de edificios físicos.",
        "en": ". This is not a count of physical buildings.",
    },
    "message.0146": {"es": "Sin letra", "en": "No rating"},
    "message.0147": {"es": " · Importe del expediente: ", "en": " · Case amount: "},
    "message.0148": {
        "es": "Objetos constructivos documentados: ",
        "en": "Documented cadastral structures: ",
    },
    "message.0149": {
        "es": "Información asociada a parcela · ",
        "en": "Information linked to a parcel · ",
    },
    "message.0150": {"es": "Dato propio del objeto · ", "en": "Object-specific information · "},
    "message.0151": {
        "es": "Varios valores declarados; sin suma.",
        "en": "Multiple declared values; not added together.",
    },
    "message.0152": {
        "es": "Declaración por objeto; sin suma.",
        "en": "Declared per object; not added together.",
    },
    "message.0153": {"es": "Programa sin descripción", "en": "Programme description unavailable"},
    "message.0154": {
        "es": "No disponible en las fuentes integradas",
        "en": "Unavailable in the integrated sources",
    },
    "message.0155": {"es": "Identificación", "en": "Identification"},
    "message.0156": {"es": "Características constructivas", "en": "Construction characteristics"},
    "message.0157": {"es": "Certificados CEEE", "en": "CEEE certificates"},
    "message.0158": {"es": "Conservación e ITE/IEE", "en": "Building maintenance and ITE/IEE"},
    "message.0159": {"es": "Subvenciones PRTR", "en": "PRTR grants"},
    "message.0160": {
        "es": "Calidad, limitaciones y procedencia",
        "en": "Quality, limitations and sources",
    },
    "message.0161": {"es": "Objeto catastral BU", "en": "Cadastral BU object"},
    "message.0162": {"es": "Tipo de objeto en origen", "en": "Source object type"},
    "message.0163": {"es": "Uso declarado", "en": "Declared use"},
    "message.0164": {"es": "Inicio constructivo declarado", "en": "Declared construction start"},
    "message.0165": {"es": "Fin constructivo declarado", "en": "Declared construction end"},
    "message.0166": {"es": "Año inicial declarado", "en": "Declared earliest year"},
    "message.0167": {"es": "Año final declarado", "en": "Declared latest year"},
    "message.0168": {"es": "Viviendas declaradas", "en": "Declared dwellings"},
    "message.0169": {"es": "Unidades declaradas", "en": "Declared units"},
    "message.0170": {
        "es": "Concesiones administrativas; no acreditan pago ni obras. El importe pertenece al expediente único y no debe sumarse entre parcelas. La coincidencia con CEEE no acredita causalidad.",
        "en": "Administrative awards do not establish payment or work. The amount belongs to a unique case and must not be added across parcels. Coexistence with CEEE does not establish causation.",
    },
    "message.0171": {
        "es": "No constan concesiones vinculadas en esta captura; no acredita ausencia real de ayudas.",
        "en": "No linked awards in this capture; this does not establish the absence of grants.",
    },
    "message.0172": {
        "es": "Referencia y geometría concordantes",
        "en": "Consistent reference and geometry",
    },
    "message.0173": {"es": "Referencia documental exacta", "en": "Exact documentary reference"},
    "message.0174": {"es": "Vínculo histórico Madrid", "en": "Historical Madrid link"},
    "message.0175": {
        "es": "Candidato espacial sin confirmación",
        "en": "Unconfirmed spatial candidate",
    },
    "message.0176": {"es": "Referencia ambigua", "en": "Ambiguous reference"},
    "message.0177": {"es": "Posición ambigua", "en": "Ambiguous location"},
    "message.0178": {"es": "Contradicción", "en": "Contradiction"},
    "message.0179": {"es": "Parcela en revisión", "en": "Parcel under review"},
    "message.0180": {"es": "Referencia no localizada", "en": "Reference not found"},
    "message.0181": {
        "es": "Información adicional protegida en modo público.",
        "en": "Additional information is protected in public mode.",
    },
    "message.0182": {
        "es": "Detalles técnicos · seis secciones y datos originales",
        "en": "Technical details · six sections and original data",
    },
    "message.0183": {"es": "Ficha de ", "en": "Details for "},
    "message.0184": {
        "es": "Identificación documental en captura. Parcela, objeto BU, portal y edificio físico son entidades diferentes.",
        "en": "Documentary identification in the capture. Parcels, BU objects, entrances and physical buildings are different entities.",
    },
    "message.0185": {
        "es": "Fuente: Dirección General del Catastro · INSPIRE",
        "en": "Source: Dirección General del Catastro · INSPIRE",
    },
    "message.0186": {
        "es": "Atributos declarados; no confirman identidad ni estado físico actual.",
        "en": "Declared attributes do not confirm identity or current physical condition.",
    },
    "message.0187": {
        "es": "Las obligaciones ITE/IEE no son resultados. Archivar, terminar o multar no acredita subsanación ni estado físico.",
        "en": "ITE/IEE filing requirements are not results. Archiving, closure or fines do not establish rectification or physical condition.",
    },
    "message.0188": {"es": "Fecha de fuente", "en": "Source date"},
    "message.0189": {"es": "Fecha de captura", "en": "Capture date"},
    "message.0190": {"es": "Fuente catastral", "en": "Cadastral source"},
    "message.0191": {"es": "SHA-256 del archivo original", "en": "Original file SHA-256"},
    "message.0192": {"es": "SHA-256 de fuente", "en": "Source SHA-256"},
    "message.0193": {"es": "SHA-256 del registro original", "en": "Original record SHA-256"},
    "message.0194": {"es": "Registro original", "en": "Original record"},
    "message.0195": {"es": "Geometría utilizable", "en": "Usable geometry"},
    "message.0196": {"es": "Estado de aceptación", "en": "Acceptance status"},
    "message.0197": {
        "es": "Catastro: INSPIRE. CEEE y PRTR: Comunidad de Madrid. Conservación y NDP: Ayuntamiento de Madrid, únicamente donde existe soporte. Cada fuente conserva fechas, ámbito y nivel de vínculo independientes.",
        "en": "Catastro: INSPIRE. CEEE and PRTR: Comunidad de Madrid. Maintenance records and NDP: Ayuntamiento de Madrid, only where supported. Each source retains its own dates, scope and link level.",
    },
    "message.0198": {"es": "Volver al objeto de origen · ", "en": "Back to origin object · "},
    "message.0199": {"es": "Municipio: ", "en": "Municipality: "},
    "message.0200": {"es": " · Identidad: ", "en": " · Identity: "},
    "message.0201": {"es": "Geometría utilizable: ", "en": "Usable geometry: "},
    "message.0202": {"es": " · Validación: ", "en": " · Validation: "},
    "message.0203": {
        "es": "Objeto constructivo consultado de forma independiente; no consta una relación documental confirmada con una parcela de las fuentes integradas",
        "en": "Cadastral structure queried independently; no confirmed documentary link to a parcel in the integrated sources is available",
    },
    "message.0204": {
        "es": "Relaciones documentales CP–BU (A validada; B/C incidencia)",
        "en": "Documentary CP–BU links (A validated; B/C issues)",
    },
    "message.0205": {
        "es": "Valores propios del objeto. No se suman superficies de Building y BuildingPart. BuildingPart no equivale a edificio completo. Nulos y estados se conservan; la condición catastral no es una inspección actual.",
        "en": "Object-specific values. Building and BuildingPart areas are not added together. BuildingPart does not mean a whole building. Null values and states are preserved; cadastral condition is not a current inspection.",
    },
    "message.0206": {
        "es": "Evidencias de parcela; no se trasladan al objeto BU ni a todas sus viviendas.",
        "en": "Parcel evidence is not transferred to the BU object or all its dwellings.",
    },
    "message.0207": {
        "es": "A: declaración y geometría concordantes según regla 95%/5%. B: incidencia documental o geométrica. C: sin CP aceptada resoluble. No acredita edificio físico ni atribuye CEEE, conservación o PRTR al BU.",
        "en": "A: consistent declaration and geometry under the 95%/5% rule. B: documentary or geometric issue. C: no resolvable accepted CP. This does not establish a physical building or attribute CEEE, maintenance records or PRTR to the BU.",
    },
    "message.0208": {
        "es": "Cobertura parcial de objetos observados; cuarentena excluida.",
        "en": "Partial coverage of observed objects; quarantined records excluded.",
    },
    "message.0209": {
        "es": "Captura municipal histórica de Madrid; no es un censo actualizado de edificios físicos.",
        "en": "Historical municipal capture of Madrid; not an up-to-date census of physical buildings.",
    },
    "message.0210": {
        "es": "Exportar ficha HTML · identificación y limitaciones",
        "en": "Export HTML record · identification and limitations",
    },
    "message.0211": {
        "es": "La exportación excluye evidencias pendientes de revisión de redistribución.",
        "en": "The export excludes evidence awaiting redistribution review.",
    },
    "message.0212": {
        "es": "). No se puede determinar la disponibilidad; identificación conservada.",
        "en": "). Availability cannot be determined; identification is preserved.",
    },
    "message.0213": {"es": "Evidencia del vínculo", "en": "Link evidence"},
    "message.0214": {"es": "objeto BU", "en": "BU object"},
    "message.0215": {"es": "Ubicación EPSG:25830: ", "en": "EPSG:25830 location: "},
    "message.0216": {"es": "Ubicación: ", "en": "Location: "},
    "message.0217": {"es": "Identificador de portal", "en": "Entrance identifier"},
    "message.0218": {"es": "Calidad del vínculo", "en": "Link quality"},
    "message.0219": {"es": "Accesos y dirección: ", "en": "Entrances and address: "},
    "message.0220": {
        "es": "Información protegida en modo público.",
        "en": "Information protected in public mode.",
    },
    "message.0221": {
        "es": "CEEE pertenece a la parcela y a su ámbito certificado; no se atribuye a este BU.",
        "en": "CEEE belongs to the parcel and its certified scope; it is not attributed to this BU.",
    },
    "message.0222": {
        "es": "PRTR protegido: reutilización sin acreditar.",
        "en": "PRTR protected: reuse has not been verified.",
    },
    "message.0223": {
        "es": "Las ayudas pertenecen al expediente y la parcela; no se atribuyen a este BU.",
        "en": "Grants belong to their cases and parcel; they are not attributed to this BU.",
    },
    "message.0224": {"es": "Snapshot: ", "en": "Snapshot: "},
    "message.0225": {"es": "Calidad documental: ", "en": "Documentary quality: "},
    "message.0226": {"es": " · Incidencias: ", "en": " · Issues: "},
    "message.0227": {
        "es": "Altura sobre rasante: no disponible en esta captura. La disponibilidad de uso, fechas, viviendas, plantas y superficie varía por objeto; consultar el detalle BU y sus estados, sin heredar valores.",
        "en": "Height above ground is unavailable in this capture. Use, dates, dwellings, floors and area vary by object; consult BU details and states without inheriting values.",
    },
    "message.0228": {"es": "Parcela catastral CP", "en": "Cadastral parcel CP"},
    "message.0229": {
        "es": "Objeto catastral BU independiente",
        "en": "Independent cadastral BU object",
    },
    "message.0230": {
        "es": "Referencia de parcela acreditada: ",
        "en": "Verified parcel reference: ",
    },
    "message.0231": {"es": "Relación BU–CP: ", "en": "BU–CP relationship: "},
    "message.0232": {"es": "captura histórica auditada", "en": "audited historical capture"},
    "message.0233": {"es": "Abrir parcela relacionada · ", "en": "Open linked parcel · "},
    "message.0234": {
        "es": " objetos BU con relación documental A · ",
        "en": " BU objects with documentary A links · ",
    },
    "message.0235": {"es": "Objeto BU", "en": "BU object"},
    "message.0236": {"es": "Construcción relacionada", "en": "Linked structure"},
    "message.0237": {"es": "Consultar construcción", "en": "View structure"},
    "message.0238": {
        "es": "Sin BU documental A en esta captura; no acredita ausencia de construcciones.",
        "en": "No documentary A-linked BU in this capture; this does not establish the absence of structures.",
    },
    "message.0239": {
        "es": " vínculos con incidencias, sin confirmación",
        "en": " links with issues, unconfirmed",
    },
    "message.0240": {"es": "Tipo de objeto: ", "en": "Object type: "},
    "message.0241": {
        "es": "Valores originales y procedencia de cada atributo",
        "en": "Original values and sources for each attribute",
    },
    "message.0242": {
        "es": "Campos no declarados válidos: ",
        "en": "Fields without valid declarations: ",
    },
    "message.0243": {
        "es": "Expedientes únicos de SUB_TOTAL_XY. Las otras capas describen componentes, no ayudas adicionales. No equivale a edificios físicos, pagos ni obras ejecutadas.",
        "en": "Unique cases from SUB_TOTAL_XY. The other layers describe components, not additional grants. These records do not establish physical buildings, payments or completed work.",
    },
    "message.0244": {
        "es": "Tipo de actuación · componente fuente",
        "en": "Work type · source component",
    },
    "message.0245": {"es": "Expedientes del filtro", "en": "Cases matching the filters"},
    "message.0246": {"es": "Expedientes con CP confirmada", "en": "Cases with a confirmed parcel"},
    "message.0247": {"es": "CP distintas confirmadas", "en": "Distinct confirmed parcels"},
    "message.0248": {
        "es": "Localización = punto de fuente; confirmación = dirección exacta, un acceso y una CP aceptada. Las coincidencias B/C permanecen pendientes y no se atribuyen como ayudas de una parcela.",
        "en": "Location is the source point; confirmation requires an exact address, one entrance and one accepted CP. B/C matches remain pending and are not attributed as parcel grants.",
    },
    "message.0249": {
        "es": "Datos aportados por usuario; captura original y licencia no verificadas. FECHA_ACTU es actualización, BOAM_C/BOCM_C son campos de publicación. No se conoce aquí el estado individual de pago o ejecución. PRTR se conserva como programa independiente.",
        "en": "Owner-supplied data; original capture date and licence unverified. FECHA_ACTU denotes an update; BOAM_C/BOCM_C are publication fields. Individual payment or completion status is unknown. PRTR remains a separate programme.",
    },
    "message.0250": {
        "es": "Consulta local deshabilitada en modo público: licencia y redistribución no acreditadas.",
        "en": "Local query disabled in public mode: reuse licence and redistribution have not been verified.",
    },
    "message.0251": {
        "es": "No hay expedientes para estos filtros.",
        "en": "No cases match these filters.",
    },
    "message.0252": {"es": "Expediente con parcela confirmada", "en": "Case with confirmed parcel"},
    "message.0253": {"es": "Consultar ficha vinculada", "en": "View linked property details"},
    "message.0254": {
        "es": "No se puede verificar el producto municipal.",
        "en": "The municipal product cannot be verified.",
    },
    "message.0255": {"es": "Mapa: ", "en": "Map: "},
    "message.0256": {
        "es": " puntos de expedientes confirmados, máximo 500. Varios puntos pueden referirse a la misma CP; no son edificios distintos.",
        "en": " confirmed case points, up to 500. Several points may refer to the same CP; they are not distinct buildings.",
    },
    "message.0257": {"es": "Detalle de fuente", "en": "Source details"},
    "message.0258": {
        "es": "Subvención revisada · céntimos por expediente",
        "en": "Revised subsidy · cents per case",
    },
    "message.0259": {
        "es": "Presupuesto protegible · céntimos por expediente",
        "en": "Eligible budget · cents per case",
    },
    "message.0260": {
        "es": "Expediente {case_id}\nParcela {parcel_ref14}",
        "en": "Case {case_id}\nParcel {parcel_ref14}",
    },
    "message.0261": {"es": "Fecha declarada en la fuente", "en": "Date declared in the source"},
    "message.0262": {"es": "Letra de consumo", "en": "Consumption rating"},
    "message.0263": {"es": "Letra de emisiones", "en": "Emissions rating"},
    "message.0264": {"es": "Consumo · unidad sin verificar", "en": "Consumption · unit unverified"},
    "message.0265": {"es": "Emisiones · unidad sin verificar", "en": "Emissions · unit unverified"},
    "message.0266": {"es": "Ámbito declarado", "en": "Declared scope"},
    "message.0267": {"es": "Nivel del vínculo", "en": "Link level"},
    "message.0268": {
        "es": "**Evidencia energética regional · fuentes integradas**",
        "en": "**Regional energy evidence · integrated sources**",
    },
    "message.0269": {
        "es": "Capturas disponibles, sin exhaustividad. Las fechas no acreditan vigencia. Una letra de vivienda no califica el edificio. Licencia energética pendiente: consulta local.",
        "en": "Available captures do not establish completeness. Dates do not establish current validity. A dwelling's rating does not rate the building. Energy licence pending: local query.",
    },
    "message.0270": {
        "es": "Parcelas solo con CEEE vinculado en estas fuentes",
        "en": "Parcels with only linked CEEE in these sources",
    },
    "message.0271": {
        "es": "Parcelas con CEEE y concesión PRTR",
        "en": "Parcels with CEEE and PRTR awards",
    },
    "message.0272": {
        "es": "Parcelas solo con concesión PRTR vinculada",
        "en": "Parcels with only linked PRTR awards",
    },
    "message.0273": {
        "es": "**Información energética regional**",
        "en": "**Regional energy information**",
    },
    "message.0274": {"es": "Consultar auditoría", "en": "View audit"},
    "message.0275": {
        "es": "A: relación documental con parcela aceptada; D: ambigua o en cuarentena. No se ha confirmado ningún objeto BU. Consumo y emisiones conservan valores originales con unidades sin verificar; no se comparan entre unidades distintas.",
        "en": "A: documentary relationship to an accepted parcel; D: ambiguous or quarantined. No BU object has been confirmed. Consumption and emissions retain their original values with unverified units; different units are not compared.",
    },
    "message.0276": {
        "es": "La coincidencia de CEEE y concesión PRTR en una parcela no acredita causalidad, pago ni obras ejecutadas. No se atribuye una calificación a la parcela.",
        "en": "Coexistence of CEEE and PRTR on a parcel does not establish causation, payment or completed work. No energy rating is assigned to the parcel.",
    },
    "message.0277": {"es": "Producto energético alterado", "en": "Energy product altered"},
    "message.0278": {"es": "Captura energética cambiada", "en": "Energy capture changed"},
    "message.0279": {
        "es": "Consultar energía de un municipio",
        "en": "View energy information for a municipality",
    },
    "message.0280": {
        "es": "Sin parcelario integrado para este municipio: no se puede calcular la coexistencia CEEE–PRTR por parcela. Los certificados municipales se conservan; no implica ausencia de ayudas.",
        "en": "No integrated parcels for this municipality: CEEE–PRTR coexistence cannot be calculated by parcel. Municipal certificates are preserved; this does not imply an absence of grants.",
    },
    "message.0281": {
        "es": "Fuente CEEE no disponible o protegida; consulta no realizada.",
        "en": "CEEE source unavailable or protected; no query performed.",
    },
    "message.0282": {
        "es": "Hay fechas posteriores a la captura o identidades de inscripción conflictivas. Consultar la auditoría antes de interpretar estas observaciones.",
        "en": "Some dates are later than capture or registration identities conflict. Consult the audit before interpreting these observations.",
    },
    "message.0283": {
        "es": "No constan expedientes PRTR con vínculo confirmado a esta parcela en las fuentes integradas; no acredita ausencia de otras ayudas.",
        "en": "No PRTR cases with confirmed links to this parcel in the integrated sources; this does not establish the absence of other grants.",
    },
    "message.0284": {
        "es": "Referencia con estructura válida: ",
        "en": "Structurally valid reference: ",
    },
    "message.0285": {
        "es": "%. Edificio completo declarado: ",
        "en": "%. Declared whole building: ",
    },
    "message.0286": {"es": "; ámbito desconocido: ", "en": "; unknown scope: "},
    "message.0287": {
        "es": ". Estructura válida no prueba existencia catastral.",
        "en": ". A valid structure does not prove cadastral existence.",
    },
    "message.0288": {"es": "Relación", "en": "Relationship"},
    "message.0289": {
        "es": "Consultar certificados de una parcela aceptada",
        "en": "View certificates for an accepted parcel",
    },
    "message.0290": {"es": "En esta parcela constan ", "en": "This parcel has "},
    "message.0291": {
        "es": " expedientes PRTR con vínculo confirmado en las fuentes integradas. Son concesiones administrativas; no se dispone de fecha de concesión individual contrastada. Los importes pertenecen al expediente y no se suman por parcela.",
        "en": " PRTR cases with confirmed links in the integrated sources. These are administrative awards; individual award dates have not been independently verified. Amounts belong to the case and must not be added across parcels.",
    },
    "message.0292": {"es": "Observaciones canónicas", "en": "Canonical records"},
    "message.0293": {"es": "Con parcela confirmada", "en": "With confirmed parcel"},
    "message.0294": {"es": "Primera fecha declarada", "en": "Earliest declared date"},
    "message.0295": {"es": "Última fecha declarada", "en": "Latest declared date"},
    "message.0296": {
        "es": "Catastro integrado (cobertura parcial)",
        "en": "Integrated Catastro (partial coverage)",
    },
    "message.0297": {
        "es": "Referencia documental y municipio concordantes",
        "en": "Consistent documentary reference and municipality",
    },
    "message.0298": {
        "es": "Varias parcelas o referencias de distinta calidad",
        "en": "Multiple parcels or references of different quality",
    },
    "message.0299": {"es": "Parcela en cuarentena", "en": "Quarantined parcel"},
    "message.0300": {
        "es": "Varias filas catastrales para la referencia",
        "en": "Multiple cadastral rows for the reference",
    },
    "message.0301": {
        "es": "Posible desplazamiento de columnas en origen",
        "en": "Possible source column shift",
    },
    "message.0302": {"es": "Sin parcelario integrado", "en": "No integrated parcels"},
    "message.0303": {"es": "Municipio sin verificar", "en": "Unverified municipality"},
    "message.0304": {
        "es": "Identificación documental insuficiente",
        "en": "Insufficient documentary identification",
    },
    "message.0305": {
        "es": "Fuente municipal histórica: obligaciones de presentación y órdenes, no actas ITE/IEE. Una orden antigua o una multa no acreditan deficiencias actuales. Archivo y terminación no acreditan subsanación. Parcela, acceso y edificio son entidades distintas. Cobertura parcial; la ausencia de registros no acredita ausencia de incidencias. Uso local.",
        "en": "Historical municipal source: filing requirements and orders, not ITE/IEE inspection reports. An old order or fine does not establish current defects. Archiving and closure do not establish rectification. Parcels, entrances and buildings are distinct entities. Partial coverage; an absence of records does not establish an absence of issues. Local use.",
    },
    "message.0306": {"es": "Orden de ejecución histórica", "en": "Historical enforcement order"},
    "message.0307": {"es": "Obligación de presentación ITE", "en": "ITE filing requirement"},
    "message.0308": {"es": "Obligación de presentación IEE", "en": "IEE filing requirement"},
    "message.0309": {"es": "Licencia concedida", "en": "Granted permit"},
    "message.0310": {
        "es": "Declaración responsable presentada",
        "en": "Responsible declaration filed",
    },
    "message.0311": {"es": "Tipo de actuación", "en": "Work type"},
    "message.0312": {"es": "Acceso/dirección de origen", "en": "Source entrance/address"},
    "message.0313": {"es": "Fecha administrativa", "en": "Administrative date"},
    "message.0314": {"es": "Naturaleza de la fecha", "en": "Date semantics"},
    "message.0315": {"es": "Fecha de consulta original", "en": "Original query date"},
    "message.0316": {"es": "Motivo original", "en": "Original reason"},
    "message.0317": {
        "es": "Situación administrativa original",
        "en": "Original administrative status",
    },
    "message.0318": {"es": "Fila original", "en": "Original row"},
    "message.0319": {"es": "SHA-256 original", "en": "Original SHA-256"},
    "message.0320": {"es": "Método de vínculo CP", "en": "CP linking method"},
    "message.0321": {"es": "Calidad de vínculo CP", "en": "CP link quality"},
    "message.0322": {
        "es": "Mención indirecta desfavorable en motivo de orden",
        "en": "Indirect unfavourable mention in an order's reason",
    },
    "message.0323": {
        "es": "**Conservación e inspecciones**",
        "en": "**Building maintenance and inspections**",
    },
    "message.0324": {
        "es": "Captura histórica de conservación independiente de la consulta REC bajo demanda.",
        "en": "Historical maintenance capture, separate from on-demand REC queries.",
    },
    "message.0325": {"es": "Captura de conservación cambiada", "en": "Maintenance capture changed"},
    "message.0326": {
        "es": "Producto de conservación alterado o incompatible",
        "en": "Maintenance product altered or incompatible",
    },
    "message.0327": {
        "es": "Captura de conservación con Catastro incompatible",
        "en": "Maintenance capture incompatible with Catastro",
    },
    "message.0328": {"es": "Captura cambió durante lectura", "en": "Capture changed while reading"},
    "message.0329": {"es": "Referencia CP no válida", "en": "Invalid CP reference"},
    "message.0330": {"es": "Producto no permitido", "en": "Product not allowed"},
    "message.0331": {
        "es": "Política de conservación incompatible",
        "en": "Incompatible maintenance policy",
    },
    "message.0332": {
        "es": "Catastro incompatible con conservación",
        "en": "Catastro incompatible with maintenance records",
    },
    "message.0333": {"es": "error de consulta de conservación", "en": "maintenance query error"},
    "message.0334": {
        "es": "Conservación · fuentes municipales integradas",
        "en": "Building maintenance · integrated municipal sources",
    },
    "message.0335": {
        "es": "No hay filtros de dictamen ni deficiencias: no se han integrado actas reales.",
        "en": "There are no assessment or defect filters: real inspection reports have not been integrated.",
    },
    "message.0336": {
        "es": "No constan órdenes ni obligaciones vinculadas en las fuentes integradas.",
        "en": "No orders or filing requirements linked in the integrated sources.",
    },
    "message.0337": {
        "es": "Accesos municipales con relación documental a esta parcela; no identifican edificio físico.",
        "en": "Municipal entrances linked to this parcel by documentary evidence; they do not identify a physical building.",
    },
    "message.0338": {
        "es": "Perfil explicable de evidencias vinculadas; sin diagnóstico ni puntuación de riesgo.",
        "en": "An explainable profile of linked evidence; no diagnosis or risk score.",
    },
    "message.0339": {"es": "Órdenes históricas", "en": "Historical orders"},
    "message.0340": {"es": "Obligaciones ITE observadas", "en": "Observed ITE filing requirements"},
    "message.0341": {"es": "Obligaciones IEE observadas", "en": "Observed IEE filing requirements"},
    "message.0342": {
        "es": "Última fecha administrativa (puede ser plazo)",
        "en": "Latest administrative date (may be a deadline)",
    },
    "message.0343": {
        "es": "Última consulta de obligaciones",
        "en": "Latest filing-requirement query",
    },
    "message.0344": {"es": "Contenidos CEEE vinculados", "en": "Linked CEEE records"},
    "message.0345": {"es": "Expedientes PRTR vinculados", "en": "Linked PRTR cases"},
    "message.0346": {
        "es": "Ámbitos de certificados observados",
        "en": "Observed certificate scopes",
    },
    "message.0347": {
        "es": "Certificados declarados de edificio completo",
        "en": "Declared whole-building certificates",
    },
    "message.0348": {
        "es": "CEEE y PRTR son evidencias independientes. Su coexistencia no acredita financiación de una orden, obras realizadas ni una calificación energética de la parcela.",
        "en": "CEEE and PRTR are independent evidence. Their coexistence does not establish funding for an order, completed work or an energy rating for the parcel.",
    },
    "message.0349": {"es": "Tipo de conservación", "en": "Maintenance record type"},
    "message.0350": {"es": "Año administrativo", "en": "Administrative year"},
    "message.0351": {"es": "Situación de origen", "en": "Source status"},
    "message.0352": {"es": "Fuente de conservación", "en": "Maintenance source"},
    "message.0353": {
        "es": "No se puede verificar la evidencia de conservación: ",
        "en": "Maintenance evidence cannot be verified: ",
    },
    "message.0354": {"es": "Información documentada", "en": "Documented information"},
    "message.0355": {
        "es": "Información asociada a parcela",
        "en": "Information linked to a parcel",
    },
    "message.0356": {"es": "Información parcial", "en": "Partial information"},
    "message.0357": {"es": "Vinculación ambigua", "en": "Ambiguous link"},
    "message.0358": {"es": "Información no disponible", "en": "Information unavailable"},
    "message.0359": {
        "es": "Fuente no cubierta para ese municipio",
        "en": "Source not covered for this municipality",
    },
    "message.0360": {"es": "Fecha no documentada", "en": "Date not documented"},
    "message.0361": {"es": "Agrícola", "en": "Agricultural"},
    "message.0362": {"es": "Servicios públicos", "en": "Public services"},
    "message.0363": {
        "es": "Objetos constructivos asociados a parcela",
        "en": "Structures linked to a parcel",
    },
    "message.0364": {"es": "Objeto BU consultado", "en": "Queried BU object"},
    "message.0365": {"es": "Consulta catastral · ", "en": "Cadastral query · "},
    "message.0366": {"es": "Años constructivos declarados", "en": "Declared construction years"},
    "message.0367": {"es": "Superficie bruta de plantas (m²)", "en": "Gross floor area (m²)"},
    "message.0368": {
        "es": "Viviendas declaradas por objeto",
        "en": "Declared dwellings per object",
    },
    "message.0369": {
        "es": "Plantas sobre rasante por objeto",
        "en": "Floors above ground per object",
    },
    "message.0370": {
        "es": "Plantas bajo rasante por objeto",
        "en": "Floors below ground per object",
    },
    "message.0371": {"es": "Unidades declaradas por objeto", "en": "Declared units per object"},
    "message.0372": {"es": "Condición catastral declarada", "en": "Declared cadastral condition"},
    "message.0373": {
        "es": "Revisar el encaje del producto de financiación: constan usos distintos del residencial en los objetos consultados.",
        "en": "Check the suitability of the financing product: non-residential uses are declared for the queried objects.",
    },
    "message.0374": {
        "es": "Ayuntamiento de Madrid · índice S20",
        "en": "Ayuntamiento de Madrid · S20 index",
    },
    "message.0375": {"es": "Versión postal de acceso", "en": "Entrance address version"},
    "message.0376": {"es": "Índice postal S20", "en": "S20 address index"},
    "message.0377": {"es": "Acceso seleccionado", "en": "Selected entrance"},
    "message.0378": {"es": "Parcela; no comunidades", "en": "Parcel; not owners' associations"},
    "message.0379": {
        "es": "Comprobar qué portal y comunidad corresponden al interlocutor: la parcela tiene varios accesos documentados.",
        "en": "Check which entrance and owners' association correspond to your contact: the parcel has several documented entrances.",
    },
    "message.0380": {"es": "Contenido CEEE", "en": "CEEE record"},
    "message.0381": {
        "es": "Contenido canónico, no inmueble único ni certificado vigente verificado; no califica la parcela o todo el edificio. Magnitudes de la unidad certificada; unidades solo según estado de la fuente, sin suponer kWh/m² o m².",
        "en": "Canonical record, not a unique property or a certificate with verified current validity; it does not rate the parcel or entire building. Values relate to the certified unit; units are retained only as supported by the source, without assuming kWh/m² or m².",
    },
    "message.0382": {"es": "Concesión PRTR", "en": "PRTR award"},
    "message.0383": {
        "es": "Expediente vinculado a parcela; importe del expediente único",
        "en": "Case linked to a parcel; amount belongs to the unique case",
    },
    "message.0384": {
        "es": "Antecedente administrativo de parcela",
        "en": "Parcel administrative record",
    },
    "message.0385": {
        "es": "Obligación no es resultado; orden histórica no acredita deficiencias actuales ni subsanación.",
        "en": "A filing requirement is not a result; a historical order does not establish current defects or rectification.",
    },
    "message.0386": {
        "es": "Solicitar al interlocutor el certificado energético disponible: no consta un CEEE documental utilizable en estas fuentes.",
        "en": "Ask your contact for the available energy certificate: no usable documentary CEEE is recorded in these sources.",
    },
    "message.0387": {
        "es": "Comprobar compatibilidad de ayudas y estado real de la actuación; la concesión no acredita pago ni obras.",
        "en": "Check grant compatibility and the actual stage of the project; an award does not establish payment or work.",
    },
    "message.0388": {
        "es": "Verificar el resultado vigente de ITE/IEE: los antecedentes disponibles son históricos u obligaciones de presentación.",
        "en": "Verify the current ITE/IEE outcome: available records are historical or filing requirements.",
    },
    "message.0389": {
        "es": "Vínculo documental a parcela; no identifica un edificio físico único.",
        "en": "Documentary parcel link; does not identify a unique physical building.",
    },
    "message.0390": {"es": "Dirección postal", "en": "Postal address"},
    "message.0391": {"es": "Auditoría postal S20", "en": "S20 address audit"},
    "message.0392": {"es": "Municipio piloto", "en": "Pilot municipality"},
    "message.0393": {"es": "Parcela CP", "en": "CP parcel"},
    "message.0394": {
        "es": "Recuento de objetos catastrales; no edificios físicos ni comunidades.",
        "en": "Count of cadastral objects, not physical buildings or owners' associations.",
    },
    "message.0395": {"es": "Registro declarado", "en": "Declared registration"},
    "message.0396": {"es": "Dirección certificada", "en": "Certified address"},
    "message.0397": {"es": "Tipo certificado original", "en": "Original certificate type"},
    "message.0398": {"es": "Estado de magnitudes", "en": "Measurement status"},
    "message.0399": {"es": "Consumo declarado", "en": "Declared consumption"},
    "message.0400": {"es": "Unidad consumo", "en": "Consumption unit"},
    "message.0401": {"es": "Emisiones declaradas", "en": "Declared emissions"},
    "message.0402": {"es": "Unidad emisiones", "en": "Emissions unit"},
    "message.0403": {"es": "Superficie certificada", "en": "Certified area"},
    "message.0404": {"es": "Unidad superficie", "en": "Area unit"},
    "message.0405": {"es": "Comunidad de Madrid · CEEE · ", "en": "Comunidad de Madrid · CEEE · "},
    "message.0406": {"es": "Estados documentales", "en": "Documentary statuses"},
    "message.0407": {"es": "Fecha de concesión declarada", "en": "Declared award date"},
    "message.0408": {"es": "Actualización fuente", "en": "Source update"},
    "message.0409": {
        "es": "Concesión no acredita pago, inicio ni terminación de obras. No sumar por parcelas.",
        "en": "An award does not establish payment, start or completion of work. Do not add amounts across parcels.",
    },
    "message.0410": {
        "es": "Expediente municipal relacionado con acceso y CP; no edificio físico",
        "en": "Municipal case linked to an entrance and CP; not a physical building",
    },
    "message.0411": {
        "es": "Importe revisado por expediente único, sin reparto ni suma por CP o capas. No acredita pago, obra iniciada/ejecutada, necesidad actual de financiación ni equivalencia con PRTR. Viviendas del ámbito del expediente, no del portal. Fechas de publicación no son fecha individual de concesión.",
        "en": "Revised amount per unique case, without allocation or addition across CP or layers. Does not establish payment, started/completed work, current financing needs or equivalence with PRTR. Dwellings belong to the case's scope, not the entrance. Publication dates are not individual award dates.",
    },
    "message.0412": {"es": "Significado de fecha", "en": "Date semantics"},
    "message.0413": {"es": "Situación original", "en": "Original status"},
    "message.0414": {"es": "Expediente original", "en": "Original case reference"},
    "message.0415": {"es": "Acceso NDP declarado", "en": "Declared NDP entrance"},
    "message.0416": {"es": "Dirección original del antecedente", "en": "Original record address"},
    "message.0417": {"es": "Calle declarada", "en": "Declared street"},
    "message.0418": {"es": "Número declarado", "en": "Declared house number"},
    "message.0419": {"es": "Fecha de fuente no documentada", "en": "Source date not documented"},
    "message.0420": {"es": "BU histórico agregado", "en": "Historical aggregated BU"},
    "message.0421": {
        "es": "Valores por objeto, sin suma; no se atribuyen al portal. BuildingPart no equivale a edificio completo.",
        "en": "Values per object, not added together or attributed to an entrance. BuildingPart does not mean a whole building.",
    },
    "message.0422": {"es": "Fecha no disponible", "en": "Date unavailable"},
    "message.0423": {
        "es": "Fecha individual de concesión no contrastada",
        "en": "Individual award date not independently verified",
    },
    "message.0424": {
        "es": " P4 corresponde a vivienda y no se extiende al edificio.",
        "en": " P4 relates to a dwelling and does not extend to the building.",
    },
    "message.0425": {"es": "Dirección original", "en": "Original address"},
    "message.0426": {"es": "Actuaciones por componente fuente", "en": "Work by source component"},
    "message.0427": {
        "es": "Viviendas declaradas del expediente",
        "en": "Declared dwellings in the case",
    },
    "message.0428": {
        "es": "Presupuesto protegible del expediente (€)",
        "en": "Case eligible budget (€)",
    },
    "message.0429": {
        "es": "Subvención revisada del expediente (€)",
        "en": "Case revised subsidy (€)",
    },
    "message.0430": {"es": "BOAM_C · publicación según campo", "en": "BOAM_C · publication field"},
    "message.0431": {"es": "BOCM_C · publicación según campo", "en": "BOCM_C · publication field"},
    "message.0432": {"es": "Actualización de fuente", "en": "Source update"},
    "message.0433": {"es": "Estado individual", "en": "Individual status"},
    "message.0434": {"es": "Captura original", "en": "Original capture"},
    "message.0435": {"es": "No verificado en esta captura", "en": "Not verified in this capture"},
    "message.0436": {
        "es": "Fecha no acreditada; ZIP aportado por usuario",
        "en": "Date unverified; owner-supplied ZIP",
    },
    "message.0437": {
        "es": "Ayuntamiento de Madrid · SUB_TOTAL_XY · ",
        "en": "Ayuntamiento de Madrid · SUB_TOTAL_XY · ",
    },
    "message.0438": {
        "es": "Fecha de fuente en detalle técnico",
        "en": "Source date in technical details",
    },
    "message.0439": {"es": "Municipio", "en": "Municipality"},
    "message.0440": {"es": "Distrito", "en": "District"},
    "message.0441": {"es": "Producto", "en": "Product"},
    "message.0442": {"es": "Buscar", "en": "Search"},
    "message.0443": {"es": "Convocatoria", "en": "Call for applications"},
    "message.0444": {"es": "Local", "en": "Commercial unit"},
    "message.0445": {"es": "Desconocido", "en": "Unknown"},
    "message.0446": {"es": "Licencias", "en": "Permits"},
    "message.0447": {"es": "Valor", "en": "Value"},
    "message.0448": {"es": "Dato", "en": "Item"},
    "message.0449": {"es": "Fuente", "en": "Source"},
    "message.0450": {"es": "Calidad", "en": "Quality"},
    "message.0451": {"es": "Consumo", "en": "Consumption"},
    "message.0452": {"es": "Emisiones", "en": "Emissions"},
    "message.0453": {"es": "Programa", "en": "Programme"},
    "message.0454": {"es": "Fecha", "en": "Date"},
    "message.0455": {"es": "Calle", "en": "Street"},
    "message.0456": {"es": "Complemento", "en": "Additional details"},
    "message.0457": {"es": "Tipo", "en": "Type"},
    "message.0458": {"es": "Atributo", "en": "Attribute"},
    "message.0459": {"es": "Estado", "en": "State"},
    "message.0460": {"es": "Residencial", "en": "Residential"},
    "message.0461": {"es": "Industrial", "en": "Industrial"},
    "message.0462": {"es": "Comercio", "en": "Retail"},
    "message.0463": {"es": "Oficinas", "en": "Offices"},
    "message.0464": {"es": "parcela", "en": "parcel"},
    "message.0465": {"es": "Ayudas", "en": "Grants"},
    "filters.energy": {"es": "Solo CEEE", "en": "Energy certificates"},
    "filters.inspections": {"es": "Solo ITE/IEE", "en": "Building inspections (ITE/IEE)"},
    "filters.rehabilita": {"es": "Solo Plan Rehabilita", "en": "Plan Rehabilita"},
    "filters.prtr": {"es": "Solo ayudas PRTR", "en": "PRTR grants"},
    "message.0470": {"es": "CEEE", "en": "CEEE"},
    "message.0471": {"es": "ITE/IEE", "en": "ITE/IEE"},
    "message.0472": {"es": "ayudas PRTR", "en": "PRTR grants"},
    "message.0473": {
        "es": "Datos constructivos documentados",
        "en": "Documented construction data",
    },
    "message.0474": {
        "es": "Antecedente administrativo confirmado",
        "en": "Confirmed administrative record",
    },
    "message.0475": {
        "es": "No hay información suficiente para ofrecer una ficha comercial de esta dirección.",
        "en": "There is not enough information to offer commercial details for this address.",
    },
    "message.0476": {
        "es": "Publicación externa bloqueada: licencia/procedencia de PRTR y Plan Rehabilita pendientes. Sus filtros y evidencias están deshabilitados en modo público. La membresía pública del catálogo no autoriza la redistribución.",
        "en": "External publication blocked: PRTR and Plan Rehabilita reuse licences and provenance remain unverified. Their filters and evidence are disabled in public mode. Public catalogue membership does not authorise redistribution.",
    },
    "message.0477": {
        "es": "Información orientativa basada en fuentes públicas, no certificación oficial. Una parcela no equivale a un edificio. Ausencia de evidencia no significa estado favorable. Las observaciones individuales no califican el edificio. Sin diagnóstico ni score financiero.",
        "en": "Guidance based on public sources, not official certification. A parcel is not the same as a building. Missing evidence does not imply favourable condition. Individual observations do not rate the building. No diagnosis or financial score.",
    },
    "message.0478": {
        "es": "Información comercial suficiente",
        "en": "Sufficient commercial information",
    },
    "message.0479": {"es": "Información comercial parcial", "en": "Partial commercial information"},
    "message.0480": {"es": "Información suficiente", "en": "Sufficient information"},
    "message.0481": {"es": "Información insuficiente", "en": "Insufficient information"},
    "message.0482": {"es": " de ", "en": " of "},
    "message.0483": {"es": " a ", "en": " to "},
    "message.0484": {"es": "acceso ", "en": "entrance "},
    "message.0485": {"es": "Ámbito", "en": "Scope"},
    "message.0486": {"es": "Situación", "en": "Status"},
    "message.0487": {"es": "Versión", "en": "Version"},
    "message.0488": {"es": " parcela(s) confirmada(s) · ", "en": " confirmed parcel(s) · "},
    "message.0489": {
        "es": " relaciones ambiguas o contenidos con incidencias, excluidos del recuento documental utilizable.",
        "en": " ambiguous links or records with issues, excluded from the usable documentary count.",
    },
    "message.0490": {"es": " valores distintos", "en": " distinct values"},
    "message.0491": {"es": " · acceso ", "en": " · entrance "},
    "message.0492": {"es": ": consulta fallida (", "en": ": query failed ("},
    "message.0493": {"es": "; vivienda individual: ", "en": "; individual dwelling: "},
    "message.0494": {
        "es": "Información suficiente para una primera consulta",
        "en": "Sufficient information for an initial review",
    },
    "message.0495": {
        "es": "\n**Madrid Rehab Intelligence** es un proyecto personal que nace con una idea sencilla: reunir en un mismo lugar información pública sobre edificios para que sea más fácil conocer sus características y explorar posibles actuaciones de rehabilitación.\n\nActualmente, la herramienta permite consultar información sobre edificios y parcelas de Madrid y otros cinco municipios de la Comunidad de Madrid.\n\nPuedes encontrar datos sobre su antigüedad, características constructivas, eficiencia energética, inspecciones y antecedentes administrativos, así como determinadas ayudas públicas relacionadas con la rehabilitación.\n",
        "en": "\n**Madrid Rehab Intelligence** is a personal project built around a simple idea: bring public information about buildings together in one place, making it easier to understand their characteristics and explore possible renovation projects.\n\nThe tool currently provides information about buildings and cadastral parcels in Madrid and five other municipalities in Comunidad de Madrid, the region surrounding the city.\n\nYou can explore documented age, construction characteristics, energy performance, inspection-related requirements and administrative records, as well as selected public grants connected with renovation.\n",
    },
    "message.0496": {
        "es": "\nMadrid Rehab Intelligence todavía está en una fase inicial de desarrollo. Lo que ves es un primer prototipo, pensado para demostrar lo que se puede conseguir combinando distintas fuentes de información.\n\nLa idea es seguir mejorándolo poco a poco: incorporar nuevos datos, ampliar la cobertura geográfica, facilitar las búsquedas y desarrollar herramientas que ayuden a comprender mejor la situación de los edificios.\n\nQueremos que, con el tiempo, sea cada vez más fácil encontrar información útil sin tener que consultar numerosas páginas y registros por separado.\n",
        "en": "\nMadrid Rehab Intelligence is still at an early stage. What you see is an initial prototype, designed to demonstrate what can be achieved by connecting different information sources.\n\nThe plan is to improve it gradually: add more data, extend geographic coverage, make searching easier and develop tools that help people understand the available evidence about buildings.\n\nOver time, we hope it will become easier to find useful information without visiting numerous separate websites and registers.\n",
    },
    "message.0497": {
        "es": "\n- **Explorar un mapa:** descubrir inmuebles sobre los que existe información disponible.\n- **Consultar sus características:** conocer datos constructivos documentados.\n- **Examinar su información energética:** consultar certificados energéticos vinculados.\n- **Investigar antecedentes:** encontrar obligaciones de inspección y otros registros administrativos disponibles.\n- **Consultar ayudas públicas:** identificar expedientes de rehabilitación relacionados con las parcelas.\n\nLa disponibilidad de estas funciones puede variar según el municipio y las fuentes autorizadas para su consulta.\n",
        "en": "\n- **Explore a map:** discover properties with available information.\n- **View their characteristics:** examine documented construction data.\n- **Explore energy information:** view linked energy performance certificates.\n- **Research administrative records:** find inspection filing requirements and other available records.\n- **Explore public grants:** identify renovation cases linked to parcels.\n\nAvailability varies by municipality and by the sources authorised for consultation.\n",
    },
    "message.0498": {
        "es": "\nUtilizamos información procedente de organismos públicos como la Dirección General del Catastro, la Comunidad de Madrid y el Ayuntamiento de Madrid.\n\nCada fuente tiene su propia cobertura, fecha de actualización y limitaciones. Puedes consultar su procedencia en las fichas.\n\n- [Dirección General del Catastro](https://www.catastro.hacienda.gob.es/): productos INSPIRE; se deben aplicar las condiciones del producto de origen.\n- CEEE · Comunidad de Madrid: CC BY 4.0 según el catálogo local. Los certificados conservan su ámbito documental.\n- Conservación y callejero · Ayuntamiento de Madrid: obligaciones y antecedentes disponibles; no hay resultados reales de inspecciones integrados.\n- PRTR · visor de rehabilitación de la Comunidad de Madrid alojado en COAM; Plan Rehabilita · Ayuntamiento de Madrid, captura local facilitada por el usuario. Licencia y procedencia de reutilización pendientes de verificar; consulta bloqueada en modo público.\n\nLos vínculos ambiguos no se convierten en confirmaciones. Los importes pertenecen a expedientes únicos y no se suman por parcela.\n",
        "en": "\nWe use information published by public bodies including Dirección General del Catastro (Spain's cadastral authority), Comunidad de Madrid (the regional government) and Ayuntamiento de Madrid (Madrid's city council).\n\nEach source has its own coverage, update date and limitations. Property details retain their source information.\n\n- [Dirección General del Catastro](https://www.catastro.hacienda.gob.es/): INSPIRE products; the terms of the original product must be applied.\n- CEEE · Comunidad de Madrid: Spanish energy performance certificates, CC BY 4.0 according to the local catalogue. Each certificate retains its documentary scope.\n- Maintenance records and street directory · Ayuntamiento de Madrid: available filing requirements and administrative records. No actual inspection outcomes have been integrated. ITE/IEE are Spanish building inspection and evaluation requirements; an obligation to file a report is not an inspection result.\n- PRTR · Comunidad de Madrid rehabilitation viewer hosted by COAM. PRTR is Spain's Recovery, Transformation and Resilience Plan. Plan Rehabilita · Ayuntamiento de Madrid, local capture supplied by the owner. Reuse licence and provenance remain unverified; access is blocked in public mode.\n\nAmbiguous links are not treated as confirmations. Amounts belong to unique cases and must not be added across parcels.\n",
    },
    "message.0499": {
        "es": "\nEl mapa comercial incluye Madrid, Getafe, Móstoles, Leganés, Alcorcón y Alcalá de Henares. La cobertura catastral de los cinco últimos es parcial.\n\nLa búsqueda por dirección está disponible para Madrid capital; no es una búsqueda postal completa de los otros cinco municipios. Madrid utiliza las asignaciones distritales del producto procesado, sin inferir distritos por proximidad. Las parcelas sin asignación fiable se conservan en «Todos los distritos».\n\nLa cobertura varía por fuente. Plan Rehabilita corresponde a Madrid y la fuente de conservación no está integrada en los otros cinco municipios. Ausencia de datos no significa ausencia de ayudas o antecedentes.\n",
        "en": "\nThe commercial map covers Madrid, Getafe, Móstoles, Leganés, Alcorcón and Alcalá de Henares. Cadastral coverage in the latter five municipalities is partial.\n\nAddress search is available for Madrid city; it is not a complete address search for the other five municipalities. Madrid uses district assignments from the processed product, without inferring districts from proximity. Parcels without a reliable assignment remain under “All districts”.\n\nCoverage varies by source. Plan Rehabilita relates to Madrid, and maintenance records have not been integrated for the other five municipalities. Missing data does not establish the absence of grants or administrative records.\n",
    },
    "message.0500": {
        "es": "\nLos datos pueden estar incompletos o desactualizados, y no todos los edificios disponen de la misma información.\n\nAdemás, una parcela catastral puede contener varios edificios o accesos. Un certificado energético de una vivienda no describe necesariamente todo el edificio, y una subvención concedida no significa que las obras hayan terminado.\n\n**La herramienta no determina si un edificio necesita rehabilitación.** Su objetivo es facilitar la consulta y el análisis inicial de información disponible.\n\nPara tomar decisiones concretas, siempre será necesario contrastar los datos con documentación actualizada y fuentes oficiales.\n",
        "en": "\nThe data may be incomplete or out of date, and the same information is not available for every building.\n\nA cadastral parcel may contain several buildings or entrances. A dwelling's energy performance certificate does not necessarily describe the whole building, and a grant award does not mean that work has been completed.\n\n**The tool does not determine whether a building needs renovation.** Its purpose is to make available information easier to consult and support an initial review.\n\nBefore making specific decisions, always check the data against up-to-date documentation and official sources.\n",
    },
    "message.0501": {
        "es": "\nNuestro objetivo es incorporar progresivamente:\n\n- Más información sobre edificios y su estado de conservación.\n- Nuevas fuentes de certificados energéticos e inspecciones.\n- Información adicional sobre programas de ayudas.\n- Más municipios y mejores herramientas de búsqueda.\n- Mapas, filtros y fichas cada vez más claros y útiles.\n\n**Esto es solo el principio.** Madrid Rehab Intelligence seguirá evolucionando a medida que encontremos nuevas fuentes de información y formas más útiles de conectarlas.\n",
        "en": "\nWe would like to add progressively:\n\n- More information about buildings and their state of repair.\n- Additional sources of energy certificates and inspection information.\n- More information about grant programmes.\n- More municipalities and better search tools.\n- Clearer, more useful maps, filters and property details.\n\n**This is just the beginning.** Madrid Rehab Intelligence will continue to evolve as we find new information sources and more useful ways to connect them.\n",
    },
    "template.000": {
        "es": "{v0} parcelas en esta página del mapa; máximo 500 por carga. La lista permite recorrer todo el conjunto filtrado.",
        "en": "{v0} parcels on this map page; up to 500 per load. Use the list to browse the full filtered result set.",
    },
    "template.001": {
        "es": "{v0} coincidencias · página {v1} de {v2}",
        "en": "{v0} matches · page {v1} of {v2}",
    },
    "template.002": {
        "es": "{v0} · {v1} · {v2} · {v3} parcela(s) confirmada(s) · {v4} · acceso {v5} / versión {v6}",
        "en": "{v0} · {v1} · {v2} · {v3} confirmed parcel(s) · {v4} · entrance {v5} / version {v6}",
    },
    "template.003": {
        "es": "{v0} relaciones ambiguas o contenidos con incidencias, excluidos del recuento documental utilizable.",
        "en": "{v0} ambiguous links or records with issues, excluded from the usable documentary count.",
    },
    "template.004": {
        "es": "{v0}: consulta no verificable. No se interpreta como ausencia de registros.",
        "en": "{v0}: query cannot be verified. This is not interpreted as an absence of records.",
    },
    "template.005": {"es": "Corte catastral: {v0} · {v1}", "en": "Cadastral snapshot: {v0} · {v1}"},
    "template.006": {
        "es": "{v0} contenidos CEEE vinculados documentalmente a parcela.",
        "en": "{v0} CEEE records linked to the parcel by documentary evidence.",
    },
    "template.007": {
        "es": "{v0} expedientes PRTR con concesión asociada documentalmente a parcela.",
        "en": "{v0} PRTR award cases linked to the parcel by documentary evidence.",
    },
    "template.008": {
        "es": "{v0} expedientes municipales con relación documental confirmada a la parcela.",
        "en": "{v0} municipal cases with confirmed documentary links to the parcel.",
    },
    "template.009": {"es": "{v0} · {v1} · Fuente: {v2}", "en": "{v0} · {v1} · Source: {v2}"},
    "template.010": {"es": "{v0} a {v1}", "en": "{v0} to {v1}"},
    "template.011": {
        "es": "{v0} · {v1} · Importe del expediente: ",
        "en": "{v0} · {v1} · Case amount: ",
    },
    "template.012": {"es": " · {v0} valores distintos", "en": " · {v0} distinct values"},
    "template.013": {"es": "Ficha de {v0} · {v1}", "en": "Details for {v0} · {v1}"},
    "template.014": {
        "es": "Municipio: {v0} · Identidad: {v1}",
        "en": "Municipality: {v0} · Identity: {v1}",
    },
    "template.015": {
        "es": "Geometría utilizable: {v0} · Validación: {v1}",
        "en": "Usable geometry: {v0} · Validation: {v1}",
    },
    "template.016": {
        "es": "{v0}: consulta fallida ({v1}). No se puede determinar la disponibilidad; identificación conservada.",
        "en": "{v0}: query failed ({v1}). Availability cannot be determined; identification is preserved.",
    },
    "template.017": {
        "es": "Ubicación EPSG:25830: {v0}, {v1}",
        "en": "EPSG:25830 location: {v0}, {v1}",
    },
    "template.018": {
        "es": "Calidad documental: {v0} · Incidencias: {v1}",
        "en": "Documentary quality: {v0} · Issues: {v1}",
    },
    "template.019": {
        "es": "Referencia de parcela acreditada: {v0}",
        "en": "Verified parcel reference: {v0}",
    },
    "template.020": {
        "es": "{v0} objetos BU con relación documental A · {v1} Building · {v2} BuildingPart",
        "en": "{v0} BU objects with documentary A links · {v1} Building · {v2} BuildingPart",
    },
    "template.021": {
        "es": "{v0} vínculos con incidencias, sin confirmación",
        "en": "{v0} links with issues, unconfirmed",
    },
    "template.022": {
        "es": "Mapa: {v0} puntos de expedientes confirmados, máximo 500. Varios puntos pueden referirse a la misma CP; no son edificios distintos.",
        "en": "Map: {v0} confirmed case points, up to 500. Several points may refer to the same CP; they are not distinct buildings.",
    },
    "template.023": {
        "es": "Referencia con estructura válida: {v0}%. Edificio completo declarado: {v1}; vivienda individual: {v2}; ámbito desconocido: {v3}. Estructura válida no prueba existencia catastral.",
        "en": "Structurally valid reference: {v0}%. Declared whole building: {v1}; individual dwelling: {v2}; unknown scope: {v3}. A valid structure does not prove cadastral existence.",
    },
    "template.024": {
        "es": "En esta parcela constan {v0} expedientes PRTR con vínculo confirmado en las fuentes integradas. Son concesiones administrativas; no se dispone de fecha de concesión individual contrastada. Los importes pertenecen al expediente y no se suman por parcela.",
        "en": "This parcel has {v0} PRTR cases with confirmed links in the integrated sources. These are administrative awards; individual award dates have not been independently verified. Amounts belong to the case and must not be added across parcels.",
    },
    "template.025": {
        "es": "No se puede verificar la evidencia de conservación: {v0}",
        "en": "Maintenance evidence cannot be verified: {v0}",
    },
}


MESSAGES.update(
    {
        "additional.000": {"es": "Ámbitos", "en": "Scopes"},
        "additional.001": {"es": "Fechas declaradas", "en": "Declared dates"},
        "additional.002": {"es": "Ficha documentada", "en": "Documented property record"},
        "additional.003": {
            "es": "Ficha parcial con evidencia",
            "en": "Partial record with evidence",
        },
        "additional.004": {"es": "Registro técnico excluido", "en": "Excluded technical record"},
        "additional.005": {"es": " accesos", "en": " entrances"},
        "additional.006": {
            "es": "**ITE / IEE — Registro municipal**",
            "en": "**ITE / IEE — Municipal register**",
        },
        "additional.007": {
            "es": "Información orientativa procedente del REC municipal; no constituye una certificación oficial",
            "en": "Guidance from the municipal REC register; not official certification",
        },
        "additional.008": {
            "es": "Vínculo documental CP–NDP confirmado",
            "en": "Confirmed documentary CP–NDP link",
        },
        "additional.009": {
            "es": "Resultado obtenido correctamente",
            "en": "Result retrieved successfully",
        },
        "additional.010": {
            "es": "Sin inspecciones registradas en la respuesta consultada",
            "en": "No inspections recorded in the retrieved response",
        },
        "additional.011": {"es": "Dirección: ", "en": "Address: "},
        "additional.012": {
            "es": "Fuente: REC del Ayuntamiento de Madrid · Consulta: ",
            "en": "Source: REC, Ayuntamiento de Madrid · Queried: ",
        },
        "additional.013": {"es": " · Verificación: ", "en": " · Verification: "},
        "additional.014": {
            "es": "Captura local histórica de prueba; no es una consulta actual al REC",
            "en": "Historical local test capture; not a current REC query",
        },
        "additional.015": {
            "es": "Información del acceso y sus expedientes; no acredita el estado físico actual ni se extiende a todos los edificios de la parcela.",
            "en": "Information about the entrance and its cases; it does not establish current physical condition or extend to every building on the parcel.",
        },
        "additional.016": {"es": "Expediente", "en": "Case reference"},
        "additional.017": {"es": "Presentación", "en": "Filing date"},
        "additional.018": {"es": "Dictamen", "en": "Assessment"},
        "additional.019": {"es": "Alcance", "en": "Scope"},
        "additional.020": {"es": "Causa desfavorable", "en": "Unfavourable reason"},
        "additional.021": {"es": "Situación administrativa", "en": "Administrative status"},
        "additional.022": {"es": "Dependencia", "en": "Department"},
        "additional.023": {"es": "Expediente de seguimiento", "en": "Follow-up case"},
        "additional.024": {"es": "Incumplimiento", "en": "Non-compliance"},
        "additional.025": {"es": "Fecha resolución", "en": "Resolution date"},
        "additional.026": {"es": "Resolución", "en": "Resolution"},
        "additional.027": {"es": "Antecedentes", "en": "Prior records"},
        "additional.028": {"es": "Subsanación literal", "en": "Rectification (original wording)"},
        "additional.029": {"es": "Historial administrativo", "en": "Administrative history"},
        "additional.030": {
            "es": "Sin registros en esta respuesta.",
            "en": "No records in this response.",
        },
        "additional.031": {
            "es": "ARCHIVADO o TERMINADO no equivale a SUBSANADO. Se conservan los literales y expedientes independientes.",
            "en": "ARCHIVADO (archived) or TERMINADO (closed) does not mean SUBSANADO (rectified). Original wording and independent cases are preserved.",
        },
        "additional.032": {
            "es": "Consulta REC y accesos NDP de Madrid no aplicables a este municipio.",
            "en": "Madrid REC queries and NDP entrances do not apply to this municipality.",
        },
        "additional.033": {"es": "Seleccionar portal municipal", "en": "Select municipal entrance"},
        "additional.034": {
            "es": "Seleccione expresamente un acceso",
            "en": "Select an entrance explicitly",
        },
        "additional.035": {
            "es": "No se ha identificado un acceso municipal suficientemente verificado",
            "en": "No sufficiently verified municipal entrance has been identified",
        },
        "additional.036": {
            "es": "NDP ambiguo o relación CP–NDP no confirmada; esos accesos no son consultables.",
            "en": "Ambiguous NDP or unconfirmed CP–NDP link; these entrances cannot be queried.",
        },
        "additional.037": {"es": "Parcela candidata", "en": "Candidate parcel"},
        "additional.038": {
            "es": "Referencia catastral de parcela",
            "en": "Cadastral parcel reference",
        },
        "additional.039": {
            "es": "No se puede verificar el puente municipal: ",
            "en": "The municipal link cannot be verified: ",
        },
        "additional.040": {"es": "Abrir ficha oficial del REC", "en": "Open official REC record"},
        "additional.041": {
            "es": "Consulta integrada no habilitada",
            "en": "Integrated query disabled",
        },
        "additional.042": {"es": "Consultar ITE/IEE", "en": "Query ITE/IEE"},
        "additional.043": {"es": "Captura", "en": "Capture"},
        "additional.044": {"es": "Plantas sobre rasante", "en": "Floors above ground"},
        "additional.045": {"es": "Plantas bajo rasante", "en": "Floors below ground"},
        "additional.046": {"es": "Altura bajo rasante (m)", "en": "Height below ground (m)"},
        "additional.047": {"es": "Altura sobre rasante (m)", "en": "Height above ground (m)"},
        "additional.048": {
            "es": "Rehabilitación a nivel de barrio",
            "en": "Neighbourhood-level renovation",
        },
        "additional.049": {
            "es": "Rehabilitación a nivel de edificio",
            "en": "Building-level renovation",
        },
        "additional.050": {
            "es": "Mejora de eficiencia energética en viviendas",
            "en": "Energy efficiency improvements in dwellings",
        },
        "additional.051": {
            "es": "Libro del edificio existente y proyectos de rehabilitación",
            "en": "Existing-building logbook and renovation projects",
        },
        "additional.052": {"es": "NDP inválido", "en": "Invalid NDP"},
        "additional.053": {"es": "Redirección a otro NDP", "en": "Redirect to a different NDP"},
        "additional.054": {
            "es": "Respuesta supera el tamaño máximo",
            "en": "Response exceeds the size limit",
        },
        "additional.055": {"es": "Respuesta incompleta", "en": "Incomplete response"},
        "additional.056": {"es": "HTTP no satisfactorio: ", "en": "Unsuccessful HTTP response: "},
        "additional.057": {"es": "Timeout al consultar REC", "en": "REC query timed out"},
        "additional.058": {"es": "Respuesta HTTP interrumpida", "en": "HTTP response interrupted"},
        "additional.059": {
            "es": "La captura local pertenece a otro NDP",
            "en": "The local capture belongs to a different NDP",
        },
        "additional.060": {
            "es": "Dirección oficial no disponible para contrastar",
            "en": "Official address unavailable for verification",
        },
        "additional.061": {"es": "Respuesta no HTML", "en": "Response is not HTML"},
        "additional.062": {"es": "Codificación HTML inesperada", "en": "Unexpected HTML encoding"},
        "additional.063": {"es": "Error de sesión REC", "en": "REC session error"},
        "additional.064": {
            "es": "HTML incompleto o mal formado",
            "en": "Incomplete or malformed HTML",
        },
        "additional.065": {
            "es": "Respuesta de formulario sin expediente",
            "en": "Form response without a case",
        },
        "additional.066": {"es": "HTML inesperado", "en": "Unexpected HTML"},
        "additional.067": {"es": "Error de parser REC", "en": "REC parser error"},
        "additional.068": {
            "es": "Datos identificativos incompatibles: otro NDP",
            "en": "Incompatible identity: different NDP",
        },
        "additional.069": {
            "es": "Datos identificativos incompatibles: dirección distinta",
            "en": "Incompatible identity: different address",
        },
        "additional.070": {
            "es": "Inspección incompleta; revisar ficha oficial",
            "en": "Incomplete inspection; check the official record",
        },
        "additional.071": {
            "es": "Formato con campos sin interpretar; requiere revisión",
            "en": "Format contains uninterpreted fields; review required",
        },
        "additional.072": {
            "es": "No se identifica la sección de inspecciones",
            "en": "Inspection section not identified",
        },
        "additional.073": {
            "es": "Información no disponible en modo público",
            "en": "Information unavailable in public mode",
        },
    }
)


MESSAGES.update(
    {
        "error.000": {
            "es": "Colección enriquecida no validada",
            "en": "Enriched collection not validated",
        },
        "error.001": {"es": "Manifiesto municipal alterado", "en": "Municipal manifest altered"},
        "error.002": {
            "es": "Partición enriquecida incompatible",
            "en": "Incompatible enriched partition",
        },
        "error.003": {"es": "Producto enriquecido alterado: ", "en": "Enriched product altered: "},
        "error.004": {
            "es": "CP incompatible con sesión 18",
            "en": "CP incompatible with session 18",
        },
        "error.005": {
            "es": "Cruce municipal incompatible",
            "en": "Incompatible municipality crosswalk",
        },
        "error.006": {"es": "Identidades BU incompatibles", "en": "Incompatible BU identities"},
        "error.007": {"es": "BU no único o no utilizable", "en": "BU is not unique or usable"},
        "error.008": {"es": "Catálogo incompatible", "en": "Incompatible catalogue"},
        "error.009": {
            "es": "Permisos públicos incompatibles",
            "en": "Incompatible public permissions",
        },
        "error.010": {"es": "Catálogo desactualizado: ", "en": "Out-of-date catalogue: "},
        "error.011": {"es": "Catálogo alterado: ", "en": "Catalogue altered: "},
        "error.012": {
            "es": "Captura activa incompatible con catálogo: ",
            "en": "Active capture incompatible with catalogue: ",
        },
        "error.013": {"es": "Captura regional incompatible", "en": "Incompatible regional capture"},
        "error.014": {"es": "Municipio fuera del MVP", "en": "Municipality outside the MVP"},
        "error.015": {"es": "Filtro de evidencia inválido", "en": "Invalid evidence filter"},
        "error.016": {"es": "Filtros inválidos", "en": "Invalid filters"},
        "error.017": {"es": "Complementos contradictorios", "en": "Contradictory address details"},
        "error.018": {"es": "Contrato postal incompatible", "en": "Incompatible address contract"},
        "error.019": {"es": "Índice postal desactualizado: ", "en": "Out-of-date address index: "},
        "error.020": {"es": "Índice postal alterado", "en": "Address index altered"},
        "error.021": {
            "es": "Captura activa incompatible con el resumen postal: ",
            "en": "Active capture incompatible with the address summary: ",
        },
        "error.022": {
            "es": "Captura activa incompatible con el índice postal; regenere en salida nueva",
            "en": "Active capture incompatible with the address index; rebuild in a new output directory",
        },
        "error.023": {"es": "Tipo catastral desconocido", "en": "Unknown cadastral type"},
        "error.024": {
            "es": "Registros constructivos alterados",
            "en": "Construction records altered",
        },
        "error.025": {
            "es": "Ámbitos documentales; no diagnóstico del edificio.",
            "en": "Documentary scope only; not a building diagnosis.",
        },
        "error.026": {
            "es": "No es un recuento de edificios físicos.",
            "en": "This is not a count of physical buildings.",
        },
        "template.access_count": {"es": "{v0} · {v1} accesos", "en": "{v0} · {v1} entrances"},
        "template.date_range": {
            "es": "Fechas declaradas: {v0} a {v1}",
            "en": "Declared dates: {v0} to {v1}",
        },
        "template.rec_source": {
            "es": "Fuente: REC del Ayuntamiento de Madrid · Consulta: {v0} · Verificación: {v1}",
            "en": "Source: REC, Ayuntamiento de Madrid · Queried: {v0} · Verification: {v1}",
        },
        "template.rec_address": {
            "es": "Dirección: {v0} · NDP: {v1}",
            "en": "Address: {v0} · NDP: {v1}",
        },
    }
)


MESSAGES.update(
    {
        "export.000": {"es": "Importe del expediente", "en": "Case amount"},
        "export.001": {"es": "Accesibilidad", "en": "Accessibility"},
        "export.002": {"es": "Eficiencia energética", "en": "Energy efficiency"},
        "export.003": {"es": "Salubridad", "en": "Health and sanitation"},
        "export.004": {"es": "Ficha de consulta · ", "en": "Property query · "},
        "export.005": {
            "es": "Objeto: parcela catastral. Geometría disponible. Identificación documental en captura local.",
            "en": "Object: cadastral parcel. Geometry available. Documentary identification in a local capture.",
        },
        "export.006": {
            "es": "Energía, conservación y ayudas",
            "en": "Energy, building maintenance and grants",
        },
        "export.007": {
            "es": "Evidencias excluidas de la exportación: revisión específica de redistribución pendiente. Resultado ITE/IEE no disponible en las fuentes integradas.",
            "en": "Evidence excluded from the export: source-specific redistribution review pending. ITE/IEE outcomes are unavailable in the integrated sources.",
        },
        "export.008": {"es": "Fuentes y fecha", "en": "Sources and date"},
        "export.009": {
            "es": "Dirección General del Catastro, servicio INSPIRE. Referencia de captura: ",
            "en": "Dirección General del Catastro, INSPIRE service. Capture reference: ",
        },
        "export.010": {"es": ". Fecha de generación: ", "en": ". Generated: "},
        "export.011": {
            "es": "Dirección y año de construcción no incluidos. La fecha de generación no es la fecha de actualización de la fuente.",
            "en": "Address and construction year are not included. The generation date is not the source update date.",
        },
        "export.012": {"es": "Consulta oficial REC (Madrid)", "en": "Official REC query (Madrid)"},
        "export.013": {"es": "Ficha ", "en": "Property record "},
        "template.html_date": {
            "es": "Dirección General del Catastro, servicio INSPIRE. Referencia de captura: {v0}. Fecha de generación: {v1}.",
            "en": "Dirección General del Catastro, INSPIRE service. Capture reference: {v0}. Generated: {v1}.",
        },
    }
)


MESSAGES["template.html_title"] = {"es": "Ficha {v0}", "en": "Property record {v0}"}


MESSAGES.update(
    {
        "explore.area_label": {"es": "Área {area}", "en": "Area {area}"},
        "explore.overview": {"es": "Mapa general", "en": "Map overview"},
        "address.portal_type": {"es": "PORTAL", "en": "Entrance"},
        "address.access_type": {"es": "ACCESO", "en": "Entrance"},
    }
)


MESSAGES.update(
    {
        "bundle.orders_empty": {
            "es": "Sin órdenes documentadas en la captura autorizada. Padrones de obligaciones ITE/IEE no disponibles; no acredita ausencia real de antecedentes.",
            "en": "No orders documented in the authorized snapshot. ITE/IEE obligation lists are unavailable; this does not establish absence of real records.",
        },
        "bundle.source_version": {
            "es": "Versión oficial verificada",
            "en": "Verified official version",
        },
        "bundle.scope": {
            "es": "Plan Rehabilita disponible con procedencia oficial verificada. PRTR permanece protegido. Conservación: órdenes históricas; padrones ITE/IEE y resultados no incluidos por permisos pendientes.",
            "en": "Plan Rehabilita is available with verified official provenance. PRTR remains protected. Maintenance: historical orders; ITE/IEE obligation lists and outcomes are excluded pending reuse permissions.",
        },
        "bundle.missing": {
            "es": "Paquete de producción ausente, incompleto o incompatible. No se han cargado datos alternativos.",
            "en": "Production package missing, incomplete or incompatible. No alternative data has been loaded.",
        },
        "bundle.licenses": {
            "es": "[Catastro INSPIRE · licencia](https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf) · [CEEE · fuente](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Plan Rehabilita · fuente oficial](https://geoportal.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=00000009-b145-11ea-a01e-ecb1d753f6e8) · [Condiciones municipales](https://datos.madrid.es/pages/condiciones-generales-ayuntamiento-de-madrid)",
            "en": "[Catastro INSPIRE · license](https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf) · [CEEE · source](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Plan Rehabilita · official source](https://geoportal.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=00000009-b145-11ea-a01e-ecb1d753f6e8) · [Municipal terms](https://datos.madrid.es/pages/condiciones-generales-ayuntamiento-de-madrid)",
        },
        "bundle.attribution": {
            "es": "Producto derivado independiente: Dirección General del Catastro · INSPIRE; Comunidad de Madrid · CEEE (CC BY 4.0); Ayuntamiento de Madrid · callejero y órdenes (CC BY 4.0), Plan Rehabilita (condiciones municipales). No constituye información oficial ni acredita estado físico, pago u obra ejecutada.",
            "en": "Independent derived product: Dirección General del Catastro · INSPIRE; Comunidad de Madrid · CEEE (CC BY 4.0); Ayuntamiento de Madrid · street register and orders (CC BY 4.0), Plan Rehabilita (municipal reuse conditions). It is not official certification and does not establish physical condition, payment or completed works.",
        },
    }
)


def language():
    value = _st.session_state.get("i18n_language", DEFAULT_LANGUAGE)
    return value if value in {"es", "en"} else DEFAULT_LANGUAGE


class _SafeVariables(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def t(key, **kwargs):
    """Resolve a stable key with Spanish fallback; unknown keys remain readable."""
    message = MESSAGES.get(key)
    if message is None:
        return key
    template = message.get(language()) or message.get(DEFAULT_LANGUAGE) or key
    if not kwargs:
        return template
    try:
        return template.format_map(_SafeVariables(kwargs))
    except (ValueError, TypeError):
        return template


_BY_SPANISH = {v["es"]: k for k, v in MESSAGES.items()}


@lru_cache(maxsize=1)
def _patterns():
    patterns = []
    for key, message in MESSAGES.items():
        if not key.startswith("template."):
            continue
        parts = list(Formatter().parse(message["es"]))
        pattern = ""
        literal_length = 0
        for literal, field, spec, conversion in parts:
            pattern += re.escape(literal)
            literal_length += len(literal.strip())
            if field:
                pattern += "(?P<" + field + ">.*?)"
        if literal_length >= 5:
            patterns.append((literal_length, re.compile(pattern, re.DOTALL), key))
    return sorted(patterns, key=lambda item: -item[0])


def translate(text, *, depth=0):
    """Localise known UI phrases/templates while preserving unknown source literals."""
    if language() == "es" or not isinstance(text, str) or depth > 8:
        return text
    if text.isdecimal():
        return text
    if text in _BY_SPANISH:
        return t(_BY_SPANISH[text])
    stripped = text.strip()
    if stripped in _BY_SPANISH:
        start = len(text) - len(text.lstrip())
        end = len(text.rstrip())
        return text[:start] + t(_BY_SPANISH[stripped]) + text[end:]
    for _, pattern, key in _patterns():
        match = pattern.fullmatch(text)
        if match:
            return t(
                key, **{k: translate(v, depth=depth + 1) for k, v in match.groupdict().items()}
            )
    # Explicitly authored prefixes/suffixes (not individual translated words).
    for es, key in sorted(_BY_SPANISH.items(), key=lambda item: -len(item[0])):
        if len(es) < 12:
            continue
        if text.startswith(es):
            return t(key) + translate(text[len(es) :], depth=depth + 1)
        if text.endswith(es):
            return translate(text[: -len(es)], depth=depth + 1) + t(key)
    # Composed labels are UI text; source addresses themselves are never tokenised
    # into words or passed through a general-purpose replacement engine.
    for separator in (" · ", ": ", "\n", " — "):
        if separator in text:
            parts = text.split(separator)
            translated = [translate(part, depth=depth + 1) for part in parts]
            if parts != translated:
                return separator.join(translated)
    for prefix in ("### ", "**", "• "):
        if text.startswith(prefix):
            suffix = "**" if prefix == "**" and text.endswith("**") else ""
            body = text[len(prefix) : -len(suffix)] if suffix else text[len(prefix) :]
            return prefix + translate(body, depth=depth + 1) + suffix
    return text


def localize_html(document):
    """Translate only the existing allowlisted HTML export, never add evidence."""
    if language() == "es":
        return document

    class PresentationHTML(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.parts = []
            self.style = False

        def handle_decl(self, decl):
            self.parts.append("<!" + decl + ">")

        def handle_starttag(self, tag, attrs):
            original = self.get_starttag_text()
            if tag == "html":
                original = original.replace('lang="es"', 'lang="en"')
            self.parts.append(original)
            if tag == "style":
                self.style = True

        def handle_endtag(self, tag):
            self.parts.append("</" + tag + ">")
            if tag == "style":
                self.style = False

        def handle_data(self, data):
            self.parts.append(data if self.style else html.escape(translate(data), quote=False))

        def handle_entityref(self, name):
            self.parts.append("&" + name + ";")

        def handle_charref(self, name):
            self.parts.append("&#" + name + ";")

    parser = PresentationHTML()
    parser.feed(document)
    return "".join(parser.parts)


# Only application-generated evidence values are localised. Addresses, original
# descriptions, dates, amounts, identifiers and source documents remain verbatim.
PRESENTATION_COLUMNS = {
    "Dato",
    "Atributo",
    "Estado",
    "Calidad",
    "Ámbito del dato",
    "Fecha / periodo",
    "Fuente",
    "Valor",
    "Ámbito",
    "Estado individual",
    "Captura original",
    "Límite de interpretación",
    "Evidencia del vínculo",
    "Tipo de actuación",
    "Relación",
    "Estado de aceptación",
    "Naturaleza de la fecha",
}


def localize_frame(frame):
    if language() == "es" or not isinstance(frame, pd.DataFrame):
        return frame
    result = frame.copy()
    for column in result:
        if column in PRESENTATION_COLUMNS:
            result[column] = result[column].map(lambda v: translate(v) if isinstance(v, str) else v)
    return result.rename(columns=lambda label: translate(label))


def _change_language():
    _st.session_state["i18n_language"] = _st.session_state["language_selector"].lower()
    # Label changes can alter widget identity in Streamlit. Restore only registered
    # value widgets, never buttons, map events or callbacks, before rendering them.
    _st.session_state["i18n_restore"] = {
        key: _st.session_state[key]
        for key in _st.session_state.get("i18n_widgets", {})
        if key in _st.session_state
    }


def language_selector():
    _st.session_state.setdefault("i18n_language", DEFAULT_LANGUAGE)
    _st.sidebar.radio(
        "ES | EN",
        LANGUAGES,
        horizontal=True,
        key="language_selector",
        index=0 if language() == "es" else 1,
        on_change=_change_language,
        label_visibility="collapsed",
    )


class _UI:
    """Scoped Streamlit adapter; it never monkey-patches Streamlit or its caches."""

    _texts = {
        "title",
        "header",
        "subheader",
        "caption",
        "markdown",
        "text",
        "write",
        "info",
        "warning",
        "error",
        "success",
        "expander",
        "metric",
        "download_button",
        "form_submit_button",
        "link_button",
    }
    _widgets = {"radio", "selectbox", "multiselect", "checkbox", "text_input", "button"}

    def __init__(self, target=None):
        self._target = target if target is not None else _st

    def __enter__(self):
        return self._target.__enter__()

    def __exit__(self, *args):
        return self._target.__exit__(*args)

    def __getattr__(self, name):
        attr = getattr(self._target, name)
        if name == "sidebar":
            return _UI(attr)
        if name == "columns":
            return lambda *a, **kw: [_UI(col) for col in attr(*a, **kw)]
        if name == "tabs":
            return lambda labels, **kw: attr([translate(v) for v in labels], **kw)
        if name == "dataframe":
            return lambda data, *a, **kw: attr(localize_frame(data), *a, **kw)
        if name not in self._texts | self._widgets:
            return attr

        def call(*args, **kwargs):
            args = list(args)
            original = args[0] if args else kwargs.get("label", "")
            if args and isinstance(original, str):
                args[0] = translate(original)
            elif "label" in kwargs:
                kwargs["label"] = translate(kwargs["label"])
            if name == "download_button":
                data = args[1] if len(args) > 1 else kwargs.get("data")
                if isinstance(data, str) and data.startswith("<!doctype html>"):
                    if len(args) > 1:
                        args[1] = localize_html(data)
                    else:
                        kwargs["data"] = localize_html(data)
            for key in ("placeholder", "help"):
                if key in kwargs:
                    kwargs[key] = translate(kwargs[key])
            if name in self._widgets:
                widget_key = kwargs.setdefault(
                    "key",
                    "i18n_widget_"
                    + name
                    + "_"
                    + hashlib.sha256(str(original).encode()).hexdigest()[:16],
                )
                if name != "button":
                    registered = dict(_st.session_state.get("i18n_widgets", {}))
                    registered[widget_key] = name
                    _st.session_state["i18n_widgets"] = registered
                    pending = dict(_st.session_state.get("i18n_restore", {}))
                    if widget_key in pending:
                        _st.session_state[widget_key] = pending.pop(widget_key)
                        _st.session_state["i18n_restore"] = pending
                if name in {"radio", "selectbox", "multiselect"}:
                    formatter = kwargs.get("format_func", str)
                    options = args[1] if len(args) > 1 else kwargs["options"]
                    labels = {str(value): translate(formatter(value)) for value in options}
                    # Freeze labels for this render; formatters can also be called
                    # by Streamlit/AppTest outside the session's script context.
                    kwargs["format_func"] = lambda value: labels.get(str(value), str(value))
            return attr(*args, **kwargs)

        return call


ui = _UI()
