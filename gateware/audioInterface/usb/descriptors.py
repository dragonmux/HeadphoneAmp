import construct

from usb_construct.types.descriptor import DescriptorField, DescriptorNumber, DescriptorFormat
from usb_construct.types.descriptors.uac3 import (
	AudioClassSpecificDescriptorTypes, AudioClassSpecificACInterfaceDescriptorSubtypes,
)

__all__ = (
	'MonoFeatureUnitDescriptor',
	'StereoFeatureUnitDescriptor'
)

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
