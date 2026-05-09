# =============================================================
# shift_register.py  —  StrangerTEC Morse Translator
# Módulo: Control del registro de corrimiento 74HC164
# Raspberry Pi Pico W  |  MicroPython
#
# DESCRIPCIÓN:
#   Maneja la comunicación bit a bit con los dos 74HC164
#   encadenados (cascada) para controlar 16 LEDs con solo
#   3 pines del Pico W: DATA, CLK y CLR.
#
# CONEXIONES (según Figura 6 del enunciado):
#   GP0 → Pin A y B del 74HC164 #1 (DATA)
#   GP1 → Pin CLK de ambos 74HC164 (en cadena)
#   GP2 → Pin CLR de ambos 74HC164 (activo en LOW = reset)
#
#   Cascada: Q7 del 74HC164 #1 → Pin A y B del 74HC164 #2
#
# PROTOCOLO 74HC164:
#   - En cada pulso de CLK, el bit en DATA se desplaza
#     hacia Q0, y los demás avanzan una posición.
#   - CLR en LOW limpia todo el registro inmediatamente.
#   - Se envían 16 bits: primero el bit 15 (LED16), último
#     el bit 0 (LED1), porque el registro desplaza hacia
#     arriba.
# =============================================================

from machine import Pin
import utime


class ShiftRegister:
    """
    Controla dos 74HC164 en cascada para manejar 16 LEDs.
    """

    def __init__(self, data_pin=0, clk_pin=1, clr_pin=2):
        """
        Inicializa los tres pines de control.

        Args:
            data_pin: GP del Pico conectado a A y B del 74HC164 #1
            clk_pin:  GP del Pico conectado a CLK de ambos chips
            clr_pin:  GP del Pico conectado a CLR de ambos chips
        """
        self.data = Pin(data_pin, Pin.OUT)
        self.clk  = Pin(clk_pin,  Pin.OUT)
        self.clr  = Pin(clr_pin,  Pin.OUT)

        # Estado inicial: CLR en HIGH (no resetear), todo apagado
        self.clr.value(1)
        self.clk.value(0)
        self.data.value(0)

        self._current = 0  # Valor de 16 bits actualmente en los registros
        self.write(0)      # Asegurar que arranque apagado

    # ----------------------------------------------------------
    def write(self, value_16bit):
        """
        Envía 16 bits a los registros de corrimiento.
        El bit 15 se envía primero (MSB first).
        Cada pulso de CLK desplaza un bit al registro.

        Args:
            value_16bit: entero de 0 a 65535 (0x0000 a 0xFFFF)
        """
        value_16bit = value_16bit & 0xFFFF  # Asegurar 16 bits

        for i in range(15, -1, -1):         # Del bit 15 al bit 0
            bit = (value_16bit >> i) & 0x01  # Extraer un bit
            self.data.value(bit)             # Poner en DATA
            self.clk.value(1)               # Flanco de subida
            utime.sleep_us(2)               # Mínimo setup time 74HC164
            self.clk.value(0)               # Flanco de bajada
            utime.sleep_us(2)

        self._current = value_16bit

    # ----------------------------------------------------------
    def clear(self):
        """
        Apaga todos los LEDs activando CLR (LOW) brevemente.
        Más rápido que escribir 16 ceros.
        """
        self.clr.value(0)     # CLR activo en LOW
        utime.sleep_us(5)
        self.clr.value(1)     # Volver a HIGH para operación normal
        self._current = 0

    # ----------------------------------------------------------
    def set_bit(self, index, value):
        """
        Enciende o apaga un LED individual sin tocar los demás.

        Args:
            index: posición del LED (0=LED1 ... 15=LED16)
            value: 1 para encender, 0 para apagar
        """
        if not 0 <= index <= 15:
            return
        if value:
            new_val = self._current | (1 << index)
        else:
            new_val = self._current & ~(1 << index)
        self.write(new_val)

    # ----------------------------------------------------------
    @property
    def current_value(self):
        """Retorna el patrón de 16 bits actualmente encendido."""
        return self._current
