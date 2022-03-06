from amaranth import Elaboratable, Module, Signal, Array, DomainRenamer
from luna.gateware.usb.usb2.request import USBOutStreamInterface

__all__ = (
	'StreamDeserializer',
)

class StreamDeserializer(Elaboratable):
	""" Gateware that deserializes a short Array output from a stream.

	I/O port:
		I: start        -- Strobe that indicates when reading the stream should be started.
		O: done         -- Strobe that pulses high when we finish reception.

		O: data         -- The data stream receieved. Length is set by the dataLength initializer argument.
		I: maxLength[] -- The maximum length to be received. Defaults to the length of the stream.
		                   Only present if the `maxLengthWidth` parameter is provided on creation.

		*: stream       -- The stream being consumed.

	"""

	def __init__(self, dataLength, streamType = USBOutStreamInterface, domain = 'sync', dataWidth = 8, maxLengthWidth = None):
		"""
		Parameters:
			dataLength      -- The length of the data to be received.
			domain          -- The clock domain this deserializer should belong to. Defaults to 'sync'.
			dataWidth       -- The width of the data chunks
			streamType      -- The stream we'll be consuming. Must be a subclass of USBOutStreamInterface
			maxLengthWidth  -- If provided, a `maxLength` signal will be present that can limit the total length
			                   consumed from the stream.
		"""

		self.domain = domain
		self.dataWidth = dataWidth
		self.dataLength = dataLength

		#
		# I/O port
		#
		self.start = Signal()
		self.done = Signal()

		self.data = Array(Signal(dataWidth, name = f'datum_{i}') for i in range(dataLength))
		self.stream = streamType(payload_width = dataWidth)

		# If we have a maximium length width, provide maxLength as a signal, otherwise it's a constant
		if maxLengthWidth:
			self.maxLength = Signal(maxLengthWidth)
		else:
			self.maxLength = self.dataLength

	def elaborate(self, platform):
		m = Module()

		# Register for where we've written to in the output data
		positionInData = Signal(range(self.dataLength))
		# Track whether we've more work to do to complete the read
		shouldContinue = (
			(positionInData < (self.dataLength - 1)) &
			(positionInData < (self.maxLength - 1))
		)

		with m.FSM(domain = self.domain):
			# IDLE -- we're not actively receiving
			with m.State('IDLE'):
				# Keep ourselves at the beginning of the output data and don't count up
				m.d.sync += positionInData.eq(0)
				# Once the user requests we start, begin consuming the data
				with m.If(self.start & (self.maxLength > 0)):
					m.next = 'STREAMING'
			# STREAMING -- we're actively consuming data
			with m.State('STREAMING'):
				# If the current data byte becomes valid, store it and move to the next
				with m.If(self.stream.valid & self.stream.next):
					m.d.sync += self.data[positionInData].eq(self.stream.payload)

					# Update the counter if we need to continue
					with m.If(shouldContinue):
						m.d.sync += positionInData.eq(positionInData + 1)
					# Otherwise go back to idle
					with m.Else():
						m.next = 'DONE'
			# DONE -- report our completion then go to idle
			with m.State('DONE'):
				m.d.comb += self.done.eq(1)
				m.next = 'IDLE'

		# Convert our sync domain to the domain requested by the user, if necessary
		if self.domain != 'sync':
			m = DomainRenamer({'sync': self.domain})(m)
		return m
