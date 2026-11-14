# Testes da versão 1.3.0

Feitos em 14/11/2026, na branch `v1.3.0`, neste PC (Ryzen 5 5600G + RTX 3060). Nenhum teste usou os seus vídeos ou a sua pasta de trabalho: tudo rodou em pastas temporárias.

## Como rodar

Na pasta do repositório, com o ambiente do modo desenvolvedor (`.venv`, criado pelo `.bat`):

```
.venv\Scripts\python -m pytest              (rápidos: menos de 1 segundo)
.venv\Scripts\python -m pytest -m lento     (ponta a ponta e botão a botão: cerca de 1 minuto)
```

## Resultados

| Função | Funcionou? | Observação |
|---|---|---|
| Testes rápidos (`testes/test_basico.py`) | sim | 41 de 41: tempos, versões, pastas, correções, censura, `cortes.json` v2 e antigo, duração do Short, legendas editadas, `edicao.json`, capítulos e limpeza. |
| Ponta a ponta (`testes/test_ponta_a_ponta.py`) | sim | Vídeo de amostra de 20 s com a voz "Maria" do Windows → transcrição no processador (Whisper "tiny") → cortes falsos → Short → legenda editada e censurada → Short refeito com a legenda nova. Cerca de 55 s. |
| Botão a botão (`testes/test_telas.py`) | sim | 57 de 57 botões e itens do Menu, sem erro (tabela abaixo). As perguntas são respondidas sozinhas e nada é renderizado de verdade. |
| Sem placa NVIDIA (como no notebook) | sim | Transcrição e Short no processador: "Usando o PROCESSADOR" e "Codificando na: PROCESSADOR (x264)". |
| Com placa NVIDIA | sim | Com o ffmpeg 8.1, a RTX 3060 (driver 595.97) volta a montar os vídeos. |
| Modo desenvolvedor num "PC novo" | sim | Clone numa pasta vazia + `.bat`: tudo pronto em cerca de 2 minutos; na segunda vez, 2 s. |
| Aviso de código novo de outro PC | sim | GitHub falso: pergunta, baixa e reabre. Também avisa as mudanças sem Commit. |
| Aviso de versão nova (app instalado) | sim | Com o repositório público, o app encontra o Release 1.2.0. Janela testada com uma versão falsa. |
| Build local (`build/montar_app.ps1`) | sim | Montou o app em `dist\app` em cerca de 2 minutos; o teste de abrir os módulos passou. |
| App montado | sim | Abre as telas, tem o corretor e o `truststore`, e gerou o Short 04. |
| Shorts iguais aos de antes | sim | Short 04 do Bully 11: imagem idêntica em todas as fases. O áudio às vezes varia um pouco entre duas execuções (mistura da música no ffmpeg); isso já acontecia antes da 1.3.0. |
| Instalador (`.exe`) | não testado | O Inno Setup não está neste PC. Ele é montado pelo GitHub, quando a branch for para a `main`. |
| Download e instalação da versão nova | não testado | Só dá para testar de verdade quando existir uma versão maior publicada (a 1.3.0). |
| Notebook de verdade | não testado | Testado neste PC fingindo não ter placa NVIDIA. |

## Botão a botão

As ações externas (abrir pasta, rodar programa, navegador) foram só registradas, não executadas. "pergunta" = o teste respondeu NÃO ou CANCELAR.

