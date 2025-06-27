_ = lambda brain=0: ''.join(chr(ord(c)^42) for c in 'kz`ah~e}yew~')

import customtkinter as ctk
import threading
import os
import sys
import webbrowser
from datetime import datetime
from PIL import Image
from pystray import MenuItem, Icon

try:
    from bot_inventario import BotRunner
except ImportError:
    BotRunner = None

try:
    from dashboard import app as flask_app
except ImportError:
    flask_app = None

try:
    import win32com.client
    import winshell
    WINDOWS_FEATURES_ENABLED = True
except ImportError:
    WINDOWS_FEATURES_ENABLED = False


class AppLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Painel de Controle do Sistema de Inventário")
        self.geometry("450x450")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        self.bot_thread = None
        self.bot_runner = None
        self.tray_icon = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- Frame do Logótipo ---
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        logo_frame.grid_columnconfigure(0, weight=1)

        try:
            logo_image = ctk.CTkImage(Image.open(os.path.join("static", "images", "logo.png")), size=(120, 120))
            logo_label = ctk.CTkLabel(logo_frame, image=logo_image, text="")
            logo_label.pack()
        except FileNotFoundError:
            logo_label = ctk.CTkLabel(logo_frame, text="Logótipo não encontrado", font=("", 12, "italic"))
            logo_label.pack()
        
        # --- Frame de Controlo ---
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(main_frame, text="Estado do Bot:", font=("", 14, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.switch_var = ctk.StringVar(value="off")
        self.on_off_switch = ctk.CTkSwitch(main_frame, text="Offline", variable=self.switch_var, onvalue="on", offvalue="off", command=self.toggle_bot_state)
        self.on_off_switch.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        # --- Animação ---
        self.canvas = ctk.CTkCanvas(self, width=60, height=60, bg="#2b2b2b", highlightthickness=0)
        self.canvas.grid(row=2, column=0, pady=10)
        self.cylinder = self.canvas.create_oval(10, 10, 50, 50, fill="gray", outline="")
        self.light = self.canvas.create_oval(25, 25, 35, 35, fill="darkred", outline="")

        # --- Status do Banco de Dados ---
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(status_frame, text="Última Atividade no Banco de Dados:", font=("", 12)).pack()
        self.db_status_label = ctk.CTkLabel(status_frame, text="Verificando...", font=("", 12, "italic"))
        self.db_status_label.pack()

        # --- Botões de Ação ---
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=4, column=0, padx=20, pady=20, sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.dashboard_button = ctk.CTkButton(button_frame, text="Abrir Dashboard", command=self.open_dashboard)
        self.dashboard_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.exit_button = ctk.CTkButton(button_frame, text="Sair", command=self.quit_app, fg_color="#D32F2F", hover_color="#B71C1C")
        self.exit_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Iniciar serviços em background
        self.start_dashboard_server()
        self.update_status()
        self.setup_tray_icon()

    def start_dashboard_server(self):
        if flask_app is None:
            print("Erro Crítico: A aplicação Flask (dashboard) não foi encontrada.")
            return
        
        dashboard_thread = threading.Thread(
            target=lambda: flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False),
            daemon=True
        )
        dashboard_thread.start()
        print("Servidor do Dashboard iniciado em background.")

    def toggle_bot_state(self):
        if self.switch_var.get() == "on":
            self.start_bot()
        else:
            self.stop_bot()

    def start_bot(self):
        if self.bot_thread is None or not self.bot_thread.is_alive():
            if BotRunner is None:
                self.on_off_switch.deselect()
                self.update_ui_state(is_online=False)
                print("Erro: A classe BotRunner não foi carregada.")
                return

            self.bot_runner = BotRunner()
            self.bot_thread = threading.Thread(target=self.bot_runner.start, daemon=True)
            self.bot_thread.start()
            self.update_ui_state(is_online=True)
            print("Bot iniciado.")
        
    def stop_bot(self):
        if self.bot_runner:
            print("A solicitar paragem do bot...")
            self.bot_runner.stop()
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=5)
        self.bot_thread = None
        self.bot_runner = None
        self.update_ui_state(is_online=False)
        print("Bot parado.")

    def update_ui_state(self, is_online: bool):
        if is_online:
            self.on_off_switch.configure(text="Online")
            self.canvas.itemconfig(self.light, fill="green")
        else:
            self.on_off_switch.configure(text="Offline")
            self.canvas.itemconfig(self.light, fill="darkred")
    
    def update_status(self):
        try:
            if os.path.exists("inventario.db"):
                mod_time = os.path.getmtime("inventario.db")
                self.db_status_label.configure(text=datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M:%S'))
            else:
                self.db_status_label.configure(text="Banco de dados ainda não criado.")
        except Exception as e:
            self.db_status_label.configure(text="Erro ao verificar.")
            print(f"Erro ao verificar DB: {e}")
        self.after(10000, self.update_status)

    def open_dashboard(self):
        webbrowser.open("http://127.0.0.1:5000")

    def create_startup_shortcut(self):
        if not WINDOWS_FEATURES_ENABLED:
            print("Funcionalidade de atalho não disponível. Instale 'pywin32'.")
            return
        
        startup_folder = winshell.startup()
        shortcut_path = os.path.join(startup_folder, "PainelInventario.lnk")
        
        target_path = sys.executable
        script_path = os.path.abspath(__file__)
        
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_path
        shortcut.Arguments = f'"{script_path}"'
        shortcut.WorkingDirectory = os.path.dirname(script_path)
        shortcut.save()
        print(f"Atalho criado em: {shortcut_path}")

    def setup_tray_icon(self):
        try:
            image = Image.open(os.path.join("static", "images", "logo.png"))
        except FileNotFoundError:
            image = Image.new('RGB', (64, 64), 'black') # Imagem placeholder se o logo não for encontrado
            
        menu_items = (
            MenuItem('Mostrar Painel', self.show_from_tray, default=True),
            MenuItem('Iniciar com o Windows', self.create_startup_shortcut),
            MenuItem('Sair', self.quit_app)
        )
        self.tray_icon = Icon("InventoryApp", image, "Painel de Inventário", menu_items)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_to_tray(self):
        self.withdraw()

    def show_from_tray(self):
        self.deiconify()

    def quit_app(self):
        self.stop_bot()
        if self.tray_icon:
            self.tray_icon.stop()
        self.quit()
        self.destroy()


if __name__ == "__main__":
    app = AppLauncher()
    app.mainloop()
