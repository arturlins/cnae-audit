"""Ferramentas autorais expostas ao agente Verificador de CNAE."""

from agente.ferramentas.enquadramento import validar_enquadramento
from agente.ferramentas.ibge import consultar_cnae_ibge

__all__ = ["consultar_cnae_ibge", "validar_enquadramento"]
