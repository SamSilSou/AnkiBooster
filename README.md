# 🧠 Como o Booster Funciona

> **Anki Booster é um Companion SRS Engine independente e complementar ao Anki.**
>
> Ele não substitui o scheduler oficial.
>
> Ele executa um **segundo sistema de repetição espaçada em paralelo**, focado exclusivamente em identificar e reforçar cartões que ainda apresentam fragilidade real.

Enquanto o Anki responde:

> 📅 **"Quando devo rever este cartão novamente?"**

O Booster responde:

> 🎯 **"Quais cartões ainda estão frágeis neste momento?"**

Para isso, ele mantém:

✅ Scheduler próprio  
✅ Métricas próprias  
✅ Estado persistente próprio  
✅ Sistema de domínio próprio  
✅ Priorização própria

Tudo sem alterar o funcionamento interno do Anki.

---

# ⚙️ Arquitetura

```text
┌───────────────────────┐
│         Anki          │
│   Official Scheduler  │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│      Anki Booster     │
│  Companion SRS Engine │
└───────────────────────┘
```

### Responsabilidades

| Sistema | Responsabilidade |
|----------|----------|
| 🧠 Anki | Memória de longo prazo |
| 🚀 Booster | Reforço contínuo |
| 📈 Booster | Recuperação de cartões frágeis |
| 🎯 Booster | Priorização por dificuldade recente |
| 🔄 Booster | Micro-revisões ao longo do dia |

---

# 🧠 Priorização por Dificuldade Real

A maioria das ferramentas semelhantes considera apenas:

```text
Lapses históricos
```

O Booster considera:

- 🔥 Erros recentes do Anki
- 🔥 Erros recentes do Booster
- 📚 Histórico geral de lapses

---

## Fórmula de Prioridade

```python
score = (
    anki_revlog_lapses * 100 +
    booster_errors * 50 +
    anki_lapses * 5
)
```

### Pesos

| Métrica | Peso |
|----------|----------:|
| 🔥 Erro recente no Anki | 100 |
| ⚠️ Erro recente no Booster | 50 |
| 📚 Lapse histórico | 5 |

---

# 🔬 Exemplo Real de Decisão

## Card A

```text
Lapses históricos: 15
Erros recentes: 0
Ease: 250
```

## Card B

```text
Lapses históricos: 2
Erros recentes hoje: 3
Ease: 250
```

### Pontuação

**Card A**

```text
15 × 5 = 75
```

**Card B**

```text
3 × 100 = 300
```

---

## Resultado

🏆 **Card B é exibido primeiro**

Mesmo tendo menos lapses históricos.

Porque o Booster considera que:

> 🎯 **Dificuldade recente é mais importante que dificuldade antiga.**

---

# ⏳ Scheduler Independente

Cada cartão possui seu próprio agendamento.

```python
card["next_due"] = now + card_delay
```

Além disso existe um ritmo global de exibição:

```python
self.next_global_show = min(
    now + GLOBAL_CORRECT,
    now + card_delay
)
```

---

## Resultado

```text
Scheduler do Anki
          +
Scheduler do Booster
```

Funcionando simultaneamente.

Sem interferir um no outro.

---

# 📊 Seleção Inteligente

Quando vários cartões estão disponíveis, o Booster escolhe automaticamente o mais relevante.

```python
card = min(
    available_cards,
    key=lambda c: self._calculate_priority(c, favs_set)
)
```

A decisão considera:

- 📚 Lapses
- 📉 Ease Factor
- 📆 Intervalo atual
- 🔥 Erros recentes
- 📈 Streak
- ⭐ Favoritos
- 📝 Revlog recente

---

# 🔄 Buffer Rotativo Contínuo

Os cartões não são exibidos diretamente da fila principal.

O Booster utiliza uma arquitetura de buffer ativo.

```python
self.active_cards = self.pool_cards[:BUFFER_SIZE]
```

Após cada revisão:

```python
self.active_cards.append(
    self.active_cards.pop(idx)
)
```

---

## Fluxo

```text
Pool Global
     │
     ▼
Buffer Ativo
     │
     ▼
Card Exibido
```

### Benefícios

✅ Menos repetição imediata

✅ Fluxo contínuo

✅ Melhor distribuição de exposição

✅ Menos efeito de memorização por posição

---

# 📈 Estado Persistente Próprio

O Booster mantém métricas independentes para cada cartão.

```json
{
  "streak": 0,
  "errors_recent": 0,
  "next_due": 0,
  "fav_level": 1
}
```

Esses dados permanecem salvos mesmo após reiniciar o programa.

---

## O Booster Aprende

Com o tempo ele constrói uma segunda camada de conhecimento sobre o usuário:

- 📊 Cartões frágeis
- 📈 Cartões dominados
- 🔥 Erros recorrentes
- ⭐ Cartões prioritários

---

# ⭐ Sistema de Progressão de Domínio

Favoritos não são apenas marcadores.

Eles entram em um sistema próprio de progressão.

```python
if card["fav_consecutive"] >= required:
    card["fav_level"] += 1
```

---

## Progressão

```text
⭐ N1
   ↓
⭐⭐ N2
   ↓
⭐⭐⭐ N3
   ↓
🏆 Graduado
```

### Regras

✅ Acertos consecutivos avançam níveis

❌ Um erro reinicia o progresso

🏆 Domínio comprovado remove o favorito automaticamente

---

# 📡 Dupla Camada de Detecção de Erros

O Booster monitora duas fontes independentes.

## Fonte 1 — Anki

```python
anki_revlog_lapses
```

Obtidos diretamente do Revlog.

---

## Fonte 2 — Booster

```python
errors_recent
```

Obtidos durante as revisões extras.

---

## O que isso permite detectar?

Situações como:

```text
O usuário já não erra mais no Anki...

Mas continua errando
quando encontra o cartão
fora da sessão principal.
```

🎯 Exatamente o tipo de fragilidade que normalmente passa despercebida.

---

# 🔒 Segurança

O Booster foi projetado para ser extremamente conservador.

## Garantias

✅ Leitura segura do banco

✅ Cópia temporária da collection

✅ Nenhuma alteração em `collection.anki2`

✅ Nenhuma alteração no scheduler oficial

✅ Nenhuma modificação de intervalos

✅ Nenhuma modificação de decks

✅ Nenhuma modificação de notas

---

# 🚀 Em Resumo

O **Anki Booster** não é um addon tradicional.

Ele é um:

> 🧠 **Companion SRS Engine**

que executa um segundo sistema de repetição espaçada em paralelo ao Anki.

Com:

✅ Scheduler próprio

✅ Métricas próprias

✅ Estado persistente próprio

✅ Sistema de domínio próprio

✅ Priorização baseada em dificuldade recente

✅ Reforço contínuo ao longo do dia

O resultado é um sistema capaz de transformar pequenos momentos livres em oportunidades constantes de consolidação da memória, atuando exatamente onde o aprendizado ainda apresenta fragilidade.

---

## 💡 Filosofia

```text
Anki:
"Quando devo rever novamente?"

Booster:
"O que ainda não está realmente dominado?"
```

Os dois sistemas trabalham juntos.

🧠 Anki constrói a memória.

🚀 Booster fortalece a memória.
