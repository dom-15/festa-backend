
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "ingressos.db"

class Venda(BaseModel):
    aluno: str
    vendedor: str
    quantidade: int
    forma_pagamento: List[str]
    valor_recebido: float

class Ativacao(BaseModel):
    codigo: str
    operador: str

class RelatorioRequest(BaseModel):
    senha: str

def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS ingressos (
            codigo TEXT PRIMARY KEY,
            status TEXT,
            forma_pagamento TEXT,
            data_venda TEXT,
            vendedor TEXT,
            ativado_por TEXT,
            aluno TEXT
        )''')

@app.on_event("startup")
def startup():
    init_db()

@app.post("/venda")
def registrar_venda(venda: Venda):
    codigos = []
    for _ in range(venda.quantidade):
        codigo = str(uuid.uuid4())[:8]
        codigos.append(codigo)
        with sqlite3.connect(DB) as conn:
            conn.execute("INSERT INTO ingressos VALUES (?, ?, ?, ?, ?, ?, ?)", (
                codigo,
                "aguardando_pagamento",
                "+".join(venda.forma_pagamento),
                datetime.now().isoformat(),
                venda.vendedor,
                "",
                venda.aluno
            ))
    return {"mensagem": "Ingressos registrados com sucesso.", "codigos": codigos}

@app.post("/ativar")
def ativar_ingresso(dados: Ativacao):
    with sqlite3.connect(DB) as conn:
        cur = conn.execute("SELECT status FROM ingressos WHERE codigo = ?", (dados.codigo,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ingresso não encontrado.")
        if row[0] == "liberado":
            raise HTTPException(status_code=400, detail="Ingresso já está liberado.")
        conn.execute("UPDATE ingressos SET status = 'liberado', ativado_por = ? WHERE codigo = ?", (dados.operador, dados.codigo))
    return {"mensagem": f"Ingresso {dados.codigo} ativado."}

@app.post("/relatorio")
def relatorio(req: RelatorioRequest):
    if req.senha != "vida1921":
        raise HTTPException(status_code=403, detail="Senha incorreta.")
    with sqlite3.connect(DB) as conn:
        dados = conn.execute("SELECT * FROM ingressos").fetchall()
    total = len(dados)
    ativados = sum(1 for d in dados if d[1] == "liberado")
    total_valor = total * 30
    return {
        "total_vendidos": total,
        "total_ativados": ativados,
        "valor_total": total_valor,
        "por_forma_pagamento": _contar_por(dados, 2),
        "por_vendedor": _contar_por(dados, 4),
        "por_aluno": _contar_por(dados, 6)
    }

def _contar_por(registros, idx):
    contagem = {}
    for r in registros:
        chaves = r[idx].split("+") if idx == 2 else [r[idx]]
        for chave in chaves:
            contagem[chave] = contagem.get(chave, 0) + 1
    return contagem
