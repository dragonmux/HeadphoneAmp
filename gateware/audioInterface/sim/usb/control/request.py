from torii.sim import Settle
from torii.test import ToriiTestCase
from usb_construct.types import USBRequestType, USBRequestRecipient, USBStandardRequests
from usb_construct.types.descriptors.uac3 import (
	AudioClassSpecificRequestCodes, AudioControlInterfaceControlSelectors, FeatureUnitControlSelectors
)
from typing import Tuple

from ....usb.control.request import AudioRequestHandler

class AudioRequestHandlerTestCase(ToriiTestCase):
	dut : AudioRequestHandler = AudioRequestHandler
	dut_args = {
		'configuration': 1,
		'interfaces': (0, 1)
	}
	domains = (('usb', 60e6),)

	def setupReceived(self):
		yield self.setup.received.eq(1)
		yield Settle()
		yield
		yield self.setup.received.eq(0)
		yield Settle()
		yield
		yield

	def sendSetup(self, *, type : USBRequestType, retrieve : bool, request,
		value : Tuple[int, int], index : Tuple[int, int], length : int
	):
		yield self.setup.recipient.eq(USBRequestRecipient.INTERFACE)
		yield self.setup.type.eq(type)
		yield self.setup.is_in_request.eq(1 if retrieve else 0)
		yield self.setup.request.eq(request)
		yield self.setup.value[0:8].eq(value[0]) # This specifies the interface
		yield self.setup.value[8:16].eq(value[1])
		yield self.setup.index[0:8].eq(index[0])
		yield self.setup.index[8:16].eq(index[1])
		yield self.setup.length.eq(length)
		yield from self.setupReceived()

	def sendSetupSetInterface(self):
		# setup packet for interface 1
		yield from self.sendSetup(type = USBRequestType.STANDARD, retrieve = False,
			request = USBStandardRequests.SET_INTERFACE, value = (1, 0), index = (1, 0), length = 0)

	def sendSetupPowerState(self, *, retrieve : bool):
		# setup packet for interface 0 to the power domain control
		yield from self.sendSetup(type = USBRequestType.CLASS, retrieve = retrieve,
			request = AudioClassSpecificRequestCodes.CUR,
			value = (0, AudioControlInterfaceControlSelectors.AC_POWER_DOMAIN_CONTROL),
			index = (0, 10), length = 1)

	def sendSetupMuteState(self, *, retrieve : bool):
		# setup packet for interface 0 to the feature unit
		yield from self.sendSetup(type = USBRequestType.CLASS, retrieve = retrieve,
			request = AudioClassSpecificRequestCodes.CUR,
			value = (0, FeatureUnitControlSelectors.FU_MUTE_CONTROL),
			index = (0, 2), length = 1)

	def sendSetupVolumeState(self, *, retrieve : bool):
		# setup packet for interface 0 to the feature unit
		yield from self.sendSetup(type = USBRequestType.CLASS, retrieve = retrieve,
			request = AudioClassSpecificRequestCodes.CUR,
			value = (0, FeatureUnitControlSelectors.FU_VOLUME_CONTROL),
			index = (0, 2), length = 2)

	def sendSetupVolumeRange(self):
		# setup packet for interface 0 to the feature unit
		yield from self.sendSetup(type = USBRequestType.CLASS, retrieve = True,
			request = AudioClassSpecificRequestCodes.RANGE,
			value = (0, FeatureUnitControlSelectors.FU_VOLUME_CONTROL),
			index = (0, 2), length = 8)

	def receiveData(self, *, data : Tuple):
		yield self.tx.ready.eq(1)
		yield self.interface.data_requested.eq(1)
		yield Settle()
		yield
		assert (yield self.tx.valid) == 0
		assert (yield self.tx.payload) == 0
		yield self.interface.data_requested.eq(0)
		yield Settle()
		yield
		for idx, value in enumerate(data):
			assert (yield self.tx.first) == (1 if idx == 0 else 0)
			assert (yield self.tx.last) == (1 if idx == len(data) - 1 else 0)
			assert (yield self.tx.valid) == 1
			assert (yield self.tx.payload) == value
			assert (yield self.interface.handshakes_out.ack) == 0
			if idx == len(data) - 1:
				yield self.tx.ready.eq(0)
				yield self.interface.status_requested.eq(1)
			yield Settle()
			yield
		assert (yield self.tx.valid) == 0
		assert (yield self.tx.payload) == 0
		assert (yield self.interface.handshakes_out.ack) == 1
		yield self.interface.status_requested.eq(0)
		yield Settle()
		yield
		assert (yield self.interface.handshakes_out.ack) == 0

	def receiveZLP(self):
		assert (yield self.tx.valid) == 0
		assert (yield self.tx.last) == 0
		yield self.interface.status_requested.eq(1)
		yield Settle()
		yield
		assert (yield self.tx.valid) == 1
		assert (yield self.tx.last) == 1
		yield self.interface.status_requested.eq(0)
		yield self.interface.handshakes_in.ack.eq(1)
		yield Settle()
		yield
		assert (yield self.tx.valid) == 0
		assert (yield self.tx.last) == 0
		yield self.interface.handshakes_in.ack.eq(0)
		yield Settle()
		yield

	def sendData(self, *, data : Tuple):
		yield self.rx.valid.eq(1)
		for value in data:
			yield Settle()
			yield
			yield self.rx.payload.eq(value)
			yield self.rx.next.eq(1)
			yield Settle()
			yield
			yield self.rx.next.eq(0)
		yield self.rx.valid.eq(0)
		yield self.interface.rx_ready_for_response.eq(1)
		yield Settle()
		yield
		yield self.interface.rx_ready_for_response.eq(0)
		yield self.interface.status_requested.eq(1)
		yield Settle()
		yield
		yield self.interface.status_requested.eq(0)
		yield self.interface.handshakes_in.ack.eq(1)
		yield Settle()
		yield
		yield self.interface.handshakes_in.ack.eq(0)
		yield Settle()
		yield

	@ToriiTestCase.simulation
	@ToriiTestCase.sync_domain(domain = 'usb')
	def testAudioRequestHandler(self):
		self.interface = self.dut.interface
		self.setup = self.interface.setup
		self.tx = self.interface.tx
		self.rx = self.interface.rx

		yield self.interface.active_config.eq(1)
		yield Settle()
		yield
		yield from self.sendSetupSetInterface()
		assert (yield self.dut.altModes[1]) == 0
		yield from self.receiveZLP()
		assert (yield self.dut.altModes[1]) == 1
		yield from self.sendSetupMuteState(retrieve = True)
		yield from self.receiveData(data = (0, ))
		yield from self.sendSetupPowerState(retrieve = False)
		yield from self.sendData(data = (1, ))
		yield from self.sendSetupVolumeRange()
		yield from self.receiveData(data = (1, 0, 0x88, 0xFF, 0, 0, 1, 0))
		yield from self.sendSetupMuteState(retrieve = False)
		yield from self.sendData(data = (1, ))
		yield from self.sendSetupPowerState(retrieve = True)
		yield from self.receiveData(data = (1, ))
		yield from self.sendSetupMuteState(retrieve = True)
		yield from self.receiveData(data = (1, ))
		yield from self.sendSetupVolumeState(retrieve = True)
		yield from self.receiveData(data = (0, 0))
		yield
