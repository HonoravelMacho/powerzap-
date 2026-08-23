"""Calendário interativo em tela cheia com CRUD de mensagens."""
import calendar as pycal
from datetime import date, datetime

import flet as ft

from powerzap import db

STATUS_COLORS = {
    "pendente": ft.colors.AMBER_400,
    "enviada": ft.colors.GREEN_400,
    "falhou": ft.colors.RED_400,
}

PRESET_HOURS = ["08:00", "09:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]


class MessageDialog(ft.AlertDialog):
    def __init__(self, page, on_done, message=None, default_day=None):
        super().__init__(modal=True)
        self.page_ref = page
        self.on_done = on_done
        self.message = message
        self.selected_tag_id = None

        self.number_field = ft.TextField(
            label="Número do WhatsApp",
            hint_text="5511999999999",
            width=280,
        )
        self.text_field = ft.TextField(
            label="Mensagem", multiline=True, min_lines=3, max_lines=6, expand=True
        )
        self.date_field = ft.TextField(
            label="Data", width=140, hint_text="AAAA-MM-DD",
            value=(default_day or date.today().isoformat()),
        )
        self.time_field = ft.TextField(label="Hora", width=100, value="09:00")
        if message:
            self.number_field.value = message["number"]
            self.text_field.value = message["text"]
            dt = message["scheduled_at"]
            self.date_field.value = dt[:10]
            self.time_field.value = dt[11:16]

        self.tag_dropdown = ft.Dropdown(
            label="Etiqueta", width=200,
            options=[ft.dropdown.Option(key="", text="Sem etiqueta")]
            + [
                ft.dropdown.Option(key=str(t["id"]), text=t["name"])
                for t in db.list_tags()
            ],
            value=str(message["tag_id"]) if message and message["tag_id"] else "",
        )

        quick_hours = ft.Row(
            [
                ft.TextButton(h, on_click=lambda e, h=h: self._set_hour(h))
                for h in PRESET_HOURS
            ],
            wrap=True, spacing=4,
        )

        self.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: self._close()),
            ft.FilledButton("Salvar", icon=ft.icons.SAVE, on_click=lambda e: self._save()),
        ]
        if message:
            self.actions.insert(
                0,
                ft.TextButton(
                    "Excluir", icon=ft.icons.DELETE_OUTLINE, style=ft.ButtonStyle(color=ft.colors.RED_300),
                    on_click=lambda e: self._delete(),
                ),
            )
        self.content = ft.Container(
            width=560,
            content=ft.Column([
                ft.Text("Editar mensagem" if message else "Nova mensagem agendada",
                        size=18, weight=ft.FontWeight.BOLD),
                self.number_field,
                self.text_field,
                ft.Row([self.date_field, self.time_field]),
                quick_hours,
                self.tag_dropdown,
            ], tight=True, spacing=14),
        )

    def _set_hour(self, h):
        self.time_field.value = h
        self.update()

    def _close(self):
        self.page_ref.close(self)

    def _parse_dt(self) -> str | None:
        try:
            dt = datetime.strptime(
                f"{self.date_field.value} {self.time_field.value}", "%Y-%m-%d %H:%M"
            )
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    def _save(self):
        dt = self._parse_dt()
        if not self.number_field.value or not self.text_field.value or not dt:
            self.page_ref.open(
                ft.SnackBar(ft.Text("Preencha número, mensagem e data/hora válidas."))
            )
            return
        tag_id = int(self.tag_dropdown.value) if self.tag_dropdown.value else None
        if self.message:
            db.update_message(self.message["id"], self.number_field.value,
                              self.text_field.value, dt, tag_id)
        else:
            db.create_message(self.number_field.value, self.text_field.value, dt, tag_id)
        self._close()
        self.on_done()

    def _delete(self):
        db.delete_message(self.message["id"])
        self._close()
        self.on_done()


