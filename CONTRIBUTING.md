# Contribuindo com o projeto

Atualmente, o projeto está sendo mantido por [SwiftNathalie](https://github.com/swiftnathalie), responsável pelo design e manutenção do `Utopiafy`. Contribuições e sugestões são sempre bem-vindas, mas há certas considerações à serem feitas antes de começar.

- Comunicação é uma peça-chave; caso esteja em dúvida sobre qualquer coisa, não hesite em perguntar para os desenvolvedores.

- Embora o projeto seja mantido por uma única pessoa, o código é aberto para qualquer um que desejar contribuir ou copiar. Caso deseje possuir uma cópia do projeto, bifurque-o e faça as alterações que desejar.


# Configurando seu ambiente de desenvolvimento
### Pré-requisitos

Antes de começar, você precisa ter instalado em sua máquina:

- [Python ^3.8](https://www.python.org/downloads/release/python-380/)
- [Git](https://git-scm.com/downloads)
- [Poetry](https://python-poetry.org/docs/#installation)
- [Bash/Zsh](https://www.gnu.org/software/bash/)

Além disso, é recomendado que você possua um editor de texto, como o [VSCode](https://code.visualstudio.com/), [Sublime Text](https://www.sublimetext.com/) ou [Atom](https://atom.io/).


### Variáveis de ambiente

No intuito de facilitar a replicação do projeto em outros ambientes, o projeto utiliza variáveis de ambiente para armazenar informações sensíveis e únicas, como Tokens, Chaves de API, IDs de usuários, etc. Para isso, é necessário criar um arquivo `.env` na raíz do projeto, e preencher as variáveis necessárias.

Segue uma lista de variáveis utilizadas pelo projeto:

| Variável | Padrão | Descrição |
| -------- | ------- | ----------- |
| `TOKEN` | | Token de acesso do bot |
| `PREFIX` | `==` | Prefixo utilizado para invocar os comandos do bot |
| `GUILD_ID` | | ID do servidor do Discord |
| `HTTPX_CLIENT` |  | Credenciais do cliente HTTP |

### Instalando dependências

O projeto utiliza o [Poetry](https://python-poetry.org/) para gerenciar suas dependências. Para instalar as dependências do projeto, execute o seguinte comando:

```bash
poetry install
```

# Executando o projeto

Para executar o projeto, execute o seguinte comando:

```bash
python -m bot
```

### Executando os testes

Para executar os testes do projeto, execute o seguinte comando:

```bash
poetry run pytest
```
