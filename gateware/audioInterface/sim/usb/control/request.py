from arachne.core.sim import sim_case
from amaranth.sim import Simulator, Settle
from luna.gateware.usb.usb2.request import SetupPacket
from usb_protocol.types import USBRequestType, USBRequestRecipient
from usb_protocol.types.descriptors.uac3 import AudioClassSpecificRequestCodes, AudioControlInterfaceControlSelectors

from ....usb.control.request import AudioRequestHandler

@sim_case(
	domains = (('usb', 60e6),),
	dut = AudioRequestHandler()
)
def audioRequestHandler(sim : Simulator, dut : AudioRequestHandler):
	interface = dut.interface
	rx = interface.rx

	def sendSetup(setup):
		yield setup.recipient.eq(USBRequestRecipient.INTERFACE)
		yield setup.type.eq(USBRequestType.CLASS)
		yield setup.is_in_request.eq(0)
		yield setup.request.eq(AudioClassSpecificRequestCodes.CUR)
		yield setup.value[0:7].eq(0)
		yield setup.value[8:15].eq(AudioControlInterfaceControlSelectors.AC_POWER_DOMAIN_CONTROL)
		yield setup.index[0:7].eq(0)
		yield setup.index[8:15].eq(11)
		yield setup.length.eq(1)

	def domainUSB():
		yield
		yield from sendSetup(interface.setup)
		yield interface.setup.received.eq(1)
		yield Settle()
		yield
		yield interface.setup.received.eq(0)
		yield Settle()
		yield
		yield
		yield rx.valid.eq(1)
		yield Settle()
		yield
		yield rx.payload.eq(1)
		yield rx.next.eq(1)
		yield Settle()
		yield
		yield rx.next.eq(0)
		yield Settle()
		yield
		yield rx.valid.eq(0)
		yield Settle()
		yield
	yield domainUSB, 'usb'
