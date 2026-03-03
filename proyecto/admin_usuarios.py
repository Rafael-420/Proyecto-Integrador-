# admin_usuarios.py
import flet as ft

# Compatibilidad íconos (Flet nuevo)
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons



def admin_usuarios_view(page: ft.Page, nombre_admin: str = "Administrador") -> ft.View:
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

    txt_buscar = ft.TextField(label="Buscar usuario/cliente", border_radius=12, width=320)

    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID Cliente")),
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

    def cargar_demo():
        tabla.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text("1")),
                ft.DataCell(ft.Text("Ana")),
                ft.DataCell(ft.Text("López")),
                ft.DataCell(ft.Text("8888888888")),
                ft.DataCell(ft.Text("ana@correo.com")),
                ft.DataCell(ft.Text("22")),
            ])
        ]
        page.update()

    cargar_demo()

    header = ft.Row(
        [
            ft.Text("Control de usuarios (Clientes)", size=22, weight="bold", color="#C86DD7"),
            ft.Container(expand=True),
            txt_buscar,
            ft.ElevatedButton(
                "+ Nuevo cliente",
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

    return ft.View(route="/admin_usuarios", controls=[content], appbar=appbar)