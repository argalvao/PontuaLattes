# pyright: reportMissingImports=false
"""
Banco local em SQLite para rodar o PontuaLattes sem Turso.

Serve como alternativa ao libsql-client quando a variável TURSO_URL não está
definida: expõe a mesma interface mínima usada pelo turso_store
(``execute``, ``batch`` e um resultado com ``columns``, ``rows`` e
``last_insert_rowid``), gravando tudo em um arquivo .db na máquina.

Como o Turso é SQLite distribuído, o mesmo SQL funciona nos dois modos.
"""

import sqlite3
import threading


class ResultadoConsulta:
    """Equivalente local ao ResultSet devolvido pelo libsql-client."""

    def __init__(self, columns, rows, last_insert_rowid):
        self.columns = columns
        self.rows = rows
        self.last_insert_rowid = last_insert_rowid

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)


class ClienteSqliteLocal:
    def __init__(self, caminho):
        self.caminho = caminho
        self._lock = threading.RLock()
        self._conexao = sqlite3.connect(caminho, check_same_thread=False)
        try:
            # WAL melhora a concorrência, mas não é suportado em todo sistema
            # de arquivos (pastas de rede, por exemplo). Se falhar, segue no
            # journal padrão.
            self._conexao.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass

    def _executar(self, sql, args=None):
        cursor = self._conexao.execute(sql, tuple(args or ()))
        colunas = [descricao[0] for descricao in cursor.description] if cursor.description else []
        linhas = cursor.fetchall() if cursor.description else []
        return ResultadoConsulta(colunas, linhas, cursor.lastrowid)

    def execute(self, sql, args=None):
        with self._lock:
            resultado = self._executar(sql, args)
            self._conexao.commit()
            return resultado

    def batch(self, statements):
        with self._lock:
            resultados = []
            for statement in statements:
                if isinstance(statement, (list, tuple)):
                    sql, args = statement[0], statement[1] if len(statement) > 1 else None
                else:
                    sql, args = statement, None
                resultados.append(self._executar(sql, args))
            self._conexao.commit()
            return resultados

    def close(self):
        with self._lock:
            self._conexao.close()


def criar_cliente_local(caminho):
    return ClienteSqliteLocal(caminho)
