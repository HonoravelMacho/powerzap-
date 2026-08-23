# PowerZap

Agendador de mensagens WhatsApp com interface moderna (Flet), integrado à Evolution API local.

## Funcionalidades
- Calendário interativo em tela cheia (Dark Mode)
- CRUD de mensagens agendadas
- Etiquetas coloridas (CRUD)
- Integração com Evolution API (`http://localhost:8080`)
- Persistência local via SQLite

## Desenvolvimento
```bash
pip install -r requirements.txt
python -m powerzap
```

## Instalação (Pop!_OS / Ubuntu)
Baixe o `.deb` na aba Releases e:
```bash
sudo apt install ./powerzap_*_amd64.deb
```
Depois execute `powerzap` no terminal ou use o menu de aplicativos.
