# Instruções para o Claude neste repositório

- **Sem atribuição ao Claude:** não colocar "Generated with Claude Code", "Co-Authored-By: Claude", link de sessão
  nem nada parecido em commits, descrições de pull request, comentários ou qualquer outro texto do repositório.
- Escrever em português simples (o dono tem pouca experiência com código) e explicar o que mudou e por quê.
- Nomes e comentários do código em português; cada arquivo novo começa com um comentário dizendo para que serve.
- Toda mudança entra no `CHANGELOG.md`, na seção da versão em andamento.
- **Bugs reportados pelo app — revisar antes de TODA versão nova:** o botão direito > "🐞 Reportar bug" do Studio
  abre issues no GitHub com a etiqueta `bug-do-app` e a marca `<!-- relato-do-app: bug-do-app -->` no texto
  (procurar pelas duas: a etiqueta só entra se existir no repositório) (versão, tela, vídeos selecionados, últimos cliques, erros e
  o fim do `studio.log`). Antes de mudar `app/versao.py` para lançar uma versão, ler as issues abertas com essa
  etiqueta ou marca, investigar e corrigir o que der; anotar cada conserto no `CHANGELOG.md` citando a issue e, depois de
  o dono aprovar, fechar a issue dizendo em qual versão saiu. O que não der para corrigir: explicar na issue o
  porquê. Fora desse momento, não precisa olhar as issues (a não ser que o dono peça).
