from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid
import logging
from security import CommandSecurity


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuração do banco
load_dotenv()
DATABASE = os.getenv("DATABASE_URL")
if not DATABASE:
    raise ValueError("DATABASE_URL não está definida nas variáveis de ambiente")

DATABASE = DATABASE.replace("postgres://", "postgresql://")
engine = create_engine(DATABASE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Modelos do banco
class Machine(Base):
    __tablename__ = "machines"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow)


class Script(Base):
    __tablename__ = "scripts"
    name = Column(String, primary_key=True)
    content = Column(Text, nullable=False)


class Command(Base):
    __tablename__ = "commands"
    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String, ForeignKey("machines.id"))
    script_name = Column(String, ForeignKey("scripts.name"))
    status = Column(String, default="pending")  # pending, completed
    output = Column(Text, default="")

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Modelos Pydantic
class MachineRegistration(BaseModel):
    name: str


class ScriptRegistration(BaseModel):
    name: str
    content: str


class ExecuteRequest(BaseModel):
    machine_name: str
    script_name: str


class CommandResult(BaseModel):
    output: str


class CommandResultInput(BaseModel):
    machine_id: str
    script_name: str
    output: str


# Endpoints
@app.get("/")
def root():
    logger.info("Health check: API funcionando")
    return {"message": "API funcionando"}


@app.get("/machines")
def list_machines():
    logger.info("Listando máquinas ativas")
    db = SessionLocal()
    try:
        active_threshold = datetime.utcnow() - timedelta(minutes=5)
        machines = db.query(Machine).filter(Machine.last_seen >= active_threshold).all()
        logger.info(f"{len(machines)} máquinas ativas encontradas")
        return {"machines": [{"id": m.id, "name": m.name, "last_seen": m.last_seen} for m in machines]}
    finally:
        db.close()


@app.post("/register_machine")
def register_machine(machine: MachineRegistration):
    logger.info(f"Registrando/atualizando máquina: {machine.name}")
    db = SessionLocal()
    try:
        existing_machine = db.query(Machine).filter(Machine.name == machine.name).first()

        if existing_machine:
            existing_machine.last_seen = datetime.utcnow()
            db.commit()
            logger.info(f"Máquina atualizada: {existing_machine.id} - {existing_machine.name}")
            return {"message": "Máquina atualizada", "machine_id": existing_machine.id}
        else:
            new_machine = Machine(name=machine.name, last_seen=datetime.utcnow())
            db.add(new_machine)
            db.commit()
            db.refresh(new_machine)
            logger.info(f"Nova máquina registrada: {new_machine.id} - {new_machine.name}")
            return {"message": "Máquina registrada", "machine_id": new_machine.id}
    except Exception as e:
        logger.error(f"Erro ao registrar máquina {machine.name}: {str(e)}")
        raise
    finally:
        db.close()


@app.post("/scripts")
def register_script(script: ScriptRegistration):
    logger.info(f"Registrando script: {script.name}")
    if CommandSecurity.is_dangerous(script.content):
        logger.warning(f"Script perigoso bloqueado: {script.name}")
        raise HTTPException(status_code=400, detail="Script perigoso detectado")

    db = SessionLocal()
    try:
        existing_script = db.query(Script).filter(Script.name == script.name).first()

        if existing_script:
            existing_script.content = script.content
            db.commit()
            logger.info(f"Script atualizado: {script.name}")
            return {"message": "Script atualizado com sucesso."}
        else:
            new_script = Script(name=script.name, content=script.content)
            db.add(new_script)
            db.commit()
            logger.info(f"Novo script registrado: {script.name}")
            return {"message": "Script registrado com sucesso."}
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao registrar script {script.name}: {str(e)}")
        raise
    finally:
        db.close()


@app.post("/execute")
def execute_script(request: ExecuteRequest):
    logger.info(f"Solicitada execução: máquina={request.machine_name}, script={request.script_name}")
    db = SessionLocal()
    try:
        machine = db.query(Machine).filter(Machine.name == request.machine_name).first()
        if not machine:
            logger.warning(f"Máquina não encontrada: {request.machine_name}")
            raise HTTPException(status_code=404, detail="Máquina não encontrada")

        script = db.query(Script).filter(Script.name == request.script_name).first()
        if not script:
            logger.warning(f"Script não encontrado: {request.script_name}")
            raise HTTPException(status_code=404, detail="Script não encontrado")

        new_command = Command(machine_id=machine.id, script_name=request.script_name, status="pending")
        db.add(new_command)
        db.commit()
        db.refresh(new_command)

        logger.info(f"Comando agendado: id={new_command.id}, máquina={machine.id}, script={request.script_name}")
        return {"message": "Comando agendado", "command_id": new_command.id}
    except Exception as e:
        logger.error(f"Erro ao executar script {request.script_name} na máquina {request.machine_name}: {str(e)}")
        raise
    finally:
        db.close()


@app.get("/commands/{machine_id}")
def get_pending_commands(machine_id: str):
    logger.info(f"Buscando comandos pendentes para máquina {machine_id}")
    db = SessionLocal()
    try:
        commands = db.query(Command).filter(
            Command.machine_id == machine_id,
            Command.status == "pending"
        ).all()
        logger.info(f"{len(commands)} comandos pendentes encontrados para máquina {machine_id}")
        return {"commands": [
            {
                "id": cmd.id,
                "script_name": cmd.script_name,
                "script_content": db.query(Script).filter(Script.name == cmd.script_name).first().content
            } for cmd in commands
        ]}
    finally:
        db.close()


@app.post("/commands/{command_id}/result")
def post_command_result(command_id: int, result: CommandResult):
    logger.info(f"Recebido resultado para comando {command_id}")
    db = SessionLocal()
    try:
        command = db.query(Command).filter(Command.id == command_id).first()
        if not command:
            logger.warning(f"Comando {command_id} não encontrado")
            raise HTTPException(status_code=404, detail="Comando não encontrado")

        command.status = "completed"
        command.output = result.output
        db.commit()

        logger.info(f"Resultado registrado para comando {command_id}")
        return {"message": "Resultado registrado"}
    except Exception as e:
        logger.error(f"Erro ao registrar resultado do comando {command_id}: {str(e)}")
        raise
    finally:
        db.close()

@app.get("/commands/result/{machine_id}")
def get_last_command_result(machine_id: str):
    logger.info(f"Buscando último resultado de comando para máquina {machine_id}")
    db = SessionLocal()
    try:
        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if not machine:
            logger.warning(f"Máquina {machine_id} não encontrada")
            raise HTTPException(status_code=404, detail="Máquina não encontrada")

        command = (
            db.query(Command)
            .filter(Command.machine_id == machine.id, Command.status == "completed")
            .order_by(Command.id.desc())
            .first()
        )

        if not command:
            logger.info(f"Nenhum comando completado encontrado para máquina {machine_id}")
            return {"message": "Nenhum comando completado encontrado", "command": None}

        logger.info(f"Último comando completado encontrado: id={command.id}, máquina={machine_id}")
        return {
            "command_id": command.id,
            "script_name": command.script_name,
            "output": command.output,
            "status": command.status
        }
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Iniciando servidor na porta {port}")
    uvicorn.run(app, host="127.0.0.1", port=port)