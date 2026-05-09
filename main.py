# main.py  —  StrangerTEC Morse Translator
# Raspberry Pi Pico W  |  MicroPython
# CE-1104 Fundamentos de Sistemas Computacionales — TEC
# DESCRIPCIÓN GENERAL:
#   Este archivo es el punto de entrada del sistema embebido.
#   Coordina todos los módulos y gestiona el loop principal.
# FLUJO DEL JUEGO (Modo Local):
#   1. La PC envía una frase al Pico por serial USB
#   2. La Pico la muestra letra a letra con los LEDs
#      (Modo Simple) o con el buzzer (Modo Escucha)
#   3. El jugador ingresa la frase en Morse con el botón
#   4. La Pico evalúa y envía el resultado a la PC



from machine import Pin, PWM
import utime
import sys

#Importar módulos propios 
from shift_register import ShiftRegister
from morse_input    import MorseInput
from buzzer         import Buzzer
from led_panel      import LEDPanel
from serial_comm    import SerialComm

# INICIALIZACIÓN DE HARDWARE

# Registro de corrimiento: DATA=GP0, CLK=GP1, CLR=GP2
shift = ShiftRegister(data_pin=0, clk_pin=1, clr_pin=2)

# Panel de LEDs (usa el registro de corrimiento)
panel = LEDPanel(shift)

# Buzzer pasivo en GP15
buzzer = Buzzer(pin=15)

# Botón Morse en GP14, PULL_DOWN (HIGH cuando se presiona)
# Switch de modo en GP16, PULL_DOWN (HIGH = Versus)
morse_input = MorseInput(button_pin=14, unit_ms=200)

# Switch físico de modo
switch = Pin(16, Pin.IN, Pin.PULL_DOWN)

# Comunicación serial con la PC
serial = SerialComm()

# LED onboard del Pico (GP25) como indicador de vida
led_onboard = Pin(25, Pin.OUT)

# ESTADO GLOBAL DEL SISTEMA
state = {
    "mode":          "LOCAL",    # LOCAL o VERSUS
    "trans_mode":    "SIMPLE",   # SIMPLE o LISTEN
    "unit_ms":       200,        # Duración unidad: 200 o 300 ms
    "current_phrase": "",        # Frase enviada desde la PC
    "player_turn":   1,          # 1 = Jugador A,  2 = Jugador B
    "waiting_input": False,      # True cuando espera que el jugador ingrese Morse
    "game_active":   False,      # Hay partida en curso
}

# FUNCIONES DE PRESENTACIÓN DE FRASE

def show_phrase_leds(phrase, unit_ms):
    """
    Modo Transmisión Simple:
    Muestra cada letra de la frase encendiendo el LED
    correspondiente en el panel, letra por letra.
    Entre letras hay pausa de 3 unidades,
    entre palabras pausa de 7 unidades.
    """
    serial.send("STATUS", "SHOWING_PHRASE_LEDS")
    panel.clear()

    for ch in phrase:
        if ch == " ":
            # Pausa entre palabras = 7 unidades
            panel.clear()
            utime.sleep_ms(unit_ms * 7)
            continue

        # Encender el LED de esta letra/número
        panel.show_character(ch)
        # LED visible por 3 unidades (duración de una raya, referencia visual)
        utime.sleep_ms(unit_ms * 3)
        panel.clear()
        # Pausa entre caracteres = 3 unidades
        utime.sleep_ms(unit_ms * 3)

    panel.clear()
    serial.send("STATUS", "PHRASE_SHOWN")


def show_phrase_buzzer(phrase, unit_ms):
    """
    Modo Escucha y Transmisión:
    Reproduce la frase en código Morse usando el buzzer.
    Temporización estándar:
      punto  = 1 unidad ON
      raya   = 3 unidades ON
      entre símbolos de un carácter = 1 unidad OFF
      entre caracteres  = 3 unidades OFF
      entre palabras    = 7 unidades OFF
    También enciende el LED del carácter mientras suena.
    """
    from morse_input import MORSE_TABLE  # Tabla letra→morse

    serial.send("STATUS", "PLAYING_PHRASE_BUZZER")

    for ch in phrase:
        if ch == " ":
            # Silencio entre palabras
            buzzer.stop()
            panel.clear()
            utime.sleep_ms(unit_ms * 7)
            continue

        code = MORSE_TABLE.get(ch.upper(), None)
        if code is None:
            continue

        # Mostrar LED del carácter mientras se reproduce
        panel.show_character(ch)

        for i, sym in enumerate(code):
            if sym == ".":
                buzzer.tone(800)           # Tono agudo = punto
                utime.sleep_ms(unit_ms)    # Duración: 1 unidad
            elif sym == "-":
                buzzer.tone(600)           # Tono medio = raya
                utime.sleep_ms(unit_ms * 3)  # Duración: 3 unidades

            buzzer.stop()

            # Pausa entre símbolos del mismo carácter = 1 unidad
            if i < len(code) - 1:
                utime.sleep_ms(unit_ms)

        panel.clear()
        # Pausa entre caracteres = 3 unidades
        utime.sleep_ms(unit_ms * 3)

    buzzer.stop()
    panel.clear()
    serial.send("STATUS", "PHRASE_PLAYED")

#FUNCIÓN PARA RECIBIR INPUT MORSE DEL JUGADOR

