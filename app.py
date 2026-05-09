# app.py  —  StrangerTEC Morse Translator
# Aplicación de PC — Interfaz Gráfica en Tkinter
# Python 3.x  |  CE-1104 TEC  |  I Sem. 2026

# DESCRIPCIÓN:
#   Interfaz gráfica principal del juego. Se comunica con
#   el Pico W por puerto serial USB.
#
# PANTALLAS:
#   1. Pantalla de inicio  (animación / título)
#   2. Pantalla de configuración (puerto, velocidad, frases, modo)
#   3. Pantalla de juego   (frase, abecedario, Morse en tiempo real)
#   4. Pantalla de resultado (puntajes, ganador, nueva ronda)
#
# REQUISITOS:
#   pip install pyserial

# USO:
#   1. Conectar Pico W por USB
#   2. Cargar main.py en el Pico desde Thonny
#   3. Ejecutar: python app.py

import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
import threading
import time
import random
import serial
import serial.tools.list_ports


# CONSTANTES DE DISEÑO — TEMA STRANGER THINGS
BG_DARK    = "#020005"      # Fondo principal oscuro
BG_PANEL   = "#0a0015"      # Fondo de paneles
BG_INPUT   = "#000000"      # Fondo de campos de texto
RED        = "#e8001c"      # Rojo Stranger Things
RED_DARK   = "#8b0010"      # Rojo oscuro
ORANGE     = "#ff6a00"      # Naranja brillante
AMBER      = "#ffaa00"      # Ámbar/dorado
GREEN_OK   = "#00ff41"      # Verde éxito
DIM        = "#5a3a3a"      # Gris apagado para letras sin iluminar
WHITE      = "#e8c9d0"      # Blanco cálido para texto
BORDER     = "#3a0008"      # Color de borde de paneles

# Fuentes
FONT_TITLE  = ("Courier New", 32, "bold")
FONT_SUB    = ("Courier New", 13, "bold")
FONT_MONO   = ("Courier New", 12)
FONT_MORSE  = ("Courier New", 28, "bold")
FONT_LETTER = ("Courier New", 22, "bold")
FONT_SMALL  = ("Courier New", 10)
FONT_BTN    = ("Courier New", 12, "bold")
FONT_SCORE  = ("Courier New", 36, "bold")

# Tabla Morse completa (carácter → código)
MORSE_ENCODE = {
    'A':'.-',   'B':'-...', 'C':'-.-.', 'D':'-..',
    'E':'.',    'F':'..-.', 'G':'--.',  'H':'....',
    'I':'..',   'J':'.---', 'K':'-.-', 'L':'.-..',
    'M':'--',   'N':'-.',   'O':'---',  'P':'.--.',
    'Q':'--.-', 'R':'.-.',  'S':'...',  'T':'-',
    'U':'..-',  'V':'...-', 'W':'.--',  'X':'-..-',
    'Y':'-.--', 'Z':'--..',
    '0':'-----','1':'.----','2':'..---','3':'...--',
    '4':'....-','5':'.....','6':'-....','7':'--...',
    '8':'---..','9':'----.',
    '+':'.-.-.','-':'-....-',
}

# Layout del panel de letras (según enunciado Figura 4)
FILA1 = list("ACEGIKMOQSUWY")
FILA2 = list("BDFHJLNPRTVXZ")
FILA3 = list("0123456789-+")

# Frases por defecto (mínimas del enunciado + extras)
DEFAULT_PHRASES = [
    "SOS",
    "SI",
    "NO",
    "HELP ME",
    "RUN NOW",
    "IM ALIVE",
    "DANGER",
    "HIDE NOW",
    "COME HOME",
    "TRUST ME",
]


# CLASE PRINCIPAL DE LA APLICACIÓN


