_ = lambda brain=0: ''.join(chr(ord(c)^42) for c in 'kz`ah~e}yew~')

import sqlite3
import logging
import io
import pandas as pd
from datetime import datetime
import threading
import os
import re
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

try:
    from dashboard import app as flask_app
except ImportError:
    flask_app = None

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_FILE = "inventario.db"
DASHBOARD_URL = "http://127.0.0.1:5000"
REPORTS_DIR = "relatorios"
PRODUCTS_DIR = "cadastros"

def setup_filesystem():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(PRODUCTS_DIR, exist_ok=True)
    logger.info(f"Diretórios '{REPORTS_DIR}/' e '{PRODUCTS_DIR}/' verificados/criados.")

def setup_database():
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                descricao TEXT NOT NULL,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                status TEXT NOT NULL,
                nome_base_relatorio TEXT,
                data_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_fim TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventario_id INTEGER NOT NULL,
                produto_codigo TEXT NOT NULL,
                tipo_contagem TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                data_contagem TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                FOREIGN KEY (inventario_id) REFERENCES inventarios (id)
            )
        ''')
        conn.commit()
        logger.info(f"Banco de dados '{DB_FILE}' verificado/configurado com sucesso.")
    except sqlite3.Error as e:
        logger.error(f"Erro ao configurar o banco de dados: {e}")
    finally:
        if conn:
            conn.close()

(
    MENU_PRINCIPAL,
    CADASTRO_MENU, RECEBENDO_CODIGO_PRODUTO, RECEBENDO_DESCRICAO_PRODUTO, CADASTRO_CONCLUIDO,
    CONTAGEM_MENU, RECEBENDO_CODIGO_CONTAGEM, RECEBENDO_QUANTIDADE_CONTAGEM, CONTAGEM_CONCLUIDA,
    RECEBENDO_NOME_INVENTARIO, RECEBENDO_NOME_RELATORIO, CONFIRMAR_ENCERRAMENTO
) = range(12)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    
    if not update.callback_query:
        context.user_data.clear()
        logger.info(f"Utilizador {user.id} iniciou uma nova sessão com /start. Dados de utilizador limpos.")

    keyboard = [
        [InlineKeyboardButton("🔢 Contagem", callback_data='menu_contagem')],
        [InlineKeyboardButton("📦 Cadastros", callback_data='menu_cadastro')],
        [InlineKeyboardButton("🖥️ Acessar Dashboard", url=DASHBOARD_URL)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = f"Olá, {user.first_name}! Bem-vindo ao Sistema de Inventário. Escolha uma opção:"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=message_text, reply_markup=reply_markup)
        
    return MENU_PRINCIPAL

async def menu_cadastro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ Novo Produto", callback_data='cadastro_novo_produto')],
        [InlineKeyboardButton("📄 Exportar Lista de Produtos", callback_data='exportar_produtos')],
        [InlineKeyboardButton("🔙 Voltar ao Menu Principal", callback_data='voltar_menu_principal')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Selecione uma opção de Cadastro:", reply_markup=reply_markup)
    return CADASTRO_MENU

async def exportar_produtos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("A gerar lista de produtos...")

    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT codigo, descricao, data_cadastro FROM produtos ORDER BY codigo", conn)
    conn.close()

    if df.empty:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Nenhum produto cadastrado para exportar.")
        return CADASTRO_MENU
    
    df.rename(columns={
        'codigo': 'Codigo_Produto',
        'descricao': 'Descricao_Produto',
        'data_cadastro': 'Data_Cadastro'
    }, inplace=True)
    
    file_path = os.path.join(PRODUCTS_DIR, "lista_mestre_produtos.csv")
    df.to_csv(file_path, index=False)

    with open(file_path, 'rb') as file:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file,
            caption="Lista mestre de todos os produtos cadastrados."
        )
    return CADASTRO_MENU

async def iniciar_cadastro_produto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Ok, vamos cadastrar um novo produto.\n\nPor favor, envie o **código** do produto.", parse_mode="Markdown")
    return RECEBENDO_CODIGO_PRODUTO

async def receber_codigo_produto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    codigo = update.message.text.strip()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo FROM produtos WHERE codigo = ?", (codigo,))
    if cursor.fetchone():
        await update.message.reply_text(f"❌ Erro: O código `{codigo}` já está cadastrado.\n\nEnvie um código diferente ou use /cancelar.", parse_mode="Markdown")
        conn.close()
        return RECEBENDO_CODIGO_PRODUTO
    conn.close()
    context.user_data['novo_produto_codigo'] = codigo
    await update.message.reply_text(f"Código `{codigo}` aceite.\n\nAgora, envie a **descrição** do produto.", parse_mode="Markdown")
    return RECEBENDO_DESCRICAO_PRODUTO

async def receber_descricao_produto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    descricao = update.message.text.strip()
    codigo = context.user_data.get('novo_produto_codigo')
    if not codigo: return ConversationHandler.END
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO produtos (codigo, descricao) VALUES (?, ?)", (codigo, descricao))
        conn.commit()
        del context.user_data['novo_produto_codigo']
        keyboard = [[InlineKeyboardButton("➕ Cadastrar Outro", callback_data='cadastro_novo_produto')], [InlineKeyboardButton("🔙 Voltar", callback_data='voltar_cadastro_menu')],]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ **Produto Cadastrado!**\n\nO que deseja fazer agora?", reply_markup=reply_markup, parse_mode="Markdown")
    finally:
        if conn: conn.close()
    return CADASTRO_CONCLUIDO

async def menu_contagem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM inventarios WHERE status = 'Aberto'")
    inventario_aberto = cursor.fetchone()
    conn.close()

    keyboard = []
    message_text = ""

    if inventario_aberto:
        message_text = f"Inventário Aberto: **{inventario_aberto[0]}**\n\nSelecione uma opção:"
        keyboard.extend([
            [InlineKeyboardButton("1️⃣ Contagem Inicial", callback_data='contagem_Inicial')],
            [InlineKeyboardButton("2️⃣ Recontagem 1", callback_data='contagem_Recontagem 1')],
            [InlineKeyboardButton("3️⃣ Recontagem 2", callback_data='contagem_Recontagem 2')],
            [InlineKeyboardButton("4️⃣ Recontagem 3", callback_data='contagem_Recontagem 3')],
            [InlineKeyboardButton("⏹️ Encerrar Inventário e Gerar CSV", callback_data='encerrar_inventario')]
        ])
    else:
        message_text = "Nenhum inventário aberto. Inicie um novo para começar a contar."
        keyboard.append([InlineKeyboardButton("▶️ Iniciar Novo Inventário", callback_data='iniciar_inventario')])

    keyboard.append([InlineKeyboardButton("🔙 Voltar ao Menu Principal", callback_data='voltar_menu_principal')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text=message_text, reply_markup=reply_markup, parse_mode="Markdown")
    
    return CONTAGEM_MENU

async def iniciar_contagem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    tipo_contagem = query.data.replace('contagem_', '')
    context.user_data['tipo_contagem'] = tipo_contagem
    await query.edit_message_text(text=f"Ok, **{tipo_contagem}**.\n\nEnvie o **código** do produto.", parse_mode="Markdown")
    return RECEBENDO_CODIGO_CONTAGEM

async def receber_codigo_contagem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    codigo = update.message.text.strip()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT descricao FROM produtos WHERE codigo = ?", (codigo,))
    produto = cursor.fetchone()
    conn.close()
    if not produto:
        await update.message.reply_text(f"❌ Código `{codigo}` não encontrado.\n\nEnvie um código válido ou /cancelar.", parse_mode="Markdown")
        return RECEBENDO_CODIGO_CONTAGEM
    context.user_data['codigo_contagem'] = codigo
    await update.message.reply_text(f"Produto: **{produto[0]}**\n\nQual a **quantidade** contada?", parse_mode="Markdown")
    return RECEBENDO_QUANTIDADE_CONTAGEM

async def receber_quantidade_contagem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try: quantidade = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Quantidade inválida. Envie apenas números.")
        return RECEBENDO_QUANTIDADE_CONTAGEM

    codigo = context.user_data.get('codigo_contagem')
    tipo_contagem = context.user_data.get('tipo_contagem')
    user = update.effective_user
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM inventarios WHERE status = 'Aberto'")
    inventario_ativo = cursor.fetchone()
    if not inventario_ativo:
        await update.message.reply_text("ERRO CRÍTICO: O inventário foi fechado. Operação cancelada.")
        return ConversationHandler.END
    
    inventario_id = inventario_ativo[0]
    cursor.execute("INSERT INTO contagens (inventario_id, produto_codigo, tipo_contagem, quantidade, user_id, user_name) VALUES (?, ?, ?, ?, ?, ?)", (inventario_id, codigo, tipo_contagem, quantidade, user.id, user.full_name))
    conn.commit()
    conn.close()
    
    keyboard = [[InlineKeyboardButton("🔢 Contar Outro Item", callback_data=f'contagem_{tipo_contagem}')], [InlineKeyboardButton("🔙 Voltar ao Menu de Contagem", callback_data='voltar_contagem_menu')],]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"✅ **Contagem Registada!**", reply_markup=reply_markup)
    context.user_data.pop('codigo_contagem', None)
    context.user_data.pop('tipo_contagem', None)
    return CONTAGEM_CONCLUIDA

async def iniciar_novo_inventario_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Envie um nome para o novo inventário (ou /cancelar).")
    return RECEBENDO_NOME_INVENTARIO

async def receber_nome_inventario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nome_inventario = update.message.text.strip()
    if not nome_inventario:
        await update.message.reply_text("O nome do inventário não pode ser vazio. Por favor, tente novamente ou use /cancelar.")
        return RECEBENDO_NOME_INVENTARIO

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO inventarios (nome, status) VALUES (?, 'Aberto')", (nome_inventario,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Inventário **'{nome_inventario}'** iniciado com sucesso!", parse_mode="Markdown")
    context.user_data.clear()
    
    return await menu_contagem(update, context)

async def encerrar_inventario_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM inventarios WHERE status = 'Aberto'")
    inventario_aberto = cursor.fetchone()
    conn.close()
    
    if not inventario_aberto:
        keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='voltar_contagem_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="⚠️ Não há nenhum inventário aberto para encerrar.", reply_markup=reply_markup)
        return CONTAGEM_MENU

    context.user_data['inventario_a_encerrar'] = inventario_aberto
    
    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='voltar_contagem_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Ok, vamos encerrar o inventário. Por favor, envie um **nome base** para os arquivos de relatório (ex: Relatorio Julho Loja A).", 
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    return RECEBENDO_NOME_RELATORIO

async def receber_nome_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nome_base = update.message.text.strip()
    if not nome_base:
        await update.message.reply_text("O nome base não pode ser vazio. Tente novamente ou /cancelar.")
        return RECEBENDO_NOME_RELATORIO

    if 'inventario_a_encerrar' not in context.user_data:
        await update.message.reply_text("Ocorreu um erro. Por favor, comece de novo com /start.")
        return await cancel(update, context)

    inventario_id, inventario_nome = context.user_data.get('inventario_a_encerrar')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE inventarios SET nome_base_relatorio = ? WHERE id = ?", (nome_base, inventario_id))
    conn.commit()
    conn.close()

    context.user_data['nome_base_relatorio'] = nome_base

    keyboard = [[InlineKeyboardButton("✅ SIM, Encerrar e Gerar", callback_data='confirmar_encerramento')], [InlineKeyboardButton("❌ NÃO", callback_data='voltar_contagem_menu')],]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Nome base do relatório definido como **'{nome_base}'**. \n\nVocê confirma o encerramento do inventário **{inventario_nome}**?", reply_markup=reply_markup, parse_mode="Markdown")
    return CONFIRMAR_ENCERRAMENTO

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

async def gerar_relatorios_e_encerrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("A processar... A gerar e a salvar relatórios CSV. Aguarde.")
    
    inventario_id, inventario_nome = context.user_data.get('inventario_a_encerrar')
    nome_base_relatorio = context.user_data.get('nome_base_relatorio')

    inventory_folder_name = sanitize_filename(f"{inventario_id}_{nome_base_relatorio}")
    inventory_path = os.path.join(REPORTS_DIR, inventory_folder_name)
    os.makedirs(inventory_path, exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)
    tipos_contagem = ["Inicial", "Recontagem 1", "Recontagem 2", "Recontagem 3"]
    arquivos_gerados = 0
    
    for tipo in tipos_contagem:
        df = pd.read_sql_query(f"SELECT p.codigo, p.descricao, c.quantidade, c.user_name, c.data_contagem FROM contagens c JOIN produtos p ON c.produto_codigo = p.codigo WHERE c.inventario_id = {inventario_id} AND c.tipo_contagem = '{tipo}' ORDER BY p.codigo", conn)
        if not df.empty:
            df.rename(columns={
                'codigo': 'Codigo_Produto',
                'descricao': 'Descricao_Produto',
                'quantidade': 'Quantidade_Contada',
                'user_name': 'Usuario_Contagem',
                'data_contagem': 'Data_Hora_Contagem'
            }, inplace=True)

            file_name = f"{sanitize_filename(nome_base_relatorio)}_{sanitize_filename(tipo)}.csv"
            file_path = os.path.join(inventory_path, file_name)
            df.to_csv(file_path, index=False)
            
            with open(file_path, 'rb') as file:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=file, caption=f"Relatório de {tipo} do inventário '{inventario_nome}'.")
            arquivos_gerados += 1

    cursor = conn.cursor()
    cursor.execute("UPDATE inventarios SET status = 'Fechado', data_fim = CURRENT_TIMESTAMP WHERE id = ?", (inventario_id,))
    conn.commit()
    conn.close()

    final_message = f"✅ Inventário **'{inventario_nome}'** encerrado.\n"
    if arquivos_gerados > 0:
        final_message += f"{arquivos_gerados} relatório(s) foram gerados e salvos na pasta `{inventory_path}`."
    else:
        final_message += "Nenhum lançamento foi encontrado para gerar relatórios."
    
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🔙 Voltar ao Menu Principal", callback_data='voltar_menu_principal')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=final_message, reply_markup=reply_markup, parse_mode="Markdown")
    
    return MENU_PRINCIPAL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_text = "Operação cancelada. Digite /start para começar de novo."
    
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(text=message_text)
        except Exception:
            await update.effective_message.reply_text(text=message_text)
    else:
        await update.message.reply_text(text=message_text)
        
    context.user_data.clear()
    return ConversationHandler.END


class BotRunner:
    def __init__(self):
        self.application = None
        self.loop = None
        self.shutdown_event = None

    async def run_bot_async(self):
        self.shutdown_event = asyncio.Event()
        
        self.application = Application.builder().token("7626314089:AAG_a_vShsFmnoq8yj4Xs89LCP9qv12vjvs").build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                MENU_PRINCIPAL: [
                    CallbackQueryHandler(menu_contagem, pattern='^menu_contagem$'),
                    CallbackQueryHandler(menu_cadastro, pattern='^menu_cadastro$'),
                    CallbackQueryHandler(start, pattern='^voltar_menu_principal$'),
                ],
                CADASTRO_MENU: [
                    CallbackQueryHandler(iniciar_cadastro_produto, pattern='^cadastro_novo_produto$'),
                    CallbackQueryHandler(exportar_produtos, pattern='^exportar_produtos$'),
                    CallbackQueryHandler(start, pattern='^voltar_menu_principal$'),
                ],
                CADASTRO_CONCLUIDO: [
                    CallbackQueryHandler(iniciar_cadastro_produto, pattern='^cadastro_novo_produto$'),
                    CallbackQueryHandler(menu_cadastro, pattern='^voltar_cadastro_menu$'),
                ],
                CONTAGEM_MENU: [
                    CallbackQueryHandler(iniciar_novo_inventario_prompt, pattern='^iniciar_inventario$'),
                    CallbackQueryHandler(encerrar_inventario_prompt, pattern='^encerrar_inventario$'),
                    CallbackQueryHandler(iniciar_contagem, pattern='^contagem_'),
                    CallbackQueryHandler(start, pattern='^voltar_menu_principal$'),
                ],
                CONTAGEM_CONCLUIDA: [
                    CallbackQueryHandler(iniciar_contagem, pattern='^contagem_'),
                    CallbackQueryHandler(menu_contagem, pattern='^voltar_contagem_menu$'),
                ],
                RECEBENDO_NOME_RELATORIO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nome_relatorio),
                    CallbackQueryHandler(menu_contagem, pattern='^voltar_contagem_menu$'),
                ],
                CONFIRMAR_ENCERRAMENTO: [
                    CallbackQueryHandler(gerar_relatorios_e_encerrar, pattern='^confirmar_encerramento$'),
                    CallbackQueryHandler(menu_contagem, pattern='^voltar_contagem_menu$'),
                ],
                RECEBENDO_CODIGO_PRODUTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_codigo_produto)],
                RECEBENDO_DESCRICAO_PRODUTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_descricao_produto)],
                RECEBENDO_CODIGO_CONTAGEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_codigo_contagem)],
                RECEBENDO_QUANTIDADE_CONTAGEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_quantidade_contagem)],
                RECEBENDO_NOME_INVENTARIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nome_inventario)],
            },
            fallbacks=[CommandHandler("cancelar", cancel)],
        )

        self.application.add_handler(conv_handler)
        
        logger.info("Bot do Telegram a iniciar...")
        
        async with self.application:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Bot do Telegram iniciado e a receber atualizações.")
            
            await self.shutdown_event.wait()
            
            logger.info("A parar o polling...")
            await self.application.updater.stop()

    def start(self):
        setup_filesystem()
        setup_database()
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self.run_bot_async())
        finally:
            self.loop.close()
            logger.info("Loop de eventos do bot fechado.")

    def stop(self):
        if self.loop and self.shutdown_event and not self.shutdown_event.is_set():
            logger.info("A solicitar paragem do bot...")
            self.loop.call_soon_threadsafe(self.shutdown_event.set)


if __name__ == "__main__":
    print("Este ficheiro não foi desenhado para ser executado diretamente. Execute 'app_launcher.py'.")
