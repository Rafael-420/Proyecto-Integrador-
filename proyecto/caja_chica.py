import flet as ft

# Compatibilidad íconos (Flet nuevo)
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

from datetime import datetime, date
from connector import get_connection  # usa tu conexión actual


def caja_chica_view(page: ft.Page, nombre: str):
    # -----------------------
    # Helpers
    # -----------------------
    def money(v: float) -> str:
        try:
            return f"$ {float(v):,.2f}"
        except Exception:
            return "$ 0.00"

    def to_float(s: str):
        s = (s or "").strip().replace(",", "")
        if not s:
            return None
        try:
            return float(s)
        except Exception:
            return None

    def show_snack(msg: str, ok: bool = False):
        page.snack_bar = ft.SnackBar(
            ft.Text(msg),
            bgcolor="#2e7d32" if ok else "#c62828",
        )
        page.snack_bar.open = True
        page.update()

    # -----------------------
    # UI controls (form)
    # -----------------------
    dd_tipo = ft.Dropdown(
        label="Tipo de movimiento",
        options=[
            ft.dropdown.Option("Ingreso"),
            ft.dropdown.Option("Egreso"),
        ],
        value=None,
        border_radius=12,
    )

    txt_monto = ft.TextField(
        label="Monto",
        hint_text="Ej: 150.50",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
    )

    txt_desc = ft.TextField(
        label="Descripción",
        hint_text="Ej: Compra de insumos / Cambio / Etc.",
        multiline=True,
        min_lines=2,
        max_lines=3,
        border_radius=12,
    )

    # Filtros
    chk_hoy = ft.Checkbox(label="Mostrar solo hoy", value=False)

    # Totales
    lbl_ingresos = ft.Text("Ingresos: $ 0.00", weight="bold")
    lbl_egresos = ft.Text("Egresos: $ 0.00", weight="bold")
    lbl_balance = ft.Text("Balance: $ 0.00", weight="bold")

    # Tabla movimientos
    table = ft.DataTable(
        expand=True,
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Monto")),
            ft.DataColumn(ft.Text("Descripción")),
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("Hora")),
        ],
        rows=[],
    )

    table_container = ft.Container(
        expand=True,
        padding=10,
        bgcolor="white",
        border_radius=16,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Movimientos", size=18, weight="bold"),
                        ft.Container(expand=True),
                        chk_hoy,
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="Actualizar",
                            on_click=lambda e: load_movimientos(),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                        controls=[table],
                    ),
                ),
            ],
            expand=True,
        ),
    )

    # -----------------------
    # Apartado COBRO PEDIDOS (BEBIDAS)
    # -----------------------
    chk_pedidos_hoy = ft.Checkbox(label="Pedidos solo hoy", value=True)

    pedidos_table = ft.DataTable(
        expand=True,
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Total")),
            ft.DataColumn(ft.Text("Mesa")),
            ft.DataColumn(ft.Text("Estatus")),
            ft.DataColumn(ft.Text("Acción")),
        ],
        rows=[],
    )

    pedidos_container = ft.Container(
        expand=True,
        padding=10,
        bgcolor="white",
        border_radius=16,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Cobro de pedidos (Bebidas)", size=18, weight="bold"),
                        ft.Container(expand=True),
                        chk_pedidos_hoy,
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="Actualizar pedidos",
                            on_click=lambda e: load_pedidos_bebidas(),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    "Aquí cobras pedidos del menú y se registran como Ingreso automáticamente.",
                    size=12,
                    color="#777777",
                ),
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                        controls=[pedidos_table],
                    ),
                ),
            ],
            expand=True,
        ),
    )

    # Heurística para "BEBIDAS" sin cambiar BD:
    # Si en tu sistema ya tienes un campo categoría, dímelo y lo conecto a eso.
    BEBIDA_KEYWORDS = (
        "bebida", "café", "cafe", "refresco", "agua", "té", "te", "jug", "soda",
        "malteada", "frapp", "limonada", "naranja", "cerveza"
    )

    def parece_bebida(texto: str) -> bool:
        t = (texto or "").strip().lower()
        if not t:
            return False
        return any(k in t for k in BEBIDA_KEYWORDS)

    # Dialog cobro
    txt_recibido = ft.TextField(
        label="Efectivo recibido",
        hint_text="Ej: 200",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
    )
    lbl_total_cobro = ft.Text("Total: $ 0.00", weight="bold")
    lbl_cambio = ft.Text("Cambio: $ 0.00", weight="bold")

    pedido_actual = {"id": None, "total": 0.0, "producto": ""}

    def recalcular_cambio(e=None):
        recibido = to_float(txt_recibido.value)
        total = float(pedido_actual.get("total") or 0)
        if recibido is None:
            lbl_cambio.value = "Cambio: $ 0.00"
        else:
            cambio = recibido - total
            lbl_cambio.value = f"Cambio: {money(cambio)}"
        page.update()

    txt_recibido.on_change = recalcular_cambio

    def cerrar_dialogo():
        dialog.open = False
        page.update()

    def confirmar_cobro():
        # Validaciones de ingreso de dinero
        recibido = to_float(txt_recibido.value)
        total = float(pedido_actual.get("total") or 0)

        if pedido_actual.get("id") is None:
            show_snack("No hay pedido seleccionado.", ok=False)
            return

        if recibido is None:
            show_snack("El efectivo recibido debe ser numérico.", ok=False)
            return

        if recibido <= 0:
            show_snack("El efectivo recibido debe ser mayor a 0.", ok=False)
            return

        if recibido < total:
            show_snack("El efectivo recibido no puede ser menor al total.", ok=False)
            return

        # Registrar cobro: marcar pedido PAGADO + insertar ingreso en caja chica
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)

            # Revalidar estatus para evitar doble cobro
            cur.execute(
                "SELECT Estatus, Producto, Total FROM generarpedido WHERE IdGenerarPedido = %s",
                (pedido_actual["id"],),
            )
            row = cur.fetchone()
            if not row:
                show_snack("El pedido ya no existe.", ok=False)
                return

            est = (row.get("Estatus") or "").strip().lower()
            if est == "pagado":
                show_snack("Este pedido ya está pagado.", ok=False)
                cerrar_dialogo()
                load_pedidos_bebidas()
                return

            # Marcar pagado
            cur2 = conn.cursor()
            cur2.execute(
                "UPDATE generarpedido SET Estatus = 'Pagado' WHERE IdGenerarPedido = %s",
                (pedido_actual["id"],),
            )

            now = datetime.now()
            fecha = now.date()
            hora = now.time().replace(microsecond=0)

            desc = f"VENTA BEBIDAS (Pedido #{pedido_actual['id']}) - {pedido_actual.get('producto','')}"
            cur2.execute(
                """
                INSERT INTO ingresos_egresos (TipoMovimiento, Monto, Descripcion, Fecha, Hora)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ("Ingreso", total, desc, fecha, hora),
            )

            conn.commit()
            show_snack("✅ Cobro registrado en Caja Chica.", ok=True)
            cerrar_dialogo()

            # refrescar ambos
            load_movimientos()
            load_pedidos_bebidas()

        except Exception as ex:
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass
            show_snack(f"Error al cobrar: {ex}", ok=False)
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Cobrar pedido"),
        content=ft.Column(
            tight=True,
            controls=[
                lbl_total_cobro,
                txt_recibido,
                lbl_cambio,
                ft.Text(
                    "Validación: el efectivo recibido debe ser mayor o igual al total.",
                    size=12,
                    color="#777777",
                ),
            ],
        ),
        actions=[
            ft.OutlinedButton("Cancelar", on_click=lambda e: cerrar_dialogo()),
            ft.ElevatedButton(
                "Confirmar cobro",
                bgcolor="#C86DD7",
                color="white",
                on_click=lambda e: confirmar_cobro(),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # -----------------------
    # DB actions
    # -----------------------
    def load_movimientos():
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)

            if chk_hoy.value:
                cur.execute(
                    """
                    SELECT idMovimiento, TipoMovimiento, Monto, Descripcion, Fecha, Hora
                    FROM ingresos_egresos
                    WHERE Fecha = %s
                    ORDER BY Fecha DESC, Hora DESC, idMovimiento DESC
                    """,
                    (date.today(),),
                )
            else:
                cur.execute(
                    """
                    SELECT idMovimiento, TipoMovimiento, Monto, Descripcion, Fecha, Hora
                    FROM ingresos_egresos
                    ORDER BY Fecha DESC, Hora DESC, idMovimiento DESC
                    """
                )

            data = cur.fetchall()

            table.rows.clear()
            total_ing = 0.0
            total_egr = 0.0

            for r in data:
                tipo = (r.get("TipoMovimiento") or "").strip()
                monto = float(r.get("Monto") or 0)

                if tipo.lower() == "ingreso":
                    total_ing += monto
                elif tipo.lower() == "egreso":
                    total_egr += monto

                table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(r.get("idMovimiento", "")))),
                            ft.DataCell(ft.Text(tipo)),
                            ft.DataCell(ft.Text(money(monto))),
                            ft.DataCell(ft.Text(str(r.get("Descripcion", "")))),
                            ft.DataCell(ft.Text(str(r.get("Fecha", "")))),
                            ft.DataCell(ft.Text(str(r.get("Hora", "")))),
                        ]
                    )
                )

            lbl_ingresos.value = f"Ingresos: {money(total_ing)}"
            lbl_egresos.value = f"Egresos: {money(total_egr)}"
            lbl_balance.value = f"Balance: {money(total_ing - total_egr)}"

            page.update()

        except Exception as ex:
            show_snack(f"Error al cargar movimientos: {ex}", ok=False)
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    def guardar_movimiento(e):
        tipo = (dd_tipo.value or "").strip()
        monto_raw = (txt_monto.value or "").strip().replace(",", "")
        desc = (txt_desc.value or "").strip()

        # Validaciones (más estrictas para ingreso/egreso manual)
        if not tipo or not monto_raw or not desc:
            show_snack("Completa Tipo, Monto y Descripción.", ok=False)
            return

        monto = to_float(monto_raw)
        if monto is None:
            show_snack("El monto debe ser numérico (ej: 150.50).", ok=False)
            return
        if monto <= 0:
            show_snack("El monto debe ser mayor a 0.", ok=False)
            return
        if len(desc) < 3:
            show_snack("La descripción es muy corta.", ok=False)
            return

        now = datetime.now()
        fecha = now.date()
        hora = now.time().replace(microsecond=0)

        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO ingresos_egresos (TipoMovimiento, Monto, Descripcion, Fecha, Hora)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (tipo, monto, desc, fecha, hora),
            )
            conn.commit()

            dd_tipo.value = None
            txt_monto.value = ""
            txt_desc.value = ""

            show_snack("Movimiento guardado correctamente.", ok=True)
            load_movimientos()

        except Exception as ex:
            show_snack(f"Error al guardar: {ex}", ok=False)
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    def load_pedidos_bebidas():
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)

            if chk_pedidos_hoy.value:
                cur.execute(
                    """
                    SELECT IdGenerarPedido, Producto, Total, NumeroMesa, Estatus, FechaPedido, HoraPedido
                    FROM generarpedido
                    WHERE FechaPedido = %s AND Estatus <> 'Pagado'
                    ORDER BY FechaPedido DESC, HoraPedido DESC, IdGenerarPedido DESC
                    """,
                    (date.today(),),
                )
            else:
                cur.execute(
                    """
                    SELECT IdGenerarPedido, Producto, Total, NumeroMesa, Estatus, FechaPedido, HoraPedido
                    FROM generarpedido
                    WHERE Estatus <> 'Pagado'
                    ORDER BY FechaPedido DESC, HoraPedido DESC, IdGenerarPedido DESC
                    """
                )

            data = cur.fetchall()

            pedidos_table.rows.clear()

            # Filtrar bebidas por heurística
            data_bebidas = [r for r in data if parece_bebida(r.get("Producto", ""))]

            for r in data_bebidas:
                pid = int(r.get("IdGenerarPedido"))
                producto = str(r.get("Producto") or "")
                total = float(r.get("Total") or 0)
                mesa = r.get("NumeroMesa")
                estatus = str(r.get("Estatus") or "")

                def abrir_cobro(e, pid=pid, total=total, producto=producto):
                    pedido_actual["id"] = pid
                    pedido_actual["total"] = total
                    pedido_actual["producto"] = producto

                    lbl_total_cobro.value = f"Total: {money(total)}"
                    txt_recibido.value = ""
                    lbl_cambio.value = "Cambio: $ 0.00"

                    page.dialog = dialog
                    dialog.open = True
                    page.update()

                btn = ft.ElevatedButton(
                    "Cobrar",
                    bgcolor="#C86DD7",
                    color="white",
                    height=34,
                    on_click=abrir_cobro,
                )

                pedidos_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(pid))),
                            ft.DataCell(ft.Text(producto, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)),
                            ft.DataCell(ft.Text(money(total))),
                            ft.DataCell(ft.Text(str(mesa))),
                            ft.DataCell(ft.Text(estatus)),
                            ft.DataCell(btn),
                        ]
                    )
                )

            page.update()

        except Exception as ex:
            show_snack(f"Error al cargar pedidos: {ex}", ok=False)
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    # Recargar si cambia filtro
    chk_hoy.on_change = lambda e: load_movimientos()
    chk_pedidos_hoy.on_change = lambda e: load_pedidos_bebidas()

    # -----------------------
    # Layout
    # -----------------------
    header_card = ft.Container(
        padding=20,
        bgcolor="white",
        border_radius=24,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text("Caja Chica", size=26, weight="bold", color="#222222"),
                ft.Text(
                    "Controla los movimientos de efectivo del día.",
                    size=14,
                    color="#666666",
                ),
                ft.Text(
                    f"Empleado: {nombre}",
                    size=12,
                    color="#888888",
                ),
            ],
        ),
    )

    form_card = ft.Container(
        padding=20,
        bgcolor="white",
        border_radius=24,
        content=ft.Column(
            controls=[
                ft.Text("Nuevo movimiento", size=18, weight="bold"),
                dd_tipo,
                txt_monto,
                txt_desc,
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Guardar",
                            bgcolor="#C86DD7",
                            color="white",
                            on_click=guardar_movimiento,
                            height=44,
                        ),
                        ft.OutlinedButton(
                            "Limpiar",
                            on_click=lambda e: (
                                setattr(dd_tipo, "value", None),
                                setattr(txt_monto, "value", ""),
                                setattr(txt_desc, "value", ""),
                                page.update(),
                            ),
                            height=44,
                        ),
                    ],
                    spacing=10,
                ),
                ft.Divider(),
                ft.Row(
                    controls=[lbl_ingresos, lbl_egresos, lbl_balance],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=12,
        ),
    )

    content = ft.Container(
        expand=True,
        bgcolor="#F9F6FB",
        padding=20,
        content=ft.Column(
            expand=True,
            spacing=16,
            controls=[
                ft.Row(
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            tooltip="Regresar",
                            on_click=lambda e: (page.views.pop(), page.update()),
                        ),
                        ft.Text(""),
                    ]
                ),
                header_card,

                # 3 columnas: (form) (movimientos) (cobro pedidos)
                ft.Row(
                    expand=True,
                    controls=[
                        ft.Container(expand=4, content=form_card),
                        ft.Container(expand=6, content=table_container),
                        ft.Container(expand=6, content=pedidos_container),
                    ],
                ),
            ],
        ),
    )

    # cargar al entrar
    load_movimientos()
    load_pedidos_bebidas()

    return ft.View(route="/caja_chica", controls=[content])
