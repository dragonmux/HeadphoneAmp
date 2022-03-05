from amaranth import Elaboratable, Module
from luna.usb2 import USBDevice
from usb_protocol.emitters.descriptors.standard import (
	DeviceDescriptorCollection, LanguageIDs, DeviceClassCodes, MiscellaneousSubclassCodes, MultifunctionProtocolCodes
)

from usb_protocol.emitters.descriptors.uac3 import *
from .types import *

__all__ = (
	'USBInterface',
)

class USBInterface(Elaboratable):
	def __init__(self, *, resource):
		self._ulpiResource = resource

	def elaborate(self, platform):
		m = Module()
		self.ulpiInterface = platform.request(*self._ulpiResource)
		# Constrain the ULPI clock to 60MHz
		platform.add_clock_constraint(self.ulpiInterface.clk.i, 60e6)
		m.submodules.device = device = USBDevice(bus = self.ulpiInterface, handle_clocking = True)

		descriptors = DeviceDescriptorCollection()
		with descriptors.DeviceDescriptor() as deviceDesc:
			deviceDesc.bDeviceClass = DeviceClassCodes.MISCELLANEOUS
			deviceDesc.bDeviceSubclass = MiscellaneousSubclassCodes.MULTIFUNCTION
			deviceDesc.bDeviceProtocol = MultifunctionProtocolCodes.INTERFACE_ASSOCIATION
			deviceDesc.idVendor = 0x1209
			deviceDesc.idProduct = 0xBADC
			deviceDesc.bcdDevice = 1.01
			deviceDesc.iManufacturer = 'bad_alloc Heavy Industries'
			deviceDesc.iProduct = 'Headphone Amp+DAC Audio Interface'
			#deviceDesc.iSerialNumber
			deviceDesc.bNumConfigurations = 1

		with descriptors.ConfigurationDescriptor() as configDesc:
			configDesc.bConfigurationValue = 1
			configDesc.iConfiguration = 'PCM audio interface'
			# Bus powered with no remote wakeup support
			configDesc.bmAttributes = 0x80
			# 50mA max.
			configDesc.bMaxPower = 25

			with configDesc.InterfaceAssociationDescriptor() as ifaceAssocDesc:
				ifaceAssocDesc.bFirstInterface = 0
				ifaceAssocDesc.bInterfaceCount = 2
				ifaceAssocDesc.bFunctionClass = AudioFunctionClassCode.AUDIO_FUNCTION
				ifaceAssocDesc.bFunctionSubclass = AudioFunctionSubclassCodes.HEADPHONE
				ifaceAssocDesc.bFunctionProtocol = AudioFunctionProtocolCodes.AF_VERSION_03_00
				ifaceAssocDesc.iFunction = 'PCM audio interface'

			with configDesc.InterfaceDescriptor() as interfaceDesc:
				interfaceDesc.bInterfaceNumber = 0
				interfaceDesc.bAlternateSetting = 0
				interfaceDesc.bInterfaceClass = AudioInterfaceClassCode.AUDIO
				interfaceDesc.bInterfaceSubclass = AudioInterfaceSubclassCodes.AUDIO_CONTROL
				interfaceDesc.bInterfaceProtocol = AudioInterfaceProtocolCodes.IP_VERSION_03_00
				interfaceDesc.iInterface = 'Control interface'

			with configDesc.InterfaceDescriptor() as interfaceDesc:
				interfaceDesc.bInterfaceNumber = 1
				interfaceDesc.bAlternateSetting = 0
				interfaceDesc.bInterfaceClass = AudioInterfaceClassCode.AUDIO
				interfaceDesc.bInterfaceSubclass = AudioInterfaceSubclassCodes.AUDIO_STREAMING
				interfaceDesc.bInterfaceProtocol = AudioInterfaceProtocolCodes.IP_VERSION_03_00
				interfaceDesc.iInterface = 'Output stream interface'

				with interfaceDesc.EndpointDescriptor() as ep1Out:
					ep1Out.bEndpointAddress = 0x01
					# Isochronous asynchronous data endpoint
					ep1Out.bmAttributes = 0x05
					ep1Out.wMaxPacketSize = 64
					ep1Out.bInterval = 4 # Spec requires we support a 1ms interval here.

		descriptors.add_language_descriptor((LanguageIDs.ENGLISH_US, ))
		device.add_standard_control_endpoint(descriptors)

		# Signal that we always want LUNA to try connecting
		m.d.comb += [
			device.connect.eq(1),
			device.low_speed_only.eq(0),
			device.full_speed_only.eq(0),
		]
		return m
