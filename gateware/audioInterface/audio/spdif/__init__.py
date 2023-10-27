from torii import Elaboratable, Module, Signal
from torii.build import Platform

from .timing import Timing
from .biphaseDecode import BMCDecoder
from .blockHandler import BlockHandler

__all__ = (
	'SPDIF',
)

class SPDIF(Elaboratable):
	def __init__(self):
		self.available = Signal()
		self.sample = Signal(24)
		self.sampleValid = Signal()

	def elaborate(self, platform : Platform) -> Module:
		m = Module()
		# Grab the S/PDIF bus from the platform
		bus = platform.request('spdif', 0)

		# Instantiate all the modules that comprise this S/PDIF decoder
		m.submodules.timing = timing = Timing()
		m.submodules.bmcDecoder = bmcDecoder = BMCDecoder()
		m.submodules.blockHandler = blockHandler = BlockHandler()

		available = self.available
		sample = self.sample
		sampleValid = self.sampleValid

		# Wire them all up to create the completed decoder block
		m.d.comb += [
			# The incoming data signal goes into the timing block
			timing.spdifIn.eq(bus.data.i),

			# The outgoing reset data, and bitClock signals then go into the
			# Biphase Mark Code decoder so we can get out decoded data and
			# to go into the next block
			bmcDecoder.reset.eq(timing.reset),
			bmcDecoder.dataIn.eq(timing.data),
			bmcDecoder.bitClock.eq(timing.bitClock),

			# Finally, the remaining timing signals and the decoded data go
			# into the block handler where they're buffered and the completed
			# blocks are validated and queued to the I²S sample playback engine
			blockHandler.channel.eq(timing.channel),
			blockHandler.dataIn.eq(bmcDecoder.dataOut),
			blockHandler.dataAvailable.eq(bmcDecoder.dataAvailable),
			blockHandler.blockBeginning.eq(timing.blockBegin),
			blockHandler.blockComplete.eq(timing.blockEnd),
			blockHandler.dropBlock.eq(timing.reset),

			sampleValid.eq(blockHandler.dataValid),
			sample.eq(blockHandler.dataOut),
		]

		# If we see sync, block begin and then the block handler go valid, mark the source available
		# until such a time as the block handler indicates it had to drop data
		with m.FSM():
			with m.State('WAIT-SYNC'):
				with m.If(timing.syncing):
					m.next = 'WAIT-BLOCK'

			with m.State('WAIT-BLOCK'):
				with m.If(timing.blockBegin):
					m.next = 'WAIT-DATA'
				with m.Elif(timing.reset):
					m.next = 'WAIT-SYNC'

			with m.State('WAIT-DATA'):
				with m.If(blockHandler.blockValid):
					m.d.usb += available.eq(1)
					m.next = 'AVAILABLE'
				with m.Elif(blockHandler.droppingData):
					m.next = 'WAIT-SYNC'

			with m.State('AVAILABLE'):
				with m.If(blockHandler.droppingData):
					m.d.usb += available.eq(0)
					m.next = 'WAIT-SYNC'

		return m
