from torii import Elaboratable, Module, Signal
from torii.build import Platform

class Timing(Elaboratable):
	'''
	This implements S/PDIF clock recovery and synchronisation logic in the **USB**
	clock domain (60MHz) to guarantee we have a fast enough clock to actually do this.
	The process is acomplished via a series of timers and discarding biphase mark coded
	(BMC) data while looking for a synchronising preamble.

	Specifically, we start by looking for a 'Z' preamble, which starts with a transition,
	waits 3 half bit periods, has another transition, then another half bit period,
	transition, half bit period, transition, 3 more half bit periods and a final transition.
	It does not matter what the starting state is.

	Once we've found this block begin sync sequence, we lock onto that w/ the resulting
	half bit period timer value being used to generate clock pulses out to the rest of
	the logic. We also generate a begin bit when we find this sync pattern, and trigger
	any timing changes required in the I²S output engine.

	Finally, if we see no transition for more than a full bit period, we set a sync signal
	which inhibits decoding in the rest of the implementation, and we start looking for
	which pattern is being used - if we see the 'Y' or 'X' sequence, we set a signal accordingly.
	If we see no further transitions for more than another full bit period, we assume the user
	disconnected the input and re-enter the reset state, generating a full S/PDIF module reset
	to the rest of the hardware.

	We treat the 'Z' sequence the same as the 'X' sequence for generating the channel signal.
	sync sequence 'Z' is also known as sequence 'B', 'X' as 'M' and 'Y' as 'W'.
	'''

	def __init__(self):
		self.spdifIn = Signal()

	def elaborate(self, platform : Platform) -> Module:
		m = Module()
		#

		return m
