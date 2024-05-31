# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries

# SPDX-License-Identifier: MIT

import time
import board
import pwmio
import digitalio
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

# Set the motor decay modes (if unset the default will be FAST_DECAY)
mot_a.decay_mode = DECAY_MODE
mot_b.decay_mode = DECAY_MODE
mot_c.decay_mode = DECAY_MODE
mot_d.decay_mode = DECAY_MODE

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

Motor_Speed = 1.0
Motor_Retract_Speed = 1.0
Motor_Retract_Timing = 3.75

ZSwitch = False

ZPosFlag = False
ZNegFlag = False
YPosFlag = False
YNegFlag = False
XPosFlag = False
XNegFlag = False

ZPosMoveFlag = False
ZNegMoveFlag = False
YPosMoveFlag = False
YNegMoveFlag = False
XPosMoveFlag = False
XNegMoveFlag = False


VOLTAGE_GAIN = 13.9 / 3.9
CURRENT_GAIN = 1 / 0.47
CURRENT_OFFSET = -0.005
CURRENT_THRESHOLD_X = 0.2
CURRENT_THRESHOLD_Y = 0.2
CURRENT_THRESHOLD_Z = 0.2

current_list = [0, 0, 0, 0]
function_current_list = [0, 0, 0, 0]

def Read_Current():
    # Read the current sense and print the value
    function_current_list = []
    for i in range(board.NUM_MOTORS):
        select(i + board.CURRENT_SENSE_A_ADDR)
        current = (get_voltage(analog_in) + CURRENT_OFFSET) * CURRENT_GAIN
        function_current_list.append(current)
    return function_current_list

def Motor_Retract(Motor, Speed):
    print('Motor current limit reached')
    Motor.throttle = Speed
    time.sleep(Motor_Retract_Timing)
    Motor.throttle = 0.0

def Motor_Pos_Movement(Motor, CList, BoolMain, BoolOther, BoolMove, LastJoyVal, Current_Threshold):
    current_list = Read_Current()
    print(current_list)
    if (LastJoyVal > Joy_High and current_list[CList] < Current_Threshold and BoolMain is False):
        print("PosMove")
        Motor.throttle = +Motor_Speed
        BoolOther = False
        BoolMove = True
    elif (current_list[CList] > Current_Threshold and BoolOther is False):
        print("PosFlag")
        Motor.throttle = 0.0
        #Motor_Retract(Motor, -Motor_Retract_Speed)
        BoolMain = True
        BoolMove = False
    elif (LastJoyVal > Joy_Low):
        print("PosStop")
        Motor.throttle = 0.0
        BoolMove = False
    time.sleep(0.05)
    return BoolMain, BoolOther, BoolMove

def Motor_Neg_Movement(Motor, CList, BoolMain, BoolOther, BoolMove, LastJoyVal, Current_Threshold):
    current_list = Read_Current()
    print(current_list)
    if (LastJoyVal < Joy_Low and current_list[CList] < Current_Threshold and BoolMain is False):
        print("NegMove")
        Motor.throttle = -Motor_Speed
        BoolOther = False
        BoolMove = True
    elif (current_list[CList] > Current_Threshold and BoolOther is False):
        print("NegFlag")
        Motor.throttle = 0.0
        #Motor_Retract(Motor, +Motor_Retract_Speed)
        BoolMain = True
        BoolMove = False
    elif (LastJoyVal < Joy_High):
        print("NegStop")
        Motor.throttle = 0.0
        BoolMove = False
    time.sleep(0.05)
    return BoolMain, BoolOther, BoolMove

# Motor_Movement(mot_b, Motor_Retract_Timing, 1, YPosFlag, YNegFlag, last_x)

