from torii import Elaboratable, Module, Signal, Cat
from torii.build import Platform

class BMCDecoder(Elaboratable):
	'''
	This implements Biphase-Mark Coding (BMC, aka Differential Manchester) decoding.
	It decodes and collates 28 bits from the input and pulses dataAvailable when complete,
	resetting state ready for the next 28 bits.
	The reset signal cleans internal state and puts things back into the initial state.
	'''

	def __init__(self):
		self.reset = Signal()
		self.dataIn = Signal()
		self.bitClock = Signal()

		self.dataOut = Signal(28)
		self.dataAvailable = Signal()

	def elaborate(self, platform : Platform) -> Module:
		m = Module()

		reset = self.reset
		dataIn = self.dataIn
		bitClock = self.bitClock

		dataOut = self.dataOut
		dataAvailable = self.dataAvailable

		firstHalf = Signal()
		counter = Signal(range(28))
		bits = Signal(28)

		with m.FSM(domain = 'usb'):
			# Wait for a pulse on bitClock signaling the start of a sequence
			with m.State('BEGIN'):
				# Continually reset the bit counter and data available state
				m.d.usb += [
					counter.eq(0),
					dataAvailable.eq(0),
				]
				# Once we've got that clock pulse, grab the input data state and store it
				# then switch to looking for the end of the bit
				with m.If(bitClock):
					m.d.usb += firstHalf.eq(dataIn)
					m.next = 'BIT-END'

			# Wait for the end (second half) of a bit so we can determine if it's 0 or 1
			with m.State('BIT-END'):
				# When we get the bit half's clock pulse
				with m.If(bitClock):
					# Increment the bit counter, and store if the state flipped (1), or didn't (0) as the new MSB
					# of the captured bits, shifting the rest down
					m.d.usb += [
						counter.eq(counter + 1),
						bits.eq(Cat(bits.shift_right(1), firstHalf != dataIn))
					]
					# If this is not the last bit, go to wait for the next in the sequence
					with m.If(counter != 27):
						m.next = 'BIT-BEGIN'
					# Otherwise go the completion state
					with m.Else():
						m.next = 'END'
				# If we get a reset while waiting, act on it
				with m.Elif(reset):
					m.next = 'BEGIN'

			# Wait for the beginning (first half) of a bit
			with m.State('BIT-BEGIN'):
				# When we get the bit half's clock pulse
				with m.If(bitClock):
					# Store the input data state, then switch to looking for the end of the bit
					m.d.usb += firstHalf.eq(dataIn)
					m.next = 'BIT-END'
				# If we get a reset while waiting, act on it
				with m.Elif(reset):
					m.next = 'BEGIN'

			# Handle closing steps for a sequence and reset state ready for the next
			with m.State('END'):
				# With all 28 bits in a sequence captured, make the data available from the shift register
				# and pulse the available line to indicate there's data now
				m.d.usb += [
					dataOut.eq(bits),
					dataAvailable.eq(1),
				]
				m.next = 'BEGIN'

		return m
