from torii.hdl import Elaboratable, Module, Signal
from torii_usb.usb.usb2.endpoint import EndpointInterface

__all__ = (
	'AudioEndpoint',
)

class AudioEndpoint(Elaboratable):
	def __init__(self, endpointNumber : int):
		self._endpointNumber = endpointNumber

		# LUNA required endpoint interface values
		self.interface = EndpointInterface()
		self.bytes_in_frame = Signal(range(196 + 1))
		self.address = Signal(range(196))
		self.next_address = Signal.like(self.address)
		self.value = Signal(8)
		self.valid = Signal()

	def elaborate(self, platform):
		m = Module()

		interface = self.interface
		stream = interface.rx
		newToken = interface.tokenizer.new_token

		targetingEPNum = (interface.tokenizer.endpoint == self._endpointNumber)
		targetingUs = targetingEPNum & interface.tokenizer.is_out

		m.d.comb += [
			self.valid.eq(0),
			self.value.eq(stream.data),
		]

		with m.FSM(domain = 'usb'):
			# IDLE -- the host hasn't yet sent data to our endpoint.
			with m.State('IDLE'):
				m.d.usb += [
					self.address.eq(0),
				]
				m.d.comb += self.next_address.eq(0)

				with m.If(targetingUs & newToken):
					m.next = 'RECV_DATA'

			# RECV_DATA -- handle data from the host
			with m.State('RECV_DATA'):
				m.d.usb += self.address.eq(self.next_address)
				m.d.comb += self.next_address.eq(self.address)

				with m.If(stream.valid & stream.next):
					m.d.comb += [
						self.next_address.eq(self.address + 1),
						self.valid.eq(1)
					]

				with m.If(interface.rx_complete | interface.rx_invalid):
					m.next = 'IDLE'

		return m
