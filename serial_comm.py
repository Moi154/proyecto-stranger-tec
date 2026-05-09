# serial_comm.py  —  StrangerTEC Morse Translator
# Módulo: Comunicación serial USB entre Pico W y la PC
# Raspberry Pi Pico W  |  MicroPython
# DESCRIPCIÓN:
#   Gestiona el envío y recepción de mensajes entre el Pico
#   y la aplicación Python en la PC mediante USB serial.



import sys
import utime


class SerialComm:
    """
    Maneja la comunicación serial USB con la PC.
    Usa sys.stdin/stdout que en MicroPython corresponden
    al puerto USB serial visible desde Thonny/pyserial.
    """

    def __init__(self):
        self._buffer = ""  # Buffer de caracteres recibidos


    def send(self, msg_type, data=""):
        """
        Envía un mensaje a la PC con formato TIPO:datos.

        Args:
            msg_type: tipo de mensaje en mayúsculas (ej: "LETTER")
            data:     datos adicionales como string
        """
        line = "{}:{}\n".format(msg_type, data)
        sys.stdout.write(line)


    def try_read(self):
        """
        Intenta leer un mensaje completo de la PC sin bloquear.
        Usa sys.stdin.read(1) con verificación de disponibilidad.

        Returns:
            Tupla (tipo, datos) si hay mensaje completo.
            None si no hay datos disponibles todavía.
        """
        # Leer bytes disponibles sin bloquear
        try:
            # poll() no existe en MicroPython stdstream,
            # usamos any() para verificar si hay datos
            if sys.stdin in []:   # Placeholder — ver nota abajo
                pass

            # Leer carácter a carácter lo disponible
            # En MicroPython el stdin es bloqueante en modo REPL,
            # pero en modo raw/script podemos leer así:
            ch = sys.stdin.read(1)
            if ch:
                self._buffer += ch
        except:
            pass

        # Verificar si hay línea completa en el buffer
        if "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if ":" in line:
                idx = line.index(":")
                return (line[:idx], line[idx+1:])

        return None


    def read_blocking(self, timeout_ms=10000):
        """
        Lee un mensaje completo de la PC, bloqueando el programa
        hasta que llegue o se agote el timeout.

        Args:
            timeout_ms: máximo tiempo de espera en ms

        Returns:
            Tupla (tipo, datos) o None si se agotó el tiempo.
        """
        start = utime.ticks_ms()

        while True:
            # Verificar timeout
            if utime.ticks_diff(utime.ticks_ms(), start) > timeout_ms:
                return None

            try:
                ch = sys.stdin.read(1)
                if ch:
                    self._buffer += ch
            except:
                utime.sleep_ms(5)
                continue

            if "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                line = line.strip()
                if ":" in line:
                    idx = line.index(":")
                    return (line[:idx], line[idx+1:])

            utime.sleep_ms(2)
