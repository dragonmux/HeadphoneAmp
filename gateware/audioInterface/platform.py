from amaranth.vendor.lattice_ice40 import LatticeICE40Platform
from amaranth.build import Resource, Subsignal, Pins, Clock, Attrs
from amaranth_boards.resources.interface import SPIResource, ULPIResource

__all__ = (
	'AudioInterfacePlatform',
)

class AudioInterfacePlatform(LatticeICE40Platform):
	device = 'iCE40HX8K'
	package = 'BG121'
	toolchain = 'IceStorm'

	resources = [
		Resource(
			'sys_clk', 0,
			Pins('B6', dir = 'i', assert_width = 1),
			Clock(36.864e6),
			Attrs(GLOBAL = True, IO_STANDARD = 'SB_LVCMOS')
		),

		SPIResource(
			'cfg_spi', 0,
			clk = 'F11',
			copi = 'F10',
			cipo = 'G11',
			cs_n = 'E11 A7',
			attrs = Attrs(IO_STANDARD = 'SB_LVCMOS')
		),

		ULPIResource(
			'ulpi', 0,
			clk = 'G1', clk_dir = 'i',
			data = 'E1 F2 F1 G2 H2 H1 J2 J1',
			dir = 'D1',
			nxt = 'E2',
			stp = 'D2',
			rst = 'C1', rst_invert = True,
			attrs = Attrs(IO_STANDARD = 'SB_LVCMOS')
		),

		Resource(
			'i2s', 0,
			Subsignal('clk', Pins('E10', dir = 'o', assert_width = 1)),
			# right/!left
			Subsignal('rnl', Pins('D10', dir = 'o', assert_width = 1)),
			Subsignal('data', Pins('D11', dir = 'o', assert_width = 1)),
			Attrs(IO_STANDARD = 'SB_LVCMOS')
		),

		Resource(
			'spdif', 0,
			Subsignal('data', Pins('A1', dir = 'i', assert_width = 1)),
			Attrs(IO_STANDARD = 'SB_LVCMOS')
		),
	]

	connectors = []

	def build(self, elaboratable, name = 'top', build_dir = 'build', do_build = True,
		program_opts = None, do_program = False, **kwargs):
		super().build(
			elaboratable, name, build_dir, do_build, program_opts, do_program,
			nextpnr_opts = ['--opt-timing', '--tmg-ripup', '--seed=1'], **kwargs
		)
