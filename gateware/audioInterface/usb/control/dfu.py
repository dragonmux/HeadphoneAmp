from amaranth import Module, Signal, Instance, Cat
from usb_protocol.types import USBRequestType, USBRequestRecipient
from usb_protocol.types.descriptors.dfu import DFURequests
from luna.gateware.usb.usb2.request import USBRequestHandler, SetupPacket
from luna.gateware.usb.stream import USBInStreamInterface
from luna.gateware.stream.generator import StreamSerializer
from enum import IntEnum, unique

__all__ = (
	'DFURequestHandler',
)

@unique
class DFUState(IntEnum):
	appIdle = 0

@unique
class DFUStatus(IntEnum):
	ok = 0

class DFURequestHandler(USBRequestHandler):
	def __init__(self, *, interface : int):
		super().__init__()

		self._interface = interface
		self._triggerReboot = Signal(name = "triggerReboot")

	def elaborate(self, platform) -> Module:
		m = Module()
		interface = self.interface
		setup = interface.setup

		m.submodules.transmitter = transmitter = StreamSerializer(
			data_length = 6, domain = 'usb', stream_type = USBInStreamInterface, max_length_width = 3
		)

		triggerReboot = self._triggerReboot
		warmbootSelect = Signal(2)

		with m.FSM(domain = 'usb', name = 'dfu'):
			with m.State('IDLE'):
				with m.If(setup.received & self.handlerCondition(setup)):
					with m.Switch(setup.request):
						with m.Case(DFURequests.DETACH):
							m.next = 'HANDLE_DETACH'
						with m.Case(DFURequests.GET_STATUS):
							m.next = 'HANDLE_GET_STATUS'
						with m.Case(DFURequests.GET_STATE):
							m.next = 'HANDLE_GET_STATE'
						with m.Default():
							m.next = 'UNHANDLED'

			with m.State('HANDLE_DETACH'):
				with m.If(interface.status_requested):
					m.d.comb += self.send_zlp()

				with m.If(interface.handshakes_in.ack):
					m.d.usb += triggerReboot.eq(1)

			with m.State('HANDLE_GET_STATUS'):
				m.d.comb += [
					transmitter.stream.connect(interface.tx),
					transmitter.max_length.eq(6),
					transmitter.data[0].eq(DFUStatus.ok),
					Cat(transmitter.data[1:4]).eq(0),
					transmitter.data[4].eq(DFUState.appIdle),
					transmitter.data[5].eq(0),
				]

				with m.If(interface.data_requested):
					with m.If(setup.length == 6):
						m.d.comb += transmitter.start.eq(1)
					with m.Else():
						m.d.comb += interface.handshakes_out.stall.eq(1)
						m.next = 'IDLE'

				with m.If(interface.status_requested):
					m.d.comb += interface.handshakes_out.ack.eq(1)
					m.next = 'IDLE'

			with m.State('HANDLE_GET_STATE'):
				m.d.comb += [
					transmitter.stream.connect(interface.tx),
					transmitter.max_length.eq(1),
					transmitter.data[0].eq(DFUState.appIdle),
				]

				with m.If(interface.data_requested):
					with m.If(setup.length == 1):
						m.d.comb += transmitter.start.eq(1)
					with m.Else():
						m.d.comb += interface.handshakes_out.stall.eq(1)
						m.next = 'IDLE'

				with m.If(interface.status_requested):
					m.d.comb += interface.handshakes_out.ack.eq(1)
					m.next = 'IDLE'

			with m.State('UNHANDLED'):
				with m.If(interface.data_requested | interface.status_requested):
					m.d.comb += interface.handshakes_out.stall.eq(1)
					m.next = 'IDLE'

		m.submodules += Instance(
			'SB_WARMBOOT',
			i_BOOT = triggerReboot,
			i_S0 = warmbootSelect[0],
			i_S1 = warmbootSelect[1],
		)
		m.d.comb += warmbootSelect.eq(0b00)
		return m

	def handlerCondition(self, setup : SetupPacket):
		return (
			(setup.type == USBRequestType.CLASS) &
			(setup.recipient == USBRequestRecipient.INTERFACE) &
			(setup.index == self._interface)
		)
