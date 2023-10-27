from torii import Elaboratable, Module, Signal, Cat, DomainRenamer
from torii.lib.fifo import SyncFIFOBuffered
from torii.build import Platform

from ..i2s import Channel

class BlockHandler(Elaboratable):
	'''
	This handles S/PDIF blocks, validating their metadata, updating the playback engine
	with appropriate sample rate and bit depth information.

	When signaled by the timing block that the block is complete, it then moves the data from
	the internal FIFO into the playback FIFO with suitable sample interleaving.

	If the handler gets an incomplete block it will **discard** the data for the block.
	We try to do our best to ensure any previous complete block has been flushed out to the
	playback FIFO however so that complete audio chunks get processed properly.
	'''

	def __init__(self):
		self.channel = Signal()
		self.dataIn = Signal(28)
		self.dataAvailable = Signal()
		self.blockBeginning = Signal()
		self.blockComplete = Signal()
		self.dropBlock = Signal()

		self.blockValid = Signal()
		self.droppingData = Signal()
		self.dataOut = Signal(24)
		self.dataValid = Signal()
		self.bitDepth = Signal(range(24))
		self.sampleRate = Signal(range(192000))

	def elaborate(self, platform : Platform) -> Module:
		m = Module()

		channel = self.channel
		dataIn = self.dataIn
		dataAvailable = self.dataAvailable
		blockBeginning = self.blockBeginning
		blockComplete = self.blockComplete
		dropBlock = self.dropBlock

		blockValid = self.blockValid
		droppingData = self.droppingData
		dataOut = self.dataOut
		dataValid = self.dataValid

		parityOk = Signal()
		blockError = Signal()
		samplesA = Signal(range(192))
		samplesB = Signal(range(192))
		controlBits = Signal(192)

		bitDepthInvalid = Signal()
		sampleRateInvalid = Signal()
		channelTypeInvalid = Signal()

		dropData = Signal()
		transferData = Signal()
		discardSamplesA = Signal(range(192))
		discardSamplesB = Signal(range(192))
		transferSamples = Signal(range(192))
		transferChannel = Signal()
		sample = Signal(24)
		bitDepth = Signal(range(24))
		sampleRate = Signal(range(192000))
		channelAType = Signal(Channel)

		channelA : SyncFIFOBuffered = DomainRenamer({'sync': 'usb'})(SyncFIFOBuffered(width = 24, depth = 192))
		channelB : SyncFIFOBuffered = DomainRenamer({'sync': 'usb'})(SyncFIFOBuffered(width = 24, depth = 192))

		m.submodules.channelA = channelA
		m.submodules.channelB = channelB

		# Continually compute the even parity for the incomming data
		m.d.comb += [
			parityOk.eq(~dataIn[0:28].xor()),
			channelA.w_data.eq(dataIn[0:24]),
			channelA.w_en.eq(0),
			channelA.r_en.eq(0),
			channelB.w_data.eq(dataIn[0:24]),
			channelB.w_en.eq(0),
			channelB.r_en.eq(0),
			dropData.eq(0),
			transferData.eq(0),
			bitDepthInvalid.eq(0),
			sampleRateInvalid.eq(0),
			blockValid.eq(transferData),
			droppingData.eq(0),
			dataValid.eq(0),
		]

		with m.FSM(domain = 'usb', name = 'blockFSM'):
			# Wait for a S/PDIF block to begin
			with m.State('WAIT-BLOCK'):
				with m.If(blockBeginning):
					m.d.usb += [
						blockError.eq(0),
						samplesA.eq(0),
						samplesB.eq(0),
					]
					m.next = 'COLLECT-DATA'

			# Buffer up each new sample as it comes in
			with m.State('COLLECT-DATA'):
				# When a new chunk of data is made available
				with m.If(dataAvailable):
					# Shift the control bit into the control bits set when on channel 0
					with m.If(~channel):
						m.d.usb += controlBits.eq(Cat(controlBits.shift_right(1), dataIn[26]))

					# And stuff the sample into the channel's sample FIFO if valid
					with m.If((~dataIn[24]) & parityOk):
						with m.If(~channel):
							m.d.comb += channelA.w_en.eq(1)
							m.d.usb += samplesA.eq(samplesA + 1)
						with m.Else():
							m.d.comb += channelB.w_en.eq(1)
							m.d.usb += samplesB.eq(samplesB + 1)
					# If it's not valid, set a block error
					with m.Else():
						m.d.usb += blockError.eq(1)
				# If the timing logic indicates we need to drop the block, go into an abort state
				with m.Elif(dropBlock):
					m.next = 'ABORT'
				# Otherwise, when it tells us that the block is now complete, go to validating the control data
				with m.Elif(blockComplete):
					# Unless we had a block error, in which case, go to the abort state
					with m.If(blockError):
						m.next = 'ABORT'
					with m.Else():
						m.next = 'VALIDATE-CONTROL'

			# Check that we have a S/PDIF control frame and move settings about as needed
			with m.State('VALIDATE-CONTROL'):
				# If the first control bit indicates this is an AES3 frame, immediately go to discarding the data.
				# Likewise if this is compressed or 4-channel PCM data.
				with m.If(controlBits[0] | controlBits[1] | controlBits[3]):
					m.next = 'ABORT'
				# Otherwise copy the sample rate and other information out
				with m.Else():
					# Decode the sample bit depth
					with m.Switch(controlBits[32:36]):
						# 24-bit words, full word length
						with m.Case('1011'):
							m.d.usb += bitDepth.eq(24)
						# 20-bit words, minus 4 bits
						with m.Case('0010'):
							m.d.usb += bitDepth.eq(16)
						# Not one of these two? Don't support it so signal invalid
						with m.Default():
							m.d.comb += bitDepthInvalid.eq(1)

					# Decode the sample rate
					with m.Switch(controlBits[24:28]):
						with m.Case('0000'):
							m.d.usb += sampleRate.eq(44100)
						with m.Case('0010'):
							m.d.usb += sampleRate.eq(48000)
						with m.Case('1010'):
							m.d.usb += sampleRate.eq(96000)
						with m.Case('1110'):
							m.d.usb += sampleRate.eq(192000)
						with m.Case('0011'):
							m.d.usb += sampleRate.eq(32000)
						# If it's not one of the valid sample rates, signal it's invalid
						with m.Default():
							m.d.comb += sampleRateInvalid.eq(1)

					# Decode what channel A carries (left or right channel audio)
					with m.Switch(controlBits[20:24]):
						with m.Case('0001'):
							m.d.usb += channelAType.eq(Channel.left)
						with m.Case('0010'):
							m.d.usb += channelAType.eq(Channel.right)
						# If it's not one of left or right, signal it's invalid
						with m.Default():
							m.d.comb += channelTypeInvalid.eq(1)

					# If any of the channel information is bad, abort
					with m.If(bitDepthInvalid | sampleRateInvalid | channelTypeInvalid):
						m.next = 'ABORT'
					# If there's a mismatch on the number of samples per channel, abort
					with m.Elif(samplesA != samplesB):
						m.next = 'ABORT'
					# If all is well, continue to transfer
					with m.Else():
						m.next = 'START-TRANSFER'

			# Validation succeeded, so indicate to the transfer FSM that it can move the data
			# from our FIFOs into the I²S block's
			with m.State('START-TRANSFER'):
				m.d.comb += transferData.eq(1)
				m.next = 'WAIT-BLOCK'

			# Buffering of the block has been aborted, either by a parity error or by an abort
			# from the timing system. Tell the transfer FSM what to do and go back to waiting
			with m.State('ABORT'):
				m.d.comb += dropData.eq(1)
				m.next = 'WAIT-BLOCK'

		with m.FSM(domain = 'usb', name = 'transferFSM'):
			with m.State('WAIT-DATA'):
				with m.If(dropData):
					m.d.usb += [
						discardSamplesA.eq(samplesA),
						discardSamplesB.eq(samplesB),
					]
					m.d.comb += droppingData.eq(1)
					m.next = 'DROP-DATA'
				with m.Elif(transferData):
					m.d.usb += [
						transferSamples.eq(samplesA),
						# This sets which channel we start pulling data from
						# 0 for channel A (A is left) 1 for channel B (A is right)
						transferChannel.eq(channelAType == Channel.right),
						self.bitDepth.eq(bitDepth),
						self.sampleRate.eq(sampleRate),
					]
					m.next = 'XFER-DATA-L'

			with m.State('DROP-DATA'):
				with m.If(discardSamplesA):
					m.d.comb += channelA.r_en.eq(1)
					# Compute `discardSamplesA - 1` by manually doing subtract-with-borrow, which turns `- 1`
					# into `+ ((2 ** width) - 1)` - subtraction is expensive on the iCE40, due to architecture.
					m.d.usb += discardSamplesA.eq(discardSamplesA + ((2 ** discardSamplesA.width) - 1))

				with m.If(discardSamplesB):
					m.d.comb += channelB.r_en.eq(1)
					# Compute `discardSamplesB - 1` by manually doing subtract-with-borrow, which turns `- 1`
					# into `+ ((2 ** width) - 1)` - subtraction is expensive on the iCE40, due to architecture.
					m.d.usb += discardSamplesB.eq(discardSamplesB + ((2 ** discardSamplesB.width) - 1))

				with m.If((discardSamplesA == 0) & (discardSamplesB == 0)):
					m.next = 'WAIT-DATA'

			with m.State('XFER-DATA-L'):
				# Should we pull data from buffer B first? If true, we should
				with m.If(transferChannel):
					m.d.comb += channelB.r_en.eq(1)
				with m.Else():
					m.d.comb += channelA.r_en.eq(1)
				# Flip the channel used ready for the right data, mark that we're consuming this sample
				# (computed as above with manual subtract-with-borrow for speed
				m.d.usb += [
					transferChannel.eq(~transferChannel),
					transferSamples.eq(transferSamples + ((2 ** transferSamples.width) - 1)),
				]
				m.d.comb += dataValid.eq(1)
				m.next = 'XFER-DATA-R'

			with m.State('XFER-DATA-R'):
				# Should we pull data from buffer B first? If true, we should
				with m.If(transferChannel):
					m.d.comb += channelB.r_en.eq(1)
				with m.Else():
					m.d.comb += channelA.r_en.eq(1)
				# Flip the channel used back and check if we've consumed all the samples to transfer
				m.d.usb += transferChannel.eq(~transferChannel)
				m.d.comb += dataValid.eq(1)
				# If we've still got samples, go back to handle the next left channel sample
				with m.If(transferSamples):
					m.next = 'XFER-DATA-L'
				# Otherwise if we've consumed them all, go back to idle to await more data
				with m.Else():
					m.next = 'WAIT-DATA'

		# Connect an approriate channel through to the data output based on the transfer channel value
		with m.If(transferChannel):
			m.d.comb += sample.eq(channelB.r_data)
		with m.Else():
			m.d.comb += sample.eq(channelA.r_data)

		# If we're outputting 16-bit data, undo the left alignment S/PDIF does
		with m.If(bitDepth == 16):
			m.d.comb += dataOut.eq(sample.shift_right(8))
		# Otherwise it's 24-bit data, so pass it straight through unchanged
		with m.Else():
			m.d.comb += dataOut.eq(sample)

		return m
