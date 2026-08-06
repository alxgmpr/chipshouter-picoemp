# PicoEMP trigger front-end self-test -- Phase 5
#
# Exercises the buffered trigger input end to end:
#
#   J3 SMA centre --+
#                   +-- TRIG_IN -- R14 100R --+-- U2.2 (A)  ->  U2.4 (Y) -- GP0
#   J6.1 header ----+                         +-- R15 10k -- GND
#
# U2 is a 74LVC1G17 Schmitt buffer on +3V3 (C6 100n). R16 (0R) is the DNP
# bypass across the buffer and must stay unfitted.
#
# Note the net names: "TRIG_BUF" is the buffer's INPUT node, not its output.
# The output net is plain GP0, and it is not brought out to any header --
# probe it at U2 pin 4 or the Pico's pin 1.
#
# Two phases need no instruments:
#
#   Loopback -- jumper J6.1 (TRIG_IN) to J6.2 (GP1). The script then drives
#   its own trigger and checks GP0 follows, so the pass/fail is self-checking.
#   DISCONNECT anything else driving TRIG_IN first, including the SMA: GP1
#   would be fighting it.
#
#   On a rev A board that header is P1, so the same two pins are P1.1 and
#   P1.2. Only the silkscreen changed -- the Pico pins and the nets behind
#   them are identical, so this script needs no edit to run there.
#
#   Watch -- mirrors GP0 onto the STATUS LED and counts edges, so an outside
#   source can be checked by eye. GP1 is released to an input first, so the
#   loopback jumper no longer holds the trigger down if it is left fitted.
#   Something still has to drive the trigger: the SMA, or a wire touched from
#   TRIG_IN to +3V3. An idle input reads 0 and the LED stays dark, which looks
#   identical to a broken board.
#
# It CANNOT make high voltage: GP20 (HVPWM) and GP14 (HVPULSE) are never
# referenced, so both stay high-Z and R5/R10 hold the Q3/Q4 gates at GND.
# tests/test_bringup_firmware.py enforces that.
#
# Run with:  mpremote connect <port> run trigtest.py
# Do not save this as main.py -- it is a test, not the firmware.

from machine import Pin
import utime

PIN_TRIG = 0          # GP0, U2's output -- the buffered trigger
PIN_LOOP_SRC = 1      # GP1, on J6.2, one jumper away from TRIG_IN on J6.1
PIN_STATUS_LED = 7

SETTLE_MS = 5
IDLE_SAMPLE_MS = 500
SLOW_PULSES = 50
SLOW_HALF_MS = 1
# Narrow-pulse widths in microseconds. None means "back to back", i.e. as
# short as two consecutive MicroPython pin writes can make it -- somewhere
# under a microsecond, and the shortest edge this script can generate.
NARROW_WIDTHS_US = (100, 10, 1, None)
JUMPER_REMOVE_MS = 5000
WATCH_MS = 15000


class EdgeCounter:
    """Counts rising edges on `pin` via its IRQ.

    Rising only: a narrow pulse is two edges close together, and counting
    just one of them keeps "one pulse in, one count out" true regardless of
    how short the pulse is.

    The count is firmware-limited. A MicroPython IRQ handler will not keep
    up with a fast continuous stream, so a shortfall at high rates says
    nothing about the buffer. Everything gated on below runs slowly enough
    that the handler is not the limit.
    """

    def __init__(self, pin):
        self.n = 0
        self._pin = pin
        pin.irq(trigger=Pin.IRQ_RISING, handler=self._bump)

    def _bump(self, _pin):
        self.n += 1

    def reset(self):
        self.n = 0

    def stop(self):
        self._pin.irq(handler=None)


def check_idle(trig):
    """With nothing driving TRIG_IN, R15 must hold GP0 low and steady.

    Only a real test of R15 with the loopback jumper OFF. With it fitted,
    GP1 is already an output at 0 and holds the trigger down itself, so this
    passes whether or not R15 is there.
    """
    level = trig.value()
    stable = True
    deadline = utime.ticks_add(utime.ticks_ms(), IDLE_SAMPLE_MS)
    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        if trig.value() != level:
            stable = False
            break
    if level == 0 and stable:
        print('IDLE: PASS -- GP0 low and steady with the trigger open')
        return True
    if not stable:
        print('IDLE: FAIL -- GP0 is not settled. The buffer input is floating; '
              'suspect R15 open or unfitted.')
    else:
        print('IDLE: FAIL -- GP0 sits high with nothing driving the trigger. '
              'Suspect R15 shorted to +3V3, a solder bridge on U2, or '
              'something still connected to the SMA.')
    return False


def check_dc(trig, src):
    """Drive the trigger high and low and confirm GP0 follows.

    Returns False if GP0 never moves, which almost always means the J6.1 to
    J6.2 jumper is missing -- there is no other way for GP1 to reach the
    trigger.
    """
    src.off()
    utime.sleep_ms(SETTLE_MS)
    low = trig.value()
    src.on()
    utime.sleep_ms(SETTLE_MS)
    high = trig.value()
    src.off()
    utime.sleep_ms(SETTLE_MS)
    back = trig.value()

    if low == high:
        print('DC: NO RESPONSE -- GP0 stayed at %d while GP1 was driven both '
              'ways. Fit the jumper from J6.1 (TRIG_IN) to J6.2 (GP1) -- P1.1 '
              'to P1.2 on rev A -- or check R14/U2.' % low)
        return False
    if (low, high, back) == (0, 1, 0):
        print('DC: PASS -- GP0 follows the trigger 0/1/0')
        return True
    print('DC: FAIL -- GP0 read %d/%d/%d for driven low/high/low; expected '
          '0/1/0. An inverting part in place of the 74LVC1G17 would read '
          '1/0/1.' % (low, high, back))
    return False


