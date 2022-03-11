from amaranth import Elaboratable, Module, Signal
from luna.gateware.usb.usb2.endpoint import EndpointInterface

__all__ = (
	'AudioEndpoint',
)

class AudioEndpoint(Elaboratable):
	def __init__(self):
		# LUNA required endpoint interface values
		self.interface = EndpointInterface()
		self.bytes_in_frame = Signal(range(196 + 1))
		self.address = Signal(range(196))
		self.next_address = Signal.like(self.address)
		self.value = Signal(8)

	def elaborate(self, platform):
		m = Module()
		return m
