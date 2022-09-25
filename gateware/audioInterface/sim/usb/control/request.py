from arachne.core.sim import sim_case
from amaranth.sim import Simulator, Settle
from usb_protocol.types import USBRequestType, USBRequestRecipient, USBStandardRequests
from usb_protocol.types.descriptors.uac3 import (
	AudioClassSpecificRequestCodes, AudioControlInterfaceControlSelectors, FeatureUnitControlSelectors
)
from typing import Tuple

from ....usb.control.request import AudioRequestHandler

@sim_case(
	domains = (('usb', 60e6),),
	dut = AudioRequestHandler(interfaces = (0, 1))
)
def audioRequestHandler(sim : Simulator, dut : AudioRequestHandler):
	interface = dut.interface
	setup = interface.setup
	tx = interface.tx
	rx = interface.rx

	def setupReceived():
		yield setup.received.eq(1)
		yield Settle()
		yield
		yield setup.received.eq(0)
		yield Settle()
		yield
		yield

	def sendSetup(*, type : USBRequestType, retrieve : bool, request,
		value : Tuple[int, int], index : Tuple[int, int], length : int
	):
		yield setup.recipient.eq(USBRequestRecipient.INTERFACE)
		yield setup.type.eq(type)
		yield setup.is_in_request.eq(1 if retrieve else 0)
		yield setup.request.eq(request)
		yield setup.value[0:8].eq(value[0]) # This specifies the interface
		yield setup.value[8:16].eq(value[1])
		yield setup.index[0:8].eq(index[0])
		yield setup.index[8:16].eq(index[1])
		yield setup.length.eq(length)
		yield from setupReceived()

	def sendSetupSetInterface():
		# setup packet for interface 1
		yield from sendSetup(type = USBRequestType.STANDARD, retrieve = False,
			request = USBStandardRequests.SET_INTERFACE, value = (1, 0), index = (1, 0), length = 0)

	def sendSetupPowerState(*, retrieve : bool):
		# setup packet for interface 0 to the power domain control
		yield from sendSetup(type = USBRequestType.CLASS, retrieve = retrieve,
			request = AudioClassSpecificRequestCodes.CUR,
			value = (0, AudioControlInterfaceControlSelectors.AC_POWER_DOMAIN_CONTROL),
			index = (0, 10), length = 1)

	def sendSetupMuteState(*, retrieve : bool):
		# setup packet for interface 0 to the feature unit
		yield from sendSetup(type = USBRequestType.CLASS, retrieve = retrieve,
			request = AudioClassSpecificRequestCodes.CUR,
			value = (0, FeatureUnitControlSelectors.FU_MUTE_CONTROL),
			index = (0, 2), length = 1)

	def sendSetupVolumeState(*, retrieve : bool):
		# setup packet for interface 0 to the feature unit
		yield from sendSetup(type = USBRequestType.CLASS, retrieve = retrieve,
			request = AudioClassSpecificRequestCodes.CUR,
			value = (0, FeatureUnitControlSelectors.FU_VOLUME_CONTROL),
			index = (0, 2), length = 2)

	def sendSetupVolumeRange():
		# setup packet for interface 0 to the feature unit
		yield from sendSetup(type = USBRequestType.CLASS, retrieve = True,
			request = AudioClassSpecificRequestCodes.RANGE,
			value = (0, FeatureUnitControlSelectors.FU_VOLUME_CONTROL),
			index = (0, 2), length = 8)

	def receiveData(*, data : Tuple):
		yield tx.ready.eq(1)
		yield interface.data_requested.eq(1)
		yield Settle()
		yield
		assert (yield tx.valid) == 0
		assert (yield tx.payload) == 0
		yield interface.data_requested.eq(0)
		yield Settle()
		yield
		for idx, value in enumerate(data):
			assert (yield tx.first) == (1 if idx == 0 else 0)
			assert (yield tx.last) == (1 if idx == len(data) - 1 else 0)
			assert (yield tx.valid) == 1
			assert (yield tx.payload) == value
			assert (yield interface.handshakes_out.ack) == 0
			if idx == len(data) - 1:
				yield tx.ready.eq(0)
				yield interface.status_requested.eq(1)
			yield Settle()
			yield
		assert (yield tx.valid) == 0
		assert (yield tx.payload) == 0
		assert (yield interface.handshakes_out.ack) == 1
		yield interface.status_requested.eq(0)
		yield Settle()
		yield
		assert (yield interface.handshakes_out.ack) == 0

	def receiveZLP():
		assert (yield tx.valid) == 0
		assert (yield tx.last) == 0
		yield interface.status_requested.eq(1)
		yield Settle()
		yield
		assert (yield tx.valid) == 1
		assert (yield tx.last) == 1
		yield interface.status_requested.eq(0)
		yield interface.handshakes_in.ack.eq(1)
		yield Settle()
		yield
		assert (yield tx.valid) == 0
		assert (yield tx.last) == 0
		yield interface.handshakes_in.ack.eq(0)
		yield Settle()
		yield

	def sendData(*, data : Tuple):
		yield rx.valid.eq(1)
		for value in data:
			yield Settle()
			yield
			yield rx.payload.eq(value)
			yield rx.next.eq(1)
			yield Settle()
			yield
			yield rx.next.eq(0)
		yield rx.valid.eq(0)
		yield interface.rx_ready_for_response.eq(1)
		yield Settle()
		yield
		yield interface.rx_ready_for_response.eq(0)
		yield interface.status_requested.eq(1)
		yield Settle()
		yield
		yield interface.status_requested.eq(0)
		yield interface.handshakes_in.ack.eq(1)
		yield Settle()
		yield
		yield interface.handshakes_in.ack.eq(0)
		yield Settle()
		yield

	def domainUSB():
		yield
		yield from sendSetupSetInterface()
		assert (yield dut.altModes[1]) == 0
		yield from receiveZLP()
		assert (yield dut.altModes[1]) == 1
		yield from sendSetupMuteState(retrieve = True)
		yield from receiveData(data = (0, ))
		yield from sendSetupPowerState(retrieve = False)
		yield from sendData(data = (1, ))
		yield from sendSetupVolumeRange()
		yield from receiveData(data = (1, 0, 0x88, 0xFF, 0, 0, 1, 0))
		yield from sendSetupMuteState(retrieve = False)
		yield from sendData(data = (1, ))
		yield from sendSetupPowerState(retrieve = True)
		yield from receiveData(data = (1, ))
		yield from sendSetupMuteState(retrieve = True)
		yield from receiveData(data = (1, ))
		yield from sendSetupVolumeState(retrieve = True)
		yield from receiveData(data = (0, 0))
		yield
	yield domainUSB, 'usb'
