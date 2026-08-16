import os
import httpx


async def criar_sala(modo: int, senha: str):
    oauth_key = os.getenv("GUCCIFER_OAUTH_KEY")

    if not oauth_key:
        raise RuntimeError("GUCCIFER_OAUTH_KEY não configurada.")

    url = "https://guccifersalas.online/api/v1/create:room"

    params = {
        "oauth_key": oauth_key,
        "modo": modo,
        "senha": senha,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)

    response.raise_for_status()

    return response.json()
