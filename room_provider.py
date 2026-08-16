import httpx


async def criar_sala(key: str, salaid: str, iniciar: int = 5):
    url = "https://salasff.com/criar"

    params = {
        "key": key,
        "salaid": salaid,
        "iniciar": iniciar,
        "resultado": "true",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)

    response.raise_for_status()

    return response.json()
