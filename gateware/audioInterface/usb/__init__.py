from torii import Elaboratable, Module
from sol_usb.usb2 import USBDevice
from usb_construct.types import USBTransferType, USBSynchronizationType, USBUsageType
from usb_construct.emitters.descriptors.standard import (
	DeviceDescriptorCollection, LanguageIDs, DeviceClassCodes, MiscellaneousSubclassCodes,
	MultifunctionProtocolCodes, InterfaceClassCodes, ApplicationSubclassCodes, DFUProtocolCodes
)
from usb_construct.emitters.descriptors.uac3 import *
from usb_construct.contextmgrs.descriptors.uac3 import *
from usb_construct.emitters.descriptors.dfu import *
from usb_construct.contextmgrs.descriptors.dfu import *
from usb_construct.emitters.descriptors.microsoft import PlatformDescriptorCollection
from usb_construct.contextmgrs.descriptors.microsoft import *

from .types import *
from .control import *

__all__ = (
	'USBInterface',
)

class USBInterface(Elaboratable):
	def __init__(self, *, resource):
		self.audioRequestHandler = AudioRequestHandler(configuration = 1, interfaces = (0, 1))

		self._ulpiResource = resource
		self._endpoints = []

	def addEndpoint(self, endpoint):
		self._endpoints.append(endpoint)

	def elaborate(self, platform):
		m = Module()
		self.ulpiInterface = platform.request(*self._ulpiResource)
		m.submodules.device = device = USBDevice(bus = self.ulpiInterface, handle_clocking = True)

		descriptors = DeviceDescriptorCollection()
		with descriptors.DeviceDescriptor() as deviceDesc:
			deviceDesc.bcdUSB = 2.01
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

				with HeaderDescriptor(interfaceDesc) as headerDesc:
					headerDesc.bCategory = AudioFunctionCategoryCodes.HEADPHONE
					# Read-only latency control
					headerDesc.bmControls = 0x00000001

					with InputTerminalDescriptor(headerDesc) as terminalDesc:
						terminalDesc.bTerminalID = 1
						terminalDesc.wTerminalType = USBTerminalTypes.USB_STREAMING
						terminalDesc.bAssocTerminal = 0
						terminalDesc.bCSourceID = 9
						# No controls
						terminalDesc.bmControls = 0x00000000
						terminalDesc.wClusterDescrID = 2
						terminalDesc.wExTerminalDescrID = 0
						terminalDesc.wConnectorsDescrID = 0
						terminalDesc.wTerminalDescrStr = 0

					with OutputTerminalDescriptor(headerDesc) as terminalDesc:
						terminalDesc.bTerminalID = 3
						terminalDesc.wTerminalType = OutputTerminalTypes.HEADPHONES
						terminalDesc.bAssocTerminal = 0
						terminalDesc.bSourceID = 2
						# No controls
						terminalDesc.bmControls = 0x00000000
						terminalDesc.bCSourceID = 9
						terminalDesc.wExTerminalDescrID = 0
						terminalDesc.wConnectorsDescrID = 0
						terminalDesc.wTerminalDescrStr = 0

					with FeatureUnitDescriptor(headerDesc, AudioChannels.STEREO) as unitDesc:
						unitDesc.bUnitID = 2
						unitDesc.bSourceID = 1

					with ClockSourceDescriptor(headerDesc) as clockDesc:
						clockDesc.bClockID = 9
						# Async internal clock
						clockDesc.bmAttributes = 0x01
						# With only read-only frequency control (hah)
						clockDesc.bmControls = 0x00000001
						# Which is not derived in any manner
						clockDesc.bReferenceTerminal = 0
						clockDesc.wCSourceDescrStr = 0

					with PowerDomainDescriptor(headerDesc) as pdDesc:
						pdDesc.bPowerDomainID = 10
						# 30ms and 300ms expressed in 50µs increments
						pdDesc.waRecoveryTime = [600, 6000]
						pdDesc.bNrEntities = 2
						pdDesc.baEntityID = [1, 3]
						pdDesc.wPDomainDescrStr = 0

					# This is actually a "High Capability" descriptor that's returned another way.
					# with ConnectorsDescriptor(headerDesc) as connectorDesc:
					# 	connectorDesc.wDescriptorID = 4
					# 	connectorDesc.bNrConnectors = 1
					# 	connectorDesc.bConnID = 1
					# 	connectorDesc.waClusterDescrID = 2
					# 	connectorDesc.baConType = ConnectorTypes.PHONE_CONNECTOR_3_5_MM
					# 	connectorDesc.bmaConAttributes = ConnectorAttributes.FEMALE | ConnectorAttributes.INSERTION_DETECTION
					# 	connectorDesc.daConColor = ConnectorColour(colour = 0x000000)

			with configDesc.InterfaceDescriptor() as interfaceDesc:
				interfaceDesc.bInterfaceNumber = 1
				interfaceDesc.bAlternateSetting = 0
				interfaceDesc.bInterfaceClass = AudioInterfaceClassCode.AUDIO
				interfaceDesc.bInterfaceSubclass = AudioInterfaceSubclassCodes.AUDIO_STREAMING
				interfaceDesc.bInterfaceProtocol = AudioInterfaceProtocolCodes.IP_VERSION_03_00

			with configDesc.InterfaceDescriptor() as interfaceDesc:
				interfaceDesc.bInterfaceNumber = 1
				interfaceDesc.bAlternateSetting = 1
				interfaceDesc.bInterfaceClass = AudioInterfaceClassCode.AUDIO
				interfaceDesc.bInterfaceSubclass = AudioInterfaceSubclassCodes.AUDIO_STREAMING
				interfaceDesc.bInterfaceProtocol = AudioInterfaceProtocolCodes.IP_VERSION_03_00
				interfaceDesc.iInterface = 'Output stream interface'

				with ClassSpecificAudioStreamingInterfaceDescriptor(interfaceDesc) as streamDesc:
					streamDesc.bTerminalLink = 1
					# No controls
					streamDesc.bmControls = 0x00000000
					streamDesc.wClusterDescrID = 2
					streamDesc.bmFormats = AudioDataFormats.PCM
					# 16-bit PCM audio here please
					streamDesc.bSubslotSize = 2
					streamDesc.bBitResolution = 16
					streamDesc.bmAuxProtocols = 0x0000
					streamDesc.bControlSize = 0

				with interfaceDesc.EndpointDescriptor() as ep1Out:
					ep1Out.bEndpointAddress = 0x01
					ep1Out.bmAttributes = USBTransferType.ISOCHRONOUS | USBSynchronizationType.ASYNC | USBUsageType.DATA
					ep1Out.wMaxPacketSize = 196
					ep1Out.bInterval = 4 # Spec requires we support a 1ms interval here.

			with configDesc.InterfaceAssociationDescriptor() as ifaceAssocDesc:
				ifaceAssocDesc.bFirstInterface = 2
				ifaceAssocDesc.bInterfaceCount = 1
				ifaceAssocDesc.bFunctionClass = InterfaceClassCodes.APPLICATION
				ifaceAssocDesc.bFunctionSubclass = ApplicationSubclassCodes.DFU
				ifaceAssocDesc.bFunctionProtocol = DFUProtocolCodes.APPLICATION
				ifaceAssocDesc.iFunction = 'Gateware DFU interface'

			with configDesc.InterfaceDescriptor() as interfaceDesc:
				interfaceDesc.bInterfaceNumber = 2
				interfaceDesc.bAlternateSetting = 0
				interfaceDesc.bInterfaceClass = InterfaceClassCodes.APPLICATION
				interfaceDesc.bInterfaceSubclass = ApplicationSubclassCodes.DFU
				interfaceDesc.bInterfaceProtocol = DFUProtocolCodes.APPLICATION
				interfaceDesc.iInterface = 'Audio interface device gateware upgrade interface'

				with FunctionalDescriptor(interfaceDesc) as functionalDesc:
					functionalDesc.bmAttributes = (
						DFUWillDetach.YES | DFUManifestationTolerant.NO | DFUCanUpload.NO | DFUCanDownload.YES
					)
					functionalDesc.wDetachTimeOut = 1000
					functionalDesc.wTransferSize = 4096

		platformDescriptors = PlatformDescriptorCollection()
		with descriptors.BOSDescriptor() as bos:
			with PlatformDescriptor(bos, platform_collection = platformDescriptors) as platformDesc:
				with platformDesc.DescriptorSetInformation() as descSetInfo:
					descSetInfo.bMS_VendorCode = 1

					with descSetInfo.SetHeaderDescriptor() as setHeader:
						with setHeader.SubsetHeaderConfiguration() as subsetConfig:
							subsetConfig.bConfigurationValue = 1

							with subsetConfig.SubsetHeaderFunction() as subsetFunc:
								subsetFunc.bFirstInterface = 2

								with subsetFunc.FeatureCompatibleID() as compatID:
									compatID.CompatibleID = 'WINUSB'
									compatID.SubCompatibleID = ''

		descriptors.add_language_descriptor((LanguageIDs.ENGLISH_US, ))
		ep0 = device.add_standard_control_endpoint(descriptors)

		ep0.add_request_handler(self.audioRequestHandler)
		ep0.add_request_handler(DFURequestHandler(configuration = 1, interface = 2))
		ep0.add_request_handler(WindowsRequestHandler(platformDescriptors))

		for endpoint in self._endpoints:
			device.add_endpoint(endpoint)

		# Signal that we always want LUNA to try connecting
		m.d.comb += [
			device.connect.eq(1),
			device.low_speed_only.eq(0),
			device.full_speed_only.eq(0),
		]
		return m
