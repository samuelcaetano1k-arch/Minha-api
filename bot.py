import os
from urllib.parse import quote

import discord
import httpx

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# CONFIGURAÇÃO
# =========================================================
import os

TOKEN = os.getenv("DISCORD_TOKEN")

API_BASE = os.getenv(
    "ROOM_API_URL",
    "https://ff-custom-room-api-1.onrender.com"
).rstrip("/")

# Guarda a última sala criada em cada canal
salas_ativas = {}


# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# EVENTO BOT ONLINE
# =========================================================

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")
    print(f"API: {API_BASE}")


# =========================================================
# TESTE
# =========================================================

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")


# =========================================================
# CRIAR SALA
#
# !sala
# !sala 4v4
# !sala 4v4 13
# !sala 4v4 13 1234
# !sala 4v4 13 1234 Minha Sala
# =========================================================

@bot.command()
async def sala(ctx, modo: str = "4v4", rodadas: int = 7,
               senha: str = "1234", *, nome: str = "Sala Free Fire"):

    # -----------------------------------------------------
    # Verifica rodadas
    # -----------------------------------------------------

    if rodadas < 1:
        await ctx.send("❌ A quantidade de rodadas precisa ser maior que 0.")
        return

    # -----------------------------------------------------
    # Converte modo
    # -----------------------------------------------------

    modos = {
        "1v1": 1,
        "2v2": 2,
        "3v3": 3,
        "4v4": 4,
        "5v5": 5,
    }

    modo_numero = modos.get(modo.lower())

    if modo_numero is None:

        # Também permite mandar diretamente um número
        try:
            modo_numero = int(modo)
        except ValueError:
            await ctx.send(
                "❌ Modo inválido.\n"
                "Use, por exemplo: `!sala 4v4 13`"
            )
            return

    # -----------------------------------------------------
    # Mensagem aguardando
    # -----------------------------------------------------

    mensagem = await ctx.send(
        "⏳ **CRIANDO SALA...**\n"
        f"🎮 Modo: `{modo}`\n"
        f"🔄 Rodadas: `{rodadas}`"
    )

    # -----------------------------------------------------
    # Dados enviados para a API
    # -----------------------------------------------------

    dados = {
        "room_name": nome,
        "password": senha,
        "mode": modo_numero,
        "rounds": rodadas,
        "map_name": "Bermuda",
        "configuration": "padrão",
        "start_delay_minutes": 0
    }

    # -----------------------------------------------------
    # Chamada da API
    # -----------------------------------------------------

    try:

        async with httpx.AsyncClient(timeout=30) as client:

            resposta = await client.post(
                f"{API_BASE}/rooms",
                json=dados
            )

        # -------------------------------------------------
        # Erro HTTP
        # -------------------------------------------------

        if resposta.status_code != 200:

            try:
                erro = resposta.json()
            except Exception:
                erro = resposta.text

            await mensagem.edit(
                content=(
                    "❌ **ERRO AO CRIAR SALA**\n\n"
                    f"Status: `{resposta.status_code}`\n"
                    f"Resposta: `{erro}`"
                )
            )
            return

        resultado = resposta.json()

    except httpx.RequestError as erro:

        await mensagem.edit(
            content=(
                "❌ **NÃO FOI POSSÍVEL CONECTAR À API**\n\n"
                f"`{erro}`"
            )
        )
        return

    except Exception as erro:

        await mensagem.edit(
            content=(
                "❌ **ERRO**\n\n"
                f"`{erro}`"
            )
        )
        return

    # -----------------------------------------------------
    # Dados retornados
    # -----------------------------------------------------

    room_id = resultado.get("external_room_id")

    # Se não existir ID externo, usa o ID interno
    if not room_id:
        room_id = resultado.get("id", "Não informado")

    room_password = resultado.get(
        "password",
        senha
    )

    # -----------------------------------------------------
    # Guarda sala no canal
    # -----------------------------------------------------

    salas_ativas[ctx.channel.id] = resultado

    # -----------------------------------------------------
    # Embed
    # -----------------------------------------------------

    embed = discord.Embed(
        title="🎮 SALA CRIADA!",
        description="Sua sala foi criada com sucesso.",
        color=discord.Color.green()
    )

    embed.add_field(
        name="🆔 ID da Sala",
        value=f"`{room_id}`",
        inline=False
    )

    embed.add_field(
        name="🔑 Senha",
        value=f"`{room_password}`",
        inline=True
    )

    embed.add_field(
        name="🎮 Modo",
        value=f"`{modo}`",
        inline=True
    )

    embed.add_field(
        name="🔄 Rodadas",
        value=f"`{rodadas}`",
        inline=True
    )

    embed.add_field(
        name="🗺️ Mapa",
        value=f"`{dados['map_name']}`",
        inline=True
    )

    embed.add_field(
        name="⚙️ Configuração",
        value=f"`{dados['configuration']}`",
        inline=True
    )

    embed.set_footer(
        text=f"Criada por {ctx.author}"
    )

    await mensagem.edit(
        content=None,
        embed=embed
    )


