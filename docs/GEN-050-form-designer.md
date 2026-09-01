# GEN-050 — Form Designer

## Objetivo

Criar um designer visual de formulários no DjangoForge capaz de configurar, por entidade, como os formulários CRUD serão apresentados no sistema gerado, sem alterar os modelos de dados existentes e sem quebrar o fluxo validado das GEN-047 a GEN-049.

A GEN-050 atua na camada de apresentação e geração de formulários. Ela não substitui o Model Designer e não altera a definição estrutural dos campos do banco.

## Princípios

1. Partir exclusivamente do baseline validado da GEN-049.
2. A entidade e seus campos continuam sendo definidos pelo Model Designer.
3. O Form Designer configura apresentação, organização e comportamento de formulário.
4. Configuração ausente deve manter o comportamento legado atual.
5. Nenhuma migração de banco é necessária nesta GEN; a configuração deve permanecer no contrato JSON do rascunho.
6. O runtime gerado deve reproduzir fielmente a configuração definida no designer.
7. Nenhuma regra arbitrária de Python, JavaScript ou template será aceita como configuração.
8. Alterações nesta GEN não podem modificar Dashboard Designer, Data Engine, Analytics, Runtime Agent, Release Manager ou Environment Manager.

## Escopo incluído

### Seleção de entidade

O usuário escolhe a entidade cujo formulário deseja configurar.

### Ordem dos campos

Permitir ordenar visualmente os campos do formulário.

### Visibilidade

Cada campo poderá ser configurado como:

- visível no formulário;
- oculto no formulário;
- somente leitura.

Campos não editáveis definidos pelo próprio modelo continuam respeitando as restrições do Django.

### Layout em grade

O formulário utilizará grade responsiva de 12 colunas.

Cada campo terá largura configurável:

- 3 colunas;
- 4 colunas;
- 6 colunas;
- 8 colunas;
- 12 colunas.

O designer deve reorganizar automaticamente campos quando a soma ultrapassar 12 colunas na linha.

### Seções

Permitir organizar campos em seções visuais com:

- identificador estável;
- título;
- descrição opcional;
- ordem;
- campos associados.

Campos sem seção permanecem em uma seção padrão.

### Aparência por campo

Configurações permitidas:

- label customizado;
- placeholder;
- help text visual;
- largura na grade;
- somente leitura;
- visível/oculto.

O Form Designer não altera `verbose_name`, `help_text`, `blank`, `null`, `unique` ou qualquer metadado estrutural do model.

### Tipo visual do controle

O controle padrão é inferido do tipo Django do campo. Quando compatível, o designer poderá selecionar uma variante visual segura.

Variantes previstas nesta GEN:

- text;
- textarea;
- number;
- date;
- datetime;
- checkbox;
- select.

A variante deve ser validada contra o tipo do campo. Exemplo: não permitir `checkbox` para um DecimalField.

### Preview

O designer terá modo Preview sem ferramentas de edição, permitindo visualizar o formulário final antes de salvar.

Preview não persiste estado adicional.

### Persistência

A configuração será armazenada no rascunho `VersaoGeracao.numero = 0`, dentro de `estrutura_json`, sem migration.

Contrato sugerido:

```json
{
  "forms": {
    "Pedido": {
      "title": "Cadastro de Pedido",
      "sections": [
        {
          "id": "principal",
          "title": "Dados principais",
          "description": "",
          "order": 0
        }
      ],
      "fields": [
        {
          "name": "descricao",
          "order": 0,
          "section": "principal",
          "visible": true,
          "readonly": false,
          "width": 12,
          "label": "Descrição",
          "placeholder": "Informe a descrição",
          "help_text": "",
          "widget": "textarea"
        }
      ]
    }
  }
}
```

## Normalização e retrocompatibilidade

Configuração ausente para uma entidade deve gerar automaticamente um formulário padrão com:

- campos editáveis atuais da entidade;
- ordem original dos campos;
- largura 12;
- labels provenientes do metadata atual;
- widget inferido pelo tipo;
- sem seções customizadas;
- sem campos ocultos adicionais.

Campos novos adicionados posteriormente ao modelo devem aparecer no formulário padrão mesmo que ainda não exista configuração explícita para eles. Quando uma configuração já existir, a normalização deverá incorporar campos novos sem destruir personalizações existentes.

Campos removidos do modelo devem ser ignorados pelo Form Designer e pelo gerador, sem quebrar a configuração inteira.

## Validação

A camada de contrato deve rejeitar:

- entidade inexistente;
- campo inexistente quando recebido em atualização direta;
- IDs de seção duplicados;
- seção inexistente referenciada por campo;
- largura fora de `3, 4, 6, 8, 12`;
- widget incompatível com o tipo de campo;
- valores que não sejam booleanos em `visible` e `readonly`;
- nomes inseguros contendo lookup ou caminho arbitrário.

Erros devem ser estruturados e legíveis pela interface.

## Runtime gerado

O sistema gerado deverá materializar a configuração usando Django Forms/ModelForm, mantendo validação de domínio no Django.

A geração deverá controlar:

- ordem dos campos;
- campos excluídos/ocultos;
- atributos readonly quando aplicável;
- widgets seguros;
- labels;
- placeholders;
- help text visual;
- classes/atributos necessários ao grid de 12 colunas;
- seções no template gerado.

Não será permitido gerar validações de negócio arbitrárias nesta GEN.

## Fora do escopo

- regras condicionais entre campos;
- mostrar/ocultar campo baseado em outro campo;
- fórmulas;
- campos calculados;
- máscaras complexas;
- autocomplete remoto;
- upload avançado;
- validações de negócio customizadas;
- workflows;
- permissões por campo;
- CRUD Designer completo;
- Business Rules Engine;
- geração de JavaScript arbitrário.

Esses itens pertencem a GENs posteriores, principalmente GEN-051 e GEN-052.

## Fases

### GEN-050.1 — Form Contract

- normalização do contrato;
- defaults retrocompatíveis;
- metadata de campo;
- validação segura;
- testes unitários.

### GEN-050.2 — Form Designer UI

- seleção de entidade;
- ordenação de campos;
- largura 12 colunas;
- propriedades por campo;
- seções;
- Preview;
- persistência no draft;
- testes de regressão da interface.

### GEN-050.3 — Generated Forms

- integração com gerador;
- ModelForm configurado;
- template com seções e grid;
- labels/placeholders/help text;
- visible/readonly;
- widgets compatíveis;
- testes do código gerado.

### GEN-050.4 — Regressão e validação manual

- executar suíte completa;
- garantir ausência de migration;
- validar retrocompatibilidade;
- validar sistema gerado;
- validar criação e edição;
- validar Preview;
- promover somente após validação manual.

## Critérios de aceite

1. Formulários legados continuam sendo gerados quando não existe configuração de Form Designer.
2. O usuário consegue reorganizar campos visualmente.
3. O usuário consegue configurar largura dos campos em grid de 12 colunas.
4. O usuário consegue criar seções e associar campos.
5. O usuário consegue alterar label, placeholder e help text visual.
6. O usuário consegue ocultar ou marcar campo como somente leitura dentro das regras permitidas.
7. Widgets incompatíveis são rejeitados.
8. Preview não altera a configuração persistida.
9. Salvar/recarregar preserva a configuração.
10. O sistema gerado reproduz a ordem, seções e apresentação configuradas.
11. Campos novos no modelo são incorporados sem destruir configuração existente.
12. Campos removidos não quebram o formulário.
13. Não existe migration nova para a GEN-050.
14. Todos os testes anteriores continuam passando.
15. A GEN-050 só pode ser promovida após validação automatizada e manual.