def receive_morse_input(expected_phrase, unit_ms):
    """
    Espera que el jugador ingrese la frase en código Morse
    usando el botón. Cuando detecta fin de mensaje, retorna
    el texto decodificado.

    Usa el módulo MorseInput que gestiona tiempos de presión.
    """
    morse_input.reset()
    morse_input.unit_ms = unit_ms
    serial.send("STATUS", "WAITING_INPUT")

    decoded_chars = []   # Lista de caracteres decodificados
    current_morse = ""   # Símbolos acumulados del carácter actual

    # Parpadeo del onboard para indicar que espera input
    led_onboard.value(1)

    TIMEOUT_NO_ACTIVITY = unit_ms * 30  # 30 unidades sin actividad = fin
    last_activity = utime.ticks_ms()

    while True:
        now = utime.ticks_ms()

        #Verificar si llegó comando SKIP desde la PC 
        msg = serial.try_read()
        if msg and msg[0] == "SKIP":
            serial.send("STATUS", "INPUT_SKIPPED")
            break

        #Leer botón
        result = morse_input.update(now)

        if result == "DOT":
            current_morse += "."
            buzzer.beep_short(unit_ms)
            serial.send("SYMBOL", ".")
            serial.send("MORSE_BUF", current_morse)
            last_activity = now

        elif result == "DASH":
            current_morse += "-"
            buzzer.beep_long(unit_ms)
            serial.send("SYMBOL", "-")
            serial.send("MORSE_BUF", current_morse)
            last_activity = now

        elif result == "CHAR_END":
            # Pausa de letra detectada: decodificar símbolo acumulado
            if current_morse:
                letter = morse_input.decode(current_morse)
                decoded_chars.append(letter)
                current_morse = ""
                serial.send("LETTER", letter)
                panel.show_character(letter)   # Mostrar letra en LEDs
                utime.sleep_ms(unit_ms * 2)
                panel.clear()
                last_activity = now

        elif result == "WORD_END":
            # Pausa de palabra detectada
            if current_morse:
                letter = morse_input.decode(current_morse)
                decoded_chars.append(letter)
                current_morse = ""
                serial.send("LETTER", letter)

            decoded_chars.append(" ")
            serial.send("WORD_SPACE", " ")
            last_activity = now

        # Timeout: fin de mensaje
        elapsed_no_activity = utime.ticks_diff(now, last_activity)
        if elapsed_no_activity >= TIMEOUT_NO_ACTIVITY and decoded_chars:
            # Decodificar último carácter pendiente
            if current_morse:
                letter = morse_input.decode(current_morse)
                decoded_chars.append(letter)
                current_morse = ""
                serial.send("LETTER", letter)
            break

        utime.sleep_ms(5)

    led_onboard.value(0)
    result_text = "".join(decoded_chars).strip()
    return result_text

#
# LOOP PRINCIPAL
# 

def main():
    """
    Loop principal del sistema.
    Espera comandos de la PC por serial y ejecuta acciones.
    """
    panel.clear()
    buzzer.stop()

    # Animación de inicio
    panel.animate_startup()
    buzzer.play_startup()

    serial.send("BOOT", "STRANGERTEC_PICO_V1")
    serial.send("READY", "WAITING_COMMANDS")

    while True:
        #Leer el switch de modo
        if switch.value() == 1:
            state["mode"] = "VERSUS"
        else:
            state["mode"] = "LOCAL"

        #Leer comandos de la PC
        cmd = serial.try_read()

        if cmd is None:
            # Parpadeo suave del onboard = sistema vivo
            led_onboard.toggle()
            utime.sleep_ms(500)
            continue

        cmd_type, cmd_data = cmd

        #CMD: SET_UNIT — cambiar velocidad 
        if cmd_type == "SET_UNIT":
            
            try:
                state["unit_ms"] = int(cmd_data)
                serial.send("ACK", "UNIT_SET_" + cmd_data)
            except:
                serial.send("ERR", "INVALID_UNIT")

        #CMD: SET_MODE — cambiar modo de transmisión 
        elif cmd_type == "SET_TRANS_MODE":
            # SIMPLE o LISTEN
            state["trans_mode"] = cmd_data
            serial.send("ACK", "TRANS_MODE_" + cmd_data)

        #CMD: SHOW_PHRASE — mostrar frase al jugador
        elif cmd_type == "SHOW_PHRASE":
            state["current_phrase"] = cmd_data
            unit = state["unit_ms"]

            if state["trans_mode"] == "SIMPLE":
                show_phrase_leds(cmd_data, unit)
            else:
                show_phrase_buzzer(cmd_data, unit)

        # CMD: START_INPUT — jugador empieza a ingresar 
        elif cmd_type == "START_INPUT":
            phrase = state["current_phrase"]
            unit   = state["unit_ms"]
            player = cmd_data   # "A" o "B"

            serial.send("INPUT_START", player)
            result = receive_morse_input(phrase, unit)

            # Enviar resultado a la PC para evaluación
            serial.send("INPUT_RESULT", result)

        #CMD: SHOW_RESULT  mostrar resultado con LEDs 
        elif cmd_type == "SHOW_RESULT":
            # La PC manda "WIN" o "LOSE" o "TIE"
            if cmd_data == "WIN":
                panel.animate_win()
                buzzer.play_win()
            elif cmd_data == "LOSE":
                panel.animate_lose()
                buzzer.play_lose()
            else:
                panel.animate_blink(times=3)

        # CMD: RESET  reiniciar estado 
        elif cmd_type == "RESET":
            state["current_phrase"] = ""
            panel.clear()
            buzzer.stop()
            serial.send("ACK", "RESET_OK")

        # CMD: PING  verificar conexión 
        elif cmd_type == "PING":
            serial.send("PONG", "OK")

        utime.sleep_ms(10)



# PUNTO DE ENTRADA
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        panel.clear()
        buzzer.stop()
        led_onboard.value(0)
        print("LOG:Sistema detenido por usuario")