# =========================================================
# VER ÚLTIMA SALA
#
# !minhasala
# =========================================================

@bot.command()
async def minhasala(ctx):

    sala = salas_ativas.get(ctx.channel.id)

    if not sala:
        await ctx.send(
            "❌ Não existe uma sala criada recentemente neste canal."
        )
        return

    room_id = sala.get(
        "external_room_id"
    ) or sala.get("id")

    embed = discord.Embed(
        title="🎮 ÚLTIMA SALA",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🆔 ID",
        value=f"`{room_id}`",
        inline=False
    )

    embed.add_field(
        name="🔑 Senha",
        value=f"`{sala.get('password', 'Não informado')}`",
        inline=True
    )

    embed.add_field(
        name="🔄 Rodadas",
        value=f"`{sala.get('rounds', '?')}`",
        inline=True
    )

    embed.add_field(
        name="🗺️ Mapa",
        value=f"`{sala.get('map_name', '?')}`",
        inline=True
    )

    await ctx.send(embed=embed)


# =========================================================
# INICIAR SALA
#
# !iniciarsala
# =========================================================

@bot.command()
async def iniciarsala(ctx):

    sala = salas_ativas.get(ctx.channel.id)

    if not sala:
        await ctx.send("❌ Nenhuma sala encontrada neste canal.")
        return

    room_id = sala.get("id")

    if not room_id:
        await ctx.send("❌ ID interno da sala não encontrado.")
        return

    try:

        async with httpx.AsyncClient(timeout=30) as client:

            resposta = await client.post(
                f"{API_BASE}/rooms/{room_id}/start"
            )

        if resposta.status_code != 200:
            await ctx.send(
                f"❌ Erro ao iniciar sala: `{resposta.status_code}`"
            )
            return

        await ctx.send("▶️ **SALA INICIADA!**")

    except Exception as erro:

        await ctx.send(
            f"❌ Erro ao conectar à API: `{erro}`"
        )


# =========================================================
# FINALIZAR SALA
#
# !finalizarsala
# =========================================================

@bot.command()
async def finalizarsala(ctx):

    sala = salas_ativas.get(ctx.channel.id)

    if not sala:
        await ctx.send("❌ Nenhuma sala encontrada neste canal.")
        return

    room_id = sala.get("id")

    if not room_id:
        await ctx.send("❌ ID interno da sala não encontrado.")
        return

    try:

        async with httpx.AsyncClient(timeout=30) as client:

            resposta = await client.post(
                f"{API_BASE}/rooms/{room_id}/finish"
            )

        if resposta.status_code != 200:
            await ctx.send(
                f"❌ Erro ao finalizar sala: `{resposta.status_code}`"
            )
            return

        await ctx.send("🏁 **SALA FINALIZADA!**")

    except Exception as erro:

        await ctx.send(
            f"❌ Erro ao conectar à API: `{erro}`"
        )


# =========================================================
# ERROS DE COMANDO
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):

        await ctx.send(
            "❌ Argumento faltando.\n\n"
            "Exemplo:\n"
            "`!sala 4v4 13`"
        )
        return

    if isinstance(error, commands.BadArgument):

        await ctx.send(
            "❌ Quantidade de rodadas inválida.\n"
            "Exemplo: `!sala 4v4 13`"
        )
        return

    print(f"Erro no comando {ctx.command}: {error}")


# =========================================================
# INICIAR BOT
# =========================================================

if not DISCORD_TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN não configurado."
    )

bot.run(DISCORD_TOKEN)
