import flet as ft
from datetime import datetime
import asyncio

from connector import get_connection
from corte_manager import obtener_info_corte, resumen_por_corte, cerrar_corte

# -----------------------------
# PARCHES COMPATIBILIDAD FLET
# -----------------------------
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

if not hasattr(ft, "animation"):
    ft.animation = ft


def build_sidebar(
    page: ft.Page,
    nombre: str,
    ir_inicio,
    ir_inventario,
    ir_movimientos,
    ir_caja_chica,
    ir_reportes,
    cerrar_sesion_real,
):
    """Sidebar unificado (estilo POS):

    - Colapsar/expandir con animación
    - Menú de 3 puntos: Perfil / Ajustes / Cerrar sesión
    - Confirmación al cerrar sesión

    Nota: El diálogo de Perfil incluye también el resumen de corte y movimientos,
    pero EXCLUYE los campos de Fecha/Hora por solicitud.
    """

    # -----------------------------
    # Helpers
    # -----------------------------
    def open_dialog(dlg: ft.AlertDialog):
        if hasattr(page, "open"):
            page.open(dlg)
        else:
            page.dialog = dlg
            dlg.open = True
            page.update()

    def _store_get(key, default=None):
        # Prefer memoria de sesión (sync)
        try:
            store = getattr(page, "_mem_store", None)
            if isinstance(store, dict) and key in store:
                return store.get(key)
        except Exception:
            pass

        # Compat: client_storage viejo
        try:
            if hasattr(page, "client_storage"):
                return page.client_storage.get(key)
        except Exception:
            pass

        return default

    def _store_remove(key):
        try:
            store = getattr(page, "_mem_store", None)
            if isinstance(store, dict) and key in store:
                store.pop(key, None)
        except Exception:
            pass
        try:
            if hasattr(page, "client_storage"):
                page.client_storage.remove(key)
        except Exception:
            pass

    def _get(info_dict, keys, default="-"):
        if not info_dict:
            return default
        for k in keys:
            if k in info_dict and info_dict[k] not in (None, ""):
                return info_dict[k]
        return default

    def money(v):
        try:
            return f"$ {float(v):,.2f}"
        except Exception:
            return "$ 0.00"

    # -----------------------------
    # DB: movimientos por corte (entradas/salidas)
    # -----------------------------
    def db_movimientos_corte(corte_id: int, limit: int = 6):
        if not corte_id:
            return []

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
                WHERE CorteCaja_idCorteCaja = %s

                UNION ALL

                SELECT
                    'Salida' AS Tipo,
                    FechaSalida AS FechaMov,
                    Cantidad AS Cant,
                    Detalle AS Texto
                FROM salidasproductos
                WHERE CorteCaja_idCorteCaja = %s

                ORDER BY FechaMov DESC
                LIMIT {int(limit)}
                """,
                (int(corte_id), int(corte_id)),
            )
            return cur.fetchall() or []
        except Exception:
            return []
        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except Exception:
                pass

    # -----------------------------
    # Estado corte
    # -----------------------------
    corte_id = _store_get("corte_id")
    corte_id_int = int(corte_id) if corte_id else None

    info = obtener_info_corte(corte_id_int) if corte_id_int else None
    if corte_id_int:
        ing, egr, bal, movs, platillos = resumen_por_corte(corte_id_int)
    else:
        ing, egr, bal, movs, platillos = 0.0, 0.0, 0.0, 0, 0

    movs_list = db_movimientos_corte(corte_id_int or 0, limit=6)

    # -----------------------------
    # Confirmar cerrar sesión
    # -----------------------------
    def confirmar_cierre(e=None):
        # resumen corto
        lines = []
        if corte_id_int:
            lines.append(f"Corte activo: #{corte_id_int}")
            lines.append(f"Ingresos: {money(ing)}   |   Egresos: {money(egr)}")
            lines.append(f"Balance: {money(bal)}   |   Movimientos: {movs}")
        else:
            lines.append("No hay corte activo detectado.")

        mov_txt = "Sin movimientos recientes."
        if movs_list:
            parts = []
            for m in movs_list[:6]:
                parts.append(
                    f"• {m.get('Tipo')} | {m.get('FechaMov')} | {m.get('Cant')} | {str(m.get('Texto') or '')[:40]}"
                )
            mov_txt = "\n".join(parts)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cerrar sesión"),
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Text("¿Deseas cerrar sesión?", weight="bold"),
                    ft.Container(height=6),
                    ft.Text("\n".join(lines), size=12),
                    ft.Divider(),
                    ft.Text("Movimientos del corte (recientes):", size=12, weight="bold"),
                    ft.Text(mov_txt, size=11),
                ],
            ),
        )

        def cancelar(ev=None):
            dlg.open = False
            page.update()

        def solo_salir(ev=None):
            dlg.open = False
            page.update()
            cerrar_sesion_real(None)

        def cerrar_corte_y_salir(ev=None):
            try:
                if corte_id_int:
                    cerrar_corte(int(corte_id_int))
            except Exception:
                pass

            try:
                _store_remove("corte_id")
                _store_remove("empleado")
            except Exception:
                pass

            dlg.open = False
            page.update()
            cerrar_sesion_real(None)

        actions = [ft.TextButton("Cancelar", on_click=cancelar)]
        if corte_id_int:
            actions.append(ft.OutlinedButton("Solo cerrar sesión", on_click=solo_salir))
            actions.append(
                ft.ElevatedButton(
                    "Cerrar corte y salir",
                    bgcolor="#C86DD7",
                    color="white",
                    on_click=cerrar_corte_y_salir,
                )
            )
        else:
            actions.append(
                ft.ElevatedButton(
                    "Sí, cerrar sesión",
                    bgcolor="#C86DD7",
                    color="white",
                    on_click=solo_salir,
                )
            )

        dlg.actions = actions
        dlg.actions_alignment = ft.MainAxisAlignment.END
        open_dialog(dlg)

    # -----------------------------
    # Perfil: agregar info de corte (SIN fecha/hora)
    # -----------------------------
    def ver_perfil(e=None):
        # Texto movimientos
        mov_txt = "Sin movimientos recientes."
        if movs_list:
            parts = []
            for m in movs_list[:8]:
                parts.append(
                    f"• {m.get('Tipo')} | {m.get('FechaMov')} | Cant: {m.get('Cant')}"
                )
            mov_txt = "\n".join(parts)

        corte_block = ft.Container(
            padding=12,
            border_radius=16,
            bgcolor="#F3F4F6",
            content=ft.Column(
                tight=True,
                spacing=6,
                controls=[
                    ft.Row(
                        [
                            ft.Text("Corte de caja", weight="bold"),
                            ft.Container(expand=True),
                            ft.Text(
                                f"#{corte_id_int}" if corte_id_int else "—",
                                weight="bold",
                                color="#6B7280",
                            ),
                        ]
                    ),
                    ft.Text(
                        (
                            f"Inicio: {_get(info, ['Fecha_Inicio', 'FechaInicio', 'FechaInicioCorte'])}"
                        )
                        if corte_id_int
                        else "Inicio: —",
                        size=12,
                        color="#374151",
                    ),
                    ft.Divider(height=6),
                    ft.Text(f"Ingresos: {money(ing)}", size=12),
                    ft.Text(f"Egresos: {money(egr)}", size=12),
                    ft.Text(f"Balance: {money(bal)}   |   Movs: {movs}", size=12, color="#6B7280"),
                    ft.Divider(height=10),
                    ft.Text("Movimientos recientes", weight="bold", size=12),
                    ft.Text(mov_txt, size=11, color="#4B5563"),
                ],
            ),
        )

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Perfil"),
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Row(
                        [
                            ft.Container(
                                width=56,
                                height=56,
                                border_radius=18,
                                bgcolor="#FFE0F0",
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text((nombre[:1] or "U").upper(), size=22, weight="bold"),
                            ),
                            ft.Column(
                                [
                                    ft.Text(nombre, size=16, weight="bold"),
                                    ft.Text("Rol: Empleado", size=12, color="#6B7280"),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Divider(),
                    corte_block,
                ],
            ),
            actions=[ft.TextButton("Cerrar", on_click=lambda ev: setattr(dlg, "open", False) or page.update())],
        )
        open_dialog(dlg)

    # -----------------------------
    # Sidebar: animado + estilo POS
    # -----------------------------
    sidebar_state = {"collapsed": False}
    nav_text_refs = []

    # -----------------------------
    # Fecha + hora actual (solo UNA línea)
    # -----------------------------
    lbl_datetime = ft.Text("", size=11, color="white70")

    def paint_datetime():
        now = datetime.now()
        lbl_datetime.value = now.strftime("%Y-%m-%d  %H:%M")
        try:
            lbl_datetime.update()
        except Exception:
            page.update()

    async def _datetime_loop():
        while True:
            try:
                paint_datetime()
                await asyncio.sleep(1)
            except Exception:
                await asyncio.sleep(1)

    if hasattr(page, "run_task") and not getattr(page, "_sidebar_datetime_started", False):
        page._sidebar_datetime_started = True
        page.run_task(_datetime_loop)

    paint_datetime()

    # Avatar (no se recorta al colapsar)
    avatar_txt = ft.Text((nombre[:1] or "U").upper(), weight="bold", color="#6C2BD9")
    avatar = ft.Container(
        width=44,
        height=44,
        border_radius=16,
        bgcolor="#FFE0F0",
        alignment=ft.Alignment.CENTER,
        content=avatar_txt,
    )

    user_info = ft.Column(
        [
            ft.Text(nombre, size=13, weight="bold", color="white", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text("Empleado", size=11, color="white70"),
        ],
        spacing=1,
        expand=True,
    )

    user_menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_HORIZ,
        icon_color="white",
        items=[
            ft.PopupMenuItem(content=ft.Text("Ver perfil"), on_click=ver_perfil),
            ft.PopupMenuItem(content=ft.Text("Ajustes (próx.)")),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(content=ft.Text("Cerrar sesión"), on_click=confirmar_cierre),
        ],
    )

    user_row = ft.Row(
        [avatar, user_info, user_menu],
        spacing=10,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Header expandido vs colapsado (layout distinto para evitar recortes)
    user_header_expanded = ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        border_radius=18,
        bgcolor="rgba(255,255,255,0.12)",
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=user_row,
    )

    user_header_collapsed = ft.Container(
        padding=6,
        border_radius=18,
        bgcolor="rgba(255,255,255,0.12)",
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        alignment=ft.Alignment.CENTER,
        content=avatar,
    )

    user_header_switch = ft.AnimatedSwitcher(
        content=user_header_expanded,
        transition=ft.AnimatedSwitcherTransition.FADE,
        duration=200,
        reverse_duration=160,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
    )

    def nav_item(icon, text, on_click):
        icon_ctrl = ft.Icon(icon, color="white", size=22)
        text_ctrl = ft.Text(text, color="white", size=13, visible=True)
        nav_text_refs.append(text_ctrl)

        item = ft.Container(
            height=44,
            padding=ft.padding.symmetric(horizontal=10),
            border_radius=16,
            ink=True,
            on_click=on_click,
            animate=ft.animation.Animation(180, ft.AnimationCurve.EASE_OUT),
            content=ft.Row([icon_ctrl, text_ctrl], spacing=10),
        )

        def on_hover(e):
            if getattr(item, "page", None) is None:
                return
            item.bgcolor = "rgba(255,255,255,0.18)" if e.data == "true" else None
            try:
                item.update()
            except AssertionError:
                return


        item.on_hover = on_hover
        return item

    def toggle_sidebar(e=None):
        sidebar_state["collapsed"] = not sidebar_state["collapsed"]
        collapsed = sidebar_state["collapsed"]

        sidebar.width = 76 if collapsed else 240
        sidebar.padding = 12 if collapsed else 16

        user_info.visible = not collapsed
        user_menu.visible = not collapsed
        user_row.alignment = ft.MainAxisAlignment.CENTER if collapsed else ft.MainAxisAlignment.SPACE_BETWEEN
        user_row.spacing = 0 if collapsed else 10

        # Cambia el header completo para que el avatar NO se recorte
        user_header_switch.content = user_header_collapsed if collapsed else user_header_expanded

        # Avatar un poquito más chico en modo colapsado
        avatar.width = 40 if collapsed else 44
        avatar.height = 40 if collapsed else 44
        avatar.border_radius = 14 if collapsed else 16
        avatar_txt.size = 14 if collapsed else None

        # Fecha/hora: visible solo expandido
        lbl_datetime.visible = not collapsed

        for t in nav_text_refs:
            t.visible = not collapsed

        page.update()

    nav_column = ft.Column(
        [
            nav_item(ft.Icons.HOME, "Inicio", ir_inicio),
            nav_item(ft.Icons.INVENTORY_2, "Ver inventario", ir_inventario),
            nav_item(ft.Icons.SWAP_HORIZ, "Entradas y salidas", ir_movimientos),
            nav_item(ft.Icons.ACCOUNT_BALANCE_WALLET, "Caja chica", ir_caja_chica),
            nav_item(ft.Icons.ASSESSMENT, "Reportes", ir_reportes),
        ],
        spacing=6,
    )

    header_row = ft.Row(
        [
            ft.IconButton(icon=ft.Icons.MENU, icon_color="white", on_click=toggle_sidebar),
            ft.Container(expand=True),
        ],
        alignment=ft.MainAxisAlignment.START,
    )

    sidebar = ft.Container(
        width=240,
        bgcolor="#C86DD7",
        padding=16,
        animate=ft.animation.Animation(220, ft.AnimationCurve.EASE_OUT),
        content=ft.Column(
            [
                header_row,
                ft.Container(height=10),
                user_header_switch,
                ft.Container(height=8),
                ft.Container(
                    padding=ft.padding.only(left=6),
                    content=lbl_datetime,
                ),
                ft.Container(height=10),
                nav_column,
                ft.Container(expand=True),
                nav_item(ft.Icons.LOGOUT, "Cerrar sesión", confirmar_cierre),
            ],
            spacing=6,
        ),
    )

    return sidebar
