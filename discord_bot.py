import os
import discord
import aiohttp
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_URL = "https://sistema-de-gerenciamento-remot-b77adc170aa9.herokuapp.com/"  # URL do seu serviço web
AUTHORIZED_USERS = [410731828618592256]  # IDs dos usuários autorizados

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def make_get_request(endpoint):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/{endpoint}") as response:
            return await response.json()


async def make_post_request(endpoint, data):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SERVER_URL}/{endpoint}", json=data) as response:
            return await response.json()


@client.event
async def on_ready():
    print(f"Bot conectado como {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Verifica permissões
    if message.author.id not in AUTHORIZED_USERS:
        await message.channel.send("❌ Você não tem permissão para executar comandos.")
        return

    # Comando !list_machines
    if message.content.lower().startswith("!list_machines"):
        try:
            data = await make_get_request("machines")
            machines = [m for m in data['machines'] if
                        datetime.fromisoformat(m['last_ping']) > datetime.now() - timedelta(minutes=5)]

            if not machines:
                await message.channel.send("Nenhuma máquina ativa nos últimos 5 minutos.")
                return

            response = "🖥️ **Máquinas Ativas:**\n" + "\n".join(
                f"{m['name']} (Último ping: {m['last_ping']})" for m in machines
            )
            await message.channel.send(response)
        except Exception as e:
            await message.channel.send(f"Erro ao listar máquinas: {str(e)}")

    # Comando !register_script
    elif message.content.lower().startswith("!register_script"):
        parts = message.content.split(maxsplit=2)
        if len(parts) < 3:
            await message.channel.send("Uso: !register_script <nome> <conteúdo>")
            return

        name = parts[1]
        content = parts[2]

        try:
            data = await make_post_request("scripts", {"name": name, "content": content})
            await message.channel.send(f"✅ Script '{name}' registrado com sucesso!")
        except Exception as e:
            await message.channel.send(f"Erro ao registrar script: {str(e)}")

    # Comando !execute_script
    elif message.content.lower().startswith("!execute_script"):
        parts = message.content.split()
        if len(parts) < 3:
            await message.channel.send("Uso: !execute_script <nome_máquina> <nome_script>")
            return

        machine_name = parts[1]
        script_name = parts[2]

        try:
            data = await make_post_request("execute", {
                "machine_name": machine_name,
                "script_name": script_name
            })
            await message.channel.send(f"✅ Script '{script_name}' agendado para execução em {machine_name}!")
        except Exception as e:
            await message.channel.send(f"Erro ao executar script: {str(e)}")


if __name__ == "__main__":
    client.run(TOKEN)