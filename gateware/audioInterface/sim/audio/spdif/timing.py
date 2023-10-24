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
		spdif = self.dut.spdifIn
		value = yield spdif
		# Create the first bit inversion to start the bit, and step to the second bit time
		yield spdif.eq(1 - value)
		yield from self.bitTime()
		# Encode the transition that defines this as a 0 or 1
		if data == 1:
			yield spdif.eq(value)
		yield from self.bitTime()

	def syncX(self):
		# Get the current state of the signal
		spdif = self.dut.spdifIn
		value = yield spdif
		# Generate the first transition for the sync sequence, wait 3 time units
		yield spdif.eq(1 - value)
		yield from self.bitTime()
		yield from self.bitTime()
		yield from self.bitTime()
		# Generate the second transition and wait another 3 time units
		yield spdif.eq(value)
		yield from self.bitTime()
		yield from self.bitTime()
		yield from self.bitTime()
		# Generate the third transition and wait 1 time unit
		yield spdif.eq(1 - value)
		yield from self.bitTime()
		# Generate the final transition and wait 1 last time unit
		yield spdif.eq(value)
		yield from self.bitTime()

	def syncY(self):
		# Get the current state of the signal
		spdif = self.dut.spdifIn
		value = yield spdif
		# Generate the first transition for the sync sequence, wait 3 time units
		yield spdif.eq(1 - value)
		yield from self.bitTime()
		yield from self.bitTime()
		yield from self.bitTime()
		# Generate the second transition and wait another 2 time units
		yield spdif.eq(value)
		yield from self.bitTime()
		yield from self.bitTime()
		# Generate the third transition, waiting 1 time unit
		yield spdif.eq(1 - value)
		yield from self.bitTime()
		# Generate the final transition, waiting 2 more time units
		yield spdif.eq(value)
		yield from self.bitTime()
		yield from self.bitTime()

	def syncZ(self):
		# Get the current state of the signal
		spdif = self.dut.spdifIn
		value = yield spdif
		# Generate the first transition for the sync sequence, wait 3 time units
		yield spdif.eq(1 - value)
		yield from self.bitTime()
		yield from self.bitTime()
		yield from self.bitTime()
		# Generate the second transition and wait 1 time unit
		yield spdif.eq(value)
		yield from self.bitTime()
		# Generate the third transition, waiting 1 time unit again
		yield spdif.eq(1 - value)
		yield from self.bitTime()
		# Generate the final transition, waiting 3 more time units
		yield spdif.eq(value)
		yield from self.bitTime()
		yield from self.bitTime()
		yield from self.bitTime()

	@ToriiTestCase.simulation
	def testSyncZ(self):
		spdif = self.dut.spdifIn

		@ToriiTestCase.sync_domain(domain = 'usb')
		def domainUSB(self : TimingTestCase):
			# Validate preconditions
			self.assertEqual((yield self.dut.reset), 1)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Wait until the first step from the S/PDIF input registers
			yield from self.step(213)
			self.assertEqual((yield self.dut.reset), 1)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Check the reset signal is properly generated
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Wait till the first sync fail
			yield from self.step(61)
			self.assertEqual((yield self.dut.reset), 0)
			# Check we end back in the IDLE state as a result
			yield
			self.assertEqual((yield self.dut.reset), 1)
			# Fast forward to the second (fail to sync on 'Y' sequence)
			yield from self.step(211)
			self.assertEqual((yield self.dut.reset), 0)
			# Check we end back in the IDLE state as a result
			yield
			self.assertEqual((yield self.dut.reset), 1)
			# Fast forward to the third (fail to sync on 01 bit sequence)
			yield from self.step(83)
			self.assertEqual((yield self.dut.reset), 0)
			# Check we end back in the IDLE state as a result
			yield
			self.assertEqual((yield self.dut.reset), 1)
			# Fast forward to the end of the 'Z' sync sequence
			yield from self.step(189)
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Check that we synchronised to it
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.frameBegin), 1)
			# Then check that the frame block begin signal goes low
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Fast forward to loosing sync again
			yield from self.step(126)
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
			yield from self.syncY()
			# Encode another bit (this time a 1-bit) just in case
			yield from self.bmc(data = 1)
			# Now encode preamble Z to validate we get a lock and sync
			yield from self.syncZ()
			# Encode a couple more bits (pattern 01) to check the lock is maintained
			yield from self.bmc(data = 0)
			yield from self.bmc(data = 1)
			# Finally, check that the logic times out after sufficient idle time as if the link just got unplugged
			for _ in range(4):
				yield from self.bitTime()

		domainUSB(self)
		domainSPDIF(self)

	@ToriiTestCase.simulation
	def testReceiveBlock(self):
		spdif = self.dut.spdifIn

		@ToriiTestCase.sync_domain(domain = 'usb')
		def domainUSB(self : TimingTestCase):
			# Validate preconditions
			self.assertEqual((yield self.dut.reset), 1)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Fast forward to the end of the 'Z' sync sequence
			yield from self.step(191)
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Check that we synchronised to it
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.frameBegin), 1)

		@ToriiTestCase.comb_domain
		def domainSPDIF(self : TimingTestCase):
			yield spdif.eq(1)
			yield from self.bitTime()
			# Start by encoding preamble Z to begin the frame
			yield from self.syncZ()
			# Now start sending samples
			for sample in range(384):
				#yield from self.sample24Bit(sample)
				# Having encoded this sample, determine what the next preamble needs to be
				if (sample & 1) == 0:
					yield from self.syncY()
				elif sample != 383:
					yield from self.syncX()
			# Having sent a full frame's worth of samples, go idle to check sync timesout properly
			for _ in range(4):
				yield from self.bitTime()

		domainUSB(self)
		domainSPDIF(self)
