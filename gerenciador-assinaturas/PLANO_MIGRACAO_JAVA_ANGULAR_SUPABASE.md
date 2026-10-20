# Plano completo de migração — Licenzy para Java, Angular e Supabase

## 1. Objetivo

Este documento descreve como migrar o Licenzy, hoje implementado em Python/Streamlit e Google Sheets, para uma aplicação web com:

- **Frontend:** Angular;
- **Backend:** Java com Spring Boot;
- **Banco, autenticação e arquivos:** Supabase;
- **Banco relacional:** PostgreSQL gerenciado pelo Supabase.

A meta é preservar as funcionalidades e regras já existentes, substituir a planilha por um modelo relacional consistente, melhorar segurança, concorrência, auditoria, testes e capacidade de evolução, e executar a troca sem perda de dados.

> Decisão recomendada: o Angular nunca deve acessar tabelas de negócio diretamente. O frontend autentica no Supabase e chama a API Java. A API valida o JWT e concentra autorização, regras, transações, relatórios e auditoria. O acesso direto ao Supabase pelo Angular deve ficar limitado à autenticação e, se necessário, a URLs assinadas de arquivos.

---

## 2. Diagnóstico do sistema atual

### 2.1 Tecnologias atuais

| Área | Implementação atual |
|---|---|
| Interface | Streamlit 1.66, CSS próprio |
| Linguagem | Python |
| Dados | Google Sheets; Excel local apenas em desenvolvimento/testes |
| Cálculos | pandas |
| Gráficos | Plotly |
| PDF | fpdf2; Plotly/Kaleido ou matplotlib |
| Excel | openpyxl |
| Integração Google | gspread e conta de serviço |
| Testes | pytest, mocks do Sheets e Playwright |
| Autenticação | senha única da aplicação; bloqueio por IP após cinco erros |
| Auditoria externa | Apps Script para alterações feitas na planilha |

### 2.2 Módulos e telas atuais

| Módulo | Capacidades que precisam ser preservadas |
|---|---|
| Login | Impedir acesso anônimo e encerrar sessão |
| Dashboard | Indicadores, gasto mensal/anual, vencimentos, gráficos por categoria/status, evolução e maiores custos |
| Assinaturas | Listar, buscar, filtrar, criar, editar, excluir, vincular pessoas, ver histórico e registrar pagamento |
| Pessoas | Listar, buscar por nome/e-mail/departamento, criar, editar, excluir, vincular assinaturas e calcular custo individual |
| Projetos | CRUD, concluir projeto, vincular assinaturas e ratear custos entre projetos ativos |
| Histórico | Filtros por período, evento, origem e assinatura; tabela, linha do tempo e exportação |
| Pendências | Detectar dados inválidos da planilha e abrir correção no aplicativo |
| Relatórios | Resumo PDF, assinaturas por categoria em Excel, vencimentos PDF, colaboradores/departamentos em PDF e Excel |

### 2.3 Fonte de verdade atual

As abas atuais são:

- `Assinaturas`;
- `Funcionários`;
- `Histórico`;
- `Listas`;
- `Projetos`;
- `Uso por projeto`.

Há uma fragilidade estrutural importante: a relação pessoa–assinatura é guardada como uma lista de nomes separada por vírgulas na coluna `Funcionários.Assinaturas`. A migração deve transformar isso em uma tabela de associação por identificadores imutáveis.

### 2.4 Regras de negócio encontradas no código

#### Assinaturas

- Nome obrigatório, único sem diferenciar maiúsculas/acentos e sem vírgula no sistema atual.
- Categoria, plano e status obrigatórios.
- Valor estritamente maior que zero.
- Vencimento obrigatório, exceto para plano vitalício.
- Logo opcional e, atualmente, validado como URL HTTP/HTTPS.
- Uma assinatura precisa ter pelo menos uma pessoa vinculada no cadastro atual.
- Status padrão disponível: `Ativa`, `Em teste`, `Pausada`, `Cancelada`.
- Planos: mensal, trimestral, semestral, anual e vitalício.
- Apenas assinaturas ativas entram no gasto recorrente.
- Custo mensal: mensal = valor; trimestral = valor/3; semestral = valor/6; anual = valor/12; vitalício = zero no recorrente.
- Gasto anual projetado = gasto mensal × 12.

#### Pagamento e vencimento

- Registrar pagamento altera somente o vencimento.
- O próximo vencimento parte do vencimento armazenado, não da data atual.
- Cada confirmação avança somente um ciclo.
- Mensal avança um mês e anual avança um ano.
- O dia é preservado quando possível; caso contrário usa-se o último dia do mês.
- Vitalício e demais planos atualmente não aceitos pela função de pagamento devem ser rejeitados de forma explícita.
- A operação registra evento `Pagamento registrado`, campo `Vencimento`, valor anterior e novo.

