import os
import time
import uuid
import requests
import subprocess
import socket

# URL do seu FastAPI
SERVER_URL = "https://sistema-de-gerenciamento-remot-b77adc170aa9.herokuapp.com"
MACHINE_FILE = "/etc/agent_id"        # onde salvar o ID único da máquina

# Identificação da máquina
def get_machine_id():
    if os.path.exists(MACHINE_FILE):
        with open(MACHINE_FILE, "r") as f:
            return f.read().strip()
    else:
        machine_id = str(uuid.uuid4())
        with open(MACHINE_FILE, "w") as f:
            f.write(machine_id)
        return machine_id

MACHINE_ID = get_machine_id()
MACHINE_NAME = socket.gethostname()

# Registrar ou atualizar a máquina no servidor
def register_machine():
    try:
        resp = requests.post(f"{SERVER_URL}/register_machine", json={
            "id": MACHINE_ID,
            "name": MACHINE_NAME
        })
        resp.raise_for_status()
        print(f"[OK] Máquina registrada: {MACHINE_NAME} ({MACHINE_ID})")
    except Exception as e:
        print(f"[ERRO] Falha ao registrar máquina: {e}")

# Buscar comandos pendentes
def check_commands():
    try:
        resp = requests.get(f"{SERVER_URL}/commands/{MACHINE_ID}")
        resp.raise_for_status()
        data = resp.json()
        for cmd in data.get("commands", []):
            execute_command(cmd)
    except Exception as e:
        print(f"[ERRO] Falha ao buscar comandos: {e}")

# Executar comando
def execute_command(cmd):
    cmd_id = cmd["id"]
    script_name = cmd["script_name"]
    script_content = cmd["script_content"]

    print(f"[EXECUTANDO] Comando {cmd_id}: {script_name} -> {script_content}")

    try:
        result = subprocess.run(
            script_content,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        output = result.stdout + result.stderr
    except Exception as e:
        output = f"Erro ao executar comando: {e}"

    send_result(cmd_id, output)

# Enviar resultado de volta
def send_result(cmd_id, output):
    try:
        resp = requests.post(f"{SERVER_URL}/commands/{cmd_id}/result", json={
            "output": output
        })
        resp.raise_for_status()
        print(f"[OK] Resultado enviado para comando {cmd_id}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar resultado: {e}")

# Loop principal
def main():
    register_machine()
    while True:
        check_commands()
        time.sleep(300)  # 5 minutos

if __name__ == "__main__":
    main()
