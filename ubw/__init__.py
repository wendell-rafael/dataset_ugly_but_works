"""Pacote de suporte do experimento UBW (Ugly But It Works).

Contém as definições compartilhadas por todos os scripts de coleta e análise:
léxico (Seção 3.2 do plano), schema de coleta (Tabela 3.5), critérios de
inclusão (Seção 2.2/2.4) e o cliente HTTP para a API do GitHub.

Manter essas definições centralizadas evita divergência entre os scripts,
o que seria metodologicamente grave já que o léxico é "fechado" após o
piloto (Seção 3.1) e precisa ser idêntico em todas as etapas da coleta.
"""