> Ponto para decisão antes da implementação: planos trimestral e semestral existem e têm custo recorrente, mas o fluxo atual de pagamento só aceita mensal e anual. A primeira versão migrada deve manter esse comportamento para equivalência. Uma evolução posterior pode habilitá-los mediante requisito aprovado.

#### Alertas

- Canceladas não geram alerta.
- Vencida ou até 7 dias: vermelho/urgente.
- De 8 a 30 dias: amarelo/atenção.
- Acima de 30 dias: verde/em dia.

#### Pessoas e rateio

- Nome, e-mail e departamento são obrigatórios.
- E-mail deve ter formato válido, ser normalizado para minúsculas e ser único.
- O custo de cada assinatura é dividido igualmente entre as pessoas vinculadas.
- O custo por departamento é a soma das partes das pessoas do departamento.

#### Projetos e rateio

- Nome do projeto é obrigatório e único.
- Status do projeto é obrigatório.
- Pelo menos uma assinatura deve ser vinculada na regra atual.
- O custo de cada assinatura é dividido igualmente entre os usos/projetos ativos que a utilizam.
- Concluir um projeto o retira do rateio ativo.
- Excluir uma assinatura remove também seus vínculos com projetos.

#### Concorrência e histórico

- O código atual relê o registro antes de atualizar e recusa a gravação se os dados mudaram.
- Criação, alteração, exclusão, renomeação, vínculos, pagamento e operações de projeto são auditados.
- O banco novo deve tornar atualização do registro e criação da auditoria uma única transação.

### 2.5 Segurança: ação imediata

Foi encontrado no workspace um `.streamlit/secrets.toml` com senha do sistema e chave privada de uma conta de serviço Google. Antes de qualquer migração:

1. revogar/excluir a chave exposta no Google Cloud;
2. gerar outra chave somente se o sistema legado ainda precisar funcionar;
3. trocar a senha atual da aplicação;
4. confirmar que `secrets.toml` está ignorado e nunca entrou no histórico Git;
5. se já entrou no histórico, removê-lo com ferramenta própria e tratar a chave como comprometida mesmo após a remoção;
6. usar variáveis de ambiente ou cofre de segredos no backend novo;
7. nunca colocar `service_role`, senha do banco ou segredo JWT no Angular.

---

## 3. Arquitetura de destino

```text
Navegador
  └─ Angular SPA
       ├─ login/renovação de sessão → Supabase Auth
       └─ chamadas HTTPS com Bearer JWT → API Java/Spring Boot
                                               ├─ valida JWT e papéis
                                               ├─ executa regras/transações
                                               ├─ gera PDF/Excel
                                               └─ PostgreSQL/Supabase
                                                     ├─ tabelas e views
                                                     ├─ auditoria
                                                     ├─ RLS como defesa adicional
                                                     └─ Storage para logos/arquivos
```

### 3.1 Stack recomendada

- Java 21 LTS;
- Spring Boot 3.x suportado no momento da execução;
- Spring Web, Validation, Security, Data JPA;
- Flyway para versionamento do banco;
- PostgreSQL driver e HikariCP;
- springdoc-openapi para contrato e Swagger UI;
- Apache POI para Excel;
- OpenPDF ou OpenHTMLToPDF para PDF;
- Angular em versão LTS/suportada no início do desenvolvimento;
- Angular Material ou outro design system único;
- Supabase Auth, PostgreSQL e Storage;
- Testcontainers PostgreSQL, JUnit 5, Mockito e REST Assured/MockMvc;
- Vitest/Jasmine e Playwright/Cypress no frontend.

Não fixar versões neste documento de planejamento: escolher versões compatíveis e suportadas no início da implementação, registrá-las no `pom.xml`, `package-lock.json` e ADR técnico, e atualizar somente com testes.

### 3.2 Responsabilidades

| Camada | Responsabilidade |
|---|---|
| Angular | Navegação, formulários, tabelas, filtros, gráficos, acessibilidade, confirmação e tratamento visual de erros |
| Spring Boot | Regras, autorização, validação final, concorrência, transações, auditoria, consultas agregadas e relatórios |
| Supabase Auth | Identidade, recuperação de senha, sessões e tokens JWT |
| PostgreSQL | Integridade, relacionamentos, índices, constraints e persistência |
| Supabase Storage | Logos enviados e artefatos que precisem permanecer armazenados |

### 3.3 Organização sugerida do monorepo

