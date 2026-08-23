"""Serviço de envio em background do PowerZap."""
import argparse
import logging
import sys
import time

from powerzap import db
from powerzap.evolution import EvolutionAPI, EvolutionError

log = logging.getLogger("powerzap.scheduler")


def process_due_messages(api: EvolutionAPI) -> int:
    now = db._now()
    due = db.list_pending(now)
    sent = 0
    for msg in due:
        try:
            api.send_text(msg["number"], msg["text"])
            db.mark_sent(msg["id"])
            log.info("Mensagem %s enviada para %s", msg["id"], msg["number"])
            sent += 1
        except EvolutionError as ex:
            db.mark_failed(msg["id"], str(ex))
            log.error("Falha ao enviar mensagem %s: %s", msg["id"], ex)
    return sent


def run(interval: float):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log.info("PowerZap scheduler iniciado (intervalo %.0fs)", interval)
    while True:
        try:
            settings = db.get_settings()
            if not settings["api_key"]:
                log.warning("API Key não configurada. Abra o PowerZap e configure em Ajustes.")
            else:
                api = EvolutionAPI(
                    settings["evolution_url"], settings["api_key"], settings["instance"]
                )
                n = process_due_messages(api)
                if n:
                    log.info("%d mensagem(ns) processada(s)", n)
        except Exception as e:
            log.exception("Erro no ciclo do scheduler: %s", e)
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PowerZap - serviço de envio")
    parser.add_argument("--interval", type=float, default=20.0,
                        help="intervalo entre ciclos em segundos")
    args = parser.parse_args()
    try:
        run(args.interval)
    except KeyboardInterrupt:
        sys.exit(0)
