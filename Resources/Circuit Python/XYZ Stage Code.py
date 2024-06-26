# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries

# SPDX-License-Identifier: MIT

import time
import board
import pwmio
import digitalio
import rotaryio
from digitalio import DigitalInOut, Direction
from analogio import AnalogIn
from adafruit_motor import motor

from micropython import const
from adafruit_seesaw.seesaw import Seesaw


addr0_pin = DigitalInOut(board.ADC_ADDR_0)
addr0_pin.direction = Direction.OUTPUT

addr1_pin = DigitalInOut(board.ADC_ADDR_1)
addr1_pin.direction = Direction.OUTPUT

addr2_pin = DigitalInOut(board.ADC_ADDR_2)
addr2_pin.direction = Direction.OUTPUT

analog_in = AnalogIn(board.SHARED_ADC)


def get_voltage(pin):
    return (pin.value * 3.3) / 65536


def select(address):
    addr0_pin.value = address & 0b001
    addr1_pin.value = address & 0b010
    addr2_pin.value = address & 0b100

# Motor constants
FREQUENCY = 25000               # Chose a frequency above human hearing
DECAY_MODE = motor.SLOW_DECAY   # The decay mode affects how the motor
# responds, with SLOW_DECAY having improved spin
# threshold and speed-to-throttle linearity

# Create the pwm objects
pwm_a_p = pwmio.PWMOut(board.MOTOR_A_P, frequency=FREQUENCY)
pwm_a_n = pwmio.PWMOut(board.MOTOR_A_N, frequency=FREQUENCY)
pwm_b_p = pwmio.PWMOut(board.MOTOR_B_P, frequency=FREQUENCY)
pwm_b_n = pwmio.PWMOut(board.MOTOR_B_N, frequency=FREQUENCY)
pwm_c_p = pwmio.PWMOut(board.MOTOR_C_P, frequency=FREQUENCY)
pwm_c_n = pwmio.PWMOut(board.MOTOR_C_N, frequency=FREQUENCY)
pwm_d_p = pwmio.PWMOut(board.MOTOR_D_P, frequency=FREQUENCY)
pwm_d_n = pwmio.PWMOut(board.MOTOR_D_N, frequency=FREQUENCY)

# Create the motor objects
mot_a = motor.DCMotor(pwm_a_p, pwm_a_n)
mot_b = motor.DCMotor(pwm_b_p, pwm_b_n)
mot_c = motor.DCMotor(pwm_c_p, pwm_c_n)
mot_d = motor.DCMotor(pwm_d_p, pwm_d_n)
motors = [mot_a, mot_b, mot_c, mot_d]

# Set the motor decay modes (if unset the default will be FAST_DECAY)
mot_a.decay_mode = DECAY_MODE
mot_b.decay_mode = DECAY_MODE
mot_c.decay_mode = DECAY_MODE
mot_d.decay_mode = DECAY_MODE

# Create the encoder objects
enc_a = rotaryio.IncrementalEncoder(board.ENCODER_A_B, board.ENCODER_A_A, divisor=1)
enc_b = rotaryio.IncrementalEncoder(board.ENCODER_B_B, board.ENCODER_B_A, divisor=1)
enc_c = rotaryio.IncrementalEncoder(board.ENCODER_C_B, board.ENCODER_C_A, divisor=1)
enc_d = rotaryio.IncrementalEncoder(board.ENCODER_D_B, board.ENCODER_D_A, divisor=1)
encoders = [enc_a, enc_b, enc_c, enc_d]

BUTTON_X = const(6)
BUTTON_Y = const(2)
BUTTON_A = const(5)
BUTTON_B = const(1)
BUTTON_SELECT = const(0)
BUTTON_START = const(16)
button_mask = const(
    (1 << BUTTON_X)
    | (1 << BUTTON_Y)
    | (1 << BUTTON_A)
    | (1 << BUTTON_B)
    | (1 << BUTTON_SELECT)
    | (1 << BUTTON_START)
)

