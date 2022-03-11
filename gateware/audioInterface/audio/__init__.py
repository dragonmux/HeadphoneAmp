from amaranth import Elaboratable, Module, Signal, Array, Cat
from amaranth.lib.fifo import AsyncFIFO

from ..usb import USBInterface
from .i2s import *
from .endpoint import *

__all__ = (
	'AudioStream'
)

class AudioStream(Elaboratable):
	def __init__(self, usb : USBInterface):
		self._endpoint = AudioEndpoint(1)
		usb.addEndpoint(self._endpoint)

	def elaborate(self, platform):
		m = Module()
		# m.d.sync is the audio domain.
		m.submodules.audioFIFO = fifo = AsyncFIFO(width = 48, depth = 256, r_domain = 'sync', w_domain = 'usb')
		m.submodules.i2s = i2s = I2S()

		endpoint = self._endpoint
		channel = Signal()
		sampleBytes = Array(Signal(8) for _ in range(3))
		sampleSubByte = Signal(range(3))
		sample = Array((Signal(24, name = 'sampleR'), Signal(24, name = 'sampleL')))
		writeSample = Signal()

		sampleBits = Signal(range(24))

		# I²S control
		m.d.comb += fifo.r_en.eq(0)

		with m.If(i2s.needSample):
			with m.If(fifo.r_rdy):
				m.d.sync += Cat(i2s.sample).eq(fifo.r_data)
				m.d.comb += fifo.r_en.eq(1)
			with m.Else():
				m.d.sync += Cat(i2s.sample).eq(0)

		# endpoint control
		m.d.usb += writeSample.eq(channel)

		with m.If(endpoint.valid):
			m.d.usb += sampleBytes[sampleSubByte].eq(endpoint.value)
			# If we've collected enough bytes
			with m.If(sampleSubByte == sampleBits[3:5]):
				m.d.usb += [
					sampleSubByte.eq(0),
					sample[~channel].eq(Cat(sampleBytes)),
					channel.eq(~channel),
				]
			with m.Else():
				m.d.usb += sampleSubByte.eq(sampleSubByte + 1)

		m.d.comb += [
			fifo.w_data.eq(Cat(sample)),
			fifo.w_en.eq(writeSample & ~channel),
		]
		return m
