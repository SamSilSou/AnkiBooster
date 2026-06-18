# 🧠 Como o Booster Funciona

## Um Companion SRS, não um Addon

O Anki Booster não foi projetado como uma extensão tradicional.

Ele é um **Companion SRS Engine** que opera em paralelo ao scheduler oficial do Anki.

Enquanto o Anki é responsável por determinar quando um cartão deve voltar a ser revisado para maximizar retenção de longo prazo, o Booster possui um objetivo diferente:

> Identificar quais conhecimentos ainda apresentam fragilidade real e reforçá-los continuamente ao longo do dia.

Esses dois objetivos são complementares.

O Anki responde:

> 📅 "Quando devo rever este cartão novamente?"

O Booster responde:

> 🎯 "Quais cartões ainda não estão realmente dominados?"

Por isso o Booster mantém seu próprio modelo de estado, suas próprias métricas e seu próprio scheduler, sem alterar o funcionamento do Anki.

---

# ⚙️ Arquitetura Geral

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

O scheduler do Anki continua sendo a fonte de verdade para memória de longo prazo.

O Booster adiciona uma segunda camada especializada em:

- 🔥 Recuperação de cartões frágeis
- 🎯 Priorização por dificuldade recente
- 📈 Reforço contínuo
- 🧠 Consolidação fora do contexto de revisão
- ⭐ Domínio ativo de cartões prioritários

O resultado é um sistema híbrido onde ambos trabalham simultaneamente, cada um resolvendo um problema diferente.

---

# 🧠 Priorização por Dificuldade Real

Um dos maiores problemas de utilizar apenas lapses históricos é que eles não distinguem dificuldades antigas de dificuldades atuais.

Imagine dois cartões.

### Card A

```text
15 lapses históricos
0 erros recentes
Ease 250
```

### Card B

```text
2 lapses históricos
3 erros hoje
Ease 250
```

Em muitos sistemas, o Card A continuará sendo tratado como mais problemático simplesmente porque acumulou mais erros ao longo da vida.

O Booster segue uma filosofia diferente.

Dificuldades recentes possuem mais valor diagnóstico do que dificuldades antigas.

Por isso sua pontuação principal é calculada utilizando múltiplas fontes de informação:

```python
score = (
    anki_revlog_lapses * 100 +
    booster_errors * 50 +
    anki_lapses * 5
)
```

Onde:

- 🔥 `anki_revlog_lapses` representa erros recentes detectados pelo próprio Anki
- ⚠️ `booster_errors` representa erros observados durante as revisões extras do Booster
- 📚 `anki_lapses` representa o histórico acumulado do cartão

O peso muito maior dos erros recentes faz com que cartões atualmente problemáticos recebam prioridade máxima.

### Exemplo

Card A:

```text
15 × 5 = 75
```

Card B:

```text
3 × 100 = 300
```

Resultado:

🏆 O Card B será exibido primeiro.

Mesmo possuindo menos lapses históricos.

Isso acontece porque o Booster considera que a dificuldade observada hoje é mais relevante do que a dificuldade observada meses atrás.

---

# 📊 Seleção Inteligente de Cartões

Após identificar os cartões disponíveis, o Booster não escolhe um cartão aleatório.

Ele executa uma ordenação baseada em múltiplos critérios.

Trecho real da implementação:

```python
card = min(
    available_cards,
    key=lambda c: self._calculate_priority(c, favs_set)
)
```

A prioridade final considera:

```python
return (
    -score,
    anki_ease,
    anki_interval,
    booster_streak,
    -fav_bonus
)
```

Isso significa que a decisão de exibição não depende apenas de erros.

Ela considera simultaneamente:

- dificuldade recente
- Ease Factor
- intervalo atual
- desempenho acumulado
- sequência de acertos
- prioridade de favoritos

Dois cartões com a mesma quantidade de erros podem receber prioridades completamente diferentes dependendo do contexto.

---

# ⏳ Scheduler Independente

O Booster possui um scheduler próprio.

Cada cartão recebe um agendamento individual:

```python
card["next_due"] = now + card_delay
```

Esse agendamento é completamente separado dos intervalos oficiais do Anki.

Além disso existe um controle global responsável por manter um ritmo constante de exposição:

```python
self.next_global_show = min(
    now + GLOBAL_CORRECT,
    now + card_delay
)
```

Na prática existem dois schedulers funcionando simultaneamente:

```text
Scheduler do Anki
          +
Scheduler do Booster
```

O primeiro controla memória de longo prazo.

O segundo controla reforço contínuo.

Nenhum interfere no outro.

