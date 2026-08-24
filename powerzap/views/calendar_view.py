"""Calendário interativo em tela cheia com CRUD de mensagens."""
import calendar as pycal
import threading
from datetime import date, datetime, timedelta

import flet as ft

from powerzap import db
from powerzap.views.connect_view import get_api

STATUS_COLORS = {
    "pendente": ft.colors.AMBER_400,
    "enviada": ft.colors.GREEN_400,
    "falhou": ft.colors.RED_400,
}

PRESET_HOURS = ["08:00", "09:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]

WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


class MessageDialog(ft.AlertDialog):
    """Diálogo único com dois painéis: formulário e lista de contatos."""

    def __init__(self, page, on_done, message=None, default_day=None):
        super().__init__(modal=True)
        self.page_ref = page
        self.on_done = on_done
        self.message = message
        self.picker_contacts = []

        # ---------- Formulário ----------
        self.number_field = ft.TextField(
            label="Número do WhatsApp",
            hint_text="5511999999999",
            width=280,
        )
        pick_contact_btn = ft.IconButton(
            icon=ft.icons.CONTACTS,
            tooltip="Selecionar contato da lista",
            icon_color=ft.colors.GREEN_400,
            on_click=lambda e: self._show_picker(),
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

        self.form_area = ft.Column([
            ft.Row([self.number_field, pick_contact_btn], spacing=6),
            self.text_field,
            ft.Row([self.date_field, self.time_field]),
            quick_hours,
            self.tag_dropdown,
        ], tight=True, spacing=14, visible=True)

        # ---------- Seletor de contatos (mesmo diálogo, sem empilhar) ----------
        self.search_field = ft.TextField(
            label="Buscar por nome ou número...",
            prefix_icon=ft.icons.SEARCH,
            on_change=lambda e: self._filter(),
            border_radius=10,
        )
        self.picker_status = ft.Text("", size=12,
                                     color=ft.colors.with_opacity(0.6, ft.colors.WHITE))
        self.contact_list = ft.ListView(height=420, spacing=4)

        back_btn = ft.IconButton(
            icon=ft.icons.ARROW_BACK,
            tooltip="Voltar ao formulário",
            on_click=lambda e: self._show_form(),
        )
        sync_btn = ft.IconButton(
            icon=ft.icons.SYNC, tooltip="Atualizar da API",
            on_click=lambda e: threading.Thread(
                target=self._sync_from_api, daemon=True
            ).start(),
        )

        self.picker_area = ft.Column([
            ft.Row([
                back_btn,
                ft.Text("Selecionar contato", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                sync_btn,
            ]),
            self.search_field,
            self.contact_list,
            self.picker_status,
        ], tight=False, spacing=10, visible=False)

        # ---------- Ações ----------
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
                self.form_area,
                self.picker_area,
            ], tight=True, spacing=14),
        )

    # ----- navegação entre painéis do diálogo -----

    def _show_picker(self):
        self.picker_area.visible = True
        self.form_area.visible = False
        for a in self.actions:          # esconde todos os botões na listagem
            a.visible = False
        self._load_contacts()
        try:
            self.update()
        except Exception:
            pass
        if db.count_contacts() == 0:
            self._set_status("Sincronizando contatos da Evolution API...")
        threading.Thread(target=self._sync_from_api, daemon=True).start()

    def _show_form(self):
        self.picker_area.visible = False
        self.form_area.visible = True
        for a in self.actions:
            a.visible = True
        try:
            self.update()
        except Exception:
            pass

    # ----- contatos -----

    def _load_contacts(self):
        self.picker_contacts = db.list_contacts()
        self._render_list()
        self._set_status(f"{len(self.picker_contacts)} contato(s) em cache.")

    def _set_status(self, msg: str):
        self.picker_status.value = msg
        try:
            self.picker_status.update()
        except Exception:
            pass

    def _sync_from_api(self):
        try:
            fresh = get_api().find_contacts()
            db.replace_contacts(fresh)
            self.picker_contacts = db.list_contacts()
            query = (self.search_field.value or "").strip()
            if query:
                self.picker_contacts = db.filter_local(self.picker_contacts, query)
            self._render_list()
            self._set_status(f"{len(fresh)} contato(s) sincronizados da API.")
        except Exception as ex:
            self._set_status(f"Sem conexão com a API — usando cache ({ex.__class__.__name__}).")

    def _filter(self):
        query = (self.search_field.value or "").strip().lower()
        if not query:
            self.picker_contacts = db.list_contacts()
        else:
            self.picker_contacts = db.filter_local(db.list_contacts(), query)
        self._render_list()

    def _render_list(self):
        rows = []
        for ct in self.picker_contacts[:300]:
            name = ct["name"] or "(sem nome)"
            icon = ft.icons.GROUPS if ct["is_group"] else ft.icons.PERSON_OUTLINE
            rows.append(
                ft.ListTile(
                    leading=ft.Icon(icon, color=ft.colors.GREEN_300),
                    title=ft.Text(name, weight=ft.FontWeight.W_600),
                    subtitle=ft.Text(ct["number"], size=12,
                                     color=ft.colors.with_opacity(0.55, ft.colors.WHITE)),
                    dense=True,
                    on_click=lambda e, c=dict(ct): self._pick(c),
                )
            )
        if not rows:
            rows.append(ft.Container(
                padding=30,
                content=ft.Column([
                    ft.Icon(ft.icons.PHONE_DISABLED_OUTLINED, size=36,
                            color=ft.colors.with_opacity(0.35, ft.colors.WHITE)),
                    ft.Text(
                        "Nenhum contato encontrado.\n"
                        "Conecte o WhatsApp na aba 'Conexão' e envie/receba\n"
                        "mensagens para que os contatos sejam sincronizados.",
                        size=12, text_align=ft.TextAlign.CENTER,
                        color=ft.colors.with_opacity(0.55, ft.colors.WHITE),
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        self.contact_list.controls = rows
        try:
            self.contact_list.update()
        except Exception:
            pass

    def _pick(self, contact: dict):
        self.number_field.value = contact["number"]
        self._show_form()
        try:
            self.text_field.focus()
        except Exception:
            pass

    # ----- formulário -----

    def _set_hour(self, h):
        self.time_field.value = h
        try:
            self.update()
        except Exception:
            pass

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
        self.selected_date: date = today
        self.month_label = ft.Text(size=22, weight=ft.FontWeight.BOLD, width=190,
                                   text_align=ft.TextAlign.CENTER)

        prev_btn = ft.IconButton(ft.icons.CHEVRON_LEFT, tooltip="Mês anterior",
                                 on_click=lambda e: self._move(-1))
        next_btn = ft.IconButton(ft.icons.CHEVRON_RIGHT, tooltip="Próximo mês",
                                 on_click=lambda e: self._move(1))
        today_btn = ft.OutlinedButton("Hoje", icon=ft.icons.EVENT_AVAILABLE,
                                      on_click=lambda e: self._go_today())
        new_btn = ft.FilledButton(
            "Nova mensagem", icon=ft.icons.ADD, on_click=lambda e: self.open_dialog()
        )

        header = ft.Container(
            padding=ft.padding.only(left=20, right=20, top=12, bottom=12),
            content=ft.Row([
                prev_btn,
                self.month_label,
                next_btn,
                today_btn,
                ft.VerticalDivider(width=10),
                new_btn,
                ft.Container(expand=True),
                self._legend(),
            ]),
        )

        self.grid_area = ft.Column(spacing=8, expand=True)
        self.detail_area = ft.Container(
            bgcolor=ft.colors.with_opacity(0.04, ft.colors.WHITE),
            border_radius=12, padding=16,
            width=340,
        )

        body = ft.Row(
            [ft.Container(content=self.grid_area, expand=True,
                          padding=ft.padding.only(left=20, bottom=16)),
             self.detail_area],
            spacing=16, expand=True,
        )
        self.controls = [header, ft.Divider(height=1), body]
        self.reload()

    # ---------------- cabeçalho ----------------

    def _legend(self):
        row = []
        for name, color in STATUS_COLORS.items():
            row.append(ft.Container(width=12, height=12, border_radius=6, bgcolor=color))
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
        if self.selected_date.month != self.month or self.selected_date.year != self.year:
            self.selected_date = date(self.year, self.month, 1)
        self.reload()

    def _go_today(self):
        t = date.today()
        self.year, self.month = t.year, t.month
        self.selected_date = t
        self.reload()

    # ---------------- grade ----------------

    def _counts_by_day(self) -> dict:
        counts = {}
        for msg in db.list_messages():
            d = msg["scheduled_at"][:10]
            counts.setdefault(d, []).append(msg)
        return counts

    def _month_matrix(self) -> list[list[date]]:
        """Matriz 6x7 sempre completa, começando na segunda-feira."""
        first = date(self.year, self.month, 1)
        start = first - timedelta(days=first.weekday())
        return [
            [start + timedelta(days=w * 7 + d) for d in range(7)]
            for w in range(6)
        ]

    def _build_cell(self, d: date, msgs: list) -> ft.Control:
        in_month = d.month == self.month
        is_today = d == date.today()
        is_selected = d == self.selected_date

        if is_selected:
            bg, fg, day_weight = ft.colors.GREEN_700, ft.colors.WHITE, ft.FontWeight.BOLD
        elif is_today:
            bg, fg, day_weight = (
                ft.colors.with_opacity(0.35, ft.colors.BLUE_GREY_700),
                ft.colors.WHITE, ft.FontWeight.BOLD,
            )
        else:
            bg, fg, day_weight = (
                ft.colors.with_opacity(0.05, ft.colors.WHITE), None, None
            )

        badges = ft.Row([
            ft.Container(width=7, height=7, border_radius=3,
                         bgcolor=STATUS_COLORS.get(m["status"], ft.colors.GREY))
            for m in msgs[:9]
        ], spacing=3, alignment=ft.MainAxisAlignment.CENTER)

        cell = ft.Container(
            bgcolor=bg,
            border_radius=12,
            border=ft.border.all(1, ft.colors.with_opacity(0.08, ft.colors.WHITE)),
            ink=True,
            on_click=lambda e, dd=d: self._select_day(dd),
            on_hover=self._hover_cell,
            data={"base": bg, "ativa": in_month},
            padding=8,
            alignment=ft.alignment.center,
            content=ft.Column([
                ft.Text(str(d.day), color=fg, weight=day_weight, size=15),
                badges,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               alignment=ft.MainAxisAlignment.CENTER, tight=True),
        )
        if not in_month:
            cell.opacity = 0.28
        cell.tooltip = d.strftime("%d/%m/%Y")
        return cell

    @staticmethod
    def _hover_cell(e: ft.ControlEvent):
        c: ft.Container = e.control
        info = c.data or {}
        if not info.get("ativa"):
            return
        if e.data == "true" and c.bgcolor != ft.colors.GREEN_700:
            c.bgcolor = ft.colors.with_opacity(0.12, ft.colors.WHITE)
        elif e.data != "true":
            c.bgcolor = info.get("base")
        try:
            c.update()
        except Exception:
            pass

    def _build_grid(self):
        self.month_label.value = f"{pycal.month_name[self.month].capitalize()} {self.year}"
        days_header = ft.Row([
            ft.Container(ft.Text(d, weight=ft.FontWeight.BOLD, size=13,
                                 color=ft.colors.with_opacity(0.6, ft.colors.WHITE)),
                         alignment=ft.alignment.center, expand=True)
            for d in WEEKDAYS
        ], spacing=8)

        by_day = self._counts_by_day()
        weeks = self._month_matrix()
        rows = [days_header]
        for week in weeks:
            cells = []
            for d in week:
                key = d.isoformat()
                cells.append(ft.Container(
                    content=self._build_cell(d, by_day.get(key, [])),
                    expand=True,
                ))
            rows.append(ft.Row(cells, spacing=8, expand=True))
        self.grid_area.controls = rows

    def _select_day(self, d: date):
        if d.month != self.month or d.year != self.year:
            self.year, self.month = d.year, d.month
        self.selected_date = d
        self.reload()

    # ---------------- painel lateral ----------------

    def _build_detail(self):
        key = self.selected_date.isoformat()
        msgs = sorted(db.list_messages(day=key), key=lambda m: m["scheduled_at"])
        header = ft.Row([
            ft.Text(self.selected_date.strftime("%d/%m"), size=17,
                    weight=ft.FontWeight.BOLD),
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
