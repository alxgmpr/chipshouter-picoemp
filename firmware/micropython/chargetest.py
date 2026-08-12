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

from machine import Pin, PWM, ADC
import utime

PIN_HVPWM = 20
PIN_CHARGED = 18
# CHARGED lands on two Pico pads: GP18 (U1.24) and GP26/ADC0 (U1.31). Both
# must be configured -- see the comment in main().
PIN_CHARGED_ADC = 26
# D6 (red, HV present) is no longer driven from a GPIO. Q5 inverts CHARGED in
# hardware, so the LED tracks the rail with no MCU in the path -- it will light
# on its own during this test and stay true even if this script dies.

# Empirically tuned upstream; ~250 V on C3. Do not retune.
PWM_FREQ_HZ = 2500
PWM_DUTY_U16 = 800

CHARGE_TIMEOUT_MS = 10000
DISCHARGE_TIMEOUT_MS = 30000

# CHARGED is read as a voltage, not a logic level. At rest R6's 22k pull-up
# holds the net near 3.3 V; a conducting LDA111 drags it to near 0. Reading
# the ADC instead of the pin removes any dependence on where the RP2040's
# input thresholds happen to fall.
CHARGED_MAX_V = 1.0   # at or below this, the opto is conducting
IDLE_MIN_V = 2.9      # at or above this, the opto is off


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
    # Both CHARGED pads must be configured. The RP2040 resets every GPIO pad
    # with its pull-down enabled (PADS_BANK0 reset value 0x56, bit 2 PDE=1),
    # and CHARGED reaches two of them. Leaving GP26 at its default puts a
    # second ~65k pull-down on the net; the pair in parallel against R6's 22k
    # pull-up divides it to roughly 2 V, inside the RP2040's indeterminate
    # band, and a digital read of GP18 becomes arbitrary. Configuring GP26 as
    # an analog input disables its digital pull and gives us a real voltage.
    charged_adc = ADC(PIN_CHARGED_ADC)
    Pin(PIN_CHARGED, Pin.IN, None)

    def volts():
        return charged_adc.read_u16() * 3.3 / 65535

    at_rest = volts()
    print('CHARGED at rest: %.2f V' % at_rest)
    if at_rest <= CHARGED_MAX_V:
        print('ABORT: CHARGED already asserted before we started.')
        print('Hold SW3 for one second and re-run.')
        return
    if at_rest < IDLE_MIN_V:
        print('ABORT: CHARGED sits at %.2f V, between %.1f and %.1f V.'
              % (at_rest, CHARGED_MAX_V, IDLE_MIN_V))
        print('That is neither charged nor idle. Do not charge into an')
        print('unreadable sense line -- investigate before re-running.')
        return

    print('Charging, up to %d ms...' % CHARGE_TIMEOUT_MS)
    start = utime.ticks_ms()
    elapsed = None
    try:
        pwm_on()
        deadline = utime.ticks_add(start, CHARGE_TIMEOUT_MS)
        while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
            if volts() <= CHARGED_MAX_V:
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

    print('CHARGED asserted after %d ms, at %.2f V.' % (elapsed, volts()))
    print('D6 (red) should now be lit -- Q5 drives it from CHARGED directly.')
    print('Now press and hold SW3 for one second to discharge.')

    start = utime.ticks_ms()
    deadline = utime.ticks_add(start, DISCHARGE_TIMEOUT_MS)
    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        if volts() >= IDLE_MIN_V:
            print('CHARGED released after %d ms.'
                  % utime.ticks_diff(utime.ticks_ms(), start))
            print('=== RESULT: PASS ===')
            return
        utime.sleep_ms(10)

    print('=== RESULT: FAIL -- CHARGED still asserted after %d ms ==='
          % DISCHARGE_TIMEOUT_MS)
    print('The rail may still be live. Hold SW3 and do not touch J1.')


main()
