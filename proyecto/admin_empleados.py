# admin_empleados.py
import flet as ft

# Compatibilidad íconos (Flet nuevo)
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons



def admin_empleados_view(page: ft.Page, nombre_admin: str = "Administrador") -> ft.View:
    def volver_admin(e=None):
        if len(page.views) > 1:
            page.views.pop()
        page.go("/admin")
        page.update()

    def cerrar_sesion(e):
        from login import LoginView
        page.views.clear()
        page.views.append(LoginView(page))
        page.go("/")
        page.update()

    # UI
    txt_buscar = ft.TextField(label="Buscar empleado", border_radius=12, width=320)

    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Nombre")),
            ft.DataColumn(ft.Text("Apellido")),
            ft.DataColumn(ft.Text("Teléfono")),
            ft.DataColumn(ft.Text("Correo")),
            ft.DataColumn(ft.Text("Usuario_ID")),
        ],
        rows=[],
        border_radius=12,
        heading_row_color="#F3E9F7",
        data_row_min_height=52,
        data_row_max_height=80,
    )

    # Nota: aquí luego conectamos a BD (tabla empleado + joins si quieres)
    # Por ahora, lo dejamos listo para trabajar por módulos.
    def cargar_demo():
        tabla.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text("1")),
                ft.DataCell(ft.Text("Juan")),
                ft.DataCell(ft.Text("Pérez")),
                ft.DataCell(ft.Text("9999999999")),
                ft.DataCell(ft.Text("juan@correo.com")),
                ft.DataCell(ft.Text("10")),
            ])
        ]
        page.update()

    cargar_demo()

    header = ft.Row(
        [
            ft.Text("Control de empleados", size=22, weight="bold", color="#C86DD7"),
            ft.Container(expand=True),
            txt_buscar,
            ft.ElevatedButton(
                "+ Nuevo empleado",
                bgcolor="#C86DD7",
                color="white",
                on_click=lambda e: page.snack_bar.__setattr__("open", True),  # placeholder
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), padding=18),
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    content = ft.Container(
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
                        controls=[
                            ft.Row([ft.Container(content=tabla, padding=6)], scroll=ft.ScrollMode.AUTO)
                        ],
                    ),
                ),
                ft.Row(
                    [
                        ft.Text(f"Admin: {nombre_admin}", size=12, color="#888888"),
                        ft.Container(expand=True),
                        ft.TextButton("Cerrar sesión", on_click=cerrar_sesion),
                    ]
                )
            ],
            expand=True,
        ),
    )

    appbar = ft.AppBar(
        title=ft.Text("Corallie Bubble - Admin"),
        bgcolor="#C86DD7",
        color="white",
    )

    return ft.View(route="/admin_empleados", controls=[content], appbar=appbar)