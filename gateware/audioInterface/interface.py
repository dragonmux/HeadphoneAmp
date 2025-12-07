from torii.hdl import Elaboratable, Module, ClockDomain, ResetSignal
from .usb import USBInterface
from .audio import AudioStream

__all__ = (
	'AudioInterface',
)

class AudioInterface(Elaboratable):
	def elaborate(self, platform):
		m = Module()
		m.domains += ClockDomain('usb')
		m.submodules.usb = usb = USBInterface(resource = ('ulpi', 0))
		m.submodules.audio = AudioStream(usb)

		m.d.comb += ResetSignal('usb').eq(0)
		return m
