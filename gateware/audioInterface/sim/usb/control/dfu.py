from torii.sim import Settle
from torii.test import ToriiTestCase
from usb_construct.types import USBRequestType, USBRequestRecipient, USBStandardRequests
from usb_construct.types.descriptors.dfu import DFURequests
from typing import Tuple, Union

from ....usb.control.dfu import DFURequestHandler, DFUState

class DFURequestHandlerTestCase(ToriiTestCase):
	dut : DFURequestHandler = DFURequestHandler
	dut_args = {
		'configuration': 1,
		'interface': 0
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
		value : Union[Tuple[int, int], int], index : Union[Tuple[int, int], int], length : int,
		recipient : USBRequestRecipient = USBRequestRecipient.INTERFACE
	):
		yield self.setup.recipient.eq(recipient)
		yield self.setup.type.eq(type)
		yield self.setup.is_in_request.eq(1 if retrieve else 0)
		yield self.setup.request.eq(request)
		if isinstance(value, int):
			yield self.setup.value.eq(value)
		else:
			yield self.setup.value[0:8].eq(value[0]) # This specifies the interface
			yield self.setup.value[8:16].eq(value[1])
		if isinstance(index, int):
			yield self.setup.index.eq(index)
		else:
			yield self.setup.index[0:8].eq(index[0])
			yield self.setup.index[8:16].eq(index[1])
		yield self.setup.length.eq(length)
		yield from self.setupReceived()

	def sendSetupSetInterface(self):
		# setup packet for interface 0
		yield from self.sendSetup(type = USBRequestType.STANDARD, retrieve = False,
			request = USBStandardRequests.SET_INTERFACE, value = (1, 0), index = (0, 0), length = 0)

	def sendDFUDetach(self):
		yield from self.sendSetup(type = USBRequestType.CLASS, retrieve = False,
			request = DFURequests.DETACH, value = 1000, index = 0, length = 0)

	def sendDFUGetStatus(self):
		yield from self.sendSetup(type = USBRequestType.CLASS, retrieve = True,
			request = DFURequests.GET_STATUS, value = 0, index = 0, length = 6)

	def receiveData(self, *, data : Union[Tuple[int], bytes], check = True):
		result = True
		yield self.tx.ready.eq(1)
		yield self.interface.data_requested.eq(1)
		yield Settle()
		yield
		yield self.interface.data_requested.eq(0)
		assert (yield self.tx.valid) == 0
		assert (yield self.tx.payload) == 0
		while (yield self.tx.first) == 0:
			yield Settle()
			yield
		for idx, value in enumerate(data):
			assert (yield self.tx.first) == (1 if idx == 0 else 0)
			assert (yield self.tx.last) == (1 if idx == len(data) - 1 else 0)
			assert (yield self.tx.valid) == 1
			if check:
				assert (yield self.tx.payload) == value
			elif (yield self.tx.payload) != value:
				result = False
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
		return result

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

	@ToriiTestCase.simulation
	@ToriiTestCase.sync_domain(domain = 'usb')
	def testDFURequestHandler(self):
		self.interface = self.dut.interface
		self.setup = self.interface.setup
		self.tx = self.interface.tx
		self.rx = self.interface.rx

		yield self.interface.active_config.eq(1)
		yield Settle()
		yield
		yield from self.sendSetupSetInterface()
		yield from self.receiveZLP()
		yield
		yield
		yield
		yield from self.sendDFUGetStatus()
		yield from self.receiveData(data = (0, 0, 0, 0, DFUState.appIdle, 0))
		yield from self.sendDFUDetach()
		yield from self.receiveZLP()
		assert (yield self.dut._triggerReboot) == 1
