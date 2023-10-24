from torii import Elaboratable, Module, Record
from torii.hdl.rec import DIR_FANOUT, DIR_FANIN
from torii.sim import Settle
from torii.test import ToriiTestCase

from ...audio import AudioStream
from ...audio.endpoint import AudioEndpoint
from ...usb.control import AudioRequestHandler

i2sBus = Record(
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

spdifBus = Record(
	layout = (
		('data', [
			('i', 1, DIR_FANIN),
		]),
	)
)

class Platform:
	def request(self, name, number, *, xdr = {}):
		if name == 'i2s':
			assert number == 0
			assert isinstance(xdr, dict)
			return i2sBus
		elif name == 'spdif':
			assert number == 0
			assert isinstance(xdr, dict)
			return spdifBus

class USBInterface(Elaboratable):
	def __init__(self):
		self.audioRequestHandler = AudioRequestHandler(configuration = 1, interfaces = (0, 1))

	def addEndpoint(self, endpoint : AudioEndpoint):
		self.endpoint = endpoint

	def elaborate(self, platform):
		m = Module()
		m.submodules.endpoint = self.endpoint
		m.submodules.audioRequestHandler = self.audioRequestHandler
		return m

class AudioInterface(Elaboratable):
	def __init__(self):
		self.usb = USBInterface()
		self.audio = AudioStream(self.usb)

	def elaborate(self, platform):
		m = Module()
		m.submodules.usb = self.usb
		m.submodules.audio = self.audio
		return m

class AudioStreamTestCase(ToriiTestCase):
	dut : AudioInterface = AudioInterface
	domains = (('sync', 36.864e6), ('usb', 60e6))
	platform = Platform()

	def readBit(self, bit):
		for i in range(6):
			yield
		yield Settle()
		(yield i2sBus.data.o) == bit
		for i in range(6):
			yield
		yield Settle()

	def readSample(self, sample):
		for bit in range(16):
			yield from self.readBit((sample >> bit) & 1)

	@ToriiTestCase.simulation
	def testAudioStream(self):
		requestHandler = self.dut.usb.audioRequestHandler
		endpoint = self.dut.usb.endpoint
		audio = self.dut.audio
		interface = endpoint.interface
		stream = interface.rx

		@ToriiTestCase.sync_domain(domain = 'sync')
		def domainSync(self):
			yield Settle()
			yield
			yield Settle()
			yield
			yield Settle()
			assert (yield i2sBus.rnl.o) == 1
			assert (yield audio._needSample) == 0
			yield
			yield Settle()
			assert (yield i2sBus.rnl.o) == 0
			assert (yield audio._needSample) == 0
			yield from self.readBit(0)
			yield Settle()
			assert (yield i2sBus.rnl.o) == 0
			assert (yield audio._needSample) == 1
			yield from self.readSample(0x0000)
			assert (yield i2sBus.rnl.o) == 1
			assert (yield audio._needSample) == 0
			yield from self.readSample(0x0000)
			assert (yield i2sBus.rnl.o) == 0
			assert (yield audio._needSample) == 1
			yield from self.readSample(0xDEAD)
			assert (yield i2sBus.rnl.o) == 1
			assert (yield audio._needSample) == 0
			yield from self.readSample(0xBEEF)
			assert (yield i2sBus.rnl.o) == 0
			assert (yield audio._needSample) == 1
			yield from self.readSample(0x110C)
			assert (yield i2sBus.rnl.o) == 1
			assert (yield audio._needSample) == 0
			yield from self.readSample(0xBADA)
			assert (yield i2sBus.rnl.o) == 0
			assert (yield audio._needSample) == 1
			yield
			yield Settle()
			assert (yield audio._needSample) == 0
			yield
			yield Settle()
			yield
		domainSync(self)

		@ToriiTestCase.sync_domain(domain = 'usb')
		def domainUSB(self):
			yield interface.active_config.eq(1)
			yield interface.tokenizer.endpoint.eq(1)
			yield interface.tokenizer.is_out.eq(1)
			yield requestHandler.altModes[1].eq(1)
			yield Settle()
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
		domainUSB(self)