---

# 🔄 Buffer Rotativo Contínuo

Mostrar cartões diretamente da coleção carregada gera um problema clássico:

alguns cartões podem monopolizar a fila.

Para evitar isso o Booster utiliza um buffer ativo.

Quando a sessão é iniciada:

```python
self.active_cards = self.pool_cards[:BUFFER_SIZE]
```

Apenas os cartões presentes nesse buffer participam da seleção.

Após cada revisão, o cartão é reposicionado:

```python
self.active_cards.append(
    self.active_cards.pop(idx)
)
```

Essa arquitetura cria um fluxo contínuo:

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
- distribuição mais homogênea
- menor previsibilidade
- sensação de revisão mais natural

---

# 📈 Estado Persistente Próprio

O Anki já possui métricas próprias.

Porém elas foram projetadas para resolver problemas específicos do scheduler oficial.

O Booster precisa responder perguntas diferentes.

Por isso ele mantém um estado independente:

```json
{
    "streak": 0,
    "errors_recent": 0,
    "next_due": 0,
    "fav_level": 1,
    "fav_consecutive": 0
}
```

Cada campo possui uma função específica.

### streak

Quantidade de exposições consecutivas respondidas corretamente dentro do Booster.

### errors_recent

Dificuldades observadas durante as revisões extras.

### next_due

Próximo momento em que o cartão poderá ser exibido novamente pelo scheduler do Booster.

### fav_level

Nível atual dentro do sistema de domínio.

### fav_consecutive

Quantidade de acertos consecutivos dentro do nível atual.

Esses dados permanecem salvos entre reinicializações.

Com o tempo o Booster constrói uma visão própria sobre a evolução do usuário.

---

# ⭐ Sistema de Progressão de Domínio

Favoritos não funcionam apenas como marcadores.

Eles entram em um fluxo completo de domínio.

Trecho real:

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

Cada nível exige uma sequência mínima de acertos.

Um erro reinicia o progresso.

Quando o domínio é comprovado, o favorito é automaticamente graduado e removido da lista de treinamento especial.

O objetivo não é apenas revisar.

É comprovar domínio.

---

# 📡 Dupla Camada de Detecção de Dificuldade

O Booster monitora duas fontes independentes de informação.

### Dados do Anki

```python
anki_revlog_lapses
```

Obtidos diretamente do Revlog.

Representam erros observados pelo scheduler oficial.

### Dados do Booster

```python
errors_recent
```

Obtidos durante as revisões extras.

Representam dificuldades observadas fora do contexto normal do Anki.

Isso permite detectar situações extremamente interessantes.

Por exemplo:

```text
O usuário não erra mais durante as revisões normais.

Mas continua errando quando encontra o cartão
fora da sessão principal.
```

Esse tipo de fragilidade normalmente passa despercebido.

O Booster consegue identificá-la.

---

# 🧠 Reforço Fora do Contexto

Uma revisão tradicional acontece dentro de um contexto específico.

O usuário senta para estudar.

Abre o Anki.

Entra em modo de revisão.

O Booster quebra esse contexto.

Os cartões podem aparecer enquanto o usuário:

- programa
- trabalha
- navega na internet
- estuda outro assunto
- realiza atividades normais do dia

Isso transforma cada resposta correta em uma evidência muito mais forte de domínio real.

O conhecimento deixa de depender do contexto da sessão.

---

# 🔒 Segurança

O Booster foi projetado para operar de forma totalmente não destrutiva.

Garantias da arquitetura:

✅ Leitura segura do banco do Anki

✅ Cópia temporária para processamento

✅ Nenhuma alteração em `collection.anki2`

✅ Nenhuma modificação do scheduler oficial

✅ Nenhuma alteração de intervalos

✅ Nenhuma alteração de notas

✅ Nenhuma alteração de decks

O Anki continua sendo o único responsável pelo estado oficial do aprendizado.

---

# 🚀 Resumo

O Booster não é um visualizador de cartões.

Não é um popup.

Não é um addon de interface.

Ele é um segundo sistema de repetição espaçada operando em paralelo ao Anki.

Com:

- 🧠 Scheduler próprio
- 📈 Estado persistente próprio
- 🎯 Engine de priorização própria
- ⭐ Sistema de domínio próprio
- 🔥 Métricas próprias de dificuldade
- 📡 Monitoramento independente de erros

Tudo isso sem modificar o funcionamento interno do Anki.

O resultado é um sistema capaz de transformar pequenos momentos do dia em oportunidades contínuas de reforço, consolidação e domínio real da memória.
