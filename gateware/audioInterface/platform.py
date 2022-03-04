from amaranth.vendor.lattice_ice40 import LatticeICE40Platform
from amaranth.build import Resource, Subsignal, Pins, Clock, Attrs

__all__ = (
	'AudioInterfacePlatform',
)

class AudioInterfacePlatform(LatticeICE40Platform):
	device = 'iCE40HX8K'
	package = 'BG121'
	toolchain = 'IceStorm'

	resources = [
		Resource(
			'ulpi', 0,
			Subsignal('clk', Pins('G1', dir = 'i'), Clock(60e6)),
			Subsignal('data', Pins('E1 E2 F1 F2 G2 H1 H2 J1', dir = 'io')),
			Subsignal('dir', Pins('D1', dir = 'i')),
			Subsignal('nxt', Pins('D2', dir = 'i')),
			Subsignal('stp', Pins('C2', dir = 'o')),
			Subsignal('rst', Pins('C1', dir = 'o')),
			Attrs(IO_STANDARD = 'SB_LVCMOS')
		),
	]

	connectors = []
