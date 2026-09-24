# evals/stress/fixtures/build_pdfs.py
"""
Genera PDFs sintéticos de tamaños calibrados para el stress test.
Ejecutar: uv run python -m evals.stress.fixtures.build_pdfs
"""
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent
SIZES_KB = [5, 20, 50, 100]

CONTENT_BLOCK = """
Especificacion Tecnica del Proyecto

Alcance del Proyecto:
El sistema debe gestionar pedidos de clientes con panel de administracion,
autenticacion de usuarios, gestion de inventario y reportes mensuales.
El cliente requiere integracion con sistemas externos de facturacion.

Requisitos Funcionales:
- Autenticacion de usuarios con roles admin y operario
- Gestion de inventario con alertas de stock minimo
- Integracion con pasarela de pagos Stripe
- Panel de administracion con estadisticas en tiempo real
- Exportacion de reportes en CSV y PDF mensualmente

Stack Tecnologico:
Backend: Python con FastAPI y PostgreSQL como base de datos principal.
Frontend: React con TypeScript y Tailwind CSS para el diseno.
Cache: Redis para sesiones y cache de consultas frecuentes.
Infraestructura: Docker en servidor Ubuntu con Nginx como proxy.

Estimacion Inicial:
El equipo estima entre 200 y 400 horas de desarrollo segun complejidad.
Coste estimado entre 10000 EUR y 20000 EUR a tarifa de 50 EUR por hora.
Duracion estimada de 8 a 16 semanas con equipo de 2 desarrolladores.

Riesgos Identificados:
- Integracion con sistemas legados puede requerir tiempo adicional
- Curva de aprendizaje del equipo con nuevas tecnologias
- Posibles cambios de requisitos durante el desarrollo
- Dependencia de APIs externas fuera del control del equipo

"""


def generate_pdf(target_kb: int) -> Path:
    """Genera un PDF de aproximadamente target_kb KB usando texto plano."""
    output_path = OUTPUT_DIR / f"attach_{target_kb}kb.pdf"
    target_bytes = target_kb * 1024

    # Calcular repeticiones necesarias
    block_size = len(CONTENT_BLOCK.encode("latin-1"))
    repetitions = max(3, (target_bytes // block_size) + 3)

    # Construir contenido completo
    full_text = f"DOCUMENTO SINTETICO {target_kb}KB\n\n"
    for i in range(repetitions):
        full_text += f"=== SECCION {i+1} ===\n"
        full_text += CONTENT_BLOCK

    # Crear PDF con reportlab-style usando solo texto
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.set_margins(20, 20, 20)
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        pdf.set_font("Courier", size=9)

        # Añadir línea por línea para evitar problemas de ancho
        for line in full_text.split("\n"):
            # Truncar líneas muy largas
            if len(line) > 90:
                line = line[:90]
            pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")

        pdf.output(str(output_path))

    except Exception as e:
        # Fallback: crear PDF manualmente con estructura básica
        _create_pdf_manual(output_path, full_text)

    final_size = len(output_path.read_bytes())
    print(f"Generado: {output_path.name} ({final_size / 1024:.1f} KB) — objetivo: {target_kb} KB")
    return output_path


def _create_pdf_manual(output_path: Path, text: str):
    """Fallback: crea un PDF mínimo válido con el texto embebido."""
    # PDF mínimo válido con texto
    lines = text.split("\n")[:500]  # limitar líneas
    
    stream_content = "BT\n/F1 9 Tf\n"
    y_pos = 750
    for line in lines:
        clean = line.replace("(", "\\(").replace(")", "\\)").replace("\\", "\\\\")
        clean = "".join(c if ord(c) < 128 else "?" for c in clean)
        stream_content += f"50 {y_pos} Td\n({clean}) Tj\n"
        y_pos -= 12
        if y_pos < 50:
            y_pos = 750
    stream_content += "ET\n"
    
    stream_bytes = stream_content.encode("latin-1")
    
    pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj

2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj

3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj

4 0 obj
<< /Length {len(stream_bytes)} >>
stream
""".encode("latin-1")
    
    pdf_content += stream_bytes
    pdf_content += b"\nendstream\nendobj\n\n"
    pdf_content += b"""5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>
endobj

xref
0 6

trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF
"""
    # Rellenar hasta el tamaño objetivo
    output_path.write_bytes(pdf_content)


if __name__ == "__main__":
    print("Generando PDFs sinteticos para stress test...")
    for size in SIZES_KB:
        generate_pdf(size)
    print("Done.")