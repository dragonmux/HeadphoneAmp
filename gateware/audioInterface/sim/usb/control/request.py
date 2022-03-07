from arachne.core.sim import sim_case
from amaranth.sim import Simulator, Settle
from usb_protocol.types import USBRequestType, USBRequestRecipient, USBStandardRequests
from usb_protocol.types.descriptors.uac3 import (
	AudioClassSpecificRequestCodes, AudioControlInterfaceControlSelectors, FeatureUnitControlSelectors
)

from ....usb.control.request import AudioRequestHandler

@sim_case(
	domains = (('usb', 60e6),),
	dut = AudioRequestHandler(interfaces = (0, 1))
)
def audioRequestHandler(sim : Simulator, dut : AudioRequestHandler):
	interface = dut.interface
	tx = interface.tx
	rx = interface.rx

	def setupReceived():
		yield interface.setup.received.eq(1)
		yield Settle()
		yield
		yield interface.setup.received.eq(0)
		yield Settle()
		yield
		yield

	def sendSetupSetInterface(setup):
		yield setup.recipient.eq(USBRequestRecipient.INTERFACE)
		yield setup.type.eq(USBRequestType.STANDARD)
		yield setup.is_in_request.eq(0)
		yield setup.request.eq(USBStandardRequests.SET_INTERFACE)
		yield setup.value[0:8].eq(1) # Interface 1
		yield setup.value[8:16].eq(0)
		yield setup.index[0:8].eq(1)
		yield setup.index[8:16].eq(0)
		yield setup.length.eq(0)
		yield from setupReceived()

	def sendSetupPowerState(setup, *, retrieve : bool):
		yield setup.recipient.eq(USBRequestRecipient.INTERFACE)
		yield setup.type.eq(USBRequestType.CLASS)
		yield setup.is_in_request.eq(1 if retrieve else 0)
		yield setup.request.eq(AudioClassSpecificRequestCodes.CUR)
		yield setup.value[0:8].eq(0) # Interface 0
		yield setup.value[8:16].eq(AudioControlInterfaceControlSelectors.AC_POWER_DOMAIN_CONTROL)
		yield setup.index[0:8].eq(0)
		yield setup.index[8:16].eq(10) # Power Domain ID
		yield setup.length.eq(1)
		yield from setupReceived()

	def sendSetupMuteState(setup, *, retrieve : bool):
		yield setup.recipient.eq(USBRequestRecipient.INTERFACE)
		yield setup.type.eq(USBRequestType.CLASS)
		yield setup.is_in_request.eq(1 if retrieve else 0)
		yield setup.request.eq(AudioClassSpecificRequestCodes.CUR)
		yield setup.value[0:8].eq(0) # Interface 0
		yield setup.value[8:16].eq(FeatureUnitControlSelectors.FU_MUTE_CONTROL)
		yield setup.index[0:8].eq(0)
		yield setup.index[8:16].eq(2) # Input Terminal ID
		yield setup.length.eq(1)
		yield from setupReceived()

	def sendSetupVolumeState(setup, *, retrieve : bool):
		yield setup.recipient.eq(USBRequestRecipient.INTERFACE)
		yield setup.type.eq(USBRequestType.CLASS)
		yield setup.is_in_request.eq(1 if retrieve else 0)
		yield setup.request.eq(AudioClassSpecificRequestCodes.CUR)
		yield setup.value[0:8].eq(0) # Interface 0
		yield setup.value[8:16].eq(FeatureUnitControlSelectors.FU_VOLUME_CONTROL)
		yield setup.index[0:8].eq(0)
		yield setup.index[8:16].eq(2) # Input Terminal ID
		yield setup.length.eq(2)
		yield from setupReceived()

	def domainUSB():
		yield
		yield from sendSetupSetInterface(interface.setup)
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
		assert (yield dut.altModes[1]) == 0
		assert (yield tx.valid) == 0
		assert (yield tx.last) == 0
		yield interface.handshakes_in.ack.eq(0)
		yield Settle()
		yield
		assert (yield dut.altModes[1]) == 1
		yield from sendSetupMuteState(interface.setup, retrieve = True)
		yield tx.ready.eq(1)
		yield interface.data_requested.eq(1)
		yield Settle()
		yield
		assert (yield tx.valid) == 0
		assert (yield tx.payload) == 0
		yield interface.data_requested.eq(0)
		yield Settle()
		yield
		assert (yield tx.valid) == 1
		assert (yield tx.payload) == 0
		assert (yield interface.handshakes_out.ack) == 0
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
		yield from sendSetupVolumeState(interface.setup, retrieve = True)
		yield tx.ready.eq(1)
		yield interface.data_requested.eq(1)
		yield Settle()
		yield
		assert (yield tx.valid) == 0
		assert (yield tx.payload) == 0
		yield interface.data_requested.eq(0)
		yield Settle()
		yield
		assert (yield tx.valid) == 1
		assert (yield tx.payload) == 0
		yield Settle()
		yield
		assert (yield tx.valid) == 1
		assert (yield tx.payload) == 0
		assert (yield interface.handshakes_out.ack) == 0
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
		yield from sendSetupPowerState(interface.setup, retrieve = False)
		yield rx.valid.eq(1)
		yield Settle()
		yield
		yield rx.payload.eq(1)
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
		yield from sendSetupPowerState(interface.setup, retrieve = True)
		yield tx.ready.eq(1)
		yield interface.data_requested.eq(1)
		yield Settle()
		yield
		assert (yield tx.valid) == 0
		assert (yield tx.payload) == 0
		yield interface.data_requested.eq(0)
		yield Settle()
		yield
		assert (yield tx.valid) == 1
		assert (yield tx.payload) == 1
		assert (yield interface.handshakes_out.ack) == 0
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
		yield
	yield domainUSB, 'usb'