```text
licenzy/
├── backend/
│   ├── pom.xml
│   └── src/
│       ├── main/java/br/org/recocavo/licenzy/
│       │   ├── config/
│       │   ├── security/
│       │   ├── common/
│       │   ├── subscription/
│       │   ├── person/
│       │   ├── project/
│       │   ├── audit/
│       │   ├── dashboard/
│       │   └── report/
│       └── main/resources/db/migration/
├── frontend/
│   └── src/app/
│       ├── core/
│       ├── shared/
│       ├── auth/
│       ├── dashboard/
│       ├── subscriptions/
│       ├── people/
│       ├── projects/
│       ├── history/
│       └── reports/
├── migration/
│   ├── exports/          # nunca versionar dados reais
│   ├── scripts/
│   └── reconciliation/
└── docs/
```

---

## 4. Modelo de dados proposto

### 4.1 Entidades

| Tabela | Finalidade |
|---|---|
| `organizations` | Preparar isolamento por organização, mesmo que inicialmente exista apenas uma |
| `profiles` | Complementar usuário do Supabase Auth com nome, papel e organização |
| `categories` | Categorias configuráveis |
| `departments` | Departamentos configuráveis |
| `subscriptions` | Assinaturas e seus dados financeiros |
| `people` | Colaboradores/pessoas |
| `person_subscriptions` | Relação N:N entre pessoas e assinaturas |
| `projects` | Projetos |
| `project_subscriptions` | Uso N:N de assinaturas em projetos, com metadados |
| `audit_events` | Histórico imutável de operações |

### 4.2 DDL inicial de referência

O SQL abaixo é uma base para a primeira migration Flyway. Nomes técnicos ficam em inglês; textos de interface permanecem em português.

```sql
create extension if not exists pgcrypto;

create table organizations (
    id uuid primary key default gen_random_uuid(),
    name varchar(160) not null,
    created_at timestamptz not null default now()
);

create type app_role as enum ('ADMIN', 'MANAGER', 'VIEWER');
create type subscription_plan as enum ('MONTHLY', 'QUARTERLY', 'SEMIANNUAL', 'ANNUAL', 'LIFETIME');
create type subscription_status as enum ('ACTIVE', 'TRIAL', 'PAUSED', 'CANCELED');
create type project_status as enum ('PLANNED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'CANCELED');
create type usage_status as enum ('ACTIVE', 'INACTIVE');

create table profiles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    organization_id uuid not null references organizations(id),
    full_name varchar(160) not null,
    role app_role not null default 'VIEWER',
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table categories (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id),
    name varchar(100) not null,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    unique (organization_id, name)
);

create table departments (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id),
    name varchar(100) not null,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    unique (organization_id, name)
);

create table subscriptions (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id),
    legacy_id varchar(30),
    name varchar(160) not null,
    logo_url text,
    category_id uuid not null references categories(id),
    plan subscription_plan not null,
    amount numeric(14,2) not null check (amount > 0),
    due_date date,
    status subscription_status not null,
    version bigint not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by uuid references auth.users(id),
    updated_by uuid references auth.users(id),
    check (plan = 'LIFETIME' or due_date is not null)
);

create unique index uq_subscriptions_name_ci
    on subscriptions (organization_id, lower(name));
create index ix_subscriptions_due_date on subscriptions (organization_id, due_date);
create index ix_subscriptions_status on subscriptions (organization_id, status);

create table people (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id),
    legacy_id varchar(30),
    full_name varchar(160) not null,
    email varchar(254) not null,
    department_id uuid not null references departments(id),
    job_title varchar(120),
    active boolean not null default true,
    version bigint not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index uq_people_email_ci on people (organization_id, lower(email));
create index ix_people_department on people (organization_id, department_id);

create table person_subscriptions (
    person_id uuid not null references people(id) on delete cascade,
    subscription_id uuid not null references subscriptions(id) on delete cascade,
    created_at timestamptz not null default now(),
    created_by uuid references auth.users(id),
    primary key (person_id, subscription_id)
);

create table projects (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id),
    legacy_id varchar(30),
    name varchar(180) not null,
    client varchar(180),
    owner_name varchar(160),
    department_id uuid references departments(id),
    start_date date,
    end_date date,
    status project_status not null,
    notes text,
    version bigint not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (end_date is null or start_date is null or end_date >= start_date)
);

create unique index uq_projects_name_ci on projects (organization_id, lower(name));

create table project_subscriptions (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id),
    legacy_id varchar(30),
    project_id uuid not null references projects(id) on delete cascade,
    subscription_id uuid not null references subscriptions(id) on delete cascade,
    purpose text,
    owner_name varchar(160),
    start_date date,
    end_date date,
    status usage_status not null default 'ACTIVE',
    notes text,
    created_at timestamptz not null default now(),
    unique (project_id, subscription_id)
);

create table audit_events (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id),
    occurred_at timestamptz not null default now(),
    actor_user_id uuid references auth.users(id),
    actor_email varchar(254),
    origin varchar(30) not null check (origin in ('APP', 'MIGRATION', 'SYSTEM')),
    entity_type varchar(50) not null,
    entity_id uuid,
    entity_name varchar(180),
    event_type varchar(80) not null,
    field_name varchar(80),
    old_value text,
    new_value text,
    metadata jsonb not null default '{}'::jsonb
);

create index ix_audit_filter
    on audit_events (organization_id, occurred_at desc, event_type);
create index ix_audit_entity
    on audit_events (organization_id, entity_type, entity_id, occurred_at desc);
```

