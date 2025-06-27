Leia-me

Sistema de Inventário com Bot do Telegram e Dashboard v1.0
Este projeto implementa um sistema completo para contagem de inventário, operado através de um bot no Telegram e visualizado através de um dashboard web local. Ele permite o cadastro de produtos, múltiplas etapas de contagem e a exportação de relatórios detalhados.

Autor: GhostC0der

Funcionalidades
Gestão via Bot do Telegram: Toda a operação (cadastro, contagem, início/fim de inventário) é feita através de uma interface de botões intuitiva no Telegram.

Cadastro de Produtos: Módulo para criar uma lista mestra de produtos com código e descrição.

Ciclo de Inventário Completo: Permite iniciar um evento de inventário, realizar até 4 etapas de contagem (Inicial + 3 Recontagens) e encerrá-lo.

Exportação de Relatórios: Ao encerrar um inventário, o sistema gera e salva automaticamente relatórios em formato .csv para cada etapa de contagem.

Dashboard Web Local: Uma interface web para visualizar o status do inventário atual, o histórico de inventários passados e baixar relatórios.

Relatório Comparativo: Página especial no dashboard que mostra as contagens lado a lado, destacando automaticamente as divergências para análise rápida.

Armazenamento Persistente: Utiliza um banco de dados SQLite para guardar todos os dados de forma segura.

Tecnologias Utilizadas
Backend:Python
Bot: python-telegram-bot
Dashboard Web: Flask
Manipulação de Dados: pandas
Banco de Dados: SQLite3

Estrutura do Projeto
/
├── bot_inventario.py       # Script principal do bot do Telegram
├── dashboard.py            # Script da aplicação web Flask
├── requirements.txt        # Lista de dependências Python
├── pyproject.toml          # Arquivo de configuração do projeto
├── .gitignore              # Arquivos a serem ignorados pelo Git
├── inventario.db           # Banco de dados (criado na primeira execução)
├── /templates/             # Pasta para os arquivos HTML do dashboard
│   ├── index.html
│   ├── detalhes_inventario.html
│   └── comparativo.html
├── /relatorios/            # Pasta onde os relatórios CSV são salvos
└── /cadastros/             # Pasta onde a lista de produtos é salva


Instalação
Siga os passos abaixo para configurar e rodar o projeto em seu ambiente local.
1. Pré-requisitos:Python 3.8 ou superiorGit
2. Clone o Repositório:git clone <URL_DO_SEU_REPOSITORIO_GIT>
cd <NOME_DA_PASTA_DO_PROJETO>
3. Crie um Ambiente Virtual (Recomendado):# Windows
python -m venv venv
venv\Scripts\activate
# macOS / Linux
python3 -m venv venv
source venv/bin/activate
4. Instale as Dependências:O projeto utiliza as bibliotecas listadas no arquivo requirements.txt. Instale-as com o pip:
pip install -r requirements.txt

Configuração
Antes de iniciar o sistema, você precisa obter um token de acesso para o seu bot do Telegram.
No Telegram, procure pelo bot oficial BotFather.
Inicie uma conversa e envie o comando /newbot.
Siga as instruções para dar um nome e um nome de usuário ao seu bot.O BotFather irá fornecer um token de acesso.
 Copie este token.Abra o arquivo bot_inventario.py e cole o seu token na linha:application = Application.builder().token("SEU_TOKEN_AQUI").build()

Uso

Para iniciar o sistema (bot e dashboard simultaneamente), execute o seguinte comando no seu terminal, na pasta raiz do projeto:python bot_inventario.py
Bot do Telegram: Encontre seu bot no Telegram e envie o comando /start para ver o menu principal.
Dashboard Web: Abra seu navegador e acesse o endereço http://127.0.0.1:5000.Exemplos de Entrada e SaídaEntrada (Telegram):Clicar em Contagem -> Iniciar Novo Inventário.
Enviar o nome: Inventário Mensal Julho
Clicar em Contagem Inicial, enviar o código 12345 e a quantidade 100.
Saída (Telegram):O bot confirma o registro.Ao encerrar, o bot envia os arquivos .csv no chat.
Saída (Arquivos Locais):O relatório é salvo em: /relatorios/ID_Inventário_Mensal_Julho/Inicial.csv.

