from enum import IntEnum, auto, unique
import construct

from usb_protocol.types.descriptor import DescriptorField, DescriptorNumber, DescriptorFormat
from usb_protocol.types.descriptors.uac3 import (
	AudioClassSpecificDescriptorTypes, AudioClassSpecificACInterfaceDescriptorSubtypes,
)

__all__ = (
	'AudioChannels',
	'ConnectorAttributes',
	'ConnectorColour',
	'MonoFeatureUnitDescriptor',
	'StereoFeatureUnitDescriptor'
)

@unique
class AudioChannels(IntEnum):
	MONO = auto()
	STEREO = auto()

@unique
class ConnectorAttributes(IntEnum):
	NEUTERAL = 0x00
	MALE = 0x01
	FEMALE = 0x02
	INSERTION_DETECTION = 0x04

class ConnectorColour(int):
	def __init__(self, *, colour = None, unspecified = None):
		assert colour is not None or unspecified is not None, 'One of colour and/or unspecified must be given'
		if unspecified is True:
			super().__init__(0x01000000)
		elif isinstance(colour, int):
			assert (colour & 0xFF000000) == 0, 'Colour must be a 24-bit RGB value'
			super().__init__(colour & 0x00FFFFFF)
		else:
			raise AssertionError('unspecified was False and no colour was given or colour was non-integral')

MonoFeatureUnitDescriptor = DescriptorFormat(
	'bLength'             / construct.Const(15, construct.Int8ul),
	'bDescriptorType'     / DescriptorNumber(AudioClassSpecificDescriptorTypes.CS_INTERFACE),
	'bDescriptorSubtype'  / DescriptorNumber(AudioClassSpecificACInterfaceDescriptorSubtypes.FEATURE_UNIT),
	'bUnitID'             / DescriptorField(description = 'unique identifier for the feature unit within the audio function.'),
	'bSourceID'           / DescriptorField(description = 'ID of the unit or terminal which is connected to this feature unit'),
	'bmaControls'         / construct.Sequence(
			construct.Const(0x00000003, construct.Int32ul),
			construct.Const(0x0000000C, construct.Int32ul)
		),
	'wFeatureDescrStr'    / construct.Const(0, construct.Int16ul),
)

StereoFeatureUnitDescriptor = DescriptorFormat(
	'bLength'             / construct.Const(19, construct.Int8ul),
	'bDescriptorType'     / DescriptorNumber(AudioClassSpecificDescriptorTypes.CS_INTERFACE),
	'bDescriptorSubtype'  / DescriptorNumber(AudioClassSpecificACInterfaceDescriptorSubtypes.FEATURE_UNIT),
	'bUnitID'             / DescriptorField(description = 'unique identifier for the feature unit within the audio function.'),
	'bSourceID'           / DescriptorField(description = 'ID of the unit or terminal which is connected to this feature unit'),
	'bmaControls'         / construct.Sequence(
			construct.Const(0x00000003, construct.Int32ul),
			construct.Const(0x0000000C, construct.Int32ul),
			construct.Const(0x0000000C, construct.Int32ul)
		),
	'wFeatureDescrStr'    / construct.Const(0, construct.Int16ul),
)

ClockSourceDescriptor = DescriptorFormat(
	'bLength'             / construct.Const(12, construct.Int8ul),
	'bDescriptorType'     / DescriptorNumber(AudioClassSpecificDescriptorTypes.CS_INTERFACE),
	'bDescriptorSubtype'  / DescriptorNumber(AudioClassSpecificACInterfaceDescriptorSubtypes.CLOCK_SOURCE),
	'bClockID'            / DescriptorField(description = 'unique identifier for the clock source within the audio function.'),
	'bmAttributes'        / DescriptorField(description = 'D0: Internal Clock; D1: Endpoint Synchronous.'),
	'bmControls'          / DescriptorField(description = 'D1..0: Clock Frequency Control; D3..2: Clock Validity Control; D31..4: Reserved.', length = 4),
	'bReferenceTerminal'  / DescriptorField(description = 'ID of the terminal from which this clock source is derived. Zero if it is not derived'),
	'wCSourceDescrStr'    / DescriptorField(description = 'ID of a class-specific string descriptor, describing the clock source.'),
)

ConnectorDescriptor = DescriptorFormat(
	'wLength'             / construct.Const(18, construct.Int16ul),
	'bDescriptorType'     / DescriptorNumber(AudioClassSpecificDescriptorTypes.CS_INTERFACE),
	'bDescriptorSubtype'  / DescriptorNumber(AudioClassSpecificACInterfaceDescriptorSubtypes.CONNECTORS),
	'wDescriptorID'       / DescriptorField(description = 'unique identifier for the connector descriptor'),
	'bNrConnectors'       / DescriptorField(description = 'number of connectors associated with the parent terminal'),
	'bConID'              / DescriptorField(description = 'unique identifier for the connector'),
	'wClusterDescrID'     / DescriptorField(description = 'ID of the cluster descriptor for this connector'),
	'bConType'            / DescriptorField(description = 'type of the connector'),
	'bmConAttributes'     / DescriptorField(description = 'D1..0: Connector Gender; D2: Insertion Detection Presense; D7..3: Reserved. physical attributes of the connector'),
	'wConDescrStr'        / construct.Const(0, construct.Int16ul),
	'dwConColor'          / DescriptorField(description = 'colour of the physical connector'),
)
