#!/usr/bin/env python3

from threading import Thread
import logging
import random
import time
import sys
import serial
sys.path.insert(0, "..")

from opcua import ua, uamethod, Server

# method to be exposed through server
def set_speed(parent, variant):
    print("set_speed", variant.Value)
    a='0' + str(variant.Value)                  # 头上加个0是为了让MCU区分这是设置速度的信息还是设置转向的信息
    for i in range(3-len(str(variant.Value))):  # 补全一个字节，触发中断,因为mcu的代码是收到一个字节触发中断，如果不足一个字节
        a = a + '0'                             # 会出很多问题。 但是这个写法有个bug，就是控制台输入{"speed":5}速度会设置成50
    ser.write(a.encode())

def set_dir(parent, variant):
    print("set_dir", variant.Value)
    a = '1' + str(variant.Value)                # 头上加个1
    for i in range(3-len(str(variant.Value))):  # 补全一个字节，触发中断
        a = a + '0'
    ser.write(a.encode())

class Temperature(Thread):

    def __init__(self, dir, speed):  ##
        Thread.__init__(self)
        self._stop = False
        self.dir = dir
        self.speed = speed  ##

    def stop(self):
        self._stop = True

    def run(self):
        count = 1
        while not self._stop:

            value = g_dir
            self.dir.set_value(value)

            value = g_speed
            self.speed.set_value(value)   ##

            led_event.event.Message = ua.LocalizedText("high_speed %d" % count)
            led_event.event.Severity = count  # 这个Message和Severity不知道有什么用，但是删了定义多个事件的时候就会有问题
                                              # freeopcua官方example：server-events 里也有这些东西。
            led_event.event.speed = g_speed  # 这里如果删去.event改成led_event.speed,控制台上报的事件速度都为0
            if g_speed > 70:
                led_event.trigger()

            low_speed_event.event.speed = g_speed
            if g_speed < 20:
                low_speed_event.trigger()

            count += 1
            time.sleep(5)


if __name__ == "__main__":

    # optional: setup logging
    logging.basicConfig(level=logging.WARN)

    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.5)  # 串口设置
    g_speed = 1         # 速度和方向的全局变量
    g_dir = True

    # now setup our server
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    server.set_server_name("FreeOpcUa Example Server")

    # set all possible endpoint policies for clients to connect through
    server.set_security_policy([
                ua.SecurityPolicyType.NoSecurity,
                ua.SecurityPolicyType.Basic128Rsa15_SignAndEncrypt,
                ua.SecurityPolicyType.Basic128Rsa15_Sign,
                ua.SecurityPolicyType.Basic256_SignAndEncrypt,
                ua.SecurityPolicyType.Basic256_Sign])

    # setup our own namespace
    uri = "http://examples.freeopcua.github.io"
    idx = server.register_namespace(uri)

    # create directly some objects and variables
    demo_led = server.nodes.objects.add_object(idx, "demo_led")

    led_dir = demo_led.add_variable(idx, "direction", True)
    led_dir.set_writable()  # Set MyVariable to be writable by clients

    led_speed = demo_led.add_variable(idx, "speed", 10)  ##
    led_speed.set_writable()

    led_server1 = demo_led.add_method(idx, "set_speed", set_speed, [ua.VariantType.UInt32])
    led_server2 = demo_led.add_method(idx, "set_dir", set_dir, [ua.VariantType.UInt32])  # 添加两个服务，对于上面的两个函数

    # creating a default event object, the event object automatically will have members for all events properties
    # 创建第一个事件
    led_event_type = server.create_custom_event_type(idx,
                                                    'high_speed',
                                                    ua.ObjectIds.BaseEventType,
                                                    [('speed', ua.VariantType.UInt32)])  ##

    led_event = server.get_event_generator(led_event_type, demo_led)
    led_event.event.Severity = 300
    # 创建第二个事件
    low_speed_event_type = server.create_custom_event_type(idx,
                                                     'low_speed',
                                                     ua.ObjectIds.BaseEventType,
                                                     [('speed', ua.VariantType.UInt32)])  ##

    low_speed_event = server.get_event_generator(low_speed_event_type, demo_led)
    low_speed_event.event.Severity = 400


    # start opcua server
    server.start()
    print("Start opcua server...")
    # 开启线程
    temperature_thread = Temperature(led_dir, led_speed)  # just  a stupide class update a variable
    temperature_thread.start()

    try:

        # led_event.trigger(message="This is BaseEvent") # 这句话好像没用

        while True:
            time.sleep(5)

            if (ser.in_waiting > 0):
                buffer = ser.read(ser.in_waiting)
                #print(buffer)
                g_speed = 0
                for i in range (1, len(buffer)):
                    g_speed += (buffer[-i]-48)*10**(i-1)  # 计算速度，处理了一下数据，因为读到的buffer数组长度不确定。
                g_dir = buffer[0]-48
                print(g_speed)


    finally:
        print("Exit opcua server...")
        temperature_thread.stop()
        server.stop()