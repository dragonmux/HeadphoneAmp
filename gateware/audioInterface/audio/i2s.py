from amaranth import Elaboratable, Module, Signal, Array, Cat

__all__ = (
	'I2S',
)

class I2S(Elaboratable):
	def __init__(self):
		# Max division is 24, but because we need to generate both halfs of the clock this is 12.
		self.clkDivider = Signal(range(12))
		self.sampleBits = Signal(range(24))
		self.sample = Array((Signal(24, name = 'sampleL'), Signal(24, name = 'sampleR')))
		self.needSample = Signal()

	def elaborate(self, platform):
		m = Module()
		bus = platform.request('i2s', 0)

		clkCounter = Signal(range(12))
		audioClk = Signal(reset = 1)
		sampleBit = Signal(range(24))
		# 0 = Left, 1 = Right
		channel = Signal(reset = 1)
		sample = Array(Signal() for i in range(24))

		sampleLatch = Signal()
		m.d.sync += sampleLatch.eq(channel)
		m.d.comb += self.needSample.eq((~channel) & sampleLatch)

		with m.FSM():
			with m.State('IDLE'):
				m.d.sync += sampleLatch.eq(0)
				with m.If((self.sampleBits != 0) & (self.clkDivider != 0)):
					m.d.sync += [
						clkCounter.eq(self.clkDivider),
						sampleBit.eq(self.sampleBits),
					]
					m.next = 'RUN'
			with m.State('RUN'):
				with m.If(clkCounter == self.clkDivider):
					m.d.sync += [
						clkCounter.eq(0),
						audioClk.eq(~audioClk),
					]

					with m.If(audioClk):
						with m.If(sampleBit == self.sampleBits):
							m.d.sync += [
								channel.eq(~channel),
								sampleBit.eq(0),
							]
						with m.Else():
							m.d.sync += sampleBit.eq(sampleBit + 1)

				with m.Else():
					m.d.sync += clkCounter.eq(clkCounter + 1)

		m.d.comb += [
			Cat(sample).eq(self.sample[channel]),
			bus.clk.eq(audioClk),
			bus.rnl.eq(channel),
			# TODO: Put the bits out MSB to LSB.
			bus.data.eq(sample[sampleBit]),
		]
		return m
