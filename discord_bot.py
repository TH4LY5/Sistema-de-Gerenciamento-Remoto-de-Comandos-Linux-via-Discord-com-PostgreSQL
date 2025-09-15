import os
import discord
import aiohttp
import asyncio
import asyncpg
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = "https://sistema-de-gerenciamento-remot-b77adc170aa9.herokuapp.com/"
AUTHORIZED_USERS = [410731828618592256]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


# CONECTAR NO BANCO PARA OBTER A CHAVE DO DISCORD
async def get_discord_token_from_db():
    """Conecta ao banco de dados usando a DATABASE_URL e busca o token do Discord."""
    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("🔥 ERRO: A variável de ambiente 'DATABASE_URL' não foi encontrada.")
            return None

        # Conecta ao banco usando a URL diretamente
        conn = await asyncpg.connect(dsn=db_url)
        print("✅ Conectado ao banco de dados via DATABASE_URL.")

        # Executa a query para buscar o valor da chave
        record = await conn.fetchrow("SELECT * FROM config WHERE key = $1", 'DISCORD_TOKEN')

        await conn.close()

        if record:
            return record['value']
        else:
            print("❌ Token não encontrado no banco de dados.")
            return None

    except Exception as e:
        print(f"🔥 Erro ao conectar ou buscar token no banco de dados: {e}")
        return None


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
    # (O resto do seu código de comandos continua o mesmo, sem alterações)
    if message.author == client.user:
        return

    if message.author.id not in AUTHORIZED_USERS:
        await message.channel.send("❌ Você não tem permissão para executar comandos.")
        return

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

    elif message.content.lower().startswith("!register_script"):
        parts = message.content.split(maxsplit=2)
        if len(parts) < 3:
            await message.channel.send("Uso: !register_script <nome> <conteúdo>")
            return
        name, content = parts[1], parts[2]
        try:
            await make_post_request("scripts", {"name": name, "content": content})
            await message.channel.send(f"✅ Script '{name}' registrado com sucesso!")
        except Exception as e:
            await message.channel.send(f"Erro ao registrar script: {str(e)}")

    elif message.content.lower().startswith("!execute_script"):
        parts = message.content.split()
        if len(parts) < 3:
            await message.channel.send("Uso: !execute_script <nome_máquina> <nome_script>")
            return
        machine_name, script_name = parts[1], parts[2]
        try:
            await make_post_request("execute", {"machine_name": machine_name, "script_name": script_name})
            await message.channel.send(f"✅ Script '{script_name}' agendado para execução em {machine_name}!")
        except Exception as e:
            await message.channel.send(f"Erro ao executar script: {str(e)}")


async def main():
    """Função principal que busca o token e inicia o bot."""
    discord_token = await get_discord_token_from_db()

    if discord_token:
        try:
            print("🚀 Iniciando o bot com o token do banco de dados...")
            await client.start(discord_token)
        except discord.errors.LoginFailure:
            print("🔥 Falha no login. Verifique se o token do Discord no banco de dados é válido.")
        except Exception as e:
            print(f"🔥 Ocorreu um erro ao tentar iniciar o bot: {e}")
    else:
        print("❌ Bot não iniciado: token não pôde ser obtido.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot desligado pelo usuário.")