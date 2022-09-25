from arachne.core.sim import sim_case
from amaranth.sim import Simulator, Settle
from usb_protocol.types import USBRequestType, USBRequestRecipient, USBStandardRequests
from usb_protocol.types.descriptors.dfu import DFURequests
from typing import Tuple, Union

from ....usb.control.dfu import DFURequestHandler, DFUState

@sim_case(
	domains = (('usb', 60e6),),
	dut = DFURequestHandler(configuration = 1, interface = 0)
)
def dfuRequestHandler(sim : Simulator, dut : DFURequestHandler):
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
		value : Union[Tuple[int, int], int], index : Union[Tuple[int, int], int], length : int,
		recipient : USBRequestRecipient = USBRequestRecipient.INTERFACE
	):
		yield setup.recipient.eq(recipient)
		yield setup.type.eq(type)
		yield setup.is_in_request.eq(1 if retrieve else 0)
		yield setup.request.eq(request)
		if isinstance(value, int):
			yield setup.value.eq(value)
		else:
			yield setup.value[0:8].eq(value[0]) # This specifies the interface
			yield setup.value[8:16].eq(value[1])
		if isinstance(index, int):
			yield setup.index.eq(index)
		else:
			yield setup.index[0:8].eq(index[0])
			yield setup.index[8:16].eq(index[1])
		yield setup.length.eq(length)
		yield from setupReceived()

	def sendSetupSetInterface():
		# setup packet for interface 0
		yield from sendSetup(type = USBRequestType.STANDARD, retrieve = False,
			request = USBStandardRequests.SET_INTERFACE, value = (1, 0), index = (0, 0), length = 0)

	def sendDFUDetach():
		yield from sendSetup(type = USBRequestType.CLASS, retrieve = False,
			request = DFURequests.DETACH, value = 1000, index = 0, length = 0)

	def sendDFUGetStatus():
		yield from sendSetup(type = USBRequestType.CLASS, retrieve = True,
			request = DFURequests.GET_STATUS, value = 0, index = 0, length = 6)

	def receiveData(*, data : Union[Tuple[int], bytes], check = True):
		result = True
		yield tx.ready.eq(1)
		yield interface.data_requested.eq(1)
		yield Settle()
		yield
		yield interface.data_requested.eq(0)
		assert (yield tx.valid) == 0
		assert (yield tx.payload) == 0
		while (yield tx.first) == 0:
			yield Settle()
			yield
		for idx, value in enumerate(data):
			assert (yield tx.first) == (1 if idx == 0 else 0)
			assert (yield tx.last) == (1 if idx == len(data) - 1 else 0)
			assert (yield tx.valid) == 1
			if check:
				assert (yield tx.payload) == value
			elif (yield tx.payload) != value:
				result = False
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
		return result

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

	def domainUSB():
		yield interface.active_config.eq(1)
		yield Settle()
		yield
		yield from sendSetupSetInterface()
		yield from receiveZLP()
		yield
		yield
		yield
		yield from sendDFUGetStatus()
		yield from receiveData(data = (0, 0, 0, 0, DFUState.appIdle, 0))
		yield from sendDFUDetach()
		yield from receiveZLP()
		assert (yield dut._triggerReboot) == 1
	yield domainUSB, 'usb'
