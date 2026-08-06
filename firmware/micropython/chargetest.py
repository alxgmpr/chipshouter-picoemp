# PicoEMP commanded charge test -- Phase 3
#
# The ONLY script in this set that drives GP20 (HVPWM). It charges for at
# most CHARGE_TIMEOUT_MS, reports whether CHARGED asserted, then stops the
# PWM unconditionally and waits for the operator to discharge with SW3.
#
# SAFETY: J1's centre pin carries HV_RAIL from the moment CHARGED asserts
# until discharge -- not only during a pulse. Cap it, keep the shield on,
# and hold SW3 for a second before touching anything.
#
# Run with:  mpremote connect <port> run chargetest.py

from machine import Pin, PWM
import utime

PIN_HVPWM = 20
PIN_CHARGED = 18
PIN_HV_DET_LED = 6

# Empirically tuned upstream; ~250 V on C3. Do not retune.
PWM_FREQ_HZ = 2500
PWM_DUTY_U16 = 800

CHARGE_TIMEOUT_MS = 10000
DISCHARGE_TIMEOUT_MS = 30000


def pwm_off():
    """Drive HVPWM actively low. Q3's gate then sits at GND through R5."""
    Pin(PIN_HVPWM, Pin.OUT).low()


def pwm_on():
    pwm = PWM(Pin(PIN_HVPWM))
    pwm.freq(PWM_FREQ_HZ)
    pwm.duty_u16(PWM_DUTY_U16)
    return pwm


def main():
    print('=== PicoEMP charge test (Phase 3) ===')
    print('Shield on. SMA capped. Hands clear of J1.')

    pwm_off()
    charged = Pin(PIN_CHARGED, Pin.IN)
    hv_led = Pin(PIN_HV_DET_LED, Pin.OUT)
    hv_led.off()

    if charged.value() == 0:
        print('ABORT: CHARGED already asserted before we started.')
        print('Hold SW3 for one second and re-run.')
        return

    print('Charging, up to %d ms...' % CHARGE_TIMEOUT_MS)
    start = utime.ticks_ms()
    elapsed = None
    try:
        pwm_on()
        deadline = utime.ticks_add(start, CHARGE_TIMEOUT_MS)
        while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
            if charged.value() == 0:
                elapsed = utime.ticks_diff(utime.ticks_ms(), start)
                break
            utime.sleep_ms(10)
    finally:
        pwm_off()
        print('PWM stopped.')

    if elapsed is None:
        print('=== RESULT: FAIL -- CHARGED never asserted in %d ms ==='
              % CHARGE_TIMEOUT_MS)
        print('Press SW3 anyway before touching the board.')
        return

    hv_led.on()
    print('CHARGED asserted after %d ms.' % elapsed)
    print('Now press and hold SW3 for one second to discharge.')

    start = utime.ticks_ms()
    deadline = utime.ticks_add(start, DISCHARGE_TIMEOUT_MS)
    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        if charged.value() == 1:
            hv_led.off()
            print('CHARGED released after %d ms.'
                  % utime.ticks_diff(utime.ticks_ms(), start))
            print('=== RESULT: PASS ===')
            return
        utime.sleep_ms(10)

    hv_led.off()
    print('=== RESULT: FAIL -- CHARGED still asserted after %d ms ==='
          % DISCHARGE_TIMEOUT_MS)
    print('The rail may still be live. Hold SW3 and do not touch J1.')


main()
