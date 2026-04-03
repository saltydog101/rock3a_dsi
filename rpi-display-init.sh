#!/bin/bash
# Initialize the BTT Pi TFT50 display and fix VPLL clock bypass.
# Must run early in boot, before DRM modeset.

# Fix VPLL bypass: The RK3568 clock framework programs VPLL but never
# takes it out of slow/bypass mode. Force it to normal mode so the
# display gets the correct pixel clock instead of 24 MHz.
#
# CRU_MODE_CON00 at 0xfdd200c0:
#   bits [11:10] = VPLL mode (0=slow/24MHz, 1=normal/PLL)
#   Upper 16 bits = write mask
#   Write 0x0C000400 = mask bits [27:26] + set bits [11:10] to 01
if command -v devmem2 > /dev/null 2>&1; then
    devmem2 0xfdd200c0 w 0x0C000400 > /dev/null 2>&1
    echo "rpi-display-init: VPLL switched to normal mode"
fi

# Initialize MCU at I2C 0x45
I2C_BUS=3
MCU_ADDR=0x45

for i in $(seq 1 30); do
    [ -e /dev/i2c-${I2C_BUS} ] && break
    sleep 0.1
done

if [ -e /dev/i2c-${I2C_BUS} ]; then
    i2cset -y ${I2C_BUS} ${MCU_ADDR} 0x85 0x01 2>/dev/null  # Power on
    sleep 0.2
    # Release all resets: LED_EN + RST_TP_N + RST_LCD_N + RST_BRIDGE_N
    # REG_PORTC (0x83) bits: 0=LED_EN, 1=RST_TP_N, 2=RST_LCD_N, 3=RST_BRIDGE_N
    i2cset -y ${I2C_BUS} ${MCU_ADDR} 0x83 0x0f 2>/dev/null  # All resets released
    sleep 0.1
    i2cset -y ${I2C_BUS} ${MCU_ADDR} 0x86 0xff 2>/dev/null  # Backlight max
    echo "rpi-display-init: display powered on, resets released, backlight enabled"
fi
