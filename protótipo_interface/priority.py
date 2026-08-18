"""
priority.py
============
Índice de Prioridade de Roçada (0-100).

Combina, com pesos configuráveis:
- altura da vegetação
- cobertura vegetal (% da cena coberta por grama detectada)
- velocidade de crescimento (cm/dia, estimada por histórico ou modelo demo)
- criticidade da localização (curva, pista, cruzamento — vem do KMZ se houver)
- proximidade de áreas de roçada já mapeadas
- condições climáticas (chuva/umidade aumentam o risco de crescimento acelerado)
- tendência histórica (subiu, caiu ou estabilizou nas últimas medições)

O resultado é sempre 0-100 e vem acompanhado do detalhamento por fator,
para o dashboard poder explicar "por que" um trecho está com aquela nota
(transparência é importante numa ferramenta de decisão operacional).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Pesos padrão — somam 100. Ajustáveis conforme validação de campo.
PESOS_PADRAO = {
    "altura": 25,
    "cobertura": 15,
    "crescimento": 20,
    "localizacao": 15,
    "proximidade_rocada": 10,
    "clima": 10,
    "historico": 5,
}


@dataclass
class ResultadoPrioridade:
    indice: float
    nivel: str  # "Normal", "Monitorar", "Alta prioridade", "Intervenção"
    cor: str  # código de cor para o mapa/UI
    fatores: dict = field(default_factory=dict)  # nome_fator -> pontuação 0-100
    contribuicoes: dict = field(default_factory=dict)  # nome_fator -> pontos no índice final


def _clamp(valor, minimo=0.0, maximo=100.0):
    return max(minimo, min(maximo, valor))


def _score_altura(altura_cm):
    if altura_cm is None:
        return 0.0
    # 0cm -> 0 pontos, 30cm -> ~50 pontos, 80cm+ -> 100 pontos (curva suave)
    return _clamp((altura_cm / 80.0) * 100.0)


def _score_cobertura(cobertura_pct):
    if cobertura_pct is None:
        return 0.0
    return _clamp(cobertura_pct)


def _score_crescimento(cm_por_dia):
    if cm_por_dia is None:
        return 0.0
    # 0 cm/dia -> 0, 3 cm/dia -> ~75, 4+ cm/dia -> 100
    return _clamp((cm_por_dia / 4.0) * 100.0)


def _score_localizacao(criticidade_local):
    """criticidade_local: 0-100 vindo de metadado do KMZ (curva, cruzamento,
    proximidade de faixa) ou um valor médio (50) se não houver essa info."""
    if criticidade_local is None:
        return 50.0
    return _clamp(criticidade_local)


def _score_proximidade_rocada(distancia_km):
    """Quanto mais perto de uma área de roçada já mapeada, maior a pontuação
    (indica que a operação já passa perto e pode aproveitar o deslocamento)."""
    if distancia_km is None:
        return 50.0
    if distancia_km <= 0.1:
        return 100.0
    if distancia_km >= 5.0:
        return 0.0
    return _clamp(100.0 * (1 - distancia_km / 5.0))


def _score_clima(chuva_mm, umidade_pct):
    """Chuva e umidade recentes aceleram o crescimento -> aumentam a urgência."""
    chuva_mm = chuva_mm or 0.0
    umidade_pct = umidade_pct or 50.0
    score_chuva = _clamp((chuva_mm / 20.0) * 100.0)
    score_umidade = _clamp(umidade_pct)
    return _clamp(0.6 * score_chuva + 0.4 * score_umidade)


def _score_historico(tendencia_cm):
    """tendencia_cm: variação de altura entre as últimas medições (positivo =
    crescendo). None quando não há histórico suficiente."""
    if tendencia_cm is None:
        return 30.0  # neutro-baixo: sem dado, não assume urgência
    return _clamp(50.0 + tendencia_cm * 5.0)


def _classificar(indice):
    if indice >= 75:
        return "Intervenção", "#d32f2f"
    if indice >= 50:
        return "Alta prioridade", "#f57c00"
    if indice >= 25:
        return "Monitorar", "#fbc02d"
    return "Normal", "#2e7d32"


def calcular_prioridade(
    altura_cm=None,
    cobertura_pct=None,
    crescimento_cm_dia=None,
    criticidade_local=None,
    distancia_rocada_km=None,
    chuva_mm=None,
    umidade_pct=None,
    tendencia_historica_cm=None,
    pesos=None,
) -> ResultadoPrioridade:
    pesos = pesos or PESOS_PADRAO

    fatores = {
        "altura": _score_altura(altura_cm),
        "cobertura": _score_cobertura(cobertura_pct),
        "crescimento": _score_crescimento(crescimento_cm_dia),
        "localizacao": _score_localizacao(criticidade_local),
        "proximidade_rocada": _score_proximidade_rocada(distancia_rocada_km),
        "clima": _score_clima(chuva_mm, umidade_pct),
        "historico": _score_historico(tendencia_historica_cm),
    }

    soma_pesos = sum(pesos.values()) or 1
    contribuicoes = {
        chave: (fatores[chave] * pesos.get(chave, 0) / soma_pesos) for chave in fatores
    }
    indice = round(sum(contribuicoes.values()), 1)

    nivel, cor = _classificar(indice)

    return ResultadoPrioridade(
        indice=indice,
        nivel=nivel,
        cor=cor,
        fatores={k: round(v, 1) for k, v in fatores.items()},
        contribuicoes={k: round(v, 1) for k, v in contribuicoes.items()},
    )
