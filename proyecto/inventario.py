import flet as ft

# Compatibilidad íconos (Flet nuevo)
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

from datetime import datetime
from connector import get_connection


def inventario_view(page: ft.Page, nombre: str) -> ft.View:
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
    # Overlay helpers (compatibles)
    # -----------------------------
    def open_dialog(dlg: ft.AlertDialog):
        if hasattr(page, "open"):
            page.open(dlg)
        else:
            page.dialog = dlg
            dlg.open = True
            page.update()

    def close_dialog(dlg: ft.AlertDialog):
        try:
            if hasattr(page, "close"):
                page.close(dlg)
            else:
                dlg.open = False
                page.update()
        except:
            try:
                dlg.open = False
                page.update()
            except:
                pass

    def show_snack(texto: str):
        sb = ft.SnackBar(content=ft.Text(texto))
        if hasattr(page, "open"):
            page.open(sb)
        else:
            page.snack_bar = sb
            sb.open = True
            page.update()

    # -----------------------------
    # Helpers validación
    # -----------------------------
    def normalizar_nombre(s: str) -> str:
        s = (s or "").strip()
        # colapsa espacios múltiples
        s = " ".join(s.split())
        return s

    def parse_fecha_caducidad(s: str) -> int:
        """
        Acepta:
          - YYYYMMDD (8 dígitos)
          - YYYY-MM-DD
        Retorna int YYYYMMDD si es válido, si no lanza ValueError.
        """
        raw = (s or "").strip()
        if not raw:
            raise ValueError("Fecha vacía")

        if "-" in raw:
            dt = datetime.strptime(raw, "%Y-%m-%d")
        else:
            if len(raw) != 8 or not raw.isdigit():
                raise ValueError("Formato inválido")
            dt = datetime.strptime(raw, "%Y%m%d")
        return int(dt.strftime("%Y%m%d"))

    # -----------------------------
    # Sidebar
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
                crear_boton_sidebar("Ver inventario", lambda e: None),
                ft.Container(expand=True),
                crear_boton_sidebar("Cerrar sesión", cerrar_sesion),
            ],
            spacing=6,
        ),
    )

    # -----------------------------
    # UI
    # -----------------------------
    txt_buscar = ft.TextField(label="Buscar", border_radius=12, width=320)

    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Nombre")),
            ft.DataColumn(ft.Text("Precio")),
            ft.DataColumn(ft.Text("Caducidad")),
            ft.DataColumn(ft.Text("Marca")),
            ft.DataColumn(ft.Text("Unidad")),
            ft.DataColumn(ft.Text("Descripción")),
            ft.DataColumn(ft.Text("Stock")),
            ft.DataColumn(ft.Text("Acciones")),
        ],
        rows=[],
        border_radius=12,
        heading_row_color="#F3E9F7",
        data_row_min_height=52,
        data_row_max_height=90,
    )

    productos_cache = []

    # -----------------------------
    # BD (productos + stock)
    # -----------------------------
    def db_listar():
        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT
                    p.IdProductos,
                    p.Nombre,
                    p.Precio,
                    p.FechaCaducidad,
                    p.Descripcion,
                    p.Marca,
                    p.UnidadMedida,
                    p.CorteCaja_idCorteCaja,
                    COALESCE(ps.Cantidad, 0) AS Cantidad
                FROM productos p
                LEFT JOIN productosstock ps
                    ON ps.Nombre = p.Nombre
                ORDER BY p.Nombre ASC
            """)
            return cur.fetchall() or []
        finally:
            try:
                if cur: cur.close()
                if conn: conn.close()
            except:
                pass

    def db_existe_nombre(nombre_norm: str, exclude_id: int | None = None) -> bool:
        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            if exclude_id is None:
                cur.execute("SELECT COUNT(*) FROM productos WHERE LOWER(Nombre)=LOWER(%s)", (nombre_norm,))
            else:
                cur.execute("SELECT COUNT(*) FROM productos WHERE LOWER(Nombre)=LOWER(%s) AND IdProductos<>%s",
                            (nombre_norm, exclude_id))
            return (cur.fetchone()[0] or 0) > 0
        finally:
            try:
                if cur: cur.close()
                if conn: conn.close()
            except:
                pass

    def db_crear_producto(nombre, precio, fecha_cad, descripcion, marca, unidad, corte_id=1):
        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO productos (Nombre, Precio, FechaCaducidad, Descripcion, Marca, UnidadMedida, CorteCaja_idCorteCaja)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (nombre, precio, fecha_cad, descripcion, marca, unidad, corte_id))

            # Crea stock si no existe (Cantidad=0)
            cur.execute("SELECT COUNT(*) FROM productosstock WHERE Nombre=%s", (nombre,))
            existe = (cur.fetchone()[0] or 0) > 0
            if not existe:
                cur.execute("""
                    INSERT INTO productosstock (Nombre, Descripcion, Cantidad, CorteCaja_idCorteCaja)
                    VALUES (%s, %s, 0, %s)
                """, (nombre, descripcion[:35], corte_id))

            conn.commit()
        finally:
            try:
                if cur: cur.close()
                if conn: conn.close()
            except:
                pass

    def db_editar_producto(id_prod, nombre, precio, fecha_cad, descripcion, marca, unidad):
        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT Nombre FROM productos WHERE IdProductos=%s", (id_prod,))
            row = cur.fetchone()
            if not row:
                raise Exception("Producto no encontrado")
            nombre_anterior = row[0]

            cur.execute("""
                UPDATE productos
                SET Nombre=%s, Precio=%s, FechaCaducidad=%s, Descripcion=%s, Marca=%s, UnidadMedida=%s
                WHERE IdProductos=%s
            """, (nombre, precio, fecha_cad, descripcion, marca, unidad, id_prod))

            cur.execute("""
                UPDATE productosstock
                SET Nombre=%s, Descripcion=%s
                WHERE Nombre=%s
            """, (nombre, descripcion[:35], nombre_anterior))

            conn.commit()
        finally:
            try:
                if cur: cur.close()
                if conn: conn.close()
            except:
                pass

    def db_eliminar_producto(id_prod):
        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT Nombre FROM productos WHERE IdProductos=%s", (id_prod,))
            row = cur.fetchone()
            if not row:
                return
            nom = row[0]

            cur.execute("DELETE FROM productos WHERE IdProductos=%s", (id_prod,))
            cur.execute("DELETE FROM productosstock WHERE Nombre=%s", (nom,))
            conn.commit()
        finally:
            try:
                if cur: cur.close()
                if conn: conn.close()
            except:
                pass

    # -----------------------------
    # Render / filtro
    # -----------------------------
    def recargar():
        nonlocal productos_cache
        try:
            productos_cache = db_listar()
        except Exception as ex:
            productos_cache = []
            show_snack(f"Error inventario: {ex}")
        aplicar_filtro()

    def aplicar_filtro(e=None):
        q = (txt_buscar.value or "").strip().lower()
        lista = productos_cache
        if q:
            lista = [
                p for p in productos_cache
                if q in str(p["Nombre"]).lower()
                or q in str(p["Descripcion"]).lower()
                or q in str(p["Marca"]).lower()
            ]
        pintar_tabla(lista)

    txt_buscar.on_change = aplicar_filtro

    def pintar_tabla(lista):
        tabla.rows = []

        def link(texto, callback):
            return ft.GestureDetector(
                content=ft.Text(texto, color=ft.Colors.BLUE, weight="w600"),
                on_tap=callback,
                mouse_cursor=ft.MouseCursor.CLICK,
            )

        def cell(ctrl, bg=None, w=None):
            return ft.Container(
                width=w,
                bgcolor=bg,
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                border_radius=10,
                content=ctrl,
            )

        for p in lista:
            try:
                cant = float(p.get("Cantidad", 0) or 0)
            except:
                cant = 0

            sin_stock = cant <= 0
            row_bg = "#FFF3CD" if sin_stock else None

            stock_cell = ft.Row(
                [
                    ft.Text(str(cant), weight="bold" if sin_stock else None),
                    ft.Container(
                        visible=sin_stock,
                        bgcolor="#FFE08A",
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=12,
                        content=ft.Text("SIN STOCK", size=11, weight="bold"),
                    )
                ],
                spacing=10,
            )

            def _editar(prod=p):
                abrir_dialogo_editar(prod)

            def _eliminar(prod_id=p["IdProductos"]):
                confirmar_eliminar(prod_id)

            tabla.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(cell(ft.Text(str(p["IdProductos"])), bg=row_bg, w=70)),
                        ft.DataCell(cell(ft.Text(str(p["Nombre"])), bg=row_bg, w=170)),
                        ft.DataCell(cell(ft.Text(str(p["Precio"])), bg=row_bg, w=110)),
                        ft.DataCell(cell(ft.Text(str(p["FechaCaducidad"])), bg=row_bg, w=140)),
                        ft.DataCell(cell(ft.Text(str(p["Marca"])), bg=row_bg, w=140)),
                        ft.DataCell(cell(ft.Text(str(p["UnidadMedida"])), bg=row_bg, w=130)),
                        ft.DataCell(cell(ft.Text(str(p["Descripcion"])), bg=row_bg, w=260)),
                        ft.DataCell(cell(stock_cell, bg=row_bg, w=180)),
                        ft.DataCell(
                            cell(
                                ft.Row(
                                    [
                                        link("Editar", lambda e, prod=p: _editar(prod)),
                                        link("Eliminar", lambda e, prod_id=p["IdProductos"]: _eliminar(prod_id)),
                                    ],
                                    spacing=18,
                                ),
                                bg=row_bg,
                                w=170,
                            )
                        ),
                    ]
                )
            )

        page.update()

    # -----------------------------
    # Diálogos
    # -----------------------------
    def abrir_dialogo_nuevo(e=None):
        nombre_f = ft.TextField(label="Nombre", border_radius=12)
        precio_f = ft.TextField(label="Precio", border_radius=12, keyboard_type=ft.KeyboardType.NUMBER)
        cad_f = ft.TextField(label="FechaCaducidad (YYYYMMDD o YYYY-MM-DD)", border_radius=12)
        desc_f = ft.TextField(label="Descripción", border_radius=12, multiline=True, min_lines=2, max_lines=3)
        marca_f = ft.TextField(label="Marca", border_radius=12)
        unidad_f = ft.TextField(label="Unidad de medida", border_radius=12)

        dlg = ft.AlertDialog(title=ft.Text("Nuevo producto"))

        def validar():
            ok = True
            for f in [nombre_f, precio_f, cad_f, desc_f, marca_f, unidad_f]:
                f.error_text = None

            n = normalizar_nombre(nombre_f.value)
            pr = (precio_f.value or "").strip()
            fc = (cad_f.value or "").strip()
            d = (desc_f.value or "").strip()
            m = (marca_f.value or "").strip()
            u = (unidad_f.value or "").strip()

            if not n:
                nombre_f.error_text = "Requerido"
                ok = False
            else:
                if db_existe_nombre(n):
                    nombre_f.error_text = "Ya existe un producto con ese nombre"
                    ok = False

            try:
                precio = float(pr)
                if precio <= 0:
                    raise ValueError()
            except:
                precio_f.error_text = "Precio inválido (debe ser > 0)"
                ok = False
                precio = 0.0

            try:
                fecha_cad = parse_fecha_caducidad(fc)
            except:
                cad_f.error_text = "Fecha inválida (YYYYMMDD o YYYY-MM-DD)"
                ok = False
                fecha_cad = 0

            if not d:
                desc_f.error_text = "Requerido"
                ok = False
            if not m:
                marca_f.error_text = "Requerido"
                ok = False
            if not u:
                unidad_f.error_text = "Requerido"
                ok = False

            page.update()
            return ok, n, precio, fecha_cad, d, m, u

        def cancelar(ev):
            close_dialog(dlg)

        def guardar(ev):
            ok, n, precio, fecha_cad, d, m, u = validar()
            if not ok:
                return  # no cierra si hay errores
            try:
                db_crear_producto(n, precio, fecha_cad, d, m, u, corte_id=1)
                close_dialog(dlg)
                recargar()
                show_snack("Producto guardado ✅ (stock inicial 0)")
            except Exception as ex:
                show_snack(f"Error al guardar: {ex}")

        dlg.content = ft.Column([nombre_f, precio_f, cad_f, desc_f, marca_f, unidad_f], tight=True, width=480)
        dlg.actions = [
            ft.TextButton("Cancelar", on_click=cancelar),
            ft.ElevatedButton("Guardar", bgcolor="#C86DD7", color="white", on_click=guardar),
        ]
        dlg.actions_alignment = ft.MainAxisAlignment.END
        open_dialog(dlg)

    def abrir_dialogo_editar(prod):
        nombre_f = ft.TextField(label="Nombre", border_radius=12, value=str(prod["Nombre"]))
        precio_f = ft.TextField(label="Precio", border_radius=12, keyboard_type=ft.KeyboardType.NUMBER, value=str(prod["Precio"]))
        cad_f = ft.TextField(label="FechaCaducidad (YYYYMMDD o YYYY-MM-DD)", border_radius=12, value=str(prod["FechaCaducidad"]))
        desc_f = ft.TextField(label="Descripción", border_radius=12, multiline=True, min_lines=2, max_lines=3, value=str(prod["Descripcion"]))
        marca_f = ft.TextField(label="Marca", border_radius=12, value=str(prod["Marca"]))
        unidad_f = ft.TextField(label="Unidad de medida", border_radius=12, value=str(prod["UnidadMedida"]))

        dlg = ft.AlertDialog(title=ft.Text(f"Editar producto #{prod['IdProductos']}"))

        def validar():
            ok = True
            for f in [nombre_f, precio_f, cad_f, desc_f, marca_f, unidad_f]:
                f.error_text = None

            n = normalizar_nombre(nombre_f.value)
            pr = (precio_f.value or "").strip()
            fc = (cad_f.value or "").strip()
            d = (desc_f.value or "").strip()
            m = (marca_f.value or "").strip()
            u = (unidad_f.value or "").strip()

            if not n:
                nombre_f.error_text = "Requerido"
                ok = False
            else:
                if db_existe_nombre(n, exclude_id=int(prod["IdProductos"])):
                    nombre_f.error_text = "Ya existe otro producto con ese nombre"
                    ok = False

            try:
                precio = float(pr)
                if precio <= 0:
                    raise ValueError()
            except:
                precio_f.error_text = "Precio inválido (debe ser > 0)"
                ok = False
                precio = 0.0

            try:
                fecha_cad = parse_fecha_caducidad(fc)
            except:
                cad_f.error_text = "Fecha inválida (YYYYMMDD o YYYY-MM-DD)"
                ok = False
                fecha_cad = 0

            if not d:
                desc_f.error_text = "Requerido"
                ok = False
            if not m:
                marca_f.error_text = "Requerido"
                ok = False
            if not u:
                unidad_f.error_text = "Requerido"
                ok = False

            page.update()
            return ok, n, precio, fecha_cad, d, m, u

        def cancelar(ev):
            close_dialog(dlg)

        def guardar(ev):
            ok, n, precio, fecha_cad, d, m, u = validar()
            if not ok:
                return
            try:
                db_editar_producto(prod["IdProductos"], n, precio, fecha_cad, d, m, u)
                close_dialog(dlg)
                recargar()
                show_snack("Producto actualizado ✅")
            except Exception as ex:
                show_snack(f"Error al actualizar: {ex}")

        dlg.content = ft.Column([nombre_f, precio_f, cad_f, desc_f, marca_f, unidad_f], tight=True, width=480)
        dlg.actions = [
            ft.TextButton("Cancelar", on_click=cancelar),
            ft.ElevatedButton("Guardar", bgcolor="#C86DD7", color="white", on_click=guardar),
        ]
        dlg.actions_alignment = ft.MainAxisAlignment.END
        open_dialog(dlg)

    def confirmar_eliminar(id_prod):
        dlg = ft.AlertDialog(title=ft.Text("Eliminar producto"))

        def cancelar(ev):
            close_dialog(dlg)

        def eliminar(ev):
            try:
                db_eliminar_producto(id_prod)
                close_dialog(dlg)
                recargar()
                show_snack("Producto eliminado 🗑️")
            except Exception as ex:
                show_snack(f"Error al eliminar: {ex}")

        dlg.content = ft.Text(f"¿Seguro que deseas eliminar el producto ID {id_prod}?")
        dlg.actions = [
            ft.TextButton("Cancelar", on_click=cancelar),
            ft.ElevatedButton("Eliminar", bgcolor="#E53935", color="white", on_click=eliminar),
        ]
        dlg.actions_alignment = ft.MainAxisAlignment.END
        open_dialog(dlg)

    # -----------------------------
    # Encabezado
    # -----------------------------
    header = ft.Row(
        [
            ft.Text("Inventario", size=22, weight="bold", color="#C86DD7"),
            ft.Container(expand=True),
            txt_buscar,
            ft.ElevatedButton(
                "+ Nuevo producto",
                bgcolor="#C86DD7",
                color="white",
                on_click=abrir_dialogo_nuevo,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=20),
                    padding=18,
                ),
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    recargar()

    # ✅ Tabla responsiva:
    # - Scroll vertical: ListView
    # - Scroll horizontal: Row(scroll="auto") envolviendo la tabla
    tabla_responsiva = ft.Row(
        controls=[
            ft.Container(
                padding=6,
                content=tabla,
            )
        ],
        scroll=ft.ScrollMode.AUTO,  # horizontal
    )

    main_content = ft.Container(
        expand=True,
        bgcolor="#F9F6FB",
        padding=20,
        content=ft.Column(
            [
                header,
                ft.Container(height=10),
                ft.Container(
                    expand=True,
                    bgcolor="white",
                    border_radius=18,
                    padding=12,
                    content=ft.ListView(
                        expand=True,
                        controls=[tabla_responsiva],
                    ),
                ),
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

    return ft.View(route="/inventario", controls=[layout], appbar=appbar)
