# buzzer.py  —  StrangerTEC Morse Translator
# Módulo: Control del buzzer pasivo mediante PWM
# Raspberry Pi Pico W  |  MicroPython
# DESCRIPCIÓN:
#   El buzzer pasivo requiere una señal PWM para sonar.
#   Diferencia tonos para punto, raya, inicio y resultado.
#   Según el enunciado:
#   "Buzzer pasivo: Suena mediante PWM durante toda la
#   presión del botón. Retroalimentación auditiva que ayuda
#   a controlar la duración de la señal Morse."
# CONEXIÓN:
#   GP15 (PWM) → Terminal + del buzzer
#   GND        → Terminal - del buzzer


from machine import Pin, PWM
import utime


class Buzzer:
    """
    Controla el buzzer pasivo con señal PWM.
    Tonos diferenciados para cada tipo de señal Morse.
    """

    # Frecuencias usadas
    FREQ_DOT     = 880   # Hz — punto (agudo, corto)
    FREQ_DASH    = 660   # Hz — raya  (medio, largo)
    FREQ_STARTUP = 440   # Hz — melodía de inicio
    FREQ_WIN     = 1047  # Hz — Do alto, victoria
    FREQ_LOSE    = 220   # Hz — La grave, derrota
    DUTY         = 32768 # 50% de ciclo de trabajo (0-65535)

    def __init__(self, pin=15):
        """
        Args:
            pin: número de pin GP para el PWM del buzzer
        """
        self.pwm = PWM(Pin(pin))
        self.pwm.duty_u16(0)    #Silencio al iniciar
        self._active = False


    def tone(self, freq_hz):
        """
        Empieza a sonar a la frecuencia indicada de forma
        continua (no bloqueante). Detener con stop().

        Args:
            freq_hz: frecuencia en Hz
        """
        self.pwm.freq(freq_hz)
        self.pwm.duty_u16(self.DUTY)
        self._active = True

    def stop(self):
        """Detiene el buzzer (silencio)."""
        self.pwm.duty_u16(0)
        self._active = False

    def beep_short(self, unit_ms):
        """
        Suena la duración de UN PUNTO (1 unidad) y para.
        Usado para retroalimentación de punto.

        Args:
            unit_ms: duración de la unidad en ms
        """
        self.pwm.freq(self.FREQ_DOT)
        self.pwm.duty_u16(self.DUTY)
        utime.sleep_ms(unit_ms)      #Duración punto = 1 unidad
        self.pwm.duty_u16(0)
        self._active = False

    def beep_long(self, unit_ms):
        """
        Suena la duración de UNA RAYA (3 unidades) y para.
        Usado para retroalimentación de raya.

        Args:
            unit_ms: duración de la unidad en ms
        """
        self.pwm.freq(self.FREQ_DASH)
        self.pwm.duty_u16(self.DUTY)
        utime.sleep_ms(unit_ms * 3)  #Duración raya = 3 unidades
        self.pwm.duty_u16(0)
        self._active = False

    def beep_button_hold(self):
        """
        Activa el buzzer mientras el botón está presionado.
        Llamar continuamente en el loop; detener con stop()
        cuando el botón se suelte.
        Solo activa si no está ya sonando.
        """
        if not self._active:
            self.pwm.freq(self.FREQ_DOT)
            self.pwm.duty_u16(self.DUTY)
            self._active = True

    def play_startup(self):
        """
        Melodía corta de inicio inspirada en Stranger Things.
        Notas sencillas: Re-Mi-Sol descendente.
        """
        melody = [
            (294, 150),   # D4
            (330, 150),   # E4
            (392, 200),   # G4
            (330, 150),   # E4
            (294, 300),   # D4
            (0,   100),   # silencio
            (262, 150),   # C4
            (294, 400),   # D4
        ]
        for freq, dur in melody:
            if freq == 0:
                self.pwm.duty_u16(0)
            else:
                self.pwm.freq(freq)
                self.pwm.duty_u16(self.DUTY)
            utime.sleep_ms(dur)

        self.pwm.duty_u16(0)
        self._active = False

    def play_win(self):
        """Melodía corta de victoria."""
        for freq, dur in [(784,100),(880,100),(1047,300)]:
            self.pwm.freq(freq)
            self.pwm.duty_u16(self.DUTY)
            utime.sleep_ms(dur)
            self.pwm.duty_u16(0)
            utime.sleep_ms(40)
        self._active = False

    def play_lose(self):
        """Melodía corta de derrota."""
        for freq, dur in [(440,200),(330,200),(220,400)]:
            self.pwm.freq(freq)
            self.pwm.duty_u16(self.DUTY)
            utime.sleep_ms(dur)
            self.pwm.duty_u16(0)
            utime.sleep_ms(40)
        self._active = False

    def deinit(self):
        """Libera el recurso PWM. Llamar al terminar."""
        self.stop()
        self.pwm.deinit()