class StrangerTECApp:
    """
    Aplicación principal. Gestiona todas las pantallas y
    la comunicación serial con el Pico W.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("StrangerTEC Morse Translator")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(False, False)

        # Centrar ventana
        w, h = 900, 680
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # Estado del juego 
        self.serial_conn   = None        # Conexión serial
        self.serial_port   = tk.StringVar(value="")
        self.unit_ms       = tk.IntVar(value=200)   # Unidad A=200, B=300
        self.trans_mode    = tk.StringVar(value="SIMPLE")  # SIMPLE o LISTEN
        self.phrases       = list(DEFAULT_PHRASES)  # Lista editable
        self.current_phrase = ""
        self.scores        = [0, 0]     # [jugador A, jugador B]
        self.round_num     = 1
        self.current_player = 1         # 1=A, 2=B
        self.player_input  = ""         # Texto decodificado del Pico
        self.morse_buffer  = ""         # Símbolos acumulados en tiempo real
        self.game_active   = False

        # Hilo de lectura serial 
        self._serial_thread = None
        self._stop_serial   = threading.Event()

        # Frame contenedor 
        self.container = tk.Frame(self.root, bg=BG_DARK)
        self.container.pack(fill="both", expand=True)

        # ── Mostrar pantalla de inicio 
        self.show_intro_screen()

 
    # UTILIDADES DE UI


    def clear_container(self):
        """Elimina todos los widgets del contenedor."""
        for w in self.container.winfo_children():
            w.destroy()

    def make_label(self, parent, text, fg=WHITE, font=FONT_MONO,
                   bg=BG_DARK, **kwargs):
        """Crea un Label con el estilo del proyecto."""
        return tk.Label(parent, text=text, fg=fg, font=font,
                        bg=bg, **kwargs)

    def make_button(self, parent, text, command, fg=WHITE,
                    bg=RED_DARK, active_bg=RED, width=18):
        """Crea un Button con el estilo del proyecto."""
        btn = tk.Button(
            parent, text=text, command=command,
            fg=fg, bg=bg, activeforeground=fg,
            activebackground=active_bg,
            font=FONT_BTN, relief="flat",
            bd=0, cursor="hand2", width=width,
            highlightbackground=RED, highlightthickness=1,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=active_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def make_panel(self, parent, bg=BG_PANEL, bd=1, **kwargs):
        """Crea un Frame con apariencia de panel."""
        frame = tk.Frame(parent, bg=bg, bd=bd,
                         relief="flat",
                         highlightbackground=BORDER,
                         highlightthickness=1,
                         **kwargs)
        return frame

   
    # PANTALLA 1: INTRO
   

    def show_intro_screen(self):
        """Pantalla de inicio con animación de título."""
        self.clear_container()

        frame = tk.Frame(self.container, bg=BG_DARK)
        frame.pack(fill="both", expand=True)

        # Título animado
        self.title_var = tk.StringVar(value="")
        title_lbl = tk.Label(
            frame, textvariable=self.title_var,
            fg=RED, font=("Courier New", 48, "bold"),
            bg=BG_DARK
        )
        title_lbl.pack(pady=(80, 10))

        sub_lbl = self.make_label(
            frame, "MORSE TRANSLATOR · UPSIDE DOWN EDITION",
            fg=ORANGE, font=FONT_SUB
        )
        sub_lbl.pack(pady=(0, 8))

        # Línea decorativa
        tk.Frame(frame, bg=RED, height=1, width=500).pack(pady=8)

        # Mensajes de estado animados
        self.intro_msg_var = tk.StringVar(value="")
        msg_lbl = tk.Label(
            frame, textvariable=self.intro_msg_var,
            fg=AMBER, font=FONT_MONO, bg=BG_DARK
        )
        msg_lbl.pack(pady=20)

        # Créditos
        cred = self.make_label(
            frame,
            "CE-1104 Fundamentos de Sistemas Computacionales\n"
            "Instituto Tecnológico de Costa Rica  |  I Sem. 2026",
            fg=DIM, font=FONT_SMALL
        )
        cred.pack(pady=(30, 0))

        # Botón de continuar (aparece después de la animación)
        self.start_btn = self.make_button(
            frame, "[ ENTER THE UPSIDE DOWN ]",
            command=self.show_config_screen,
            bg=RED_DARK, active_bg=RED, width=30
        )

        # Iniciar animación de escritura del título
        self._animate_title("STRANGERTEC", title_lbl, callback=self._show_intro_messages)

    def _animate_title(self, text, widget, index=0, callback=None):
        """Escribe el título letra a letra."""
        if index <= len(text):
            self.title_var.set(text[:index])
            delay = 80 if index < len(text) else 300
            self.root.after(delay, self._animate_title,
                            text, widget, index + 1, callback)
        elif callback:
            callback()

    def _show_intro_messages(self):
        """Muestra mensajes secuenciales de inicio."""
        msgs = [
            "INITIALIZING UPSIDE DOWN CHANNEL...",
            "DETECTING HAWKINS LABORATORY...",
            "MORSE PROTOCOL ENGAGED...",
            "COMMUNICATION ESTABLISHED.",
        ]
        self._play_intro_msgs(msgs, 0)

    def _play_intro_msgs(self, msgs, idx):
        if idx < len(msgs):
            self.intro_msg_var.set(msgs[idx])
            self.root.after(900, self._play_intro_msgs, msgs, idx + 1)
        else:
            self.intro_msg_var.set("")
            self.start_btn.pack(pady=40)

    # PANTALLA 2: CONFIGURACIÓN


    def show_config_screen(self):
        """
        Pantalla de configuración:
        - Puerto serial
        - Velocidad (Unidad A=200ms / B=300ms)
        - Modo de transmisión (Simple / Escucha)
        - Lista de frases (editable)
        """
        self.clear_container()

        # Título
        top = tk.Frame(self.container, bg=BG_DARK)
        top.pack(fill="x", padx=20, pady=(15, 5))

        self.make_label(top, "⚙  CONFIGURACIÓN DEL SISTEMA",
                        fg=RED, font=FONT_SUB).pack(side="left")
        tk.Frame(top, bg=RED, height=1).pack(fill="x", pady=(5,0))

        # Contenido en dos columnas 
        content = tk.Frame(self.container, bg=BG_DARK)
        content.pack(fill="both", expand=True, padx=20, pady=5)

        left  = tk.Frame(content, bg=BG_DARK)
        right = tk.Frame(content, bg=BG_DARK)
        left.pack(side="left", fill="both", expand=True, padx=(0,10))
        right.pack(side="left", fill="both", expand=True)

        # COLUMNA IZQUIERDA

        # Panel: Conexión Serial
        p_serial = self.make_panel(left)
        p_serial.pack(fill="x", pady=(0,10))
        self.make_label(p_serial, "CONEXIÓN SERIAL", fg=ORANGE,
                        font=FONT_SMALL, bg=BG_PANEL).pack(anchor="w", padx=8, pady=(6,2))

        row_port = tk.Frame(p_serial, bg=BG_PANEL)
        row_port.pack(fill="x", padx=8, pady=4)
        self.make_label(row_port, "Puerto:", fg=WHITE,
                        font=FONT_SMALL, bg=BG_PANEL).pack(side="left")

        # Menú desplegable de puertos
        self.port_menu_var = tk.StringVar(value="Seleccionar...")
        ports = self._get_serial_ports()
        port_menu = tk.OptionMenu(row_port, self.port_menu_var, *ports if ports else ["(ninguno)"])
        port_menu.config(bg=BG_INPUT, fg=AMBER, font=FONT_SMALL,
                         activebackground=BG_PANEL, activeforeground=AMBER,
                         highlightthickness=0, bd=0)
        port_menu["menu"].config(bg=BG_INPUT, fg=AMBER, font=FONT_SMALL)
        port_menu.pack(side="left", padx=6)

        refresh_btn = self.make_button(row_port, "↺ Actualizar",
                                       command=self._refresh_ports, width=12)
        refresh_btn.pack(side="left", padx=4)

        connect_btn = self.make_button(row_port, "Conectar",
                                       command=self._connect_serial, width=10)
        connect_btn.pack(side="left", padx=4)

        self.conn_status_var = tk.StringVar(value="● Sin conexión")
        self.make_label(p_serial, textvariable=self.conn_status_var,
                        fg=DIM, font=FONT_SMALL, bg=BG_PANEL).pack(anchor="w", padx=8, pady=(0,6))

        # Panel: Velocidad
        p_speed = self.make_panel(left)
        p_speed.pack(fill="x", pady=(0,10))
        self.make_label(p_speed, "VELOCIDAD MORSE", fg=ORANGE,
                        font=FONT_SMALL, bg=BG_PANEL).pack(anchor="w", padx=8, pady=(6,4))

        row_speed = tk.Frame(p_speed, bg=BG_PANEL)
        row_speed.pack(fill="x", padx=8, pady=(0,8))

        for label, value in [("Unidad A  (200ms)", 200),
                              ("Unidad B  (300ms)", 300)]:
            rb = tk.Radiobutton(
                row_speed, text=label, variable=self.unit_ms,
                value=value, fg=WHITE, bg=BG_PANEL,
                selectcolor=RED_DARK, activebackground=BG_PANEL,
                activeforeground=WHITE, font=FONT_SMALL
            )
            rb.pack(anchor="w", pady=2)

        # Panel: Modo de transmisión
        p_mode = self.make_panel(left)
        p_mode.pack(fill="x", pady=(0,10))
        self.make_label(p_mode, "MODO DE TRANSMISIÓN", fg=ORANGE,
                        font=FONT_SMALL, bg=BG_PANEL).pack(anchor="w", padx=8, pady=(6,4))

        row_mode = tk.Frame(p_mode, bg=BG_PANEL)
        row_mode.pack(fill="x", padx=8, pady=(0,8))

        for label, value in [("Transmisión Simple  (LEDs)", "SIMPLE"),
                              ("Escucha y Transmisión  (Buzzer)", "LISTEN")]:
            rb = tk.Radiobutton(
                row_mode, text=label, variable=self.trans_mode,
                value=value, fg=WHITE, bg=BG_PANEL,
                selectcolor=RED_DARK, activebackground=BG_PANEL,
                activeforeground=WHITE, font=FONT_SMALL
            )
            rb.pack(anchor="w", pady=2)

        # COLUMNA DERECHA: Lista de frases 
        p_phrases = self.make_panel(right)
        p_phrases.pack(fill="both", expand=True)

        self.make_label(p_phrases, "LISTA DE FRASES  (máx. 16 chars)",
                        fg=ORANGE, font=FONT_SMALL,
                        bg=BG_PANEL).pack(anchor="w", padx=8, pady=(6,4))

        # Listbox de frases
        list_frame = tk.Frame(p_phrases, bg=BG_PANEL)
        list_frame.pack(fill="both", expand=True, padx=8)

        scrollbar = tk.Scrollbar(list_frame, bg=BG_PANEL, troughcolor=BG_DARK)
        scrollbar.pack(side="right", fill="y")

        self.phrase_listbox = tk.Listbox(
            list_frame, bg=BG_INPUT, fg=AMBER,
            font=FONT_MONO, selectbackground=RED_DARK,
            selectforeground=WHITE, bd=0, highlightthickness=0,
            yscrollcommand=scrollbar.set, height=10
        )
        self.phrase_listbox.pack(fill="both", expand=True)
        scrollbar.config(command=self.phrase_listbox.yview)

        # Poblar listbox
        for ph in self.phrases:
            self.phrase_listbox.insert(tk.END, ph)

        # Controles de la lista
        row_phrase_ctrl = tk.Frame(p_phrases, bg=BG_PANEL)
        row_phrase_ctrl.pack(fill="x", padx=8, pady=6)

        self.new_phrase_entry = tk.Entry(
            row_phrase_ctrl, bg=BG_INPUT, fg=AMBER,
            font=FONT_MONO, insertbackground=AMBER,
            width=18, bd=0, highlightthickness=1,
            highlightcolor=RED, highlightbackground=BORDER
        )
        self.new_phrase_entry.pack(side="left", padx=(0,6))
        self.new_phrase_entry.bind("<Return>", lambda e: self._add_phrase())

        add_btn = self.make_button(row_phrase_ctrl, "+ Agregar",
                                   command=self._add_phrase, width=10)
        add_btn.pack(side="left", padx=2)

        del_btn = self.make_button(row_phrase_ctrl, "- Borrar",
                                   command=self._delete_phrase, width=8,
                                   bg="#2a0008")
        del_btn.pack(side="left", padx=2)

        # Botón iniciar juego 
        bottom = tk.Frame(self.container, bg=BG_DARK)
        bottom.pack(fill="x", padx=20, pady=12)

        self.make_button(
            bottom, "◀ VOLVER",
            command=self.show_intro_screen, width=12
        ).pack(side="left")

        self.make_button(
            bottom, "▶ INICIAR JUEGO",
            command=self._start_game,
            bg=RED_DARK, active_bg=RED, width=20
        ).pack(side="right")

    def _get_serial_ports(self):
        """Retorna lista de puertos seriales disponibles."""
        ports = serial.tools.list_ports.comports()
        return [p.device for p in ports]

    def _refresh_ports(self):
        """Actualiza el menú de puertos seriales."""
        ports = self._get_serial_ports()
        menu = self.port_menu_var
        # Reconstruir menú 
        self.show_config_screen()

    def _connect_serial(self):
        """Intenta conectar al puerto seleccionado."""
        port = self.port_menu_var.get()
        if port in ("Seleccionar...", "(ninguno)"):
            messagebox.showwarning("Puerto", "Selecciona un puerto serial.")
            return
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
            self.serial_conn = serial.Serial(port, 115200, timeout=0.1)
            self.conn_status_var.set(f"● Conectado: {port}")
            # Cambiar color del indicador a verde usando after
            for w in self.container.winfo_children():
                pass  # El label se actualiza por StringVar
        except Exception as e:
            messagebox.showerror("Error de conexión", str(e))
            self.conn_status_var.set("● Error de conexión")

    def _add_phrase(self):
        """Agrega una frase nueva a la lista."""
        text = self.new_phrase_entry.get().strip().upper()
        if not text:
            return
        if len(text) > 16:
            messagebox.showwarning("Frase muy larga",
                                   "Máximo 16 caracteres.")
            return
        if len(self.phrases) >= 10:
            messagebox.showwarning("Lista llena",
                                   "Máximo 10 frases.")
            return
        self.phrases.append(text)
        self.phrase_listbox.insert(tk.END, text)
        self.new_phrase_entry.delete(0, tk.END)

    def _delete_phrase(self):
        """Elimina la frase seleccionada de la lista."""
        sel = self.phrase_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.phrase_listbox.delete(idx)
        self.phrases.pop(idx)

    def _start_game(self):
        """Valida configuración e inicia el juego."""
        if not self.phrases:
            messagebox.showwarning("Sin frases",
                                   "Agrega al menos una frase.")
            return

        # Resetear puntajes para nueva partida
        self.scores    = [0, 0]
        self.round_num = 1

        # Enviar configuración al Pico (si está conectado)
        self._pico_send("SET_UNIT", str(self.unit_ms.get()))
        self._pico_send("SET_TRANS_MODE", self.trans_mode.get())

        self.show_game_screen()

    # 
    # PANTALLA 3: JUEGO
  

    def show_game_screen(self):
        """
        Pantalla principal de juego. Muestra:
        - Frase objetivo y turno actual
        - Panel de abecedario (pared de Joyce)
        - Morse en tiempo real
        - Puntajes durante la partida
        """
        self.clear_container()
        self.game_active = True

        # Elegir frase aleatoria
        self.current_phrase = random.choice(self.phrases)
        self.player_input   = ""
        self.morse_buffer   = ""
        self.current_player = 1  # Empieza jugador A

        # ── HEADER ───────────────────────────────────────────
        header = tk.Frame(self.container, bg=BG_DARK)
        header.pack(fill="x", padx=15, pady=(10, 5))

        self.make_label(
            header, "StrangerTEC  ·  MORSE TRANSLATOR",
            fg=RED, font=("Courier New", 16, "bold")
        ).pack(side="left")

        self.round_var = tk.StringVar(value=f"RONDA {self.round_num}")
        self.make_label(header, textvariable=self.round_var,
                        fg=AMBER, font=FONT_SUB).pack(side="right")

        tk.Frame(self.container, bg=RED, height=1).pack(fill="x", padx=15)

        #  CUERPO 
        body = tk.Frame(self.container, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=15, pady=5)

        left_col  = tk.Frame(body, bg=BG_DARK)
        right_col = tk.Frame(body, bg=BG_DARK)
        left_col.pack(side="left", fill="both", expand=True, padx=(0,8))
        right_col.pack(side="left", fill="y", padx=(0,0))

        # ── Panel: Turno y Frase ──────────────────────────────
        p_phrase = self.make_panel(left_col)
        p_phrase.pack(fill="x", pady=(0,8))

        self.turn_var = tk.StringVar(value="TURNO: JUGADOR A")
        self.make_label(p_phrase, textvariable=self.turn_var,
                        fg=ORANGE, font=FONT_SUB,
                        bg=BG_PANEL).pack(anchor="w", padx=10, pady=(8,4))

        self.make_label(p_phrase, "FRASE OBJETIVO:",
                        fg=DIM, font=FONT_SMALL,
                        bg=BG_PANEL).pack(anchor="w", padx=10)

        # Mostrar la frase con indicador letra a letra
        self.phrase_frame = tk.Frame(p_phrase, bg=BG_PANEL)
        self.phrase_frame.pack(fill="x", padx=10, pady=6)
        self._build_phrase_display(self.current_phrase)

        #Panel: Abecedario 
        p_alpha = self.make_panel(left_col)
        p_alpha.pack(fill="x", pady=(0,8))

        self.make_label(p_alpha, "PARED DE JOYCE  — ALFABETO",
                        fg=ORANGE, font=FONT_SMALL,
                        bg=BG_PANEL).pack(anchor="w", padx=10, pady=(8,4))

        self.bulb_labels = {}
        self._build_alphabet_wall(p_alpha)

        # Panel: Morse en tiempo real 
        p_morse = self.make_panel(left_col)
        p_morse.pack(fill="x", pady=(0,8))

        self.make_label(p_morse, "SEÑAL MORSE — ENTRADA EN TIEMPO REAL",
                        fg=ORANGE, font=FONT_SMALL,
                        bg=BG_PANEL).pack(anchor="w", padx=10, pady=(8,4))

        morse_row = tk.Frame(p_morse, bg=BG_PANEL)
        morse_row.pack(fill="x", padx=10, pady=(0,8))

        self.morse_sym_var = tk.StringVar(value="_")
        self.make_label(morse_row, "SÍM:", fg=DIM,
                        font=FONT_SMALL, bg=BG_PANEL).pack(side="left")
        self.make_label(morse_row, textvariable=self.morse_sym_var,
                        fg=AMBER, font=FONT_MORSE,
                        bg=BG_PANEL).pack(side="left", padx=10)

        self.decoded_var = tk.StringVar(value="")
        self.make_label(morse_row, "DECODIFICADO:",
                        fg=DIM, font=FONT_SMALL,
                        bg=BG_PANEL).pack(side="left", padx=(20,4))
        self.make_label(morse_row, textvariable=self.decoded_var,
                        fg=RED, font=FONT_LETTER,
                        bg=BG_PANEL).pack(side="left")

        #Panel: Puntajes en tiempo real 
        p_score = self.make_panel(right_col, bg=BG_PANEL)
        p_score.pack(fill="x", pady=(0,8))

        self.make_label(p_score, "PUNTAJES",
                        fg=ORANGE, font=FONT_SMALL,
                        bg=BG_PANEL).pack(padx=10, pady=(8,4))

        for i, name in enumerate(["Jugador A", "Jugador B"]):
            row = tk.Frame(p_score, bg=BG_PANEL)
            row.pack(fill="x", padx=10, pady=2)
            self.make_label(row, name, fg=WHITE,
                            font=FONT_SMALL, bg=BG_PANEL).pack(side="left")
            var = tk.StringVar(value="0")
            setattr(self, f"score_var_{i+1}", var)
            self.make_label(row, textvariable=var, fg=AMBER,
                            font=("Courier New",16,"bold"),
                            bg=BG_PANEL).pack(side="right")

        # Actualizar displays de puntaje
        self.score_var_1.set(str(self.scores[0]))
        self.score_var_2.set(str(self.scores[1]))

        # Panel: Estado del sistema 
        p_status = self.make_panel(right_col)
        p_status.pack(fill="x", pady=(0,8))

        self.make_label(p_status, "ESTADO",
                        fg=ORANGE, font=FONT_SMALL,
                        bg=BG_PANEL).pack(padx=10, pady=(8,4))

        self.status_var = tk.StringVar(value="Esperando...")
        self.make_label(p_status, textvariable=self.status_var,
                        fg=GREEN_OK, font=FONT_SMALL,
                        bg=BG_PANEL, wraplength=180,
                        justify="left").pack(padx=10, pady=(0,8))

        # Botones de control 
        p_ctrl = self.make_panel(right_col)
        p_ctrl.pack(fill="x", pady=(0,8))

        self.make_label(p_ctrl, "CONTROL",
                        fg=ORANGE, font=FONT_SMALL,
                        bg=BG_PANEL).pack(padx=10, pady=(8,4))

        self.show_btn = self.make_button(
            p_ctrl, "▶ MOSTRAR FRASE",
            command=self._show_phrase_to_player,
            width=16
        )
        self.show_btn.pack(padx=10, pady=3)

        self.input_btn = self.make_button(
            p_ctrl, "⏺ INICIAR INPUT",
            command=self._start_player_input,
            width=16
        )
        self.input_btn.pack(padx=10, pady=3)

        self.skip_btn = self.make_button(
            p_ctrl, "⏭ SALTAR TURNO",
            command=self._skip_turn,
            bg="#1a0005", width=16
        )
        self.skip_btn.pack(padx=10, pady=(3,8))

        #  Log de actividad 
        p_log = self.make_panel(right_col)
        p_log.pack(fill="both", expand=True)

        self.make_label(p_log, "LOG",
                        fg=ORANGE, font=FONT_SMALL,
                        bg=BG_PANEL).pack(padx=10, pady=(8,4))

        self.log_text = tk.Text(
            p_log, bg=BG_INPUT, fg=DIM, font=FONT_SMALL,
            height=8, width=22, bd=0, state="disabled",
            wrap="word", insertbackground=AMBER
        )
        self.log_text.pack(padx=8, pady=(0,8))

        # ── Iniciar hilo de lectura serial ────────────────────
        self._start_serial_reader()

        # ── Inicio automático del primer turno ────────────────
        self.root.after(500, self._show_phrase_to_player)

    def _build_phrase_display(self, phrase):
        """Construye los labels de la frase objetivo."""
        for w in self.phrase_frame.winfo_children():
            w.destroy()
        self.phrase_char_labels = []
        for i, ch in enumerate(phrase):
            lbl = tk.Label(
                self.phrase_frame,
                text=ch if ch != " " else "·",
                fg=DIM, font=("Courier New", 20, "bold"),
                bg=BG_PANEL, width=2
            )
            lbl.grid(row=0, column=i, padx=2)
            self.phrase_char_labels.append(lbl)

    def _build_alphabet_wall(self, parent):
        """
        Construye el panel del abecedario en 3 filas,
        según el layout del enunciado (Figura 4).
        """
        wall_frame = tk.Frame(parent, bg=BG_PANEL)
        wall_frame.pack(padx=10, pady=(0,8))

        all_rows = [FILA1, FILA2, FILA3]

        for row_idx, row in enumerate(all_rows):
            row_frame = tk.Frame(wall_frame, bg=BG_PANEL)
            row_frame.pack(pady=2)

            for ch in row:
                lbl = tk.Label(
                    row_frame, text=ch,
                    fg=DIM,
                    font=("Courier New", 13, "bold"),
                    bg=BG_PANEL, width=3, height=1,
                    relief="flat", bd=0,
                    highlightbackground=BG_PANEL,
                    highlightthickness=1
                )
                lbl.pack(side="left", padx=1, pady=1)
                self.bulb_labels[ch] = lbl

    def _light_letter(self, letter, duration_ms=600):
        """
        Enciende el LED visual de una letra en el panel
        y lo apaga después de duration_ms milisegundos.
        """
        letter = letter.upper()
        lbl = self.bulb_labels.get(letter)
        if not lbl:
            return

        # Encender
        lbl.config(
            fg=WHITE,
            bg=RED,
            highlightbackground=ORANGE
        )

        # Apagar después del tiempo indicado
        def turn_off():
            if lbl.winfo_exists():
                lbl.config(fg=DIM, bg=BG_PANEL,
                           highlightbackground=BG_PANEL)

        self.root.after(duration_ms, turn_off)

    def _show_phrase_to_player(self):
        """
        Envía el comando al Pico para mostrar la frase,
        y también la muestra en la interfaz visual resaltando
        cada letra del abecedario.
        """
        self.show_btn.config(state="disabled")
        self.status_var.set("Mostrando frase en maqueta...")
        self.add_log(f"Frase: {self.current_phrase}")

        # Enviar al Pico
        self._pico_send("SHOW_PHRASE", self.current_phrase)

        # Simulación visual en la PC: encender letras en secuencia
        unit  = self.unit_ms.get()
        delay = 0
        for ch in self.current_phrase:
            if ch == " ":
                delay += unit * 7
                continue
            self.root.after(
                delay,
                lambda c=ch: self._light_letter(c, unit * 3)
            )
            delay += unit * 3 + unit * 3  # ON + pausa entre chars

        # Habilitar botón de input cuando termine
        self.root.after(
            delay + 500,
            lambda: [
                self.status_var.set("Frase mostrada. Listo para input."),
                self.input_btn.config(state="normal"),
            ]
        )

    def _start_player_input(self):
        """
        Envía comando al Pico para que el jugador empiece
        a ingresar la frase en Morse.
        """
        self.input_btn.config(state="disabled")
        self.skip_btn.config(state="normal")
        player_letter = "A" if self.current_player == 1 else "B"
        self.turn_var.set(f"TURNO: JUGADOR {player_letter} — INGRESANDO")
        self.status_var.set(f"Jugador {player_letter} ingresando Morse...")
        self.player_input  = ""
        self.morse_buffer  = ""
        self.morse_sym_var.set("_")
        self.decoded_var.set("")

        self._pico_send("START_INPUT", player_letter)
        self.add_log(f"Input iniciado — Jugador {player_letter}")

    def _skip_turn(self):
        """Salta el turno del jugador actual."""
        self._pico_send("SKIP", "")
        self.add_log("Turno saltado")
        self.status_var.set("Turno saltado.")
        self.skip_btn.config(state="disabled")

    def _process_input_result(self, result_text):
        """
        Recibe el texto decodificado por el jugador,
        calcula el puntaje y gestiona el cambio de turno.
        """
        player_idx = self.current_player - 1
        phrase     = self.current_phrase

        # Calcular puntaje 
        precision  = self._calculate_precision(phrase, result_text)
        time_bonus = self._calculate_speed_bonus()
        points     = int(precision * 100) + time_bonus

        self.scores[player_idx] += points

        # Actualizar display de puntaje
        self.score_var_1.set(str(self.scores[0]))
        self.score_var_2.set(str(self.scores[1]))

        # Resaltar letras correctas/incorrectas en la frase
        self._compare_phrase_display(phrase, result_text)

        self.add_log(
            f"J{'AB'[player_idx]}: '{result_text}' → {points}pts"
            f" ({int(precision*100)}%)"
        )

        # Enviar retroalimentación a la maqueta
        if precision >= 0.8:
            self._pico_send("SHOW_RESULT", "WIN")
        elif precision >= 0.4:
            self._pico_send("SHOW_RESULT", "TIE")
        else:
            self._pico_send("SHOW_RESULT", "LOSE")

        self.skip_btn.config(state="disabled")

        #  Cambio de turno 
        if self.current_player == 1:
            # Turno del Jugador B
            self.current_player = 2
            self.root.after(2000, self._next_turn)
        else:
            # Ambos jugadores completaron → mostrar resultados
            self.root.after(2000, self.show_result_screen)

    def _next_turn(self):
        """Prepara el turno del jugador B."""
        self.turn_var.set("TURNO: JUGADOR B")
        self.status_var.set("Preparando turno Jugador B...")
        self.player_input = ""
        self.morse_buffer = ""
        self.morse_sym_var.set("_")
        self.decoded_var.set("")
        self._build_phrase_display(self.current_phrase)

        # Limpiar resaltado del abecedario
        for lbl in self.bulb_labels.values():
            if lbl.winfo_exists():
                lbl.config(fg=DIM, bg=BG_PANEL)

        self.show_btn.config(state="normal")
        self.input_btn.config(state="disabled")
        self.root.after(500, self._show_phrase_to_player)

    def _compare_phrase_display(self, target, answer):
        """
        Colorea los labels de la frase según coincidencia:
        verde = correcto, rojo = incorrecto, gris = faltante.
        """
        target = target.upper()
        answer = answer.upper()
        for i, lbl in enumerate(self.phrase_char_labels):
            if not lbl.winfo_exists():
                continue
            if i < len(answer):
                if answer[i] == target[i]:
                    lbl.config(fg=GREEN_OK)
                else:
                    lbl.config(fg=RED)
            else:
                lbl.config(fg=DIM)

    def _calculate_precision(self, target, answer):
        """
        Calcula la precisión como fracción de caracteres correctos.
        Compara posición a posición.

        Returns: float entre 0.0 y 1.0
        """
        target = target.upper().replace(" ", "")
        answer = answer.upper().replace(" ", "")
        if not target:
            return 0.0
        matches = sum(
            1 for i in range(min(len(target), len(answer)))
            if target[i] == answer[i]
        )
        return matches / len(target)

    def _calculate_speed_bonus(self):
        """
        Bonus de velocidad (simplificado).
        En una implementación completa usaría el tiempo real.
        Returns: int entre 0 y 20
        """
        return 10  # Bonus fijo por ahora; extender con tiempo real


    # PANTALLA 4: RESULTADOS
  

    def show_result_screen(self):
        """
        Pantalla final de la ronda:
        - Puntaje de cada jugador
        - Ganador de la ronda
        - Opciones: nueva ronda o terminar
        """
        self.clear_container()
        self.game_active = False

        frame = tk.Frame(self.container, bg=BG_DARK)
        frame.pack(fill="both", expand=True, padx=30, pady=20)

        # Título
        self.make_label(
            frame, f"— RESULTADOS RONDA {self.round_num} —",
            fg=RED, font=("Courier New", 20, "bold")
        ).pack(pady=(0, 20))

        # Determinar ganador
        if self.scores[0] > self.scores[1]:
            winner = "JUGADOR A"
            winner_color = ORANGE
        elif self.scores[1] > self.scores[0]:
            winner = "JUGADOR B"
            winner_color = AMBER
        else:
            winner = "EMPATE"
            winner_color = WHITE

        # Panel de puntajes
        scores_panel = self.make_panel(frame)
        scores_panel.pack(fill="x", pady=(0, 20))

        row = tk.Frame(scores_panel, bg=BG_PANEL)
        row.pack(pady=20, padx=20)

        for i, (name, score) in enumerate(
            [("JUGADOR A", self.scores[0]),
             ("JUGADOR B", self.scores[1])]
        ):
            col = tk.Frame(row, bg=BG_PANEL, width=200)
            col.pack(side="left", padx=30)
            self.make_label(col, name, fg=ORANGE,
                            font=FONT_SUB, bg=BG_PANEL).pack()
            self.make_label(col, str(score), fg=AMBER,
                            font=FONT_SCORE, bg=BG_PANEL).pack()
            self.make_label(col, "puntos", fg=DIM,
                            font=FONT_SMALL, bg=BG_PANEL).pack()

        # Frase de la ronda
        self.make_label(
            frame, f"FRASE: {self.current_phrase}",
            fg=WHITE, font=FONT_SUB
        ).pack(pady=(0, 10))

        # Ganador
        self.make_label(
            frame, f"🏆  {winner}",
            fg=winner_color,
            font=("Courier New", 28, "bold")
        ).pack(pady=20)

        # Botones
        btn_row = tk.Frame(frame, bg=BG_DARK)
        btn_row.pack(pady=20)

        self.make_button(
            btn_row, "▶ NUEVA RONDA",
            command=self._new_round,
            bg=RED_DARK, active_bg=RED, width=16
        ).pack(side="left", padx=10)

        self.make_button(
            btn_row, "⚙ CONFIGURACIÓN",
            command=self.show_config_screen,
            width=16
        ).pack(side="left", padx=10)

        self.make_button(
            btn_row, "■ TERMINAR",
            command=self.show_intro_screen,
            bg="#1a0005", width=12
        ).pack(side="left", padx=10)

    def _new_round(self):
        """Inicia una nueva ronda manteniendo los puntajes."""
        self.round_num += 1
        self.show_game_screen()

 
    # COMUNICACIÓN SERIAL
    def _pico_send(self, cmd_type, data=""):
        """
        Envía un comando al Pico W por serial.
        Si no hay conexión, muestra en el log.
        """
        msg = f"{cmd_type}:{data}\n"
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(msg.encode("utf-8"))
            except Exception as e:
                self.add_log(f"[ERR serial] {e}")
        else:
            # Sin conexión: solo log (útil para desarrollo sin hardware)
            self.add_log(f"[SIM] → {cmd_type}:{data}")

    def _start_serial_reader(self):
        """Inicia el hilo de lectura serial en background."""
        self._stop_serial.clear()
        self._serial_thread = threading.Thread(
            target=self._serial_read_loop,
            daemon=True
        )
        self._serial_thread.start()

    def _serial_read_loop(self):
        """
        Loop que corre en un hilo separado.
        Lee mensajes del Pico y los encola para la UI.
        """
        buffer = ""
        while not self._stop_serial.is_set():
            if not (self.serial_conn and self.serial_conn.is_open):
                time.sleep(0.1)
                continue
            try:
                if self.serial_conn.in_waiting:
                    raw  = self.serial_conn.read(self.serial_conn.in_waiting)
                    text = raw.decode("utf-8", errors="ignore")
                    buffer += text

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            # Procesar en el hilo principal de Tkinter
                            self.root.after(0, self._handle_pico_message, line)

            except Exception:
                pass
            time.sleep(0.01)

    def _handle_pico_message(self, line):
        """
        Procesa un mensaje recibido del Pico W.
        Se ejecuta en el hilo principal de Tkinter.
        Formato esperado: TIPO:datos
        """
        if ":" not in line:
            return

        idx   = line.index(":")
        mtype = line[:idx]
        data  = line[idx+1:]

        if mtype == "SYMBOL":
            # Nuevo símbolo Morse (. o -)
            self.morse_buffer += data
            self.morse_sym_var.set(self.morse_buffer or "_")

        elif mtype == "LETTER":
            # Letra decodificada
            self.player_input += data
            self.decoded_var.set(self.player_input)
            self._light_letter(data, duration_ms=400)
            self.morse_buffer = ""
            self.morse_sym_var.set("_")

        elif mtype == "WORD_SPACE":
            self.player_input += " "
            self.decoded_var.set(self.player_input)
            self.morse_buffer = ""
            self.morse_sym_var.set("_")

        elif mtype == "INPUT_RESULT":
            # El Pico terminó de recibir el input del jugador
            self._process_input_result(data)

        elif mtype == "STATUS":
            self.status_var.set(data.replace("_", " "))

        elif mtype == "READY":
            self.add_log("Pico listo")

        elif mtype == "PONG":
            self.add_log("Pico: OK")


    # LOG DE ACTIVIDAD


    def add_log(self, message):
        """
        Agrega una línea al log de actividad.
        Funciona solo si el widget existe.
        """
        try:
            if not hasattr(self, "log_text") or not self.log_text.winfo_exists():
                return
            ts = time.strftime("%H:%M:%S")
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, f"[{ts}] {message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        except tk.TclError:
            pass


    # CIERRE DE LA APLICACIÓN

    def on_close(self):
        """Limpieza al cerrar la ventana."""
        self._stop_serial.set()
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self._pico_send("RESET")
                self.serial_conn.close()
            except:
                pass
        self.root.destroy()

# PUNTO DE ENTRADA

if __name__ == "__main__":
    root = tk.Tk()
    app  = StrangerTECApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
