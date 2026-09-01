# GEN-046 — Health & Monitoring

## Objetivo

Transformar os snapshots pontuais do Runtime Agent da GEN-045 em uma visão operacional consolidada da saúde dos ambientes de cada sistema.

## Escopo incluído

- painel `/sistemas/<id>/health/`;
- estados `HEALTHY`, `DEGRADED`, `OFFLINE` e `UNKNOWN`;
- detecção de drift entre release desejada e observada;
- migrations pendentes como sinal de degradação;
- latência da consulta ao Runtime Agent;
- latência média histórica;
- último snapshot por ambiente;
- histórico imutável de verificações;
- visão consolidada dos quatro ambientes;
- proteção por proprietário do sistema;
- testes de regressão dos estados de saúde e histórico.

## Fora de escopo

- deploy remoto;
- execução remota de migrations;
- SSH;
- Docker remoto;
- restart automático;
- alertas assíncronos;
- polling automático;
- retenção/expurgo de histórico;
- métricas de CPU, memória ou disco.

## Regras de saúde

### UNKNOWN

Ambiente ainda sem snapshot de Runtime Agent.

### OFFLINE

Última consulta não conseguiu obter um payload válido do Runtime Agent.

### DEGRADED

O Agent está online, mas pelo menos uma condição operacional exige atenção:

- `status` diferente de `ok`;
- migrations pendentes maiores que zero;
- release observada diferente da release desejada.

### HEALTHY

Agent online, status `ok`, nenhuma migration pendente e sem drift de release.

## Persistência

`RuntimeSnapshot` continua representando o último estado conhecido e recebe `latency_ms`.

`RuntimeCheck` registra cada consulta de forma histórica com:

- ambiente;
- online;
- health;
- release observada;
- migrations pendentes;
- latência;
- erro;
- payload;
- instante da verificação.

## Migration

`0013_health_monitoring.py`

## Critérios de aceite

1. suíte anterior continua passando;
2. novos testes da GEN-046 passam;
3. `makemigrations --check --dry-run` não encontra alterações;
4. painel é owner-only;
5. estados HEALTHY/DEGRADED/OFFLINE/UNKNOWN são classificados corretamente;
6. drift degrada o ambiente;
7. migrations pendentes degradam o ambiente;
8. cada consulta gera histórico sem sobrescrever verificações anteriores;
9. falha de comunicação não gera erro 500;
10. nenhum deploy ou ação remota é executado.