class CalendarView(ft.Column):
    def __init__(self, page, on_change=None):
        super().__init__(expand=True, spacing=0)
        self.page_ref = page
        self.external_on_change = on_change or (lambda: None)
        today = date.today()
        self.year, self.month = today.year, today.month
        self.selected_day = today.day
        self.month_label = ft.Text(size=22, weight=ft.FontWeight.BOLD)

        prev_btn = ft.IconButton(ft.icons.CHEVRON_LEFT, on_click=lambda e: self._move(-1))
        next_btn = ft.IconButton(ft.icons.CHEVRON_RIGHT, on_click=lambda e: self._move(1))
        new_btn = ft.FilledButton(
            "Nova mensagem", icon=ft.icons.ADD, on_click=lambda e: self.open_dialog()
        )

        header = ft.Container(
            padding=ft.padding.only(left=20, right=20, top=12, bottom=12),
            content=ft.Row([
                prev_btn, self.month_label, next_btn,
                ft.VerticalDivider(width=10),
                new_btn,
                ft.Container(expand=True),
                self._legend(),
            ]),
        )

        self.grid_area = ft.Column(spacing=6, expand=True)
        self.detail_area = ft.Container(
            bgcolor=ft.colors.with_opacity(0.04, ft.colors.WHITE),
            border_radius=12, padding=16,
            width=340,
        )

        body = ft.Row(
            [ft.Container(content=self.grid_area, expand=True, padding=ft.padding.symmetric(horizontal=20)),
             self.detail_area],
            spacing=16, expand=True,
        )
        self.controls = [header, ft.Divider(height=1), body]
        self.reload()

    def _legend(self):
        items = [
            ft.Container(width=12, height=12, border_radius=6, bgcolor=c)
            for c in STATUS_COLORS.values()
        ]
        labels = list(STATUS_COLORS.keys())
        row = []
        for i, name in enumerate(labels):
            row.append(items[i])
            row.append(ft.Text(name, size=13))
        return ft.Row(row, spacing=6, wrap=True)

    def reload(self):
        self._build_grid()
        self._build_detail()
        if hasattr(self, "page") and self.page:
            try:
                self.update()
            except Exception:
                pass

    def _move(self, delta):
        m = self.month + delta
        if m < 1:
            self.year, self.month = self.year - 1, 12
        elif m > 12:
            self.year, self.month = self.year + 1, 1
        else:
            self.month = m
        self.reload()

    def _counts_by_day(self) -> dict:
        counts = {}
        for msg in db.list_messages():
            d = msg["scheduled_at"][:10]
            counts.setdefault(d, []).append(msg)
        return counts

    def _build_grid(self):
        self.month_label.value = f"{pycal.month_name[self.month].capitalize()} {self.year}"
        weeks = pycal.monthcalendar(self.year, self.month)
        days_header = ft.Row(
            [ft.Container(ft.Text(d, weight=ft.FontWeight.BOLD, size=13,
                                  color=ft.colors.with_opacity(0.6, ft.colors.WHITE)),
                          alignment=ft.alignment.center, expand=True)
             for d in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]],
            spacing=6,
        )
        rows = [days_header]
        by_day = self._counts_by_day()
        for week in weeks:
            cells = []
            for day in week:
                if day == 0:
                    cells.append(ft.Container(expand=True))
                    continue
                is_today = (date(self.year, self.month, day) == date.today())
                is_selected = (day == self.selected_day)
                key = f"{self.year:04d}-{self.month:02d}-{day:02d}"
                msgs = by_day.get(key, [])
                badges = ft.Row([
                    ft.Container(width=7, height=7, border_radius=3,
                                 bgcolor=STATUS_COLORS.get(m["status"], ft.colors.GREY))
                    for m in msgs[:8]
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)
                cell = ft.GestureDetector(
                    content=ft.Container(
                        bgcolor=(
                            ft.colors.GREEN_700 if is_selected
                            else ft.colors.with_opacity(0.35, ft.colors.BLUE_GREY_700)
                            if is_today else
                            ft.colors.with_opacity(0.05, ft.colors.WHITE)
                        ),
                        border_radius=10,
                        padding=6,
                        alignment=ft.alignment.center,
                        content=ft.Column([
                            ft.Text(str(day),
                                    weight=ft.FontWeight.BOLD if (is_today or is_selected) else None,
                                    color=ft.colors.WHITE if is_selected else None),
                            badges,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                    ),
                    on_tap=lambda e, d=day: self._select_day(d),
                    mouse_cursor=ft.MouseCursor.CLICK,
                )
                cells.append(ft.Container(content=cell, expand=True))
            rows.append(ft.Row(cells, spacing=6, vertical_alignment=ft.Stretch))
        rows.append(ft.Row([ft.Container(expand=True)]))
        self.grid_area.controls = rows

    def _select_day(self, day):
        self.selected_day = day
        self.reload()

    def _build_detail(self):
        key = f"{self.year:04d}-{self.month:02d}-{self.selected_day:02d}"
        msgs = sorted(db.list_messages(day=key), key=lambda m: m["scheduled_at"])
        header = ft.Row([
            ft.Text(f"{self.selected_day:02d}/{self.month:02d}",
                    size=17, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.IconButton(ft.icons.ADD_CIRCLE_OUTLINE, tooltip="Nova mensagem",
                          on_click=lambda e: self.open_dialog(default_day=key)),
        ])
        cards = [header]
        if not msgs:
            cards.append(ft.Container(
                padding=30,
                content=ft.Column([
                    ft.Icon(ft.icons.EVENT_NOTE_OUTLINED, size=40,
                            color=ft.colors.with_opacity(0.4, ft.colors.WHITE)),
                    ft.Text("Nenhuma mensagem neste dia",
                            color=ft.colors.with_opacity(0.5, ft.colors.WHITE)),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        for m in msgs:
            tag_chip = (
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    border_radius=8,
                    bgcolor=m["tag_color"],
                    content=ft.Text(m["tag_name"], size=11, color=ft.colors.BLACK),
                ) if m["tag_name"] else ft.Container()
            )
            card = ft.Container(
                margin=ft.margin.only(top=8),
                padding=12,
                border_radius=10,
                bgcolor=ft.colors.with_opacity(0.06, ft.colors.WHITE),
                ink=True,
                on_click=lambda e, msg=m: self.open_dialog(message=msg),
                content=ft.Column([
                    ft.Row([
                        ft.Text(m["scheduled_at"][11:16], weight=ft.FontWeight.BOLD,
                                size=16),
                        tag_chip,
                        ft.Container(expand=True),
                        ft.Container(
                            width=10, height=10, border_radius=5,
                            bgcolor=STATUS_COLORS.get(m["status"], ft.colors.GREY),
                        ),
                    ]),
                    ft.Text(m["text"], size=13, max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"→ {m['number']}", size=12,
                            color=ft.colors.with_opacity(0.55, ft.colors.WHITE)),
                ], spacing=4),
            )
            cards.append(card)
        self.detail_area.content = ft.ListView(cards, expand=True, spacing=0)

    def open_dialog(self, e=None, message=None, default_day=None):
        dlg = MessageDialog(
            self.page_ref, on_done=self._after_change,
            message=message, default_day=default_day,
        )
        self.page_ref.open(dlg)

    def _after_change(self):
        self.reload()
        self.external_on_change()
