# Sistema de Gerenciamento Remoto de Comandos Linux via Discord com PostgreSQL

Este projeto implementa um sistema de gerenciamento remoto de comandos Linux, permitindo a execução e monitoramento de scripts em máquinas Linux através de um bot do Discord. A comunicação é feita via API, e os dados são persistidos em um banco de dados PostgreSQL.

## Visão Geral da Arquitetura

O sistema é composto por três componentes principais:

*   **Bot do Discord (`discord_bot.py`)**: A interface principal para interação com o usuário. Ele recebe comandos, os envia para o serviço web e exibe os resultados no Discord.
*   **Serviço Web (`server.py`)**: O cérebro do sistema. Ele gerencia o banco de dados, registra máquinas e scripts, e agenda comandos para os agentes.
*   **Agente Linux (`agent.py`)**: Um script que roda em cada máquina Linux a ser gerenciada. Ele se comunica com o serviço web para buscar e executar comandos.

## Estrutura do Repositório

```
.
├── .env
├── Collection/
├── Procfile
├── README.md
├── agent.py
├── discord_bot.py
├── requirements.txt
├── security.py
└── server.py
```

## Funcionalidades

*   **Gerenciamento de Máquinas**: Registre e liste máquinas Linux remotas.
*   **Gerenciamento de Scripts**: Crie e armazene scripts de shell para execução remota.
*   **Execução de Comandos**: Execute scripts em máquinas específicas através de comandos do Discord.
*   **Consulta de Resultados**: Verifique o resultado da execução dos comandos.

## Comandos do Discord

### `!help`

Exibe todos os comandos disponíveis.

### `!list_machines`

Lista todas as máquinas ativas (online nos últimos 5 minutos).

### `!register_script <nome> <conteúdo>`

Registra um novo script.

*   **Exemplo**: `!register_script listar_arquivos ls -l`

### `!execute_script <nome_máquina> <nome_script>`

Executa um script em uma máquina.

*   **Exemplo**: `!execute_script minha_maquina listar_arquivos`

### `!command_result <nome_máquina>`

Mostra o resultado do último comando executado na máquina.

## Endpoints da API

### `GET /machines`

Retorna uma lista de todas as máquinas registradas.

### `POST /register_machine`

Registra uma nova máquina.

### `POST /scripts`

Registra um novo script.

### `POST /execute`

Agenda um comando para ser executado em uma máquina.

### `GET /commands/result/{machine_id}`

Retorna o resultado do último comando executado em uma máquina.

## Instalação e Configuração

### Pré-requisitos

*   Python 3.8+
*   Conta no Discord e um bot configurado no Developer Portal
*   Conta no Heroku (ou similar) para hospedar o serviço web
*   Um banco de dados PostgreSQL

### Instalação do Agente Linux

Para instalar o agente em uma máquina Linux:

#### 1. Instalar Dependências

```bash
sudo apt update && sudo apt install python3 python3-pip -y
pip3 install requests
```

#### 2. Salvar o Script do Agente

```bash
sudo nano /usr/local/bin/agent.py
```

Cole o conteúdo de `agent.py` e salve o arquivo.

#### 3. Criar Arquivo de Serviço systemd

```bash
sudo nano /etc/systemd/system/agent.service
```

Cole o seguinte conteúdo:

```ini
[Unit]
Description=Agente para Gerenciamento Remoto
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /usr/local/bin/agent.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

#### 4. Habilitar e Iniciar o Serviço

```bash
sudo systemctl daemon-reload
sudo systemctl start agent
sudo systemctl enable agent
```

#### 5. Verificar Status e Logs

```bash
sudo systemctl status agent
sudo journalctl -u agent -f
```

## Contato

*   **Autor**: TH4LY5
## Testes Locais da API (Insomnia)

A pasta `Collection/` contém um arquivo de coleção da API que pode ser importado no Insomnia (ou ferramenta similar) para facilitar os testes locais dos endpoints da API.


