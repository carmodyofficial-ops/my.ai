# Arduino & ESP32

## Arduino model
- Two entry points: `setup()` runs once at boot (init pins, Serial, peripherals); `loop()` runs forever after. No `main()` you write — the core provides it.
- `Serial.begin(115200);` then `Serial.println(x)`; open Serial Monitor at the same baud. `digitalWrite`/`digitalRead`/`analogRead`/`analogWrite` are the core API.
- Boards differ: classic AVR Uno (5V, 8-bit, 2KB RAM) vs ESP32 (3.3V, 32-bit dual-core, WiFi/BT, 520KB RAM). **ESP32 is 3.3V — 5V on a GPIO can kill the pin.**

## Pins & I/O
- `pinMode(pin, INPUT | OUTPUT | INPUT_PULLUP)`. Floating input reads noise — always set a pull-up/down or drive it.
- Digital: `digitalWrite(pin, HIGH/LOW)`, `digitalRead(pin)`.
- **Analog in**: `analogRead(pin)` -> 0..1023 (AVR 10-bit) or 0..4095 (ESP32 12-bit). ESP32 ADC is nonlinear near rails and needs attenuation set (`analogSetPinAttenuation`, default ~0..3.3V with 11dB).
- **PWM out**: AVR `analogWrite(pin, 0..255)`. ESP32 has no `analogWrite` on all pins historically — use LEDC: `ledcSetup(ch, freq, resBits); ledcAttachPin(pin, ch); ledcWrite(ch, duty);` (newer cores add `analogWrite`/`ledcAttach`).
- **True DAC** on ESP32 GPIO25/26 only (`dacWrite`).

## ESP32 specifics
- **Dual-core** (Pro CPU 0, App CPU 1) Xtensa LX6 @ up to 240MHz; Arduino `loop()` runs on core 1 by default; WiFi/BT stack on core 0. FreeRTOS underneath (see below).
- **WiFi**: `WiFi.begin(ssid, pass); while(WiFi.status()!=WL_CONNECTED) delay(...);`. STA/AP/AP+STA modes. **Bluetooth**: Classic (`BluetoothSerial`) and BLE (`BLEDevice`, GATT). Classic BT + WiFi share the 2.4GHz radio and RAM — heavy.
- **Deep sleep**: `esp_deep_sleep_start()` after configuring a wake source (`esp_sleep_enable_timer_wakeup(us)`, ext0/ext1 GPIO, touch). Deep sleep ~10µA vs ~40-240mA active. RAM is lost; only **RTC memory** (`RTC_DATA_ATTR int x;`) survives, and code restarts from `setup()` (check `esp_sleep_get_wakeup_cause()`).
- **RTC GPIOs** (subset) can wake from deep sleep and drive during sleep.
- **ADC2 pins are unusable while WiFi is active** — the WiFi driver owns ADC2. Use ADC1 pins (GPIO32-39) for analog reads alongside WiFi.
- **Brownout detector** resets the chip on voltage sag — common with weak USB power during WiFi TX current spikes (~500mA peaks).
- Strapping pins (0, 2, 5, 12, 15) affect boot — don't hold them at the wrong level at reset. GPIO34-39 are **input-only, no pull-ups**.

## Non-blocking timing
- **Never gate your loop on `delay()`** — it blocks everything (no sensor reads, no network servicing). Use `millis()`:
```c
unsigned long last = 0;
void loop(){
  if (millis() - last >= 1000) { last += 1000; doPeriodic(); }
  handleOtherStuff();               // runs continuously
}
```
- `millis()` wraps after ~49 days; the subtraction form `millis()-last` is wrap-safe because unsigned arithmetic. `micros()` wraps ~71 min.

## Interrupts
- `attachInterrupt(digitalPinToInterrupt(pin), isr, RISING|FALLING|CHANGE);`
- ESP32 ISRs (and any code they call) should be in IRAM: `void IRAM_ATTR isr(){ flag = true; }` — otherwise a flash cache miss during the ISR crashes.
- Keep ISRs tiny; share state with `volatile` (ESP32: `portMUX`/`portENTER_CRITICAL_ISR` for multi-core safety). No `Serial.print`, no `delay`, no `malloc`, no blocking in an ISR.

## FreeRTOS on ESP32
- The Arduino core runs on FreeRTOS. Spawn tasks: `xTaskCreatePinnedToCore(taskFn, "n", stack, param, prio, &handle, coreID);`.
- Use queues/semaphores/mutexes for cross-task/ISR data. `vTaskDelay(pdMS_TO_TICKS(ms))` yields the CPU (unlike `delay` which on ESP32 also yields, but `vTaskDelay` is explicit). Long busy loops starve the WiFi task and trip the task watchdog ("Task watchdog got triggered").