### 4.3 Observações de modelagem

- Usar `numeric`, nunca `double`, para valores monetários.
- Persistir datas de vencimento como `date` e eventos como `timestamptz` em UTC; exibir em `America/Bahia`.
- Manter `legacy_id` durante a migração para reconciliação e rastreabilidade.
- Usar `@Version`/coluna `version` para concorrência otimista. A API recebe a versão lida e retorna HTTP `409 Conflict` quando estiver desatualizada.
- Não apagar eventos de auditoria. Restringir `UPDATE` e `DELETE` nessa tabela.
- A restrição “assinatura deve ter uma pessoa” cruza tabelas; validar na transação do serviço. Avaliar se a regra continua adequada, pois ela dificulta cadastro incremental.
- A origem `planilha` deixa de existir após a desativação do Google Sheets. Eventos históricos importados podem guardar `origin = MIGRATION` e a origem legada em `metadata`.

### 4.4 Views úteis

Criar views SQL ou projeções de consulta para:

- custo mensal normalizado por assinatura;
- quantidade de pessoas por assinatura;
- custo por pessoa;
- gasto por departamento;
- quantidade de projetos ativos por assinatura;
- custo rateado por projeto;
- vencimentos e nível de alerta.

As fórmulas podem ser SQL para consultas agregadas ou Java para domínio. A regra deve existir em um único ponto e ser coberta por testes; não duplicá-la no Angular.

---

## 5. Autenticação e autorização

### 5.1 Fluxo

1. Usuário entra com e-mail/senha ou provedor corporativo pelo Supabase Auth.
2. Angular recebe sessão e access token.
3. Um interceptor envia `Authorization: Bearer <token>` à API.
4. Spring Security valida assinatura, emissor, audiência e expiração do JWT.
5. A API carrega `profiles`, organização e papel do usuário.
6. Toda consulta filtra por `organization_id` derivado do usuário, nunca de um valor confiado do frontend.

### 5.2 Papéis sugeridos

| Papel | Permissões |
|---|---|
| `ADMIN` | Usuários, configurações, todos os cadastros, exclusões, relatórios e auditoria |
| `MANAGER` | CRUD operacional, pagamentos, projetos, relatórios e histórico |
| `VIEWER` | Consultas, dashboard e downloads permitidos; sem alteração |

### 5.3 RLS e chaves

- Habilitar RLS em tabelas expostas pela API REST do Supabase.
- Como o backend pode usar uma conexão PostgreSQL privilegiada, o filtro organizacional também deve existir obrigatoriamente nos repositórios/serviços Java.
- Se usar `service_role`, armazená-la somente no backend e preferir conexão direta/pooler do banco quando adequado.
- No Angular são públicas apenas URL do projeto e chave publicável/anon; isso não elimina a necessidade de RLS.
- Configurar CORS exclusivamente para os domínios do frontend.
- Aplicar rate limit no gateway/backend, política de senha/MFA e logs sem tokens ou dados sensíveis.

---

## 6. API REST proposta

Prefixo: `/api/v1`. Listagens devem suportar paginação, ordenação e filtros. Usar `application/problem+json` para erros.

### 6.1 Sessão e listas

| Método | Endpoint | Uso |
|---|---|---|
| GET | `/me` | Perfil, papel e organização do usuário atual |
| GET | `/categories` | Categorias ativas |
| POST/PUT | `/categories` | Administração de categorias |
| GET | `/departments` | Departamentos ativos |
| POST/PUT | `/departments` | Administração de departamentos |

### 6.2 Assinaturas

| Método | Endpoint | Uso |
|---|---|---|
| GET | `/subscriptions` | Busca/filtros/paginação |
| GET | `/subscriptions/{id}` | Detalhe, pessoas, projetos e versão |
| POST | `/subscriptions` | Cria assinatura e vínculos em transação |
| PUT | `/subscriptions/{id}` | Atualiza com concorrência otimista |
| DELETE | `/subscriptions/{id}?version=n` | Exclui com confirmação e auditoria |
| POST | `/subscriptions/{id}/payments` | Registra um pagamento e avança um ciclo |
| GET | `/subscriptions/{id}/history` | Histórico da assinatura |

Exemplo de pagamento:

