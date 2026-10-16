nome: Command (comando)
aliases: command, comando, desfazer e refazer, undo redo, undo, historico de acoes, histórico de ações, padrao command, padrão command
problema: Quando usar: transformar uma ação em um objeto para poder desfazer, refazer, guardar um histórico, enfileirar ou executar depois (editores, desfazer de formulários, filas de tarefas).
funcoes: python=demo; javascript=demo
casos: [[[], ["Olá mundo", "Olá"]]]

## Ideia
- Cada ação é um objeto com `fazer` e `desfazer`, guardando o que precisa para reverter.
- Quem executa mantém uma pilha de comandos já feitos; desfazer tira o último e chama `desfazer`.
- Refazer exige uma segunda pilha com os desfeitos.
- Também serve para filas de tarefas e registros de auditoria (o comando é o registro).

## Pseudocódigo
```
classe Editor: texto, historico
    executar(comando): comando.fazer(editor); historico.empilhe(comando)
    desfazer(): se historico não vazio: historico.desempilhe().desfazer(editor)
classe Inserir(trecho): fazer → texto += trecho; desfazer → remove o trecho do fim
```

## Código
```python
class Editor:
    def __init__(self):
        self.texto = ""
        self._historico = []

    def executar(self, comando):
        comando.fazer(self)
        self._historico.append(comando)

    def desfazer(self):
        if self._historico:
            self._historico.pop().desfazer(self)


class Inserir:
    def __init__(self, trecho):
        self.trecho = trecho

    def fazer(self, editor):
        editor.texto += self.trecho

    def desfazer(self, editor):
        editor.texto = editor.texto[:-len(self.trecho)]


def demo():
    editor = Editor()
    editor.executar(Inserir("Olá"))
    editor.executar(Inserir(" mundo"))
    antes = editor.texto
    editor.desfazer()
    return [antes, editor.texto]
```
```javascript
class Editor {
  constructor() { this.texto = ""; this.historico = []; }
  executar(comando) { comando.fazer(this); this.historico.push(comando); }
  desfazer() { if (this.historico.length) this.historico.pop().desfazer(this); }
}

class Inserir {
  constructor(trecho) { this.trecho = trecho; }
  fazer(editor) { editor.texto += this.trecho; }
  desfazer(editor) { editor.texto = editor.texto.slice(0, editor.texto.length - this.trecho.length); }
}

function demo() {
  const editor = new Editor();
  editor.executar(new Inserir("Olá"));
  editor.executar(new Inserir(" mundo"));
  const antes = editor.texto;
  editor.desfazer();
  return [antes, editor.texto];
}
```
