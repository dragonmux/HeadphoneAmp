from amaranth import Elaboratable, Module, ClockDomain, ResetSignal
from .usb import USBInterface

__all__ = (
	'AudioInterface',
)

class AudioInterface(Elaboratable):
	def elaborate(self, platform):
		m = Module()
		m.domains += ClockDomain('usb')
		m.submodules.usb = USBInterface(resource = ('ulpi', 0))

		m.d.comb += ResetSignal('usb').eq(0)
		return m
