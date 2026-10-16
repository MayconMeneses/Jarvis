<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__NOME__</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main>
    <h1>__NOME__</h1>
    <form id="formulario">
      <label for="titulo" class="sr-only">Nova tarefa</label>
      <input id="titulo" name="titulo" placeholder="O que precisa ser feito?" maxlength="200" required autofocus>
      <button type="submit">Adicionar</button>
    </form>
    <p id="aviso" role="status"></p>
    <ul id="lista" aria-label="Tarefas"></ul>
  </main>
  <script src="app.js"></script>
</body>
</html>
