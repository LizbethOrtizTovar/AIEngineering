# app/context/examples.py

CANONICAL_EXAMPLES = [
    {
        "meeting_summary": "El cliente necesita una plataforma web de gestión de inventario con control de stock, alertas de mínimos y reportes mensuales. Tienen 3 almacenes distintos. El acceso debe ser por roles: admin y operario.",
        "estimation": """
## Estimación: Plataforma de Gestión de Inventario

### Desglose de tareas:
1. Diseño UI/UX: 40 horas
2. Backend API (CRUD inventario + multi-almacén): 60 horas
3. Autenticación y roles (admin / operario): 20 horas
4. Sistema de alertas de stock mínimo: 15 horas
5. Dashboard con reportes mensuales: 30 horas
6. Testing y QA: 25 horas

**Total estimado: 190 horas**
**Coste estimado: 9.500 € (tarifa 50 €/h)**
**Equipo recomendado: 2 desarrolladores full-stack + 1 diseñador UX (part-time)**
**Duración estimada: 6-8 semanas**

### Riesgos identificados:
- Integración entre los 3 almacenes puede requerir lógica adicional
- Los reportes dependen del volumen de datos históricos disponibles
"""
    },
    {
        "meeting_summary": "Necesitan migrar su web corporativa de WordPress a una solución moderna. La web tiene blog, página de servicios, formulario de contacto y área privada para clientes. El diseño ya existe en Figma.",
        "estimation": """
## Estimación: Migración Web Corporativa

### Desglose de tareas:
1. Maquetación desde Figma (páginas públicas): 35 horas
2. Blog con CMS headless: 25 horas
3. Formulario de contacto + integración email: 10 horas
4. Área privada de clientes (auth + dashboard): 40 horas
5. Migración de contenidos desde WordPress: 15 horas
6. Testing, QA y despliegue: 20 horas

**Total estimado: 145 horas**
**Coste estimado: 7.250 € (tarifa 50 €/h)**
**Equipo recomendado: 1 desarrollador full-stack + 1 maquetador**
**Duración estimada: 5-6 semanas**

### Riesgos identificados:
- El volumen de contenidos a migrar puede variar
- El área privada depende de los requisitos exactos del cliente
"""
    },
    {
        "meeting_summary": "El cliente quiere una landing page con formulario de contacto, integración con HubSpot y una sección de blog con editor WYSIWYG. El plazo ideal es 4 semanas. El diseño ya existe en Figma.",
        "estimation": """
## Estimación: Landing Page con CRM e Blog

### Desglose de tareas:
1. Maquetación desde Figma (landing): 20 horas
2. Formulario de contacto + integración HubSpot: 15 horas
3. Blog con editor WYSIWYG: 25 horas
4. Testing, QA y despliegue: 10 horas

**Total estimado: 70 horas**
**Coste estimado: 3.500 € (tarifa 50 €/h)**
**Equipo recomendado: 1 desarrollador full-stack**
**Duración estimada: 3-4 semanas**

### Riesgos identificados:
- El plazo de 4 semanas es ajustado si hay cambios en el diseño
- La integración HubSpot depende del plan contratado por el cliente
"""
    },
]


def format_examples() -> str:
    """Convierte los ejemplos en texto para inyectar en el system prompt."""
    lines = []
    for i, ex in enumerate(CANONICAL_EXAMPLES, 1):
        lines.append(f"--- Ejemplo {i} ---")
        lines.append(f"Resumen de reunión: {ex['meeting_summary']}")
        lines.append(f"Estimación generada:{ex['estimation']}")
        lines.append("")
    return "\n".join(lines)