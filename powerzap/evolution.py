"""Cliente HTTP para a Evolution API."""
import base64

import requests


class EvolutionError(Exception):
    pass


class EvolutionAPI:
    def __init__(self, url: str, api_key: str, instance: str, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.instance = instance
        self.timeout = timeout

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["apikey"] = self.api_key
        return h

    def _request(self, method: str, path: str, json_body=None,
                 timeout: float | None = None):
        url = f"{self.url}{path}"
        try:
            resp = requests.request(
                method, url, headers=self._headers(), json=json_body,
                timeout=self.timeout if timeout is None else timeout,
            )
        except requests.RequestException as e:
            raise EvolutionError(f"Falha de conexão com a Evolution API: {e}") from e
        if resp.status_code >= 400:
            raise EvolutionError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    # ---- Instância / Conexão ----

    def create_instance(self) -> dict:
        """Cria a instância já solicitando QR Code."""
        return self._request(
            "POST", "/instance/create",
            {
                "instanceName": self.instance,
                "integration": "WHATSAPP-BAILEYS",
                "qrcode": True,
            },
        )

    def connect_qr(self) -> str:
        """Retorna o QR Code em data-URI base64 para pareamento."""
        data = self._request("GET", f"/instance/connect/{self.instance}", timeout=60)
        b64 = data.get("base64") or ""
        if not b64:
            raise EvolutionError("Resposta sem QR Code. A instância pode já estar conectada.")
        if not b64.startswith("data:"):
            b64 = "data:image/png;base64," + b64
        return b64

    def connection_state(self) -> dict:
        return self._request("GET", f"/instance/connectionState/{self.instance}")

    def is_connected(self) -> bool:
        try:
            state = self.connection_state()
        except EvolutionError:
            return False
        info = state.get("instance") or state
        return str(info.get("state", "")).lower() == "open"

    def logout(self) -> dict:
        return self._request("DELETE", f"/instance/logout/{self.instance}")

    # ---- Envio ----

    def send_text(self, number: str, text: str) -> dict:
        number = "".join(ch for ch in number if ch.isdigit() or ch == "+")
        return self._request(
            "POST", f"/message/sendText/{self.instance}",
            {"number": number, "text": text},
        )

    # ---- Contatos ----

    def find_contacts(self) -> list:
        """Lista os contatos sincronizados da instância."""
        data = self._request("POST", f"/chat/findContacts/{self.instance}",
                             {}, timeout=120)
        rows = data.get("contacts") if isinstance(data, dict) else (data or [])
        out = []
        for r in rows:
            jid = r.get("remoteJid") or ""
            if not jid or "@" not in jid:
                continue
            is_group = jid.endswith("@g.us")
            name = (r.get("pushName") or r.get("name") or "").strip()
            out.append({
                "number": jid if is_group else jid.split("@")[0],
                "name": name,
                "is_group": is_group,
            })
        return out
