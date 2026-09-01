# Baseline de Recuperação

Esta branch foi criada a partir do commit `f2a49c29b728c3f3d26aa20b5eca07c7a1cad5d3` (`gen-036-dashboard-field-metadata`), que corresponde ao estado salvo no stash local `backup-local-antes-gen038`.

Objetivo desta baseline:

- preservar o Model Designer com configurações avançadas de campos e relacionamentos;
- recuperar o banco SQLite populado a partir do stash local;
- validar o estado funcional antes de qualquer nova evolução;
- proibir evolução posterior sem partir desta baseline validada.

Nenhuma funcionalidade nova deve ser adicionada nesta branch antes da validação local do banco e da suíte de testes.
