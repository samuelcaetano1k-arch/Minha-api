import os
import json
import uuid

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(
    title="Free Fire Custom Rooms API",
    version="3.0.0"
)


DATABASE_FILE = "salas.json"


# =========================================================
# BANCO DE DADOS
# =========================================================

def carregar_salas():
    if not os.path.exists(DATABASE_FILE):
        return []

    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except Exception:
        return []


def salvar_salas(salas):
    with open(DATABASE_FILE, "w", encoding="utf-8") as arquivo:
        json.dump(
            salas,
            arquivo,
            indent=4,
            ensure_ascii=False
        )


# =========================================================
# MODELOS
# =========================================================

class RoomRequest(BaseModel):
    room_name: str = Field(default="Sala Free Fire")
    password: str = Field(default="00")
    mode: int = Field(default=1, ge=1)
    rounds: int = Field(default=7, ge=1)
    map_name: str = Field(default="Bermuda")
    configuration: str = Field(default="padrão")
    start_delay_minutes: int = Field(default=0, ge=0)


class RoomResponse(BaseModel):
    id: str
    room_name: str
    password: str
    mode: int
    rounds: int
    map_name: str
    configuration: str
    start_delay_minutes: int
    status: str
    provider: str
    created_at: str
    external_room_id: Optional[str] = None


# =========================================================
# PROVIDER
# =========================================================

class RoomProvider:

    name = "local"

    def create_room(self, room_data):

        # ATENÇÃO:
        # Atualmente isso NÃO cria uma sala real no Free Fire.
        # Apenas cria uma sala no banco da nossa API.

        return {
            "success": True,
            "external_room_id": None,
            "message": "Sala criada localmente."
        }

    def start_room(self, room_data):

        return {
            "success": True,
            "message": "Sala iniciada."
        }

    def finish_room(self, room_data):

        return {
            "success": True,
            "message": "Sala finalizada."
        }


provider = RoomProvider()


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "status": "online",
        "api": "Free Fire Custom Rooms API",
        "version": "3.0.0",
        "provider": provider.name
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "provider": provider.name
    }


# =========================================================
# CRIAR SALA
# =========================================================

@app.post("/rooms", response_model=RoomResponse)
def criar_sala(dados: RoomRequest):

    salas = carregar_salas()

    room_id = str(uuid.uuid4())[:8]

    room_data = {
        "id": room_id,
        "room_name": dados.room_name,
        "password": dados.password,
        "mode": dados.mode,
        "rounds": dados.rounds,
        "map_name": dados.map_name,
        "configuration": dados.configuration,
        "start_delay_minutes": dados.start_delay_minutes
    }

    resultado = provider.create_room(room_data)

    if not resultado.get("success"):
        raise HTTPException(
            status_code=502,
            detail="O provider não conseguiu criar a sala."
        )

    nova_sala = {
        **room_data,
        "status": "created",
        "provider": provider.name,
        "external_room_id": resultado.get("external_room_id"),
        "created_at": datetime.now().isoformat()
    }

    salas.append(nova_sala)

    salvar_salas(salas)

    return nova_sala


# =========================================================
# LISTAR SALAS
# =========================================================

@app.get("/rooms")
def listar_salas():

    salas = carregar_salas()

    return {
        "total": len(salas),
        "rooms": salas
    }


# =========================================================
# BUSCAR SALA
# =========================================================

@app.get("/rooms/{room_id}")
def pegar_sala(room_id: str):

    salas = carregar_salas()

    for sala in salas:

        if sala["id"] == room_id:
            return sala

    raise HTTPException(
        status_code=404,
        detail="Sala não encontrada."
    )


# =========================================================
# INICIAR SALA
# =========================================================

@app.post("/rooms/{room_id}/start")
def iniciar_sala(room_id: str):

    salas = carregar_salas()

    for sala in salas:

        if sala["id"] == room_id:

            resultado = provider.start_room(sala)

            if not resultado.get("success"):
                raise HTTPException(
                    status_code=502,
                    detail="Não foi possível iniciar a sala."
                )

            sala["status"] = "started"

            salvar_salas(salas)

            return {
                "success": True,
                "room": sala
            }

    raise HTTPException(
        status_code=404,
        detail="Sala não encontrada."
    )


# =========================================================
# FINALIZAR SALA
# =========================================================

@app.post("/rooms/{room_id}/finish")
def finalizar_sala(room_id: str):

    salas = carregar_salas()

    for sala in salas:

        if sala["id"] == room_id:

            resultado = provider.finish_room(sala)

            if not resultado.get("success"):
                raise HTTPException(
                    status_code=502,
                    detail="Não foi possível finalizar a sala."
                )

            sala["status"] = "finished"

            salvar_salas(salas)

            return {
                "success": True,
                "room": sala
            }

    raise HTTPException(
        status_code=404,
        detail="Sala não encontrada."
    )


# =========================================================
# EXCLUIR SALA
# =========================================================

@app.delete("/rooms/{room_id}")
def excluir_sala(room_id: str):

    salas = carregar_salas()

    nova_lista = [
        sala for sala in salas
        if sala["id"] != room_id
    ]

    if len(nova_lista) == len(salas):
        raise HTTPException(
            status_code=404,
            detail="Sala não encontrada."
        )

    salvar_salas(nova_lista)

    return {
        "success": True,
        "message": "Sala excluída."
    }