```json
POST /api/v1/subscriptions/2ec.../payments
{
  "version": 4
}
```

Resposta `200`:

```json
{
  "subscriptionId": "2ec...",
  "previousDueDate": "2026-01-31",
  "newDueDate": "2026-02-28",
  "version": 5
}
```

### 6.3 Pessoas e projetos

| Método | Endpoint | Uso |
|---|---|---|
| GET/POST | `/people` | Lista/cria pessoa |
| GET/PUT/DELETE | `/people/{id}` | Detalhe/edição/exclusão |
| PUT | `/people/{id}/subscriptions` | Substitui vínculos atomicamente |
| GET/POST | `/projects` | Lista/cria projeto |
| GET/PUT/DELETE | `/projects/{id}` | Detalhe/edição/exclusão |
| POST | `/projects/{id}/complete` | Conclui projeto com auditoria |
| PUT | `/projects/{id}/subscriptions` | Substitui usos e metadados em transação |

### 6.4 Dashboard, histórico e relatórios

| Método | Endpoint | Uso |
|---|---|---|
| GET | `/dashboard?referenceDate=...` | Indicadores e datasets dos gráficos |
| GET | `/audit-events` | Período, evento, origem, entidade, pessoa e paginação |
| GET | `/reports/summary.pdf` | Resumo geral |
| GET | `/reports/by-category.xlsx` | Uma aba por categoria |
| GET | `/reports/due.pdf?days=30` | Vencimentos 30/60/90 |
| GET | `/reports/people-departments.pdf` | Pessoas/departamentos PDF |
| GET | `/reports/people-departments.xlsx` | Pessoas/departamentos Excel |

### 6.5 Erros padronizados

- `400`: formato/requisição inválida;
- `401`: sessão ausente ou expirada;
- `403`: papel insuficiente;
- `404`: registro inexistente;
- `409`: nome/e-mail duplicado ou versão concorrente;
- `422`: regra de negócio violada;
- `500`: erro inesperado com `traceId`, sem stack trace para o cliente.

---

## 7. Backend Java

### 7.1 Padrão interno

Organizar por funcionalidade, não apenas por tipo técnico. Cada módulo pode conter:

- `Controller`: contrato HTTP;
- `Request`/`Response`: DTOs, sem expor entidades JPA;
- `Service`: caso de uso, transação, autorização e auditoria;
- `Entity`/`Repository`: persistência;
- `Mapper`: conversão explícita;
- `Specification` ou consultas dedicadas para filtros.

### 7.2 Transações essenciais

Devem ser atômicas:

- criar/editar assinatura + substituir pessoas vinculadas + eventos;
- renomear assinatura (no modelo novo os vínculos usam UUID e não exigem propagação);
- excluir assinatura + cascatas + evento final;
- registrar pagamento + evento;
- criar/editar projeto + usos + eventos;
- concluir projeto + evento;
- criar/editar pessoa + vínculos + eventos.

### 7.3 Concorrência

Substituir a comparação de todas as células por concorrência otimista:

- entidade com `@Version`;
- frontend envia `version` recebida;
- atualização SQL só funciona se a versão ainda for a mesma;
- `OptimisticLockException` vira `409` com mensagem para recarregar;
- não fazer “last write wins” silencioso.

### 7.4 Auditoria

Usar um serviço explícito de domínio dentro da mesma transação. Registrar:

- instante UTC;
- usuário/e-mail;
- organização;
- entidade, ID e nome exibível;
- tipo de evento;
- campo, valor anterior e novo quando aplicável;
- metadados úteis, sem dados secretos.

Triggers de banco podem complementar alterações fora da API, mas não substituem os eventos semânticos do serviço (`Pagamento registrado`, `Projeto concluído`, etc.). Em produção, negar escrita humana direta nas tabelas.

### 7.5 Relatórios

- O backend recebe filtros validados e busca os dados da organização do usuário.
- PDF: usar template HTML/CSS renderizado ou biblioteca PDF; incluir cabeçalho, data/hora, fuso e paginação.
- Excel: Apache POI, filtros, cabeçalho congelado, datas e moedas tipadas, nomes de abas sanitizados e únicos.
- Para relatórios grandes, evoluir para job assíncrono e Storage; para o volume atual, resposta síncrona deve ser suficiente.

---

## 8. Frontend Angular

### 8.1 Rotas

```text
/login
/dashboard
/assinaturas
/assinaturas/:id
/pessoas
/pessoas/:id
/projetos
/projetos/:id
/relatorios
/historico
/configuracoes       (ADMIN)
```

### 8.2 Estrutura e padrões

