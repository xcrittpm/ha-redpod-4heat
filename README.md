# Red-Pod 4Heat (local) for Home Assistant

Control a Red-Pod pellet stove fitted with a **4Heat WiFi module** from Home Assistant, over your local network. No cloud and no account needed.

*Versión en español más abajo.*

## What you get

| Entity | What it does |
|---|---|
| **Stove** (thermostat) | Turn on/off, see room temperature, set the target temperature (5–40 °C) |
| **Combustion power** | Auto or P1–P5 |
| **Room fan** | Auto or 1–5 |
| **Ducted fan** | Auto or 1–5 (only if your stove reports it) |
| **State** | Off, Ignition, Stabilization, Running, Modulation, Standby, Shutting down… |
| **Error** | The display code with its meaning, e.g. "Er44 Door open" |
| **Combustion phase** | Code 30011 shown by name (Check-up, Ignition, Stabilization, Power 1–5, Modulation, Shutting down, Off…). While running it shows the power level the stove is actually burning at, also in Auto. Only values seen together with a known state are named; others show "Unknown" and the raw number is in the `code` attribute |
| **Problem** | On while the stove reports an error (handy for notifications) |
| **Reset error** | Clears the error once its cause is gone |
| **Exhaust / room temperature** | Live readings |
| **Hours until service** | Counts down to the 2100 h maintenance warning. With 50 h or less left, a warning appears in **Settings → Repairs** |
| **Heat output (estimated)** | kW, from the actual power level: 4.1 kW at P1/modulation, 8.3 kW at P5, evenly in between |
| **Heat produced (estimated)** | kWh, adds up the estimated output over time. Usable in the Energy dashboard |
| **Raw data** (disabled by default) | Every code the module reports, to help decode new ones |

The stove's thermostat also shows up in Apple Home or Google Home if you expose it through Home Assistant.

## Installation

### HACS (custom repository)
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/xcrittpm/ha-redpod-4heat`, type **Integration**.
2. Install **Red-Pod 4Heat (local)** and restart Home Assistant.

### Manual
Copy `custom_components/redpod_4heat` into your `config/custom_components/` folder and restart.

### Set up
**Settings → Devices & services → Add integration → Red-Pod 4Heat (local)**, then enter the module's IP address. Give the module a fixed IP in your router first.

## Notes and safety

- The integration polls the module every 30 seconds.
- While the stove is igniting it ignores "off" commands until ignition ends. This is a stove safety feature.
- **Reset error** only clears the error if the cause is gone. For example, door error Er44 stays until the door is properly closed.
- Writing to the stove is done at your own risk. Only the codes listed below are written.

## Protocol

The module listens on TCP port 80 but does not speak HTTP. Each request opens a socket and sends one array:

| Action | Sent |
|---|---|
| Read all | `["SEL","0"]` |
| Write a value | `["SEC","1","B<code 5 digits><value 12 digits>"]` → answer marker `A` = accepted |
| On / Off / Reset error | `["SEC","1","J30253000000000001"]` / `J30254…` / `J30255…` |

Codes confirmed on a Red-Pod P0147 stove:

| Code | Meaning | Values |
|---|---|---|
| 30001 | State | see `const.py` |
| 30002 | Error | display code number (12 = ignition failure, 44 = door…) |
| 30005 / 30006 | Exhaust / room temperature | °C |
| 30138 | Target temperature (read) | °C |
| 20493 | Target temperature (write) | °C |
| 20364 | Combustion power | 1–5 manual, 6 = auto |
| 20575 | Room fan | 1–5, 6 = auto |
| 20614 | Ducted fan | 1–5, 6 = auto |
| 20119 | Hours until service | h |
| 30011 | Combustion phase (partly known) | 120 check-up, −1 ignition, 0 stabilization, 1–5 actual power level while running, 9 modulation, 6 recovering ignition, 7 shutting down (also in standby), 110 off; other values unknown |

Still unknown on this stove: 20570, 30142, 30143, and the meaning of other 30011 values. If you decode one, please open an issue.

## Credits

Written from scratch. The protocol was first documented by [zaubererty/homeassistant-4heat](https://github.com/zaubererty/homeassistant-4heat); the codes above were then checked one by one on a real stove.

Not affiliated with Red-Pod or 4Heat.

---

## En español

Integración local para controlar una estufa de pellets Red-Pod con módulo WiFi **4Heat** desde Home Assistant, sin nube.

**Incluye:** termostato (encender, apagar y temperatura deseada), potencia de combustión (Auto o P1–P5), ventilador de ambiente y canalizado (Auto o 1–5), estado y error en español con su código (por ejemplo "Er44 Puerta abierta"), sensor de problema para avisos, botón para desbloquear errores, temperaturas de humos y ambiente, y horas hasta la revisión.

**Instalación:** en HACS añade este repositorio como "Integración" personalizada, instálala, reinicia y añádela en **Ajustes → Dispositivos y servicios** con la IP del módulo. Conviene darle una IP fija en el router.

**Avisos:** durante el encendido la estufa no acepta la orden de apagar hasta terminar. El botón de desbloquear solo borra el error si la causa ha desaparecido. Úsala bajo tu responsabilidad.
