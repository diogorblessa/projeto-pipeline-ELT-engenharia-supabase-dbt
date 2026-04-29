# Guia de criação de commits para este projeto.

## Objetivo

Padronizar mensagens de commit para manter o histórico do Git claro, rastreável e fácil de revisar.

## Regra principal

- Sempre use commits semânticos em português do Brasil, com acentuação correta.
- Cada commit deve representar uma única mudança lógica e significativa.
- Evite commits genéricos como `update`, `ajustes`, `correções`, `mudanças`, `wip` ou `alterações gerais`.
- Prefira commits pequenos, objetivos e fáceis de revisar.
- Sempre que possível, cada commit deve ser executável e testável por si só.
- Não misture alterações sem relação direta no mesmo commit.
- Antes de commitar, revise os arquivos alterados e confirme que todos pertencem ao mesmo objetivo.

## Tempo verbal

- Use o presente no imperativo.
- Escreva como se estivesse dando uma ordem ao código.
- Prefira verbos como `adiciona`, `corrige`, `atualiza`, `remove`, `ajusta`, `simplifica`, `organiza`, `refatora`, `documenta`, `configura`, `valida`, `padroniza` e `separa`.

Exemplos corretos:

```text
feat: adiciona função de exportação
fix: corrige erro na conexão com MongoDB em ambientes Linux
docs: atualiza instruções de configuração
chore(dbt): permite versionar profiles.yml
refactor(extract): simplifica leitura de variáveis de ambiente
```

Exemplos incorretos:

```text
feat: adicionado função de exportação
feat: adicionando função de exportação
update
ajustes
correções gerais
```

## Tipos permitidos

Use os tipos abaixo para organizar o histórico de commits:

| Tipo | Quando usar |
|---|---|
| `feat` | Adição de nova funcionalidade ou capacidade do projeto, incluindo nova funcionalidade em pipeline, script ETL, modelo dbt, API ou aplicação. |
| `fix` | Correção de erro, falha ou comportamento inesperado, incluindo erro de leitura, escrita, conexão, query incorreta ou falha em pipeline. |
| `docs` | Alteração em documentação, README, guias, comentários, notebooks explicativos ou instruções técnicas. |
| `refactor` | Reestruturação interna do código, etapa ETL, transformação, modelo ou consulta sem mudar o comportamento esperado. |
| `test` | Criação, correção ou melhoria de testes, incluindo testes de pipeline, dbt, qualidade de dados, schemas e validações. |
| `chore` | Tarefa de manutenção, organização ou configuração sem impacto direto na regra de negócio. |
| `build` | Alterações em dependências, Docker, empacotamento, ambiente de build ou ferramentas de projeto. |
| `ci` | Alterações em pipelines de integração contínua, GitHub Actions, deploy, execução automatizada, agendamento ou orquestração. |
| `perf` | Melhoria de desempenho sem alterar o comportamento funcional, como otimização de leitura, processamento em chunks, queries ou transformações. |
| `style` | Ajustes de formatação, lint, espaçamento, nomes ou estilo sem alterar lógica. |
| `revert` | Reversão de uma alteração anterior. |
| `data` | Modificações em datasets, seeds, dados de teste, mocks, amostras, cargas manuais ou remoção de dados versionados. |
| `schema` | Mudanças em estrutura de dados, schemas, tabelas, campos, constraints, tipos de colunas ou contratos de dados. |
| `query` | Alterações em queries SQL, filtros, joins, CTEs, agregações ou regras de consulta. |
| `config` | Alterações em arquivos de configuração, paths, parâmetros, arquivos `.yml`, `.toml`, `.json` ou configurações de ferramentas. |
| `env` | Criação ou alteração de variáveis de ambiente, arquivos `.env.example`, conexões com banco ou configurações sensíveis sem expor credenciais reais. |
| `pipeline` | Criação ou ajuste no fluxo completo do pipeline, incluindo ingestão, carga, transformação, validação e orquestração. |
| `visual` | Criação ou ajuste de gráficos, dashboards, relatórios, visualizações analíticas ou logs visuais. |
| `monitor` | Adição ou ajuste de logs, alertas, verificações de status, auditoria, observabilidade ou monitoramento de pipeline. |


## Escopo

Use escopo quando ele deixar claro qual parte do projeto foi alterada.

Formato:

```text
tipo(escopo): descrição
```

Exemplos:

```text
feat(extract): adiciona extração de dados da API
fix(load): corrige gravação de dados no Supabase
feat(dbt): adiciona modelos da camada silver
test(dbt): adiciona testes de unicidade e nulos
build(docker): adiciona serviços de extract e dbt
docs(readme): atualiza instruções de instalação
chore(env): organiza variáveis de ambiente
```

## Corpo do commit

O corpo do commit deve conter uma descrição explicativa com até 3 bullet points curtos.

Regras:

- Use `-` no início de cada bullet point.
- Use até 3 bullet points.
- Explique objetivamente o que foi alterado.
- Quando relevante, explique também o motivo da alteração.
- Não repita exatamente a mesma informação do título.
- Não invente impacto que não foi validado.
- Não mencione segredos, chaves, tokens, senhas, credenciais ou valores sensíveis.

Exemplo:

```bash
git commit -m "chore: permite versionar transform/profiles.yml e mantém docs/ ignorado" \
-m "- Remove a regra global profiles.yml do .gitignore.
- Versiona transform/profiles.yml, que não contém segredos e lê variáveis via env_var().
- Mantém docs/ no .gitignore, pois especificações e planos ficam apenas locais."
```

## Segurança

Antes de commitar, verifique se não há:

- Arquivos `.env` com valores reais.
- Chaves de API.
- Tokens.
- Senhas.
- Credenciais de banco.
- Arquivos temporários.
- Arquivos locais ignorados.
- Logs sensíveis.
- Dados pessoais ou dados de clientes.

Nunca inclua informações sensíveis no título, no corpo ou nos arquivos do commit.

## Checklist antes do commit

Antes de executar `git commit`, revise:

```bash
git status
git diff
```

Confirme que:

- O commit contém apenas uma mudança lógica.
- Os arquivos alterados pertencem ao mesmo objetivo.
- A mensagem está em português do Brasil.
- O título está no presente imperativo.
- O tipo semântico está correto.
- O escopo foi usado quando ajuda a dar contexto.
- O corpo tem até 3 bullet points curtos.
- Nenhum segredo ou arquivo sensível será versionado.
- O commit é pequeno o suficiente para ser revisado com facilidade.

## Exemplos ruins

```bash
git commit -m "update"
```

```bash
git commit -m "ajustes"
```

```bash
git commit -m "feat: adicionando função de exportação"
```

Problemas:

- Não informam claramente o que foi alterado.
- Não usam o tipo semântico corretamente.
- Não seguem o presente imperativo.
- Dificultam revisão, histórico, rastreabilidade e geração de changelog.

## Exemplos melhores

```bash
git commit -m "fix: corrige conexão com MongoDB em ambientes Linux" \
-m "- Ajusta a configuração usada na conexão com o banco.
- Corrige falha identificada em ambientes Linux.
- Mantém a alteração isolada da lógica de negócio."
```

```bash
git commit -m "feat: adiciona função de exportação" \
-m "- Cria função para exportar dados processados.
- Mantém a lógica separada do fluxo principal.
- Facilita o reaproveitamento em outras etapas do pipeline."
```
