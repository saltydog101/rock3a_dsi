# BTT Pi TFT50 DSI Display on Radxa Rock 3A

Driver and configuration to run a **BigTreeTech Pi TFT50 V2.0** 5-inch DSI touchscreen on a **Radxa Rock 3A** (RK3568) with Armbian mainline kernel (6.18.x).

## What's Included

- **Modified `panel-raspberrypi-touchscreen` kernel module** — patched with correct display timings and BURST mode DSI for the BTT TFT50
- **Device tree overlay** — wires DSI1 to VOP VP1 with proper endpoint configuration
- **Touch polling daemon** — userspace driver for the FT5x06 touch controller (no IRQ needed)
- **MCU init script** — powers on the display and backlight via I2C

## Hardware

| Component | Details |
|-----------|---------|
| SBC | Radxa Rock 3A (RK3568) |
| Display | BTT Pi TFT50 V2.0 (800x480, DSI) |
| Bridge | Chipone ICN6211 (DSI-to-RGB) |
| Touch | FT5x06-compatible at I2C 0x38 |
| MCU | HK32F030K6T6 at I2C 0x45 |

## Quick Start

```bash
# Build the panel driver module
make

# Install module
sudo cp panel-raspberrypi-touchscreen.ko /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/panel/
sudo depmod -a

# Compile and install device tree overlay
cpp -nostdinc -I /usr/src/linux-headers-$(uname -r)/include \
    -undef -x assembler-with-cpp rp7touchscreen.dts | \
    dtc -I dts -O dtb -o rp7touchscreen.dtbo -@ -
sudo cp rp7touchscreen.dtbo /boot/dtb/rockchip/overlay/rk35xx-rp7touchscreen.dtbo

# Enable overlay
echo 'overlays=rp7touchscreen' | sudo tee -a /boot/armbianEnv.txt

# Install touch daemon
sudo cp touch-poll.py /usr/local/bin/
sudo cp rpi-display-init.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/touch-poll.py /usr/local/bin/rpi-display-init.sh

# Install services (see install.sh or do manually)
# Reboot
sudo reboot
```

## Key Technical Details

- **BURST mode DSI is required** — SYNC_PULSE mode causes a horizontal shift due to how the ICN6211 bridge interprets the DSI stream
- **Display timings**: HFP=86, HSYNC=18, HBP=20, VFP=7, VSYNC=1, VBP=21 (derived from Radxa BSP `raspits,tc358762-5inch` and tuned)
- **DSI1 input endpoint must use `reg = <0>`** — the Rockchip DW-MIPI-DSI driver hardcodes this lookup
- **Touch uses polling** — the FT5x06 touch controller has no IRQ connection on this board, so a userspace daemon polls I2C at 50 Hz
- **Touch 180° inversion** — configure via X11 TransformationMatrix: `-1 0 1 0 -1 1 0 0 1`

## Files

| File | Description |
|------|-------------|
| `panel-raspberrypi-touchscreen.c` | Modified panel driver (timings + BURST mode) |
| `rp7touchscreen.dts` | Device tree overlay |
| `touch-poll.py` | Touch input polling daemon |
| `rpi-display-init.sh` | MCU init script |
| `Makefile` | Kernel module build |
| `rpi-panel-attiny-regulator.c` | ATtiny regulator driver (optional) |
| `tc358762.c` | TC358762 bridge driver (reference, not used) |
| `panel-raspits-tc358762.c` | Radxa BSP panel driver (reference) |

## Credits

- Radxa BSP kernel overlays and `raspits,tc358762-5inch` timing
- BigTreeTech hardware documentation
- Linux kernel `panel-raspberrypi-touchscreen` and `chipone-icn6211` drivers
