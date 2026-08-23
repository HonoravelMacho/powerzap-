"""Configurações da integração com a Evolution API."""
import threading

import flet as ft

from powerzap import db
from powerzap.views.connect_view import get_api
from powerzap.evolution import EvolutionError


class SettingsView(ft.Column):
    def __init__(self, page):
        super().__init__(
            expand=True, spacing=14, scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.page_ref = page
        s = db.get_settings()

        title = ft.Text("Ajustes", size=22, weight=ft.FontWeight.BOLD)

        self.url_field = ft.TextField(
            label="URL da Evolution API", value=s["evolution_url"],
            prefix_icon=ft.icons.LINK, expand=True,
        )
        self.key_field = ft.TextField(
            label="API Key (apikey)", value=s["api_key"],
            prefix_icon=ft.icons.KEY, password=True, can_reveal_password=True, expand=True,
        )
        self.instance_field = ft.TextField(
            label="Nome da instância", value=s["instance"],
            prefix_icon=ft.icons.ACCOUNT_CIRCLE_OUTLINED, width=300,
        )
        self.test_result = ft.Container()

        save_btn = ft.FilledButton(
            "Salvar configurações", icon=ft.icons.SAVE, on_click=self.save
        )
        test_btn = ft.OutlinedButton(
            "Testar conexão", icon=ft.icons.NETWORK_CHECK, on_click=self.test
        )

        info = ft.Container(
            padding=16, border_radius=12,
            bgcolor=ft.colors.with_opacity(0.06, ft.colors.WHITE),
            content=ft.Column([
                ft.Text("Como conectar", weight=ft.FontWeight.BOLD),
                ft.Text(
                    "1. Rode a Evolution API localmente (padrão http://localhost:8080).\n"
                    "2. Informe aqui a API Key definida na sua instalação.\n"
                    "3. Vá em 'Conexão' e escaneie o QR Code.\n"
                    "4. Agende mensagens no Calendário.",
                    size=13, color=ft.colors.with_opacity(0.7, ft.colors.WHITE),
                ),
            ], tight=True),
            width=520,
        )

        self.controls = [
            ft.Container(height=10), title,
            ft.Container(width=520, content=self.url_field),
            ft.Container(width=520, content=self.key_field),
            self.instance_field,
            ft.Row([save_btn, test_btn], alignment=ft.MainAxisAlignment.CENTER),
            self.test_result,
            info,
        ]

    def reload(self):
        pass

    def save(self, e=None):
        url = (self.url_field.value or "").strip()
        key = (self.key_field.value or "").strip()
        inst = (self.instance_field.value or "").strip() or "powerzap"
        db.set_setting("evolution_url", url)
        db.set_setting("api_key", key)
        db.set_setting("instance", inst)
        self.page_ref.open(ft.SnackBar(ft.Text("Configurações salvas!")))

    def test(self, e=None):
        self.save()
        self.test_result.content = ft.Row([
            ft.ProgressRing(16, stroke_width=3),
            ft.Text("Testando conexão..."),
        ])
        self.update()
        threading.Thread(target=self._test_async, daemon=True).start()

    def _test_async(self):
        try:
            api = get_api()
            api.connection_state()
            msg, color, icon = "Evolution API respondeu com sucesso!", ft.colors.GREEN_400, ft.icons.CHECK_CIRCLE
        except EvolutionError as ex:
            msg, color, icon = str(ex), ft.colors.RED_400, ft.icons.ERROR_OUTLINE
        except Exception as ex:
            msg, color, icon = f"Erro: {ex}", ft.colors.RED_400, ft.icons.ERROR_OUTLINE
        self.test_result.content = ft.Row([
            ft.Icon(icon, color=color), ft.Expanded(ft.Text(msg, size=13)),
        ])
        try:
            self.update()
        except AssertionError:
            pass