- Componentes standalone e lazy loading por área.
- Reactive Forms tipados.
- Guard de autenticação e guard por papel.
- Interceptor de token, renovação e erros `401/403/409`.
- Signals ou store somente onde houver estado compartilhado real.
- Datas enviadas em ISO (`yyyy-MM-dd`) e formatadas em `pt-BR`.
- Valores monetários exibidos em BRL, mas enviados como números decimais.
- Tabelas com paginação server-side, ordenação, busca com debounce e estado na URL.
- Diálogos de confirmação para exclusão, conclusão e pagamento.
- Toasts acessíveis; erros de campo associados ao controle.
- Tema claro/escuro e layout responsivo equivalentes ao sistema atual.

### 8.3 Telas e componentes

#### Dashboard

- cards: ativas, gasto mensal, gasto anual, vencendo em 30 dias e colaboradores;
- donut por categoria;
- gráfico por status;
- evolução em 12 meses;
- top 5 por custo mensal;
- lista de alertas e ação de atualizar.

#### Assinaturas

- filtros por texto, status, categoria e plano;
- tabela paginada e detalhe lateral/página;
- formulário com pessoas vinculadas;
- ações: nova, editar, excluir, histórico e marcar como pago;
- pagamento mostra nome, plano, vencimento atual e próximo antes de confirmar;
- botão indisponível para plano não suportado, data inválida ou usuário sem permissão.

#### Pessoas

- pesquisa por nome, e-mail e departamento;
- formulário e seleção de assinaturas;
- detalhe com parte mensal por assinatura e total da pessoa.

#### Projetos

- lista, busca, métricas, CRUD e concluir;
- seleção de assinaturas com finalidade, responsável, período, status e observações;
- detalhe com custo rateado.

#### Histórico e relatórios

- filtros persistidos na URL;
- tabela paginada e linha do tempo;
- download como `Blob`, extraindo nome do arquivo do header;
- progresso e mensagens de erro na geração.

### 8.4 Pendências na nova solução

A tela de pendências perde grande parte da função porque constraints e FKs impedem dados inválidos. Recomenda-se substituí-la por uma tela de **Qualidade de dados**, com verificações úteis que constraints não cobrem:

- assinatura ativa sem pessoa;
- assinatura vencida há muitos ciclos;
- projeto ativo sem uso ativo;
- pessoa inativa ainda vinculada;
- categoria/departamento inativo em registro operacional;
- logo inacessível, opcionalmente verificado por job.

---

## 9. Migração de dados

### 9.1 Estratégia recomendada

Executar ETL repetível, idempotente e auditável, nunca copiar manualmente. O Google Sheets permanece somente leitura durante o corte final.

### 9.2 Mapeamento

| Origem | Destino |
|---|---|
| `Listas.Categorias` | `categories` |
| `Listas.Departamentos` | `departments` |
| `Assinaturas` | `subscriptions` |
| `Funcionários` | `people` |
| `Funcionários.Assinaturas` | `person_subscriptions`, resolvendo nome → ID |
| `Projetos` | `projects` |
| `Uso por projeto` | `project_subscriptions` |
| `Histórico` | `audit_events`, com metadados legados |

### 9.3 Normalização antes da carga

1. Exportar cada aba em CSV UTF-8 e preservar uma cópia imutável com hash SHA-256.
2. Validar cabeçalhos e quantidade de colunas.
3. Normalizar espaços, e-mails, datas, moedas e valores de enum.
4. Detectar IDs vazios/duplicados e nomes duplicados sem diferenciar caixa.
5. Resolver assinaturas em listas de pessoas; gerar relatório para nomes inexistentes ou ambíguos.
6. Resolver IDs de projeto/assinatura em usos; impedir órfãos.
7. Converter timestamps legados no fuso `America/Bahia` para UTC.
8. Importar categorias/departamentos, depois entidades e por último relações/histórico.
9. Salvar mapa `legacy_id → uuid` e relatório de rejeições.

### 9.4 Ferramenta de migração

Criar um utilitário Java separado ou um `CommandLineRunner` ativado por profile `migration`, com:

- modo `validate` sem gravar;
- modo `import` em transação/lotes;
- `migration_run_id` e checksums;
- política explícita para duplicidades;
- log sem dados sensíveis;
- possibilidade de limpar apenas uma execução de homologação, nunca produção sem confirmação.

### 9.5 Reconciliação obrigatória

Comparar origem e destino:

- total de assinaturas, pessoas, projetos, usos e eventos;
- total por status/plano/categoria/departamento;
- soma de valores originais;
- gasto mensal e anual calculados;
- vínculos por assinatura e pessoa;
- custo por departamento e projeto;
- lista e datas de vencimentos;
- amostra de históricos por assinatura;
- zero relações órfãs e zero duplicidades indevidas.

Gerar CSV/HTML de reconciliação e obter aceite do responsável de negócio.

### 9.6 Corte e rollback