| Onde | Botão | Funcionou? | O que fez |
|---|---|---|---|
| Aba Shorts | 1 Transcrever vídeo novo | sim | roda nucleo.transcrever |
| Aba Shorts | 2 Pedir cortes ao Claude | sim | copia texto; aviso: Pedir cortes ao Claude |
| Aba Shorts | 3 Gerar Shorts | sim | pergunta: Gerar Shorts |
| Aba Shorts | 4 Revisar legendas | sim | abre a janela: Revisar legendas - teste das telas |
| ↳ janela Revisar legendas - teste das | Aplicar linha (Enter) | sim | - |
| ↳ janela Revisar legendas - teste das | Ouvir trecho | sim | corta o trecho no ffmpeg; abre (abrir) |
| ↳ janela Revisar legendas - teste das | Censurar palavra | sim | - |
| ↳ janela Revisar legendas - teste das | Tirar censura | sim | - |
| ↳ janela Revisar legendas - teste das | Adicionar sempre à lista | sim | pergunta: Adicionar sempre à lista |
| ↳ janela Revisar legendas - teste das | Censurar as palavras da lista (censura.txt) neste Short | sim | - |
| ↳ janela Revisar legendas - teste das | Salvar | sim | - |
| ↳ janela Revisar legendas - teste das | Desfazer | sim | - |
| ↳ janela Revisar legendas - teste das | Voltar ao original | sim | pergunta: Voltar ao original |
| ↳ janela Revisar legendas - teste das | Renderizar de novo só este Short | sim | roda shorts.gerar_shorts; aviso: Renderizar de novo |
| ↳ janela Revisar legendas - teste das | Assistir o Short | sim | abre (abrir) |
| Aba Shorts | 5 Publicar (Buffer) | sim | abre a janela: Publicar - teste das telas |
| ↳ janela Publicar - teste das telas | Abrir o Buffer | sim | abre navegador https://publish.buffer.com |
| ↳ janela Publicar - teste das telas | Mostrar na pasta | sim | abre (mostrar_na_pasta) |
| ↳ janela Publicar - teste das telas | Assistir | sim | abre (abrir) |
| ↳ janela Publicar - teste das telas | Copiar título | sim | copia texto |
| ↳ janela Publicar - teste das telas | Copiar descrição | sim | copia texto |
| ↳ janela Publicar - teste das telas | Copiar tags | sim | copia texto |
| ↳ janela Publicar - teste das telas | Título EN | sim | copia texto |
| ↳ janela Publicar - teste das telas | Desc. EN | sim | copia texto |
| ↳ janela Publicar - teste das telas | Postado | sim | - |
| ↳ janela Publicar - teste das telas | Copiar legenda | sim | copia texto |
| ↳ janela Publicar - teste das telas | Postado | sim | - |
| ↳ janela Publicar - teste das telas | Copiar legenda | sim | copia texto |
| ↳ janela Publicar - teste das telas | Postado | sim | - |
| Aba Shorts | Link do vídeo completo... | sim | pergunta: link |
| Aba Shorts | Abrir pasta dos Shorts | sim | abre (abrir) |
| Aba Shorts | Limpar projeto (depois de postar) | sim | pergunta: Limpar projeto |
| Aba Shorts | Marcar câmera e gameplay | sim | roda interface.marcar_camera |
| Aba Vídeos longos | 1 Juntar vídeos (partes da live) | sim | abre juntar vídeos |
| Aba Vídeos longos | 2 Transcrever a live | sim | roda nucleo.transcrever |
| Aba Vídeos longos | 3 Editar vídeo longo | sim | abre a janela: Editar vídeo longo - teste das telas |
| ↳ janela Editar vídeo longo - teste d | Ouvir emenda | sim | aviso: Ouvir emenda |
| ↳ janela Editar vídeo longo - teste d | Gerar prévia (10 min) | sim | roda videos_longos.editar_episodio |
| ↳ janela Editar vídeo longo - teste d | Gerar episódio | sim | roda videos_longos.editar_episodio |
| ↳ janela Editar vídeo longo - teste d | Abrir pasta do episódio | sim | abre (abrir) |
| ↳ janela Editar vídeo longo - teste d | Colar edicao.json | sim | pergunta: Colar edicao.json |
| ↳ janela Editar vídeo longo - teste d | Copiar pedido de novo | sim | copia texto; aviso: Editar vídeo longo |
| Aba Vídeos longos | Colar edicao.json | sim | pergunta: Colar edicao.json |
| Aba Vídeos longos | Abrir pasta do episódio | sim | abre (abrir) |
| Aba Vídeos longos | Limpar projeto (depois de postar) | sim | pergunta: Limpar projeto |
| Menu | Novidades da versão 1.2.0 | sim | abre a janela: Novidades - FamosoZora Studio 1.2.0 |
| Menu | Procurar atualização | sim | procura atualização |
| Menu | Verificar atualizações ao abrir | sim | - |
| Menu | Abrir pasta de trabalho | sim | abre (abrir) |
| Menu | Mudar pasta de trabalho... | sim | escolher pasta |
| Menu | Configurações (config.json) | sim | abre (abrir_texto) |
| Menu | Vocabulário (nomes do canal) | sim | abre (abrir_texto) |
| Menu | Correções automáticas | sim | abre (abrir_texto) |
| Menu | Músicas de fundo | sim | abre (abrir) |
| Menu | Diretrizes do canal (o que o Claude segue) | sim | abre (abrir) |
| Menu | Guia: COMO USAR | sim | abre (abrir) |
| Menu | Atualizar dependências (modo desenvolvedor) | sim | roda programa |
