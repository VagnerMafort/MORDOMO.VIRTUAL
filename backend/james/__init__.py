"""
JAMES AGENCY — Autonomous Marketing Intelligence System
Arquitetura consolidada do PDF "Agência de marketing automação (arquitetura)".

Objetivo do sistema:
  coletar → normalizar → baseline → detectar anomalias → priorizar → orquestrar
  → governar objetivo → validar guardrails → executar → verificar → avaliar
  → aprender → arquivar → reportar

Componentes:
  - 1 Orquestrador Central (orchestrator.py)
  - 24 Agentes Especializados (agents/*.py)
  - 14 Camadas Operacionais (layers.py)
  - 8 Squads (agrupamento lógico)
  - 6 Fases de implementação (Foundation, Decision, Execution, Sales, Learning, Reporting)
"""
