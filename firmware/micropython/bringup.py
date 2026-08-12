# PicoEMP bring-up self-test -- Phase 2
#
# Exercises every driven LED, all three buttons and the CHARGED input, and
# prints a structured result. It CANNOT make high voltage: GP20 (HVPWM) and
# GP14 (HVPULSE) are never referenced, so both stay high-Z and R5/R10 hold the
# Q3/Q4 gates at GND. GP12 (SAFE_DRV) is likewise never driven, so the U4
# photorelay stays open. tests/test_bringup_firmware.py enforces that.
#
# Run with:  mpremote connect <port> run bringup.py
# Do not save this as main.py -- it is a test, not the firmware.

from machine import Pin, ADC
import utime

PIN_STATUS_LED = 7
PIN_CHARGE_LED = 27
PIN_SAFE_LED = 15
PIN_ARM_SW = 28
PIN_PULSE_SW = 11
PIN_SAFE_SW = 13
PIN_CHARGED = 18
# CHARGED lands on two Pico pads: GP18 (U1.24) and GP26/ADC0 (U1.31). Both
# must be configured -- see the comment in main().
PIN_CHARGED_ADC = 26

# D6 (red, HV present) is deliberately absent: Q5 inverts CHARGED in hardware,
# so no GPIO drives it and there is nothing here to exercise. Confirm it by
# charging the rail (chargetest.py), not by blinking it. GP6 is now free.
LEDS = (
    ('STATUS', PIN_STATUS_LED),
    ('CHARGE', PIN_CHARGE_LED),
    ('SAFE', PIN_SAFE_LED),
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

    # All three buttons pull their net down to GND, so pressed reads low
    # against a pullup. SW1 used to pull ARM_SW up to +3V3 instead; that
    # asymmetry was inherited from upstream's milled single-layer prototype
    # and was dropped when the arm switch moved to GND.
    #
    # SW4 (SAFE) is read only. It does NOT drive SAFE_DRV (GP12) here -- the
    # photorelay is left alone so this script cannot actuate anything on the
    # HV side, same reasoning as HVPWM/HVPULSE above.
    arm = Pin(PIN_ARM_SW, Pin.IN, Pin.PULL_UP)
    pulse = Pin(PIN_PULSE_SW, Pin.IN, Pin.PULL_UP)
    safe = Pin(PIN_SAFE_SW, Pin.IN, Pin.PULL_UP)
    # CHARGED needs BOTH its pads configured. The RP2040 resets every GPIO
    # pad with its pull-down enabled (PADS_BANK0 reset value 0x56, bit 2
    # PDE=1), and CHARGED reaches two pads. Leaving GP26 at its default puts
    # a second ~65k pull-down on the net; the pair in parallel against R6's
    # 22k pull-up divides it to roughly 2 V, inside the RP2040's
    # indeterminate band (VIL 0.99 V, VIH 2.31 V), and the digital read
    # becomes arbitrary. Configuring GP26 as an analog input disables its
    # digital pull, leaving R6 -- the intended pull-up -- in charge.
    charged_adc = ADC(PIN_CHARGED_ADC)
    charged = Pin(PIN_CHARGED, Pin.IN, None)

    volts = charged_adc.read_u16() * 3.3 / 65535
    print('CHARGED idle: level %d, %.2f V (expect 1 and > 2.9 V at rest)'
          % (charged.value(), volts))
    if 1.0 < volts < 2.9:
        print('WARNING: CHARGED is in the indeterminate band -- the digital '
              'level above is not trustworthy.')

    ok_arm = wait_for_press('ARM', arm, 0)
    ok_pulse = wait_for_press('PULSE', pulse, 0)
    ok_safe = wait_for_press('SAFE', safe, 0)

    ok = ok_arm and ok_pulse and ok_safe
    print('=== RESULT: %s ===' % ('PASS' if ok else 'FAIL'))


main()
