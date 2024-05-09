# This file contains the UUIDs for the D-LAB ESTIM01 device

class CoyoteV2(object):
    name: str = "D-LAB ESTIM01"
    serviceBattery: str = "955a180a-0fe2-f5aa-a094-84b8d4f3e8ad"
    characteristicBattery: str = "955a1500-0fe2-f5aa-a094-84b8d4f3e8ad"
    serviceEStim: str = "955a180b-0fe2-f5aa-a094-84b8d4f3e8ad"
    characteristicEStimPower: str = "955a1504-0fe2-f5aa-a094-84b8d4f3e8ad"
    characteristicEStimA: str = "955a1505-0fe2-f5aa-a094-84b8d4f3e8ad"
    characteristicEStimB: str = "955a1506-0fe2-f5aa-a094-84b8d4f3e8ad"

class CoyoteV3(object):
    name: str = "47L121000"
    wirelessSensorName: str = "47L120100"
    serviceWrite: str = "0000180c-0000-1000-8000-00805f9b34fb"
    serviceNotify: str = "0000180c-0000-1000-8000-00805f9b34fb"
    characteristicWrite: str = "0000150A-0000-1000-8000-00805f9b34fb"
    characteristicNotify: str = "0000150B-0000-1000-8000-00805f9b34fb"