Joy_X = const(14)
Joy_Y = const(15)
last_x = 0
last_y = 0
Joy_High = 675
Joy_Low = 375

i2c_bus = board.STEMMA_I2C()  # The built-in STEMMA QT connector on the microcontroller
# i2c_bus = board.I2C()  # Uses board.SCL and board.SDA. Use with breadboard.

seesaw = Seesaw(i2c_bus, addr=0x50)

seesaw.pin_mode_bulk(button_mask, seesaw.INPUT_PULLUP)

Motor_Speed = 0.275
Motor_Retract_Speed = 1.0
Motor_Retract_Timing = 3.75

Motor_Home_Check = False
LightSwitch = False
ZSwitch = False

ZPosMoveFlag = False
ZNegMoveFlag = False
YPosMoveFlag = False
YNegMoveFlag = False
XPosMoveFlag = False
XNegMoveFlag = False


VOLTAGE_GAIN = 13.9 / 3.9
CURRENT_GAIN = 1 / 0.47
CURRENT_OFFSET = -0.005
CURRENT_THRESHOLD_GLOBAL = 0.425

Encoder_Threshold_X = 32500
Encoder_Threshold_Y = 32500
Encoder_Threshold_Z = 18750
Encoder_Threshold_Global = 0

current_list = [0, 0, 0, 0]
function_current_list = [0, 0, 0, 0]

def Read_Current():
    # Read the current sense and print the values
    function_current_list = []
    for i in range(board.NUM_MOTORS):
        select(i + board.CURRENT_SENSE_A_ADDR)
        current = (get_voltage(analog_in) + CURRENT_OFFSET) * CURRENT_GAIN
        function_current_list.append(current)
        print("C", i + 1, " = ", round(current, 4), sep="", end=", ")
    print()
    return function_current_list

def Motor_Home():
    homes = [1, 2, 3]
    for i in homes:
        current_list = [0, 0, 0, 0]
        motors[i].throttle = -1.0
        time.sleep(0.75)
        while (current_list[i] < 0.175):
            time.sleep(0.1)
            current_list = Read_Current()
        motors[i].throttle = 0.0
        time.sleep(0.5)
        motors[i].throttle = 1.0
        time.sleep(0.875)
        motors[i].throttle = 0.0
        encoders[i].position = 0

def Motor_Pos_Movement(Motor, Encoder, CList, Speed, BoolMove, LastJoyVal, Current_Threshold, Encoder_Threshold):
    current_list = Read_Current()
    if (LastJoyVal > Joy_High and current_list[CList] < Current_Threshold and Encoder.position < Encoder_Threshold):
        # print("PosMove")
        Motor.throttle = Speed
        BoolMove = True
    elif (current_list[CList] > Current_Threshold):
        # print("PosFlag")
        Motor.throttle = 0.0
        BoolMove = False
    elif (Encoder.position > Encoder_Threshold):
        # print("PosFlag")
        Motor.throttle = 0.0
        BoolMove = False
    elif (LastJoyVal > Joy_Low):
        # print("PosStop")
        Motor.throttle = 0.0
        BoolMove = False
    time.sleep(0.01)
    return BoolMove

def Motor_Neg_Movement(Motor, Encoder, CList, Speed, BoolMove, LastJoyVal, Current_Threshold, Encoder_Threshold):
    current_list = Read_Current()
    if (LastJoyVal < Joy_Low and current_list[CList] < Current_Threshold and Encoder.position > Encoder_Threshold):
        # print("NegMove")
        Motor.throttle = Speed
        BoolMove = True
    elif (current_list[CList] > Current_Threshold):
        # print("NegFlag")
        Motor.throttle = 0.0
        BoolMove = False
    elif (Encoder.position < Encoder_Threshold):
        # print("NegFlag")
        Motor.throttle = 0.0
        BoolMove = False
    elif (LastJoyVal < Joy_High):
        # print("NegStop")
        Motor.throttle = 0.0
        BoolMove = False
    time.sleep(0.01)
    return BoolMove