1. Concluir homologação e ensaio de migração.
2. Anunciar janela curta de manutenção.
3. Colocar legado em somente leitura.
4. Fazer exportação final e registrar hashes.
5. Executar importação final e reconciliação.
6. Fazer smoke test com conta real de cada papel.
7. Liberar novo frontend.
8. Manter legado somente leitura durante período acordado.

Rollback: retirar o frontend novo do ar, reabrir temporariamente o legado e descartar/restaurar o banco novo a partir do backup pré-corte. Depois que houver escrita válida no novo sistema, rollback exige estratégia de reconciliação; não reabrir os dois para escrita simultânea.

---

## 10. Plano de implementação por fases

### Fase 0 — decisões e segurança

- Rotacionar os segredos expostos.
- Confirmar responsáveis, papéis e organização única/múltipla.
- Decidir política de exclusão: física, lógica ou bloqueio quando houver histórico.
- Confirmar se trimestral/semestral terão registro de pagamento.
- Definir hospedagem, domínios, e-mail e ambientes.

**Saída:** ADRs aprovados, backlog e credenciais seguras.

### Fase 1 — fundação

- Criar projetos backend/frontend.
- Provisionar Supabase dev/homologação/produção separados.
- Criar migrations Flyway, CI, lint, testes e OpenAPI.
- Integrar Supabase Auth, JWT e papéis.
- Configurar observabilidade e tratamento de erro.

**Saída:** login funcional, `/me`, banco versionado e pipeline verde.

### Fase 2 — cadastros centrais

- Categorias e departamentos.
- Assinaturas e pessoas com relação N:N.
- Concorrência otimista e auditoria.
- Listagens, filtros, formulários e validação.

**Saída:** equivalência do CRUD principal.

### Fase 3 — pagamentos, projetos e cálculos

- Pagamento e avanço de vencimento.
- Projetos/usos e conclusão.
- Rateio por pessoa/departamento/projeto.
- Alertas e consultas agregadas.

**Saída:** regras operacionais completas e testadas.

### Fase 4 — dashboard, histórico e relatórios

- Dashboard e gráficos.
- Histórico filtrável.
- PDFs e Excel equivalentes.
- Tela de qualidade de dados.

**Saída:** paridade funcional do sistema atual.

### Fase 5 — ETL e homologação

- Construir e testar importador.
- Fazer migrações de ensaio.
- Reconciliar dados e corrigir exceções.
- Executar testes de aceitação e acessibilidade.

**Saída:** aceite do negócio e runbook de corte.

### Fase 6 — produção e estabilização

- Backup, congelamento, migração final e reconciliação.
- Smoke tests, publicação e monitoramento.
- Período de suporte intensivo.
- Desativação controlada do Sheets/Streamlit após aceite.

**Saída:** Supabase como única fonte oficial e legado arquivado.

---

## 11. Estratégia de testes

### 11.1 Backend

- Unitários: custo mensal, alertas, datas, rateios, validações e sanitização de planilhas.
- Serviço/transação: CRUD + vínculos + auditoria; rollback completo em falha.
- Integração com Testcontainers PostgreSQL: constraints, migrations, queries e concorrência real.
- Segurança: JWT inválido/expirado, organização diferente e matriz de papéis.
- Contrato: OpenAPI e respostas de erro.

Casos obrigatórios do pagamento:

- mensal normal;
- dezembro → janeiro;
- 31 de janeiro → último dia de fevereiro;
- 29/02 em avanço anual → 28/02;
- vitalício rejeitado;
- trimestral/semestral conforme decisão;
- vencimento inválido;
- versão concorrente retorna `409`;
- atualização e auditoria confirmadas juntas ou revertidas juntas.

### 11.2 Frontend

- Componentes/formulários: obrigatórios, moeda, e-mail e mensagens.
- Serviços HTTP e interceptors.
- Guards e papéis.
- Estados: carregando, vazio, erro, sem permissão e conflito.
- Responsividade e navegação por teclado.

### 11.3 E2E

- login válido/inválido e logout;
- percorrer todas as rotas;
- criar pessoa, assinatura e vínculos;
- editar em duas sessões e validar conflito;
- registrar pagamento com confirmação;
- criar/concluir projeto e conferir rateio;
- filtrar histórico;
- baixar e validar PDF/Excel;
- viewport desktop e celular;
- garantir isolamento entre organizações, se multi-tenant.

### 11.4 Paridade

Rodar um dataset fixo no Python e no Java e comparar:

- indicadores;
- custos por assinatura/pessoa/departamento/projeto;
- alertas;
- evolução de 12 meses;
- conteúdo tabular de relatórios.

---

## 12. Operação, deploy e observabilidade

### 12.1 Ambientes

- `dev`: dados fictícios;
- `staging`: cópia anonimizada ou dataset representativo;
- `prod`: dados reais e acesso restrito.

