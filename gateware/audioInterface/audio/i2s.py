from enum import IntEnum
from amaranth import Elaboratable, Module, Signal, Array, Cat
from amaranth.build import Platform

__all__ = (
	'I2S',
)

class Channel(IntEnum):
	left = 0
	right = 1

class I2S(Elaboratable):
	def __init__(self):
		# Max division is 12, but because we need to generate both halfs of the clock this is 6.
		self.clkDivider = Signal(range(6))
		self.sampleBits = Signal(range(24))
		self.sample = Array((Signal(24, name = 'sampleL'), Signal(24, name = 'sampleR')))
		self.needSample = Signal()

	def elaborate(self, platform : Platform) -> Module:
		m = Module()
		bus = platform.request('i2s', 0)

		clkCounter = Signal.like(self.clkDivider)
		audioClk = Signal(reset = 1)
		sampleBit = Signal(range(24))
		channelCurrent = Signal(Channel, reset = Channel.left)
		channelNext = Signal(Channel, reset = Channel.right)
		sample = Array(Signal() for _ in range(24))

		sampleLatch = Signal()
		m.d.sync += sampleLatch.eq(channelCurrent)
		m.d.comb += self.needSample.eq((~channelCurrent) & sampleLatch)

		with m.FSM():
			with m.State('IDLE'):
				m.d.sync += [
					sampleLatch.eq(0),
					channelCurrent.eq(Channel.left),
					channelNext.eq(Channel.right),
				]
				with m.If((self.sampleBits != 0) & (self.clkDivider != 0)):
					m.d.sync += [
						clkCounter.eq(self.clkDivider),
						sampleBit.eq(0),
					]
					m.next = 'SETUP'

			with m.State('SETUP'):
				with m.If(clkCounter == self.clkDivider):
					m.d.sync += [
						clkCounter.eq(0),
						audioClk.eq(~audioClk),
					]

					# If the audio clock was high switch channels and calculate lastBit.
					with m.If(audioClk):
						m.d.sync += [
							channelNext.eq(~channelNext),
							channelCurrent.eq(channelNext),
						]
					with m.Else():
						m.next = 'RUN'

				with m.Else():
					m.d.sync += clkCounter.eq(clkCounter + 1)

			with m.State('RUN'):
				# Each time the system clock to data clock counter fills to the set value,
				# Do one half of the audio data clock cycle.
				with m.If(clkCounter == self.clkDivider):
					m.d.sync += [
						clkCounter.eq(0),
						audioClk.eq(~audioClk),
					]

					# If the audio clock was high put the next sample bit out.
					with m.If(audioClk):
						# If we've put all the sample bits out for this channel then reset the sample bit
						# counter, and switch to the other channel.
						with m.If(sampleBit == 0):
							m.d.sync += sampleBit.eq(self.sampleBits)
						# Else we need to put out the next sample bit and count up.
						with m.Else():
							with m.If(sampleBit == 1):
								m.d.sync += channelNext.eq(~channelNext)
							m.d.sync += sampleBit.eq(sampleBit - 1)

						m.d.sync += channelCurrent.eq(channelNext)

				# Otherwise count up on the system clock domain
				with m.Else():
					m.d.sync += clkCounter.eq(clkCounter + 1)

				with m.If((self.sampleBits == 0) | (self.clkDivider == 0)):
					m.next = 'IDLE'

		m.d.comb += [
			Cat(sample).eq(self.sample[channelCurrent]),
			bus.clk.o.eq(audioClk),
			bus.rnl.o.eq(channelNext),
			bus.data.o.eq(sample[sampleBit]),
		]
		return m
