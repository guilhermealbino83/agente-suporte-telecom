# Git Flow — Agente Suporte Telecom

Guia de comandos Git para o fluxo de desenvolvimento por etapas do projeto.

---

## Setup inicial (uma vez só)

Antes de usar o fluxo abaixo, o projeto precisa estar num repositório Git com um remote no GitHub.

### 1 — Inicializar o repositório local

Na pasta do projeto:

```bash
git init
git add .gitignore requirements.txt README.md app/ docs/ .spec/
git commit -m "feat: estrutura inicial do projeto"
```

> Não adicione `.venv/` nem `.env`. Confirme com `git status` antes do commit.

### 2 — Criar o repositório no GitHub

1. Acesse [github.com](https://github.com) → **New repository**
2. Nome sugerido: `agente-suporte-telecom`
3. Deixe **vazio** (sem README, sem .gitignore) — o conteúdo já está local
4. Copie a URL do repositório (ex: `https://github.com/seu-usuario/agente-suporte-telecom.git`)

### 3 — Conectar local ao GitHub

```bash
git remote add origin https://github.com/seu-usuario/agente-suporte-telecom.git
git branch -M main
git push -u origin main
```

---

## Fluxo por etapa

### Antes de iniciar uma etapa — criar branch

Sempre parta da `main` atualizada:

```bash
git checkout main
git pull origin main
git checkout -b feature/etapa-004
git push -u origin feature/etapa-004
```

> O `git checkout -b` cria a branch apenas localmente. O `git push -u origin` a publica no GitHub e vincula as duas — nos pushes seguintes desta branch basta `git push`.

Convenção de nome: `feature/etapa-00<numero>`.

Exemplos:
```
feature/etapa-001
feature/etapa-002
feature/etapa-003
feature/etapa-004
feature/etapa-005
```

---

### Durante o desenvolvimento — commits parciais

Faça commits pequenos e frequentes à medida que avança. Não espere terminar tudo para commitar.

```bash
git status                        # ver o que mudou
git add app/prompts.py            # adicionar arquivo específico
git commit -m "feat: adiciona arquivo de prompts"
```

```bash
git add app/agent.py
git commit -m "feat: integra system prompt no agente"
```

```bash
git add app/
git commit -m "test: valida recusa de perguntas fora do domínio"
```

**Prefixos de mensagem recomendados:**

| Prefixo | Quando usar |
|---|---|
| `feat:` | Nova funcionalidade |
| `fix:` | Correção de bug |
| `refactor:` | Melhoria de código sem mudar comportamento |
| `test:` | Adição ou ajuste de testes |
| `docs:` | Atualização de documentação |
| `chore:` | Tarefas de manutenção (atualizar deps, .gitignore) |

---

### Após concluir a etapa — commit final e push

```bash
git status                        # confirmar que não ficou nada de fora
git add .                         # adicionar tudo que falta (cuidado: não commitar .env)
git status                        # revisar o que vai entrar
git commit -m "feat: etapa 4 concluída — prompt engineering com persona telecom"
git push origin feature/etapa-004
```

---

### Criar Pull Request no GitHub

1. Acesse o repositório no GitHub
2. Clique em **"Compare & pull request"** (aparece automaticamente após o push)
3. Preencha:
   - **Título:** `feat: etapa 4 — prompt engineering`
   - **Descrição:** o que foi implementado, como testar
4. Clique em **"Create pull request"**

---

### Aprovar e fazer o merge

Como é um projeto solo, você mesmo aprova:

1. Na página da PR, clique em **"Merge pull request"**
2. Confirme com **"Confirm merge"**
3. Clique em **"Delete branch"** para limpar a branch remota

---

### Atualizar o local após o merge

```bash
git checkout main
git pull origin main
git branch -d feature/etapa-004    # remove a branch local
```

---

## Referência rápida

```bash
# ver em qual branch está
git branch

# ver histórico de commits
git log --oneline

# ver o que mudou nos arquivos
git diff

# desfazer alterações num arquivo (antes do commit)
git restore app/agent.py

# ver commits da branch atual vs main
git log main..HEAD --oneline
```

---

## Estado esperado ao final de cada etapa

```
main
  └── feature/etapa-001    (merged)
  └── feature/etapa-002    (merged)
  └── feature/etapa-003    (merged)
  └── feature/etapa-004    (em desenvolvimento)
```

A `main` sempre reflete o código aprovado no code review. Cada etapa vive na sua própria branch até ser aprovada.