while True:

    if not Motor_Home_Check:
        Motor_Home()
        Motor_Home_Check = True

    x_value = 1023 - seesaw.analog_read(Joy_X)
    y_value = 1023 - seesaw.analog_read(Joy_Y)

    if (abs(x_value - last_x) > 2) or (abs(y_value - last_y) > 2):
        last_x = x_value
        last_y = y_value
        # print("X = ", last_x, "Y = ", last_y)

    buttons = seesaw.digital_read_bulk(button_mask)

    if not buttons & (1 << BUTTON_SELECT):
        ZPosMoveFlag = False
        ZNegMoveFlag = False
        YPosMoveFlag = False
        YNegMoveFlag = False
        XPosMoveFlag = False
        XNegMoveFlag = False
        Motor_Home()

    if not buttons & (1 << BUTTON_Y):
        Motor_Speed = 0.275

    if not buttons & (1 << BUTTON_X):
        Motor_Speed = 0.625

    if not buttons & (1 << BUTTON_A):
        Motor_Speed = 1.0

    if (LightSwitch is False):
        if not buttons & (1 << BUTTON_B):
            while not buttons & (1 << BUTTON_B):
                LightSwitch = True
                mot_a.throttle = 0.5
                buttons = seesaw.digital_read_bulk(button_mask)

    if (LightSwitch is True):
        if not buttons & (1 << BUTTON_B):
            while not buttons & (1 << BUTTON_B):
                LightSwitch = False
                mot_a.throttle = 0.0
                buttons = seesaw.digital_read_bulk(button_mask)

    if (ZSwitch is False):
        if not buttons & (1 << BUTTON_START):
            while not buttons & (1 << BUTTON_START):
                ZSwitch = True
                buttons = seesaw.digital_read_bulk(button_mask)

    if (ZSwitch is True):
        if not buttons & (1 << BUTTON_START):
            while not buttons & (1 << BUTTON_START):
                ZSwitch = False
                buttons = seesaw.digital_read_bulk(button_mask)

    if (ZSwitch is False):

        if (YNegMoveFlag is False ):
            # print("PositiveYStart")
            YPosMoveFlag = Motor_Pos_Movement(mot_c, enc_c, 2, +Motor_Speed, YPosMoveFlag, last_x, CURRENT_THRESHOLD_GLOBAL, Encoder_Threshold_Y)

        if (YPosMoveFlag is False):
            # print("NegativeYStart")
            YNegMoveFlag = Motor_Neg_Movement(mot_c, enc_c, 2, -Motor_Speed, YNegMoveFlag, last_x, CURRENT_THRESHOLD_GLOBAL, Encoder_Threshold_Global)

        if (XNegMoveFlag is False):
            # print("PositiveXStart")
            XPosMoveFlag = Motor_Pos_Movement(mot_d, enc_d, 3, +Motor_Speed, XPosMoveFlag, last_y, CURRENT_THRESHOLD_GLOBAL, Encoder_Threshold_X)

        if (XPosMoveFlag is False):
            # print("NegativeXStart")
            XNegMoveFlag = Motor_Neg_Movement(mot_d, enc_d, 3, -Motor_Speed, XNegMoveFlag, last_y, CURRENT_THRESHOLD_GLOBAL, Encoder_Threshold_Global)

    if (ZSwitch is True):
        if (ZNegMoveFlag is False):
            # print("PositiveStart")
            ZPosMoveFlag = Motor_Pos_Movement(mot_b, enc_b, 1, +Motor_Speed, ZPosMoveFlag, last_y, CURRENT_THRESHOLD_GLOBAL, Encoder_Threshold_Z)

        if (ZPosMoveFlag is False):
            # print("NegativeStart")
            ZNegMoveFlag = Motor_Neg_Movement(mot_b, enc_b, 1, -Motor_Speed, ZNegMoveFlag, last_y, CURRENT_THRESHOLD_GLOBAL, Encoder_Threshold_Global)