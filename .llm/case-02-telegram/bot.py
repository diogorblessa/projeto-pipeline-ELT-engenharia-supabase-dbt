"""Bot Telegram — modo interativo (polling). Auto-registra CHAT_ID no .env da raiz."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agente import (
    ENV_PATH,
    Settings,
    chat,
    enviar_telegram,
    gerar_relatorio,
)

log = logging.getLogger(__name__)


# ── Persistência do CHAT_ID ──────────────────────────────────────────


_CHAT_ID_RE = re.compile(r"^CHAT_ID=.*$", re.MULTILINE)


def salvar_chat_id(chat_id: int, env_path: Path = ENV_PATH) -> None:
    """Atualiza ou anexa CHAT_ID=... no arquivo .env."""
    chat_id_str = str(chat_id)
    nova_linha = f"CHAT_ID={chat_id_str}"

    try:
        if env_path.exists():
            conteudo = env_path.read_text(encoding="utf-8")
        else:
            conteudo = ""

        if _CHAT_ID_RE.search(conteudo):
            atual = _CHAT_ID_RE.search(conteudo).group(0)
            if atual == nova_linha:
                return
            conteudo = _CHAT_ID_RE.sub(nova_linha, conteudo)
        else:
            if conteudo and not conteudo.endswith("\n"):
                conteudo += "\n"
            conteudo += nova_linha + "\n"

        env_path.write_text(conteudo, encoding="utf-8")
        log.info("CHAT_ID=%s salvo no .env", chat_id_str)
    except OSError as e:
        log.error("Falha ao escrever CHAT_ID no .env: %s", e)


# ── Handlers ─────────────────────────────────────────────────────────


async def _enviar_longo(update: Update, texto: str) -> None:
    for i in range(0, len(texto), 4096):
        parte = texto[i : i + 4096]
        try:
            await update.message.reply_text(parte, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(parte)


async def handler_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    salvar_chat_id(update.message.chat_id)
    await update.message.reply_text(
        "Olá! Sou o assistente de dados do e-commerce 📊\n\n"
        "Comandos disponíveis:\n"
        "/relatorio — gera o relatório executivo diário\n\n"
        "Ou faça qualquer pergunta sobre vendas, clientes ou pricing!"
    )


async def handler_relatorio(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    salvar_chat_id(update.message.chat_id)
    await update.message.reply_chat_action(ChatAction.TYPING)
    await update.message.reply_text("Gerando relatório... Aguarde um momento ⏳")
    settings: Settings = _.bot_data["settings"]
    try:
        texto = gerar_relatorio(settings)
        await _enviar_longo(update, texto)
    except Exception as e:
        log.exception("Erro ao gerar relatório")
        await update.message.reply_text(f"Erro ao gerar relatório: {e}")


async def handler_mensagem(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    salvar_chat_id(update.message.chat_id)
    await update.message.reply_chat_action(ChatAction.TYPING)
    settings: Settings = _.bot_data["settings"]
    try:
        resposta = chat(update.message.text, settings)
        await _enviar_longo(update, resposta)
    except Exception as e:
        log.exception("Erro ao processar pergunta")
        await update.message.reply_text(f"Erro ao processar pergunta: {e}")


# ── Entry point ──────────────────────────────────────────────────────


def main() -> None:
    settings = Settings()
    log.info("Iniciando bot Telegram...")

    app = ApplicationBuilder().token(settings.telegram.get_secret_value()).build()
    app.bot_data["settings"] = settings
    app.add_handler(CommandHandler("start", handler_start))
    app.add_handler(CommandHandler("relatorio", handler_relatorio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler_mensagem))

    log.info("Bot rodando! Ctrl+C para parar.")
    app.run_polling()


if __name__ == "__main__":
    main()


__all__ = ["enviar_telegram", "main", "salvar_chat_id"]
