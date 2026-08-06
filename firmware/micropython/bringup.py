# PicoEMP bring-up self-test -- Phase 2
#
# Exercises every LED, both buttons and the CHARGED input, and prints a
# structured result. It CANNOT make high voltage: GP20 (HVPWM) and GP14
# (HVPULSE) are never referenced, so both stay high-Z and R5/R10 hold the
# Q3/Q4 gates at GND. tests/test_bringup_firmware.py enforces that.
#
# Run with:  mpremote connect <port> run bringup.py
# Do not save this as main.py -- it is a test, not the firmware.

from machine import Pin
import utime

PIN_STATUS_LED = 7
PIN_HV_DET_LED = 6
PIN_CHARGE_LED = 27
PIN_ARM_SW = 28
PIN_PULSE_SW = 11
PIN_CHARGED = 18

LEDS = (
    ('STATUS', PIN_STATUS_LED),
    ('HV_DET', PIN_HV_DET_LED),
    ('CHARGE', PIN_CHARGE_LED),
)

BUTTON_TIMEOUT_MS = 15000


def led_walk():
    """Light each LED alone for a second, then all three together."""
    pins = [(name, Pin(gpio, Pin.OUT)) for name, gpio in LEDS]
    for _, pin in pins:
        pin.off()
    for name, pin in pins:
        print('LED %s: ON -- confirm it lit' % name)
        pin.on()
        utime.sleep_ms(1000)
        pin.off()
    print('LED ALL: ON')
    for _, pin in pins:
        pin.on()
    utime.sleep_ms(2000)
    for _, pin in pins:
        pin.off()
    print('LED ALL: OFF')


def wait_for_press(name, pin, pressed_level):
    """Block until `pin` reads `pressed_level`, or the timeout expires."""
    print('BUTTON %s: press it now (%d s)' % (name, BUTTON_TIMEOUT_MS // 1000))
    deadline = utime.ticks_add(utime.ticks_ms(), BUTTON_TIMEOUT_MS)
    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        if pin.value() == pressed_level:
            print('BUTTON %s: PASS' % name)
            return True
        utime.sleep_ms(10)
    print('BUTTON %s: FAIL -- no press seen' % name)
    return False


def main():
    print('=== PicoEMP bring-up self-test (Phase 2) ===')
    print('HVPWM and HVPULSE are not driven by this script.')

    led_walk()

    # SW1 pulls ARM_SW up to +3V3, so pressed reads high against a pulldown.
    arm = Pin(PIN_ARM_SW, Pin.IN, Pin.PULL_DOWN)
    # SW2 pulls PULSE_SW down to GND, so pressed reads low against a pullup.
    pulse = Pin(PIN_PULSE_SW, Pin.IN, Pin.PULL_UP)
    # R6 already pulls CHARGED up to +3V3; the opto pulls it low when the
    # rail is charged. No internal pull.
    charged = Pin(PIN_CHARGED, Pin.IN)

    print('CHARGED idle level: %d (1 = not charged, expected at rest)'
          % charged.value())

    ok_arm = wait_for_press('ARM', arm, 1)
    ok_pulse = wait_for_press('PULSE', pulse, 0)

    print('=== RESULT: %s ===' % ('PASS' if (ok_arm and ok_pulse) else 'FAIL'))


main()