while True:

    x_value = 1023 - seesaw.analog_read(Joy_X)
    y_value = 1023 - seesaw.analog_read(Joy_Y)

    if (abs(x_value - last_x) > 2) or (abs(y_value - last_y) > 2):
        last_x = x_value
        last_y = y_value
        print("X = ", last_x, "Y = ", last_y)

    #current_list = Read_Current()
    #print(current_list)

    buttons = seesaw.digital_read_bulk(button_mask)

    if not buttons & (1 << BUTTON_SELECT):
        ZPosFlag = False
        ZNegFlag = False
        YPosFlag = False
        YNegFlag = False
        XPosFlag = False
        XNegFlag = False

        ZPosMoveFlag = False
        ZNegMoveFlag = False
        YPosMoveFlag = False
        YNegMoveFlag = False
        XPosMoveFlag = False
        XNegMoveFlag = False

    if not buttons & (1 << BUTTON_Y):
        Motor_Speed = 1.0
        CURRENT_THRESHOLD_X = 0.1125
        CURRENT_THRESHOLD_Y = 0.1675
        CURRENT_THRESHOLD_Z = 0.1425

    if not buttons & (1 << BUTTON_X):
        Motor_Speed = 0.675
        CURRENT_THRESHOLD_X = 0.1925
        CURRENT_THRESHOLD_Y = 0.1875
        CURRENT_THRESHOLD_Z = 0.1875

    if not buttons & (1 << BUTTON_A):
        Motor_Speed = 0.425
        CURRENT_THRESHOLD_X = 0.25
        CURRENT_THRESHOLD_Y = 0.25
        CURRENT_THRESHOLD_Z = 0.25

    if not buttons & (1 << BUTTON_B):
        Motor_Speed = 0.275
        CURRENT_THRESHOLD_X = 0.2875
        CURRENT_THRESHOLD_Y = 0.2875
        CURRENT_THRESHOLD_Z = 0.2875

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

        if(YPosFlag is False and YNegMoveFlag is False):
            print("PositiveYStart")
            YPosFlag, YNegFlag, YPosMoveFlag = Motor_Pos_Movement(mot_c, 2, YPosFlag, YNegFlag, YPosMoveFlag, last_x, CURRENT_THRESHOLD_Y)
            print("YPOS = ", YPosFlag, "YNEG = ", YNegFlag)

        if(YNegFlag is False and YPosMoveFlag is False):
            print("NegativeYStart")
            YNegFlag, YPosFlag, YNegMoveFlag = Motor_Neg_Movement(mot_c, 2, YNegFlag, YPosFlag, YNegMoveFlag, last_x, CURRENT_THRESHOLD_Y)
            print("YPOS = ", YPosFlag, "YNEG = ", YNegFlag)

        if(XPosFlag is False and XNegMoveFlag is False):
            print("PositiveXStart")
            XPosFlag, XNegFlag, XPosMoveFlag = Motor_Pos_Movement(mot_d, 3, XPosFlag, XNegFlag, XPosMoveFlag, last_y, CURRENT_THRESHOLD_X)
            print("XPOS = ", XPosFlag, "XNEG = ", XNegFlag)

        if(XNegFlag is False and XPosMoveFlag is False):
            print("NegativeXStart")
            XNegFlag, XPosFlag, XNegMoveFlag = Motor_Neg_Movement(mot_d, 3, XNegFlag, XPosFlag, XNegMoveFlag, last_y, CURRENT_THRESHOLD_X)
            print("XPOS = ", XPosFlag, "XNEG = ", XNegFlag)

    if (ZSwitch is True):
        if(ZPosFlag is False and ZNegMoveFlag is False):
            print("PositiveStart")
            ZPosFlag, ZNegFlag, ZPosMoveFlag = Motor_Pos_Movement(mot_b, 1, ZPosFlag, ZNegFlag, ZPosMoveFlag, last_y, CURRENT_THRESHOLD_Z)
            print("ZPOS = ", ZPosFlag, "ZNEG = ", ZNegFlag)

        if(ZNegFlag is False and ZPosMoveFlag is False):
            print("NegativeStart")
            ZNegFlag, ZPosFlag, ZNegMoveFlag = Motor_Neg_Movement(mot_b, 1, ZNegFlag, ZPosFlag, ZNegMoveFlag, last_y, CURRENT_THRESHOLD_Z)
            print("ZPOS = ", ZPosFlag, "ZNEG = ", ZNegFlag)

    #time.sleep(0.05)

    '''
    # Read the current sense and print the value
    current_list = []
    for i in range(board.NUM_MOTORS):
        select(i + board.CURRENT_SENSE_A_ADDR)
        current = (get_voltage(analog_in) + CURRENT_OFFSET) * CURRENT_GAIN
        current_list.append(current)
        print("C", i + 1, " = ", round(current, 4), sep="", end=", ")
    print()
    '''

    '''
    if (last_y > Joy_High and current_list[0] < CURRENT_THRESHOLD):
            mot_a.throttle = +Motor_Speed
        elif (last_y > Joy_Low):
            mot_a.throttle = 0.0
            if (current_list[0] > CURRENT_THRESHOLD):
                print('motor current limit reached')

        if (last_y < Joy_Low and current_list[0] < CURRENT_THRESHOLD):
            mot_a.throttle = -Motor_Speed
        elif (last_y < Joy_High):
            mot_a.throttle = 0.0
            if (current_list[0] > CURRENT_THRESHOLD):
                print('motor current limit reached')
    '''

    '''
        if (last_x > Joy_High and current_list[1] < CURRENT_THRESHOLD and YPosFlag is False):
            mot_b.throttle = +Motor_Speed
            YNegFlag = False
        elif (last_x > Joy_Low):
            mot_b.throttle = 0.0
        if (current_list[1] > CURRENT_THRESHOLD):
            Motor_Retract(mot_b, -Motor_Retract_Speed, Motor_Retract_Timing, YPosFlag)

        if (last_x < Joy_Low and current_list[1] < CURRENT_THRESHOLD and YNegFlag is False):
            mot_b.throttle = -Motor_Speed
            YPosFlag = False
        elif (last_x < Joy_High):
            mot_b.throttle = 0.0
        if (current_list[1] > CURRENT_THRESHOLD):
            Motor_Retract(mot_b, +Motor_Retract_Speed, Motor_Retract_Timing, YNegFlag)

        if (last_y > Joy_High and current_list[2] < CURRENT_THRESHOLD):
            mot_c.throttle = +Motor_Speed
        elif (last_y > Joy_Low):
            mot_c.throttle = 0.0
            if (current_list[2] > CURRENT_THRESHOLD):
                print('motor current limit reached')

        if (last_y < Joy_Low and current_list[2] < CURRENT_THRESHOLD):
            mot_c.throttle = -Motor_Speed
        elif (last_y < Joy_High):
            mot_c.throttle = 0.0
            if (current_list[2] > CURRENT_THRESHOLD):
                print('motor current limit reached')
    '''
