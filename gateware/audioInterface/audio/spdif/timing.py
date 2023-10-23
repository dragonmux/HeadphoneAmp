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

		self.reset = Signal(reset = 1)
		self.sync = Signal(reset = 1)
		self.begin = Signal()
		self.channel = Signal()
		self.bitClock = Signal()

	def elaborate(self, platform : Platform) -> Module:
		m = Module()

		dataInPrev = Signal()
		dataInCurr = Signal()

		# The ranges 570 and 190 have been chosen as upper limits based on the minimum sampling frequency
		# being 32kHz, giving rise to `60MHz / 32kHz` = 187.5. The actual bit timing for 32kHz audio would
		# have to be higher than this to accomodate protocol overheads (there are 32 bit periods per sample
		# required), so this should be more than enough for any valid data stream.
		longTimer = Signal(range(570))
		shortTimer = Signal(range(190))
		bitTime = Signal(range(190))
		longTime = Signal(range(570))

		with m.FSM(domain = 'usb') as syncFSM:
			m.d.comb += [
				self.reset.eq(syncFSM.ongoing('IDLE')),
			]

			# In this state we are only looking for a transition on spdifIn (look for the channel to become active).
			with m.State('IDLE'):
				m.d.usb += longTimer.eq(0)
				with m.If(dataInPrev != dataInCurr):
					m.next = 'SYNC-Z-BEGIN'

			# Start looking for a Z preamble
			with m.State('SYNC-Z-BEGIN'):
				m.d.usb += longTimer.eq(longTimer + 1)
				# If we've not had a transition in too long and the timer is about to expire, reset
				# back to the IDLE state as the link should now be treated as 'idle'
				with m.If(longTimer == 569):
					m.next = 'IDLE'
				with m.Elif(dataInPrev != dataInCurr):
					m.d.usb += shortTimer.eq(0)
					m.next = 'SYNC-Z-SHORT1'

			# Look for the first short bit period of the sync sequence.
			with m.State('SYNC-Z-SHORT1'):
				# If we've not had a transition in too long and we've exceeded the long bit time, we
				# might have captured too short of a long bit time and instead have grabbed a BMC bit
				# so copy the timer value back to the long timer and switch back
				with m.If((shortTimer + 1) == longTimer):
					# Check if a transition is happening, if it's not, assume longer bit
					with m.If(dataInPrev == dataInCurr):
						m.d.usb += longTimer.eq(shortTimer + 1)
					# If it is, we just got two same length bits, we're in the middle of some BMC stuff.
					with m.Else():
						m.d.usb += longTimer.eq(0)
					m.next = 'SYNC-Z-BEGIN'
				# Otherwise if the timer is about to expire, abort back to idle
				with m.Elif(shortTimer == 189):
					m.next = 'IDLE'
				# Hopefully we just got a short bit time, so capture it, reset the timer and check for the second
				with m.Elif(dataInPrev != dataInCurr):
					# Well, having first checked that the long time period is ~3x this one
					checkTime = shortTimer * 3
					# If it falls long of the right range, this was a different sync sequence (Y or X)
					with m.If(checkTime > (longTimer + 7)):
						m.next = 'IDLE'
					# If it falls short of the right range, this was BMC data (01 sequence, specifically)
					with m.Elif(checkTime < (longTimer - 7)):
						m.d.usb += longTimer.eq(0)
						m.next = 'SYNC-Z-BEGIN'
					with m.Else():
						m.d.usb += [
							bitTime.eq(shortTimer),
							shortTimer.eq(0),
						]
						m.next = 'SYNC-Z-SHORT2'
				with m.Else():
					m.d.usb += shortTimer.eq(shortTimer + 1)

			with m.State('SYNC-Z-SHORT2'):
				m.d.usb += shortTimer.eq(shortTimer + 1)
				# If we exceed the previous bit time by more than a couple of counts, more than likely
				# this was not a Z sync sequence. Abort back to idle.
				with m.If((shortTimer == (bitTime + 3)) & (dataInPrev == dataInCurr)):
					m.next = 'IDLE'
				# If the timer is about to expire, abort back to idle.
				with m.Elif(shortTimer == 189):
					m.next = 'IDLE'
				# We got something that should be another short bit, so let's check the timing is with
				# a couple of counts of the expected bit time
				with m.Elif(dataInPrev != dataInCurr):
					with m.If(shortTimer > (bitTime - 3)):
						m.d.usb += [
							longTime.eq(longTimer),
							longTimer.eq(0),
							bitTime.eq((bitTime + shortTimer)[1:])
						]
						m.next = 'SYNC-Z-FINAL'
					# If it falls outside range, chances are we got something else like a BMC bit or something
					# not right, so go back to trying to capture a Z sync sequence
					with m.Else():
						m.d.usb += longTimer.eq(0)
						m.next = 'SYNC-Z-BEGIN'

			with m.State('SYNC-Z-FINAL'):
				m.d.usb += longTimer.eq(longTimer + 1)
				# If we've caught an edge transition, validate the timer is ~= longTime and go to sync'd state
				with m.If(dataInPrev != dataInCurr):
					# Validate that the bit time is aproximately the same as the one in longTime
					with m.If((longTimer > (longTime - 3)) & (longTimer < (longTime + 3))):
						m.next = 'SUBFRAME'
					# Otherwise it's fallen outside of the allowed range, so abort back to idle
					with m.Else():
						m.next = 'IDLE'
				# If the timer is about to expire, abort back to idle.
				with m.Elif(longTimer == 569):
					m.next = 'IDLE'

			with m.State('SUBFRAME'):
				pass

		# Synchronise the input S/PDIF signal and time delay it to allow us to detect edges
		m.d.usb += [
			dataInCurr.eq(self.spdifIn),
			dataInPrev.eq(dataInCurr),
		]
		return m
