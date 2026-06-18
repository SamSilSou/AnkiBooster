# 🧠 Como o Booster Funciona

## Um Companion SRS, não um Addon

O Anki Booster não é uma extensão tradicional do Anki.

Ele funciona como um **Companion SRS Engine**, executando um segundo sistema de repetição espaçada em paralelo ao scheduler oficial.

Enquanto o Anki decide:

> 📅 "Quando este cartão deve voltar?"

O Booster decide:

> 🎯 "Quais cartões ainda demonstram dificuldade real?"

Cada sistema resolve um problema diferente.

O Anki continua focado na retenção de longo prazo, enquanto o Booster atua como uma camada adicional de reforço contínuo, recuperação de cartões frágeis e consolidação da memória fora do contexto normal de revisão.

---

## ⚙️ Arquitetura

```text
┌─────────────────────┐
│        Anki         │
│ Official Scheduler  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Anki Booster     │
│ Companion SRS Engine│
└─────────────────────┘
```

O Booster não modifica intervalos, decks ou notas.

Ele apenas observa os dados do Anki, constrói suas próprias métricas e decide quais cartões merecem reforço adicional.

---

## 🧠 Priorização por Dificuldade Real

A maioria dos sistemas considera apenas o histórico acumulado de erros.

O Booster prioriza principalmente a dificuldade recente.

Sua pontuação é calculada combinando múltiplas fontes de informação:

```python
score = (
    anki_revlog_lapses * 100 +
    booster_errors * 50 +
    anki_lapses * 5
)
```

Onde:

- 🔥 `anki_revlog_lapses` → erros recentes registrados pelo Anki
- ⚠️ `booster_errors` → erros observados nas revisões extras
- 📚 `anki_lapses` → histórico total de lapses

O resultado é uma priorização mais próxima da dificuldade atual do usuário.

### 🔬 Exemplo

**Card A**

```text
15 lapses históricos
0 erros recentes
```

**Card B**

```text
2 lapses históricos
3 erros hoje
```

Pontuação:

```text
Card A = 75
Card B = 300
```

🏆 O Card B recebe prioridade.

Mesmo possuindo menos erros históricos.

---

## 📊 Seleção Inteligente

Quando existem vários cartões disponíveis, o Booster escolhe automaticamente o mais relevante.

```python
card = min(
    available_cards,
    key=lambda c: self._calculate_priority(c, favs_set)
)
```

A decisão considera simultaneamente:

- dificuldade recente
- Ease Factor
- intervalo atual
- streak de acertos
- favoritos
- histórico de erros

Isso evita que cartões sejam escolhidos apenas por uma métrica isolada.

---

## ⏳ Scheduler Independente

Cada cartão possui um agendamento próprio dentro do Booster.

```python
card["next_due"] = now + card_delay
```

Além disso existe um controle global de frequência:

```python
self.next_global_show = min(
    now + GLOBAL_CORRECT,
    now + card_delay
)
```

Na prática:

```text
Scheduler do Anki
        +
Scheduler do Booster
```

Os dois funcionam simultaneamente sem interferir um no outro.

---

## 🔄 Buffer Rotativo

Os cartões não são exibidos diretamente da coleção carregada.

O Booster utiliza um buffer ativo para distribuir melhor as revisões.

```python
self.active_cards = self.pool_cards[:BUFFER_SIZE]
```

Após cada resposta:

```python
self.active_cards.append(
    self.active_cards.pop(idx)
)
```

Fluxo:

```text
Pool Global
     │
     ▼
Buffer Ativo
     │
     ▼
Card Exibido
```

Benefícios:

- menor repetição imediata
- distribuição mais equilibrada
- revisões mais naturais

---

## 📈 Estado Persistente Próprio

Além dos dados do Anki, o Booster mantém métricas independentes para cada cartão.

```json
{
    "streak": 0,
    "errors_recent": 0,
    "next_due": 0,
    "fav_level": 1,
    "fav_consecutive": 0
}
```

Essas informações permanecem salvas entre reinicializações e permitem que o Booster acompanhe a evolução do usuário de forma independente.

---

## ⭐ Sistema de Domínio

Favoritos não são apenas marcadores visuais.

Eles entram em um sistema próprio de progressão.

```python
if card["fav_consecutive"] >= required:
    card["fav_level"] += 1
```

Fluxo:

```text
⭐ N1
 ↓
⭐⭐ N2
 ↓
⭐⭐⭐ N3
 ↓
🏆 Graduado
```

Cada nível exige uma sequência mínima de respostas corretas.

Um erro reinicia o progresso.

O objetivo não é apenas revisar, mas demonstrar domínio consistente.

---

## 📡 Dupla Camada de Detecção de Dificuldade

O Booster monitora duas fontes independentes de informação.

### Dados do Anki

```python
anki_revlog_lapses
```

Obtidos diretamente do Revlog.

### Dados do Booster

```python
errors_recent
```

Obtidos durante as revisões extras.

Isso permite detectar cartões que parecem dominados durante as revisões normais, mas continuam falhando quando aparecem fora do contexto do estudo.

---

## 🧠 Reforço Fora do Contexto

Uma das principais diferenças do Booster é que ele apresenta cartões fora da sessão tradicional de revisão.

Os cartões podem aparecer enquanto o usuário:

- 💻 programa
- 📚 estuda outro assunto
- 🌐 navega na internet
- 📝 trabalha
- 🎮 realiza atividades normais do dia

Isso reduz a dependência do contexto e fortalece a recuperação espontânea da informação.

---

## 🔒 Segurança

O Booster foi projetado para operar de forma totalmente não destrutiva.

✅ Leitura segura do banco do Anki

✅ Cópia temporária para processamento

✅ Nenhuma alteração em `collection.anki2`

✅ Nenhuma modificação dos intervalos

✅ Nenhuma alteração de decks ou notas

✅ Nenhuma interferência no scheduler oficial

O Anki continua sendo a única fonte de verdade do aprendizado.

---

## 🚀 Resumo

O Anki Booster não substitui o Anki.

Ele adiciona uma segunda camada de repetição espaçada focada em identificar fragilidades atuais e reforçá-las continuamente.

Principais componentes:

- 🧠 Scheduler próprio
- 📈 Estado persistente próprio
- 🎯 Priorização por dificuldade recente
- ⭐ Sistema de domínio para favoritos
- 📡 Monitoramento independente de erros
- 🔄 Buffer rotativo inteligente

Tudo isso funcionando em paralelo ao scheduler oficial, sem alterar o comportamento interno do Anki.
