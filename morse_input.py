# morse_input.py  —  StrangerTEC Morse Translator
# Módulo: Lectura del botón y decodificación Morse
# Raspberry Pi Pico W  |  MicroPython
# DESCRIPCIÓN:
#   Lee el botón pulsador y clasifica cada presión como
#   punto (.) o raya (-) según la duración.
# la temporización usa UNIDADES:
#     punto         = 1 unidad  (presión corta)
#     raya          = 3 unidades (presión larga)
#     pausa símbolo = 1 unidad  (entre . y - del mismo char)
#     pausa letra   = 3 unidades (entre caracteres)
#     pausa palabra = 7 unidades (entre palabras)
#   Unidad A = 200ms, Unidad B = 300ms (configurable)



from machine import Pin
import utime



# TABLA MORSE COMPLETA (letra/número → código)
# Convención del enunciado (igual al estándar internacional)
MORSE_TABLE = {
    # Letras
    ".-":    "A",  "-...": "B",  "-.-.": "C",  "-..":  "D",
    ".":     "E",  "..-.": "F",  "--.":  "G",  "....": "H",
    "..":    "I",  ".---": "J",  "-.-":  "K",  ".-..": "L",
    "--":    "M",  "-.":   "N",  "---":  "O",  ".--.": "P",
    "--.-":  "Q",  ".-.":  "R",  "...":  "S",  "-":    "T",
    "..-":   "U",  "...-": "V",  ".--":  "W",  "-..-": "X",
    "-.--":  "Y",  "--..": "Z",
    # Números
    ".----": "1",  "..---": "2", "...--": "3", "....-": "4",
    ".....": "5",  "-....": "6", "--...": "7", "---..": "8",
    "----.": "9",  "-----": "0",
    # Símbolos del enunciado
    ".-.-." : "+",   # Más
    "-....-": "-",   # Menos / Guión
}

# Tabla inversa: carácter → código Morse
CHAR_TO_MORSE = {v: k for k, v in MORSE_TABLE.items()}


class MorseInput:
    """
    Gestiona la lectura del botón y la decodificación Morse
    basada en temporización por unidades.
    """

    def __init__(self, button_pin=14, unit_ms=200):
        """
        Args:
            button_pin: número de pin GP del botón (PULL_DOWN)
            unit_ms:    duración de la unidad en ms (200 o 300)
        """
        # PULL_DOWN: HIGH cuando se presiona, LOW en reposo
        self.button = Pin(button_pin, Pin.IN, Pin.PULL_DOWN)

        self.unit_ms = unit_ms     # Duración de la unidad

        # Estado interno del botón
        self._pressed      = False  # ¿Está presionado ahora?
        self._press_start  = 0      # ticks_ms cuando empezó la presión
        self._release_time = 0      # ticks_ms cuando se soltó

        # Estado de la decodificación
        self._symbol_buf   = ""     # Puntos y rayas acumulados del carácter
        self._waiting_char = False  # Esperando pausa para decodificar

    def reset(self):
        """Limpia todos los buffers y estado interno."""
        self._pressed      = False
        self._press_start  = 0
        self._release_time = 0
        self._symbol_buf   = ""
        self._waiting_char = False

    def update(self, now_ms):
        """
        Debe llamarse en el loop principal con el tiempo actual.
        Analiza el estado del botón y retorna eventos:

        Returns:
            "DOT"      → se detectó un punto
            "DASH"     → se detectó una raya
            "CHAR_END" → pausa de letra (3 unidades sin presión)
            "WORD_END" → pausa de palabra (7 unidades sin presión)
            None       → sin evento nuevo
        """
        btn_state = self.button.value()  # 1=presionado, 0=suelto

        # Flanco de SUBIDA: botón recién presionado 
        if btn_state == 1 and not self._pressed:
            self._pressed     = True
            self._press_start = now_ms
            self._waiting_char = False
            return None

        # Flanco de BAJADA: botón recién soltado 
        if btn_state == 0 and self._pressed:
            self._pressed      = False
            self._release_time = now_ms
            self._waiting_char = True

            duration = utime.ticks_diff(now_ms, self._press_start)

            # Clasificar por duración vs umbral de 2 unidades
            # Punto: < 2 unidades, Raya: >= 2 unidades
            threshold = self.unit_ms * 2

            if duration < threshold:
                self._symbol_buf += "."
                return "DOT"
            else:
                self._symbol_buf += "-"
                return "DASH"

        #Verificar pausas cuando el botón está suelto
        if not self._pressed and self._waiting_char and self._release_time > 0:
            elapsed = utime.ticks_diff(now_ms, self._release_time)

            # Pausa de PALABRA: >= 7 unidades
            if elapsed >= self.unit_ms * 7:
                self._waiting_char = False
                self._release_time = 0
                return "WORD_END"

            # Pausa de CARÁCTER: >= 3 unidades
            if elapsed >= self.unit_ms * 3:
                self._waiting_char = False
                self._release_time = 0
                return "CHAR_END"

        return None

    
    def decode(self, morse_code):
        """
        Decodifica una secuencia de puntos y rayas a carácter.

        Args:
            morse_code: string de "." y "-", ej: ".-"

        Returns:
            El carácter decodificado, o "?" si no existe.
        """
        return MORSE_TABLE.get(morse_code, "?")


    def get_buffer(self):
        """Retorna el buffer de símbolos del carácter actual."""
        return self._symbol_buf

 
    def clear_buffer(self):
        """Limpia el buffer de símbolos del carácter actual."""
        self._symbol_buf = ""


    @property
    def is_pressed(self):
        """True si el botón está actualmente presionado."""
        return self._pressed
