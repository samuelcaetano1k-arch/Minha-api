import os
import urllib.parse
import httpx

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

# =========================================================
# CONFIGURAÇÃO
# =========================================================

TELEGRAM_TOKEN = "8690089353:AAEC5pTCg5FDVev2DWqRdDjnWGluEgHvGms"

API_BASE = os.getenv(
    "ROOM_API_URL",
    "https://ff-custom-room-api-1.onrender.com"
).rstrip("/")

# Guarda dados temporários por usuário
usuarios = {}

# Guarda a última sala criada por usuário
salas_ativas = {}


# =========================================================
# TECLADO PRINCIPAL
# =========================================================

def painel():
    keyboard = [
        [
            InlineKeyboardButton("🎮 Criar Sala", callback_data="criar")
        ],
        [
            InlineKeyboardButton("👥 Listar Jogadores", callback_data="listar")
        ],
        [
            InlineKeyboardButton("▶️ Iniciar Sala", callback_data="iniciar")
        ],
        [
            InlineKeyboardButton("🔒 Fechar Sala", callback_data="fechar")
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# /start
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
        "🎮 **PAINEL DE SALAS**\n\n"
        "Escolha uma opção abaixo:"
    )

    await update.message.reply_text(
        texto,
        parse_mode="Markdown",
        reply_markup=painel()
    )


# =========================================================
# ESCOLHER MODO
# =========================================================

async def mostrar_modos(query):

    keyboard = [
        [
            InlineKeyboardButton("🔫 1v1", callback_data="modo_1v1")
        ],
        [
            InlineKeyboardButton("🔥 4v4", callback_data="modo_4v4")
        ],
        [
            InlineKeyboardButton("⚡ 6v6", callback_data="modo_6v6")
        ],
        [
            InlineKeyboardButton("👊 4v4 Soco", callback_data="modo_soco")
        ],
        [
            InlineKeyboardButton("🏆 4v4 eSports", callback_data="modo_esports")
        ],
        [
            InlineKeyboardButton("⬅️ Voltar", callback_data="voltar")
        ],
    ]

    await query.edit_message_text(
        "🎮 **ESCOLHA O MODO**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# ESCOLHER RODADAS
# =========================================================

async def mostrar_rodadas(query, user_id):

    dados = usuarios.setdefault(user_id, {})

    if dados.get("tipo") in ["soco", "esports"]:
        dados["rodadas"] = 13
        dados["configuracao"] = (
            "fist_fight"
            if dados["tipo"] == "soco"
            else "tactical"
        )

        await pedir_nome(query, user_id)
        return

    keyboard = [
        [
            InlineKeyboardButton("7️⃣ 7 Rodadas", callback_data="rodadas_7")
        ],
        [
            InlineKeyboardButton("1️⃣3️⃣ 13 Rodadas", callback_data="rodadas_13")
        ],
        [
            InlineKeyboardButton("⬅️ Voltar", callback_data="criar")
        ],
    ]

    await query.edit_message_text(
        "🔄 **QUANTIDADE DE RODADAS**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# ESCOLHER GELO
# =========================================================

async def mostrar_gelo(query):

    keyboard = [
        [
            InlineKeyboardButton(
                "🧊 Gelo Limitado",
                callback_data="gelo_limited"
            )
        ],
        [
            InlineKeyboardButton(
                "♾️ Gelo Infinito",
                callback_data="gelo_unlimited"
            )
        ],
        [
            InlineKeyboardButton("⬅️ Voltar", callback_data="criar")
        ],
    ]

    await query.edit_message_text(
        "🧊 **ESCOLHA O TIPO DE GELO**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# PEDIR NOME
# =========================================================

async def pedir_nome(query, user_id):

    usuarios[user_id]["esperando"] = "nome"

    await query.edit_message_text(
        "📝 **Digite o nome da sala:**",
        parse_mode="Markdown"
    )


# =========================================================
# PEDIR SENHA
# =========================================================

async def pedir_senha(message, user_id):

    usuarios[user_id]["esperando"] = "senha"

    await message.reply_text(
        "🔐 **Digite a senha da sala:**",
        parse_mode="Markdown"
    )


# =========================================================
# CRIAR SALA NA API
# =========================================================
async def criar_sala_api(user_id, message):

    dados = usuarios[user_id]

    nome = dados["nome"]
    senha = dados["senha"]

    nome_url = urllib.parse.quote(nome, safe="")
    senha_url = urllib.parse.quote(senha, safe="")

    endpoint = (
        f"/create_room/4v4/7/limited_ammo/"
        f"{nome_url}/{senha_url}"
    )

    url = API_BASE + endpoint

    print("URL ENVIADA PELO BOT:", url)

    await message.reply_text(
        "⏳ **CRIANDO SALA 4V4...**",
        parse_mode="Markdown"
    )

    try:

        async with httpx.AsyncClient(timeout=60) as client:
            resposta = await client.get(url)

        texto = resposta.text

        if resposta.status_code >= 400:
            await message.reply_text(
                "❌ **ERRO AO CRIAR SALA**\n\n"
                f"HTTP: `{resposta.status_code}`\n"
                f"Resposta: `{texto[:1500]}`",
                parse_mode="Markdown"
            )
            return

        try:
            resultado = resposta.json()
        except Exception:
            resultado = None

        if not isinstance(resultado, dict):
            await message.reply_text(
                "❌ **A API não retornou JSON válido.**\n\n"
                f"📡 Resposta:\n`{texto[:1500]}`",
                parse_mode="Markdown"
            )
            return

        room_id = resultado.get("room_id")

        if not room_id:
            await message.reply_text(
                "❌ **A API não criou a sala.**\n\n"
                f"📡 Resposta da API:\n`{texto[:1500]}`",
                parse_mode="Markdown"
            )
            return

        room_password = resultado.get("password", senha)
        host_uid = resultado.get("host_uid", "Não informado")
        room_name = resultado.get("room_name", nome)

        salas_ativas[user_id] = {
            "id": room_id,
            "nome": room_name,
            "senha": room_password,
            "modo": "4v4",
            "rodadas": 7
        }

        await message.reply_text(
            "🎉 **SALA CRIADA COM SUCESSO!**\n\n"
            f"📝 Nome: `{room_name}`\n"
            "🎮 Modo: `4v4`\n"
            "🔄 Rodadas: `7`\n"
            "🧊 Gelo: `Limitado`\n"
            f"🆔 ID: `{room_id}`\n"
            f"🔑 Senha: `{room_password}`\n"
            f"👤 Host UID: `{host_uid}`",
            parse_mode="Markdown"
        )

    except Exception as erro:

        await message.reply_text(
            "❌ **ERRO AO CONECTAR À API**\n\n"
            f"`{erro}`",
            parse_mode="Markdown"
        )




# =========================================================
# BOTÕES
# =========================================================

async def botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # -----------------------------------------------------
    # VOLTAR
    # -----------------------------------------------------

    if data == "voltar":

        await query.edit_message_text(
            "🎮 **PAINEL DE SALAS**",
            parse_mode="Markdown",
            reply_markup=painel()
        )

        return

    # -----------------------------------------------------
    # CRIAR
    # -----------------------------------------------------

    if data == "criar":

        usuarios[user_id] = {}

        await mostrar_modos(query)

        return

    # -----------------------------------------------------
    # MODO
    # -----------------------------------------------------

    if data.startswith("modo_"):

        modo = data.replace("modo_", "")

        dados = usuarios.setdefault(user_id, {})

        if modo == "soco":

            dados["tipo"] = "soco"
            dados["modo"] = "4v4"

        elif modo == "esports":

            dados["tipo"] = "esports"
            dados["modo"] = "4v4"

        else:

            dados["tipo"] = "normal"
            dados["modo"] = modo

        await mostrar_rodadas(query, user_id)

        return

    # -----------------------------------------------------
    # RODADAS
    # -----------------------------------------------------

    if data.startswith("rodadas_"):

        rodadas = int(data.replace("rodadas_", ""))

        usuarios[user_id]["rodadas"] = rodadas

        await mostrar_gelo(query)

        return

    # -----------------------------------------------------
    # GELO
    # -----------------------------------------------------

    if data == "gelo_limited":

        usuarios[user_id]["configuracao"] = "limited_ammo"

        await pedir_nome(query, user_id)

        return

    if data == "gelo_unlimited":

        usuarios[user_id]["configuracao"] = "unlimited_ammo"

        await pedir_nome(query, user_id)

        return

    # -----------------------------------------------------
    # LISTAR
    # -----------------------------------------------------

    if data == "listar":

        sala = salas_ativas.get(user_id)

        if not sala or not sala.get("id"):

            await query.message.reply_text(
                "❌ Nenhuma sala criada recentemente."
            )

            return

        room_id = sala["id"]

        try:

            async with httpx.AsyncClient(timeout=30) as client:

                resposta = await client.get(
                    f"{API_BASE}/list/{room_id}"
                )

            await query.message.reply_text(
                "👥 **JOGADORES DA SALA**\n\n"
                f"{resposta.text[:3000]}",
                parse_mode="Markdown"
            )

        except Exception as erro:

            await query.message.reply_text(
                f"❌ Erro: `{erro}`",
                parse_mode="Markdown"
            )

        return

    # -----------------------------------------------------
    # INICIAR
    # -----------------------------------------------------

    if data == "iniciar":

        try:

            async with httpx.AsyncClient(timeout=30) as client:

                resposta = await client.get(
                    f"{API_BASE}/start"
                )

            await query.message.reply_text(
                "▶️ **COMANDO DE INÍCIO ENVIADO**\n\n"
                f"Resposta: `{resposta.text[:1500]}`",
                parse_mode="Markdown"
            )

        except Exception as erro:

            await query.message.reply_text(
                f"❌ Erro: `{erro}`",
                parse_mode="Markdown"
            )

        return

    # -----------------------------------------------------
    # FECHAR
    # -----------------------------------------------------

    if data == "fechar":

        sala = salas_ativas.get(user_id)

        if not sala or not sala.get("id"):

            await query.message.reply_text(
                "❌ Nenhuma sala encontrada."
            )

            return

        room_id = sala["id"]

        try:

            async with httpx.AsyncClient(timeout=30) as client:

                resposta = await client.get(
                    f"{API_BASE}/disband/{room_id}"
                )

            await query.message.reply_text(
                "🔒 **SALA FECHADA**\n\n"
                f"Resposta: `{resposta.text[:1500]}`",
                parse_mode="Markdown",
                reply_markup=painel()
            )

            salas_ativas.pop(user_id, None)

        except Exception as erro:

            await query.message.reply_text(
                f"❌ Erro: `{erro}`",
                parse_mode="Markdown"
            )

        return


# =========================================================
# MENSAGENS DE TEXTO
# =========================================================

async def mensagens(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.effective_user.id

    if user_id not in usuarios:
        return

    dados = usuarios[user_id]

    esperando = dados.get("esperando")

    # -----------------------------------------------------
    # NOME
    # -----------------------------------------------------

    if esperando == "nome":

        dados["nome"] = update.message.text.strip()
        dados["esperando"] = None

        await pedir_senha(update.message, user_id)

        return

    # -----------------------------------------------------
    # SENHA
    # -----------------------------------------------------

    if esperando == "senha":

        dados["senha"] = update.message.text.strip()
        dados["esperando"] = None

        await criar_sala_api(
            user_id,
            update.message
        )

        return


# =========================================================
# MAIN
# =========================================================

def main():

    if not TELEGRAM_TOKEN:

        raise RuntimeError(
            "TELEGRAM_TOKEN não configurado."
        )

    print("🤖 Bot Telegram iniciado!")
    print(f"🌐 API: {API_BASE}")

    app = Application.builder().token(
        TELEGRAM_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(botoes)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            mensagens
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
