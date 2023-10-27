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

	def sample16Bit(self, sample : int):
		# Convert the sample to 24-bit by padding to the right with 0's
		data = sample << 8
		# For each of the 24 bits, emit the Biphase Mark Coded version of the bit
		for bit in range(24):
			yield from self.bmc(data = (data >> bit) & 1)
		# Now emit the 4 status bits - V = 1 as this is a valid audio sample
		yield from self.bmc(data = 1)
		# U = 0 as we don't care about the user data so fill this 192 bit channel with 0's
		yield from self.bmc(data = 0)
		# C = 0 as we aren't filling the channel status data at this point, so let it be 0's
		yield from self.bmc(data = 0)
		# P = ~Cat(data, 1, 0, 0).xor() as the parity value is for even parity, xor calculates odd.
		parityData = (data << 3) | 0b100
		parity = 0
		for bit in range(27):
			parity ^= (parityData >> bit) & 1
		yield from self.bmc(data = 1 - parity)

	@ToriiTestCase.simulation
	def testSyncZ(self):
		spdif = self.dut.spdifIn

		@ToriiTestCase.sync_domain(domain = 'usb')
		def domainUSB(self : TimingTestCase):
			# Validate preconditions
			self.assertEqual((yield self.dut.reset), 1)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.blockBegin), 0)
			# Wait until the first step from the S/PDIF input registers
			yield from self.step(213)
			self.assertEqual((yield self.dut.reset), 1)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.blockBegin), 0)
			# Check the reset signal is properly generated
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.blockBegin), 0)
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
			self.assertEqual((yield self.dut.blockBegin), 0)
			# Check that we synchronised to it
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.blockBegin), 1)
			# Then check that the frame block begin signal goes low
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.blockBegin), 0)
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
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)

			# -- Frame 0
			# Fast forward to the end of the 'Z' sync sequence
			yield from self.step(191)
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Check that we synchronised to it
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.blockBegin), 1)
			self.assertEqual((yield self.dut.frameBegin), 1)
			# We don't care about the channel or bit clock signals here, so instead lets
			# fast forward onto the next sync sequence ('Y') and check that works
			yield from self.step(1189)
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Check that we correctly detected it
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Fast forward to the end of the 'Y' sync sequence
			yield from self.step(168)
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Check that we synchronised to it
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)

			# -- Frame 1
			# We don't care about the channel or bit clock signals here, so instead lets
			# fast forward onto the next sync sequence ('X') and check that works
			yield from self.step(1188)
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Check that we correctly detected it
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Fast forward to the end of the 'Y' sync sequence
			yield from self.step(169)
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Check that we synchronised to it
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 1)
			# We don't care about the channel or bit clock signals here, so instead lets
			# fast forward onto the next sync sequence ('Y') and check that works
			yield from self.step(1188)
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Check that we correctly detected it
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Fast forward to the end of the 'Y' sync sequence
			yield from self.step(168)
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 1)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)
			# Check that we synchronised to it
			yield
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.syncing), 0)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)

			# Asset through the rest of the frames in the block
			for _ in range(190):
				yield from self.wait_until_high(self.dut.syncing, timeout = 1250)
				self.assertEqual((yield self.dut.reset), 0)
				self.assertEqual((yield self.dut.blockBegin), 0)
				self.assertEqual((yield self.dut.frameBegin), 0)
				yield from self.wait_until_low(self.dut.syncing, timeout = 250)
				self.assertEqual((yield self.dut.reset), 0)
				self.assertEqual((yield self.dut.blockBegin), 0)
				self.assertEqual((yield self.dut.frameBegin), 1)
				yield from self.wait_until_high(self.dut.syncing, timeout = 1250)
				self.assertEqual((yield self.dut.reset), 0)
				self.assertEqual((yield self.dut.blockBegin), 0)
				self.assertEqual((yield self.dut.frameBegin), 0)
				yield from self.wait_until_low(self.dut.syncing, timeout = 250)
				self.assertEqual((yield self.dut.reset), 0)
				self.assertEqual((yield self.dut.blockBegin), 0)
				self.assertEqual((yield self.dut.frameBegin), 0)

			# -- Frame 192, channel B
			# Check the bit clock is working
			self.assertEqual((yield self.dut.bitClock), 1)
			yield
			self.assertEqual((yield self.dut.bitClock), 0)
			yield from self.wait_until_high(self.dut.bitClock, timeout = 25)
			yield
			self.assertEqual((yield self.dut.bitClock), 0)
			yield from self.wait_until_high(self.dut.bitClock, timeout = 20)
			yield
			self.assertEqual((yield self.dut.bitClock), 0)
			yield from self.wait_until_high(self.dut.bitClock, timeout = 25)
			yield
			self.assertEqual((yield self.dut.bitClock), 0)
			yield from self.wait_until_high(self.dut.bitClock, timeout = 20)
			yield
			self.assertEqual((yield self.dut.bitClock), 0)

			# After the first couple of cycles of the bit clock, fast forward to 'Z' sync begin
			yield from self.wait_until_high(self.dut.syncing, timeout = 1150)
			self.assertEqual((yield self.dut.reset), 0)
			self.assertEqual((yield self.dut.blockBegin), 0)
			self.assertEqual((yield self.dut.frameBegin), 0)

			# Wait for sync to time out
			yield from self.wait_until_high(self.dut.reset, timeout = 600)
			self.assertEqual((yield self.dut.syncing), 1)

		@ToriiTestCase.comb_domain
		def domainSPDIF(self : TimingTestCase):
			yield spdif.eq(1)
			yield from self.bitTime()
			# Start by encoding preamble Z to begin the frame
			yield from self.syncZ()
			# Now start sending samples
			for sample in range(384):
				yield from self.sample16Bit(sample)
				# Having encoded this sample, determine what the next preamble needs to be
				if (sample & 1) == 0:
					yield from self.syncY()
				elif sample != 383:
					yield from self.syncX()
			# Having sent a full frame's worth of samples, go idle to check sync timesout properly
			for _ in range(28):
				yield from self.bitTime()

		domainUSB(self)
		domainSPDIF(self)
