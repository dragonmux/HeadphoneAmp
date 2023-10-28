from torii import Elaboratable, Module, Signal, Array, Cat
from torii.lib.fifo import AsyncFIFO
from torii.lib.cdc import FFSynchronizer

from ..usb import USBInterface
from .i2s import *
from .spdif import *
from .endpoint import *

__all__ = (
	'AudioStream'
)

class AudioStream(Elaboratable):
	def __init__(self, usb : USBInterface):
		self._requestHandler = usb.audioRequestHandler
		self._endpoint = AudioEndpoint(1)
		usb.addEndpoint(self._endpoint)

		self._needSample = Signal()

	def elaborate(self, platform):
		m = Module()
		# m.d.sync is the audio domain.
		m.submodules.audioFIFO = fifo = AsyncFIFO(width = 48, depth = 256, r_domain = 'sync', w_domain = 'usb')
		m.submodules.i2s = i2s = I2S()
		m.submodules.spdif = spdif = SPDIF()

		endpoint = self._endpoint
		requestHandler = self._requestHandler
		channel = Signal()
		sampleBytes = Array(Signal(8, name = f'sampleByte{i}') for i in range(3))
		sampleSubByte = Signal(range(3))
		sample = Array((Signal(24, name = 'sampleL'), Signal(24, name = 'sampleR')))
		latchSample = Signal()
		writeSample = Signal()
		sampleBits = Signal(range(25))

		with m.If(requestHandler.altModes[1] == 1):
			m.d.comb += sampleBits.eq(16)
		with m.Elif(spdif.available):
			m.d.comb += sampleBits.eq(spdif.bitDepth)
		with m.Else():
			m.d.comb += sampleBits.eq(1)

		# I²S control
		with m.If(i2s.needSample):
			with m.If(fifo.r_rdy):
				m.d.sync += Cat(i2s.sample).eq(fifo.r_data)
			with m.Else():
				m.d.sync += Cat(i2s.sample).eq(0)

		# Compute `sampleBits - 1` by manually doing subtract-with-borrow, which turns `- 1` into `+ ((2 ** width) - 1)`
		# - subtraction is expensive on the iCE40, due to architecture.
		m.submodules += FFSynchronizer(sampleBits + ((2 ** sampleBits.width) - 1), i2s.sampleBits, o_domain = 'sync')
		m.d.comb += [
			i2s.clkDivider.eq(5),
			fifo.r_en.eq(i2s.needSample),
			self._needSample.eq(i2s.needSample)
		]

		# endpoint control
		m.d.usb += writeSample.eq(latchSample & ~channel)

		with m.If(endpoint.valid):
			m.d.usb += sampleBytes[sampleSubByte].eq(endpoint.value)
			# If we've collected enough bytes
			with m.If(sampleSubByte == (sampleBits[3:5] - 1)):
				m.d.usb += [
					sampleSubByte.eq(0),
					channel.eq(~channel),
					latchSample.eq(1),
				]
			with m.Else():
				m.d.usb += [
					sampleSubByte.eq(sampleSubByte + 1),
					latchSample.eq(0),
				]
		with m.Elif(spdif.sampleValid):
			m.d.usb += [
				sample[channel].eq(spdif.sample),
				channel.eq(~channel),
				latchSample.eq(1),
			]
		with m.Else():
			m.d.usb += latchSample.eq(0)

		with m.If(latchSample):
			m.d.usb += sample[~channel].eq(Cat(sampleBytes))

		m.d.comb += [
			fifo.w_data.eq(Cat(sample)),
			fifo.w_en.eq(writeSample),
		]
		return m
