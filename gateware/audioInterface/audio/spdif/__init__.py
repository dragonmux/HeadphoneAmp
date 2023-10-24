from torii import Elaboratable, Module, Signal
from torii.build import Platform

from .timing import Timing

__all__ = (
	'SPDIF',
)

class SPDIF(Elaboratable):
	def elaborate(self, platform : Platform) -> Module:
		m = Module()
		bus = platform.request('spdif', 0)

		m.submodules.timing = timing = Timing()

		m.d.comb += [
			timing.spdifIn.eq(bus.data.i),
		]

		return m
