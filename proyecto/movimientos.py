import flet as ft

# Compatibilidad íconos (Flet nuevo)
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

from datetime import date
from connector import get_connection


def movimientos_view(page: ft.Page, nombre: str) -> ft.View:
    # -----------------------------
    # Navegación
    # -----------------------------
    def volver_pos(e=None):
        if len(page.views) > 1:
            page.views.pop()
        page.update()

    def cerrar_sesion(e):
        from login import LoginView
        page.views.clear()
        page.views.append(LoginView(page))
        page.go("/")
        page.update()

    # -----------------------------
    # Helpers UI compatibles
    # -----------------------------
    def open_overlay(ctrl):
        if hasattr(page, "open"):
            page.open(ctrl)
        else:
            page.dialog = ctrl
            ctrl.open = True
            page.update()

    def show_snack(texto: str):
        sb = ft.SnackBar(content=ft.Text(texto))
        if hasattr(page, "open"):
            page.open(sb)
        else:
            page.snack_bar = sb
            sb.open = True
            page.update()

    # -----------------------------
    # Sidebar (igual estilo)
    # -----------------------------
    def crear_boton_sidebar(texto: str, on_click):
        btn = ft.Container(
            padding=ft.padding.symmetric(vertical=10, horizontal=16),
            border_radius=20,
            content=ft.Text(texto, color="white", size=14, weight="w600"),
            ink=True,
            on_click=on_click,
        )

        def on_hover(e):
            btn.bgcolor = "rgba(255,255,255,0.18)" if e.data == "true" else None
            btn.update()

        btn.on_hover = on_hover
        return btn

    sidebar = ft.Container(
        width=220,
        bgcolor="#C86DD7",
        padding=20,
        content=ft.Column(
            [
                ft.Text("Corallie Bubble", size=20, weight="bold", color="white"),
                ft.Text("Punto de Venta", size=12, color="white70"),
                ft.Container(height=20),
                crear_boton_sidebar("Inicio", volver_pos),
                crear_boton_sidebar("Entradas y salidas", lambda e: None),
                ft.Container(expand=True),
                crear_boton_sidebar("Cerrar sesión", cerrar_sesion),
            ],
            spacing=6,
        ),
    )

    # -----------------------------
    # BD
    # -----------------------------
    def db_listar_productosstock():
        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT IdProductosStock, Nombre, Cantidad
                FROM productosstock
                ORDER BY Nombre ASC
                """
            )
            return cur.fetchall() or []
        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except:
                pass

    def db_listar_movimientos(limit=100):
        """
        Une entradas + salidas y las devuelve ordenadas.
        Guardamos producto dentro de Descripcion/Detalle como: ID|NOMBRE|DESC
        """
        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                f"""
                SELECT
                    'Entrada' AS Tipo,
                    Fecha AS FechaMov,
                    Cantidad AS Cant,
                    Descripcion AS Texto
                FROM entradasproductos
                UNION ALL
                SELECT
                    'Salida' AS Tipo,
                    FechaSalida AS FechaMov,
                    CAST(Cantidad AS DECIMAL(10,2)) AS Cant,
                    Detalle AS Texto
                FROM salidasproductos
                ORDER BY FechaMov DESC
                LIMIT {int(limit)}
                """
            )
            return cur.fetchall() or []
        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except:
                pass

    def db_registrar_movimiento(tipo: str, id_prod: int, nombre_prod: str, cantidad: float, descripcion: str):
        """
        Regla clave:
        - Entrada: suma stock y registra en entradasproductos
        - Salida: valida stock suficiente, resta stock y registra en salidasproductos
        Todo en una transacción (commit/rollback).
        """
        conn = None
        cur = None
        try:
            conn = get_connection()
            conn.start_transaction()
            cur = conn.cursor(dictionary=True)

            # 1) stock actual
            cur.execute(
                "SELECT Cantidad FROM productosstock WHERE IdProductosStock=%s FOR UPDATE",
                (id_prod,),
            )
            row = cur.fetchone()
            if not row:
                raise Exception("El producto ya no existe en inventario.")

            stock_actual = float(row["Cantidad"])

            if tipo == "Salida":
                if cantidad > stock_actual:
                    raise Exception(f"No puedes sacar {cantidad} porque solo hay {stock_actual} en stock.")

            # 2) actualizar stock
            if tipo == "Entrada":
                nuevo_stock = stock_actual + cantidad
            else:
                nuevo_stock = stock_actual - cantidad

            cur.execute(
                "UPDATE productosstock SET Cantidad=%s WHERE IdProductosStock=%s",
                (nuevo_stock, id_prod),
            )

            # 3) registrar movimiento (guardando producto dentro del texto)
            texto = f"{id_prod}|{nombre_prod}|{descripcion}".strip()

            if tipo == "Entrada":
                cur.execute(
                    """
                    INSERT INTO entradasproductos (Cantidad, Fecha, Descripcion, CorteCaja_idCorteCaja)
                    VALUES (%s, %s, %s, 1)
                    """,
                    (int(cantidad), date.today(), texto),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO salidasproductos (FechaSalida, Detalle, Cantidad, CorteCaja_idCorteCaja)
                    VALUES (%s, %s, %s, 1)
                    """,
                    (date.today(), texto, str(float(cantidad))),
                )

            conn.commit()
            return nuevo_stock

        except:
            try:
                if conn:
                    conn.rollback()
            except:
                pass
            raise
        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except:
                pass

    # -----------------------------
    # UI Formulario
    # -----------------------------
    productos = db_listar_productosstock()
    opciones = [
        ft.dropdown.Option(
            key=str(p["IdProductosStock"]),
            text=f'{p["Nombre"]} (Stock: {p["Cantidad"]})',
        )
        for p in productos
    ]

    dd_producto = ft.Dropdown(
        label="Producto",
        options=opciones,
        border_radius=12,
        width=420,
    )

    dd_tipo = ft.Dropdown(
        label="Tipo de movimiento",
        options=[ft.dropdown.Option("Entrada"), ft.dropdown.Option("Salida")],
        value="Entrada",
        border_radius=12,
        width=220,
    )

    txt_cantidad = ft.TextField(
        label="Cantidad",
        border_radius=12,
        width=220,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    txt_desc = ft.TextField(
        label="Descripción (motivo)",
        border_radius=12,
        width=420,
        multiline=True,
        min_lines=2,
        max_lines=3,
    )

    # -----------------------------
    # Tabla movimientos
    # -----------------------------
    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cantidad")),
            ft.DataColumn(ft.Text("Descripción")),
        ],
        rows=[],
        border_radius=12,
        heading_row_color="#F3E9F7",
        data_row_min_height=52,
        data_row_max_height=80,
    )

    def parse_texto(texto: str):
        # Espera: ID|NOMBRE|DESC
        try:
            parts = (texto or "").split("|", 2)
            if len(parts) == 3:
                return parts[0].strip(), parts[1].strip(), parts[2].strip()
        except:
            pass
        return "", "Desconocido", (texto or "")

    def recargar_tabla():
        movimientos = db_listar_movimientos(limit=150)
        tabla.rows = []
        for m in movimientos:
            pid, pnom, desc = parse_texto(m.get("Texto"))
            tabla.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(m.get("FechaMov")))),
                        ft.DataCell(ft.Text(str(m.get("Tipo")))),
                        ft.DataCell(ft.Text(f"{pnom}")),
                        ft.DataCell(ft.Text(str(m.get("Cant")))),
                        ft.DataCell(ft.Text(desc)),
                    ]
                )
            )
        page.update()

    def recargar_dropdown_productos():
        nonlocal productos
        productos = db_listar_productosstock()
        dd_producto.options = [
            ft.dropdown.Option(
                key=str(p["IdProductosStock"]),
                text=f'{p["Nombre"]} (Stock: {p["Cantidad"]})',
            )
            for p in productos
        ]
        page.update()

    def validar_form():
        ok = True
        dd_producto.error_text = None
        txt_cantidad.error_text = None
        txt_desc.error_text = None

        if not dd_producto.value:
            dd_producto.error_text = "Selecciona un producto"
            ok = False

        c_raw = (txt_cantidad.value or "").strip()
        try:
            c = float(c_raw)
        except:
            c = -1

        if c <= 0:
            txt_cantidad.error_text = "Ingresa una cantidad válida (> 0)"
            ok = False

        d = (txt_desc.value or "").strip()
        if not d:
            txt_desc.error_text = "Escribe una descripción"
            ok = False

        page.update()
        return ok, c, d

    def guardar_movimiento(e):
        ok, c, d = validar_form()
        if not ok:
            return

        tipo = dd_tipo.value
        id_prod = int(dd_producto.value)

        # tomar nombre del producto del dropdown (más seguro: buscar en lista)
        nombre_prod = None
        for p in productos:
            if int(p["IdProductosStock"]) == id_prod:
                nombre_prod = str(p["Nombre"])
                break
        if not nombre_prod:
            show_snack("Producto no encontrado. Recarga e intenta de nuevo.")
            return

        try:
            nuevo_stock = db_registrar_movimiento(tipo, id_prod, nombre_prod, c, d)
            # limpiar
            txt_cantidad.value = ""
            txt_desc.value = ""
            page.update()

            recargar_dropdown_productos()
            recargar_tabla()
            show_snack(f"{tipo} registrada ✅ Nuevo stock: {nuevo_stock}")
        except Exception as ex:
            open_overlay(ft.AlertDialog(title=ft.Text("No se pudo registrar"), content=ft.Text(str(ex))))

    recargar_tabla()

    # -----------------------------
    # Layout principal
    # -----------------------------
    header = ft.Row(
        [
            ft.Text("Entradas y Salidas", size=22, weight="bold", color="#C86DD7"),
            ft.Container(expand=True),
        ]
    )

    formulario = ft.Container(
        bgcolor="white",
        border_radius=18,
        padding=15,
        content=ft.Column(
            [
                ft.Text("Registrar movimiento", size=16, weight="bold"),
                ft.Row([dd_tipo, txt_cantidad], spacing=12),
                dd_producto,
                txt_desc,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Guardar",
                            bgcolor="#C86DD7",
                            color="white",
                            on_click=guardar_movimiento,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), padding=18),
                        ),
                        ft.TextButton("Recargar tabla", on_click=lambda e: recargar_tabla()),
                    ],
                    spacing=12,
                ),
            ],
            spacing=10,
        ),
    )

    listado = ft.Container(
        expand=True,
        bgcolor="white",
        border_radius=18,
        padding=15,
        content=ft.Column(
            [
                ft.Text("Historial de movimientos", size=16, weight="bold"),
                ft.Container(expand=True, content=ft.ListView(expand=True, controls=[tabla])),
            ],
            expand=True,
        ),
    )

    main_content = ft.Container(
        expand=True,
        bgcolor="#F9F6FB",
        padding=20,
        content=ft.Column(
            [
                header,
                ft.Container(height=10),
                formulario,
                ft.Container(height=10),
                listado,
            ],
            expand=True,
        ),
    )

    layout = ft.Row([sidebar, main_content], expand=True)

    appbar = ft.AppBar(
        title=ft.Text("Corallie Bubble - Punto de Venta"),
        bgcolor="#C86DD7",
        color="white",
    )

    return ft.View(route="/movimientos", controls=[layout], appbar=appbar)
