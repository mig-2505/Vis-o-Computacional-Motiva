"""
historico.py
=============
Guarda e consulta o histórico de medições por ponto (marco de KM),
para permitir comparação ao longo do tempo e cálculo de tendência
(o fator "histórico" do Índice de Prioridade).

Persistência simples em CSV local — suficiente para o protótipo.
Quando o projeto for para produção, isso deve virar uma tabela em
banco de dados (Postgres/SQLite), mas a interface das funções abaixo
pode continuar igual.
"""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd

CAMINHO_HISTORICO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historico_medicoes.csv")

COLUNAS = ["timestamp", "ponto_id", "altura_cm", "cobertura_pct", "largura_cm", "fonte", "medicao_id"]


def _carregar():
    if not os.path.exists(CAMINHO_HISTORICO):
        return pd.DataFrame(columns=COLUNAS)
    try:
        df = pd.read_csv(CAMINHO_HISTORICO, parse_dates=["timestamp"])
        for coluna in COLUNAS:
            if coluna not in df.columns:
                df[coluna] = None
        return df
    except Exception:
        return pd.DataFrame(columns=COLUNAS)


def registrar_medicao(
    ponto_id,
    altura_cm=None,
    cobertura_pct=None,
    largura_cm=None,
    fonte="demo",
    medicao_id=None,
):
    """Registra uma medição sem duplicar a mesma imagem/medição.

    medicao_id deve ser um identificador estável (ex.: SHA-256 da foto).
    """
    df = _carregar()

    if medicao_id and "medicao_id" in df.columns:
        existentes = df["medicao_id"].fillna("").astype(str)
        if medicao_id in set(existentes):
            return df

    nova = pd.DataFrame(
        [
            {
                "timestamp": datetime.now(),
                "ponto_id": ponto_id,
                "altura_cm": altura_cm,
                "cobertura_pct": cobertura_pct,
                "largura_cm": largura_cm,
                "fonte": fonte,
                "medicao_id": medicao_id or "",
            }
        ]
    )
    df = pd.concat([df, nova], ignore_index=True)
    df.to_csv(CAMINHO_HISTORICO, index=False)
    return df


def historico_do_ponto(ponto_id):
    df = _carregar()
    if df.empty:
        return df
    return df[df["ponto_id"] == ponto_id].sort_values("timestamp")


def tendencia_cm(ponto_id, janela=5):
    """Retorna a variação de altura (cm) entre a primeira e a última medição
    dentro da janela mais recente. None se não houver histórico suficiente."""
    hist = historico_do_ponto(ponto_id)
    hist = hist.dropna(subset=["altura_cm"])
    if len(hist) < 2:
        return None
    janela_df = hist.tail(janela)
    return float(janela_df["altura_cm"].iloc[-1] - janela_df["altura_cm"].iloc[0])


def todos_pontos_com_historico():
    df = _carregar()
    if df.empty:
        return []
    return sorted(df["ponto_id"].dropna().unique().tolist())
