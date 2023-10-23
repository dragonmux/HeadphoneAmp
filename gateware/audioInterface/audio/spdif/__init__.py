from torii import Elaboratable, Module, Signal
from torii.build import Platform

from .timing import Timing

class SPDIF(Elaboratable):
	def __init__(self):
		self.spdifIn = Signal()

	def elaborate(self, platform : Platform) -> Module:
		m = Module()
		m.submodules.timing = timing = Timing()

		m.d.comb += [
			timing.spdifIn.eq(self.spdifIn),
		]

		return m
