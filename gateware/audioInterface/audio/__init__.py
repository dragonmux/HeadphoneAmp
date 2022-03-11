from amaranth import Elaboratable, Module, Cat
from amaranth.lib.fifo import AsyncFIFO

from .i2s import I2S

__all__ = (
	'AudioStream'
)

class AudioStream(Elaboratable):
	def __init__(self):
		pass

	def elaborate(self, platform):
		m = Module()
		# m.d.sync is the audio domain.
		m.submodules.audioFIFO = fifo = AsyncFIFO(width = 48, depth = 256, r_domain = 'sync', w_domain = 'usb')
		m.submodules.i2s = i2s = I2S()

		m.d.comb += fifo.r_en.eq(0)

		with m.If(i2s.needSample):
			with m.If(fifo.r_rdy):
				m.d.sync += Cat(i2s.sample).eq(fifo.r_data)
				m.d.comb += fifo.r_en.eq(1)
			with m.Else():
				m.d.sync += Cat(i2s.sample).eq(0)

		return m
