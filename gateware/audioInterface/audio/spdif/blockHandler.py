from torii import Elaboratable, Module, Signal, Cat, DomainRenamer
from torii.lib.fifo import SyncFIFO
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

	def elaborate(self, platform : Platform) -> Module:
		m = Module()

		channel = self.channel
		dataIn = self.dataIn
		dataAvailable = self.dataAvailable
		blockBeginning = self.blockBeginning
		blockComplete = self.blockComplete
		dropBlock = self.dropBlock

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
		bitDepth = Signal(range(24))
		sampleRate = Signal(range(192000))
		channelAType = Signal(Channel)

		channelA : SyncFIFO = DomainRenamer({'sync': 'usb'})(SyncFIFO(width = 24, depth = 192, fwft = False))
		channelB : SyncFIFO = DomainRenamer({'sync': 'usb'})(SyncFIFO(width = 24, depth = 192, fwft = False))

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
						with m.Case('1101'):
							m.d.usb += bitDepth.eq(24)
						# 20-bit words, minus 4 bits
						with m.Case('0100'):
							m.d.usb += bitDepth.eq(16)
						# Not one of these two? Don't support it so signal invalid
						with m.Default():
							m.d.comb += bitDepthInvalid.eq(1)

					# Decode the sample rate
					with m.Switch(controlBits[24:28]):
						with m.Case('0000'):
							m.d.usb += sampleRate.eq(44100)
						with m.Case('0100'):
							m.d.usb += sampleRate.eq(48000)
						with m.Case('0101'):
							m.d.usb += sampleRate.eq(96000)
						with m.Case('0111'):
							m.d.usb += sampleRate.eq(192000)
						with m.Case('1100'):
							m.d.usb += sampleRate.eq(32000)
						# If it's not one of the valid sample rates, signal it's invalid
						with m.Default():
							m.d.comb += sampleRateInvalid.eq(1)

					# Decode what channel A carries (left or right channel audio)
					with m.Switch(controlBits[20:24]):
						with m.Case('1000'):
							m.d.usb += channelAType.eq(Channel.left)
						with m.Case('0100'):
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
					m.next = 'DROP-DATA'

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

		return m
