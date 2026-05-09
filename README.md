# StrangerTEC Morse Translator
## CE-1104 Fundamentos de Sistemas Computacionales — TEC I Sem. 2026

---

## ESTRUCTURA DE ARCHIVOS

```
StrangerTEC2/
├── pico/                    ← Cargar en el Pico W con Thonny
│   ├── main.py              ← Programa principal (loop + coordinación)
│   ├── shift_register.py    ← Control del 74HC164 (bit-bang)
│   ├── led_panel.py         ← Panel de LEDs / pared de Joyce
│   ├── morse_input.py       ← Lectura de botón + tabla Morse
│   ├── buzzer.py            ← Buzzer PWM
│   └── serial_comm.py       ← Comunicación serial con PC
└── pc/
    └── app.py               ← Interfaz Tkinter (ejecutar en PC)
```

---

## FLUJO CORRECTO DEL JUEGO (según enunciado)

```
PC selecciona frase aleatoria
        ↓
PC envía frase al Pico: "SHOW_PHRASE:HELP ME"
        ↓
Pico muestra frase en la maqueta
  ├── Modo Simple  → enciende LEDs letra por letra
  └── Modo Escucha → reproduce Morse en buzzer
        ↓
PC envía "START_INPUT:A"
        ↓
Jugador ingresa frase en Morse con el botón
  · = presión corta (< 2 unidades)
  - = presión larga (≥ 2 unidades)
        ↓
Pico decodifica y envía letras en tiempo real: "LETTER:H"
        ↓
Al detectar silencio de 30u → Pico envía "INPUT_RESULT:HELP ME"
        ↓
PC calcula puntaje y muestra resultado
        ↓
Cambia turno → Jugador B repite el proceso
        ↓
Pantalla de resultados con ganador
```

---

## CONEXIONES DE HARDWARE

### Según Figura 6 del enunciado

```
Raspberry Pi Pico W
  GP0  → Pin A y B del 74HC164 #1  (DATA)
  GP1  → Pin CLK de ambos 74HC164
  GP2  → Pin CLR de ambos 74HC164  (activo LOW)
  GP14 → Botón pulsador Morse      (PULL_DOWN)
  GP15 → Buzzer pasivo             (PWM)
  GP16 → Switch de modo            (PULL_DOWN)
  VBUS → VCC de los 74HC164 (5V via regulador 7805)
  GND  → GND común
```

### Cascada de 74HC164

```
GP0 (DATA) ──→ Pins A,B del 74HC164 #1
GP1 (CLK)  ──→ Pin CLK de 74HC164 #1
               Pin CLK de 74HC164 #2  (mismo cable)

74HC164 #1 pin Q7 ──→ Pins A,B del 74HC164 #2

74HC164 #1: Q0-Q7 → Resistencias 330Ω → LEDs 1-8
74HC164 #2: Q0-Q7 → Resistencias 330Ω → LEDs 9-16

GP2 (CLR) ──→ Pin CLR de ambos 74HC164 (LOW=reset)
```

### Pull-down del botón (según enunciado)

```python
button = Pin(14, Pin.IN, Pin.PULL_DOWN)
# HIGH (1) cuando se presiona → conectar a 3.3V al presionar
# LOW  (0) en reposo
```

---

## TEMPORIZACIÓN MORSE (según enunciado)

| Elemento          | Duración       |
|-------------------|----------------|
| Punto             | 1 unidad       |
| Raya              | 3 unidades     |
| Pausa entre símbolos | 1 unidad    |
| Pausa entre letras   | 3 unidades  |
| Pausa entre palabras | 7 unidades  |

**Unidad A = 200ms** (más rápido)
**Unidad B = 300ms** (más lento)

---

## CÓMO EJECUTAR

### 1. Cargar el Pico W

En Thonny, con el Pico conectado por USB:
1. Abrir cada archivo de la carpeta `pico/`
2. File → Save As → MicroPython device
3. Cargar en este orden:
   - shift_register.py
   - led_panel.py
   - morse_input.py
   - buzzer.py
   - serial_comm.py
   - main.py
4. Ejecutar main.py con F5

### 2. Ejecutar la interfaz PC

```bash
pip install pyserial
python pc/app.py
```

### 3. Conectar

1. En la pantalla de configuración, seleccionar el puerto del Pico
2. Hacer clic en "Conectar"
3. Configurar velocidad y modo
4. Iniciar juego

---

## PANEL DE LETRAS — LAYOUT (Figura 4)

```
FILA 1:  A  C  E  G  I  K  M  O  Q  S  U  W  Y
FILA 2:  B  D  F  H  J  L  N  P  R  T  V  X  Z
FILA 3:  0  1  2  3  4  5  6  7  8  9  -  +
```

Los 16 LEDs físicos se asignan así:
- LEDs 0-7  → Fila 1 (primeras 8 letras impares)
- LEDs 8-15 → Fila 2 (primeras 8 letras pares)
- Para Fila 3 se reutilizan los LEDs 0-11

---

## PROTOCOLO SERIAL (PC ↔ Pico)

### PC → Pico
| Comando            | Descripción                    |
|--------------------|--------------------------------|
| SET_UNIT:200       | Cambiar velocidad a 200ms      |
| SET_TRANS_MODE:SIMPLE | Modo Transmisión Simple     |
| SET_TRANS_MODE:LISTEN | Modo Escucha y Transmisión  |
| SHOW_PHRASE:SOS    | Mostrar frase en maqueta       |
| START_INPUT:A      | Jugador A empieza a ingresar   |
| SKIP:              | Saltar turno                   |
| SHOW_RESULT:WIN    | Animación de victoria          |
| RESET:             | Reiniciar sistema              |
| PING:              | Verificar conexión             |

### Pico → PC
| Mensaje            | Descripción                    |
|--------------------|--------------------------------|
| BOOT:V1            | Sistema iniciado               |
| READY:             | Esperando comandos             |
| STATUS:texto       | Estado actual                  |
| SYMBOL:.           | Punto detectado                |
| SYMBOL:-           | Raya detectada                 |
| MORSE_BUF:.-       | Buffer Morse actual            |
| LETTER:A           | Letra decodificada             |
| WORD_SPACE:        | Espacio entre palabras         |
| INPUT_RESULT:HELLO | Texto completo ingresado       |
| PONG:OK            | Respuesta al PING              |
