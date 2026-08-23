"""Conexão do WhatsApp via QR Code (Evolution API)."""
import flet as ft

from powerzap import db
from powerzap.evolution import EvolutionAPI, EvolutionError


def get_api() -> EvolutionAPI:
    s = db.get_settings()
    return EvolutionAPI(s["evolution_url"], s["api_key"], s["instance"])


STATE_LABELS = {
    "open": ("Conectado", ft.colors.GREEN_400),
    "connecting": ("Conectando...", ft.colors.AMBER_400),
    "close": ("Desconectado", ft.colors.RED_400),
}


class ConnectView(ft.Column):
    def __init__(self, page):
        super().__init__(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=16,
        )
        self.page_ref = page
        self.qr_image = ft.Image(visible=False, width=280, height=280)
        self.status_row = ft.Row([], alignment=ft.MainAxisAlignment.CENTER)

        title = ft.Text("Conexão do WhatsApp", size=22, weight=ft.FontWeight.BOLD)
        subtitle = ft.Text(
            "Gere o QR Code e escaneie pelo WhatsApp "
            "(Aparelhos conectados > Conectar aparelho).",
            color=ft.colors.with_opacity(0.6, ft.colors.WHITE), text_align=ft.TextAlign.CENTER,
        )

        gen_btn = ft.FilledButton(
            "Gerar QR Code", icon=ft.icons.QR_CODE_2, on_click=self.generate_qr
        )
        check_btn = ft.OutlinedButton(
            "Verificar status", icon=ft.icons.SYNC, on_click=self.check_status
        )
        logout_btn = ft.OutlinedButton(
            "Desconectar", icon=ft.icons.LINK_OFF,
            style=ft.ButtonStyle(color=ft.colors.RED_300),
            on_click=self.logout,
        )

        self.controls = [
            ft.Container(height=20),
            title, subtitle,
            ft.Container(self.status_row, height=36),
            self.qr_image,
            ft.Row([gen_btn, check_btn, logout_btn],
                   alignment=ft.MainAxisAlignment.CENTER, wrap=True),
        ]
        self.reload()

    def reload(self):
        pass

    def _set_status(self):
        self.status_row.controls = [ft.ProgressRing(18, stroke_width=3)]
        try:
            self.update()
            api = get_api()
            state = api.connection_state()
            info = state.get("instance") or state
            raw = str(info.get("state", "desconhecido")).lower()
            label, color = STATE_LABELS.get(raw, (raw.capitalize(), ft.colors.GREY))
            self.status_row.controls = [
                ft.Icon(ft.icons.CIRCLE, size=12, color=color),
                ft.Text(f"Instância '{info.get('name', '')}': {label}", weight=ft.FontWeight.BOLD),
            ]
        except EvolutionError as ex:
            self.status_row.controls = [
                ft.Icon(ft.icons.ERROR_OUTLINE, color=ft.colors.RED_400),
                ft.Text(str(ex), size=13),
            ]
        except Exception as ex:
            self.status_row.controls = [
                ft.Icon(ft.icons.ERROR_OUTLINE, color=ft.colors.RED_400),
                ft.Text(f"Erro: {ex}", size=13),
            ]
        try:
            self.update()
        except AssertionError:
            pass

    def generate_qr(self, e=None):
        self.qr_image.visible = True
        self.qr_image.src = None
        self.status_row.controls = [ft.ProgressRing(20)]
        try:
            self.update()
        except AssertionError:
            pass
        try:
            api = get_api()
            try:
                qr = api.connect_qr()
            except EvolutionError:
                api.create_instance()
                qr = api.connect_qr()
            self.qr_image.src_base64 = qr.split(",", 1)[-1]
            self.status_row.controls = [
                ft.Icon(ft.icons.QR_CODE_SCANNER, color=ft.colors.GREEN_400),
                ft.Text("Escaneie o QR Code pelo WhatsApp"),
            ]
        except EvolutionError as ex:
            self.qr_image.visible = False
            self.status_row.controls = [
                ft.Icon(ft.icons.ERROR_OUTLINE, color=ft.colors.RED_400),
                ft.Text(str(ex), size=13),
            ]
        self.update()

    def check_status(self, e=None):
        import threading
        threading.Thread(target=self._set_status, daemon=True).start()

    def logout(self, e=None):
        try:
            get_api().logout()
            self.status_row.controls = [ft.Text("Instância desconectada.")]
        except EvolutionError as ex:
            self.status_row.controls = [ft.Text(str(ex), size=13)]
        self.update()
