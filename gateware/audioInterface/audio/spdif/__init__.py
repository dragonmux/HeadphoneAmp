from torii import Elaboratable, Module, Signal
from torii.build import Platform

from .timing import Timing
from .biphaseDecode import BMCDecoder

__all__ = (
	'SPDIF',
)

class SPDIF(Elaboratable):
	def elaborate(self, platform : Platform) -> Module:
		m = Module()
		# Grab the S/PDIF bus from the platform
		bus = platform.request('spdif', 0)

		# Instantiate all the modules that comprise this S/PDIF decoder
		m.submodules.timing = timing = Timing()
		m.submodules.bmcDecoder = bmcDecoder = BMCDecoder()

		# Wire them all up to create the completed decoder block
		m.d.comb += [
			# The incoming data signal goes into the timing block
			timing.spdifIn.eq(bus.data.i),

			# The outgoing reset data, and bitClock signals then go into the
			# Biphase Mark Code decoder so we can get out decoded data and
			# to go into the next block
			bmcDecoder.reset.eq(timing.reset),
			bmcDecoder.dataIn.eq(timing.data),
			bmcDecoder.bitClock.eq(timing.bitClock),
		]

		return m