## Peripherals
- **I2C**: `Wire.begin(SDA,SCL); Wire.beginTransmission(addr); Wire.write(...); Wire.endTransmission(); Wire.requestFrom(addr,n);`. ESP32 I2C pins are remappable. Needs pull-ups.
- **SPI**: `SPI.begin(); SPI.beginTransaction(SPISettings(freq,MSBFIRST,SPI_MODE0)); SPI.transfer(x);`. ESP32 has VSPI/HSPI, remappable pins.
- **UART**: ESP32 has 3 hardware UARTs; `Serial1.begin(baud, SERIAL_8N1, rxPin, txPin);`.

## OTA & power
- **OTA**: `ArduinoOTA` (push over WiFi from IDE) or HTTP/HTTPS OTA (`Update` library, download firmware, flash to the other OTA partition, reboot). Requires an OTA-capable partition scheme. Always keep a rollback/known-good.
- Power saving ladder: reduce CPU freq (`setCpuFrequencyMhz`), WiFi modem sleep (`WiFi.setSleep(true)`), light sleep (RAM retained, fast wake), deep sleep + RTC wake for battery/sensor nodes.
- Battery node pattern: wake -> read sensor -> connect + publish (MQTT) -> deep sleep for N seconds. Keep radio-on time minimal (radio TX dominates current). A coin cell lasts months only if average current is µA-scale.

## Memory & storage
- Flash layout set by a **partition table** (`.csv`): app0/app1 (OTA slots), NVS, SPIFFS/LittleFS/FAT data partition. `Preferences` library stores key/value config in NVS across reboots.
- **PSRAM** (external SPI RAM, on WROVER modules) adds MBs for framebuffers/large buffers — enable in board config; allocate with `ps_malloc`/`heap_caps_malloc(MALLOC_CAP_SPIRAM)`.
- Watch free heap with `ESP.getFreeHeap()`; leaks (unfreed buffers, growing `String`s) crash after long uptime. `esp_get_minimum_free_heap_size()` gives the low-water mark.

## Debugging
- `Serial.printf("%d\n", x)` for trace. Decode a crash backtrace with the exception decoder (needs the `.elf`). Enable core debug level in the IDE for driver logs.
- Common crash causes: null/OOB access (LoadProhibited/StoreProhibited), stack overflow in a task, calling non-IRAM code from an ISR, watchdog timeout.

## Gotchas -> Fix
- **`delay()` blocks the loop** — misses inputs, stalls network. Fix: `millis()` scheduling / FreeRTOS tasks.
- **ADC2 pin + WiFi returns garbage/zero**. Fix: use ADC1 (GPIO32-39) for analog when WiFi is on.
- **Brownout reset loop** on WiFi start. Fix: better 5V/USB supply + big bulk cap (470µF+) on 3.3V, quality cable, or lower TX power.
- **Floating input pin** reads random HIGH/LOW. Fix: `INPUT_PULLUP` or external pull-down; add hardware debounce/RC or software debounce for buttons.
- **ISR crash on ESP32** (flash access). Fix: `IRAM_ATTR` on the ISR and anything it calls; keep it minimal.
- **`String` fragmentation**: heavy `String +` concatenation fragments the heap over time -> crashes after hours/days. Fix: fixed `char[]` buffers, `snprintf`, or reserve capacity.
- **5V on a 3.3V GPIO** damages the pin. Fix: level shifter / voltage divider for 5V sensors.
- **Task watchdog triggered**: a tight loop never yields. Fix: `vTaskDelay`/`yield()` in long loops; move heavy work off the WiFi core.
- **`analogWrite` does nothing on ESP32 (older cores)**. Fix: use LEDC (`ledcSetup`/`ledcWrite`).
- **Serial garbage**: baud mismatch. Fix: match `Serial.begin` and monitor baud (115200 common).
- **Deep sleep "forgets" variables**. Fix: `RTC_DATA_ATTR` for values that must survive; treat every wake as a fresh `setup()`.
- **GPIO34-39 used as output / with pull-up**: they're input-only. Fix: pick a different pin; add external pull resistor.
- **Blocking WiFi reconnect in `loop()`** freezes everything. Fix: non-blocking state machine / event callbacks (`WiFi.onEvent`).
- **`millis()` compared with `>` to an absolute target** breaks at wrap. Fix: always use `millis()-start >= interval`.
