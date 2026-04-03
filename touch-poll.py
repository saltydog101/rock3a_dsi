#!/usr/bin/env python3
"""
Polling touch driver for BTT Pi TFT50 (FT5x06 at I2C 0x38).
Reads touch data via I2C and injects events via uinput.
"""
import struct
import time
import os
import fcntl

I2C_BUS = 3
TOUCH_ADDR = 0x38
POLL_INTERVAL = 0.02  # 50 Hz

# I2C ioctl
I2C_SLAVE_FORCE = 0x0706

# uinput ioctls
UI_SET_EVBIT = 0x40045564
UI_SET_ABSBIT = 0x40045567
UI_SET_PROPBIT = 0x4004556e
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502
UI_DEV_SETUP = 0x405c5503
UI_ABS_SETUP = 0x401c5504

# Event types and codes
EV_SYN = 0x00
EV_ABS = 0x03
SYN_REPORT = 0x00
ABS_MT_SLOT = 0x2f
ABS_MT_TRACKING_ID = 0x39
ABS_MT_POSITION_X = 0x35
ABS_MT_POSITION_Y = 0x36

# Input properties
INPUT_PROP_DIRECT = 0x01


def i2c_read_reg(fd, reg, length=1):
    """Read register(s) from I2C device."""
    os.write(fd, bytes([reg]))
    return os.read(fd, length)


def setup_uinput():
    """Create a uinput device for touch input."""
    fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)

    # Set event types
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_ABS)

    # Set absolute axes
    for axis in [ABS_MT_SLOT, ABS_MT_TRACKING_ID, ABS_MT_POSITION_X, ABS_MT_POSITION_Y]:
        fcntl.ioctl(fd, UI_SET_ABSBIT, axis)

    # Set direct input property
    fcntl.ioctl(fd, UI_SET_PROPBIT, INPUT_PROP_DIRECT)

    # uinput_setup struct: name[80], id{bustype,vendor,product,version}, ff_effects_max
    name = b"BTT-TFT50-Touch" + b"\0" * 64  # pad to 80
    setup = struct.pack("80sHHHHI", name, 0x18, 0x0001, 0x0001, 0x0001, 0)  # BUS_I2C
    fcntl.ioctl(fd, UI_DEV_SETUP, setup)

    # uinput_abs_setup: u16 code, struct input_absinfo{value,min,max,fuzz,flat,resolution}
    for code, minv, maxv in [
        (ABS_MT_SLOT, 0, 4),
        (ABS_MT_TRACKING_ID, 0, 65535),
        (ABS_MT_POSITION_X, 0, 799),
        (ABS_MT_POSITION_Y, 0, 479),
    ]:
        abs_setup = struct.pack("HiiiiiI", code, 0, minv, maxv, 0, 0, 0)
        fcntl.ioctl(fd, UI_ABS_SETUP, abs_setup)

    fcntl.ioctl(fd, UI_DEV_CREATE)
    time.sleep(0.5)
    return fd


def emit(fd, etype, code, value):
    """Emit an input event."""
    t = time.time()
    sec = int(t)
    usec = int((t - sec) * 1000000)
    event = struct.pack("llHHi", sec, usec, etype, code, value)
    os.write(fd, event)


def main():
    # Open I2C bus
    i2c_fd = os.open(f"/dev/i2c-{I2C_BUS}", os.O_RDWR)
    fcntl.ioctl(i2c_fd, I2C_SLAVE_FORCE, TOUCH_ADDR)

    # Set up uinput
    uinput_fd = setup_uinput()
    print("BTT TFT50 touch polling daemon started")

    prev_touching = False

    try:
        while True:
            try:
                data = i2c_read_reg(i2c_fd, 0x00, 16)
                num_touches = data[2] & 0x0f

                if num_touches > 0:
                    # FT5x06 touch data format:
                    # reg 0x03: XH (event_flag[7:6], touch_id[3:0] in some variants, X[11:8])
                    # reg 0x04: XL (X[7:0])
                    # reg 0x05: YH (Y[11:8])
                    # reg 0x06: YL (Y[7:0])
                    x = ((data[3] & 0x0f) << 8) | data[4]
                    y = ((data[5] & 0x0f) << 8) | data[6]

                    # Clamp to display resolution
                    x = min(x, 799)
                    y = min(y, 479)

                    emit(uinput_fd, EV_ABS, ABS_MT_SLOT, 0)
                    emit(uinput_fd, EV_ABS, ABS_MT_TRACKING_ID, 1)
                    emit(uinput_fd, EV_ABS, ABS_MT_POSITION_X, x)
                    emit(uinput_fd, EV_ABS, ABS_MT_POSITION_Y, y)
                    emit(uinput_fd, EV_SYN, SYN_REPORT, 0)
                    prev_touching = True

                elif prev_touching:
                    # Touch released
                    emit(uinput_fd, EV_ABS, ABS_MT_SLOT, 0)
                    emit(uinput_fd, EV_ABS, ABS_MT_TRACKING_ID, -1)
                    emit(uinput_fd, EV_SYN, SYN_REPORT, 0)
                    prev_touching = False

            except OSError:
                pass

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        pass
    finally:
        fcntl.ioctl(uinput_fd, UI_DEV_DESTROY)
        os.close(uinput_fd)
        os.close(i2c_fd)


if __name__ == "__main__":
    main()
