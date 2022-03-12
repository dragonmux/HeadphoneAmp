from arachne.core.sim import sim_case
from amaranth import Elaboratable, Module, Record
from amaranth.hdl.rec import DIR_FANOUT
from amaranth.sim import Simulator, Settle

from ...audio import AudioStream
from ...audio.endpoint import AudioEndpoint

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

class USBInterface(Elaboratable):
	def __init__(self):
		self.stream = AudioStream(self)

	def addEndpoint(self, endpoint : AudioEndpoint):
		self.endpoint = endpoint

	def elaborate(self, platform):
		m = Module()
		m.submodules.endpoint = self.endpoint
		m.submodules.audio = self.stream
		return m

@sim_case(
	domains = (('sync', 36.864e6), ('usb', 60e6)),
	platform = Platform(),
	dut = USBInterface()
)
def audioStream(sim : Simulator, dut : USBInterface):
	endpoint = dut.endpoint
	audio = dut.stream
	interface = endpoint.interface
	stream = interface.rx

	def readBit(bit):
		for i in range(12):
			yield
		yield Settle()
		(yield bus.data.o) == bit
		for i in range(12):
			yield
		yield Settle()

	def readSample(sample):
		for bit in range(16):
			yield from readBit((sample >> bit) & 1)

	def domainSync():
		yield Settle()
		yield
		yield Settle()
		yield
		yield Settle()
		assert (yield bus.rnl.o) == 1
		assert (yield audio._needSample) == 0
		yield
		yield Settle()
		assert (yield bus.rnl.o) == 0
		assert (yield audio._needSample) == 1
		yield from readSample(0x0000)
		assert (yield bus.rnl.o) == 1
		assert (yield audio._needSample) == 0
		yield from readSample(0x0000)
		assert (yield bus.rnl.o) == 0
		assert (yield audio._needSample) == 1
		yield from readSample(0xDEAD)
		assert (yield bus.rnl.o) == 1
		assert (yield audio._needSample) == 0
		yield from readSample(0xBEEF)
		assert (yield bus.rnl.o) == 0
		assert (yield audio._needSample) == 1
		yield from readSample(0x110C)
		assert (yield bus.rnl.o) == 1
		assert (yield audio._needSample) == 0
		yield from readSample(0xBADA)
		assert (yield bus.rnl.o) == 0
		assert (yield audio._needSample) == 1
		yield
		yield Settle()
		assert (yield audio._needSample) == 0
		yield
		yield Settle()
		yield
	yield domainSync, 'sync'

	def domainUSB():
		yield interface.tokenizer.endpoint.eq(1)
		yield interface.tokenizer.is_out.eq(1)
		yield audio.sampleBits.eq(16)
		yield
		yield Settle()
		yield
		yield interface.tokenizer.new_token.eq(1)
		yield Settle()
		yield
		yield interface.tokenizer.new_token.eq(0)
		yield Settle()
		yield
		yield stream.valid.eq(1)
		yield Settle()
		yield
		yield stream.next.eq(1)
		# Send the first sample pair
		yield stream.payload.eq(0xAD)
		yield Settle()
		yield
		yield stream.payload.eq(0xDE)
		yield Settle()
		yield
		yield stream.payload.eq(0xEF)
		yield Settle()
		yield
		yield stream.payload.eq(0xBE)
		yield Settle()
		yield
		# Then send the second
		yield stream.payload.eq(0xDA)
		yield Settle()
		yield
		yield stream.payload.eq(0xBA)
		yield Settle()
		yield
		yield stream.payload.eq(0x0C)
		yield Settle()
		yield
		yield stream.payload.eq(0x11)
		yield Settle()
		yield
		yield stream.next.eq(0)
		yield Settle()
		yield
		yield stream.valid.eq(0)
		yield interface.rx_complete.eq(1)
		yield Settle()
		yield
		yield interface.rx_complete.eq(0)
		yield Settle()
		yield
	yield domainUSB, 'usb'
