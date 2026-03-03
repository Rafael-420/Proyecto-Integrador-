
import flet as ft
from datetime import datetime
from connector import get_connection
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from io import BytesIO


def generar_reportes_view(page: ft.Page, nombre_usuario: str):

    ultimo_reporte = {
        "data": [],
        "total": 0.0,
        "inicio": "",
        "fin": "",
    }

    # --------------------------
    # SnackBar helper
    # --------------------------
    def show_snack(mensaje: str):
        snack = ft.SnackBar(
            content=ft.Text(mensaje),
            bgcolor="#C86DD7"
        )
        page.open(snack)

    # --------------------------
    # Consultar ventas
    # --------------------------
    def obtener_ventas(inicio, fin):
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT IdVentas, FechaVenta, Hora, DetalleVenta, Subtotal, Impuesto, Total
            FROM ventas
            WHERE FechaVenta BETWEEN %s AND %s
            """,
            (inicio, fin),
        )
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data

    # --------------------------
    # Generar PDF en memoria
    # --------------------------
    def crear_pdf_bytes(data: list, total: float, inicio: str, fin: str) -> bytes:
        styles = getSampleStyleSheet()
        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter)

        elements = []
        elements.append(Paragraph("Corallie Bubble - Reporte de Ventas", styles["Title"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Generado por: {nombre_usuario}", styles["Normal"]))
        elements.append(Paragraph(f"Rango: {inicio} a {fin}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        table_data = [["ID", "Fecha", "Hora", "Detalle", "Subtotal", "Impuesto", "Total"]]

        for r in data:
            table_data.append([
                str(r["IdVentas"]),
                str(r["FechaVenta"]),
                str(r["Hora"]),
                str(r["DetalleVenta"]),
                f'{float(r["Subtotal"]):.2f}',
                f'{float(r["Impuesto"]):.2f}',
                f'{float(r["Total"]):.2f}',
            ])

        table_data.append(["", "", "", "TOTAL GENERAL", "", "", f"{total:.2f}"])

        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
        ]))

        elements.append(t)
        doc.build(elements)
        return buf.getvalue()

    # --------------------------
    # Descargar PDF (Flet nuevo)
    # --------------------------
    async def descargar_pdf(e):
        if not ultimo_reporte["data"]:
            show_snack("Primero genera el reporte.")
            return

        nombre_archivo = (
            f"reporte_{ultimo_reporte['inicio']}_a_{ultimo_reporte['fin']}.pdf"
            .replace(":", "-")
        )

        pdf_bytes = crear_pdf_bytes(
            ultimo_reporte["data"],
            ultimo_reporte["total"],
            ultimo_reporte["inicio"],
            ultimo_reporte["fin"],
        )

        picker = ft.FilePicker()

        try:
            path = await picker.save_file(
                file_name=nombre_archivo,
                allowed_extensions=["pdf"],
                src_bytes=pdf_bytes,
            )
        except TypeError:
            path = await picker.save_file(
                file_name=nombre_archivo,
                allowed_extensions=["pdf"],
            )

        if path:
            with open(path, "wb") as f:
                f.write(pdf_bytes)
            show_snack(f"PDF guardado en: {path}")
        else:
            show_snack("Descarga iniciada")

    # --------------------------
    # Generar reporte en pantalla
    # --------------------------
    def generar_reporte(e):
        inicio = fecha_inicio.value
        fin = fecha_fin.value

        data = obtener_ventas(inicio, fin)
        total = sum(float(r["Total"]) for r in data)

        ultimo_reporte["data"] = data
        ultimo_reporte["total"] = total
        ultimo_reporte["inicio"] = inicio
        ultimo_reporte["fin"] = fin

        show_snack("Reporte generado correctamente")

    fecha_inicio = ft.TextField(label="Fecha inicio (YYYY-MM-DD)")
    fecha_fin = ft.TextField(label="Fecha fin (YYYY-MM-DD)")

    contenido = ft.Column(
        [
            ft.Text("Generar Reportes", size=22, weight="bold"),
            fecha_inicio,
            fecha_fin,
            ft.ElevatedButton("Generar reporte", on_click=generar_reporte),
            ft.ElevatedButton("Descargar PDF", on_click=descargar_pdf),
        ],
        spacing=15,
    )

    return ft.View(route="/reportes", controls=[contenido])
