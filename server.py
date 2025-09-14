# server.py
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do banco de dados
DATABASE = os.getenv("DATABASE_URL")
if not DATABASE:
    raise ValueError("DATABASE_URL não está definida nas variáveis de ambiente")

# Replace 'postgres://' with 'postgresql://' for SQLAlchemy compatibility
DATABASE = DATABASE.replace("postgres://", "postgresql://")

engine = create_engine(DATABASE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Modelos do banco de dados
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


# Cria as tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI()


# Modelos Pydantic para requests
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


# Endpoints
@app.get("/")
def root():
    return {"message": "API funcionando"}


@app.get("/machines")
def list_machines():
    db = SessionLocal()
    try:
        # Máquinas ativas (últimos 5 minutos)
        active_threshold = datetime.utcnow() - timedelta(minutes=5)
        machines = db.query(Machine).filter(Machine.last_seen >= active_threshold).all()
        return {"machines": [{"id": m.id, "name": m.name, "last_seen": m.last_seen} for m in machines]}
    finally:
        db.close()


@app.post("/register_machine")
def register_machine(machine: MachineRegistration):
    db = SessionLocal()
    try:
        # Verifica se a máquina já existe
        existing_machine = db.query(Machine).filter(Machine.name == machine.name).first()

        if existing_machine:
            # Atualiza o last_seen
            existing_machine.last_seen = datetime.utcnow()
            db.commit()
            return {"message": "Máquina atualizada", "machine_id": existing_machine.id}
        else:
            # Cria nova máquina
            new_machine = Machine(name=machine.name, last_seen=datetime.utcnow())
            db.add(new_machine)
            db.commit()
            db.refresh(new_machine)
            return {"message": "Máquina registrada", "machine_id": new_machine.id}
    finally:
        db.close()


@app.post("/scripts")
def register_script(script: ScriptRegistration):
    db = SessionLocal()
    try:
        # Verifica se script já existe
        existing_script = db.query(Script).filter(Script.name == script.name).first()

        if existing_script:
            # Atualiza o conteúdo
            existing_script.content = script.content
            db.commit()
            return {"message": "Script atualizado"}
        else:
            # Cria novo script
            new_script = Script(name=script.name, content=script.content)
            db.add(new_script)
            db.commit()
            return {"message": "Script registrado"}
    finally:
        db.close()


@app.post("/execute")
def execute_script(request: ExecuteRequest):
    db = SessionLocal()
    try:
        # Encontra a máquina pelo nome
        machine = db.query(Machine).filter(Machine.name == request.machine_name).first()
        if not machine:
            raise HTTPException(status_code=404, detail="Máquina não encontrada")

        # Verifica se o script existe
        script = db.query(Script).filter(Script.name == request.script_name).first()
        if not script:
            raise HTTPException(status_code=404, detail="Script não encontrado")

        # Cria comando pendente
        new_command = Command(
            machine_id=machine.id,
            script_name=request.script_name,
            status="pending"
        )
        db.add(new_command)
        db.commit()
        db.refresh(new_command)

        return {"message": "Comando agendado", "command_id": new_command.id}
    finally:
        db.close()


@app.get("/commands/{machine_id}")
def get_pending_commands(machine_id: str):
    db = SessionLocal()
    try:
        commands = db.query(Command).filter(
            Command.machine_id == machine_id,
            Command.status == "pending"
        ).all()

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
    db = SessionLocal()
    try:
        command = db.query(Command).filter(Command.id == command_id).first()
        if not command:
            raise HTTPException(status_code=404, detail="Comando não encontrado")

        command.status = "completed"
        command.output = result.output
        db.commit()

        return {"message": "Resultado registrado"}
    finally:
        db.close()
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="127.0.0.1", port=port)