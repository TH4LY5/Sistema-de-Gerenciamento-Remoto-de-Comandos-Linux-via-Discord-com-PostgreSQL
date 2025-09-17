import os
import discord
import aiohttp
import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

from security import CommandSecurity


# Configuração de LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("discord_bot")

# Configuração do BOT
load_dotenv()

SERVER_URL = os.getenv("SERVER_URL")
AUTHORIZED_USERS = [410731828618592256, 694217161752969327, 703340009259925624]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Funções auxiliares
async def get_discord_token_from_db():
    """Conecta ao banco e busca o token do Discord."""
    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.error("Variável de ambiente 'DATABASE_URL' não encontrada.")
            return None

        conn = await asyncpg.connect(dsn=db_url)
        logger.info("Conectado ao banco de dados para buscar token do Discord.")

        record = await conn.fetchrow("SELECT * FROM config WHERE key = $1", 'DISCORD_TOKEN')
        await conn.close()

        if record:
            logger.info("Token do Discord obtido com sucesso do banco.")
            return record['value']
        else:
            logger.warning("Token do Discord não encontrado no banco.")
            return None

    except Exception as e:
        logger.error(f"Erro ao conectar ou buscar token no banco de dados: {e}")
        return None


async def make_get_request(endpoint):
    logger.debug(f"GET -> {SERVER_URL}/{endpoint}")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/{endpoint}") as response:
            return await response.json()


async def make_post_request(endpoint, data):
    logger.debug(f"POST -> {SERVER_URL}/{endpoint} | Payload: {data}")
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SERVER_URL}/{endpoint}", json=data) as response:
            return await response.json()


# Eventos do BOT
@client.event
async def on_ready():
    logger.info(f"Bot conectado como {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    logger.info(f"Mensagem recebida de {message.author} ({message.author.id}): {message.content}")

    if message.author.id not in AUTHORIZED_USERS:
        logger.warning(f"Tentativa de uso não autorizado por {message.author} ({message.author.id})")
        await message.channel.send("❌ Você não tem permissão para executar comandos.")
        return

    if message.content.lower() == "!help":
        logger.info(f"Comando !help executado por {message.author}")
        embed = discord.Embed(
            title="📜 Ajuda de Comandos",
            description="Aqui estão todos os comandos disponíveis e como usá-los.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="`!list_machines`",
            value="Lista máquinas ativas (últimos 5 minutos).",
            inline=False
        )
        embed.add_field(
            name="`!register_script <nome> <conteúdo>`",
            value="Registra um novo script no sistema.\n**Exemplo:** `!register_script checar_ip ipconfig`",
            inline=False
        )
        embed.add_field(
            name="`!execute_script <nome_máquina> <nome_script>`",
            value="Executa um script em uma máquina.\n**Exemplo:** `!execute_script PC checar_ip`",
            inline=False
        )
        embed.add_field(
            name="`!command_result <nome_máquina>`",
            value="Mostra o resultado do último comando.\n**Exemplo:** `!command_result PC`",
            inline=False
        )
        embed.set_footer(text="Bot de Gerenciamento Remoto by TH4LY5")
        await message.channel.send(embed=embed)

    elif message.content.lower().startswith("!list_machines"):
        logger.info(f"Comando !list_machines solicitado por {message.author}")
        try:
            data = await make_get_request("machines")
            machines = [m for m in data['machines']
                        if datetime.fromisoformat(m['last_seen']) > datetime.now() - timedelta(minutes=5)]

            if not machines:
                await message.channel.send("Nenhuma máquina ativa nos últimos 5 minutos.")
                return

            response = "🖥️ **Máquinas Ativas:**\n" + "\n".join(
                f"{m['name']} (Último ping: {m['last_seen']})" for m in machines
            )
            await message.channel.send(response)
        except Exception as e:
            logger.error(f"Erro no !list_machines: {e}")
            await message.channel.send(f"Erro ao listar máquinas: {str(e)}")

    elif message.content.lower().startswith("!register_script"):
        logger.info(f"Comando !register_script solicitado por {message.author}")
        parts = message.content.split(maxsplit=2)
        if len(parts) < 3:
            await message.channel.send("Uso: !register_script <nome> <conteúdo>")
            return

        name, content = parts[1], parts[2]
        if CommandSecurity.is_dangerous(content):
            logger.warning(f"Tentativa de registrar script perigoso por {message.author}: {content}")
            await message.channel.send(f"❌ Script '{name}' contém comandos perigosos e não pode ser registrado!")
            return

        try:
            await make_post_request("scripts", {"name": name, "content": content})
            await message.channel.send(f"✅ Script '{name}' registrado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao registrar script '{name}': {e}")
            await message.channel.send(f"Erro ao registrar script: {str(e)}")

    elif message.content.lower().startswith("!command_result"):
        logger.info(f"Comando !command_result solicitado por {message.author}")
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("Uso: !command_result <nome_da_maquina>")
            return

        machine_name = parts[1]
        try:
            data = await make_get_request("machines")
            machines = [m for m in data['machines']
                        if datetime.fromisoformat(m['last_seen']) > datetime.now() - timedelta(minutes=5)]

            machine = next((m for m in machines if m['name'] == machine_name), None)
            if not machine:
                await message.channel.send(f"Máquina '{machine_name}' não encontrada ou inativa.")
                return

            machine_id = machine['id']
            data = await make_get_request(f"commands/result/{machine_id}")

            if not data or data.get('command_id') is None:
                await message.channel.send(f"Nenhum comando completado encontrado para a máquina '{machine_name}'.")
                return

            output = data['output'] or 'Sem saída'
            max_output_length = 1999 - len(f"📊 Resultado para {machine_name}\n📜 {data['script_name']}\n⚙️ {data['status']}\n📝 Output:\n```\n\n```")
            if len(output) > max_output_length:
                output = output[:max_output_length - 3] + "..."

            response = (
                f"📊 **Último Resultado para {machine_name}**\n"
                f"📜 Script: {data['script_name']}\n"
                f"⚙️ Status: {data['status']}\n"
                f"📝 Output:\n```\n{output}\n```"
            )
            await message.channel.send(response)
        except Exception as e:
            logger.error(f"Erro no !command_result para {machine_name}: {e}")
            await message.channel.send(f"Erro ao buscar resultado: {str(e)}")

# Inicialização do BOT
async def main():
    token = await get_discord_token_from_db()
    if token:
        try:
            logger.info("Iniciando bot com token do banco de dados...")
            await client.start(token)
        except discord.errors.LoginFailure:
            logger.error("Falha no login. Token inválido no banco.")
        except Exception as e:
            logger.error(f"Erro ao iniciar o bot: {e}")
    else:
        logger.error("Bot não iniciado: token não pôde ser obtido.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot desligado pelo usuário.")