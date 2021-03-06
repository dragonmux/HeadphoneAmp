from arachne.core.sim import sim_case
from arachne.util import dbg
from amaranth import Record
from amaranth.hdl.rec import DIR_FANOUT
from amaranth.sim import Simulator, Settle

from ...audio.i2s import I2S

bus = Record(
	layout = (
		('clk', [
			('o', 1, DIR_FANOUT),
		]),
		('rnl', [
			('o', 1, DIR_FANOUT),
		]),
		('data', [
			('o', 1, DIR_FANOUT),
		]),
	)
)

class Platform:
	def request(self, name, number):
		assert name == 'i2s'
		assert number == 0
		return bus

@sim_case(
	domains = (('sync', 36.864e6), ),
	platform = Platform(),
	dut = I2S()
)
def i2s(sim : Simulator, dut : I2S):
	def readBit(bit):
		for i in range(12):
			yield
		yield Settle()
		dbg(f'Got {yield bus.data.o}, expected {bit}')
		assert (yield bus.data.o) == bit
		for i in range(12):
			yield
		yield Settle()

	def readSample(sample):
		for bit in range(16):
			yield from readBit((sample >> bit) & 1)

	def domainSync():
		yield dut.clkDivider.eq(11)
		yield dut.sampleBits.eq(15)
		yield dut.sample[0].eq(0xBADA)
		yield dut.sample[1].eq(0x110C)
		yield Settle()
		yield
		yield Settle()
		assert (yield bus.rnl.o) == 1
		assert (yield dut.needSample) == 0
		yield
		yield Settle()
		assert (yield bus.rnl.o) == 0
		assert (yield dut.needSample) == 1
		yield from readSample(0xBADA)
		assert (yield bus.rnl.o) == 1
		yield from readSample(0x110C)
		assert (yield bus.rnl.o) == 0
		assert (yield dut.needSample) == 1
		yield
		yield Settle()
		assert (yield dut.needSample) == 0
		yield
	yield domainSync, 'sync'
