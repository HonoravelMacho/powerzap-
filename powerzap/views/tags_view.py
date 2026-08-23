"""CRUD de etiquetas coloridas."""
import flet as ft

from powerzap import db

PALETTE = [
    "#f44336", "#e91e63", "#9c27b0", "#673ab7", "#3f51b5",
    "#2196f3", "#00bcd4", "#009688", "#4caf50", "#8bc34a",
    "#ff9800", "#ff5722", "#795548", "#607d8b",
]


class TagDialog(ft.AlertDialog):
    def __init__(self, page, on_done, tag=None):
        super().__init__(modal=True)
        self.page_ref = page
        self.tag = tag
        self.on_done = on_done
        self.color = tag["color"] if tag else PALETTE[5]

        self.name_field = ft.TextField(label="Nome da etiqueta", width=300,
                                       value=tag["name"] if tag else "")
        self.swatches = ft.Row(wrap=True, spacing=6)

        self.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: self._close()),
            ft.FilledButton("Salvar", on_click=lambda e: self._save()),
        ]
        self.content = ft.Container(
            width=360,
            content=ft.Column([
                ft.Text("Editar etiqueta" if tag else "Nova etiqueta",
                        size=18, weight=ft.FontWeight.BOLD),
                self.name_field,
                ft.Text("Cor", size=13),
                self.swatches,
                ft.Container(height=8),
                self._preview(),
            ], tight=True, spacing=10),
        )
        self._build_swatches()

    def _preview(self):
        self.preview_text = ft.Text(self.name_field.value or "Etiqueta", size=14)
        return ft.Row([
            ft.Container(width=16, height=16, border_radius=8, bgcolor=self.color),
            self.preview_text,
        ])

    def _build_swatches(self):
        def sw(c):
            selected = c == self.color
            return ft.Container(
                width=30, height=30, border_radius=15, bgcolor=c,
                border=ft.border.all(3, ft.colors.WHITE) if selected else None,
                ink=True, on_click=lambda e, cc=c: self._pick(cc),
            )
        self.swatches.controls = [sw(c) for c in PALETTE]

    def _pick(self, color):
        self.color = color
        self._build_swatches()
        self.update()

    def _close(self):
        self.page_ref.close(self)

    def _save(self):
        name = (self.name_field.value or "").strip()
        if not name:
            self.page_ref.open(ft.SnackBar(ft.Text("Informe o nome da etiqueta.")))
            return
        try:
            if self.tag:
                db.update_tag(self.tag["id"], name, self.color)
            else:
                db.create_tag(name, self.color)
        except Exception:
            self.page_ref.open(ft.SnackBar(ft.Text("Já existe uma etiqueta com esse nome.")))
            return
        self._close()
        self.on_done()


class TagsView(ft.Column):
    def __init__(self, on_change=None):
        super().__init__(expand=True, spacing=12, scroll=ft.ScrollMode.AUTO)
        self.external_on_change = on_change or (lambda: None)
        self.reload()

    def reload(self):
        header = ft.Row([
            ft.Text("Etiquetas", size=22, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.FilledButton("Nova etiqueta", icon=ft.icons.ADD, on_click=self._new),
        ])
        cards = []
        for t in db.list_tags():
            count = sum(1 for m in db.list_messages() if m["tag_id"] == t["id"])
            cards.append(
                ft.Container(
                    padding=14,
                    border_radius=12,
                    bgcolor=ft.colors.with_opacity(0.06, ft.colors.WHITE),
                    content=ft.Row([
                        ft.Container(width=18, height=18, border_radius=9, bgcolor=t["color"]),
                        ft.Text(t["name"], weight=ft.FontWeight.W_600),
                        ft.Text(f"{count} mensagem(ns)", size=13,
                                color=ft.colors.with_opacity(0.55, ft.colors.WHITE)),
                        ft.Container(expand=True),
                        ft.IconButton(ft.icons.EDIT_OUTLINED, icon_size=20,
                                      on_click=lambda e, tag=t: self._edit(tag)),
                        ft.IconButton(ft.icons.DELETE_OUTLINE, icon_size=20,
                                      style=ft.ButtonStyle(color=ft.colors.RED_300),
                                      on_click=lambda e, tag=t: self._delete(tag)),
                    ]),
                )
            )
        self.controls = [header] + (
            cards if cards
            else [ft.Text("Nenhuma etiqueta criada ainda.",
                          color=ft.colors.with_opacity(0.5, ft.colors.WHITE))]
        )
        if hasattr(self, "page") and self.page:
            try:
                self.update()
            except AssertionError:
                pass

    def _new(self, e):
        self.page.open(TagDialog(self.page, on_done=self._changed))

    def _edit(self, tag):
        self.page.open(TagDialog(self.page, on_done=self._changed, tag=tag))

    def _delete(self, tag):
        def confirm(e):
            db.delete_tag(tag["id"])
            self.page.close(dlg)
            self._changed()
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Excluir etiqueta?"),
            content=ft.Text(f"'{tag['name']}' será removida das mensagens."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.close(dlg)),
                ft.FilledButton("Excluir", style=ft.ButtonStyle(bgcolor=ft.colors.RED_600),
                                on_click=confirm),
            ],
        )
        self.page.open(dlg)

    def _changed(self):
        self.reload()
        self.external_on_change()
