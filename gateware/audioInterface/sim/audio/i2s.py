import logging
from torii import Record
from torii.hdl.rec import DIR_FANOUT
from torii.sim import Settle
from torii.test import ToriiTestCase

from ...audio.i2s import I2S

bus = Record(
	layout = (
		('clk', [
			('o', 1, DIR_FANOUT),
			('o_clk', 1, DIR_FANOUT),
		]),
		('rnl', [
			('o', 1, DIR_FANOUT),
			('o_clk', 1, DIR_FANOUT),
		]),
		('data', [
			('o', 1, DIR_FANOUT),
			('o_clk', 1, DIR_FANOUT),
		]),
	)
)

class Platform:
	def request(self, name, number, *, xdr = {}):
		assert name == 'i2s'
		assert number == 0
		assert isinstance(xdr, dict)
		return bus

class I2STestCase(ToriiTestCase):
	dut : I2S = I2S
	domains = (('sync', 36.864e6), )
	platform = Platform()

	def readBit(self, bit):
		for _ in range(6):
			yield Settle()
			yield
		logging.debug(f'Got {yield bus.data.o}, expected {bit}')
		assert (yield bus.data.o) == bit, f'Was expecting {bit}, but got {yield bus.data.o}'
		assert (yield self.dut.needSample) == 0
		for _ in range(6):
			yield Settle()
			yield

	def readSample(self, sample, channel):
		for bit in range(16):
			yield Settle()
			if bit < 15:
				if bit == 0:
					assert (yield self.dut.needSample) == (1 if channel == 0 else 0)
				else:
					assert (yield self.dut.needSample) == 0
				assert (yield bus.rnl.o) == channel
			else:
				assert (yield self.dut.needSample) == 0
				assert (yield bus.rnl.o) == 1 - channel
			yield from self.readBit(((sample << bit) >> 15) & 1)
		yield Settle()
		assert (yield self.dut.needSample) == (1 if channel == 1 else 0)

	def readSamplePartial(self, sample, *, bits, final):
		shift = bits - 1
		for bit in range(bits):
			yield Settle()
			if bit < shift or not final:
				if bit == 0:
					assert (yield self.dut.needSample) == 0
				else:
					assert (yield self.dut.needSample) == 0
				assert (yield bus.rnl.o) == 1
			else:
				assert (yield self.dut.needSample) == 0
				assert (yield bus.rnl.o) == 0
			yield from self.readBit(((sample << bit) >> shift) & 1)
		if final:
			yield Settle()
			assert (yield self.dut.needSample) == 1

	@ToriiTestCase.simulation
	@ToriiTestCase.sync_domain(domain = 'sync')
	def testI2S(self):
		yield self.dut.clkDivider.eq(5)
		yield self.dut.sampleBits.eq(15)
		assert (yield bus.rnl.o) == 1
		yield Settle()
		assert (yield bus.rnl.o) == 1
		yield
		yield Settle()
		assert (yield bus.rnl.o) == 1
		assert (yield self.dut.needSample) == 0
		yield
		yield Settle()
		assert (yield bus.rnl.o) == 0
		assert (yield self.dut.needSample) == 0
		yield from self.readBit(0)
		yield Settle()
		assert (yield bus.rnl.o) == 0
		assert (yield self.dut.needSample) == 1
		yield self.dut.sample[0].eq(0xBADA)
		yield self.dut.sample[1].eq(0x110C)
		yield from self.readSample(0xBADA, 0)
		yield from self.readSample(0x110C, 1)
		yield self.dut.sample[0].eq(0xFEDC)
		yield self.dut.sample[1].eq(0x1234)
		yield from self.readSample(0xFEDC, 0)
		yield from self.readSample(0x1234, 1)
		yield self.dut.sample[0].eq(0xABCD)
		yield self.dut.sample[1].eq(0x9876)
		yield from self.readSample(0xABCD, 0)
		yield from self.readSamplePartial(0x987, bits = 12, final = False)
		yield self.dut.sampleBits.eq(0)
		yield from self.readSamplePartial(0x6, bits = 4, final = True)
		yield Settle()
		yield
		assert (yield bus.rnl.o) == 0
		assert (yield self.dut.needSample) == 1
		yield Settle()
		yield
		assert (yield bus.rnl.o) == 1
		assert (yield self.dut.needSample) == 0
		yield Settle()
		yield
		assert (yield bus.rnl.o) == 1
		assert (yield self.dut.needSample) == 0
		yield Settle()
		yield
		yield Settle()
		yield