Como Contribuir
Este projeto é open source e contribuições são bem-vindas!
Faça um Fork do projeto no GitHub.
Crie uma Branch para sua nova funcionalidade (git checkout -b feature/NovaFuncionalidade).
Faça o Commit de suas alterações (git commit -m 'Adiciona NovaFuncionalidade').
Faça o Push para a sua branch (git push origin feature/NovaFuncionalidade).
Abra um Pull Request.

LicençaEste projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.


Readme

Inventory System with Telegram Bot and Dashboard v1.0
This project implements a complete inventory counting system, operated through a Telegram bot and viewed through a local web dashboard. It allows product registration, multiple counting steps and export of detailed reports.

Author: GhostC0der

Features
Management via Telegram Bot: The entire operation (registration, counting, start/end of inventory) is done through an intuitive button interface in Telegram.

Product Registration: Module to create a master list of products with code and description.

Full Inventory Cycle: Allows you to start an inventory event, perform up to 4 counting steps (Initial + 3 Recounts) and end it.

Export Reports: When ending an inventory, the system automatically generates and saves reports in .csv format for each counting step.

Local Web Dashboard: A web interface to view current inventory status, past inventory history, and download reports.

Comparative Report: A dedicated dashboard page that displays counts side by side, automatically highlighting discrepancies for quick analysis.

Persistent Storage: Uses a SQLite database to securely store all data.

Technologies Used
Backend: Python
Bot: python-telegram-bot
Web Dashboard: Flask
Data Manipulation: pandas
Database: SQLite3

Project Structure
/
├── bot_inventario.py # Main script for the Telegram bot
├── dashboard.py # Flask web application script
├── requirements.txt # List of Python dependencies
├── pyproject.toml # Project configuration file
├── .gitignore # Files to be ignored by Git
├── inventory.db # Database (created on first run)
├── /templates/ # Folder for dashboard HTML files
│ ├── index.html
│ ├──detalhes_inventario.html
│ └──comparativo.html
├── /relatorios/ # Folder where CSV reports are saved
└── /cadastros/ # Folder where the product list is saved

Installation
Follow the steps below to configure and run the project in your local environment. 1. Prerequisites:Python 3.8 or higherGit
2. Clone the Repository:git clone <YOUR_GIT_REPOSITORY_URL>
cd <PROJECT_FOLDER_NAME>
3. Create a Virtual Environment (Recommended):# Windows
python -m venv venv
venv\Scripts\activate
# macOS / Linux
python3 -m venv venv
source venv/bin/activate
4. Install Dependencies:The project uses the libraries listed in the requirements.txt file. Install them with pip:
pip install -r requirements.txt

Configuration
Before starting the system, you need to obtain an access token for your Telegram bot.
In Telegram, search for the official BotFather bot.
Start a chat and send the /newbot command.
Follow the instructions to give your bot a name and username. BotFather will provide you with an access token.
Copy this token.Open the bot_inventory.py file and paste your token in the line:application = Application.builder().token("YOUR_TOKEN_HERE").build()

Usage

To start the system (bot and dashboard simultaneously), run the following command in your terminal, in the project root folder:python bot_inventory.py
Telegram Bot: Find your bot on Telegram and send the command /start to see the main menu.
Web Dashboard: Open your browser and access the address http://127.0.0.1:5000.Examples of Input and OutputInput (Telegram):Click on Count -> Start New Inventory.
Send the name: Monthly Inventory July
Click on Initial Count, send the code 12345 and the quantity 100.
Output (Telegram): The bot confirms the registration. When finished, the bot sends the .csv files in the chat.
Output (Local Files): The report is saved in: /reports/ID_Inventário_Mensal_Julho/Inicial.csv.

How to Contribute
This project is open source and contributions are welcome!
Fork the project on GitHub.
Create a Branch for your new feature (git checkout -b feature/NovaFuncionalidade).
Commit your changes (git commit -m 'Adiciona NovaFuncionalidade').
Push it to your branch (git push origin feature/NovaFuncionalidade).
Open a Pull Request.

LicenseThis project is under the MIT license. See the LICENSE file for more details.
