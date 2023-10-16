# SPDX-License-Identifier: BSD-3-Clause

from typing import Dict, List, Union, Tuple
from sys import stdout
from torii.sim import Simulator

__all__ = (
	'simCase',
	'runSims',
)

def log(str, end = '\n', file = stdout):
	print(f'\x1B[35m[*]\x1B[0m {str}', end = end, file = file)

def inf(str, end = '\n', file = stdout):
	print(f'\x1B[36m[~]\x1B[0m {str}', end = end, file = file)

def _collectSims(*, pkg) -> List[Dict[str, Union[str, Tuple[Simulator, str]]]]:
	from pkgutil   import walk_packages
	from importlib import import_module
	from inspect   import getmembers
	from os        import path

	def _casePredicate(member):
		return (
			isinstance(member, tuple) and
			len(member) == 2 and
			isinstance(member[0], Simulator) and
			isinstance(member[1], str)
		)

	sims = []

	if not path.exists(pkg):
		raise RuntimeError(f'The package {pkg} does not exist, unable to attempt to import test cases')

	for _, name, is_pkg in walk_packages(path = (pkg,), prefix = f'{pkg.replace("/", ".")}.'):
		pkg_import = import_module(name)
		cases_variables = getmembers(pkg_import, _casePredicate)
		if len(cases_variables) != 0:
			sims.append({
				'name' : name,
				'cases': [case for _, case in cases_variables]
			})
	return sims

def simCase(*, domains, dut, platform = None, engine = 'pysim'):
	def _regSim(func):
		from torii.hdl.ir import Fragment

		sim = Simulator(
			Fragment.get(dut, platform = platform),
			engine = engine
		)

		for dom, clk in domains:
			sim.add_clock(1 / clk, domain = dom)

		for case, dom in func(sim, dut):
			sim.add_sync_process(case, domain = dom)

		return (sim, getattr(func, '__name__'))
	return _regSim

def runSims(*, pkg, result_dir, skip = []):
	from os import path, mkdir, makedirs

	if not path.exists(result_dir):
		mkdir(result_dir)

	for sim in _collectSims(pkg = pkg):
		log(f'Running simulation {sim["name"]}...')

		out_dir = path.join(result_dir, sim['name'].replace('.', '/'))
		if not path.exists(out_dir):
			makedirs(out_dir, exist_ok = True)

		for case, name in sim['cases']:
			inf(f' => Running {name}')

			with case.write_vcd(path.join(out_dir, f'{name}.vcd')):
				case.reset()
				case.run()