def check_slow_edges(trig, src, counter):
    """Feed a known number of slow pulses and count them back."""
    counter.reset()
    for _ in range(SLOW_PULSES):
        src.on()
        utime.sleep_ms(SLOW_HALF_MS)
        src.off()
        utime.sleep_ms(SLOW_HALF_MS)
    utime.sleep_ms(SETTLE_MS)
    seen = counter.n
    if seen == SLOW_PULSES:
        print('EDGES: PASS -- %d sent, %d counted' % (SLOW_PULSES, seen))
        return True
    if seen > SLOW_PULSES:
        print('EDGES: FAIL -- %d sent, %d counted. Extra edges mean the input '
              'is double-triggering; on a jumper that points at a bad '
              'connection rather than ringing.' % (SLOW_PULSES, seen))
    else:
        print('EDGES: FAIL -- %d sent, only %d counted at %d Hz, which is slow '
              'enough that the handler is not the limit.'
              % (SLOW_PULSES, seen, 500 // SLOW_HALF_MS))
    return False


def check_narrow(trig, src, counter):
    """One pulse per width; each must produce exactly one edge.

    A trigger from a target board can be much shorter than anything above,
    so this checks the front-end passes a short pulse rather than swallowing
    it. The floor is how fast MicroPython can toggle a pin, not the buffer --
    the 74LVC1G17 is good to a few nanoseconds.
    """
    ok = True
    for width in NARROW_WIDTHS_US:
        counter.reset()
        if width is None:
            src.on()
            src.off()
            label = 'back-to-back'
        else:
            src.on()
            utime.sleep_us(width)
            src.off()
            label = '%d us' % width
        utime.sleep_ms(SETTLE_MS)
        seen = counter.n
        if seen == 1:
            print('NARROW %s: PASS' % label)
        else:
            ok = False
            print('NARROW %s: FAIL -- 1 pulse sent, %d edges counted' % (label, seen))
    return ok


def watch(trig, led, counter):
    """Mirror GP0 onto the STATUS LED and count edges from an outside source.

    This is the phase that covers the SMA, which the loopback jumper cannot
    reach. The caller must release GP1 first, or a jumper left fitted holds
    the trigger at 0 for the whole phase.
    """
    print('WATCH: %d s. The STATUS LED follows GP0. Something has to drive'
          % (WATCH_MS // 1000))
    print('       the trigger: the SMA, or a wire touched from TRIG_IN')
    print('       (J6.1 / P1.1) to +3V3 (J5.1 / P3.2 on rev A).')
    counter.reset()
    last = trig.value()
    led.value(last)
    changes = 0
    start = utime.ticks_ms()
    deadline = utime.ticks_add(start, WATCH_MS)
    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        level = trig.value()
        if level != last:
            changes += 1
            last = level
            led.value(level)
            print('  t=%6d ms  GP0 -> %d' % (utime.ticks_diff(utime.ticks_ms(), start), level))
    led.off()
    if changes == 0 and counter.n == 0:
        print('WATCH: NO SOURCE -- the trigger never moved. Nothing was '
              'driving it; this says nothing about the board.')
        return
    print('WATCH: done -- %d level changes seen by polling, %d rising edges '
          'counted by IRQ' % (changes, counter.n))
    print('       The polled figure lags a fast source; the IRQ count is the '
          'one to compare against what you sent.')


def main():
    print('=== PicoEMP trigger front-end self-test (Phase 5) ===')
    print('HVPWM and HVPULSE are not driven by this script.')
    print('Loopback phases need a jumper: J6.1 (TRIG_IN) <-> J6.2 (GP1),')
    print('P1.1 <-> P1.2 on a rev A board, and nothing else connected to')
    print('TRIG_IN or the SMA.')

    # No pull on GP0. The RP2040 resets every pad with its pull-down enabled
    # (PADS_BANK0 reset value 0x56, bit 2 PDE=1); U2 drives hard enough that
    # it would not matter, but leaving it on would mask a dead buffer output
    # by holding the pin low and reading as a plausible idle.
    trig = Pin(PIN_TRIG, Pin.IN, None)
    src = Pin(PIN_LOOP_SRC, Pin.OUT)
    src.off()
    led = Pin(PIN_STATUS_LED, Pin.OUT)
    led.off()
    counter = EdgeCounter(trig)

    try:
        results = [check_idle(trig)]
        if check_dc(trig, src):
            results.append(True)
            results.append(check_slow_edges(trig, src, counter))
            results.append(check_narrow(trig, src, counter))
        else:
            results.append(False)
            print('SKIP: edge and narrow-pulse checks need the jumper.')
        print('=== RESULT: %s ===' % ('PASS' if all(results) else 'FAIL'))
        # Release GP1 before the watch phase. Left as an output it sits at 0
        # and, through a jumper the operator has not removed, holds the
        # trigger down against whatever they are trying to drive it with.
        src.init(Pin.IN, None)
        print('GP1 released. %d s to fit a source -- SMA, or a wire from '
              'TRIG_IN to +3V3.' % (JUMPER_REMOVE_MS // 1000))
        utime.sleep_ms(JUMPER_REMOVE_MS)
        watch(trig, led, counter)
    finally:
        counter.stop()
        src.init(Pin.IN, None)
        led.off()


main()
