from ast import Del
import logging
from torii import Record
from torii.hdl.rec import DIR_FANOUT
from torii.sim import Settle, Delay
from torii.test import ToriiTestCase

from ....audio.spdif.timing import Timing

class TimingTestCase(ToriiTestCase):
	dut : Timing = Timing
	domains = (('usb', 60e6), )

	def bitTime(self):
		yield Settle()
		yield Delay(.5 / (44.1e3 * 32))

	# Biphase Mark Codes data into the controller
	def bmc(self, *, data : int):
		# Get the current state of the signal
		value = yield self.dut.spdifIn
		# Create the first bit inversion to start the bit, and step to the second bit time
		yield self.dut.spdifIn.eq(1 - value)
		yield from self.bitTime()
		# Encode the transition that defines this as a 0 or 1
		if data == 1:
			yield self.dut.spdifIn.eq(value)
		yield from self.bitTime()

	@ToriiTestCase.simulation
	def testSyncZ(self):
		spdif = self.dut.spdifIn

		@ToriiTestCase.sync_domain(domain = 'usb')
		def domainSync(self : TimingTestCase):
			# Validate preconditions
			self.assertEqual((yield self.dut.reset), 1)
			self.assertEqual((yield self.dut.sync), 1)
			self.assertEqual((yield self.dut.begin), 0)
			# Wait until the first step from the S/PDIF input registers
			yield from self.step(213)
			self.assertEqual((yield self.dut.reset), 1)
			self.assertEqual((yield self.dut.sync), 1)
			self.assertEqual((yield self.dut.begin), 0)
			# Check the reset signal is properly generated
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.sync), 1)
			self.assertEqual((yield self.dut.begin), 0)
			# Wait till the first sync fail
			yield from self.step(83)
			self.assertEqual((yield self.dut.reset), 0)
			# Check we end back in the IDLE state as a result
			yield
			self.assertEqual((yield self.dut.reset), 1)

		@ToriiTestCase.comb_domain
		def domainSPDIF(self : TimingTestCase):
			yield spdif.eq(0)
			# Wait at least 10 half bit times
			for _ in range(10):
				yield from self.bitTime()
			# Pretend the link just got plugged in and the target just sent bit pattern 0110
			# before then starting the sync cycle
			yield from self.bmc(data = 0)
			yield from self.bmc(data = 1)
			yield from self.bmc(data = 1)
			yield from self.bmc(data = 0)
			# Now encode preamble Y to validate the timer logic

		domainSync(self)
		domainSPDIF(self)