Nunca compartilhar projeto Supabase ou chaves entre ambientes.

### 12.2 Pipeline

Em cada pull request:

1. lint e testes Angular;
2. build Angular;
3. testes Java unitários e de integração;
4. validação das migrations em PostgreSQL vazio;
5. análise de dependências/segredos;
6. E2E em staging para releases.

Deploy deve aplicar migration antes da nova aplicação, respeitando compatibilidade expand/contract quando houver mudanças futuras.

### 12.3 Observabilidade

- logs JSON com `traceId`, usuário técnico/ID e rota, sem token;
- métricas de latência, erro, pool de conexões e geração de relatórios;
- health checks de aplicação e banco;
- rastreamento de erros com contexto seguro;
- alertas para falhas 5xx, autenticação anormal e banco indisponível;
- backup/PITR do Supabase conforme plano contratado e teste periódico de restauração.

---

## 13. Critérios de aceite

A migração está concluída somente quando:

- todas as telas e operações aprovadas estão disponíveis;
- Supabase/PostgreSQL é a única fonte de verdade operacional;
- nenhuma credencial sensível está no frontend, repositório ou logs;
- papéis e isolamento de organização foram testados;
- todas as mutations relevantes geram auditoria na mesma transação;
- conflito concorrente retorna `409` e não sobrescreve dados;
- cálculos batem com o legado no dataset de referência;
- importação final não possui órfãos nem rejeições não aprovadas;
- totais e vínculos foram reconciliados e assinados pelo negócio;
- PDFs e Excel abrem corretamente e contêm os dados esperados;
- testes unitários, integração e E2E estão verdes;
- backup e rollback foram ensaiados;
- documentação operacional e treinamento foram entregues;
- o legado está somente leitura e possui data aprovada para desligamento.

---

## 14. Riscos e decisões pendentes

| Tema | Risco/decisão | Recomendação |
|---|---|---|
| Segredos | Credencial real presente no workspace | Revogar imediatamente e verificar histórico Git |
| Pagamentos | Trimestral/semestral sem fluxo atual | Manter equivalência inicialmente e aprovar evolução separada |
| Exclusão | Exclusão física pode prejudicar rastreabilidade | Preferir inativação/soft delete para entidades usadas; definir política |
| Histórico | Eventos legados não possuem IDs relacionais | Importar texto e metadados, vinculando quando o mapa for inequívoco |
| Evolução 12 meses | Legado reconstrói por histórico e não recupera excluídas perfeitamente | Criar snapshots mensais ou eventos completos no novo sistema |
| Logos | URLs externas podem quebrar | Migrar progressivamente para Supabase Storage |
| RLS + backend | Serviço privilegiado pode ignorar RLS | Filtrar organização em todas as queries e testar isolamento |
| Relatórios | Renderização PDF pode variar | Criar golden datasets e testes estruturais, sem depender de pixel perfeito |
| Migração | Nomes inconsistentes nas listas separadas por vírgula | Relatório de exceções e correção antes do corte |

---

## 15. Melhorias recomendadas após a paridade

Não bloquear a migração com estas melhorias; tratá-las depois da equivalência:

- snapshots mensais de custo para evolução histórica confiável;
- centro de custo, moeda e impostos;
- anexos de nota fiscal/contrato no Storage;
- notificações de vencimento por e-mail/Teams/Slack;
- renovação automática e previsão de caixa;
- aprovação em duas etapas para exclusão/pagamento;
- SSO corporativo e MFA obrigatório;
- trilha de alterações com JSON antes/depois;
- importação/exportação administrativa controlada;
- API assíncrona para relatórios muito grandes.

---

## 16. Checklist para começar

- [ ] Revogar a chave Google e trocar a senha exposta.
- [ ] Confirmar escopo de paridade e decisões pendentes da seção 14.
- [ ] Escolher versões suportadas de Java/Spring/Angular.
- [ ] Criar projetos Supabase separados por ambiente.
- [ ] Definir papéis e usuários iniciais.
- [ ] Aprovar o modelo relacional e política de exclusão.
- [ ] Criar monorepo, CI e migrations.
- [ ] Implementar autenticação e `/me`.
- [ ] Migrar primeiro assinaturas, pessoas e vínculos.
- [ ] Comparar cálculos com dataset fixo do legado.
- [ ] Completar projetos, dashboard, histórico e relatórios.
- [ ] Ensaiar ETL e reconciliação pelo menos duas vezes.
- [ ] Executar corte com plano de rollback testado.

Este documento deve ser mantido como especificação viva: decisões aprovadas viram ADRs, mudanças de esquema viram migrations Flyway e qualquer diferença funcional em relação ao legado deve possuir aceite explícito.
