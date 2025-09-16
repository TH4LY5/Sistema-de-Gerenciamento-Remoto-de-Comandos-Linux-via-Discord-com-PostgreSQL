import os
import time
import requests
import subprocess
import socket
from datetime import datetime
from security import CommandSecurity
# URL do seu FastAPI
SERVER_URL = "https://sistema-de-gerenciamento-remot-b77adc170aa9.herokuapp.com"
MACHINE_FILE = "/etc/agent_id"  # onde salvar o ID único da máquina


# Função para log com timestamp
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


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
        log_message(f"Tentando registrar/atualizar máquina no servidor: {MACHINE_NAME}")
        resp = requests.post(f"{SERVER_URL}/register_machine", json={
            "name": MACHINE_NAME
        })
        resp.raise_for_status()
        data = resp.json()
        machine_id_from_server = data.get("machine_id")
        if machine_id_from_server:
            MACHINE_ID = machine_id_from_server
            # Salva o ID no arquivo
            with open(MACHINE_FILE, "w") as f:
                f.write(MACHINE_ID)
            log_message(f"Máquina registrada/atualizada com sucesso: {MACHINE_NAME} (ID: {MACHINE_ID})")
        else:
            log_message("Erro: servidor não retornou machine_id")
    except Exception as e:
        log_message(f"Falha ao registrar/atualizar máquina: {e}")


# Buscar comandos pendentes
def check_commands():
    if MACHINE_ID is None:
        log_message("Não é possível verificar comandos: MACHINE_ID não está definido")
        return

    try:
        log_message("Verificando comandos pendentes")
        resp = requests.get(f"{SERVER_URL}/commands/{MACHINE_ID}")
        resp.raise_for_status()
        data = resp.json()
        command_count = len(data.get("commands", []))
        log_message(f"Resposta do servidor recebida - {command_count} comando(s) pendente(s)")

        for cmd in data.get("commands", []):
            execute_command(cmd)
    except Exception as e:
        log_message(f"Falha ao buscar comandos: {e}")


# Executar comando
def execute_command(cmd):
    cmd_id = cmd["id"]
    script_name = cmd["script_name"]
    script_content = cmd["script_content"]

    # Validar comando
    if CommandSecurity.is_dangerous(script_content):
        output = "ERRO: Comando considerado perigoso e bloqueado pelo sistema de segurança."
        log_message(f"Comando bloqueado por segurança: {script_content}")
        send_result(cmd_id, output)
        return

    log_message(f"Executando comando {cmd_id}: {script_name}")

    try:
        result = subprocess.run(
            script_content,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        output = result.stdout + result.stderr
        log_message(f"Comando {cmd_id} executado - Status: {result.returncode}")
    except Exception as e:
        output = f"Erro ao executar comando: {e}"
        log_message(f"Erro na execução do comando {cmd_id}: {e}")

    send_result(cmd_id, output)


# Enviar resultado de volta
def send_result(cmd_id, output):
    try:
        log_message(f"Enviando resultado do comando {cmd_id} para o servidor")
        resp = requests.post(f"{SERVER_URL}/commands/{cmd_id}/result", json={
            "output": output
        })
        resp.raise_for_status()
        log_message(f"Resultado do comando {cmd_id} enviado com sucesso")
    except Exception as e:
        log_message(f"Falha ao enviar resultado do comando {cmd_id}: {e}")


# Loop principal
def main():
    log_message("Iniciando agente...")

    # Se não temos MACHINE_ID, registra a máquina
    if MACHINE_ID is None:
        register_machine()

    while True:
        log_message("Iniciando ciclo de verificação")
        # Atualiza o last_seen no servidor
        register_machine()
        # Verifica por comandos pendentes
        check_commands()
        log_message("Ciclo concluído - Aguardando 5 minutos")
        time.sleep(300)  # 5 minutos


if __name__ == "__main__":
    main()