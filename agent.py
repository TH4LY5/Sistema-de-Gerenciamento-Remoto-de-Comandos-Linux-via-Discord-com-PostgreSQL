import os
import time
import requests
import subprocess
import socket
import logging
from datetime import datetime
from security import CommandSecurity

# URL do seu FastAPI
SERVER_URL = "https://sistema-de-gerenciamento-remot-b77adc170aa9.herokuapp.com"
MACHINE_FILE = "/etc/agent_id"  # onde salvar o ID único da máquina


#LOGGING CONFIG
LOG_FILE = "/var/log/linux_agent.log"  # log persistente
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # também mostra no console
    ]
)

logger = logging.getLogger("LinuxAgent")

# Identificação da máquina
def get_machine_id():
    if os.path.exists(MACHINE_FILE):
        with open(MACHINE_FILE, "r") as f:
            return f.read().strip()
    else:
        return None

MACHINE_NAME = socket.gethostname()
MACHINE_ID = get_machine_id()

# Registrar ou atualizar a máquina no servidor
def register_machine():
    global MACHINE_ID
    try:
        logger.info(f"Tentando registrar/atualizar máquina: {MACHINE_NAME}")
        resp = requests.post(f"{SERVER_URL}/register_machine", json={
            "name": MACHINE_NAME
        })
        resp.raise_for_status()
        data = resp.json()
        machine_id_from_server = data.get("machine_id")
        if machine_id_from_server:
            MACHINE_ID = machine_id_from_server
            with open(MACHINE_FILE, "w") as f:
                f.write(MACHINE_ID)
            logger.info(f"Máquina registrada/atualizada com sucesso (ID: {MACHINE_ID})")
        else:
            logger.error("Servidor não retornou machine_id")
    except Exception as e:
        logger.error(f"Falha ao registrar/atualizar máquina: {e}")


# Buscar comandos pendentes
def check_commands():
    if MACHINE_ID is None:
        logger.warning("Não é possível verificar comandos: MACHINE_ID não definido")
        return

    try:
        logger.info("Verificando comandos pendentes...")
        resp = requests.get(f"{SERVER_URL}/commands/{MACHINE_ID}")
        resp.raise_for_status()
        data = resp.json()
        command_count = len(data.get("commands", []))
        logger.info(f"{command_count} comando(s) pendente(s) recebido(s) do servidor")

        for cmd in data.get("commands", []):
            execute_command(cmd)
    except Exception as e:
        logger.error(f"Erro ao buscar comandos: {e}")


# Executar comando
def execute_command(cmd):
    cmd_id = cmd["id"]
    script_name = cmd["script_name"]
    script_content = cmd["script_content"]

    if CommandSecurity.is_dangerous(script_content):
        output = "ERRO: Comando bloqueado por segurança."
        logger.warning(f"Comando {cmd_id} bloqueado: {script_content}")
        send_result(cmd_id, output)
        return

    logger.info(f"Executando comando {cmd_id}: {script_name}")

    try:
        result = subprocess.run(
            script_content,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        output = result.stdout + result.stderr
        logger.info(f"Comando {cmd_id} executado - Status {result.returncode}")
    except Exception as e:
        output = f"Erro ao executar comando: {e}"
        logger.error(f"Falha ao executar comando {cmd_id}: {e}")

    send_result(cmd_id, output)


# Enviar resultado de volta
def send_result(cmd_id, output):
    try:
        logger.info(f"Enviando resultado do comando {cmd_id}")
        resp = requests.post(f"{SERVER_URL}/commands/{cmd_id}/result", json={
            "output": output
        })
        resp.raise_for_status()
        logger.info(f"Resultado do comando {cmd_id} enviado com sucesso")
    except Exception as e:
        logger.error(f"Falha ao enviar resultado do comando {cmd_id}: {e}")


# Loop principal
def main():
    logger.info("🚀 Iniciando agente...")

    if MACHINE_ID is None:
        register_machine()

    while True:
        logger.info("Iniciando ciclo de verificação")
        register_machine()
        check_commands()
        logger.info("Ciclo concluído - aguardando 5 minutos")
        time.sleep(300)


if __name__ == "__main__":
    main()