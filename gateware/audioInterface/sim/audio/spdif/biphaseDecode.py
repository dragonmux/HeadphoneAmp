from torii.hdl.rec import DIR_FANOUT
from torii.sim import Settle, Delay
from torii.test import ToriiTestCase

from ....audio.spdif.biphaseDecode import BMCDecoder

class BMCDecoderTestCase(ToriiTestCase):
	dut : BMCDecoder = BMCDecoder
	domains = (('usb', 60e6), )

	@ToriiTestCase.simulation
	@ToriiTestCase.sync_domain(domain = 'usb')
	def testDecoder(self):
		reset = self.dut.reset
		dataIn = self.dut.dataIn
		bitClock = self.dut.bitClock

		dataOut = self.dut.dataOut
		dataAvailable = self.dut.dataAvailable

		# Assert our preconditions and that they hold past the first cycle
		self.assertEqual((yield dataAvailable), 0)
		yield
		self.assertEqual((yield dataAvailable), 0)

		# Start a transfer and immediately abort it
		yield from self.pulse_pos(bitClock)
		self.assertEqual((yield dataAvailable), 0)
		yield from self.pulse_pos(reset)
		self.assertEqual((yield dataAvailable), 0)

		# Do the same again but this time for two half bit times to validate it works from either half
		yield from self.pulse_pos(bitClock)
		self.assertEqual((yield dataAvailable), 0)
		yield from self.pulse_pos(bitClock)
		self.assertEqual((yield dataAvailable), 0)
		yield from self.pulse_pos(reset)
		self.assertEqual((yield dataAvailable), 0)
		yield

		# Now transfer in a bit 0xca1f00d and validate we get the finishing dataAvailable pulse
		data = 0xca1f00d
		for bit in range(28):
			value = (data >> bit) & 1
			yield dataIn.eq(~dataIn)
			yield from self.pulse_pos(bitClock)
			yield
			if value == 1:
				yield dataIn.eq(~dataIn)
			yield from self.pulse_pos(bitClock)
			yield
		# Make sure the data becomes available and is correct
		self.assertEqual((yield dataAvailable), 1)
		self.assertEqual((yield dataOut), data)
		yield
		# Then that dataAvailable goes back low the cycle after
		self.assertEqual((yield dataAvailable), 0)
		yield
